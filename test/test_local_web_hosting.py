"""Hosted transport checks use real Waitress, fake identity, and local engine jobs."""
from copy import deepcopy
from dataclasses import replace
from http.client import HTTPConnection
import io
import json
import os
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit

import pytest

from src.local_web.auth import OIDCConfig, Sessions, digest
from src.local_web.hosting import public_origin_from_environment, validate_public_origin
from src.local_web.runtime import Application, ROOT
from src.local_web.server import make_server, make_wsgi_app

ORIGIN='https://microgrid.example.com'
CONFIG=OIDCConfig('https://identity.example', 'client', 'test-secret', ORIGIN+'/auth/callback')


class Provider:
    def authorize(self,state,nonce,verifier):
        return 'https://identity.example/authorize?state='+state
    def exchange(self,code,nonce,verifier):
        return digest(code)


@pytest.fixture
def hosted(tmp_path):
    app=Application(tmp_path,embedded_worker=False)
    auth=Sessions(app.store,CONFIG,Provider())
    server=make_server(app,0,auth=auth,public_origin=ORIGIN)
    thread=threading.Thread(target=server.serve_forever);thread.start()
    def call(path,body=None,headers=None,proxy=True,method=None):
        conn=HTTPConnection('127.0.0.1',server.server_port,timeout=60)
        h={'Host':'microgrid.example.com','Content-Type':'application/json'}
        if proxy:h['X-Forwarded-Proto']='https'
        h.update(headers or {})
        conn.request(method or ('GET' if body is None else 'POST'),path,None if body is None else json.dumps(body),h)
        r=conn.getresponse();data=r.read()
        result=json.loads(data) if r.getheader('Content-Type')=='application/json' else data
        answer=r.status,result,r.getheaders();conn.close();return answer
    try:yield app,auth,call,server
    finally:server.shutdown();thread.join(timeout=15);server.server_close();app.close()


def signin(call,user):
    status,_,headers=call('/auth/login');h=dict(headers)
    assert status==302
    state=parse_qs(urlsplit(h['Location']).query)['state'][0]
    cookie=h['Set-Cookie'].split(';')[0]
    status,_,headers=call('/auth/callback?state='+state+'&code='+user,headers={'Cookie':cookie})
    assert status==302
    cookie=next(v for k,v in headers if k=='Set-Cookie' and v.startswith('__Host-microgrid_session='))
    assert '; Secure' in cookie and '; HttpOnly' in cookie and '; Path=/' in cookie and 'Domain=' not in cookie
    user_headers={'Cookie':cookie.split(';')[0]}
    status,caps,_=call('/api/capabilities',headers=user_headers)
    assert status==200 and caps['hosting_mode']=='hosted'
    return {**user_headers,'X-Study-Token':caps['token']},caps


@pytest.mark.parametrize('origin',[
    '', 'http://microgrid.example.com', 'https://microgrid.example.com/',
    'https://microgrid.example.com/path', 'https://microgrid.example.com?x=1',
    'https://user:password@microgrid.example.com', 'https://microgrid.example.com#x',
    'https://microgrid.example.com:bad', 'https://microgrid.example.com:0',
    'https://microgrid.example.com\n', 'https://microgrid.example.com:99999',
])
def test_origin_rejects_unsafe_configuration(origin):
    with pytest.raises(ValueError):validate_public_origin(origin)


def test_hosted_configuration_fails_closed(monkeypatch,tmp_path):
    monkeypatch.setenv('MICROGRID_PUBLIC_ORIGIN',ORIGIN)
    assert public_origin_from_environment(True,CONFIG)==ORIGIN
    with pytest.raises(ValueError):public_origin_from_environment(False,CONFIG)
    with pytest.raises(ValueError):public_origin_from_environment(True,None)
    with pytest.raises(ValueError):public_origin_from_environment(True,replace(CONFIG,redirect_uri='https://other.example/auth/callback'))
    app=Application(tmp_path,embedded_worker=False)
    try:
        with pytest.raises(ValueError):make_server(app,0,public_origin=ORIGIN)
        auth=Sessions(app.store,CONFIG,Provider())
        with pytest.raises(ValueError):make_server(app,0,auth=auth)
    finally:app.close()


