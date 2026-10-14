"""Dated component benchmarks and explicit real-cycle reconciliation."""
from dataclasses import replace
from datetime import date
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.billing.comed_cycles import ComEdBillingCycle, cycle_grid, parse_cycles
from src.billing.comed_costs import calculate, compile_costs
from src.dispatch.comed import optimize
from test_comed_residential import account, meter, prices, lines
from test_comed_commercial import account as commercial


def cycle(start="2026-09-15", end="2026-10-14", month="2026-10-01", **kw):
    return ComEdBillingCycle(date.fromisoformat(start), date.fromisoformat(end),
        date.fromisoformat(month), source="Explicit hypothetical meter cycle, not a customer bill", **kw)


def grid(c, freq="30min", power=1.):
    return pd.Series(power, index=pd.date_range(pd.Timestamp(c.start_date,tz="America/Chicago"),
        pd.Timestamp(c.end_date,tz="America/Chicago")+pd.DateOffset(days=1), freq=freq,inclusive="left"))


def test_independent_june_component_benchmark():
    # All final amounts independently calculated from retained filed sheets;
    # including per-adjustment rounding, not a copied September composite.
    b=calculate(meter(6),account(6))
    assert lines(b)==dict(customer=15.50, standard_metering=3.87,
        distribution_facilities=45.60, illinois_distribution_tax=.92,
        electricity_supply=62.47, transmission_services=12.40,
        purchased_electricity_adjustment=1.66, environmental_cost_recovery=.06,
        renewable_portfolio_standard=3.72,zero_emission_standard=.63,
        energy_efficiency_programs=2.66,energy_transition_assistance=.60,
        carbon_free_resource_adjustment=-9.68,coal_to_solar=.06,low_income_discount_recovery=1.35)
    assert b['subtotal_usd']==141.82
    pec=next(l for l in b['lines'] if l['name']=='electricity_supply')
    assert pec['source_documents'][0]['url'].endswith('/399143.pdf')
    assert pec['source_documents'][0]['pdf_pages']==[4]


@pytest.mark.parametrize('kind',['residential','commercial'])
@pytest.mark.parametrize('supply',['BES','BESH'])
def test_june_cost_compiler_uses_dated_components(kind,supply):
    g=meter(6,freq='30min')*(1 if kind=='residential' else 20)
    a=account(6,supply) if kind=='residential' else commercial(billing_month=date(2026,6,1),supply=supply)
    p=prices(g) if supply=='BESH' else None
    b=calculate(g,a,p);cost=compile_costs(g.index,a,p)
    assert abs(cost.subtotal(g.to_numpy())-b['subtotal_usd'])<=cost.rounding_bound_usd
    if supply=='BESH':
        assert lines(b)['capacity']==20.22
        assert b['source']['hourly_energy_multiplier']==pytest.approx(1.0124*.9979*1.0406)
    if kind=='commercial' and supply=='BES':assert b['subtotal_usd']==1900.31


def test_cross_october_boundary_uses_confirmed_billing_month_once():
    c=cycle();g=grid(c);b=calculate(g,account(),billing_cycles=[c])
    assert b['import_kwh']==720
    assert lines(b)['electricity_supply']==60.57  # 720 * October .08413
    assert len([x for x in b['lines'] if x['name']=='customer'])==1
    assert b['cycles'][0]['billing_month']=='2026-10-01'
    assert b['cycles'][0]['billing_cycle']['billing_days']==30
    assert b['cycles'][0]['version_id']=='comed_residential_2026_10'


@pytest.mark.parametrize('supply',['BES','BESH'])
def test_consecutive_cycles_have_separate_peaks_fixed_charges_and_rates(supply):
    cs=[cycle('2026-09-01','2026-09-30','2026-09-01'),cycle('2026-10-01','2026-10-31','2026-10-01')]
    g=pd.concat([grid(cs[0],power=20),grid(cs[1],power=30)])
    a=commercial(supply=supply);p=prices(g) if supply=='BESH' else None
    b=calculate(g,a,p,cs);cost=compile_costs(g.index,a,p,cs)
    assert [x['billed_mkd_kw'] for x in b['cycles']]==[20,30]
    assert lines(b['cycles'][0])['distribution_demand']==258.
    assert lines(b['cycles'][1])['distribution_demand']==387.
    assert abs(cost.subtotal(g.to_numpy())-b['subtotal_usd'])<=cost.rounding_bound_usd
    assert len([x for x in b['lines'] if x['name']=='customer'])==2
    if supply=='BESH':assert [lines(x)['capacity'] for x in b['cycles']]==[20.20,20.20]


