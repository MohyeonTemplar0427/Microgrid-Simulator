"""Real HTTP ownership boundaries and offline OIDC signature/session tests."""
from copy import deepcopy
from dataclasses import replace
from http.client import HTTPConnection
from http.cookies import SimpleCookie
import io
import json
import secrets
import socket
import sqlite3
import threading
import time
import zipfile
from types import SimpleNamespace
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
from joserfc import jwk, jwt

from src.local_web.auth import AuthenticationRequired, OIDCConfig, OIDCProvider, Sessions, digest
from src.local_web.runtime import Application, Store, ROOT, JobRunner
from src.local_web.server import make_server
from src.local_web.worker import write_json

CONFIG = OIDCConfig('https://identity.example', 'client', 'test-client-secret', 'http://127.0.0.1:8765/auth/callback')


class FakeProvider:
    def authorize(self, state, nonce, verifier):
        return 'https://identity.example/authorize?' + urlencode(dict(state=state, nonce=nonce))

    def exchange(self, code, nonce, verifier):
        assert nonce and len(verifier) >= 43
        return digest(code)


def login(sessions, user, old_headers=None):
    location, cookie = sessions.start()
    state = parse_qs(urlsplit(location).query)['state']
    headers = {'Cookie': cookie.split(';')[0] + '; ' + (old_headers or {}).get('Cookie', '')}
    cookies = sessions.callback({'code': [user], 'state': state}, headers)
    return {'Cookie': cookies[0].split(';')[0]}


@pytest.fixture
def service(tmp_path):
    app = Application(tmp_path, embedded_worker=False)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    auth = Sessions(app.store, replace(CONFIG, redirect_uri=f'http://127.0.0.1:{port}/auth/callback'), FakeProvider())
    server = make_server(app, port, auth=auth)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()

    def call(path, body=None, headers=None):
        conn = HTTPConnection('127.0.0.1', port, timeout=60)
        hdr = {'Content-Type': 'application/json', **(headers or {})}
        conn.request('GET' if body is None else 'POST', path,
                     None if body is None else json.dumps(body), hdr)
        response = conn.getresponse()
        data = response.read()
        result = json.loads(data) if response.getheader('Content-Type') == 'application/json' else data
        out = response.status, result, response.getheaders()
        conn.close()
        return out

    try:
        yield app, auth, call
    finally:
        server.shutdown(); thread.join(); server.server_close(); app.close()


def client(auth, call, user):
    headers = login(auth, user)
    status, caps, _ = call('/api/capabilities', headers=headers)
    assert status == 200
    headers['X-Study-Token'] = caps['token']
    return headers, caps


