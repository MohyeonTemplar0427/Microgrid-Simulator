"""Main form builder -> immutable queue/worker -> replay, save and downloads."""
import json
import subprocess
from pathlib import Path
import pandas as pd
import pytest
from urllib.error import HTTPError
from test_comed_dispatch import request
from test_local_web import service, wait_for_study
from test_local_web_hosting import hosted, signin


def browser_request(r):
    a=r['account'];v={**r['solar'],**r['battery'],**r['site'],
      'site_profile':r['site_profile'],'site_label':r['site']['label'],'start_date':r['start_date'],
      'end_date':r['end_date'],'timestep_minutes':r['timestep_minutes'],'pv_capacity_kw':r['pv_capacity_kw'],
      'weather_source':'clear_sky','weather_id':None,'pv_choice':'yes','ess':None,
      'tariff_id':'comed_'+a['supply'],'ce_class':a['delivery_class'],
      'ce_verification':'hypothetical_case','ce_reference':r['regional_account']['reference'],
      'ce_account_confirmed':True,'ce_voltage':a.get('service_voltage','secondary'),
      'ce_transformer':'yes','ce_competitive':'no','ce_heat':'no',
      **{'ce_'+k:a.get(k,40) for k in ['previous_12_month_peak_kw','previous_calendar_year_peak_kw','previous_year_months_ge_100kw']},
      'load_mode':'constant','load_power_kw':r['load']['power_kw'],'archetype':r['load']['archetype'],
      'ce_load_source':r['load']['source'],'ce_native_confirmed':False,
      'ce_include_battery':True,'ce_nonexport':True,'ce_standard':True,'ce_grid_charge':True,
      'ce_operation_reference':r['operating_contract']['reference'],'degradation_cost_per_kWh':.03,
      'include_degradation_in_optimization':False}
    if r['prices']:
      v.update(ce_price_mode='constant_example',ce_price=50,ce_price_source=r['prices']['source'],
               ce_price_confirmed=True,ce_capacity=a['capacity_obligation_kw'],ce_capacity_source=a['capacity_source'])
    if r.get('billing_cycles'):
      v.update(ce_cycle_mode='meter_cycles',ce_cycles_json=json.dumps(r['billing_cycles']))
    js="const {buildComedSimulationRequest}=require('./src/local_web/static/comed_simulation.js');const fs=require('fs');const x=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(buildComedSimulationRequest(x.base,x.values)));"
    return json.loads(subprocess.run(['node','-e',js],input=json.dumps({'base':r,'values':v}),
                     text=True,capture_output=True,check=True).stdout)


@pytest.mark.parametrize('kind',['residential','commercial'])
@pytest.mark.parametrize('supply',['BES','BESH'])
def test_main_builder_through_worker_comparison_save_and_download(service,kind,supply):
    app,call,headers=service;r=browser_request(request(kind,supply))
    caps=call('/api/capabilities');assert caps['comed_simulation']['schema_version']==10
    assert b'comed_simulation.js' in call('/')
    study=call('/api/v1/comed/simulations',r,headers)
    out=wait_for_study(call,study['id']);assert out['status']=='completed',out.get('error')
    result=out['result'];assert result['engine_id']==app.engine['id']
    assert result['total_usd'] is None and result['is_complete_bill'] is False
    assert result['ac_validation']['all_intervals_feasible']
    table=call('/api/studies/'+study['id']+'/tables/comparison')
    data=[dict(zip(table['columns'],row)) for row in table['data']]
    assert len(data)==3 and {x['scenario'] for x in data}=={'grid_only','pv_only','pv_battery'}
    assert all(x['total_usd'] is None and x['is_complete_bill'] is False for x in data)
    assert len({x['capacity_obligation_kw'] for x in data})==1
    assert all(abs(x['rounding_difference_usd'])<=x['rounding_bound_usd'] for x in data)
    assert data[2]['subtotal_usd']<=data[1]['subtotal_usd']+.1
    base='/api/studies/'+study['id']
    assert b'pv_curtailed_kw' in call(base+'/tables/dispatch-pv_battery.csv')
    assert b'timestamp' in call(base+'/tables/inputs.csv')
    assert len(call(base+'/tables.zip'))>0
    call(base+'/save',{'name':'ComEd '+kind+' '+supply+' reference'},headers)
    assert call(base)['saved'] and call(base)['request']['schema_version']==10
    capability=app.capabilities.pop('comed_simulation')
    try:
      with pytest.raises(HTTPError):call('/api/v1/comed/simulations',r,headers)
    finally:app.capabilities['comed_simulation']=capability


