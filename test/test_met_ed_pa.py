"""Independent Met-Ed columns of adopted FEPA leaves, 2025–2026.

Literal source values below never come from runtime rates. January GS is a
verified subtotal; the prior-refund tax adjustment remains unknown. Source
arithmetic is not calibration to an actual customer invoice.
"""
from copy import deepcopy
from decimal import Decimal as D, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import met_ed_pa as me
from src.billing.regional_math import BillingMath
from src.timeseries import build_interval_index

ROOT = Path(__file__).resolve().parents[1]
MONTHS = [f'2025-{m:02d}-01' for m in range(1,13)] + [f'2026-{m:02d}-01' for m in range(1,7)] + ['2026-10-01']
JAN_GS_GAP = 'january_2025_refund_prior_sales_tax_adjustment'


def fixture(plan='RS', day='2026-06-01'):
    a = me.hypothetical_defaults(plan, day=day)
    idx = build_interval_index(a['billing_month'], a['bill_date'], 'America/New_York', 15).index
    return a, idx


def power(idx, energy=1000., peak=None):
    p = np.full(len(idx), energy*4/len(idx))
    if peak is not None:
        p[0] = peak
        p[1:] = (energy*4-peak)/(len(idx)-1)
    return p


def bill(plan='RS', day='2026-06-01', energy=1000., state=None, account=None, peak=None):
    a, idx = fixture(plan, day)
    if account is not None:
        a = account
    me.validate_account(a, idx)
    me.validate_state(a, idx, state=state)
    return me.charge_lines(idx, power(idx, energy, peak), np.zeros(len(idx)), a, math=BillingMath(idx), state=state)


def literal_prices(day, plan):
    # Met-Ed base Supp14 pp15/17; NOT neighboring PennPower/WestPenn columns.
    rs = plan == 'RS'
    yr25 = day < '2026-01-01'
    prejun = day < '2025-06-01'
    june26 = day >= '2026-06-01'
    ptc = ('.11011' if rs else '.11048') if prejun else (('.11903' if rs else '.11574') if day < '2025-12-01' else (('.12965' if rs else '.12931') if not june26 else ('.13951' if rs else '.12864')))
    dsic = '.0017' if '2025-04-01' <= day <= '2025-06-30' else ('.0012' if '2026-04-01' <= day <= '2026-06-30' else ('.0202' if day >= '2026-10-01' else '0'))
    return dict(customer='11.25' if rs else '23.78', distribution='.05138' if rs else '.05092', ptc=ptc,
        dss=('.00317' if rs else '.00052') if prejun else (('.00546' if rs else '.00208') if june26 else ('.00123' if rs else '-.00018')),
        eec=('.00176' if rs else '.00392') if prejun else (('.00215' if rs else '.00178') if june26 else ('.00210' if rs else '.00322')),
        usc=('0' if not rs else ('.00612' if day < '2025-08-01' else ('.00900' if yr25 else '.01283'))),
        smt=('.13' if rs else '.58') if yr25 else ('.06' if rs else '-.04'),
        spv='-.00001' if prejun else '0', tcja='.0112' if '2025-07-01' <= day <= '2025-12-31' else '0',
        dsic=dsic, stas='.0002' if yr25 else '-.0002', refund=('-6.53' if rs else '-4.18') if day[:7] == '2025-01' else '0')


def independent_lines(day, plan, energy, represented=False):
    p = {k:D(v) for k,v in literal_prices(day, plan).items()}
    e = D(str(energy))
    base = p['customer'] + e*p['distribution']
    out = dict(distribution_customer=p['customer'], distribution_energy=e*p['distribution'],
        supply=e*p['ptc'], default_service_support=e*p['dss'], energy_efficiency=e*p['eec'],
        universal_service=e*p['usc'], smart_meter=p['smt'], solar_photovoltaic_requirement=e*p['spv'], tcja=base*p['tcja'])
    # DSIC excludes PTC supply, but includes other current non-supply components.
    out['distribution_dsic'] = sum(v for k,v in out.items() if k != 'supply')*p['dsic']
    out['state_tax_adjustment'] = sum(out.values())*p['stas']
    current = sum(out.values())
    out['sales_tax'] = D(0) if plan == 'RS' else current*D('.06')
    out['january_refund'] = D(0) if represented else p['refund']
    if plan == 'RS':
        out['distribution_special_demand'] = D(0)
    return out