def test_proxy_boundary_origin_and_cookie_protection(hosted):
    app,auth,call,server=hosted
    assert server.server.socket.getsockname()[0]=='127.0.0.1'
    assert call('/api/studies')[0]==401
    assert call('/',proxy=False)[0]==403
    assert call('/',headers={'Host':'evil.example'})[0]==403
    assert call('/',headers={'X-Forwarded-Proto':'http'})[0]==403
    assert call('/',headers={'X-Forwarded-Host':'evil.example','Forwarded':'host=evil.example;proto=http'})[0]==200
    status,_,headers=call('/')
    assert status==200 and dict(headers)['Strict-Transport-Security']=='max-age=31536000'
    alice,caps=signin(call,'alice');bob,_=signin(call,'bob')
    assert call('/api/studies',caps['defaults'],{**alice,'Origin':'http://microgrid.example.com'})[0]==403
    assert call('/api/studies',caps['defaults'],{**alice,'Origin':'https://evil.example'})[0]==403
    assert call('/api/studies',caps['defaults'],{**alice,'X-Study-Token':bob['X-Study-Token']})[0]==403
    assert call('/api/studies',headers={'Cookie':alice['Cookie'].replace('__Host-microgrid_session','microgrid_session')})[0]==401
    status,_,headers=call('/auth/logout',{},alice)
    assert status==200
    assert 'Secure' in dict(headers)['Set-Cookie'] and 'Max-Age=0' in dict(headers)['Set-Cookie']
    assert call('/api/studies',headers=alice)[0]==401
    assert call('/api/studies',headers=bob)[0]==200


