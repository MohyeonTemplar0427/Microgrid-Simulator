"""Independent filed-rate arithmetic, eligibility and demand-window regressions."""
from dataclasses import replace
from datetime import date
import json
import pandas as pd
import pytest
from src.billing.comed_commercial import (
    ComEdCommercialAccount, calculate_comed_commercial_bill as bill,
    build_comed_commercial_plans,
)
from test_comed_residential import meter, prices


def account(**changes):
    fields = dict(supply="BES", delivery_class="small", billing_month=date(2026,9,1),
        ordinary_import_only_confirmed=True, service_voltage="secondary", utility_transformer=True,
        previous_12_month_peak_kw=40., previous_calendar_year_peak_kw=40.,
        competitively_declared=False, previous_year_months_ge_100kw=0,
        electric_space_heat=False, watt_hour_eligibility="not_applicable", eligibility_source="Synthetic test account")
    fields.update(changes)
    if fields['supply']=='BESH':
        fields.setdefault('capacity_obligation_kw',2.)
        fields.setdefault('capacity_source','Synthetic 2 kW obligation')
    return ComEdCommercialAccount(**fields)


def amounts(result):
    return {x['name']:x['amount_usd'] for x in result['lines']}


def rate(result, key):
    return next(x['rate_usd'] for x in result['lines'] if x['name']==key)


def test_independent_small_september_benchmark():
    result = bill(meter(freq='30min')*20, account())
    assert amounts(result)==dict(customer=23.42, standard_metering=6.85,
        distribution_demand=258., illinois_distribution_tax=16.99,
        electricity_supply=1269.07, transmission_services=245.38,
        purchased_electricity_adjustment=-12.53, environmental_cost_recovery=1.01,
        renewable_portfolio_standard=74.30, zero_emission_standard=9.94,
        energy_efficiency_programs=126.14, energy_transition_assistance=12.10,
        carbon_free_resource_adjustment=-234.43, coal_to_solar=1.30,
        low_income_discount_recovery=13.50)
    assert result['subtotal_usd']==1811.04
    assert result['billed_mkd_kw']==20 and result['import_kwh']==14400
    assert result['version_id']=='comed_commercial_2026_09'
    assert result['total_usd'] is None and not result['is_complete_bill']
    json.dumps(result,allow_nan=False)


def test_mkd_uses_half_hour_average_and_excludes_night_weekend_nerc_holiday():
    g=meter()*0
    g.loc['2026-09-01 09:00']=40  # paired with zero at 09:15 =>20 kW
    g.loc['2026-09-01 18:00':'2026-09-01 18:15']=100
    g.loc['2026-09-05 12:00':'2026-09-05 12:15']=200
    g.loc['2026-09-07 12:00':'2026-09-07 12:15']=300 # Labor Day
    result=bill(g,account())
    assert result['billed_mkd_kw']==20 and result['overall_30min_peak_kw']==300
    assert amounts(result)['distribution_demand']==258
    utc=g.copy();utc.index=utc.index.tz_convert('UTC')
    assert bill(utc,account())==result


def test_october_columbus_day_is_not_a_nerc_holiday():
    g=meter(10)*0;g.loc['2026-10-12 17:30':'2026-10-12 17:45']=30
    result=bill(g,account(billing_month=date(2026,10,1)))
    assert result['billed_mkd_kw']==30
    assert rate(result,'electricity_supply')==.08470
    assert rate(result,'transmission_services')==.01672
    assert result['version_id']=='comed_commercial_2026_10'


@pytest.mark.parametrize('delivery,peak,base,rbaf,iduf,dgra',[
    ('small',100,'12.50','-.055901','1.0042','.15'),
    ('medium',400,'12.78','-.070968','1.0042','.15'),
    ('large',1000,'12.47','-.054212','1.0042','.15'),
    ('very_large',10000,'11.49','-.004777','1.0005','.13'),
    ('extra_large',10001,'11.63','-.139901','1.0005','.14'),
])
def test_delivery_bands_and_independently_transcribed_adjustments(delivery,peak,base,rbaf,iduf,dgra):
    from decimal import Decimal as D, ROUND_HALF_UP
    a=account(delivery_class=delivery,previous_12_month_peak_kw=peak,supply='BESH')
    g=meter();result=bill(g,a,hourly_prices=prices(g))
    base=D(base)
    expected=base+sum((base*f).quantize(D('.01'),rounding=ROUND_HALF_UP)
        for f in (D(iduf)-1,D('.006785'),D('0'),D('.06551'),D(rbaf)))+D(dgra)
    assert rate(result,'distribution_demand')==float(expected)
    assert result['billed_mkd_kw']==1 # history does not impose a demand ratchet
    assert rate(result,'energy_efficiency_programs')==(.00482 if peak>1000 else .00876)