@pytest.mark.parametrize('plan', ['RS','GS-S'])
@pytest.mark.parametrize('day', MONTHS)
def test_all_supported_months_independent_itemized_source_arithmetic(plan, day):
    got = bill(plan, day)
    expected = {k:float(v) for k,v in independent_lines(day, plan, 1000).items()}
    assert got['lines'] == pytest.approx(expected, abs=1e-9)
    assert sum(got['lines'].values()) == pytest.approx(sum(expected.values()), abs=1e-8)
    jan_gs = day == '2025-01-01' and plan == 'GS-S'
    assert got['is_complete_bill'] is (not jan_gs)
    assert got['excluded_components'] == ([JAN_GS_GAP] if jan_gs else [])
    assert got['rate_evidence_status'] == 'verified' and got['rate_assumptions'] == []
    m = got['metrics']
    assert m['raw_import_kwh'] == pytest.approx(1000, abs=1e-8)
    assert m['quantity_basis'] == 'raw_import_energy_no_unsourced_quantity_rounding'
    assert m['objective_scope'] == 'unrounded_verified_component_charges'
    assert m['rounded_cash_optimum_claimed'] is False
    assert m['additional_grt_percentage_applied'] is False
    assert m['monthly_charge_factor'] == 1. and m['partial_period_proration_applied'] is False
    assert m['current_charge_minimum_domain_verified'] is True
    assert not {'pjm_capacity','gross_receipts_tax','wholesale_energy','transmission','supply_administration'} & set(got['lines'])


@pytest.mark.parametrize('plan',['RS','GS-S'])
@pytest.mark.parametrize('day',['2025-01-01','2025-04-01','2025-07-01','2026-06-01'])
def test_percentage_order_and_separate_current_tax_prior_refund(plan, day):
    got = bill(plan, day); l = got['lines']; m = got['metrics']
    assert m['tcja_basis_usd'] == pytest.approx(l['distribution_customer'] + l['distribution_energy'])
    before_dsic = sum(v for k,v in l.items() if k not in {'supply','distribution_dsic','state_tax_adjustment','sales_tax','january_refund'})
    assert m['dsic_basis_usd'] == pytest.approx(before_dsic)
    assert m['stas_basis_usd'] == pytest.approx(before_dsic + l['supply'] + l['distribution_dsic'])
    current = sum(v for k,v in l.items() if k not in {'sales_tax','january_refund'})
    assert m['current_tariff_before_sales_tax_usd'] == pytest.approx(current)
    assert l['sales_tax'] == pytest.approx(0 if plan == 'RS' else current*.06)
    if day == '2025-01-01':
        assert l['january_refund'] == (-6.53 if plan == 'RS' else -4.18)
        assert m['stas_fraction'] == .0002  # Supp15 supersedes same-effective Supp14.
        assert m['january_refund_sales_tax_status'] == ('not_applicable' if plan == 'RS' else 'unverified_excluded')
    if day == '2025-07-01':
        assert l['tcja'] > 0 and m['tcja_fraction'] == .0112
    if day == '2026-06-01':
        assert l['state_tax_adjustment'] < 0


