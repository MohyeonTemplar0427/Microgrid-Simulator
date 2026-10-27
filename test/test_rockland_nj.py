"""Independent Rockland NJ October2026 ordinary SC1/SC2 source arithmetic.

BPU3current leaves50,56,58,61,65D,82/82.1/83/84,87–91. Prices are
literal published taxinclusive values; no production rates compute expectations.
The official PTC is a different-vintage shopping-credit benchmark, not an
October wholeinvoice. Its allkWh-only SC2nondemand row corroborates units.
"""
from copy import deepcopy
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import rockland_nj as re
from src.billing.regional_math import BillingMath
from src.timeseries import build_interval_index

UTILITY='rockland_electric_new_jersey'
ROOT=Path(__file__).resolve().parents[1]
CURRENT_SHA='3721612c3d326d280467ba05cbe581f2f0253adef57a88ab4035eb2c265dd841'
SBC=dict(dsm_cep='.003590',universal_service_fund='.002870',lifeline='.000715',uncollectible_expense='.000521')
RGGI=dict(low_income_audit_ii='-.000332',low_income_audit_iii='.000212',srec_i='-.000448',srec_ii='0',trec='.002941',susi='.000307',clean_energy_act_i='.002578',clean_energy_act_ii='.001410',community_solar='.000199')


def fixture(plan='SC1'):
    a=re.hypothetical_defaults(plan,day='2026-10-01')
    a.update(billing_month='2026-10-01',bill_date='2026-10-31')
    idx=build_interval_index('2026-10-01','2026-10-31','America/New_York',15).index
    return a,idx


def power_for_energy(idx,energy=1000.,peak=None):
    p=np.full(len(idx),energy*4/len(idx))
    if peak is not None:
        p[0]=peak;p[1:]=(energy*4-peak)/(len(idx)-1)
    return p


def independent_october(plan,energy):
    e=D(str(energy));res=plan=='SC1'
    return dict(customer=D('6' if res else '16'),distribution=e*D('.06886' if res else '.03601'),
        distribution_adjustment=e*D('-.01416') if res else D(0),
        generation=e*D('.14435' if res else '.11305'),transmission=e*D('.01809' if res else '.00579'),
        transmission_surcharge=e*D('.02187' if res else '.01247'),reconciliation=e*D('-.02000'),
        SBC=e*D('.007696'),RGGI=e*D('.006867'),CIP=e*D('.006170' if res else '-.001480'),ZEC=e*D('-.004265'))


def bill(plan='SC1',energy=1000.,peak=None,account=None):
    a,idx=fixture(plan);a=a if account is None else account
    re.validate_account(a,idx);re.validate_state(a,idx)
    return re.charge_lines(idx,power_for_energy(idx,energy,peak),np.zeros(len(idx)),a,math=BillingMath(idx))


def comparable(lines):
    mapping=dict(customer='distribution_customer',distribution='distribution_energy',
        distribution_adjustment='distribution_adjustment',generation='bgs_generation_energy',
        transmission='transmission_service',transmission_surcharge='transmission_surcharge_bundled',
        reconciliation='bgs_reconciliation',CIP='conservation_incentive',ZEC='zero_emission_certificate')
    got={k:lines[v] for k,v in mapping.items()}
    got['SBC']=sum(v for k,v in lines.items() if k.startswith('sbc_'))
    got['RGGI']=sum(v for k,v in lines.items() if k.startswith('rggi_'))
    return got


@pytest.mark.parametrize('plan',['SC1','SC2'])
@pytest.mark.parametrize('energy',[0.,599.995,600.,600.005,925.,1000.004,1500.])
def test_october_independent_full_stack_and_published_sbc_rggi_aggregates(plan,energy):
    got=bill(plan,energy)
    expected={k:float(v) for k,v in independent_october(plan,energy).items()}
    assert comparable(got['lines'])==pytest.approx(expected,abs=1e-9)
    assert sum(got['lines'].values())==pytest.approx(sum(expected.values()),abs=1e-8)
    assert sum(map(D,SBC.values()))==D('.007696')
    assert sum(map(D,RGGI.values()))==D('.006867')
    sbc_expected=dict(sbc_dsm_cep='.003590',sbc_usf='.002870',sbc_lifeline='.000715',sbc_uncollectible='.000521')
    for key,price in sbc_expected.items():assert got['lines'][key]==pytest.approx(energy*float(price),abs=1e-9)
    for key,price in RGGI.items():assert got['lines']['rggi_'+key]==pytest.approx(energy*float(price),abs=1e-9)
    assert got['is_complete_bill'] is True and got['excluded_components']==[]
    assert got['rate_evidence_status']=='verified' and got['rate_assumptions']==[]
    m=got['metrics']
    assert m['raw_import_kwh']==pytest.approx(energy,abs=1e-9)
    assert m['quantity_basis']=='raw_import_energy_no_unsourced_quantity_rounding'
    assert m['monthly_charge_factor']==1. and m['partial_period_proration_applied'] is False
    assert m['whole_cycle_block_kwh']==(600. if plan=='SC1' else None)
    assert m['monthly_minimum_usd']==(6. if plan=='SC1' else 16.)
    assert m['minimum_inactive_domain_verified'] is True
    assert m['additional_tax_percentage_applied'] is False
    assert m['objective_scope']=='unrounded_ordinary_component_charges' and m['rounded_cash_optimum_claimed'] is False
    assert got['next_state']=={}