def test_guest_study_is_private_then_saved_after_sign_in(tmp_path):
    app = Application(tmp_path, embedded_worker=False)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    auth = Sessions(app.store, replace(CONFIG, redirect_uri=f'http://127.0.0.1:{port}/auth/callback'), FakeProvider())
    server = make_server(app, port, auth=auth, allow_guests=True)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()

    def call(path, body=None, headers=None):
        conn = HTTPConnection('127.0.0.1', port, timeout=30)
        conn.request('GET' if body is None else 'POST', path,
                     None if body is None else json.dumps(body),
                     {'Content-Type': 'application/json', **(headers or {})})
        response = conn.getresponse()
        data = response.read()
        out = response.status, json.loads(data) if response.getheader('Content-Type') == 'application/json' else data, dict(response.getheaders())
        conn.close()
        return out

    try:
        status, caps, headers = call('/api/capabilities')
        assert status == 200 and caps['account_type'] == 'guest'
        guest = {'Cookie': headers['Set-Cookie'].split(';')[0], 'X-Study-Token': caps['token']}
        _, other_caps, other_headers = call('/api/capabilities')
        other = {'Cookie': other_headers['Set-Cookie'].split(';')[0], 'X-Study-Token': other_caps['token']}
        request = deepcopy(caps['defaults'])
        status, study, _ = call('/api/studies', request, guest)
        assert status == 202 and study['owner_id'].startswith('guest:') and study['saved'] == 0
        sid = study['id']
        assert call('/api/studies/'+sid, headers=other)[0] == 404
        directory = app.store.directory/'runs'/sid
        write_json(directory/'result.json', {'tables': []})
        app.store.finish(sid)
        assert call('/api/studies/'+sid, headers=guest)[1]['expires_at'] is not None
        status, bundle, _ = call('/api/studies/'+sid+'/tables.zip', headers=guest)
        assert status == 200 and bundle.startswith(b'PK')
        assert not list(app.store.directory.glob('*.zip'))
        assert app.bundle_slot.acquire(blocking=False)
        try:
            assert call('/api/studies/'+sid+'/tables.zip', headers=guest)[0] == 429
        finally:
            app.bundle_slot.release()
        assert call('/api/studies/'+sid+'/tables.zip', headers=other)[0] == 404
        assert call('/api/studies/'+sid+'/save', {}, guest)[0] == 401
        member = login(auth, 'alice')
        _, member_caps, _ = call('/api/capabilities', headers=member)
        both = {'Cookie': member['Cookie']+'; '+guest['Cookie'], 'X-Study-Token': member_caps['token']}
        assert call('/api/studies/'+sid+'/save', {}, {**member, 'X-Study-Token': member_caps['token']})[0] == 404
        assert call('/api/studies/'+sid+'/save', {}, {**both, 'Cookie': member['Cookie']+'; '+other['Cookie']})[0] == 404
        prior_cap = app.store.max_owner_run_bytes
        app.store.max_owner_run_bytes = 1
        assert call('/api/studies/'+sid+'/save', {}, both)[0] == 429
        assert call('/api/studies/'+sid, headers=guest)[0] == 200
        app.store.max_owner_run_bytes = prior_cap
        status, saved, _ = call('/api/studies/'+sid+'/save', {}, both)
        assert status == 200 and saved['owner_id'] == digest('alice')
        assert saved['saved'] == 1 and saved['expires_at'] is None
        status, member_study, _ = call('/api/studies', request, both)
        assert status == 202 and member_study['saved'] == 0
        write_json(app.store.directory/'runs'/member_study['id']/'result.json', {'tables': []})
        app.store.finish(member_study['id'])
        status, retained, _ = call('/api/studies/'+member_study['id']+'/save', {}, both)
        assert status == 200 and retained['saved'] == 1 and retained['expires_at'] is None
        status, expiring, _ = call('/api/studies', request, both)
        assert status == 202 and expiring['saved'] == 0
        write_json(app.store.directory/'runs'/expiring['id']/'result.json', {'tables': []})
        app.store.finish(expiring['id'])
        with app.store.connect() as db:
            db.execute("UPDATE studies SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?", (expiring['id'],))
        assert app.store.purge_expired_studies() == 1
        assert call('/api/studies/'+expiring['id'], headers=both)[0] == 404
        assert call('/api/studies/'+sid, headers=guest)[0] == 404
        assert call('/api/studies/'+sid, headers=both)[0] == 200
        previous_global = app.store.guest_global_daily_limit
        app.store.guest_global_daily_limit = 1
        assert call('/api/studies', request, guest)[0] == 429
        app.store.guest_global_daily_limit = previous_global
        status, temporary, _ = call('/api/studies', request, guest)
        assert status == 202
        app.store.finish(temporary['id'])
        with app.store.connect() as db:
            db.execute("UPDATE studies SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?", (temporary['id'],))
        assert call('/api/studies/'+temporary['id'], headers=guest)[0] == 404
        assert app.store.purge_expired_studies() == 1
        assert not (app.store.directory/'runs'/temporary['id']).exists()
        assert call('/api/studies/'+sid, headers=both)[0] == 200
        raw = (ROOT/'data/default_small_business_week.csv').read_text().replace('12.714', '13.714', 1)
        status, upload, _ = call('/api/datasets', {'name': 'temporary.csv', 'csv': raw}, guest)
        assert status == 201
        weather_id = 'f'*64
        weather_dir = app.store.directory/'weather'/weather_id
        weather_dir.mkdir()
        (weather_dir/'weather.csv').write_text('temporary')
        app.store.grant('weather', weather_id, study['owner_id'])
        with app.store.connect() as db:
            db.execute("UPDATE auth_guests SET created=0 WHERE owner_id=?", (study['owner_id'],))
        app.store.purge_expired_studies()
        assert not (app.store.directory/'datasets'/(upload['id']+'.csv')).exists()
        assert not weather_dir.exists()
        assert call('/api/studies/'+sid, headers=both)[0] == 200
        status, shared_upload, _ = call('/api/datasets', {'name': 'to-save.csv', 'csv': raw}, other)
        assert status == 201
        other_request = deepcopy(other_caps['defaults'])
        other_request['dataset_id'] = shared_upload['id']
        status, other_study, _ = call('/api/studies', other_request, other)
        assert status == 202
        write_json(app.store.directory/'runs'/other_study['id']/'result.json', {'tables': []})
        app.store.finish(other_study['id'])
        other_and_member = {'Cookie': member['Cookie']+'; '+other['Cookie'], 'X-Study-Token': member_caps['token']}
        assert call('/api/studies/'+other_study['id']+'/save', {}, other_and_member)[0] == 200
        with app.store.connect() as db:
            db.execute("UPDATE auth_guests SET created=0 WHERE owner_id=?", (other_study['owner_id'],))
        app.store.purge_expired_studies()
        assert (app.store.directory/'datasets'/(shared_upload['id']+'.csv')).is_file()
        assert call('/api/studies', other_request, both)[0] == 202
        app.store.guest_global_interaction_limit = 1
        _, fresh_caps, fresh_headers = call('/api/capabilities')
        fresh = {'Cookie': fresh_headers['Set-Cookie'].split(';')[0], 'X-Study-Token': fresh_caps['token']}
        assert call('/api/ess/resolve', {}, fresh)[0] == 400
        _, next_caps, next_headers = call('/api/capabilities')
        another = {'Cookie': next_headers['Set-Cookie'].split(';')[0], 'X-Study-Token': next_caps['token']}
        assert call('/api/ess/resolve', {}, another)[0] == 429
        app.store.guest_session_limit = 1
        assert call('/api/capabilities')[0] == 429
        assert call('/api/capabilities', headers=fresh)[0] == 200
    finally:
        server.shutdown(); thread.join(); server.server_close(); app.close()