@pytest.mark.parametrize('plan',['RS','GS-S'])
@pytest.mark.parametrize('day',['2025-01-01','2025-04-01','2026-06-01'])
def test_fixed_flow_numeric_symbolic_itemized_parity(plan,day):
    a,idx = fixture(plan,day); p = power(idx)
    numeric = bill(plan,day)
    x,y = cp.Variable(len(idx)), cp.Variable(len(idx))
    math = BillingMath(idx,convex=True,power_bound=25.)
    math.register_power(x,np.zeros(len(idx)),np.full(len(idx),25.))
    symbolic = me.charge_lines(idx,x,y,a,math=math)
    problem = cp.Problem(cp.Minimize(sum(symbolic['lines'].values())),[x==p,y==0,*math.constraints])
    problem.solve(solver='SCIPY')
    assert problem.status == cp.OPTIMAL
    expected = independent_lines(day,plan,1000)
    for key,value in symbolic['lines'].items():
        assert float(value.value if hasattr(value,'value') else value) == pytest.approx(float(expected[key]),abs=1e-8)
        assert numeric['lines'][key] == pytest.approx(float(expected[key]),abs=1e-8)
    assert symbolic['metrics']['rounded_cash_optimum_claimed'] is False


@pytest.mark.parametrize('plan',['RS','GS-S'])
def test_january_refund_once_adjacent_history_and_no_input_mutation(plan):
    jan = bill(plan,'2025-01-01'); saved = deepcopy(jan['next_state'])
    feb = bill(plan,'2025-02-01',state=saved)
    assert saved == jan['next_state']
    assert jan['next_state']['january_refund_applied'] is True
    assert feb['lines']['january_refund'] == 0.
    assert feb['next_state']['through_month'] == '2025-02-01'
    a,idx = fixture(plan,'2025-01-01'); a['refund_represented_before_study'] = True
    prior = bill(plan,'2025-01-01',account=a)
    assert prior['lines']['january_refund'] == 0.
    assert prior['metrics']['january_refund_applied_this_cycle'] is False
    assert prior['is_complete_bill'] is (plan == 'RS')
    state = dict(january_refund_applied=True,through_month='2024-12-01')
    if plan == 'GS-S':state['gs_qualification_upper_bound_kwh']=1500.
    else:state['rs_peak_upper_bound_kw']=25.
    a['refund_represented_before_study']=False
    got = me.charge_lines(idx,power(idx),np.zeros(len(idx)),a,math=BillingMath(idx),state=state)
    assert got['lines']['january_refund'] == 0.


@pytest.mark.parametrize('change',[
    dict(january_refund_applied=1),dict(through_month='2026-04-01'),dict(through_month='2026-06-01'),
    dict(opening_bank_kwh=0),dict(gs_qualification_upper_bound_kwh=True),dict(gs_qualification_upper_bound_kwh=1500.001),
    dict(gs_qualification_upper_bound_kwh=float('nan')),
])
def test_gs_carried_state_rejects_gap_reset_boolean_quantity_and_unknown_keys(change):
    a,idx = fixture('GS-S')
    state = dict(january_refund_applied=True,through_month='2026-05-01',gs_qualification_upper_bound_kwh=1500.)
    with pytest.raises(ValueError):me.validate_state(a,idx,{**state,**change})


def test_gs_conservative_native_qualification_envelope_not_pv_reset_or_demand_rule():
    got = bill('GS-S',energy=100.)
    assert got['next_state']['gs_qualification_upper_bound_kwh'] == 1500.
    assert got['metrics']['gs_qualification_envelope_kwh'] == 1500.
    assert bill('GS-S',energy=1500.)['metrics']['raw_import_kwh'] == pytest.approx(1500)
    with pytest.raises(ValueError):bill('GS-S',energy=1500.001)
    a,idx = fixture('GS-S'); a['gs_history_through_month']='2026-04-01'
    with pytest.raises(ValueError):me.validate_state(a,idx)
    assert got['lines']['universal_service'] == 0.
    assert not {'distribution_demand','transmission_demand','gs_peak_kw'} & set(got['lines'])


def test_zero_gs_2026_current_minimum_domain_rejects_without_invented_purchase_constraint():
    with pytest.raises(ValueError,match='inactive domain'):bill('GS-S',energy=0.)
    a,idx = fixture('GS-S'); x,y=cp.Variable(len(idx)),cp.Variable(len(idx))
    math=BillingMath(idx,convex=True,power_bound=3.)
    math.register_power(x,np.zeros(len(idx)),np.full(len(idx),3.))
    symbolic=me.charge_lines(idx,x,y,a,math=math)
    problem=cp.Problem(cp.Minimize(sum(symbolic['lines'].values())),[x==0,y==0,*math.constraints])
    problem.solve(solver='SCIPY')
    assert problem.status == cp.OPTIMAL  # Numeric domain guard, not forced additional imports.


