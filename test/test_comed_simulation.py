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


def test_hosted_simulation_cannot_expose_private_inputs(hosted):
    app,auth,call,_=hosted;headers,caps=signin(call,'comed-model-reviewer');r=request()
    assert call('/api/v1/comed/simulations',r,headers)[0]==400
    from src.local_web.auth import digest
    job=app.store.submit(r,app.engine,digest('comed-model-reviewer'))
    for suffix in ('','/request.json','/result.json','/tables.zip'):
      assert call('/api/studies/'+job['id']+suffix,headers=headers)[0]==403