@pytest.mark.parametrize('delivery,peak',[('small',100.1),('medium',100),('large',400),('very_large',1000),('extra_large',10000)])
def test_class_boundary_mismatch_rejects(delivery,peak):
    with pytest.raises(ValueError,match='twelve-month'):
        bill(meter(),account(delivery_class=delivery,previous_12_month_peak_kw=peak))


def test_primary_transformer_charge_only_for_utility_equipment():
    a=account(service_voltage='primary');r=bill(meter(),a)
    assert rate(r,'distribution_demand')==5.79
    assert rate(r,'transformer_demand')==.36
    own=bill(meter(),replace(a,utility_transformer=False))
    assert 'transformer_demand' not in amounts(own)
    assert r['subtotal_usd']-own['subtotal_usd']==pytest.approx(.36)


@pytest.mark.parametrize('mkd,dfc,tc',[(10000,.73,4.77),(10001,.45,2.55)])
def test_high_voltage_history_uses_prior_mkd_not_all_hours_peak(mkd,dfc,tc):
    a=account(supply='BESH',delivery_class='high_voltage',service_voltage='high_voltage',
        previous_12_month_peak_kw=20000,previous_12_month_mkd_kw=mkd)
    g=meter();r=bill(g,a,hourly_prices=prices(g))
    assert rate(r,'distribution_demand')==dfc
    assert rate(r,'transformer_demand')==tc
    assert amounts(r)['low_income_discount_recovery']==13.50 # previous calendar year still 40 kW
    big=bill(g,replace(a,previous_calendar_year_peak_kw=10000,previous_year_months_ge_100kw=12),hourly_prices=prices(g))
    assert amounts(big)['low_income_discount_recovery']==506.25
    assert amounts(big)['customer']-amounts(r)['customer']==pytest.approx(329)


@pytest.mark.parametrize('changes',[
    {'competitively_declared':True},
    {'previous_calendar_year_peak_kw':100,'previous_year_months_ge_100kw':2},
    {'previous_calendar_year_peak_kw':99,'previous_year_months_ge_100kw':1},
    {'previous_year_months_ge_100kw':True},
    {'service_voltage':'secondary','utility_transformer':False},
    {'previous_12_month_peak_kw':float('nan')},
    {'previous_12_month_mkd_kw':5},
    {'delivery_class':'high_voltage','service_voltage':'high_voltage'},
    {'delivery_class':'watt_hour','watt_hour_eligibility':'not_applicable'},
    {'eligibility_source':''}, {'ordinary_import_only_confirmed':False},
])
def test_ineligible_or_ambiguous_account_rejects(changes):
    with pytest.raises(ValueError):bill(meter(),account(**changes))


@pytest.mark.parametrize('eligibility,heat,expected',[
    ('legacy_pre_2022',False,.08704),('dedicated_ev',False,.08813),('dedicated_ev',True,.07649)])
def test_watt_hour_delivery_does_not_imply_watt_hour_supply(eligibility,heat,expected):
    r=bill(meter(),account(delivery_class='watt_hour',watt_hour_eligibility=eligibility,electric_space_heat=heat))
    assert rate(r,'electricity_supply')==expected
    assert 'distribution_demand' not in amounts(r)
    assert rate(r,'distribution_facilities')==.02914


def test_hourly_commercial_preserves_negative_prices_and_separate_capacity():
    g=meter();p=prices(g);p.values[:]=-100
    r=bill(g,account(supply='BESH'),hourly_prices=p)
    assert amounts(r)['hourly_electricity_supply']==round(-72*1.0124*.9968*1.0406,2)
    assert amounts(r)['capacity']==20.20
    assert amounts(r)['miscellaneous_procurement']==.96
    with pytest.raises(ValueError,match='15- or 30-minute'):bill(meter(freq='60min'),account())


def test_plan_catalog_commercial_versions_and_coverage():
    plans=build_comed_commercial_plans();assert len(plans)==14
    assert all(p.version_on(date(2026,10,1)).bes_demand_energy==__import__('decimal').Decimal('.08470') for p in plans)
    with pytest.raises(ValueError,match='no filed version'):bill(meter(8),account(billing_month=date(2026,8,1)))
