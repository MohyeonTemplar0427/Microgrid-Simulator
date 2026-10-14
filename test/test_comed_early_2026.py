"""Independent early-2026 tariff benchmarks and billing-cycle reconciliation."""
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.billing import comed_rates
from src.billing.comed_costs import calculate, compile_costs
from src.billing.comed_cycles import ComEdBillingCycle
from src.dispatch.comed import optimize
from src.local_web.comed_study import capabilities
from test_comed_history import meter
from test_comed_residential import account, prices, lines
from test_comed_commercial import account as commercial


# Independently calculated Decimal benchmarks, with no src imports in the
# reference calculation: 1 kW; BESH synthetic $50/MWh and a 2 kW obligation.
# CFRA values are the complete CFR+CFRMR totals, not the CFR base alone.
CASES = [
    (1,132.97,128.35,.00357,.00743,-.02381,.00007,1.17),
    (2,127.01,114.62,.00889,-.00189,-.02182,.00007,1.22),
    (3,116.23,98.54,-.00151,-.01528,-.04110,.00007,1.22),
    (4,129.85,127.56,.01159,.01773,-.03186,.00006,1.35),
    (5,161.66,153.17,.08166,.08032,-.06414,.00009,1.35),
]


@pytest.mark.parametrize('month,bes,besh,pea,hpea,cfra,cts,lid',CASES)
@pytest.mark.parametrize('supply',['BES','BESH'])
def test_independent_early_2026_residential_benchmark(month,bes,besh,pea,hpea,cfra,cts,lid,supply):
    g=meter(2026,month);a=account(supply=supply,billing_month=date(2026,month,1))
    p=prices(g) if supply=='BESH' else None
    b=calculate(g,a,p);r={x['name']:x['rate_usd'] for x in b['lines']}
    assert b['subtotal_usd']==(bes if supply=='BES' else besh)
    assert b['version_id']==f'comed_residential_2026_{month:02}'
    assert (r['customer'],r['standard_metering'],r['distribution_facilities'])==(
        (15.26,3.81,.06228) if month<=3 else (15.35,3.83,.06267))
    assert r['purchased_electricity_adjustment']==(pea if supply=='BES' else hpea)
    assert (r['carbon_free_resource_adjustment'],r['coal_to_solar'],r['low_income_discount_recovery'])==(cfra,cts,lid)
    assert r['environmental_cost_recovery']==(.00010 if month<=3 else .00009)
    assert r['renewable_portfolio_standard']==.00502
    assert r['zero_emission_standard']==.00189
    assert r['illinois_distribution_tax']==.00126
    assert b['is_complete_bill'] is False and b['total_usd'] is None
    if supply=='BES':
        assert (r['electricity_supply'],r['transmission_services'])==(.07841,.01819)
        assert 'capacity' not in r
    else:
        assert (r['capacity'],r['transmission_services'],r['miscellaneous_procurement'])==(8.32925,.01083,.00062)
        assert b['source']['hourly_energy_multiplier']==pytest.approx(1.0124*1.0002*1.0406)
    costs=compile_costs(g.index,a,p)
    assert abs(costs.subtotal(g.to_numpy())-b['subtotal_usd'])<=costs.rounding_bound_usd


@pytest.mark.parametrize('month',[1,2,3,4,5])
@pytest.mark.parametrize('supply',['BES','BESH'])
def test_early_2026_commercial_components_and_objective(month,supply):
    g=meter(2026,month,20.);a=commercial(supply=supply,billing_month=date(2026,month,1))
    p=prices(g) if supply=='BESH' else None
    b=calculate(g,a,p);r={x['name']:x['rate_usd'] for x in b['lines']}
    assert (r['customer'],r['standard_metering'],r['distribution_demand'])==(
        (23.36,6.81,12.85) if month<=3 else (23.46,6.86,12.93))
    assert r['low_income_discount_recovery']==(11.70 if month==1 else 12.20 if month<=3 else 13.50)
    assert b['billed_mkd_kw']==20 and r['energy_efficiency_programs']==.00876
    if supply=='BES':assert (r['electricity_supply'],r['transmission_services'])==(.07899,.01805)
    else:assert r['capacity']==8.32925
    varied=np.linspace(1.,50.,len(g));costs=compile_costs(g.index,a,p)
    bill=calculate(pd.Series(varied,index=g.index),a,p)
    assert abs(costs.subtotal(varied)-bill['subtotal_usd'])<=costs.rounding_bound_usd