def test_all_private_routes_require_login(service):
    app, auth, call = service
    get_routes = ['/api/capabilities', '/api/session', '/api/health', '/api/usage', '/api/datasets', '/api/studies',
                  '/api/studies/'+'a'*32, '/api/studies/'+'a'*32+'/request.json',
                  '/api/studies/'+'a'*32+'/result.json', '/api/studies/'+'a'*32+'/tables/example.csv']
    post_routes = ['/api/studies', '/api/studies/'+'a'*32+'/cancel', '/api/datasets', '/api/weather', '/api/location', '/api/utilities',
                   '/api/solar/optimize', '/api/ess/resolve', '/api/v1/utility-resolution',
                   '/api/v1/municipal/eligibility', '/api/v1/municipal/bill',
                   '/api/v1/municipal/studies', '/api/v1/socal/studies', '/auth/logout']
    for route in get_routes:
        assert call(route)[0] == 401, route
        assert call(route, headers={'X-User-ID': 'alice', 'Authorization': 'Bearer forged'})[0] == 401
    for route in post_routes:
        assert call(route, {})[0] == 401, route
    assert call('/')[0] == 200
    assert call('/.env')[0] == 401


def test_private_study_downloads_datasets_and_legacy_quarantine(service):
    app, auth, call = service
    a, caps = client(auth, call, 'alice')
    b, _ = client(auth, call, 'bob')
    request = deepcopy(caps['defaults'])
    old = app.store.submit(request, app.engine)
    status, study, _ = call('/api/studies', request, a)
    assert status == 202
    sid = study['id']
    assert study['owner_id'] == digest('alice')
    directory = app.store.directory / 'runs' / sid
    write_json(directory/'result.json', {'tables': [{'id': 'comparison'}]})
    write_json(directory/'comparison.json', {'columns': ['value'], 'data': [[12]]})
    (directory/'comparison.csv').write_text('value\n12\n')
    app.store.finish(sid)
    for suffix in ['', '/request.json', '/result.json', '/tables/comparison', '/tables/comparison.csv']:
        assert call('/api/studies/'+sid+suffix, headers=a)[0] == 200
        assert call('/api/studies/'+sid+suffix, headers=b)[0] == 404
        assert call('/api/studies/'+old['id']+suffix, headers=a)[0] == 404
    assert [r['id'] for r in call('/api/studies', headers=a)[1]] == [sid]
    assert call('/api/studies', headers=b)[1] == []
    assert call('/api/health', headers=b)[1]['queued'] == 0
    raw = (ROOT/'data/default_small_business_week.csv').read_text().replace('12.714', '13.714', 1)
    status, upload, _ = call('/api/datasets', {'name': 'private.csv', 'csv': raw}, a)
    assert status == 201
    assert upload['id'] not in {d['id'] for d in call('/api/datasets', headers=b)[1]}
    request['dataset_id'] = upload['id']
    assert call('/api/studies', request, b)[0] == 404
    assert call('/api/studies', request, a)[0] == 202
    # Identical data uploaded deliberately by both users must not reveal filenames.
    assert call('/api/datasets', {'name': 'bob.csv', 'csv': raw}, b)[1]['name'] == 'bob.csv'
    assert next(d for d in call('/api/datasets', headers=a)[1] if d['id']==upload['id'])['name'] == 'private.csv'
    request['owner_id'] = digest('bob')
    assert call('/api/studies', request, a)[0] == 400


def test_alternate_routes_and_reference_ids_cannot_cross_owners(service):
    app, auth, call = service
    a, caps = client(auth, call, 'alice')
    b, _ = client(auth, call, 'bob')
    rid, wid = 'a'*32, 'b'*64
    app.store.grant('resolution', rid, digest('alice'))
    app.store.grant('weather', wid, digest('alice'))
    for path in ['/api/v1/municipal/studies', '/api/v1/socal/studies',
                 '/api/v1/municipal/eligibility', '/api/v1/municipal/bill']:
        body = {'resolution_id': rid, 'schema_version': 6}
        assert call(path, body, b)[0] == 404
    assert call('/api/solar/optimize', {'study': {}, 'weather_id': wid}, b)[0] == 404
    request = deepcopy(caps['site_defaults'])
    request.update(weather_source='nsrdb', weather_id=wid)
    assert call('/api/studies', request, b)[0] == 404
    # The general study route cannot bypass the dedicated municipal/SCE resolver.
    for version in [4, 6]:
        assert call('/api/studies', {'schema_version': version, 'resolution_id': rid}, b)[0] == 400