@pytest.mark.parametrize('plan,total',[('SC1',241.478),('SC2',172.138)])
def test_literal_1000kwh_october_totals_and_expired_or_included_components_not_duplicated(plan,total):
    got=bill(plan)
    assert sum(got['lines'].values())==pytest.approx(total,abs=1e-9)
    for key in ['temporary_tax_act_credit','infrastructure_investment_increment','residential_generation_capacity_deferral']:
        assert got['lines'][key]==0.
    assert not {'sales_tax','gross_receipts_tax','pjm_capacity','wholesale_energy','supply_administration','tec','reliability_must_run'} & set(got['lines'])
    if plan=='SC2':
        for key in ['distribution_demand','transmission_demand','bgs_generation_demand','ciep_standby_fee']:assert got['lines'][key]==0.


def test_winter600_block_preserves_raw_kwh_and_separate_residential_adjustment():
    # Both October winter prices are equal on each side; no claim summer tiers execute.
    low=bill(energy=599.995);edge=bill(energy=600.);high=bill(energy=600.005)
    for got,e in [(low,599.995),(edge,600.),(high,600.005)]:
        assert got['lines']['distribution_energy']==pytest.approx(e*.06886,abs=1e-10)
        assert got['lines']['distribution_adjustment']==pytest.approx(-e*.01416,abs=1e-10)
        assert got['lines']['bgs_generation_energy']==pytest.approx(e*.14435,abs=1e-10)
        assert got['metrics']['whole_cycle_block_kwh']==600.
    assert high['lines']['distribution_energy']-edge['lines']['distribution_energy']==pytest.approx(.005*.06886,abs=1e-10)


@pytest.mark.parametrize('plan,old_ptc,current_without_recon,delta',[
    ('SC1','.18425','.18431','.00006'),('SC2','.13129','.13131','.00002'),
])
def test_independent_published_ptc_vintage_is_not_backdated_into_october(plan,old_ptc,current_without_recon,delta):
    r=re.rates_on('2026-10-01',plan)
    l=r['linear_rates']
    actual=D(str(r['generation_energy'][0]))+D(str(l['transmission_service']))+D(str(l['transmission_surcharge_bundled']))
    assert actual==D(current_without_recon)
    assert actual-D(old_ptc)==D(delta)
    assert l['bgs_reconciliation']==-.02000
    # Price to compare excludes reconciliation and delivery, unlike the complete bill.
    assert float(actual+D(str(l['bgs_reconciliation'])))==pytest.approx(.16431 if plan=='SC1' else .11131,abs=1e-12)


def test_925kwh_base_case_impact_is_not_a_fabricated_october_invoice_fixture():
    # BPU2026basecase is an annualized March-rate comparison, before July16credit.
    assert D('261.94')-D('247.91')==D('14.03')
    actual=sum(bill(energy=925.)['lines'].values())
    assert actual==pytest.approx(223.81715,abs=1e-9)
    assert actual!=pytest.approx(261.94,abs=.01)


@pytest.mark.parametrize('plan',['SC1','SC2'])
@pytest.mark.parametrize('energy',[0.,600.005,1000.004])
def test_fixed_flow_numeric_symbolic_itemized_parity_and_no_forced_minimum_imports(plan,energy):
    a,idx=fixture(plan);p=power_for_energy(idx,energy)
    numeric=bill(plan,energy)
    x,y=cp.Variable(len(idx)),cp.Variable(len(idx))
    math=BillingMath(idx,convex=True,power_bound=4.)
    math.register_power(x,np.zeros(len(idx)),np.full(len(idx),4.))
    symbolic=re.charge_lines(idx,x,y,a,math=math)
    problem=cp.Problem(cp.Minimize(sum(symbolic['lines'].values())),[x==p,y==0,*math.constraints])
    problem.solve(solver='SCIPY')
    assert problem.status==cp.OPTIMAL
    for key,value in symbolic['lines'].items():
        assert float(value.value if hasattr(value,'value') else value)==pytest.approx(numeric['lines'][key],abs=1e-8)
    assert symbolic['metrics']['rounded_cash_optimum_claimed'] is False


