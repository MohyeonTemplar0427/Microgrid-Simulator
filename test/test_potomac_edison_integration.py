"""Targeted Potomac Edison form, isolated-worker and evidence contracts."""
from copy import deepcopy
from io import BytesIO
import json
from zipfile import ZipFile
import numpy as np
import pytest
from src.billing.regional import calculate_cycle,cycle_account,account_region
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.billing.potomac_edison_md import hypothetical_history,excluded_components
from src.local_web.regional_study import defaults,prepare,calendar_cycles,capabilities
from tools.run_regional_validation import case_request,checked_bill_scope,selected_cases
from test_regional_study import browser_request
from test_local_web import service,wait_for_study

CASES=(("residential","R"),("commercial","G"))


def request_for(kind,plan,start="2026-09-01",end="2026-09-30"):
    r=defaults("potomac_edison_maryland",kind,plan)
    r.update(start_date=start,end_date=end,billing_cycles=calendar_cycles(start,end))
    if plan=="G":r['account']['history']=hypothetical_history(start[:7]+'-01')
    r['operating_contract'].update(interconnection_confirmed=True,grid_charging_confirmed=True,reference="Explicit hypothetical approved ordinary non-export PV/storage account")
    return r


@pytest.mark.parametrize('kind,plan',CASES)
@pytest.mark.parametrize('month,end,intervals',[('2026-09-01','2026-09-30',2880),('2026-10-01','2026-10-31',2976)])
def test_form_roundtrip_region_history_and_recovered_windows(kind,plan,month,end,intervals):
    entry=capabilities()['utilities']['potomac_edison_maryland']
    assert (entry['state'],entry['grid_operator'],entry['transmission_zone'])==('MD','PJM','APS')
    assert ('potomac_edison_maryland',kind,plan) in selected_cases(['potomac_edison_maryland'])
    r=case_request('potomac_edison_maryland',kind,'custom',plan=plan,start_date=month,end_date=end)
    restored=browser_request(r);assert restored['account']==r['account'] and restored['billing_cycles']==r['billing_cycles']
    account_region(restored['regional_account'],'potomac_edison_maryland')
    grid,load,cycles,_=prepare(restored);assert len(grid.index)==len(load)==intervals and len(cycles)==1
    reference=grid_only_counterfactual('potomac_edison_maryland',r['account'])
    assert reference['account']['der_ordinary_service_confirmed'] is False
    for key in ('history','history_source','demand_method','unmetered_source','usc_assignment_2026_source'):
        assert reference['account'][key]==r['account'][key]
    for key,value in [('state_jurisdiction','WV'),('retail_supplier','competitive_supplier'),('transmission_zone','DPL')]:
        bad=deepcopy(restored);bad['regional_account'][key]=value
        with pytest.raises(ValueError):prepare(bad)


@pytest.mark.parametrize('kind,plan',CASES)
def test_main_form_worker_component_scope_saved_settings_csv_zip_electrical(service,kind,plan):
    app,call,headers=service;r=browser_request(request_for(kind,plan));prepare(r)
    queued=call('/api/v1/regional/studies',r,headers);study=wait_for_study(call,queued['id'])
    assert study['status']=='completed',study.get('error')
    result=study['result'];assert result['engine_id']==app.engine['id']
    assert result['is_complete_bill'] is (plan=='R')
    for scenario,bills in result['billing'].items():
        assert len(bills)==1;b=bills[0]
        assert b['excluded_components']==excluded_components(plan) and b['export_kwh']<1e-5
        assert b['is_complete_bill'] is (plan=='R') and b['rate_evidence_status']=='verified'
        assert b['total_usd']==pytest.approx(sum(b['lines'].values()))
        if plan=='G':
            assert b['metrics']['distribution_minimum_inactive_verified'] is True
            assert b['next_state']['history'][-1]['import_kwh']==pytest.approx(b['import_kwh'])
        assert result['optimization'][scenario]['annual_optimum_proven'] is None
    assert result['ac_validation']['all_intervals_feasible']
    assert all(x['checked_intervals']==2880 and x['failed_intervals']==0 for x in result['ac_validation']['scenarios'])
    base='/api/studies/'+queued['id']
    with ZipFile(BytesIO(call(base+'/tables.zip'))) as archive:
        assert archive.testzip() is None and json.loads(archive.read('result-manifest.json'))==result
        assert all('ac-'+s+'.csv' in archive.namelist() for s in result['billing'])
    call(base+'/save',{'name':'Potomac Edison '+plan+' targeted acceptance'},headers)
    saved=call(base+'/request.json');assert saved['account']==r['account'] and saved['regional_account']==r['regional_account']
    assert browser_request(saved)['account']==r['account']


@pytest.mark.parametrize('kind,plan',CASES)
def test_matrix_audit_prevents_scope_promotion_and_hidden_exclusions(kind,plan):
    r=case_request('potomac_edison_maryland',kind,'monthly',plan=plan);grid,load,cycles,equipment=prepare(r)
    _,block,cycle=cycles[0];a=cycle_account(r['account'],cycle)
    bill=calculate_cycle('potomac_edison_maryland',grid.index[block],load[block],np.zeros(len(load[block])),a,equipment=equipment)
    assert checked_bill_scope(bill,'potomac_edison_maryland',a,grid.index[block])==('complete_utility_bill' if plan=='R' else 'verified_charges_subtotal',sorted(excluded_components(plan)))
    mutations=[('is_complete_bill',plan!='R'),('rate_evidence_status','provisional'),('excluded_components',['hidden'] if plan=='R' else [])]
    for key,value in mutations:
        bad=deepcopy(bill);bad[key]=value
        with pytest.raises(AssertionError):checked_bill_scope(bad,'potomac_edison_maryland',a,grid.index[block])
    if plan=='G':
        for key,value in [('distribution_minimum_inactive_verified',False),('minimum_capacity_conservative_upper_kw',8.),('transmission_minimum_capacity_status','zero')]:
            bad=deepcopy(bill);bad['metrics'][key]=value
            with pytest.raises(AssertionError):checked_bill_scope(bad,'potomac_edison_maryland',a,grid.index[block])


@pytest.mark.parametrize('kind,plan',CASES)
def test_history_gaps_full_years_and_unverified_rate_months_fail(kind,plan):
    with pytest.raises(ValueError,match='full-year2025'):case_request('potomac_edison_maryland',kind,'annual',plan=plan)
    for start,end in [('2025-01-01','2025-12-31'),('2026-06-01','2026-06-30'),('2026-08-01','2026-08-31'),('2026-11-01','2026-11-30'),('2026-09-02','2026-09-30')]:
        with pytest.raises(ValueError):prepare(request_for(kind,plan,start,end))
    if plan=='G':
        r=request_for(kind,plan);r['account']['history']=hypothetical_history('2026-08-01')
        with pytest.raises(ValueError,match='immediately before'):prepare(r)