def test_session_csrf_logout_and_origin_guards(service):
    app, auth, call = service
    a, caps = client(auth, call, 'alice')
    b, _ = client(auth, call, 'bob')
    assert call('/api/studies', caps['defaults'], {'Cookie':a['Cookie']})[0] == 403
    assert call('/api/studies', caps['defaults'], {**a, 'X-Study-Token':b['X-Study-Token']})[0] == 403
    assert call('/api/studies', caps['defaults'], {**a, 'Origin':'https://evil.example'})[0] == 403
    assert call('/api/studies', caps['defaults'], {**a, 'Host':'public.example'})[0] == 403
    assert call('/auth/logout', {}, a)[0] == 200
    assert call('/api/studies', headers=a)[0] == 401
    assert call('/api/studies', headers=b)[0] == 200
    assert call('/api/studies', headers={'Cookie':'microgrid_session=forged'})[0] == 401
    with pytest.raises(ValueError, match='requires OIDC'):
        make_server(app, 0)


def test_real_worker_retains_owner_and_outputs(service):
    app, auth, call = service
    a, caps = client(auth, call, 'alice')
    b, _ = client(auth, call, 'bob')
    request = deepcopy(caps['defaults'])
    request.update(start_date='2026-08-01', end_date='2026-08-01', strategies=['no_battery'])
    status, study, _ = call('/api/studies', request, a)
    assert status == 202
    runner = JobRunner(app.store)
    try:
        deadline = time.monotonic()+60
        while time.monotonic()<deadline:
            status, result, _ = call('/api/studies/'+study['id'], headers=a)
            if result['status'] in ('completed','failed'):
                break
            time.sleep(.2)
        assert result['status']=='completed', result
        assert result['owner_id']==digest('alice')
        assert call('/api/usage', headers=a)[1]['used_seconds'] > 0
        assert call('/api/usage', headers=b)[1]['used_seconds'] == 0
        tid=result['result']['tables'][0]['id']
        assert call('/api/studies/'+study['id']+'/tables/'+tid+'.csv', headers=a)[0]==200
        assert call('/api/studies/'+study['id']+'/tables/'+tid+'.csv', headers=b)[0]==404
        status, bundle, _ = call('/api/studies/'+study['id']+'/tables.zip', headers=a)
        assert status == 200
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            assert tid+'.csv' in archive.namelist()
            assert 'result-manifest.json' in archive.namelist()
        assert call('/api/studies/'+study['id']+'/tables.zip', headers=b)[0]==404
        assert Store(app.store.directory).get(study['id'], digest('alice'))['owner_id']==digest('alice')
    finally:
        runner.close()


def test_session_restart_rotation_expiry_and_callback_replay(tmp_path):
    store=Store(tmp_path)
    auth=Sessions(store, CONFIG, FakeProvider())
    a=login(auth,'alice')
    assert Sessions(store, CONFIG, FakeProvider()).authenticate(a)['owner_id']==digest('alice')
    newer=login(auth,'alice',a)
    with pytest.raises(AuthenticationRequired): auth.authenticate(a)
    assert newer != a
    location, cookie=auth.start()
    params={'state':parse_qs(urlsplit(location).query)['state'], 'code':['alice']}
    with pytest.raises(AuthenticationRequired): auth.callback(params, {})
    headers={'Cookie':cookie.split(';')[0]}
    auth.callback(params, headers)
    with pytest.raises(AuthenticationRequired): auth.callback(params, headers)
    with store.connect() as db:
        db.execute('UPDATE auth_sessions SET last_seen=?',(time.time()-1801,))
    with pytest.raises(AuthenticationRequired): auth.authenticate(newer)
    newer=login(auth,'alice')
    with store.connect() as db:
        db.execute('UPDATE auth_sessions SET created=?',(time.time()-28801,))
    with pytest.raises(AuthenticationRequired): auth.authenticate(newer)
    assert 'HttpOnly' in cookie and 'SameSite=Lax' in cookie and 'Path=/' in cookie


def test_hosted_guest_cookie_uses_secure_host_prefix(tmp_path):
    store = Store(tmp_path)
    config = replace(CONFIG, redirect_uri='https://microgrid.example/auth/callback')
    auth = Sessions(store, config, FakeProvider())
    guest, cookie = auth.guest({}, create=True)
    assert guest['owner_id'].startswith('guest:')
    assert cookie.startswith('__Host-microgrid_guest=')
    assert all(flag in cookie for flag in ('; Secure', '; HttpOnly', '; SameSite=Lax', '; Path=/'))
    assert auth.guest({'Cookie': cookie.split(';')[0]})[0]['owner_id'] == guest['owner_id']