@pytest.mark.parametrize('kind',['residential','commercial'])
def test_short_service_factors_are_explicit_and_not_calendar_proration(kind):
    factors=dict(customer=.5, standard_metering=.5,low_income_discount_recovery=.5,
                 capacity=.25,distribution_demand=1.)
    c=cycle('2026-09-16','2026-09-30','2026-09-01',kind='short_service',charge_factors=factors)
    a=account(9,'BESH') if kind=='residential' else commercial(supply='BESH')
    g=grid(c,power=20 if kind=='commercial' else 1);p=prices(g)
    b=calculate(g,a,p,[c]);cost=compile_costs(g.index,a,p,[c]);one=b['cycles'][0]
    assert lines(one)['capacity']==5.05  # obligation 2 kW, separate .25 factor
    assert abs(cost.subtotal(g.to_numpy())-b['subtotal_usd'])<=cost.rounding_bound_usd
    if kind=='commercial':assert lines(one)['distribution_demand']==258.


def test_weekend_only_short_bill_has_zero_mkd_without_nan():
    c=cycle('2026-09-05','2026-09-06','2026-09-01',kind='short_service',charge_factors={
        'customer':1.,'standard_metering':1.,'low_income_discount_recovery':1.,'distribution_demand':1.})
    g=grid(c,power=20);b=calculate(g,commercial(),billing_cycles=[c])
    assert b['billed_mkd_kw']==0 and b['overall_30min_peak_kw']==20
    assert np.isfinite(compile_costs(g.index,commercial(),billing_cycles=[c]).subtotal(g.to_numpy()))


@pytest.mark.parametrize('start,end,hours',[('2026-03-01','2026-03-31',743),('2026-11-01','2026-11-30',721)])
def test_dst_cycle_grid_and_missing_rate_rejection(start,end,hours):
    c=cycle(start,end,start);g=grid(c,freq='15min');utc,dt=cycle_grid(g.index,c)
    assert len(utc)*float(dt)==hours
    if start=='2026-03-01':
        assert calculate(g,account(),billing_cycles=[c])['import_kwh']==hours
    else:
        with pytest.raises(ValueError,match='no filed version'):calculate(g,account(),billing_cycles=[c])


@pytest.mark.parametrize('bad',['gap','duplicate','naive','partial_data','cycle_gap','overlap','unordered','unknown_month','no_source','no_factor','nan_factor'])
def test_cycle_contract_rejects_ambiguous_or_incomplete_data(bad):
    c=cycle();g=grid(c);cs=[c]
    if bad in ('gap','partial_data'):g=g.iloc[1:]
    if bad=='duplicate':g=pd.concat([g.iloc[:1],g])
    if bad=='naive':g.index=g.index.tz_localize(None)
    if bad=='cycle_gap':cs=[replace(c,end_date=date(2026,10,13))]
    if bad=='overlap':cs=[c,c]
    if bad=='unordered':g=g.iloc[::-1]
    if bad=='unknown_month':cs=[replace(c,billing_month=date(2026,11,1))]
    if bad=='no_source':cs=[replace(c,source='')]
    if bad=='no_factor':cs=[replace(c,kind='short_service',charge_factors={'customer':.5})]
    if bad=='nan_factor':cs=[replace(c,kind='short_service',charge_factors={'customer':float('nan')})]
    with pytest.raises((ValueError,TypeError)):calculate(g,account(),billing_cycles=cs)


def test_optimizer_reconciles_cross_month_cycles_and_terminal_energy():
    c=cycle();g=grid(c);inputs=pd.DataFrame({'timestamp':g.index,'native_load_kw':g.values,'pv_available_kw':.5})
    b=dict(capacity_kWh=2.,energy_kWh=1.,SOC_min=.2,SOC_max=.8,max_charge_kw=1.,max_discharge_kw=1.,
           charge_efficiency=.95,discharge_efficiency=.95)
    out=optimize(inputs,account(),battery=b,billing_cycles=[c])
    assert abs(out['rounding_difference_usd'])<=out['rounding_bound_usd']
    assert out['terminal_energy_kwh']==pytest.approx(1.)
    assert out['bill']['cycles'][0]['version_id']=='comed_residential_2026_10'
    assert out['dispatch'].grid_export_kw.eq(0).all()


def test_source_hashes_are_reproducible():
    import hashlib
    root=Path('docs/utility_sources/comed/history')
    manifest=json.loads((root/'manifest.json').read_text())
    for entry in manifest['retained_files']:
        assert hashlib.sha256((root/entry['file']).read_bytes()).hexdigest()==entry['sha256']