def test_hosted_worker_and_download_pipeline(hosted):
    app,auth,call,server=hosted
    alice,caps=signin(call,'alice');bob,_=signin(call,'bob')
    request=deepcopy(caps['defaults'])
    request.update(start_date='2026-08-01',end_date='2026-08-01',strategies=['no_battery'])
    status,study,_=call('/api/studies',request,alice)
    assert status==202 and study['status']=='queued'
    assert call('/api/health',headers=alice)[1]['worker']=='offline'
    process=subprocess.Popen([sys.executable,'-m','src.local_web.runner','--data-dir',str(app.store.directory)],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            status,result,_=call('/api/studies/'+study['id'],headers=alice)
            if result['status'] in ('completed','failed'):break
            time.sleep(.2)
        assert result['status']=='completed',result
        assert result['started_at'] and result['runtime_seconds'] > 0
        table=result['result']['tables'][0]['id']
        for suffix in ['/request.json','/result.json','/tables/'+table,'/tables/'+table+'.csv']:
            path='/api/studies/'+study['id']+suffix
            assert call(path,headers=alice)[0]==200
            assert call(path,headers=bob)[0]==404
        assert result['owner_id']==digest('alice')
        assert call('/api/usage',headers=alice)[1]['used_seconds'] > 0
        assert call('/api/usage',headers=bob)[1]['used_seconds'] == 0
    finally:
        process.terminate();process.communicate(timeout=15)
        assert process.returncode==0


def test_unexpected_errors_do_not_reach_logs_or_response(hosted,monkeypatch,caplog):
    app,auth,call,_=hosted
    alice,_=signin(call,'alice')
    def fail(*a):raise RuntimeError('secret-provider-response')
    monkeypatch.setattr(app,'health',fail)
    status,result,_=call('/api/health',headers=alice)
    assert status==500 and 'secret-provider-response' not in str(result)
    assert 'secret-provider-response' not in caplog.text


def test_local_transport_does_not_trust_forwarding_headers(tmp_path):
    app=Application(tmp_path,embedded_worker=False)
    server=make_server(app,0)
    thread=threading.Thread(target=server.serve_forever);thread.start()
    try:
        conn=HTTPConnection('127.0.0.1',server.server_port)
        conn.request('GET','/api/capabilities',headers={'X-Forwarded-Proto':'https','X-Forwarded-Host':'evil.example'})
        response=conn.getresponse()
        assert response.status==200 and json.loads(response.read())['auth_mode']=='local'
        conn.close()
    finally:server.shutdown();thread.join();server.server_close();app.close()


def test_actual_caddy_https_login_worker_and_download(tmp_path):
    """Optional real proxy test: certificate verification stays ON; no OS trust changes."""
    from datetime import datetime, timedelta, timezone
    from pathlib import Path
    import socket
    import requests
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    binary=os.getenv('MICROGRID_TEST_CADDY')
    if not binary:
        pytest.skip('Set MICROGRID_TEST_CADDY to a verified Caddy binary for the real TLS check.')
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')])
    stamp=datetime.now(timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(stamp-timedelta(minutes=1))
          .not_valid_after(stamp+timedelta(hours=1))
          .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]),critical=False)
          .add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True)
          .sign(key,hashes.SHA256()))
    certfile,keyfile=tmp_path/'certificate.pem',tmp_path/'key.pem'
    certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    keyfile.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    keyfile.chmod(0o600)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    origin=f'https://localhost:{port}'
    app=Application(tmp_path/'data',embedded_worker=False)
    auth=Sessions(app.store,replace(CONFIG,redirect_uri=origin+'/auth/callback'),Provider())
    server=make_server(app,0,auth=auth,public_origin=origin)
    thread=threading.Thread(target=server.serve_forever);thread.start()
    template=(ROOT/'deploy/Caddyfile').read_text()
    config=(template.replace('{\n', '{\n admin off\n auto_https off\n', 1).replace('{$MICROGRID_SITE_ADDRESS} {',origin+' {\n bind 127.0.0.1\n tls "'+str(certfile)+'" "'+str(keyfile)+'"').replace('127.0.0.1:8765',f'127.0.0.1:{server.server_port}'))
    path=tmp_path/'Caddyfile';path.write_text(config)
    proxy=runner=None
    proxy_log=(tmp_path/'proxy.log').open('w')
    client=requests.Session();client.trust_env=False;client.verify=str(certfile)
    try:
        proxy=subprocess.Popen([binary,'run','--config',str(path),'--adapter','caddyfile'],stdout=subprocess.DEVNULL,stderr=proxy_log,env={**os.environ,'XDG_CONFIG_HOME':str(tmp_path/'config'),'XDG_DATA_HOME':str(tmp_path/'proxy-data')})
        deadline=time.monotonic()+15
        while True:
            try:
                response=client.get(origin+'/',timeout=2)
                break
            except requests.ConnectionError:
                assert proxy.poll() is None,'Caddy failed to start'
                if time.monotonic()>deadline:raise
                time.sleep(.1)
        assert response.status_code==200
        assert client.get(origin+'/api/studies',timeout=5).status_code==401
        # The real TLS proxy overwrites visitor-supplied scheme and ignores fake identity.
        assert client.get(origin+'/',headers={'X-Forwarded-Proto':'http','Forwarded':'proto=http','X-Forwarded-Host':'evil.example'},timeout=5).status_code==200
        response=client.get(origin+'/auth/login',allow_redirects=False,timeout=5)
        assert response.status_code==302 and '__Host-microgrid_login' in response.headers['Set-Cookie']
        state=parse_qs(urlsplit(response.headers['Location']).query)['state'][0]
        response=client.get(origin+'/auth/callback',params={'state':state,'code':'alice'},allow_redirects=False,timeout=5)
        assert response.status_code==302 and '; Secure' in response.headers['Set-Cookie']
        caps=client.get(origin+'/api/capabilities',timeout=10).json()
        request=deepcopy(caps['defaults']);request.update(start_date='2026-08-01',end_date='2026-08-01',strategies=['no_battery'])
        response=client.post(origin+'/api/studies',json=request,headers={'X-Study-Token':caps['token'],'Origin':origin},timeout=10)
        assert response.status_code==202,response.text
        sid=response.json()['id']
        runner=subprocess.Popen([sys.executable,'-m','src.local_web.runner','--data-dir',str(app.store.directory)],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            result=client.get(origin+'/api/studies/'+sid,timeout=5).json()
            if result['status'] in ('completed','failed'):break
            time.sleep(.2)
        assert result['status']=='completed',result
        assert result['started_at'] and result['runtime_seconds'] > 0
        table=result['result']['tables'][0]['id']
        response=client.get(origin+'/api/studies/'+sid+'/tables/'+table+'.csv',timeout=5)
        assert response.status_code==200 and 'attachment' in response.headers['Content-Disposition']
        assert client.post(origin+'/auth/logout',json={},headers={'X-Study-Token':caps['token'],'Origin':origin},timeout=5).status_code==200
        assert client.get(origin+'/api/studies/'+sid,timeout=5).status_code==401
        server.shutdown();thread.join(timeout=15)
        response=client.get(origin+'/auth/callback?code=do-not-log-this-code',headers={'Cookie':'do-not-log-this-cookie'},timeout=5)
        assert response.status_code==502
    finally:
        client.close()
        for process in (runner,proxy):
            if process is not None:
                process.terminate();process.wait(timeout=15)
        server.shutdown();thread.join(timeout=15);server.server_close();app.close()
        proxy_log.close()
    log=(tmp_path/'proxy.log').read_text()
    assert 'do-not-log-this-code' not in log and 'do-not-log-this-cookie' not in log