def test_legacy_database_migration_is_non_destructive(tmp_path):
    db=sqlite3.connect(tmp_path/'studies.sqlite3')
    db.execute('CREATE TABLE studies(id TEXT PRIMARY KEY, name TEXT, status TEXT, created_at TEXT, finished_at TEXT, engine_id TEXT, error TEXT)')
    db.execute("INSERT INTO studies VALUES ('old','old','queued','then',NULL,'engine',NULL)")
    db.commit();db.close()
    store=Store(tmp_path)
    assert store.list('new-user')==[]
    assert store.list()[0]['owner_id'] is None
    assert store.list()[0]['started_at'] is None
    assert store.list()[0]['runtime_seconds'] is None
    claimed = store.claim()
    assert claimed['owner_id'] is None
    assert store.list()[0]['started_at'] is not None
    assert store.list()[0]['runtime_seconds'] is None


@pytest.mark.parametrize('changes', [
    {'iss':'https://evil.example'}, {'aud':'wrong-client'}, {'nonce':'wrong'},
    {'exp':1}, {'sub':''}, {'azp':'wrong-client'}, {'iat':time.time()+1000},
])
def test_oidc_rejects_invalid_signed_claims(monkeypatch, changes):
    provider, claims = signed_provider(monkeypatch, changes)
    with pytest.raises(Exception): provider.exchange('code','nonce','v'*43)


def signed_provider(monkeypatch, changes=None, wrong_key=False):
    key=jwk.RSAKey.generate_key(2048, parameters={'kid':'test'})
    signer=jwk.RSAKey.generate_key(2048, parameters={'kid':'test'}) if wrong_key else key
    claims=dict(iss=CONFIG.issuer, sub='alice', aud=CONFIG.client_id,
                nonce='nonce', iat=int(time.time()), exp=int(time.time())+300)
    claims.update(changes or {})
    token=jwt.encode({'alg':'RS256','kid':'test'},claims,signer)
    provider=OIDCProvider(CONFIG)
    monkeypatch.setattr(provider,'metadata',lambda: {'token_endpoint':'https://identity.example/token','jwks_uri':'https://identity.example/keys'})
    monkeypatch.setattr('src.local_web.auth.OAuth2Session.fetch_token',lambda *a,**kw: {'id_token':token})
    monkeypatch.setattr('src.local_web.auth.requests.get',lambda *a,**kw: SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'keys':[key.as_dict(private=False)]}))
    return provider,claims


def test_oidc_verifies_signature_and_identity(monkeypatch):
    provider,claims=signed_provider(monkeypatch)
    assert provider.exchange('code','nonce','v'*43)==digest(json.dumps([CONFIG.issuer,'alice']))
    provider,_=signed_provider(monkeypatch,wrong_key=True)
    with pytest.raises(Exception): provider.exchange('code','nonce','v'*43)


def test_no_silent_auth_fallback(monkeypatch):
    for key in ('MICROGRID_AUTH_MODE','MICROGRID_OIDC_ISSUER','MICROGRID_OIDC_CLIENT_ID','MICROGRID_OIDC_CLIENT_SECRET','MICROGRID_OIDC_REDIRECT_URI'):
        monkeypatch.delenv(key,raising=False)
    assert OIDCConfig.from_environment() is None
    monkeypatch.setenv('MICROGRID_AUTH_MODE','oidc')
    with pytest.raises(ValueError): OIDCConfig.from_environment()
    monkeypatch.setenv('MICROGRID_AUTH_MODE','local')
    monkeypatch.setenv('MICROGRID_OIDC_CLIENT_SECRET','secret')
    with pytest.raises(ValueError): OIDCConfig.from_environment()
    from src.local_web.hosting import public_origin_from_environment
    hosted_config = replace(CONFIG,redirect_uri='https://public.example/auth/callback')
    with pytest.raises(ValueError): public_origin_from_environment(False, hosted_config)


def test_server_secrets_redacted_in_persistence_and_responses(service, monkeypatch):
    app,auth,call=service
    a,caps=client(auth,call,'alice')
    secret='private-api-value-with-quote"and/slash'
    monkeypatch.setenv('NSRDB_API_KEY',secret)
    request=deepcopy(caps['defaults']);request['name']=secret
    status,study,_=call('/api/studies',request,a)
    assert status==202 and secret not in json.dumps(study)
    assert secret not in (app.store.directory/'runs'/study['id']/'request.json').read_text()
    assert secret not in str(call('/api/studies/'+study['id']+'/request.json',headers=a))
    from src.local_web.privacy import worker_environment
    monkeypatch.setenv('MICROGRID_OIDC_CLIENT_SECRET','private-login-secret')
    assert 'MICROGRID_OIDC_CLIENT_SECRET' not in worker_environment()