def test_sc2_nondemand_is_utility_billing_assignment_not_borrowed10kw_or_rounding_rule():
    got=bill('SC2',peak=12.345)
    assert got['metrics']['actual_15_minute_peak_kw']==pytest.approx(12.345)
    assert got['lines']['distribution_demand']==got['lines']['transmission_demand']==got['lines']['bgs_generation_demand']==0.
    assert got['lines']['distribution_customer']==16.
    a,idx=fixture('SC2')
    assert 'peak_load_share_kw' not in a and 'contract_demand_kw' not in a and 'prior_11_actual_peak_upper_bound_kw' not in a
    for change in [dict(sc2_non_demand_confirmed=False),dict(sc2_classification_source=''),dict(metering='unmetered'),dict(metering='utility_no_meter')]:
        with pytest.raises(ValueError):re.validate_account({**a,**change},idx)


@pytest.mark.parametrize('change',[
    dict(eligibility_confirmed=False),dict(ordinary_service_confirmed=False),dict(full_monthly_charges_confirmed=False),
    dict(bgs_rscp_confirmed=False),dict(supply_eligibility_source=''),dict(no_ami_opt_out_fee_confirmed=False),
    dict(no_special_provisions_confirmed=False),dict(county='Sussex'),dict(service_division='western'),
    dict(supply='retail_supplier'),dict(export_mode='nem'),dict(tax_exempt=True),dict(cycle_source=''),dict(tax_source=''),
    dict(phase='three'),dict(voltage='primary'),dict(power_factor=.95),dict(meter_count=2),dict(meter_count=True),
    dict(service_line_count=True),dict(opening_credit_usd=1.),dict(demand_interval_minutes=30),dict(rate_evidence_mode='provisional'),
    dict(provisional_assumptions_accepted=True),
])
def test_account_jurisdiction_supplier_tax_meter_and_scope_facts_are_separate(change):
    a,idx=fixture()
    with pytest.raises(ValueError):re.validate_account({**a,**change},idx)


@pytest.mark.parametrize('flag',['peak_load_share_kw','gs_no_demand_meter_confirmed','prior_11_actual_peak_upper_bound_kw','bypass_eligibility'])
def test_no_foreign_utility_fields_or_external_bypass_flags(flag):
    a,idx=fixture('SC2')
    with pytest.raises(ValueError):re.validate_account({**a,flag:True},idx)


@pytest.mark.parametrize('plan',['SC1','SC2'])
@pytest.mark.parametrize('change',[dict(der_ordinary_service_confirmed=False),dict(der_activation_date='2026-10-02'),dict(der_activation_date=''),dict(der_eligibility_source='')])
def test_der_requires_executed_active_ordinary_configuration_approval(plan,change):
    a,idx=fixture(plan)
    with pytest.raises(ValueError):
        re.validate_account({**a,**change},idx,equipment=dict(pv=True,battery=True,pv_dc_kw=4.,pv_ac_kw=4.,battery_kw=3.))


def test_no_standalone_storage_and_retained_nondemand_assignment_for_pv_storage():
    a,idx=fixture('SC2')
    approved=dict(pv=True,battery=True,pv_dc_kw=4.,pv_ac_kw=4.,battery_kw=3.)
    re.validate_account(a,idx,equipment=approved)
    with pytest.raises(ValueError):re.validate_account({**a,'sc2_non_demand_confirmed':False},idx,equipment=approved)
    with pytest.raises(ValueError):re.validate_account(a,idx,equipment=dict(pv=False,battery=True,battery_kw=3.))
    with pytest.raises(ValueError):re.validate_account(a,idx,equipment=dict(pv=True,pv_dc_kw=25.1,pv_ac_kw=25.1))
    re.validate_account({**a,'der_ordinary_service_confirmed':False},idx,equipment=dict(pv=False,battery=False))


@pytest.mark.parametrize('state',[{'credit':0.},{'gs_history_peak_upper_bound_kw':5.,'through_month':'2026-09-01'},{'bank_kwh':1.}])
def test_no_opening_credit_or_foreign_demand_history_state(state):
    a,idx=fixture('SC2')
    with pytest.raises(ValueError):re.validate_state(a,idx,state=state)


def test_exports_reject_and_numeric_component_minimum_is_not_an_extra_fixed_fee():
    a,idx=fixture()
    with pytest.raises(ValueError,match='export'):
        re.charge_lines(idx,power_for_energy(idx),np.ones(len(idx))*.001,a,math=BillingMath(idx))
    for plan,minimum in [('SC1',6.),('SC2',16.)]:
        got=bill(plan,energy=0.)
        assert sum(got['lines'].values())==minimum
        assert got['metrics']['minimum_inactive_domain_verified'] is True


