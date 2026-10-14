"""Historical filed-component benchmarks, supply-specific gaps and dispatch."""
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
import json
import subprocess
from calendar import monthrange
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.billing import comed_rates
from src.billing.comed_costs import calculate, compile_costs
from src.billing.comed_cycles import ComEdBillingCycle
from src.dispatch.comed import optimize
from src.local_web.comed_study import capabilities
from test_comed_residential import account, prices, lines
from test_comed_commercial import account as commercial


def meter(year, month, kw=1.):
    start = pd.Timestamp(year=year, month=month, day=1, tz='America/Chicago')
    return pd.Series(kw, index=pd.date_range(start, start+pd.DateOffset(months=1),
                                           inclusive='left', freq='30min'))


def test_july_august_2026_independent_component_benchmarks():
    # 744 kWh. Values calculated independently from the filed June-August
    # supply table and the official October PEA/HPEA historical record.
    expected = dict(customer=15.50, standard_metering=3.87,
        distribution_facilities=47.12, illinois_distribution_tax=.95,
        electricity_supply=64.56, transmission_services=12.81,
        purchased_electricity_adjustment=1.84, environmental_cost_recovery=.07,
        renewable_portfolio_standard=3.84, zero_emission_standard=.65,
        energy_efficiency_programs=2.75, energy_transition_assistance=.62,
        carbon_free_resource_adjustment=-9.14, coal_to_solar=.07,
        low_income_discount_recovery=1.35)
    july = calculate(meter(2026, 7), account(7))
    august = calculate(meter(2026, 8), account(8))
    assert lines(july) == expected and july['subtotal_usd'] == 146.86
    expected.update(purchased_electricity_adjustment=-1.06,
                    environmental_cost_recovery=.05, carbon_free_resource_adjustment=-5.13)
    assert lines(august) == expected and august['subtotal_usd'] == 147.95
    for month, adjustment in ((7, 5.13), (8, -2.80)):
        g = meter(2026, month)
        b = calculate(g, account(month, 'BESH'), prices(g))
        assert lines(b)['purchased_electricity_adjustment'] == adjustment
        assert lines(b)['capacity'] == 20.22


@pytest.mark.parametrize('month,subtotal,customer,metering,dfc,energy', [
    (1, 121.66, 15.56, 4.02, .06062, .05015),
    (2, 115.48, 15.56, 4.02, .06062, .05015),
    (3, 128.94, 15.56, 4.02, .06062, .05015),
    (4, 122.81, 15.51, 4.01, .06041, .05015),
    (5, 133.46, 15.51, 4.01, .06041, .05015),
    (6, 136.13, 15.55, 4.02, .06055, .08261),
    (7, 138.81, 15.55, 4.02, .06055, .08261),
    (8, 142.76, 15.55, 4.02, .06055, .08261),
    (9, 137.34, 15.56, 4.02, .06059, .08260),
    (10, 134.70, 15.56, 4.02, .06059, .07873),
    (11, 120.89, 14.86, 3.83, .05776, .07873),
    (12, 136.55, 15.25, 3.93, .05930, .07873),
])
def test_2025_independent_residential_benchmarks(month, subtotal, customer, metering, dfc, energy):
    # Independent per-factor rounding; RBAF/TPAF and LID are inoperative
    # in 2025. November's physical month has 721 hours, not 720.
    b = calculate(meter(2025, month), account(billing_month=date(2025, month, 1)))
    rates = {x['name']:x['rate_usd'] for x in b['lines']}
    assert (rates['customer'], rates['standard_metering'], rates['distribution_facilities'],
            rates['electricity_supply']) == (customer, metering, dfc, energy)
    assert b['subtotal_usd'] == subtotal
    assert rates['energy_efficiency_programs'] == .00376
    assert rates['energy_transition_assistance'] == .00072
    assert rates['renewable_portfolio_standard'] == .00502
    assert 'low_income_discount_recovery' not in lines(b)
    assert b['total_usd'] is None and b['is_complete_bill'] is False
    assert b['version_id'] == f'comed_residential_2025_{month:02}'
    for row in b['lines']:
        assert row['source_documents']
        assert all(len(d['sha256']) == 64 for d in row['source_documents'])
        assert all('2026_Ratebook' not in d['url'] for d in row['source_documents'])
    json.dumps(b, allow_nan=False)