@pytest.mark.parametrize('month',[1,2,4,5])
def test_large_customer_recovery_and_corrected_extra_large_dgra(month):
    g=meter(2026,month,20.)
    a=commercial(supply='BESH',delivery_class='extra_large',billing_month=date(2026,month,1),
        previous_12_month_peak_kw=20000.,previous_calendar_year_peak_kw=20000.,
        previous_year_months_ge_100kw=12)
    b=calculate(g,a,prices(g));r={x['name']:x['rate_usd'] for x in b['lines']}
    assert r['low_income_discount_recovery']==(438.75 if month==1 else 457.50 if month<=3 else 506.25)
    # Annual sheet56: Extra Large is $0.13/kW; $0.14 belongs to High Voltage.
    # The base and each adjustment are independently rounded before DGRA.
    assert r['distribution_demand']==(10.91 if month<=3 else 10.99)
    assert r['energy_efficiency_programs']==.00482


def test_supported_catalog_dates_and_no_later_month_substitution():
    c=capabilities()['billing_months_by_supply']
    assert c['BES']==c['BESH']
    assert all(f'2026-{m:02}-01' in c[s] for m in range(1,11) for s in ('BES','BESH'))
    for plan in comed_rates.build_comed_residential_plans():
        assert plan.version_on(date(2026,1,1)).bes_energy==comed_rates.D('.07841')
        assert plan.version_on(date(2026,5,31)).bes_energy==comed_rates.D('.07841')
        assert plan.version_on(date(2026,6,1)).bes_energy==comed_rates.D('.08677')
        with pytest.raises(ValueError,match='no filed version'):
            plan.version_on(date(2026,11,1))


def test_historical_components_require_explicit_provenance():
    v=next(v for v in comed_rates.VERSIONS if v.effective_start==date(2026,2,1))
    broken=replace(v,component_sources=tuple(s for s in v.component_sources if s[0]!=801))
    with pytest.raises(ValueError,match='No historical provenance'):
        comed_rates.line_sources(broken,'customer',[801])


def test_april_designated_cycle_crosses_calendar_change_without_splitting_demand():
    c=ComEdBillingCycle(date(2026,3,15),date(2026,4,14),date(2026,4,1),
        source='Hypothetical utility-designated April billing cycle')
    idx=pd.date_range('2026-03-15','2026-04-15',tz='America/Chicago',freq='30min',inclusive='left')
    g=pd.Series(20.,index=idx);a=commercial()
    b=calculate(g,a,billing_cycles=[c]);one=b['cycles'][0];r={x['name']:x['rate_usd'] for x in one['lines']}
    assert one['version_id']=='comed_commercial_2026_04'
    assert r['distribution_demand']==12.93 and r['coal_to_solar']==.00006
    assert one['billed_mkd_kw']==20 and len([x for x in one['lines'] if x['name']=='customer'])==1
    costs=compile_costs(idx,a,billing_cycles=[c])
    assert abs(costs.subtotal(g.to_numpy())-b['subtotal_usd'])<=costs.rounding_bound_usd
    with pytest.raises(ValueError,match='every physical interval'):
        calculate(g.iloc[1:],a,billing_cycles=[c])


@pytest.mark.parametrize('supply',['BES','BESH'])
def test_partial_may_dispatch_keeps_credit_signs_and_terminal_energy(supply):
    c=ComEdBillingCycle(date(2026,5,1),date(2026,5,2),date(2026,5,1),kind='short_service',
        source='Hypothetical per-charge allocation; not a universal proration rule',
        charge_factors={'customer':1.,'standard_metering':1.,'low_income_discount_recovery':1.,'capacity':1.})
    idx=pd.date_range('2026-05-01','2026-05-03',tz='America/Chicago',freq='30min',inclusive='left')
    load=np.where((idx.hour>=17)&(idx.hour<22),2.,.6)
    pv=np.where((idx.hour>=10)&(idx.hour<16),3.,0.)
    inputs=pd.DataFrame({'timestamp':idx,'native_load_kw':load,'pv_available_kw':pv})
    a=account(supply=supply);p=prices(pd.Series(load,index=idx)) if supply=='BESH' else None
    battery=dict(capacity_kWh=10.,energy_kWh=5.,SOC_min=.1,SOC_max=.9,max_charge_kw=3.,
        max_discharge_kw=3.,charge_efficiency=.95,discharge_efficiency=.95)
    base=optimize(inputs,a,p,billing_cycles=[c]);out=optimize(inputs,a,p,battery,billing_cycles=[c])
    assert out['bill']['subtotal_usd']<=base['bill']['subtotal_usd']+.01
    assert abs(out['rounding_difference_usd'])<=out['rounding_bound_usd']
    assert out['terminal_energy_kwh']==pytest.approx(5.)
    assert out['dispatch'].grid_export_kw.eq(0).all()
    assert lines(out['bill']['cycles'][0])['carbon_free_resource_adjustment']<0