@pytest.mark.parametrize('energy',[.005,600.,1000.005,1500.])
def test_raw_quantities_no_borrowed_rounding_or_block_prices(energy):
    got=bill('RS',energy=energy)
    assert got['metrics']['raw_import_kwh'] == pytest.approx(energy,abs=1e-10)
    assert got['lines']['distribution_energy'] == pytest.approx(energy*.05138,abs=1e-10)
    assert got['lines']['supply'] == pytest.approx(energy*.13951,abs=1e-10)


@pytest.mark.parametrize('day,hours',[('2025-02-01',672),('2025-03-01',743),('2025-11-01',721),('2026-03-01',743)])
def test_complete_calendar_cycles_keep_dst_elapsed_energy_and_fixed_monthly_charge(day,hours):
    a,idx=fixture('RS',day)
    review=me.cycle_review(a,idx)
    assert len(idx)==hours*4 and review['elapsed_hours']==hours
    assert review['monthly_charge_factor']==1. and review['partial_period_proration_applied'] is False
    assert bill('RS',day)['lines']['distribution_customer']==11.25


@pytest.mark.parametrize('kind',['missing','duplicate','naive','utc','reverse','hourly','shifted','partial'])
def test_malformed_or_partial_interval_data_rejects(kind):
    a,idx=fixture()
    bad={'missing':lambda:idx.delete(42),'duplicate':lambda:idx.insert(42,idx[42]),'naive':lambda:idx.tz_localize(None),
        'utc':lambda:idx.tz_convert('UTC'),'reverse':lambda:idx[::-1],'hourly':lambda:idx[::4],
        'shifted':lambda:idx+pd.Timedelta(minutes=15),'partial':lambda:idx[96:]}[kind]()
    with pytest.raises(ValueError):me.cycle_review(a,bad)


@pytest.mark.parametrize('day',['2024-12-31','2026-07-01','2026-08-01','2026-09-30','2026-11-01','2027-01-01','2026-6-1','2026-02-30',None])
def test_rate_gaps_and_bad_iso_dates_have_no_current_price_fallback(day):
    with pytest.raises(ValueError):me.rates_on(day)


def test_valid_november_dst_grid_still_rejects_unsupported_rate_coverage():
    a,idx=fixture('RS','2026-11-01')
    assert len(idx)==721*4
    with pytest.raises(ValueError):me.cycle_review(a,idx)


@pytest.mark.parametrize('change',[
    dict(eligibility_confirmed=False),dict(ordinary_service_confirmed=False),dict(full_monthly_charges_confirmed=False),
    dict(ptc_review_confirmed=False),dict(no_special_rates_confirmed=False),dict(supply_source=''),dict(tax_source=''),dict(cycle_source=''),
    dict(supply='retail_supplier'),dict(export_mode='net_metering'),dict(tax_jurisdiction='philadelphia'),dict(tax_exempt=True),
    dict(solely_residential_use_confirmed=False),dict(phase='three'),dict(voltage='primary'),dict(voltage_v=120.),dict(power_factor=.9),
    dict(meter_count=2),dict(meter_count=True),dict(service_line_count=True),dict(opening_credit_usd=1.),dict(demand_interval_minutes=30),
    dict(rate_evidence_mode='provisional'),dict(provisional_assumptions_accepted=True),dict(refund_represented_before_study=1),
    dict(peak_load_share_kw=0),dict(gs_qualification_upper_bound_kwh=0),dict(bill_date='2026-06-29'),dict(billing_month='2026-06-02'),
])
def test_separate_district_supply_tax_meter_cycle_and_eligibility_facts(change):
    a,idx=fixture()
    with pytest.raises(ValueError):me.validate_account({**a,**change},idx)