@pytest.mark.parametrize('month', range(1,13))
@pytest.mark.parametrize('kind', ['residential', 'commercial'])
def test_historical_hourly_bills_reconcile_with_dated_cost_compiler(month, kind):
    g = meter(2025, month, 1. if kind == 'residential' else 20.)
    a = account(supply='BESH', billing_month=date(2025, month, 1)) if kind == 'residential' else commercial(supply='BESH', billing_month=date(2025,month,1))
    p = prices(g)
    b = calculate(g, a, p); costs = compile_costs(g.index, a, p)
    assert abs(costs.subtotal(g.to_numpy())-b['subtotal_usd']) <= costs.rounding_bound_usd
    expected = .91048 if month <= 5 else 8.331 if month <= 8 else 8.31935
    assert lines(b)['capacity'] == float((D(str(expected))*2).quantize(D('.01')))
    isuf = '1.0033' if month < 6 else '1.0014' if month < 9 else '1.0000'
    assert b['source']['hourly_energy_multiplier'] == pytest.approx(float(D('1.0114')*D(isuf)*D('1.0470')))


@pytest.mark.parametrize('month,hpea,amount,filing', [
    (8,.00628,4.67,'ERM25-121'), (9,-.00538,-3.87,'ERM25-132'),
    (10,.02498,18.59,'ERM25-154'), (11,-.04214,-30.38,'ERM25-166'),
])
def test_late_2025_filed_hourly_adjustments_keep_their_signs_and_sources(month,hpea,amount,filing):
    g = meter(2025, month)
    b = calculate(g, account(supply='BESH',billing_month=date(2025,month,1)),prices(g))
    row = next(x for x in b['lines'] if x['name']=='purchased_electricity_adjustment')
    assert (row['rate_usd'],row['amount_usd']) == (hpea,amount)
    assert row['source_documents'] == [{'url':comed_rates.DOCUMENTS[filing][0],
        'sha256':comed_rates.DOCUMENTS[filing][1],'pdf_pages':[4]}]


@pytest.mark.parametrize('month,bes,besh,cfra,ecr', [
    (3,128.94,130.95,.00803,.00002), (4,122.81,126.60,.00810,.00007),
    (5,133.46,138.99,-.00522,.00007),
])
@pytest.mark.parametrize('supply',['BES','BESH'])
def test_spring_2025_independent_full_component_benchmark(month,bes,besh,cfra,ecr,supply):
    # Independent Decimal arithmetic at 1 kW, synthetic $50/MWh and a fixed
    # 2 kW BESH obligation. March has 743 physical hours across spring DST.
    g = meter(2025,month)
    b = calculate(g,account(supply=supply,billing_month=date(2025,month,1)),prices(g) if supply=='BESH' else None)
    assert b['subtotal_usd'] == (bes if supply=='BES' else besh)
    rates = {x['name']:x['rate_usd'] for x in b['lines']}
    assert rates['carbon_free_resource_adjustment'] == cfra
    assert rates['environmental_cost_recovery'] == ecr
    assert rates['coal_to_solar'] == 0
    assert b['import_kwh'] == (743 if month==3 else 720 if month==4 else 744)
    filing = {3:'ERM25-015',4:'ERM25-033',5:'ERM25-056'}[month]
    row = next(x for x in b['lines'] if x['name']=='carbon_free_resource_adjustment')
    assert row['source_documents'][0]['url'] == comed_rates.DOCUMENTS[filing][0]
    assert row['source_documents'][0]['pdf_pages'] == [3]


def test_unknown_hpea_still_disables_only_hourly_supply(monkeypatch):
    # Retrieving more history does not weaken the fail-closed catalog rule.
    monkeypatch.setattr(comed_rates,'VERSIONS',tuple(
        replace(v,besh_adjustment=None) if v.effective_start==date(2025,8,1) else v
        for v in comed_rates.VERSIONS))
    g = meter(2025,8)
    calculate(g,account(billing_month=date(2025,8,1)))
    with pytest.raises(ValueError, match='no filed version'):
        calculate(g,account(supply='BESH',billing_month=date(2025,8,1)),prices(g))