def test_native_profile_and_no_storage_replay_without_fake_device(tmp_path):
    from src.local_web.comed_simulation import prepare,execute
    r=request();r['battery']=None;r['solar']['dc_capacity_kw']=0;r['pv_capacity_kw']=0
    grid,load,_,_=prepare(r)
    r['load'].update(mode='csv',power_kw=None,archetype=None,native_basis_confirmed=True,
        csv=pd.DataFrame({'timestamp':grid.index,'native_load_kw':load}).to_csv(index=False))
    (tmp_path/'engine.json').write_text(json.dumps({'id':'direct-test'}))
    execute(tmp_path,r)
    result=json.loads((tmp_path/'result.json').read_text())
    assert result['ac_validation']['all_intervals_feasible']
    comparison=pd.read_csv(tmp_path/'comparison.csv');assert comparison.subtotal_usd.nunique()==1
    assert comparison.terminal_energy_kwh.eq(0).all()


def test_secondary_solver_failure_is_visible_in_shared_saved_results(monkeypatch,tmp_path):
    import cvxpy as cp
    from src.local_web.comed_simulation import execute
    original=cp.Problem.solve;storage_solves=0
    def solve(problem,*args,**kwargs):
        nonlocal storage_solves
        # The energy-state vector identifies storage even when nonnegative
        # prices permit an equivalent continuous formulation.
        if any(v.shape == (1441,) for v in problem.variables()):
            storage_solves+=1
            if storage_solves==2:raise cp.error.SolverError('Synthetic cycling tie-break failure')
        return original(problem,*args,**kwargs)
    monkeypatch.setattr(cp.Problem,'solve',solve)
    (tmp_path/'engine.json').write_text(json.dumps({'id':'direct-test'}))
    execute(tmp_path,request())
    result=json.loads((tmp_path/'result.json').read_text())
    status=result['optimization']['pv_battery']
    assert status['cost_optimum_proven'] and status['throughput_tie_break_status']=='solver_error'
    assert any('pv_battery' in w and 'cycling tie-break' in w for w in result['warnings'])
    comparison=pd.read_csv(tmp_path/'comparison.csv').set_index('scenario')
    assert comparison.loc['pv_battery','cost_optimum_proven']
    assert comparison.loc['pv_battery','throughput_tie_break_status']=='solver_error'
    assert result['ac_validation']['all_intervals_feasible']


def test_hosted_simulation_cannot_expose_private_inputs(hosted):
    app,auth,call,_=hosted;headers,caps=signin(call,'comed-model-reviewer');r=request()
    assert call('/api/v1/comed/simulations',r,headers)[0]==400
    from src.local_web.auth import digest
    job=app.store.submit(r,app.engine,digest('comed-model-reviewer'))
    for suffix in ('','/request.json','/result.json','/tables.zip'):
      assert call('/api/studies/'+job['id']+suffix,headers=headers)[0]==403


@pytest.mark.parametrize('kind',['residential','commercial'])
@pytest.mark.parametrize('supply',['BES','BESH'])
def test_documented_cycle_from_production_form_through_worker(service,kind,supply):
    app,call,headers=service;r=request(kind,supply)
    r.update(start_date='2026-09-15',end_date='2026-10-14',billing_cycles=[{
      'start_date':'2026-09-15','end_date':'2026-10-14','billing_month':'2026-10-01',
      'kind':'regular','source':'Explicit hypothetical October meter cycle','charge_factors':None}])
    r['account']['billing_month']='2026-10-01'
    r=browser_request(r)
    assert r['billing_cycles'][0]['billing_month']=='2026-10-01'
    study=call('/api/v1/comed/simulations',r,headers)
    out=wait_for_study(call,study['id']);assert out['status']=='completed',out.get('error')
    for bill in out['result']['billing'].values():
      assert bill['cycles'][0]['billing_cycle']['billing_days']==30
      assert bill['cycles'][0]['version_id'].endswith('_2026_10')
      assert len([x for x in bill['lines'] if x['name']=='customer'])==1
    assert out['result']['ac_validation']['all_intervals_feasible']
    assert call('/api/studies/'+study['id'])['request']['billing_cycles']==r['billing_cycles']