def test_http_login_callback_rotates_cookie_and_hides_provider_errors(service, monkeypatch):
    app,auth,call=service
    status,_,headers=call('/auth/login')
    assert status==302
    head=dict(headers)
    assert head['Cache-Control']=='no-store' and head['Referrer-Policy']=='no-referrer'
    state=parse_qs(urlsplit(head['Location']).query)['state'][0]
    browser_cookie=head['Set-Cookie'].split(';')[0]
    path='/auth/callback?'+urlencode({'state':state,'code':'alice'})
    assert call(path)[0]==401
    status,_,headers=call(path,headers={'Cookie':browser_cookie})
    assert status==302 and dict(headers)['Location']=='/'
    session_cookie=next(v for k,v in headers if k=='Set-Cookie' and v.startswith('microgrid_session='))
    assert 'HttpOnly' in session_cookie
    assert call('/api/studies',headers={'Cookie':session_cookie.split(';')[0]})[0]==200
    assert call(path,headers={'Cookie':browser_cookie})[0]==401
    def fail(*args): raise RuntimeError('provider response includes very-secret-token')
    monkeypatch.setattr(auth.provider,'exchange',fail)
    _,_,headers=call('/auth/login');head=dict(headers)
    state=parse_qs(urlsplit(head['Location']).query)['state'][0]
    status,result,_=call('/auth/callback?'+urlencode({'state':state,'code':'bad'}),headers={'Cookie':head['Set-Cookie'].split(';')[0]})
    assert status==401 and 'very-secret-token' not in str(result)


def test_pkce_metadata_and_code_exchange(monkeypatch):
    config=CONFIG
    metadata={'issuer':config.issuer,'authorization_endpoint':config.issuer+'/authorize',
              'token_endpoint':config.issuer+'/token','jwks_uri':config.issuer+'/keys',
              'code_challenge_methods_supported':['S256']}
    monkeypatch.setattr('src.local_web.auth.requests.get',lambda *a,**kw: SimpleNamespace(raise_for_status=lambda:None,json=lambda:metadata))
    provider=OIDCProvider(config)
    query=parse_qs(urlsplit(provider.authorize('state','nonce','v'*43)).query)
    assert query['code_challenge_method']==['S256'] and query['code_challenge']!=['v'*43]
    assert query['scope']==['openid'] and query['nonce']==['nonce']
    assert query['redirect_uri']==[config.redirect_uri]
    metadata['issuer']='https://wrong.example'
    with pytest.raises(ValueError,match='issuer'):provider.metadata()
    metadata['issuer']=config.issuer;metadata['jwks_uri']='http://unsafe.example/keys'
    with pytest.raises(ValueError,match='HTTPS'):provider.metadata()


def test_location_weather_and_resolution_creation_are_private(service,monkeypatch):
    app,auth,call=service
    a,_=client(auth,call,'alice');b,_=client(auth,call,'bob')
    def fake_run(command,**kwargs):
        from pathlib import Path
        directory=Path(command[-1])
        request=json.loads((directory/'resource-request.json').read_text())
        if request['kind']=='location':
            write_json(directory/'resource.json',{'matches':[]})
        else:
            write_json(directory/'resource.json',{'status':'unconfirmed'})
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr('src.local_web.runtime.subprocess.run',fake_run)
    status,first,_=call('/api/location',{'query':'private address'},a)
    assert status==200
    status,second,_=call('/api/location',{'query':'private address'},b)
    assert status==200 and first['id']!=second['id'] and not second['cached']
    status,resolution,_=call('/api/v1/utility-resolution',{},a)
    assert status==200
    app.store.require_resource('resolution',resolution['resolution_id'],digest('alice'))
    with pytest.raises(FileNotFoundError):app.store.require_resource('resolution',resolution['resolution_id'],digest('bob'))


def test_failed_worker_redacts_legacy_error_file_and_log(tmp_path, monkeypatch):
    from pathlib import Path
    from src.local_web.contract import DEFAULT_REQUEST
    secret='private-weather-api-key'
    monkeypatch.setenv('NSRDB_API_KEY',secret)
    app=Application(tmp_path,embedded_worker=False)
    dataset=app.store.datasets()[0]
    app.store.grant('dataset',dataset['id'],'alice',dataset)
    request=deepcopy(DEFAULT_REQUEST);request['dataset_id']=dataset['id']
    study=app.store.submit(request,app.engine,'alice')
    def fail_process(command,**kwargs):
        directory=Path(command[-1])
        (directory/'error.json').write_text(json.dumps({'error':'Provider request contained '+secret}))
        assert kwargs['stdout'] == kwargs['stderr'] == -3  # DEVNULL: no raw logs
        return SimpleNamespace(poll=lambda:1,returncode=1)
    monkeypatch.setattr('src.local_web.runtime.subprocess.Popen',fail_process)
    runner=JobRunner(app.store)
    try:
        deadline=time.monotonic()+5
        while app.store.get(study['id'])['status'] in ('queued','running') and time.monotonic()<deadline:
            time.sleep(.05)
        result=app.store.get(study['id'],'alice')
        assert result['status']=='failed' and secret not in result['error']
        directory=tmp_path/'runs'/study['id']
        assert secret not in (directory/'error.json').read_text()
        assert secret not in (directory/'worker.log').read_text()
    finally:
        runner.close();app.close()


def test_non_secret_database_settings_do_not_corrupt_outputs(monkeypatch):
    from src.local_web.privacy import redact
    monkeypatch.setenv('MYSQL_PORT','3306')
    monkeypatch.setenv('MYSQL_HOST','localhost')
    assert redact('3306 kWh on localhost')=='3306 kWh on localhost'