@pytest.mark.parametrize('supply',['BES','BESH'])
@pytest.mark.parametrize('month',[11,12])
def test_later_2026_unverified_composites_remain_rejected(supply,month):
    g = meter(2026,month)
    with pytest.raises(ValueError,match='no filed version'):
        calculate(g,account(supply=supply,billing_month=date(2026,month,1)),prices(g) if supply=='BESH' else None)


def test_commercial_historical_rates_and_november_rider_boundary():
    oct_bill = calculate(meter(2025,10,20), commercial(billing_month=date(2025,10,1)))
    nov_bill = calculate(meter(2025,11,20), commercial(billing_month=date(2025,11,1)))
    rate = lambda b,n: next(x['rate_usd'] for x in b['lines'] if x['name']==n)
    # 2025 small DFC12.71, DGRA.11, IDUF1.0064. October DRAF17.0696%
    # and EDAF-3.80%; November10.8072% and -2.91%, individually rounded.
    assert rate(oct_bill,'distribution_demand') == 14.59
    assert rate(nov_bill,'distribution_demand') == 13.90
    assert rate(nov_bill,'customer') == 22.55
    assert rate(nov_bill,'energy_efficiency_programs') == .00835
    assert rate(nov_bill,'electricity_supply') == .07946
    assert 'low_income_discount_recovery' not in lines(nov_bill)


def test_cycle_crossing_november_change_uses_confirmed_month_and_dst():
    c = ComEdBillingCycle(date(2025,10,15),date(2025,11,14),date(2025,11,1),
                         source='Hypothetical utility-designated November meter cycle')
    idx = pd.date_range(pd.Timestamp(c.start_date,tz='America/Chicago'),
        pd.Timestamp(c.end_date,tz='America/Chicago')+pd.DateOffset(days=1),freq='30min',inclusive='left')
    g = pd.Series(20.,index=idx); a = commercial()
    b = calculate(g,a,billing_cycles=[c]); costs = compile_costs(idx,a,billing_cycles=[c])
    assert b['import_kwh'] == 745*20
    one = b['cycles'][0]
    assert lines(one)['distribution_demand'] == 278.
    assert one['version_id'] == 'comed_commercial_2025_11'
    assert abs(costs.subtotal(g.to_numpy())-b['subtotal_usd']) <= costs.rounding_bound_usd
    assert one['billing_cycle']['rules_pdf_pages'] == [23,26,165,169,245,246]
    with pytest.raises(ValueError, match='every physical interval'):
        calculate(g.iloc[1:],a,billing_cycles=[c])


def test_historical_dispatch_is_physical_and_reconciles():
    c = ComEdBillingCycle(date(2025,7,1),date(2025,7,2),date(2025,7,1),kind='short_service',
        source='Hypothetical documented short-service allocation',
        charge_factors={'customer':1.,'standard_metering':1.,'distribution_demand':1.,'capacity':1.})
    idx = pd.date_range('2025-07-01','2025-07-03',tz='America/Chicago',freq='30min',inclusive='left')
    load = np.where((idx.hour>=9)&(idx.hour<18),20.,5.)
    pv = np.where((idx.hour>=10)&(idx.hour<16),15.,0.)
    inputs = pd.DataFrame({'timestamp':idx,'native_load_kw':load,'pv_available_kw':pv})
    a = commercial(billing_month=date(2025,7,1))
    battery = dict(capacity_kWh=10.,energy_kWh=5.,SOC_min=.1,SOC_max=.9,
                   max_charge_kw=3.,max_discharge_kw=3.,charge_efficiency=.95,discharge_efficiency=.95)
    base = optimize(inputs,a,billing_cycles=[c])
    out = optimize(inputs,a,battery=battery,billing_cycles=[c])
    assert out['bill']['subtotal_usd'] <= base['bill']['subtotal_usd']+.01
    assert abs(out['rounding_difference_usd']) <= out['rounding_bound_usd']
    assert out['terminal_energy_kwh'] == pytest.approx(5.)
    assert out['dispatch'].grid_export_kw.eq(0).all()


