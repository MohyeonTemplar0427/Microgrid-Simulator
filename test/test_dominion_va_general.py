"""Offline benchmarks from filed VA sheet arithmetic, not live API responses."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from src.billing import dominion_va_general as va
from src.billing.regional_math import BillingMath


def index(start='2026-09-01',end='2026-10-01',minutes=15):
    return pd.date_range(start,end,freq=f'{minutes}min',inclusive='left',tz=va.TIMEZONE)


def numeric(plan,load=1.,*,idx=None,patch=None,state=None):
    idx=index() if idx is None else idx
    account=va.defaults(plan);account.update(patch or {})
    power=np.broadcast_to(load,(len(idx),)).copy()
    return va.charge_lines(idx,power,np.zeros(len(idx)),account,math=BillingMath(idx),state=state)


# Independently transcribed sixteen recurring charges. Do not import module's
# RATE_COMPONENTS into expectations: this catches missing/incorrect rate rows.
RES_RIDERS=(.037648,.000454,.001322,.001765,.006054,.000754,.007685,.000625,
            .005729,.011362,0.,0.,.005520,.000147,.004027,.012730,.002901)
GS1_RIDERS=(.037648,.000384,.001116,.001765,.004673,.000541,.005780,.000456,
            .004100,.009229,0.,0.,.005520,.000124,.003429,.011929,.002901)


def test_residential_independent_full_bill_and_deferred_fuel():
    result=numeric('VA-1')
    expected=7.58+720*(.035690+.031212+.00970+sum(RES_RIDERS)+.000921)+.001565*720+1.
    assert sum(result['lines'].values())==pytest.approx(expected,abs=1e-9)
    assert result['lines']['deferred_fuel']==pytest.approx(720*.002901)
    assert result['is_complete_bill'] is True


@pytest.mark.parametrize('kwh',[0.,799.,800.,801.,1500.,2500.,2501.,50000.,50001.])
@pytest.mark.parametrize('billing_month',[9,10])
def test_residential_tiers_and_consumption_tax(kwh,billing_month):
    r=numeric('VA-1',kwh/720,patch={'billing_month':billing_month})
    dist=min(kwh,800)*.035690+max(kwh-800,0)*.023596
    first,last=(.031212,.046243) if billing_month==9 else (.030064,.026965)
    gen=min(kwh,800)*first+max(kwh-800,0)*last
    tax=min(kwh,2500)*.001565+min(max(kwh-2500,0),47500)*.001055+max(kwh-50000,0)*.000845
    assert r['lines']['distribution_energy']==pytest.approx(dist)
    assert r['lines']['generation_energy']==pytest.approx(gen)
    assert r['lines']['consumption_tax']==pytest.approx(tax)


@pytest.mark.parametrize('plan',['VA-1G','VA-1S','VA-1T','VA-5P'])
def test_residential_and_church_tou_holidays_are_the_filed_calendar(plan):
    idx=pd.date_range('2026-09-07',periods=96,freq='15min',tz=va.TIMEZONE)
    assert 'on_peak' not in va.periods(idx,plan)
    # GS-2T/3/4 deliberately price weekdays including Labor Day normally.
    assert 'on_peak' in va.periods(idx,'VA-GS2T')
    assert date(2026,7,3) not in va.holidays(2026)  # July4 falls Saturday.
    assert date(2027,12,24) not in va.holidays(2027)  # No Friday substitution.
    assert date(2028,12,25) in va.holidays(2028)


def test_1g_time_windows_season_boundaries_and_weekends():
    def p(stamp):return va.periods(pd.DatetimeIndex([pd.Timestamp(stamp,tz=va.TIMEZONE)]),'VA-1G')[0]
    assert p('2026-09-08 04:45')=='super_off_peak'
    assert p('2026-09-08 05:00')=='off_peak'
    assert p('2026-09-08 14:45')=='off_peak'
    assert p('2026-09-08 15:00')=='on_peak'
    assert p('2026-09-08 17:45')=='on_peak'
    assert p('2026-09-08 18:00')=='off_peak'
    assert p('2026-10-01 06:00')=='on_peak'
    assert p('2026-10-01 09:00')=='off_peak'
    assert p('2026-10-01 17:00')=='on_peak'
    assert p('2026-10-01 20:00')=='off_peak'
    assert p('2026-09-12 15:00')=='off_peak'


def test_small_commercial_independent_benchmark():
    kwh=7200
    r=numeric('VA-GS1',10.)
    expected=13.39+1400*(.025525+.030788)+(kwh-1400)*(.018928+.041350)+kwh*(.00582+sum(GS1_RIDERS)+.000847)
    expected+=2500*.001565+(kwh-2500)*.001055+10.
    assert sum(r['lines'].values())==pytest.approx(expected,abs=1e-8)


def test_church_5c_independent_benchmark_and_no_parallel_eligibility():
    kwh=7200.
    riders=(.037648,.000513,.001480,.001765,.007423,.000756,.006294,.000636,.006420,.013210,.005520,.000166,.004691,.012823,.002901)
    expected=13.88+3000*(.029255+.039064)+(kwh-3000)*(.024674+.041197)
    expected+=kwh*(.00887+sum(riders)+.000917)+2500*.001565+(kwh-2500)*.001055+10.
    assert sum(numeric('VA-5C',10.)['lines'].values())==pytest.approx(expected,abs=1e-8)
    with pytest.raises(ValueError,match='exclude parallel'):
        numeric('VA-5C',patch={'parallel_service':True,'parallel_operation_approved':True})


def test_gs2t_existing_candidate_reconciles_after_missing_fuel_is_added():
    # Same contract/history and20kWmeterload as legacy documented benchmark.
    patch={'parallel_service':True,'parallel_operation_approved':True,'contract_demand_kw':90.}
    r=numeric('VA-GS2T',20.,patch=patch)
    expected=37.08+90*(4.963+1.169)+14400*.000079
    expected+=20*(264*.020278+456*.009928)
    expected+=20*(4.526+2.313+4.554+1.633+.208+.182+1.581+3.366+.046+1.322)
    expected+=14400*(.037648+.000335+.000967+.001765+.005520+.002901+.000712)
    expected+=2500*.001565+11900*.001055+10
    assert sum(r['lines'].values())==pytest.approx(expected,abs=1e-8)
    assert r['metrics']['distribution_demand_kw']==90


@pytest.mark.parametrize('plan',['VA-1G','VA-1T','VA-1S','VA-5P'])
def test_independent_tou_structure_benchmarks(plan):
    # September2026:22weekdays; LaborDayexcluded =>21peak-eligible days.
    # This calendar arithmetic is independent of va.periods().
    kwh=720.
    if plan=='VA-1G':
        on,superoff,off=21*3,30*5,720-21*3-30*5
        expected=7.58+on*(.046743+.153972)+superoff*(.023674+.000112)+off*(.032360+.009307)+kwh*(.00970+sum(RES_RIDERS))
    elif plan=='VA-1T':
        on=21*11;off=720-on
        expected=12.99+on*(.080512+.056744)+off*(.008440+.014167)+kwh*(.00970+sum(RES_RIDERS))
    elif plan=='VA-1S':
        on=21*11;off=720-on
        expected=12.99+2.478+2.407+on*.031424+off*.002911+kwh*(.015465+.00970+sum(RES_RIDERS))
    else:
        on=21*12;off=720-on
        riders=(.037648,.000513,.001480,.001765,.007423,.000756,.006294,.000636,.006420,.013210,.005520,.000166,.004691,.012823,.002901)
        expected=23.01+4.055+6.332+on*.014615+off*.006928+kwh*(.010088+.00887+sum(riders))
    expected+=kwh*(.001565+(.000921 if plan!='VA-5P' else .000917))+(1. if plan!='VA-5P' else min(1.15+kwh*.00713,10.))
    assert sum(numeric(plan)['lines'].values())==pytest.approx(expected,abs=1e-8)


@pytest.mark.parametrize('plan',['VA-GS3','VA-GS4-primary','VA-GS4-transmission'])
def test_independent_large_service_benchmarks(plan):
    power=600.;kwh=432000.;reactive=power*np.tan(np.arccos(.95))
    if plan=='VA-GS3':
        demand=(3.316,8.976,2.277,.403,1.090,.189,.167,1.118,2.911,.044,1.073,3.972)
        energy=(.000111,.037648,.000271,.000834,.001765,.005520,.002901,.000541)
        expected=185.34+power*sum(demand)+60*.320+reactive*.235+kwh*sum(energy)
    else:
        primary=plan=='VA-GS4-primary'
        demand=(2.717,9.436,2.371,.311,.507,.161,.147,.993,2.437,.041,.901,4.729) if primary else (9.280,2.310,.499,.158,.145,.967,2.396,.040,.886,4.673)
        energy=(.000157,.037648,.000212,.000698,.001765,.005520,.002901,.000440)
        expected=343.54+power*sum(demand)+60*.558+reactive*.393+kwh*sum(energy)
    expected+=power*(264*.004648+456*.003299)
    expected+=2500*.001565+47500*.001055+(kwh-50000)*.000845+10.
    assert sum(numeric(plan,power)['lines'].values())==pytest.approx(expected,abs=1e-7)


def test_independent_gs2_demand_and_non_demand_branches():
    kwh=64800.;power=90.
    expected=31.90+power*(4.963+1.803+1.971+1.482+3.798+1.633+.208+.182+1.581+3.366+.046+1.322)
    expected+=13500*(.039031+.021879+.009461)+(kwh-40500)*.002301
    expected+=kwh*(.000079+.037648+.000335+.000967+.001765+.005520+.002901+.000712)
    expected+=2500*.001565+47500*.001055+(kwh-50000)*.000845+10.
    assert sum(numeric('VA-GS2',power)['lines'].values())==pytest.approx(expected,abs=1e-8)
    idx=index();load=np.ones(len(idx));load[0:2]=90.;kwh=764.5
    energy=(.035418,.030838,.01476,.037648,.000335,.000967,.001765,
            .004480,.000574,.004174,.000502,.004375,.009231,.005520,.000130,.003674,.029476,.002901)
    before_tax=31.90+kwh*sum(energy)
    # The non-demand plan still has a4.39/kWminimum when peak>=50kW.
    # Non-bypassable deferred fuel remains outside that minimum.
    expected=max(before_tax-kwh*.002901,4.39*90)+kwh*.002901+kwh*(.001565+.000712)+min(1.15+kwh*.00713,10.)
    assert sum(numeric('VA-GS2',load)['lines'].values())==pytest.approx(expected,abs=1e-8)


def test_all_supported_tariff_expressions_reconcile_fixed_schedule_milp():
    import cvxpy as cp
    idx=index(minutes=30)
    for plan in va.PLAN_INFO:
        account=va.defaults(plan)
        load=1. if account['customer_class']=='residential' else 10. if plan in ('VA-GS1','VA-5C','VA-5P') else 90. if plan in ('VA-GS2','VA-GS2T') else 600.
        power=cp.Variable(len(idx));math=BillingMath(idx,convex=True,power_bound=1000.)
        math.register(power,0.,1000.);math.constraints.append(power==load)
        result=va.charge_lines(idx,power,cp.Constant(np.zeros(len(idx))),account,math=math)
        problem=cp.Problem(cp.Minimize(sum(result['lines'].values())),math.constraints)
        assert problem.is_dcp(),plan
        problem.solve(solver='HIGHS',highs_options={'time_limit':20.})
        assert problem.status=='optimal',plan
        expected=sum(numeric(plan,load,idx=idx)['lines'].values())
        assert problem.value==pytest.approx(expected,abs=1e-6),plan


@pytest.mark.parametrize('plan',list(va.PLAN_INFO))
def test_every_supported_structure_has_itemized_finite_bill(plan):
    r=numeric(plan,10.)
    assert all(np.isfinite(float(v)) for v in r['lines'].values())
    assert 'rider_T1' in r['lines'] and 'deferred_fuel' in r['lines']
    assert 'PJM' not in r['lines']


def test_demand_uses_aligned_30_minute_average():
    idx=index();load=np.ones(len(idx));load[0:2]=[40.,0.]
    r=numeric('VA-GS2T',load,idx=idx)
    assert r['metrics']['peak_kw']==20.
    # A15minuteinstant40kW is not billed as40kW demand.
    idx30=index(minutes=30);average=load.reshape(-1,2).mean(axis=1)
    q=numeric('VA-GS2T',average,idx=idx30)
    assert r['lines']==pytest.approx(q['lines'])


def test_actual_cycle_fixed_charge_is_not_unconditionally_prorated():
    idx=index('2026-09-10','2026-10-15') #35service dates, not a calendar month.
    r=numeric('VA-1',idx=idx)
    assert r['lines']['customer']==7.58
    assert r['lines']['distribution_energy']==pytest.approx(800*.035690+40*.023596)
    q=numeric('VA-GS2T',idx=idx)
    assert q['lines']['customer']==pytest.approx(37.08*35/30)


def test_submonthly_30_day_rate_and_unverified_monthly_proration():
    idx=index('2026-09-01','2026-09-16')
    r=numeric('VA-GS2T',20.,idx=idx)
    assert r['lines']['customer']==37.08*.5
    assert r['lines']['distribution_demand']==90*4.963*.5
    with pytest.raises(ValueError,match='proration'):
        numeric('VA-1',idx=idx)


@pytest.mark.parametrize('plan',['VA-1','VA-1G','VA-1S','VA-1T','VA-GS1','VA-5C','VA-5P'])
def test_documented_initial_final_monthly_rate_proration(plan):
    idx=index('2026-09-01','2026-09-16')
    patch={'cycle_kind':'initial','cycle_source':'Explicit hypothetical complete15-day initial meter cycle'}
    r=numeric(plan,10.,idx=idx,patch=patch)
    fixed={'VA-1':7.58,'VA-1G':7.58,'VA-1S':12.99,'VA-1T':12.99,'VA-GS1':13.39,'VA-5C':13.88,'VA-5P':23.01}[plan]
    assert r['lines']['customer']==pytest.approx(fixed*.5)
    if plan=='VA-1':
        assert r['lines']['distribution_energy']==pytest.approx(400*.035690+3200*.023596)
    if plan=='VA-GS1':
        assert r['lines']['distribution_energy']==pytest.approx(700*.025525+2900*.018928)
    if plan=='VA-5C':
        assert r['lines']['distribution_energy']==pytest.approx(1500*.029255+2100*.024674)
    if plan in ('VA-1S','VA-5P'):
        assert r['lines']['distribution_demand']==pytest.approx(10.*(.5)*(2.478 if plan=='VA-1S' else 4.055))
    #The actual utility worksheet keeps consumption-tax kWh thresholds fixed.
    assert r['lines']['consumption_tax']==pytest.approx(2500*.001565+1100*.001055)
    final=numeric(plan,10.,idx=idx,patch={**patch,'cycle_kind':'final'})
    assert final['lines']==pytest.approx(r['lines'])


def test_documented_extended_monthly_rate_cycle_and_parallel_minimum_prorate():
    idx=index('2026-09-01','2026-10-16') #45days inside verified coverage.
    patch={'cycle_kind':'regular','cycle_source':'Explicit hypothetical45-day complete utility meter cycle'}
    r=numeric('VA-1',idx=idx,patch=patch)
    assert r['lines']['customer']==pytest.approx(7.58*1.5)
    assert r['lines']['distribution_energy']==pytest.approx(1080*.035690)
    idx=index('2026-09-01','2026-09-16')
    r=numeric('VA-GS1',10.,idx=idx,patch={**patch,'cycle_kind':'final','parallel_service':True,'parallel_operation_approved':True,'contract_demand_kw':20.})
    assert r['lines']['parallel_contract_shortfall']==pytest.approx(6.588*10*.5)


def test_partial_monthly_rate_numeric_and_variable_power_milp_reconcile():
    import cvxpy as cp
    idx=index('2026-09-01','2026-09-16',minutes=30)
    a=va.defaults('VA-1');a.update(cycle_kind='final',cycle_source='Complete hypothetical final cycle')
    power=cp.Variable(len(idx));math=BillingMath(idx,convex=True,power_bound=10.)
    math.register(power,0.,10.);math.constraints.extend([power==4.])
    r=va.charge_lines(idx,power,cp.Constant(np.zeros(len(idx))),a,math=math)
    problem=cp.Problem(cp.Minimize(sum(r['lines'].values())),math.constraints)
    problem.solve(solver='HIGHS')
    expected=numeric('VA-1',4.,idx=idx,patch=a)
    assert problem.status=='optimal'
    assert problem.value==pytest.approx(sum(expected['lines'].values()),abs=1e-7)


@pytest.mark.parametrize('day',['2025-01-01','2025-09-01','2026-10-16'])
def test_missing_historical_composite_never_uses_neighboring_rates(day):
    start=pd.Timestamp(day);end=start+pd.DateOffset(days=1)
    with pytest.raises(ValueError,match='coverage'):
        numeric('VA-GS2T',idx=index(start,end))


def test_large_schedule_summer_ratchet_and_state_roll_forward():
    a=va.defaults('VA-GS3');a['history'][-1].update(maximum_kw=900.,on_peak_kw=800.)
    before=deepcopy(a);idx=index();load=np.full(len(idx),300.)
    r=va.charge_lines(idx,load,np.zeros(len(idx)),a,math=BillingMath(idx))
    assert r['metrics']['distribution_demand_kw']==900.
    assert r['metrics']['billed_on_peak_kw']==600.
    assert r['next_state']['history'][-1]['on_peak_kw']==300. #actual, not75%ratchet.
    assert a==before
    assert r['lines']['reactive_demand']==pytest.approx(a['reactive_peak_kvar']*.235)


def test_unknown_local_tax_is_explicit_incomplete_bill():
    r=numeric('VA-1',patch={'locality':'unverified'})
    assert not r['is_complete_bill']
    assert r['excluded_components']==['local_utility_consumer_tax']
    assert 'henrico_utility_tax' not in r['lines']
    assert any('INCOMPLETE' in w for w in r['warnings'])


@pytest.mark.parametrize('plan,maximum',[('VA-GS1',40.),('VA-GS2',600.),('VA-GS2T',600.),('VA-GS3',20.)])
def test_evolving_history_rejects_unsupported_tariff_migration(plan,maximum):
    account=va.defaults(plan)
    state={'history':[dict(record,maximum_kw=maximum,on_peak_kw=maximum) for record in account['history']]}
    before=deepcopy(state)
    with pytest.raises(ValueError,match='reclassification'):
        numeric(plan,state=state)
    assert state==before


@pytest.mark.parametrize('plan,threshold',[('VA-GS2',30.),('VA-GS2T',30.),('VA-GS3',500.),('VA-GS4-primary',500.),('VA-GS4-transmission',500.)])
def test_confirmed_existing_service_retains_tariff_until_all_qualifying_peaks_expire(plan,threshold):
    account=va.defaults(plan)
    history=[{'billing_month':record['billing_month'],'maximum_kw':20.,'on_peak_kw':20.} for record in account['history']]
    history[-1].update(maximum_kw=threshold,on_peak_kw=threshold)
    state={'history':history};before=deepcopy(state)
    r=numeric(plan,10.,patch=account,state=state)
    assert np.isfinite(sum(r['lines'].values()))
    assert state==before
    # Three initial qualifying peaks and the existing-account retention rule
    # are different conditions; a new enrollment cannot borrow the latter.
    with pytest.raises(ValueError,match='qualifying'):
        numeric(plan,10.,patch={**account,'existing_tariff_enrollment_confirmed':False},state=state)
    expired={'history':[dict(record,maximum_kw=20.,on_peak_kw=20.) for record in history]}
    with pytest.raises(ValueError,match='reclassification'):
        numeric(plan,10.,patch=account,state=expired)


@pytest.mark.parametrize('plan',['VA-GS1','VA-GS2T'])
def test_variable_parallel_contract_expression_is_dcp(plan):
    import cvxpy as cp
    idx=index(minutes=30);account=va.defaults(plan)
    account.update(parallel_service=True,parallel_operation_approved=True)
    power=cp.Variable(len(idx));math=BillingMath(idx,convex=True,power_bound=200.)
    math.register(power,0.,200.)
    math.constraints.extend([power>=0.,power<=200.])
    result=va.charge_lines(idx,power,cp.Constant(np.zeros(len(idx))),account,math=math)
    assert cp.Problem(cp.Minimize(sum(result['lines'].values())),math.constraints).is_dcp()
    if plan=='VA-GS2T':
        assert result['next_state']['contract_demand_kw'] is result['metrics']['distribution_demand_kw']


def test_unreachable_consumption_tax_tiers_do_not_create_binary_selectors():
    import cvxpy as cp
    idx=index(minutes=30);a=va.defaults('VA-1G');a['locality']='unverified'
    power=cp.Variable(len(idx));math=BillingMath(idx,convex=True,power_bound=1.)
    math.register(power,0.,1.)
    math.constraints.extend([power>=0.,power<=1.])
    r=va.charge_lines(idx,power,cp.Constant(np.zeros(len(idx))),a,math=math)
    problem=cp.Problem(cp.Minimize(sum(r['lines'].values())),math.constraints)
    # At most720kWh cannot reach either2500/50000kWh tax threshold.
    # This checks solver structure, while the independent threshold tests above
    # still verify the exact three-tier bill arithmetic at every boundary.
    assert sum(v.size for v in problem.variables() if v.attributes['boolean'])==0
    math.constraints.append(power==.5)
    problem=cp.Problem(cp.Minimize(sum(r['lines'].values())),math.constraints)
    problem.solve(solver='HIGHS')
    assert problem.status=='optimal'
    assert r['lines']['consumption_tax'].value==pytest.approx(360*.001565)


@pytest.mark.parametrize('patch,match',[
 ({'supply_arrangement':'third_party'},'contract'),({'special_riders':True},'voluntary'),
 ({'customer_class':'commercial'},'customer class'),({'solar_mode':'net_metering'},'Net-metering'),
 ({'parallel_service':True,'parallel_operation_approved':False},'approved'),
 ({'ami':False},'AMI'),({'demand_response_enrolled':True},'demand-response'),
 ({'tou_reenrollment_eligible':False},'reenrollment')])
def test_missing_eligibility_and_unsupported_supply_reject(patch,match):
    with pytest.raises(ValueError,match=match):numeric('VA-1G',patch=patch)


def test_source_extract_hashes_match_retained_official_text():
    root=Path(__file__).parents[1]/'docs/utility_sources/dominion/va_general_2026'
    manifest=json.loads((root/'manifest.json').read_text())
    import hashlib
    assert manifest['pdf_sha256']=='b6a2fa0612183c27d839df336a9d555085757f2bbb0d698a2f21c902af0098dd'
    for item in manifest['extracts']:
        assert hashlib.sha256((root/item['file']).read_bytes()).hexdigest()==item['sha256']


def test_historical_scc_evidence_is_complete_text_and_not_enabled_coverage():
    import hashlib
    root=Path(__file__).parents[1]/'docs/utility_sources/dominion/va_history_research/approved_2024_2025'
    manifest=json.loads((root/'manifest.json').read_text())
    filings=[item for item in manifest['filings'] if not item.get('unavailable')]
    assert len(filings)>=63
    assert {374484,374485,374486,374487,377195,381286}.issubset({item['document']['DocID'] for item in filings})
    for item in filings:
        text=root/item['text_file']
        assert hashlib.sha256(text.read_bytes()).hexdigest()==item['text_sha256']
        assert text.read_text().startswith('PAGE 1\n')
        assert item['source_url'].startswith('https://www.scc.virginia.gov/docketsearch/DOCS/')
        assert len(item['pdf_sha256'])==64
    # Archived research must not automatically expand the executable composite.
    assert va.VERIFIED_START==date(2026,1,1)


def nem_account(plan='VA-1',*,bank=0.):
    account=va.defaults(plan)
    account.update(solar_mode='net_metering',parallel_service=True,parallel_operation_approved=True,
                   nem=va.nem_defaults(plan))
    if bank:
        account['nem']['bank_kwh']['all']=bank
    return account


def nem_bill(account,imports,exports,*,idx=None,state=None):
    idx=index() if idx is None else idx
    return va.charge_lines(idx,np.asarray(imports,float),np.asarray(exports,float),account,
                           math=BillingMath(idx),state=state)


def test_nem_flat_retail_credit_independent_arithmetic_and_current_net_taxes():
    idx=index();imp=np.where(idx.hour<12,2.,0.);exp=np.where(idx.hour>=12,1.,0.)
    a=nem_account(bank=100.)
    r=nem_bill(a,imp,exp)
    #720gross imports -360exports -100inherited kWh =>260billed kWh.
    #Taxes use360physical net deliveries, not260after inherited credits.
    expected=7.58+260*(.035690+.031212+.00970+sum(RES_RIDERS)+.000921)
    expected+=360*.001565+1.
    assert sum(r['lines'].values())==pytest.approx(expected,abs=1e-9)
    assert r['metrics']['import_kWh']==720.
    assert r['metrics']['export_kWh']==360.
    assert r['metrics']['billed_energy_kwh']==260.
    assert r['metrics']['tax_net_delivered_kwh']==360.
    assert r['metrics']['opening_credit_used_kwh_by_tier']=={'all':100.}
    assert r['next_state']['nem']['bank_kwh']=={'all':0.}
    assert r['next_state']['nem']['bank_as_of']=='2026-10-01'


def test_nem_net_export_earns_energy_bank_without_cash_or_negative_energy_charges():
    idx=index();imp=np.where(idx.hour<12,2.,0.);exp=np.where(idx.hour>=12,3.,0.)
    r=nem_bill(nem_account(),imp,exp)
    assert sum(r['lines'].values())==pytest.approx(7.58+.70)
    assert r['metrics']['billed_energy_kwh']==0.
    assert r['next_state']['nem']['bank_kwh']=={'all':360.}
    assert all(value>=0 for value in r['lines'].values())
    assert not any('cash' in key or 'payout' in key for key in r['lines'])


def test_nem_tou_energy_stays_in_its_own_tier_and_demand_stays_measured():
    idx=index();labels=va.periods(idx,'VA-1G')
    imp=np.where(labels=='on_peak',2.,0.);exp=np.where(labels=='off_peak',1.,0.)
    r=nem_bill(nem_account('VA-1G'),imp,exp)
    expected=7.58+126*(.046743+.153972+.00970+sum(RES_RIDERS)+.000921)+.70
    assert sum(r['lines'].values())==pytest.approx(expected,abs=1e-9)
    assert r['next_state']['nem']['bank_kwh']['off_peak']==507.
    assert r['next_state']['nem']['bank_kwh']['on_peak']==0.
    assert r['metrics']['tax_net_delivered_kwh']==0.
    #1S still bills its actual30minute on-peak demand despite net surplus.
    labels=va.periods(idx,'VA-1S');imp=np.where(labels=='on_peak',2.,0.);exp=np.where(labels=='off_peak',3.,0.)
    s=nem_bill(nem_account('VA-1S'),imp,exp)
    assert s['lines']['distribution_demand']==2.*2.478
    assert s['lines']['generation_demand']==2.*2.407


def test_nem_opening_credits_change_cash_bill_but_default_objective_excludes_them():
    a=nem_account(bank=500.);before=deepcopy(a)
    objective_account,objective_state=va.objective_inputs(a)
    assert objective_state is None
    assert objective_account['nem']['bank_kwh']=={'all':0.}
    assert a==before
    cash,_=va.objective_inputs(a,policy='explicit_cash_bill')
    assert cash==a
    idx=index();imp=np.ones(len(idx));exp=np.zeros(len(idx))
    assert sum(nem_bill(a,imp,exp)['lines'].values()) < sum(nem_bill(objective_account,imp,exp)['lines'].values())


def test_nem_monthly_bank_continues_into_documented_final_partial_cycle():
    idx=index();a=nem_account()
    first=nem_bill(a,np.where(idx.hour<12,2.,0.),np.where(idx.hour>=12,3.,0.))
    state=deepcopy(first['next_state']);before=deepcopy(state)
    final=index('2026-10-01','2026-10-15')
    a.update(billing_month=10,cycle_kind='final',cycle_source='Complete hypothetical final14-day meter cycle')
    second=nem_bill(a,np.ones(len(final)),np.zeros(len(final)),idx=final,state=state)
    assert second['metrics']['billed_energy_kwh']==0.
    assert second['metrics']['opening_credit_used_kwh_by_tier']=={'all':336.}
    assert second['next_state']['nem']['bank_kwh']=={'all':24.}
    assert second['lines']['customer']==pytest.approx(7.58*14/30)
    assert second['lines']['consumption_tax']==pytest.approx(336*.001565)
    assert state==before
    objective_account,objective_state=va.objective_inputs(a,state)
    assert objective_state['nem']['bank_kwh']=={'all':0.}
    assert objective_state['nem']['bank_as_of']=='2026-10-01'
    assert state==before


@pytest.mark.parametrize('plan',['VA-1','VA-1G','VA-1S'])
def test_nem_fixed_interval_schedule_milp_reconciles_to_numeric_bill(plan):
    import cvxpy as cp
    idx=index(minutes=30);a=nem_account(plan)
    imp_value=np.where(idx.hour<12,2.,0.);exp_value=np.where(idx.hour>=12,1.,0.)
    imp=cp.Variable(len(idx));exp=cp.Variable(len(idx));math=BillingMath(idx,convex=True,power_bound=5.)
    math.register(imp,0.,5.);math.register(exp,0.,5.)
    math.constraints.extend([imp==imp_value,exp==exp_value])
    r=va.charge_lines(idx,imp,exp,a,math=math)
    problem=cp.Problem(cp.Minimize(sum(r['lines'].values())),math.constraints)
    assert problem.is_dcp()
    problem.solve(solver='HIGHS',highs_options={'time_limit':20.})
    assert problem.status=='optimal'
    assert problem.value==pytest.approx(sum(nem_bill(a,imp_value,exp_value,idx=idx)['lines'].values()),abs=1e-7)


def test_nem_ledger_provenance_date_and_unimplemented_boundaries_reject():
    idx=index();power=np.ones(len(idx));zeros=np.zeros(len(idx))
    a=nem_account();a['nem']['bank_as_of']='2026-08-31'
    with pytest.raises(ValueError,match='stale banks'):nem_bill(a,power,zeros)
    a=nem_account();a['nem']['approved_capacity_ac_kw']=21.
    with pytest.raises(ValueError,match='standby'):nem_bill(a,power,zeros)
    a=nem_account();a['nem']['ppa']=True
    with pytest.raises(ValueError,match='PPA'):nem_bill(a,power,zeros)
    a=nem_account();a['nem']['period_start']='2025-10-01'
    with pytest.raises(ValueError,match='Annual NEM boundaries'):nem_bill(a,power,zeros)
    a=nem_account('VA-1G');idx=index('2026-09-15','2026-10-15')
    with pytest.raises(ValueError,match='seasonal'):nem_bill(a,np.ones(len(idx)),np.zeros(len(idx)),idx=idx)
    a=nem_account('VA-1S');a['nem']['storage_restrictions_confirmed']=False
    with pytest.raises(ValueError,match='storage'):
        va.validate_account(a,index(),equipment={'battery':True})
    with pytest.raises(ValueError,match='capacity exceeds'):
        va.validate_account(nem_account(),index(),equipment={'pv':True,'pv_ac_kw':9.})


def test_nem_primary_source_extracts_are_retained_with_hashes():
    import hashlib
    root=Path(__file__).parents[1]/'docs/utility_sources/dominion/va_general_2026'
    manifest=json.loads((root/'nem_manifest.json').read_text())
    for item in manifest['sources']:
        assert hashlib.sha256((root/item['file']).read_bytes()).hexdigest()==item['text_sha256']


@pytest.mark.parametrize('plan',['VA-10-secondary','VA-10-primary','VA-10-transmission'])
def test_schedule10_independent_daily_classification_and_full_bill(plan):
    #Official September2026 calendar:1A,26B,3C. Each day is priced by
    #its actual classification, including weekends and Labor Day.
    secondary=plan.endswith('secondary');transmission=plan.endswith('transmission')
    kwh=432000.;power=600.
    generation=power*(5*.278424+19*.061924+26*(10*.022304+14*.005910)+3*(15*.009616+9*.005546))
    riders=(.037648,.001765,.005520,.002901)
    specific=(.000271,.000834,.002126,.000365,.000322,.002163,.005678,.000087,.002101) if secondary else (.000212,.000698,.000826,.000275,.000252,.001700,.003972,.000070,.001530)
    expected=201.65+generation+kwh*(sum(riders)+sum(specific)+(.001682+.000541 if secondary else .001771+.000440))
    expected+=power*((3.316+.403 if secondary else 0. if transmission else 2.717+.311)+(1.094+3.897 if secondary else .646+3.988))
    expected+=2500*.001565+47500*.001055+(kwh-50000)*.000845+10.
    r=numeric(plan,power)
    assert sum(r['lines'].values())==pytest.approx(expected,abs=1e-7)
    assert r['metrics']['daily_classification_counts']=={'A':1,'B':26,'C':3}


def test_schedule10_price_boundaries_holiday_and_missing_day_rejection():
    def rate(stamp):return va.schedule10_generation_rates(pd.DatetimeIndex([pd.Timestamp(stamp,tz=va.TIMEZONE)]))[0][0]
    assert rate('2026-09-02 13:45')==.061924
    assert rate('2026-09-02 14:00')==.278424
    assert rate('2026-09-02 18:45')==.278424
    assert rate('2026-09-02 19:00')==.061924
    assert rate('2026-09-07 12:00')==.022304 #OfficialB, no invented holidayC.
    assert rate('2026-10-01 05:45')==.010106
    assert rate('2026-10-01 06:00')==.022304
    assert rate('2026-10-01 12:00')==.010106
    with pytest.raises(ValueError,match='missing'):rate('2027-01-01 12:00')


def test_schedule10_rejects_frozen_apparent_demand_or_demand_response():
    with pytest.raises(ValueError,match='maximum-kVA'):
        numeric('VA-10-secondary',600.,patch={'power_factor':.95})
    with pytest.raises(ValueError,match='demand-response'):
        numeric('VA-10-secondary',600.,patch={'demand_response_enrolled':True})


def test_schedule10_historical_calendar_dates_and_current_module_match_evidence():
    from src.billing.dominion_va_calendar_data import CLASSIFICATIONS
    root=Path(__file__).parents[1]/'docs/utility_sources/dominion/va_history_research'
    evidence=json.loads((root/'schedule10_calendar_2017_2026.json').read_text())
    expected={stamp.date().isoformat() for stamp in pd.date_range('2017-01-01','2026-10-15')}
    assert set(evidence['records'])==expected
    assert CLASSIFICATIONS=={key:value for key,value in evidence['records'].items() if key>='2026-01-01'}
    assert len(evidence['retrievals'])==118
    #Calendar availability does not authorize unverified historical rate bills.
    with pytest.raises(ValueError,match='coverage'):
        numeric('VA-10-secondary',600.,idx=index('2025-09-01','2025-10-01'))
