"""Offline independent2025 tariff benchmarks; never substitute2026taxes."""
from copy import deepcopy
import numpy as np
import pandas as pd
import pytest
from src.billing import dominion_va_general as va
from src.billing import dominion_va_historical as historical
from src.billing.regional_math import BillingMath


def idx(start,end):
    return pd.date_range(start,end,tz=va.TIMEZONE,freq='30min',inclusive='left')


def bill(plan,index,load=1.,**patch):
    account=va.defaults(plan);account.update(billing_month=index[-1].month,**patch)
    power=np.broadcast_to(load,(len(index),)).copy()
    return va.charge_lines(index,power,np.zeros(len(index)),account,math=BillingMath(index))


# Independently transcribed January filed charges in USD/kWh, ordered res / GS1.
JAN={
 'A':(.020735,.020735),'B':(.000627,.000507),'BW':(.002348,.001483),
 'GV':(.002474,.001698),'US2':(.000159,.000126),'US3':(.000687,.000469),
 'US4':(.000266,.000181),'GEN':(0.,0.),'C1A':(.000139,.000095),
 'C2A':(-.000036,-.000025),'C4A':(.001452,.000990),'CCR':(.001183,.001183),
 'CE':(.002884,.001780),'E':(.001351,.000908),'GT':(.003217,.001815),
 'U':(.004168,.002403),'DIST':(0.,0.),'OSW':(.008631,.005894),
 'PIPP':(0.,0.),'RGGI':(0.,0.),'RBB':(.000424,.000253),
 'RPS':(.004689,.004689),'SMR':(0.,0.),'SNA':(.001287,.000870),
 'T1':(.009687,.009247),'deferred_fuel':(.003371,.003371)}


def independent_rates(month,group):
    r={key:value[group] for key,value in JAN.items()}
    if month>=2:r['deferred_fuel']=.003449
    if month>=4:
        for key in ('B','BW','GV','US2','US3','US4'):r[key]=0.
        r['GEN']=(.007564,.005989)[group]
    if month>=5:r.update(CE=(.003668,.002567)[group],RBB=(.000531,.000348)[group])
    if month>=6:r.update(GT=0.,U=0.,DIST=(.006241,.004002)[group])
    if month>=7:r['A']=.029680
    if month>=8:r['deferred_fuel']=.002906
    if month>=9:r.update(C1A=(.000231,.000171)[group],C2A=0.,C4A=(.001336,.000988)[group],
        OSW=(.011229,.007957)[group],RPS=.007676,SMR=(.000287,.000212)[group],
        SNA=(.003475,.002561)[group],T1=(.011789,.010069)[group])
    if month>=11:r['E']=(.000625,.000456)[group]
    return r


def independent(plan,kwh,month,post_august_tax=False):
    res=plan=='VA-1';bound=800 if res else 1400
    dist=(.026656,.019708) if res else (.019164,.018136)
    gen=((.028063,.042708) if 6<=month<=9 else (.027031,.023430)) if res else ((.025910,.034795) if 6<=month<=9 else (.025910,.016732))
    value=(7.58 if res else 13.39)+min(kwh,bound)*(dist[0]+gen[0])+max(kwh-bound,0)*(dist[1]+gen[1])
    value+=kwh*((.00970 if res else .00582)+sum(independent_rates(month,0 if res else 1).values()))
    if post_august_tax:value+=min(kwh,2500)*.001565+min(max(kwh-2500,0),47500)*.001055+max(kwh-50000,0)*.000845
    return value


@pytest.mark.parametrize('plan,load',[('VA-1',1.),('VA-GS1',10.)])
@pytest.mark.parametrize('month',list(range(1,13)))
def test_each_month_independent_component_benchmark(plan,load,month):
    start=pd.Timestamp(2025,month,1);stop=start+pd.offsets.MonthBegin()
    grid=idx(start,stop);kwh=len(grid)*.5*load
    r=bill(plan,grid,load)
    assert sum(r['lines'].values())==pytest.approx(independent(plan,kwh,month,month>=8),abs=1e-7)
    for key,rate in independent_rates(month,0 if plan=='VA-1' else 1).items():
        assert r['lines']['deferred_fuel' if key=='deferred_fuel' else 'rider_'+key]==pytest.approx(kwh*rate,abs=1e-8)
    assert r['is_complete_bill'] is False
    assert 'sales_use_tax_surcharge' in r['excluded_components']
    assert 'local_utility_consumer_tax' in r['excluded_components']
    assert 'sales_use_tax_surcharge' not in r['lines']
    assert 'henrico_utility_tax' not in r['lines']
    assert ('consumption_tax' in r['lines'])==(month>=8)


