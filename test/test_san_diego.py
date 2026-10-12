"""Independent rate arithmetic, eligibility boundaries and bill/dispatch parity."""
import numpy as np
import pandas as pd
import pytest

from src.billing.socal import bill, eligibility
from src.billing.san_diego import charge_lines, periods, RATE_PLANS
from src.dispatch.socal import optimize
from test_socal import frame, account as old_account


def account(provider='bundled', **kw):
    a = old_account('sdge')
    a.update(actual_generation_provider=provider, sdge_city_san_diego=False,
        sdge_jurisdiction_confirmed=True, sdge_non_event_confirmed=True,
        sdge_baseline_kwh=270., sdge_baseline_confirmed=True, sdge_allocation_confirmed=True,
        sdge_pcia_vintage=2021,sdge_pcia_confirmed=True,sdge_sdcp_cohort=2021,
        sdge_generation_option={'bundled':'','sdcp':'poweron','cea':'cleanimpact'}[provider],
        sdge_generation_confirmed=True,sdge_ev_confirmed=True,sdge_storage_confirmed=True)
    a.update(kw)
    return a


BATTERY = dict(capacity_kWh=8.,energy_kWh=4.,SOC_min=.1,SOC_max=.9,
               max_charge_kw=2.,max_discharge_kw=2.,charge_efficiency=.95,discharge_efficiency=.95)


def test_august_bundled_dr1_hand_bill():
    # 1 kW constant for August: 155 on, 239 off, 350 super kWh.
    # 21 weekdays / 10 weekend days. Super=21*10+10*14=350.
    f=frame('2026-08-01','2026-08-31')
    b=bill('sdge_tou-dr1',f,account(),'2026-08-01','2026-08-31')
    gen=155*.35943+239*.13229+350*.04241
    udc=744*.32601
    wf=744*.00591
    baseline=-351*.10702
    assert b['line_items']['generation_charge']==pytest.approx(gen)
    assert b['line_items']['baseline_credit']==pytest.approx(baseline)
    assert b['total']==pytest.approx(udc+wf+gen+baseline+31*.79343+.011*wf+744*.0013)
    assert b['amount_due']==b['total'] and b['credit_balance']==0
    assert sum(b['line_items'].values())==pytest.approx(b['total'])
    assert b['rate_versions'][0]['version_id']=='sdge-TOU-DR1-2026-08-01'


def test_sdcp_replaces_generation_with_pcia_separate_and_no_duplicate_fees():
    # Thursday August 6: 5 on, 9 off, 10 super kWh at 1 kW.
    b=bill('sdge_tou-dr1',frame('2026-08-06','2026-08-06'),
           account('sdcp',sdge_baseline_kwh=9.),'2026-08-06','2026-08-06')
    imputed=5*.35943+9*.13229+10*.04241
    gen=5*.29579+9*.08635+10*.01
    lines=b['line_items']
    assert lines['generation_charge']==pytest.approx(gen)
    assert lines['pcia']==pytest.approx(24*.03348)  # August vintage 2021.
    assert lines['mcam']==0
    assert lines['franchise_fee_equivalent']==pytest.approx(.011*(imputed+24*.00591))
    assert lines['state_energy_surcharge']==pytest.approx(24*.0003)
    assert lines['state_regulatory_fee']==pytest.approx(24*.001)
    assert len(b['rate_versions'])==2


@pytest.mark.parametrize('option,premium,relief',[('cleanimpact',0.,.03871),('cleanimpactplus',.001,0.),('greenimpact',.0075,0.)])
def test_cea_relief_and_premium_distinct_from_sdge_fees(option,premium,relief):
    a=account('cea',sdge_generation_option=option)
    b=bill('sdge_ev-tou-5',frame('2026-08-06','2026-08-06'),a,'2026-08-06','2026-08-06')
    l=b['line_items'];gen=5*.51684+9*.15975+10*.04961
    assert l['generation_charge']==pytest.approx(gen)
    assert l['generation_premium']==pytest.approx(24*premium)
    assert l['generation_relief_credit']==pytest.approx(-24*relief)
    assert l['mcam']==pytest.approx(24*.00006)
    assert l['baseline_credit']==0
    assert l['franchise_fee_equivalent']==pytest.approx(.011*(5*.48396+9*.17818+10*.08385+24*.00591))