def test_authenticated_queue_limits_return_retryable_status(service):
    app, auth, call = service
    app.store.max_pending = 3
    app.store.max_per_user = 2
    alice, caps = client(auth, call, 'alice')
    bob, _ = client(auth, call, 'bob')
    request = caps['defaults']
    first = call('/api/studies', request, alice)
    second = call('/api/studies', request, alice)
    assert first[0] == second[0] == 202
    status, result, headers = call('/api/studies', request, alice)
    assert status == 429 and 'active study limit' in result['error']
    assert dict(headers)['Retry-After'] == '30'
    assert call('/api/studies', request, bob)[0] == 202
    status, result, _ = call('/api/studies', request, bob)
    assert status == 429 and 'queue is full' in result['error']
    assert len(list((app.store.directory / 'runs').iterdir())) == 3
    assert len(call('/api/studies', headers=alice)[1]) == 2
    assert len(call('/api/studies', headers=bob)[1]) == 1


def test_interactive_requests_reject_overlap_and_release_slot(service, monkeypatch):
    app, auth, call = service
    alice, _ = client(auth, call, 'alice')
    entered, release = threading.Event(), threading.Event()

    def slow_lookup(request, owner_id):
        entered.set()
        assert release.wait(10)
        return {'status': 'verified'}

    monkeypatch.setattr(app, 'utilities', slow_lookup)
    first = {}

    def do_first():
        first['response'] = call('/api/utilities', {'latitude': 37.7, 'longitude': -122.4}, alice)

    thread = threading.Thread(target=do_first)
    thread.start()
    try:
        assert entered.wait(10)
        status, result, headers = call('/api/utilities', {'latitude': 37.7, 'longitude': -122.4}, alice)
        assert status == 429 and 'in progress' in result['error']
        assert dict(headers)['Retry-After'] == '30'
    finally:
        release.set()
        thread.join(10)
    assert first['response'][0] == 200
    assert call('/api/utilities', {'latitude': 37.7, 'longitude': -122.4}, alice)[0] == 200

def test_cancel_route_requires_owner_and_csrf(service):
    app, auth, call = service
    alice, caps = client(auth, call, 'alice')
    bob, _ = client(auth, call, 'bob')
    study = call('/api/studies', caps['defaults'], alice)[1]
    path = '/api/studies/' + study['id'] + '/cancel'
    assert call(path, {})[0] == 401
    assert call(path, {}, bob)[0] == 404
    assert call(path, {}, {'Cookie': alice['Cookie']})[0] == 403
    assert call(path, {'reason': 'other'}, alice)[0] == 400
    status, cancelled, _ = call(path, {}, alice)
    assert status == 200 and cancelled['status'] == 'cancelled'
    assert call('/api/studies/' + study['id'], headers=bob)[0] == 404
    assert call(path, {}, alice)[0] == 409