@pytest.mark.parametrize('change',[
    dict(gs_small_confirmed=False),dict(gs_qualification_source=''),dict(gs_qualification_upper_bound_kwh=1500.01),
    dict(gs_qualification_upper_bound_kwh=True),dict(gs_qualification_upper_bound_kwh=float('inf')),
    dict(gs_qualification_upper_bound_kwh=-1),dict(metering='metered_demand'),dict(solely_residential_use_confirmed=True),
])
def test_gs_company_qualification_is_not_synthesized_from_import_energy(change):
    a,idx=fixture('GS-S')
    with pytest.raises(ValueError):me.validate_account({**a,**change},idx)


@pytest.mark.parametrize('change',[
    dict(rs_special_demand_inactive_confirmed=False),dict(rs_prior_11_peak_upper_bound_kw=25.01),
    dict(rs_prior_11_peak_upper_bound_kw=True),dict(rs_demand_source=''),
])
def test_residential_special_demand_prior11_ratchet_requires_independent_inactive_facts(change):
    a,idx=fixture()
    with pytest.raises(ValueError):me.validate_account({**a,**change},idx)


def test_residential_peak25_inactive_bound_history_and_no_pv_history_reset():
    got=bill(peak=25.)
    assert got['lines']['distribution_special_demand']==0.
    assert got['next_state']['rs_peak_upper_bound_kw']==25.
    with pytest.raises(ValueError):bill(peak=25.001)
    a,idx=fixture();a['rs_history_through_month']='2026-04-01'
    with pytest.raises(ValueError):me.validate_state(a,idx)
    state=dict(january_refund_applied=True,through_month='2026-05-01',rs_peak_upper_bound_kw=25.01)
    with pytest.raises(ValueError):me.validate_state(me.hypothetical_defaults('RS'),idx,state)


@pytest.mark.parametrize('plan',['RS','GS-S'])
@pytest.mark.parametrize('change',[dict(der_ordinary_service_confirmed=False),dict(der_activation_date='2026-06-02'),dict(der_activation_date=''),dict(der_eligibility_source='')])
def test_der_needs_active_ordinary_renewable_approval_not_only_pv_checkbox(plan,change):
    a,idx=fixture(plan)
    with pytest.raises(ValueError):me.validate_account({**a,**change},idx,equipment=dict(pv=True,battery=True,pv_ac_kw=4.,pv_dc_kw=4.,battery_kw=3.,renewable_only_charging=True,no_battery_export=True))


@pytest.mark.parametrize('equipment',[
    dict(pv=False,battery=True,battery_kw=3.),dict(pv=True,battery=True,renewable_only_charging=False,no_battery_export=True),
    dict(pv=True,battery=True,renewable_only_charging=True,no_battery_export=False),dict(pv=True,pv_ac_kw=26.),
])
def test_standalone_or_grid_charged_storage_and_capacity_outside_declared_study_domain_rejects(equipment):
    a,idx=fixture()
    with pytest.raises(ValueError):me.validate_account(a,idx,equipment=equipment)


@pytest.mark.parametrize('plan',['RS','GS-S'])
def test_spv_credit_applies_to_small_classes_even_with_approved_der_and_exports_reject(plan):
    a,idx=fixture(plan,'2025-05-01')
    equipment=dict(pv=True,battery=True,pv_ac_kw=4.,pv_dc_kw=4.,battery_kw=3.,renewable_only_charging=True,no_battery_export=True)
    me.validate_account(a,idx,equipment=equipment)
    assert bill(plan,'2025-05-01',account=a)['lines']['solar_photovoltaic_requirement']==pytest.approx(-.01)
    exports=np.zeros(len(idx));exports[12]=.01
    with pytest.raises(ValueError):me.charge_lines(idx,power(idx),exports,a,math=BillingMath(idx))


def test_replacement_dss_positive_tcja_and_source_pins_not_initial_superseded_rates():
    for plan,price in [('RS',.00123),('GS-S',-.00018)]:
        r=me.rates_on('2025-06-01',plan)
        assert r['dss_kwh']==price
        source=r['source_versions']['DSS']['source']
        assert source['original_sha256']=='950266135e6348aac8d173a794aa6117e65868cde47636a71a9c0922e17d410b'
        assert source['physical_page']==213 and 'Fourth' in source['revision']
    assert me.rates_on('2025-07-01')['tcja_fraction']==.0112
    assert me.rates_on('2025-01-01')['stas_fraction']==.0002
    assert me.rates_on('2026-01-01')['stas_fraction']==-.0002