@pytest.mark.parametrize('plan',['VA-1','VA-GS1'])
@pytest.mark.parametrize('month',[1,7])
@pytest.mark.parametrize('kwh',[0.,799.,800.,801.,1400.,1401.,3000.])
def test_historical_energy_blocks_against_independent_filed_arithmetic(plan,month,kwh):
    start=pd.Timestamp(2025,month,1);grid=idx(start,start+pd.offsets.MonthBegin())
    r=bill(plan,grid,kwh/(len(grid)*.5))
    assert sum(r['lines'].values())==pytest.approx(independent(plan,kwh,month),abs=1e-8)


@pytest.mark.parametrize('boundary,component,old,new',[
 ('2025-02-01','deferred_fuel',.003371,.003449),('2025-04-01','GEN',0.,.007564),
 ('2025-05-01','CE',.002884,.003668),('2025-06-01','DIST',0.,.006241),
 ('2025-07-01','A',.020735,.029680),('2025-08-01','deferred_fuel',.003449,.002906),
 ('2025-09-01','C4A',.001452,.001336),('2025-11-01','E',.001351,.000625)])
def test_exact_local_effective_boundary_and_crossing_cycle(boundary,component,old,new):
    change=pd.Timestamp(boundary);grid=idx(change-pd.Timedelta(days=14),change+pd.Timedelta(days=14))
    a=va.defaults('VA-1');a['billing_month']=change.month
    before=np.asarray(grid.date)<change.date();power=np.where(before,1.,2.)
    r=va.charge_lines(grid,power,np.zeros(len(grid)),a,math=BillingMath(grid))
    key='deferred_fuel' if component=='deferred_fuel' else 'rider_'+component
    assert r['lines'][key]==pytest.approx((power[before].sum()*old+power[~before].sum()*new)*.5)
    assert len(r['rate_components'][component])==2


def test_dst_preserves_actual_hours_and_30_minute_demand():
    march=idx('2025-03-01','2025-04-01');november=idx('2025-11-01','2025-12-01')
    assert len(march)==743*2
    assert len(november)==721*2
    for grid in (march,november):
        r=bill('VA-GS1',grid,5.)
        assert r['metrics']['import_kWh']==len(grid)*.5*5.
        assert r['metrics']['peak_kw']==5.


def test_consumption_tax_uses_verified_reading_version_not_service_day_proration():
    before=bill('VA-1',idx('2025-07-16','2025-08-16'))
    after=bill('VA-1',idx('2025-07-17','2025-08-17'))
    assert 'consumption_tax' not in before['lines']
    assert 'consumption_tax_before_2025_08_16' in before['excluded_components']
    assert after['lines']['consumption_tax']==pytest.approx(744*.001565)
    assert 'consumption_tax_before_2025_08_16' not in after['excluded_components']


@pytest.mark.parametrize('plan',['VA-1','VA-GS1'])
def test_2025_actual_partial_meter_cycle_uses_filed_proration(plan):
    grid=idx('2025-06-01','2025-06-16')
    with pytest.raises(ValueError,match='proration'):bill(plan,grid)
    r=bill(plan,grid,10.,cycle_kind='initial',cycle_source='Explicit hypothetical complete initial15-day reading period')
    assert r['lines']['customer']==pytest.approx((7.58 if plan=='VA-1' else 13.39)*.5)
    bound=400 if plan=='VA-1' else 700
    first,last=(.026656,.019708) if plan=='VA-1' else (.019164,.018136)
    assert r['lines']['distribution_energy']==pytest.approx(bound*first+(3600-bound)*last)


def test_historical_parallel_contract_and_minimum_use_2025_coefficients():
    grid=idx('2025-09-01','2025-10-01')
    r=bill('VA-GS1',grid,10.,parallel_service=True,parallel_operation_approved=True,contract_demand_kw=20.)
    assert r['lines']['parallel_contract_shortfall']==5.875*10
    assert r['next_state']['contract_demand_kw']==20.
    assert sum(r['lines'].values())==pytest.approx(independent('VA-GS1',7200,9,True)+58.75)


