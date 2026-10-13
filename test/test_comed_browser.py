"""ComEd browser request, actual pinned worker and saved-table integration."""
import json
from urllib.error import HTTPError
import pandas as pd
import pytest
from src.local_web.comed_study import defaults, prepare
from src.local_web.contract import validate_request
from test_local_web import service, wait_for_study


def request(kind='residential',supply='BES'):
    r=defaults(kind);r['account']['ordinary_import_only_confirmed']=True
    r['account']['supply']=supply
    if supply=='BESH':
        r['account'].update(capacity_obligation_kw=2.,capacity_source='Synthetic obligation')
        r['prices']=dict(mode='constant_example',usd_per_mwh=50.,csv=None,
            source='Synthetic ComEd residual LMP',basis_confirmed=True)
    return r


@pytest.mark.parametrize('kind',['residential','commercial'])
@pytest.mark.parametrize('supply',['BES','BESH'])
def test_contract_csv_and_example_energy_parity(kind,supply):
    r=request(kind,supply);g,expected=prepare(r)
    csv=pd.DataFrame({'timestamp':g.index,'grid_import_kw':g.values}).to_csv(index=False)
    r['load'].update(mode='csv',kw=None,csv=csv)
    assert prepare(validate_request(r))[1]==expected


@pytest.mark.parametrize('change',['unconfirmed','unknown_month','missing_capacity','wrong_basis','naive_csv','missing_csv_row','negative_import','extra_field'])
def test_browser_input_rejections(change):
    r=request('commercial','BESH')
    if change=='unconfirmed':r['account']['ordinary_import_only_confirmed']=False
    if change=='unknown_month':r['account']['billing_month']='2026-11-01'
    if change=='missing_capacity':r['account']['capacity_obligation_kw']=None
    if change=='wrong_basis':r['prices']['basis_confirmed']=False
    if change=='negative_import':r['load']['kw']=-1
    if change=='extra_field':r['guess_missing_rates']=True
    if change in ('naive_csv','missing_csv_row'):
        g,_=prepare(r)
        if change=='naive_csv':g.index=g.index.tz_localize(None)
        else:g=g.iloc[1:]
        r['load'].update(mode='csv',kw=None,csv=pd.DataFrame({'timestamp':g.index,'grid_import_kw':g}).to_csv(index=False))
    with pytest.raises(ValueError):validate_request(r)


def test_http_to_pinned_worker_results_downloads_and_save(service):
    app,call,headers=service
    assert set(call('/api/capabilities')['comed']['defaults'])=={'residential','commercial'}
    assert b'/comed.html' in call('/')
    assert b'customer_type' in call('/comed.html')
    assert b'buildComedRequest' in call('/comed.js')
    for kind,subtotal in [('residential',137.45),('commercial',1811.04)]:
        r=request(kind)
        study=call('/api/v1/comed/studies',r,headers)
        finished=wait_for_study(call,study['id'])
        assert finished['status']=='completed',finished.get('error')
        result=finished['result']
        assert result['engine']['id']==app.engine['id']
        assert result['bill']['subtotal_usd']==subtotal
        assert result['bill']['total_usd'] is None
        base='/api/studies/'+study['id']
        table=call(base+'/tables/comparison')
        assert table['data'][0][table['columns'].index('subtotal_usd')]==subtotal
        assert b'distribution_' in call(base+'/tables/billing-components.csv')
        assert call(base+'/request.json')==r
        saved=call(base+'/save',{'name':'Verified '+kind+' synthetic bill'},headers)
        assert call(base)['saved']
    with pytest.raises(HTTPError):call('/api/studies',request(),headers)
    with pytest.raises(HTTPError):call('/api/v1/comed/studies',request(),{'Content-Type':'application/json'})
    app.capabilities.pop('comed')
    with pytest.raises(HTTPError) as error:call('/api/v1/comed/studies',request(),headers)
    assert b'pinned engine' in error.value.read()