@pytest.mark.parametrize('day,rs,gs',[
    ('2025-05-31',.11011,.11048),('2025-06-01',.11903,.11574),('2025-11-30',.11903,.11574),
    ('2025-12-01',.12965,.12931),('2026-05-31',.12965,.12931),('2026-06-01',.13951,.12864),('2026-10-31',.13951,.12864),
])
def test_filed_ptc_and_official_may31_insert_prices_include_admin_and_grt_once(day,rs,gs):
    assert me.rates_on(day,'RS')['ptc_kwh']==rs
    assert me.rates_on(day,'GS-S')['ptc_kwh']==gs
    if day=='2026-05-31':
        ptc=me.rates_on(day)['source_versions']['PTC']
        assert ptc['may31_corroboration']['original_sha256']=='017f0010a62c102429c17a3cfd8da85b22c2ef98f2faad9942df8a63b01a5877'
        assert 'May30' in ptc['may31_source']


def test_checked_in_source_excerpts_hashes_and_every_runtime_component_original_pin():
    ledger=json.loads((ROOT/'docs/utility_sources/met_ed_pa/sources.json').read_text())
    assert ledger['source_scope']['utility_key']=='firstenergy_pa_met_ed'
    records=ledger['records'];bysha={r['original_sha256']:r for r in records}
    assert len(bysha)==len(records)  # Deduplicated originals, not an assumed stream record count.
    assert 'b74772efdc7b2c5a7bb527f6b34b007826b8e17a1e9efd387d6f5777f1e0ae99' in bysha
    assert '665736ea46b7860651226605624c298b6990e3c0581166e543ccf27bd25b8f9d' in bysha
    for record in records:
        for excerpt in record['checked_in_excerpts']:
            assert hashlib.sha256((ROOT/excerpt['path']).read_bytes()).hexdigest()==excerpt['sha256']
    for plan in ['RS','GS-S']:
        for day in MONTHS:
            versions=me.rates_on(day,plan)['source_versions']
            for component in versions.values():
                pin=component['source'];record=bysha[pin['original_sha256']]
                assert pin['url'] in record['urls']
                assert pin['physical_page']>=1
                assert hashlib.sha256((ROOT/pin['excerpt_path']).read_bytes()).hexdigest()==pin['excerpt_sha256']
    for plan,page,leaf in [('RS',15,'61'),('GS-S',17,'65')]:
        source=me.rates_on('2025-01-01',plan)['source_versions']['base']['source']
        assert source['physical_page']==page and source['printed_page']==leaf


@pytest.mark.parametrize('plan',['RS','GS-S'])
def test_regional_component_currency_rounding_retains_raw_source_arithmetic_and_scope(plan):
    from src.billing.regional import calculate_cycle
    a,idx=fixture(plan,'2025-01-01');energy=1000.005
    got=calculate_cycle('firstenergy_pa_met_ed',idx,power(idx,energy),np.zeros(len(idx)),a)
    expected=independent_lines('2025-01-01',plan,energy)
    cents={k:float(v.quantize(D('.01'),rounding=ROUND_HALF_UP)) for k,v in expected.items()}
    assert got['unrounded_lines']==pytest.approx({k:float(v) for k,v in expected.items()},abs=1e-9)
    assert got['lines']==cents
    assert got['unrounded_total_usd']==pytest.approx(float(sum(expected.values())),abs=1e-8)
    assert got['total_usd']==float(sum(D(str(v)) for v in cents.values()))
    assert abs(got['total_usd']-got['unrounded_total_usd'])<=got['rounding_bound_usd']
    assert got['is_complete_bill'] is (plan=='RS')
    assert got['metrics']['rounded_cash_optimum_claimed'] is False
