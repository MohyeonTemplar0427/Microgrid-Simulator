"""Missouri filed benchmarks, local calendars, state and form-to-worker proofs."""
from copy import deepcopy
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import ameren_mo as mo
from src.billing.ameren_mo_rates import service_rates
from src.billing.regional import account_region,calculate_cycle
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.billing.regional_math import BillingMath
from src.dispatch.regional import optimize_cycle
from src.local_web.regional_study import defaults,prepare,capabilities,calendar_cycles
from src.timeseries import build_interval_index
from test_local_web import service,wait_for_study
from test_regional_study import browser_request


def fixture(plan='1M',month='2025-07',step=15):
    start=month+'-01';end=str((pd.Timestamp(start)+pd.offsets.MonthEnd()).date())
    a=mo.hypothetical_defaults(plan);a.update(billing_month=start,bill_date=end)
    if plan=='2M':
        current=pd.Timestamp(start)
        for key,m in [('may_month',5),('october_month',10)]:
            prior=current.replace(month=m)
            if prior>=current:prior-=pd.DateOffset(years=1)
            a['history'][key]=str(prior.date())
        prior=current-pd.DateOffset(months=1) if current.month in (7,8,9,10) else current.replace(month=9,year=current.year if current.month>10 else current.year-1)
        a['history']['summer_through']=str(prior.date())
    return a,build_interval_index(start,end,mo.TIMEZONE,step).index


def bill(plan='1M',month='2025-07',kwh=1000.,state=None):
    a,idx=fixture(plan,month)
    return calculate_cycle(mo.UTILITY,idx,np.full(len(idx),kwh/(len(idx)/4)),np.zeros(len(idx)),a,state=state)


@pytest.mark.parametrize('plan',mo.PLANS)
@pytest.mark.parametrize('month,fac,sur,ee,resram,new',[
    ('2025-01','.00229','.00200',('.003572','.003739'),'.00204',False),
    ('2025-02','.00114','.00200',('.002171','.002819'),'.00313',False),
    ('2025-07','.00360','.00200',('.002171','.002819'),'.00133',True),
    ('2026-01','.00330','.00108',('.002171','.002819'),'.00133',True),
    ('2026-02','.00540','.00108',('.001905','.002272'),'.00207',True),
    ('2026-07','.00894','.00118',('.001905','.002272'),'.00207',True),
])
def test_independent_bill_components(plan,month,fac,sur,ee,resram,new):
    # Independent Decimal transcription, uniform600kWh. January/February winter;
    # every January fixture has88 eligible Smartpeak hours, Feb2025 has80,
    # Feb2026 has80. July2025 has88, July2026 has92 (July3 is not a holiday).
    commercial=plan=='2M';summer=month.endswith('-07');k=D(600)
    if commercial:energy=k*D('.1346' if new and summer else '.1197' if summer else '.1005' if new else '.0894')
    elif plan=='1M' or plan.endswith('-B') and not summer:energy=k*D('.1560' if new and summer else '.1372' if summer else '.1062' if new else '.0934')
    elif plan=='1M-EMS':
        base=('.1524' if summer else '.1045') if new else ('.1340' if summer else '.0919')
        adder=('.0057' if summer else '.0028') if new else ('.0050' if summer else '.0025')
        energy=k*D(base)+k*D(adder)/2
    elif 'OVERNIGHT' in plan:
        peak,off=(('.1839','.0732') if summer else ('.1034','.0631')) if new else (('.1617','.0644') if summer else ('.0910','.0555'))
        energy=k*(2*D(peak)+D(off))/3
    else:
        peak,mid,off=(('.4051','.1216','.0767') if summer else ('.2169','.0778','.0635')) if new else (('.3562','.1069','.0674') if summer else ('.1907','.0684','.0558'))
        days=28 if month.endswith('-02') else 31;hours=D(days*24)
        peak_hours=D(80 if days==28 else 92 if month=='2026-07' else 84 if month=='2026-01' else 88)
        off_hours=D(days*8);mid_hours=hours-peak_hours-off_hours
        energy=k*(D(peak)*peak_hours+D(mid)*mid_hours+D(off)*off_hours)/hours
    expected=dict(customer=D('25.73' if new else '22.87') if commercial else D(9),
        low_income_pilot=D('.26' if new else '.20') if commercial else D('.19' if new else '.14'),energy=energy,
        fuel_adjustment=k*D(fac),securitization=k*D(sur),energy_efficiency=k*D(ee[commercial]),renewable_adjustment=k*D(resram))
    expected['missouri_sales_tax']=sum(expected.values())*D('.056' if commercial else '0')
    b=bill(plan,month,600.)
    assert b['unrounded_lines']==pytest.approx({k:float(v) for k,v in expected.items()},abs=1e-8)
    assert b['unrounded_total_usd']==pytest.approx(float(sum(expected.values())),abs=1e-8)
    assert b['is_complete_bill'] and b['rate_evidence_status']=='verified'
    assert 'demand' not in b['lines'] and 'transmission' not in b['lines']