@pytest.mark.parametrize('day',['2025-01-01','2025-12-31','2026-07-16','2026-08-01','2026-09-30','2026-11-01','2027-01-01','2026-10-1','2026-02-29',None,20261001,True])
def test_unverified_history_future_or_malformed_dates_reject_without_backfill(day):
    with pytest.raises(ValueError):re.rates_on(day)


@pytest.mark.parametrize('day',['2026-10-01','2026-10-31'])
@pytest.mark.parametrize('plan',['SC1','SC2'])
def test_closed_october_edges_remain_one_winter_component_intersection(day,plan):
    r=re.rates_on(day,plan)
    assert r['season']=='winter'
    assert r['linear_rates']['bgs_reconciliation']==-.02
    assert r['distribution_adjustment']==((-.01416,)*2 if plan=='SC1' else (0.,0.))


def test_full_october_calendar_keeps_monthly_charges_and_reconciliation_bill_month_clock():
    a,idx=fixture();assert len(idx)==31*24*4
    review=re.cycle_review(a,idx)
    assert review['cycle_days']==31 and review['elapsed_hours']==744.
    assert review['monthly_charge_factor']==1. and review['partial_period_proration_applied'] is False
    assert 'billed in the month' in review['reconciliation_clock']
    for change in [dict(bill_date='2026-11-01'),dict(billing_month='2026-09-01'),dict(cycle_kind='final')]:
        with pytest.raises(ValueError):re.cycle_review({**a,**change},idx)


def test_missing_duplicate_shifted_reversed_naive_other_timezone_hourly_and_partial_grid_reject():
    a,idx=fixture()
    for grid in [idx[1:],idx[:-1],idx.delete(24),idx.insert(24,idx[24]),idx[::-1],idx.tz_localize(None),idx.tz_convert('America/Chicago'),idx+pd.Timedelta(minutes=15),idx[::4],idx[96:]]:
        with pytest.raises(ValueError):re.validate_account(a,grid)


@pytest.mark.parametrize('start,end,hours,day,count',[
    ('2026-03-01','2026-03-31',743,'2026-03-08',92),
    ('2026-11-01','2026-11-30',721,'2026-11-01',100),
])
def test_valid_dst_grids_are_distinguished_from_unsupported_billing_dates(start,end,hours,day,count):
    idx=build_interval_index(start,end,'America/New_York',15).index
    assert len(idx)==hours*4
    assert sum(idx.date==pd.Timestamp(day).date())==count
    a=re.hypothetical_defaults('SC1',day=start)
    with pytest.raises(ValueError,match='October2026'):
        re.validate_account(a,idx)


def test_checked_in_primary_receipts_component_hashes_and_exact_leaf_metadata():
    ledger=json.loads((ROOT/'docs/utility_sources/rockland_nj/sources.json').read_text())
    assert ledger['source_scope']['utility_key']==UTILITY
    assert ledger['source_scope']['source_rate_coverage']['start']=='2026-10-01'
    assert ledger['source_scope']['source_rate_coverage']['end_inclusive']=='2026-10-31'
    records=ledger['records']
    bysha={r['original_sha256']:r for r in records if r.get('original_sha256')}
    assert CURRENT_SHA in bysha
    ptc_sha='cc4530c871b7ff866cbb6e41c9281ce6b906535cec28d32f08d8a607adc25415'
    assert ptc_sha in bysha
    pairs={(url,r['original_sha256']) for r in records if r.get('original_sha256') for url in r.get('urls',[r.get('url')]) if url}
    for record in records:
        for pin in record.get('checked_in_excerpts',[]):
            assert hashlib.sha256((ROOT/pin['path']).read_bytes()).hexdigest()==pin['sha256']
    r=re.rates_on('2026-10-01')
    versions=r['component_versions']
    for component in versions.values():
        source=component['source']
        assert (source['url'],source['original_sha256']) in pairs
        assert hashlib.sha256((ROOT/source['excerpt_path']).read_bytes()).hexdigest()==source['excerpt_sha256']
        if source['original_sha256']==CURRENT_SHA:
            assert source['physical_page'] not in [4,131,132]  # Explicitly wrong NYPSC pages in official assembled PDF.
    minimum=versions['SC1_minimum']['source']
    assert (minimum['physical_page'],minimum['printed_leaf'],minimum['revision'])==(104,'84','10th Revised')
    commercial=versions['SC2_secondary_customer']['source']
    assert (commercial['physical_page'],commercial['printed_leaf'],commercial['revision'])==(107,'87','8th Revised')
    assert versions['CIP']['source']['effective_footer']=='July 1, 2026'
    credit=versions['SC1_non_TOD_distribution_adjustment']
    assert credit['effective']=='2026-07-16' and credit['source']['physical_page']==102
    assert versions['ZEC']['effective']=='2026-07-15'
    proof=versions['SC2_non_demand_branch_proof']['source']
    assert proof['original_sha256']==ptc_sha and proof['physical_page']==1