def test_power100_premium_does_not_change_imputed_franchise_charge():
    f=frame('2026-08-06','2026-08-06')
    results=[bill('sdge_tou-dr1',f,account('sdcp',sdge_generation_option=o),'2026-08-06','2026-08-06') for o in ['poweron','powerbase','power100']]
    assert results[2]['total']-results[0]['total']==pytest.approx(24*.01)
    assert len({x['line_items']['franchise_fee_equivalent'] for x in results})==1
    assert results[1]['total']<results[0]['total']


def test_generation_cohort_not_silently_assumed_from_pcia():
    f=frame('2026-08-06','2026-08-06')
    bills=[bill('sdge_tou-dr1',f,account('sdcp',sdge_sdcp_cohort=c),'2026-08-06','2026-08-06') for c in [2021,2022]]
    assert bills[1]['line_items']['generation_charge']==pytest.approx(5*.30138+9*.09194+10*.01)
    assert bills[0]['line_items']['pcia']==bills[1]['line_items']['pcia']


def test_zero_usage_fixed_charge_and_city_fee_no_minimum_fabricated():
    f=frame('2026-08-06','2026-08-06',kw=0.)
    b=bill('sdge_tou-dr1',f,account(sdge_city_san_diego=True),'2026-08-06','2026-08-06')
    assert b['total']==pytest.approx(.79343*1.0578)
    assert b['line_items']['state_regulatory_fee']==0


def test_climate_credit_applied_once_after_fees_does_not_change_dispatch():
    f=frame('2026-08-06','2026-08-06')
    a=account();b=account(climate_credit_amount=60.,climate_credit_confirmed=True)
    first=optimize('sdge_tou-dr1',f,a,'2026-08-06','2026-08-06',BATTERY,0.)
    second=optimize('sdge_tou-dr1',f,b,'2026-08-06','2026-08-06',BATTERY,0.)
    assert first['bill']['total']-second['bill']['total']==pytest.approx(60.,abs=1e-5)
    np.testing.assert_allclose(first['dispatch'].grid_import_kw,second['dispatch'].grid_import_kw,atol=1e-4)
    assert second['bill']['credit_balance']>0


def test_dated_boundary_changes_every_component_and_allocates_cycle_baseline():
    f=frame('2026-07-31','2026-08-01')
    a=account('sdcp',sdge_baseline_kwh=18.)
    b=bill('sdge_tou-dr1',f,a,'2026-07-31','2026-08-01')
    assert b['line_items']['energy_charge']==pytest.approx(24*.32948+24*.32601)
    assert b['line_items']['baseline_credit']==pytest.approx(-11.7*(.10663+.10702))
    assert b['line_items']['pcia']==pytest.approx(24*(.03564+.03348))
    assert len(b['rate_versions'])==3
    assert b['line_items']['fixed_charge']==pytest.approx(2*.79343)


def test_baseline_below_allowance_only_credits_imports():
    f=frame('2026-08-06','2026-08-06',kw=.1)
    b=bill('sdge_tou-dr2',f,account(sdge_baseline_kwh=9.),'2026-08-06','2026-08-06')
    assert b['line_items']['baseline_credit']==pytest.approx(-2.4*.10702)


@pytest.mark.parametrize('day,expected',[('2026-08-06',['super','off','super','off','on','off']),
                                      ('2026-08-08',['super','super','super','off','on','off']),
                                      ('2026-09-07',['super','super','super','off','on','off'])])
def test_clock_time_weekday_weekend_holiday_boundaries(day,expected):
    idx=pd.DatetimeIndex([pd.Timestamp(day+' '+t,tz='America/Los_Angeles') for t in ['05:45','06:00','10:00','14:00','16:00','21:00']])
    assert periods(idx,'TOU-DR1').tolist()==expected
    assert periods(idx,'EV-TOU-5').tolist()==expected
    assert periods(idx,'TOU-DR2').tolist()==['off','off','off','off','on','off']


@pytest.mark.parametrize('day,n',[('2026-03-08',92),('2026-11-01',100)])
def test_actual_clock_dst_rules_do_not_fabricate_intervals(day,n):
    # Calendar helper only: these dates remain outside executable bill coverage.
    idx=frame(day,day).timestamp
    assert len(idx)==n
    assert len(periods(pd.DatetimeIndex(idx),'TOU-DR1'))==n
    with pytest.raises(ValueError):bill('sdge_tou-dr1',frame(day,day),account(),day,day)