def test_browser_lists_only_supported_months_for_selected_supply_and_old_pins():
    caps = capabilities()
    assert '2025-11-01' in caps['billing_months_by_supply']['BES']
    assert '2025-11-01' in caps['billing_months_by_supply']['BESH']
    assert all(f'2025-{m:02}-01' in caps['billing_months_by_supply'][s]
               for m in range(1,13) for s in ('BES','BESH'))
    script = """const {comedBillingMonths}=require('./src/local_web/static/comed_simulation.js');
const c=JSON.parse(process.argv[1]);
console.log(JSON.stringify([comedBillingMonths({comed:c,comed_simulation:c},'BES'),
comedBillingMonths({comed:c,comed_simulation:c},'BESH'),
comedBillingMonths({comed:{billing_months:['2026-09-01']},comed_simulation:{}},'BESH')]));"""
    result = json.loads(subprocess.check_output(['node','-e',script,json.dumps(caps)],text=True))
    assert result == [caps['billing_months_by_supply']['BES'],caps['billing_months_by_supply']['BESH'],['2026-09-01']]


@pytest.mark.parametrize('kind',['residential','commercial'])
@pytest.mark.parametrize('supply',['BES','BESH'])
def test_twelve_linked_2025_cycles_have_complete_dated_bills_and_matching_objective(kind,supply):
    cycles = [ComEdBillingCycle(date(2025,m,1),date(2025,m,monthrange(2025,m)[1]),
        date(2025,m,1),source='Synthetic calendar-designated full-year billing benchmark')
        for m in range(1,13)]
    index = pd.date_range('2025-01-01','2026-01-01',tz='America/Chicago',freq='30min',inclusive='left')
    g = pd.Series(1. if kind=='residential' else 20.,index=index)
    a = (account if kind=='residential' else commercial)(supply=supply,billing_month=date(2025,1,1))
    p = prices(g) if supply=='BESH' else None
    b = calculate(g,a,p,billing_cycles=cycles)
    costs = compile_costs(index,a,p,billing_cycles=cycles)
    assert len(b['cycles']) == 12 and b['import_kwh'] == 8760*g.iloc[0]
    assert b['cycles'][2]['import_kwh'] == 743*g.iloc[0]
    assert b['cycles'][10]['import_kwh'] == 721*g.iloc[0]
    assert abs(costs.subtotal(g.to_numpy())-b['subtotal_usd']) <= costs.rounding_bound_usd
    assert all(c['version_id'].endswith(f'_2025_{m:02}') for m,c in enumerate(b['cycles'],1))
    assert len([l for l in b['lines'] if l['name']=='customer']) == 12
    if kind=='residential' and supply=='BES':
        # Sum of the independently calculated monthly benchmarks above.
        assert b['subtotal_usd'] == 1569.53
    if kind=='commercial':
        assert all(c['billed_mkd_kw']==20 for c in b['cycles'])
    # A missing interval cannot masquerade as an otherwise supported cycle.
    with pytest.raises(ValueError,match='every physical interval'):
        calculate(g.drop(index[3500]),a,p,billing_cycles=cycles)


def test_retrieved_evidence_hashes_and_runtime_provenance_match():
    import hashlib
    root = Path(__file__).resolve().parents[1]/'docs/utility_sources/comed/history'
    manifest = json.loads((root/'manifest.json').read_text())
    sources = {s['id']:s for s in manifest['sources']}
    for f in manifest['retained_files']:
        assert hashlib.sha256((root/f['file']).read_bytes()).hexdigest()==f['sha256']
    for key,(url,sha) in comed_rates.DOCUMENTS.items():
        assert (sources[key]['url'],sources[key]['sha256']) == (url,sha)
    for version in comed_rates.VERSIONS:
        if version.effective_start >= date(2026,6,1):
            continue
        for _,doc,page in version.component_sources:
            assert page in sources[doc]['implemented_pages']
