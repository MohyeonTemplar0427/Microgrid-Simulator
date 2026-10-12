"""Production browser builder, ownership-checked API and pinned worker coverage."""
import json
from copy import deepcopy
import pytest

from src.local_web.runtime import JobRunner
from src.local_web.socal_study import validate, capabilities, billing_account
from test_local_web_pipeline import api_service, until
from test_socal_form_pipeline import browser_payload
from test_socal import study_request
from test_san_diego import account, BATTERY


def request(provider='bundled'):
    r=deepcopy(study_request('sce'))
    r.update(tariff_id='sdge_tou-dr1',mode='actual_service',account=account(provider),
             start_date='2026-08-06',end_date='2026-08-06',battery=None,
             solar=dict(capacity_kw=0.,tilt=20.,azimuth=180.))
    r['resolution'].update(status='verified',delivery_utility='sdge',delivery_candidates=[{'utility_id':'sdge'}],coordinates={'latitude':32.64,'longitude':-117.09})
    return r


@pytest.mark.parametrize('provider,plan', [('bundled','sdge_tou-dr1'),('sdcp','sdge_tou-dr2'),('cea','sdge_ev-tou-5')])
def test_browser_form_api_worker_bills_and_storage(tmp_path,provider,plan):
    resolution=request(provider)['resolution'];resolution_id='d'*32
    source=tmp_path/'candidate'/resolution_id;source.mkdir(parents=True)
    (source/'resource-request.json').write_text(json.dumps({'kind':'utility-resolution'}))
    (source/'resource.json').write_text(json.dumps(resolution))
    with api_service(tmp_path) as (app, call):
        caps=call('/api/capabilities')[1]
        assert caps['service_classes']['sdge']==['residential']
        assert set(caps['socal']['san_diego_generation'])=={'bundled','sdcp','cea'}
        values=dict(utility='sdge',pv_choice='storage',sc_tariff_id=plan,
            sc_generation=provider,sc_mode='actual_service',sc_solar_program='none',
            sc_sdge_city_san_diego='no',sc_sdge_baseline_kwh='9',sc_sdge_pcia_vintage='2021',
            sc_sdge_sdcp_cohort='2022',sc_sdge_generation_option={'bundled':'','sdcp':'power100','cea':'greenimpact'}[provider],
            sc_month_factor='') # Hidden for SDG&E; BSC uses actual days.
        values.update({k:str(v) for k,v in BATTERY.items()})
        checks={f'sc_{k}':True for k in ['sdge_jurisdiction_confirmed','sdge_non_event_confirmed',
            'sdge_baseline_confirmed','sdge_allocation_confirmed','sdge_pcia_confirmed',
            'sdge_generation_confirmed','sdge_ev_confirmed','sdge_storage_confirmed']}
        payload=browser_payload(caps,resolution_id,'none','2026-08-06',value_overrides=values,check_overrides=checks)
        assert payload['battery']==BATTERY
        assert payload['solar']['capacity_kw']==0
        assert payload['account']['sdge_city_san_diego'] is False
        assert payload['account']['actual_generation_provider']==provider
        code,job=call('/api/v1/socal/studies',payload,caps['token'])
        assert code==202,job
        runner=JobRunner(app.store)
        try:
            saved=until(lambda:call('/api/studies/'+job['id'])[1],lambda v:v['status'] in ('completed','failed'))
            assert saved['status']=='completed',saved.get('error')
            assert saved['request']['account']==payload['account']
            table=call('/api/studies/'+job['id']+'/tables/comparison')[1]
            rows=[dict(zip(table['columns'],r)) for r in table['data']]
            assert {r['scenario'] for r in rows}=={'grid_only','battery_storage'}
            costs={r['scenario']:r['utility_bill'] for r in rows}
            assert costs['battery_storage']<costs['grid_only']
            table=call('/api/studies/'+job['id']+'/tables/rate_versions')[1]
            assert table['total']>= (2 if provider=='bundled' else 4)
        finally:
            runner.close()


def test_hypothetical_bundled_keeps_actual_provider_evidence_but_prices_sdge():
    r=request('sdcp');r['mode']='hypothetical_bundled'
    assert billing_account(r)['actual_generation_provider']=='bundled'
    assert validate(r)['account']['actual_generation_provider']=='sdcp'


@pytest.mark.parametrize('change',[{'mode':'actual_service','resolution':{'status':'approximate','delivery_utility':'sdge'}},
                                  {'site_profile':{'site_type':'commercial','subtype':None}},
                                  {'battery':BATTERY,'account':account(sdge_storage_confirmed=False)}])
def test_account_and_site_checks_run_before_enqueue(change):
    r=request();r.update(change)
    with pytest.raises(ValueError):validate(r)


@pytest.mark.parametrize('oid,identity',[(10,'cea'),(25,'sdcp')])
def test_sdge_mapping_and_cca_identity_retains_ambiguity(oid,identity):
    from src.local_web.utility_resolution import resolve_service,CCA_IDENTITIES
    from test_municipal import feature,geo_get,Response
    base=geo_get([feature(80402,'San Diego Gas & Electric',oid=5)])
    def get(url,params,timeout):
        if 'Other' in url:
            if not url.endswith('/query'):return Response({'serviceItemId':'cca-snapshot','editingInfo':{'dataLastEditDate':1234}})
            return Response({'features':[{'attributes':{'OBJECTID':oid,'Utility':next(iter(CCA_IDENTITIES[oid][1])),'Type':'CCA'}}]})
        return base(url,params,timeout)
    r=resolve_service(dict(latitude=32.64,longitude=-117.09),get=get)
    assert r['status']=='approximate' and r['delivery_utility']=='sdge'
    assert r['generation_candidates'][0]['service_id']==identity
    assert r['sources'][-1]['role']=='generation suggestions; not enrollment'
    assert 'actual_generation_provider' not in r
    overlap=geo_get([feature(80402,oid=5)],[feature(80402,oid=5),feature(86250,oid=3)])
    r=resolve_service(dict(latitude=33.45,longitude=-117.6),get=overlap)
    assert r['status']=='ambiguous' and r['delivery_utility'] is None


def test_source_data_rebuild_is_reproducible():
    from tools.build_san_diego_rates import build
    from src.billing.san_diego_data import SDGE,SDCP,CEA
    assert build()==dict(SDGE=SDGE,SDCP=SDCP,CEA=CEA)


def test_grid_only_form_does_not_reuse_stale_battery_selection():
    payload=browser_payload({'socal':capabilities()},'e'*32,'none','2026-08-06',
        value_overrides=dict(utility='sdge',pv_choice='no',sc_tariff_id='sdge_tou-dr1',
            sc_generation='bundled',sc_sdge_city_san_diego='no',sc_sdge_baseline_kwh='9'),
        check_overrides={'sc_include_battery':True})
    assert payload['battery'] is None
    assert payload['solar']['capacity_kw']==0