@pytest.mark.parametrize('change',[
    {'actual_generation_provider':'unknown'}, {'sdge_pcia_vintage':True},
    {'sdge_sdcp_cohort':2020}, {'sdge_pcia_confirmed':False},
    {'sdge_generation_option':'greenimpact'}, {'sdge_generation_confirmed':False},
    {'sdge_city_san_diego':True}, {'sdge_city_san_diego':'no'},
    {'local_tax_percent':5}, {'sdge_non_event_confirmed':False},
    {'sdge_baseline_confirmed':False}, {'sdge_baseline_kwh':float('nan')},
    {'sdge_allocation_confirmed':False}, {'solar_program':'sce_nbt'},
    {'climate_credit_amount':30}, {'voltage':'primary'}, {'care':True},
])
def test_ambiguous_or_unsupported_account_rejected(change):
    with pytest.raises(ValueError):eligibility('sdge_tou-dr1',account('sdcp',**change),'2026-08-01','2026-08-31')


@pytest.mark.parametrize('start,end',[('2026-05-31','2026-06-01'),('2026-10-11','2026-10-12'),('2026-08-01','2026-07-31'),('2026-06-01','2026-07-15')])
def test_unverified_dates_and_multiple_cycles_rejected(start,end):
    with pytest.raises(ValueError):eligibility('sdge_tou-dr1',account(),start,end)


def test_export_and_unqualified_ev_and_storage_rejected():
    f=frame('2026-08-06','2026-08-06').assign(grid_export_kw=.1)
    with pytest.raises(ValueError,match='Export'):bill('sdge_tou-dr1',f,account(),'2026-08-06','2026-08-06')
    with pytest.raises(ValueError,match='EV-TOU-5'):eligibility('sdge_ev-tou-5',account(sdge_ev_confirmed=False),'2026-08-01','2026-08-31')
    with pytest.raises(ValueError,match='storage'):optimize('sdge_tou-dr1',f,account(sdge_storage_confirmed=False),'2026-08-06','2026-08-06',BATTERY,0.)


@pytest.mark.parametrize('key',['sdge_tou-dr1','sdge_tou-dr2','sdge_ev-tou-5'])
@pytest.mark.parametrize('provider',['bundled','sdcp','cea'])
def test_dispatch_reconciles_all_plans_and_providers(key,provider):
    f=frame('2026-07-31','2026-08-01')
    f['native_load_kw']=np.where((f.timestamp.dt.hour>=16)&(f.timestamp.dt.hour<21),2.,.5)
    a=account(provider,sdge_baseline_kwh=18.)
    r=optimize(key,f,a,'2026-07-31','2026-08-01',BATTERY,0.)
    assert r['bill']['total']<r['baseline_bill']['total']-.01
    assert abs(r['objective_gap'])<.02
    last=r['dispatch'].iloc[-1]
    assert last.energy_kWh+.25*(last.battery_charge_kw*.95-last.battery_discharge_kw/.95)==pytest.approx(4.,abs=1e-5)
    assert r['dispatch'].grid_import_kw.min()>=-1e-7
    mask=(r['dispatch'].timestamp.dt.hour>=16)&(r['dispatch'].timestamp.dt.hour<21)
    assert r['dispatch'].loc[mask,'grid_import_kw'].sum()<f.loc[mask,'native_load_kw'].sum()
    assert r['degradation_cost']==0


def test_numerical_and_convex_baseline_cost_identical_above_and_below_cap():
    import cvxpy as cp
    for kw in (.1,2.):
        f=frame('2026-07-31','2026-08-01',kw=kw);idx=pd.DatetimeIndex(f.timestamp)
        a=account('cea',sdge_baseline_kwh=18.)
        numerical=charge_lines('sdge_tou-dr1',idx,f.grid_import_kw.to_numpy(),a)
        symbolic=charge_lines('sdge_tou-dr1',idx,cp.Constant(f.grid_import_kw.to_numpy()),a,convex=True)
        assert sum(x.value if hasattr(x,'value') else x for x in symbolic.values())==pytest.approx(sum(numerical.values()))


def test_source_versions_tile_only_verified_window():
    for plan in RATE_PLANS.values():
        plan.require_coverage(pd.Timestamp('2026-06-01').date(),pd.Timestamp('2026-10-11').date())
        assert all(v.data['source']['sha256'] and v.data['source']['url'].startswith('https://www.sdge.com/') for v in plan.versions)