@pytest.mark.parametrize('kind,supply,start,end',[
    ('residential','BESH','2026-08-01','2026-08-31'),
    ('commercial','BES','2025-11-01','2025-11-30'),
])
def test_historical_form_to_pinned_worker_preserves_rates_and_dst(service,kind,supply,start,end):
    app,call,headers=service;r=request(kind,supply)
    r.update(start_date=start,end_date=end)
    r['account']['billing_month']=start
    r=browser_request(r)
    caps=call('/api/capabilities')['comed_simulation']['billing_months_by_supply']
    assert start in caps[supply]
    study=call('/api/v1/comed/simulations',r,headers)
    out=wait_for_study(call,study['id']);assert out['status']=='completed',out.get('error')
    result=out['result'];assert result['engine_id']==app.engine['id']
    assert result['ac_validation']['all_intervals_feasible']
    grid_bill=result['billing']['grid_only']
    assert grid_bill['version_id']==f"comed_{kind}_{start[:4]}_{start[5:7]}"
    rates={line['name']:line['rate_usd'] for line in grid_bill['lines']}
    if start[:4]=='2025':
        assert grid_bill['import_kwh']==721*20  # one extra physical fall-back hour
        assert 'low_income_discount_recovery' not in rates
        assert rates['distribution_demand']==13.90
    else:
        assert rates['purchased_electricity_adjustment']==-.00376
        assert rates['environmental_cost_recovery']==.00007
    table=call('/api/studies/'+study['id']+'/tables/comparison')
    rows=[dict(zip(table['columns'],row)) for row in table['data']]
    assert all(abs(row['rounding_difference_usd'])<=row['rounding_bound_usd'] for row in rows)
    assert call('/api/studies/'+study['id'])['request']==r


@pytest.mark.parametrize('kind,supply,start,end,cfra,hpea',[
    ('residential','BES','2025-03-01','2025-03-31',.00803,None),
    ('commercial','BESH','2025-05-01','2025-05-31',-.00522,.02664),
    ('residential','BESH','2025-11-01','2025-11-30',-.00847,-.04214),
])
def test_newly_verified_history_from_form_through_worker(service,kind,supply,start,end,cfra,hpea):
    app,call,headers=service;r=request(kind,supply)
    r.update(start_date=start,end_date=end);r['account']['billing_month']=start
    r=browser_request(r)
    study=call('/api/v1/comed/simulations',r,headers)
    out=wait_for_study(call,study['id']);assert out['status']=='completed',out.get('error')
    result=out['result'];assert result['engine_id']==app.engine['id']
    assert result['ac_validation']['all_intervals_feasible']
    b=result['billing']['grid_only'];rates={x['name']:x['rate_usd'] for x in b['lines']}
    assert rates['carbon_free_resource_adjustment']==cfra
    if hpea is not None:
        assert rates['purchased_electricity_adjustment']==hpea
        assert rates['capacity']==(.91048 if start[5:7]=='05' else 8.31935)
    if start[5:7]=='03':assert b['import_kwh']==743
    table=call('/api/studies/'+study['id']+'/tables/comparison')
    rows=[dict(zip(table['columns'],row)) for row in table['data']]
    assert all(abs(x['rounding_difference_usd'])<=x['rounding_bound_usd'] for x in rows)
    assert call('/api/studies/'+study['id'])['request']==r


@pytest.mark.parametrize('kind,supply,start,end,month,cfra,lid',[
    ('residential','BES','2026-03-01','2026-03-31','2026-03-01',-.04110,1.22),
    ('commercial','BESH','2026-05-01','2026-05-31','2026-05-01',-.06414,13.50),
    ('commercial','BES','2026-03-15','2026-04-14','2026-04-01',-.03186,13.50),
])
def test_early_2026_form_to_worker_preserves_monthly_factors_and_cycles(service,kind,supply,start,end,month,cfra,lid):
    app,call,headers=service;r=request(kind,supply)
    r.update(start_date=start,end_date=end);r['account']['billing_month']=month
    cross=start!=month
    if cross:r['billing_cycles']=[dict(start_date=start,end_date=end,billing_month=month,
        kind='regular',source='Hypothetical April-designated utility meter cycle',charge_factors=None)]
    r=browser_request(r);study=call('/api/v1/comed/simulations',r,headers)
    out=wait_for_study(call,study['id']);assert out['status']=='completed',out.get('error')
    result=out['result'];assert result['engine_id']==app.engine['id']
    assert result['ac_validation']['all_intervals_feasible']
    for b in result['billing'].values():
        if cross:b=b['cycles'][0]
        rates={x['name']:x['rate_usd'] for x in b['lines']}
        assert rates['carbon_free_resource_adjustment']==cfra
        assert rates['low_income_discount_recovery']==lid
        if kind=='commercial':assert rates['distribution_demand']==12.93
        else:assert rates['distribution_facilities']==.06228
        if supply=='BESH':assert rates['capacity']==8.32925
    table=call('/api/studies/'+study['id']+'/tables/comparison')
    rows=[dict(zip(table['columns'],row)) for row in table['data']]
    assert all(abs(x['rounding_difference_usd'])<=x['rounding_bound_usd'] for x in rows)
    assert call('/api/studies/'+study['id'])['request']==r