@pytest.mark.parametrize('plan,first,tail', [('1M',.0934,.0627),('1M-EMS',.0919,.0616),('1M-SMART-B',.0934,.0627),('1M-OVERNIGHT-B',.0934,.0627)])
@pytest.mark.parametrize('kwh',[749.99,750.,750.01,1200.])
def test_winter_declining_blocks(plan,first,tail,kwh):
    expected=min(kwh,750)*first+max(kwh-750,0)*tail
    if plan=='1M-EMS':expected+=kwh/2*.0025
    assert bill(plan,'2025-01',kwh)['unrounded_lines']['energy']==pytest.approx(expected)


@pytest.mark.parametrize('day,peak,mid',[
 ('2025-01-01 06:00',False,True),('2025-04-18 15:00',False,True), # GoodFriday
 ('2025-05-26 18:00',False,True),('2025-07-04 15:00',False,True),
 ('2025-09-01 15:00',False,True),('2025-11-27 06:00',False,True),
 ('2025-11-28 18:00',False,True),('2025-12-24 06:00',False,True),('2025-12-25 18:00',False,True),
 ('2026-07-03 15:00',True,False), # No observedFriday for SaturdayJuly4
 ('2026-12-31 06:00',True,False), # No shiftedNewYear
 ('2025-07-03 14:45',False,True),('2025-07-03 15:00',True,False),
 ('2025-07-03 19:00',False,True),('2025-07-03 22:00',False,False),
 ('2025-01-02 05:45',False,False),('2025-01-02 06:00',True,False),
 ('2025-01-02 08:00',False,True),('2025-01-02 18:00',True,False),('2025-01-02 20:00',False,True),
 ('2025-07-05 15:00',False,True)])
def test_nine_actual_holidays_and_boundaries(day,peak,mid):
    idx=pd.DatetimeIndex([pd.Timestamp(day,tz=mo.TIMEZONE)])
    p=mo.periods(idx,'1M-SMART-A')
    assert bool(p['peak'][0])==peak and bool(p['mid'][0])==mid


@pytest.mark.parametrize('plan,before,at', [('1M-EMS','08:45','09:00'),('1M-OVERNIGHT-A','05:45','06:00')])
def test_every_day_tariffs_keep_holiday_peak(plan,before,at):
    idx=pd.DatetimeIndex([pd.Timestamp('2025-07-04 '+x,tz=mo.TIMEZONE) for x in [before,at]])
    assert mo.periods(idx,plan)['peak'].tolist()==[False,True]


def test_observed_holiday_changes_bill_only_for_true_holidays():
    a,idx=fixture('1M-SMART-A','2026-07');imp=np.zeros(len(idx))
    imp[(idx.day==3)&(idx.hour==15)]=1.;imp[(idx.day==4)&(idx.hour==15)]=1.
    b=calculate_cycle(mo.UTILITY,idx,imp,np.zeros(len(idx)),a)
    assert b['unrounded_lines']['energy']==pytest.approx(.4051+.1216)