@pytest.mark.parametrize('plan',['VA-1','VA-GS1'])
def test_variable_dispatch_expressions_match_authoritative_historical_bill(plan):
    import cvxpy as cp
    grid=idx('2025-06-15','2025-07-15');a=va.defaults(plan);a['billing_month']=7
    if plan=='VA-GS1':a.update(parallel_service=True,parallel_operation_approved=True)
    power=cp.Variable(len(grid));m=BillingMath(grid,convex=True,power_bound=25.)
    m.register(power,0.,25.);m.constraints.extend([power==10.])
    r=va.charge_lines(grid,power,cp.Constant(np.zeros(len(grid))),a,math=m)
    problem=cp.Problem(cp.Minimize(sum(r['lines'].values())),m.constraints)
    problem.solve(solver='HIGHS')
    assert problem.status=='optimal'
    expected=va.charge_lines(grid,np.full(len(grid),10.),np.zeros(len(grid)),a,math=BillingMath(grid))
    assert problem.value==pytest.approx(sum(expected['lines'].values()),abs=1e-7)


def test_annual_rolling_bills_state_and_inputs_do_not_reset_or_mutate():
    account=va.defaults('VA-GS1');account.update(parallel_service=True,parallel_operation_approved=True,contract_demand_kw=20.)
    original=deepcopy(account);state=None;total=0.
    for month in range(1,13):
        start=pd.Timestamp(2025,month,1);grid=idx(start,start+pd.offsets.MonthBegin());account['billing_month']=month
        r=va.charge_lines(grid,np.full(len(grid),10.),np.zeros(len(grid)),account,math=BillingMath(grid),state=state)
        total+=sum(r['lines'].values());state=r['next_state']
    assert [entry['billing_month'] for entry in state['history']]==list(range(2,13))
    assert state['contract_demand_kw']==20.
    assert account['history']==original['history']
    assert np.isfinite(total)


def test_other_historical_dates_and_export_vintages_remain_unavailable():
    with pytest.raises(ValueError,match='coverage'):bill('VA-1G',idx('2025-09-01','2025-10-01'))
    assert bill('VA-1',idx('2026-01-01','2026-02-01'))['is_complete_bill'] is True
    with pytest.raises(ValueError,match='2025 solar-export'):bill('VA-1',idx('2025-09-01','2025-10-01'),solar_mode='net_metering')
    with pytest.raises(ValueError,match='Historical'):
        historical.component_vectors(idx('2024-12-01','2025-01-01'),'res')


def test_missing_component_version_and_wrong_timezone_never_fall_back(monkeypatch):
    grid=idx('2025-01-01','2025-02-01')
    with pytest.raises(ValueError,match='America/New_York'):
        historical.component_vectors(grid.tz_convert('UTC'),'res')
    monkeypatch.setitem(historical.COMPONENT_VERSIONS,'CCR',[('2025-04-01',.001183,.001183,378662,21)])
    with pytest.raises(ValueError,match='Missing verified.*CCR'):
        historical.component_vectors(grid,'res')


def test_normalized_historical_sources_match_retained_original_manifest():
    import json
    from pathlib import Path
    from src.billing.dominion_va_historical_data import COMPONENT_VERSIONS,SOURCE_DOCUMENTS,BASE_SOURCES
    root=Path(__file__).parents[1]/'docs/utility_sources/dominion/va_history_research'
    manifest=json.loads((root/'approved_2024_2025/manifest.json').read_text())
    documents={entry['document']['DocID']:entry for entry in manifest['filings'] if not entry.get('unavailable')}
    for versions in COMPONENT_VERSIONS.values():
        for start,res,gs1,doc,page in versions:
            assert SOURCE_DOCUMENTS[doc]['pdf_sha256']==documents[doc]['pdf_sha256']
            assert SOURCE_DOCUMENTS[doc]['source_url']==documents[doc]['source_url']
            assert 1<=page<=documents[doc]['pages']
    base_manifest=json.loads((root/'manifest.json').read_text())
    for plan,source in BASE_SOURCES.items():
        item=next(s for s in base_manifest['sources'] if s['plan']==('1' if plan=='VA-1' else 'gs1'))
        assert source['pdf_sha256']==item['pdf_sha256']