def test_running_cancel_stops_simulation_subprocess(service, monkeypatch):
    import sys
    import src.local_web.runtime as runtime

    app, auth, call = service
    alice, caps = client(auth, call, 'alice')
    bob, _ = client(auth, call, 'bob')
    study = call('/api/studies', caps['defaults'], alice)[1]
    real_popen = runtime.subprocess.Popen
    processes = []

    def record_popen(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(runtime, 'command',
                        lambda *_: [sys.executable, '-c', 'import time; time.sleep(60)'])
    monkeypatch.setattr(runtime.subprocess, 'Popen', record_popen)
    runner = JobRunner(app.store)
    try:
        deadline = time.monotonic() + 15
        while (not processes or app.store.get(study['id'])['status'] != 'running') and time.monotonic() < deadline:
            time.sleep(.05)
        assert processes and processes[0].poll() is None
        path = '/api/studies/' + study['id'] + '/cancel'
        assert call(path, {}, bob)[0] == 404
        status, result, _ = call(path, {}, alice)
        assert status == 202 and result['status'] in ('cancelling', 'cancelled')
        deadline = time.monotonic() + 15
        while app.store.get(study['id'])['status'] != 'cancelled' and time.monotonic() < deadline:
            time.sleep(.05)
        cancelled = app.store.get(study['id'])
        assert cancelled['status'] == 'cancelled'
        assert cancelled['started_at'] is not None
        assert cancelled['runtime_seconds'] is not None and cancelled['runtime_seconds'] > 0
        assert call('/api/usage', headers=alice)[1]['used_seconds'] > 0
        assert processes[0].poll() is not None
        assert call('/api/studies/' + study['id'] + '/result.json', headers=alice)[0] == 400
        assert call('/api/studies/' + study['id'], headers=bob)[0] == 404
    finally:
        runner.close()


def test_daily_usage_is_private_and_submission_limit_is_enforced(service):
    app, auth, call = service
    app.store.daily_study_limit = 1
    alice, caps = client(auth, call, 'alice')
    bob, _ = client(auth, call, 'bob')
    assert call('/api/usage')[0] == 401
    assert call('/api/usage', headers=alice)[1]['submitted_studies'] == 0
    assert call('/api/studies', caps['defaults'], alice)[0] == 202
    status, usage, _ = call('/api/usage', headers=alice)
    assert status == 200 and usage['submitted_studies'] == 1
    assert usage['remaining_studies'] == 0
    assert call('/api/usage', headers=bob)[1]['submitted_studies'] == 0
    status, error, headers = call('/api/studies', caps['defaults'], alice)
    assert status == 429 and 'study limit' in error['error']
    assert int(dict(headers)['Retry-After']) > 0
    assert call('/api/studies', caps['defaults'], bob)[0] == 202


def test_csv_upload_quota_returns_private_error_without_retry_hint(service):
    app, auth, call = service
    alice, _ = client(auth, call, 'alice')
    app.store.max_owner_dataset_bytes = sum(dataset['size_bytes'] for dataset in app.store.datasets(digest('alice')))
    original_count = len(app.store.datasets(digest('alice')))
    sample = (ROOT / 'data/default_small_business_week.csv').read_bytes()
    changed = sample.replace(b'12.714', b'12.715', 1)
    status, error, headers = call('/api/datasets', {'name': 'new.csv', 'csv': changed.decode()}, alice)
    assert status == 429 and 'saved CSV upload quota' in error['error']
    assert 'Retry-After' not in dict(headers)
    assert len(app.store.datasets(digest('alice'))) == original_count


def test_weather_over_storage_limit_is_removed_and_not_granted(service, monkeypatch):
    import src.local_web.runtime as runtime
    app, auth, call = service
    alice, _ = client(auth, call, 'alice')
    app.store.max_weather_bytes = 300
    monkeypatch.setenv('NSRDB_API_KEY', 'benchmark-only')
    monkeypatch.setenv('NSRDB_API_EMAIL', 'benchmark@example.invalid')

    def fake_resource(command, **kwargs):
        directory = Path(command[-1])
        (directory / 'weather.csv').write_bytes(b'x' * 512)
        write_json(directory / 'resource.json', {'sha256': 'a' * 64})
        return SimpleNamespace(returncode=0)

    from pathlib import Path
    monkeypatch.setattr(runtime.subprocess, 'run', fake_resource)
    request = {'latitude': 37.7749, 'longitude': -122.4194, 'year': 2025,
               'timezone': 'America/Los_Angeles', 'timestep_minutes': 15}
    status, error, headers = call('/api/weather', request, alice)
    assert status == 429 and 'per-resource storage limit' in error['error']
    assert 'Retry-After' not in dict(headers)
    assert list((app.store.directory / 'weather').iterdir()) == []


def test_worker_stops_oversize_run_and_discards_partial_results(service, monkeypatch):
    import sys
    import src.local_web.runtime as runtime
    app, auth, call = service
    alice, caps = client(auth, call, 'alice')
    app.store.max_run_bytes = 100000
    monkeypatch.setattr(runtime, 'command', lambda *_: [
        sys.executable, '-c', "from pathlib import Path; import time; Path('over.bin').write_bytes(b'x'*200000); time.sleep(60)"])
    study = call('/api/studies', caps['defaults'], alice)[1]
    runner = JobRunner(app.store)
    try:
        deadline = time.monotonic() + 15
        while app.store.get(study['id'])['status'] not in ('failed', 'completed') and time.monotonic() < deadline:
            time.sleep(.05)
        result = app.store.get(study['id'])
        assert result['status'] == 'failed'
        assert 'storage limit' in result['error']
        directory = app.store.directory / 'runs' / study['id']
        assert (directory / 'request.json').is_file()
        assert not (directory / 'over.bin').exists()
        assert app.store.directory_bytes(directory) < app.store.max_run_bytes
    finally:
        runner.close()


def test_orientation_time_is_metered_without_daily_time_limit(service, monkeypatch):
    app, auth, call = service
    alice, caps = client(auth, call, 'alice')
    bob, _ = client(auth, call, 'bob')

    def fake_candidate(kind, request, owner):
        assert kind == 'orientation'
        time.sleep(.02)
        return {'tilt_degrees': 20, 'azimuth_degrees': 180}

    monkeypatch.setattr(app, '_candidate', fake_candidate)
    assert call('/api/solar/optimize', {}, alice)[0] == 200
    first_used = call('/api/usage', headers=alice)[1]['used_seconds']
    assert first_used > 0

    def failed_candidate(*args):
        time.sleep(.02)
        raise ValueError('Candidate calculation failed.')

    monkeypatch.setattr(app, '_candidate', failed_candidate)
    assert call('/api/solar/optimize', {}, alice)[0] == 400
    assert call('/api/usage', headers=alice)[1]['used_seconds'] > first_used
    event = app.store.start_orientation(digest('alice'))
    app.store.finish_orientation(event, 1.1)
    monkeypatch.setattr(app, '_candidate', fake_candidate)
    assert call('/api/solar/optimize', {}, alice)[0] == 200
    assert call('/api/studies', caps['defaults'], alice)[0] == 202
    assert call('/api/solar/optimize', {}, bob)[0] == 200