@pytest.mark.parametrize('day,base,fac,sur,ee,resram',[
 ('2025-01-31','2023-12-03',.00229,.002,.003572,.00204),
 ('2025-02-01','2023-12-03',.00114,.002,.002171,.00313),
 ('2025-05-31','2023-12-03',.00114,.002,.002171,.00313),
 ('2025-06-01','2025-06-01',.00360,.002,.002171,.00133),
 ('2025-10-01','2025-06-01',.00330,.00108,.002171,.00133),
 ('2026-02-01','2025-06-01',.00540,.00108,.001905,.00207),
 ('2026-04-01','2025-06-01',.00540,.00118,.001905,.00207),
 ('2026-06-01','2025-06-01',.00894,.00118,.001905,.00207),
 ('2026-10-01','2025-06-01',.00445,.00157,.001905,.00207)])
def test_independent_dated_components_and_rebase(day,base,fac,sur,ee,resram):
    r=service_rates(day,'1M')
    assert r['base_version']==base
    for key,value in [('fuel_adjustment',fac),('securitization',sur),('energy_efficiency',ee),('renewable_adjustment',resram)]:assert r[key]==value


@pytest.mark.parametrize('day',['2024-12-31','2026-10-22','2027-01-01'])
def test_no_coverage_extrapolation(day):
    with pytest.raises(ValueError,match='coverage'):service_rates(day,'1M')


@pytest.mark.parametrize('month,hours',[('2025-03',743),('2025-11',721),('2026-03',743)])
def test_dst_gap_duplicate_local_clock_and_import_energy(month,hours):
    a,idx=fixture(month=month)
    b=calculate_cycle(mo.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert len(idx)==4*hours and b['import_kwh']==hours
    with pytest.raises(ValueError,match='consecutive'):mo.validate_account(a,idx.delete(20))
    with pytest.raises(ValueError,match='Chicago'):mo.validate_account(a,idx.tz_convert('UTC'))


@pytest.mark.parametrize('kwh',[999.,1000.,1001.,5499.99,5500.,5500.01,7000.])
def test_commercial_seasonal_use_uses_max_of_floor_and_lesser_history(kwh):
    b=bill('2M','2025-01',kwh)
    assert b['metrics']['winter_base_threshold_kwh']==5500.
    assert b['unrounded_lines']['energy']==pytest.approx(min(kwh,5500)*.0894+max(kwh-5500,0)*.0516)


def test_history_continuity_and_scenario_specific_billed_imports():
    a,idx=fixture('2M','2025-05')
    b=calculate_cycle(mo.UTILITY,idx,np.full(len(idx),1500/(len(idx)/4)),np.zeros(len(idx)),a)
    assert b['next_state']['history']['may_kwh']==pytest.approx(1500.)
    c,octidx=fixture('2M','2025-10')
    state=deepcopy(b['next_state'])
    # Simulate the four intervening months with different solar self-use.
    for m,k in [('2025-06',8000),('2025-07',9500),('2025-08',7000),('2025-09',6000)]:
        aa,ii=fixture('2M',m)
        state=calculate_cycle(mo.UTILITY,ii,np.full(len(ii),k/(len(ii)/4)),np.zeros(len(ii)),aa,state=state)['next_state']
    result=calculate_cycle(mo.UTILITY,octidx,np.full(len(octidx),3000/(len(octidx)/4)),np.zeros(len(octidx)),c,state=state)
    assert result['metrics']['winter_base_threshold_kwh']==pytest.approx(1500.)
    assert result['next_state']['history']['summer_max_kwh']==pytest.approx(9500.)
    assert result['next_state']['history']['october_kwh']==pytest.approx(3000.)
    assert c['history']['may_kwh']==6000. # no mutation of originalaccount
    with pytest.raises(ValueError,match='consecutively'):calculate_cycle(mo.UTILITY,octidx,np.ones(len(octidx)),np.zeros(len(octidx)),c,state=result['next_state'])
    broken=deepcopy(c);broken['history']['may_month']='2024-05-01'
    with pytest.raises(ValueError,match='preceding May'):mo.validate_state(broken,octidx)


@pytest.mark.parametrize('month,expected',[('2025-01','2024-09-01'),('2025-06','2024-09-01'),
    ('2025-07','2025-06-01'),('2025-10','2025-09-01'),('2025-11','2025-09-01'),
    ('2025-12','2025-09-01'),('2026-01','2025-09-01')])
def test_preceding_summer_is_not_shifted_back_after_october(month,expected):
    assert str(mo.preceding_summer_month(month+'-01').date())==expected
    a,idx=fixture('2M',month)
    assert a['history']['summer_through']==expected
    mo.validate_state(a,idx)
    assert bill('2M',month,3000.)['total_usd']>0


def test_october_november_december_january_state_continues_same_summer():
    state=None
    for month in ['2025-10','2025-11','2025-12','2026-01']:
        a,idx=fixture('2M',month)
        b=calculate_cycle(mo.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a,state=state)
        state=b['next_state']
        assert state['history']['summer_through']=='2025-09-01'
    assert state['next_billing_month']=='2026-02-01'


@pytest.mark.parametrize('month,base,tail',[('2025-01',.0894,.0516),('2026-01',.1005,.0581)])
def test_commercial_history_below_1000_preserves_minimum_base_block(month,base,tail):
    a,idx=fixture('2M',month);a['history'].update(may_kwh=300.,october_kwh=400.,summer_max_kwh=600.)
    b=calculate_cycle(mo.UTILITY,idx,np.full(len(idx),1500/(len(idx)/4)),np.zeros(len(idx)),a)
    assert b['metrics']['winter_base_threshold_kwh']==1000.
    assert b['unrounded_lines']['energy']==pytest.approx(1000*base+500*tail)


@pytest.mark.parametrize('key,value',[
 ('eligibility_confirmed',False),('ordinary_service_confirmed',False),('local_charges_confirmed',False),
 ('tax_jurisdiction','st_louis'),('tax_source',''),('supply','rtp'),('export_mode','net_metering'),
 ('opening_credit_usd',1.),('full_monthly_charges_confirmed',False),('cycle_kind','initial'),('phase','three')])
def test_unsupported_accounts_fail(key,value):
    a,idx=fixture();a[key]=value
    with pytest.raises(ValueError):mo.validate_account(a,idx)


def test_partial_crossing_missing_history_export_and_equipment_reject():
    a,idx=fixture('2M')
    for i in [idx[:-1],idx[96:],build_interval_index('2025-07-15','2025-08-14',mo.TIMEZONE,15).index]:
        with pytest.raises(ValueError,match='complete calendar'):mo.validate_account(a,i)
    with pytest.raises(ValueError,match='100kW'):calculate_cycle(mo.UTILITY,idx,np.full(len(idx),100.1),np.zeros(len(idx)),a)
    with pytest.raises(ValueError,match='non-export'):calculate_cycle(mo.UTILITY,idx,np.ones(len(idx)),np.ones(len(idx)),a)
    broken=deepcopy(a);broken['history']=None
    with pytest.raises(ValueError,match='history'):mo.validate_account(broken,idx)
    reference=grid_only_counterfactual(mo.UTILITY,a)
    assert reference['account']['history']==a['history'] and reference['account']['dg_enrollment_confirmed'] is False
    equipment=dict(pv=True,battery=True,pv_dc_kw=10.,pv_ac_kw=8.,battery_kw=8.)
    mo.validate_account(a,idx,equipment)
    with pytest.raises(ValueError,match='approved non-export'):mo.validate_account(reference['account'],idx,equipment)
    with pytest.raises(ValueError,match='50kW'):mo.validate_account(a,idx,{**equipment,'battery_kw':45.})
    with pytest.raises(ValueError,match='standalone'):mo.validate_account(a,idx,{**equipment,'pv':False})


def test_miso_identity_default_clock_and_reproducible_cases():
    from tools.run_regional_validation import selected_cases,case_request
    r=defaults(mo.UTILITY);region=r['regional_account'];account_region(region,mo.UTILITY)
    assert r['timezone']==mo.TIMEZONE and region['resource_adequacy_zone']=='LRZ5'
    assert region['transmission_owner']=='Ameren Missouri' and region['state_jurisdiction']=='MO'
    assert region['wholesale_pricing_location'] is None
    with pytest.raises(ValueError):account_region({**region,'resource_adequacy_zone':'LRZ4'},mo.UTILITY)
    assert len(capabilities()['utilities'][mo.UTILITY]['plans'])==7
    for _,kind,p in selected_cases([mo.UTILITY]):
        q=case_request(mo.UTILITY,kind,plan=p)
        assert q['timezone']==mo.TIMEZONE and len(q['billing_cycles'])==12


@pytest.mark.parametrize('plan',['1M','1M-EMS','1M-SMART-A','1M-OVERNIGHT-A','2M'])
def test_exact_fixed_schedule_symbolic_billing_parity(plan):
    a,idx=fixture(plan,'2025-01');n=len(idx)
    g=cp.Variable(n,nonneg=True);values=np.full(n,1.5)
    math=BillingMath(idx,convex=True,power_bound=3.)
    math.register_power(g,np.zeros(n),np.full(n,3.),energy_upper=1200.)
    charges=mo.charge_lines(idx,g,cp.Constant(np.zeros(n)),a,math=math)
    objective=sum(charges['lines'].values())
    problem=cp.Problem(cp.Minimize(objective),[g==values,*math.constraints])
    problem.solve(solver='SCIPY',scipy_options={'time_limit':20.})
    b=calculate_cycle(mo.UTILITY,idx,values,np.zeros(n),a)
    assert problem.status=='optimal' and problem.value==pytest.approx(b['unrounded_total_usd'],abs=1e-6)


@pytest.mark.parametrize('plan',['1M','1M-SMART-A','2M'])
def test_winter_dispatch_cost_proof_bill_and_flow_reconciliation(plan):
    a,idx=fixture(plan,'2025-01')
    pv=3*np.maximum(0,np.sin((idx.hour.to_numpy()-6)*np.pi/12))
    inputs=pd.DataFrame(dict(timestamp=idx,native_load_kw=np.full(len(idx),2.),pv_available_kw=pv))
    battery=defaults(mo.UTILITY,'commercial' if plan=='2M' else 'residential',plan)['battery']
    out=optimize_cycle(inputs,mo.UTILITY,a,battery=battery,terminal_energy=battery['energy_kWh'],grid_charging=True,time_limit=30.)
    assert out['cost_optimum_proven'] and out['reconciliation_difference_usd']<.0001
    assert out['dispatch'].grid_export_kw.max()<1e-5


@pytest.mark.parametrize('plan',['1M','1M-SMART-A','2M'])
def test_main_browser_form_worker_bills_electrical_saved_results(service,plan):
    app,call,headers=service
    r=defaults(mo.UTILITY,'commercial' if plan=='2M' else 'residential',plan)
    r['operating_contract'].update(interconnection_confirmed=True,grid_charging_confirmed=True,reference='Explicit hypothetical approved Ameren Missouri non-export PV/storage')
    r=browser_request(r);prepare(r)
    study=call('/api/v1/regional/studies',r,headers);out=wait_for_study(call,study['id'])
    assert out['status']=='completed',out.get('error')
    result=out['result']
    assert result['engine_id']==app.engine['id'] and result['ac_validation']['all_intervals_feasible']
    assert set(result['billing'])=={'grid_only','pv_only','pv_battery'}
    assert all(b[0]['is_complete_bill'] and b[0]['rate_evidence_status']=='verified' for b in result['billing'].values())
    base='/api/studies/'+study['id']
    assert b'missouri_sales_tax' in call(base+'/tables/billing-components.csv')
    assert b'scheduled_grid' in call(base+'/tables/ac-pv_battery.csv')
    assert call(base+'/tables.zip')[:2]==b'PK'
    call(base+'/save',{'name':'Missouri '+plan+' acceptance'},headers)
    restored=call(base+'/request.json')
    assert restored['account']==r['account'] and browser_request(restored)['account']==r['account']


def test_retained_source_hashes_and_dates():
    sources=json.loads(Path('docs/utility_sources/ameren_mo/manifest.json').read_text())['sources']
    assert len(sources)>=20
    for s in sources:
        assert len(s['pdf_sha256'])==64
        assert hashlib.sha256(Path(s['extracted_text']).read_bytes()).hexdigest()==s['extracted_text_sha256']
