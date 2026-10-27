"""Independent JCP&L NJ filed arithmetic and ordinary calendar-cycle scope.

Expected prices below are transcribed from the official PartIII leaves and the
independently published PTC/BPU impact checks, never production rate helpers.
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

from src.billing import jcpl_nj as jcpl
from src.billing.regional_math import BillingMath
from src.timeseries import build_interval_index

UTILITY = "jcpl_new_jersey"
ROOT = Path(__file__).resolve().parents[1]

# month, publishedSBC, ZEC, LRAM_R, LRAM_G, CRC, monthlyresidentialEGCC.
# Printed50,64,67,72,65; NGCsecondary.000234 untilOct26 .000312;
# RPzero untilOct26 ENJ_R.000135/ENJ_G.000148. RRCpublishedtotal.004729.
MONTHS = [
    ("2025-01", ".007700", ".004265", ".000546", ".000494", "0", "0"),
    ("2025-02", ".007700", ".004265", ".000546", ".000494", "0", "0"),
    ("2025-03", ".007700", ".004265", ".000546", ".000494", "0", "0"),
    ("2025-04", ".007700", ".004265", ".000546", ".000494", "0", "0"),
    ("2025-05", ".007700", ".004265", ".000546", ".000494", ".000358", "0"),
    ("2025-06", ".007700", "0", ".000546", ".000494", ".000358", "0"),
    ("2025-07", ".007700", "0", ".000546", ".000494", ".000358", "-30"),
    ("2025-08", ".007700", "0", ".000546", ".000494", ".000358", "-30"),
    ("2025-09", ".007700", "0", ".000546", ".000494", ".000358", "10"),
    ("2025-10", ".009239", "0", ".000546", ".000494", ".000358", "10"),
    ("2025-11", ".009239", "0", ".000546", ".000494", ".000358", "10"),
    ("2025-12", ".009239", "0", ".000546", ".000494", ".000358", "10"),
    ("2026-01", ".009239", "0", ".000546", ".000494", ".000358", "10"),
    ("2026-02", ".009239", "0", ".000971", ".001001", ".000358", "10"),
    ("2026-03", ".009239", "0", ".000971", ".001001", ".000358", "0"),
    ("2026-04", ".009239", "0", ".000971", ".001001", ".000358", "0"),
    ("2026-05", ".009239", "0", ".000971", ".001001", ".000358", "0"),
    ("2026-06", ".009239", "-.004265", ".000971", ".001001", ".000358", "0"),
    ("2026-07", ".009239", "-.004265", ".000971", ".001001", ".000358", "0"),
    ("2026-08", ".009239", "-.004265", ".000971", ".001001", ".000358", "0"),
    ("2026-09", ".009239", "-.004265", ".000971", ".001001", ".000358", "0"),
    ("2026-10", ".008476", "-.004265", ".000971", ".001001", ".000358", "0"),
]

# Reconciliation printed42: quarterly service periods, separatefromannualenergy.
RECONCILIATION = [
    ("2025-01", "-.004426"), ("2025-03", ".001036"),
    ("2025-06", ".000039"), ("2025-09", ".002501"),
    ("2025-12", "-.009951"), ("2026-03", "0"),
    ("2026-06", ".004441"), ("2026-09", ".008040"),
]


def independent_supply(month, plan):
    summer = 6 <= int(month[5:7]) <= 9
    if month < "2025-06":
        r = (".092332", ".101557") if summer else (".101010",)*2
        g = ".095517" if summer else ".095073"
    elif month < "2026-06":
        r = (".125888", ".135113") if summer else (".136817",)*2
        g = ".124982" if summer else ".124626"
    else:
        r = (".128815", ".138040") if summer else (".141185",)*2
        g = ".124922" if summer else ".124319"
    return r if plan == "RS" else (g, g)


def dated_linear_prices(index, component):
    """Apply actual local service instants; no average-by-days substitution."""
    windows = (
        [("2025-01-01", ".012709"), ("2025-05-01", ".014877"), ("2026-07-15", ".017244")]
        if component == "transmission" else
        [("2025-01-01", ".004071"), ("2025-05-01", ".004335"),
         ("2025-09-15", ".004339"), ("2026-07-15", ".004065"), ("2026-10-01", ".004059")]
    )
    result = np.zeros(len(index))
    for day, price in windows:
        result[index >= pd.Timestamp(day, tz="America/New_York")] = float(price)
    return result


def fixture(plan="RS", month="2026-09"):
    start = month + "-01"
    end = str((pd.Timestamp(start) + pd.offsets.MonthEnd(0)).date())
    a = jcpl.hypothetical_defaults(plan, day=start)
    a.update(billing_month=start, bill_date=end)
    idx = build_interval_index(start, end, "America/New_York", 15).index
    return a, idx


def power_for_energy(index, energy=1000., peak=None):
    x = np.full(len(index), energy*4/len(index))
    if peak is not None:
        x[0] = peak
        x[1:] = (energy*4-peak)/(len(index)-1)
    return x


def independent_lines(index, power, plan):
    month = index[0].strftime("%Y-%m")
    row = next(r for r in MONTHS if r[0] == month)
    _, sbc, zec, lram_r, lram_g, crc, egcc = row
    e = D(str(float(np.sum(power)*.25)))
    summer = 6 <= int(month[5:7]) <= 9
    distribution = ((".020182", ".079810") if summer else (".033061",)*2) if plan == "RS" else ((".075288", ".006021") if summer else (".069662", ".006021"))
    generation = independent_supply(month, plan)
    def tier(pair, threshold):
        return min(e,D(threshold))*D(pair[0])+max(e-D(threshold),D(0))*D(pair[1])
    recon = next(v for start,v in reversed(RECONCILIATION) if month >= start)
    return {
        "customer": float(D("4.27" if plan == "RS" else "4.65")),
        "distribution": float(tier(distribution,"600" if plan == "RS" else "1000")),
        "generation": float(tier(generation,"600")),
        "transmission": float(np.dot(power*.25,dated_linear_prices(index,"transmission"))),
        "TEC": float(np.dot(power*.25,dated_linear_prices(index,"TEC"))),
        "reconciliation": float(e*D(recon)),
        "NGC": float(e*D(".000312" if month == "2026-10" else ".000234")),
        "SBC": float(e*D(sbc)),
        "RRC": float(e*D(".004729")),
        "ZEC": float(e*D(zec)),
        "RP_ENJ": float(e*D((".000135" if plan == "RS" else ".000148") if month == "2026-10" else "0")),
        "LRAM": float(e*D(lram_r if plan == "RS" else lram_g)),
        "CRC": float(e*D(crc)),
        "EGCC": float(D(egcc)) if plan == "RS" else 0.,
    }


def bill(plan="RS", month="2026-09", energy=1000., peak=None, account=None, state=None, power=None):
    a, idx = fixture(plan, month)
    a = a if account is None else account
    jcpl.validate_account(a, idx)
    jcpl.validate_state(a, idx, state=state)
    p = power_for_energy(idx, energy, peak) if power is None else power
    return jcpl.charge_lines(idx, p, np.zeros(len(idx)), a, math=BillingMath(idx), state=state)


def comparable_lines(lines, plan):
    mapping = dict(customer="distribution_customer", distribution="distribution_energy",
        generation="bgs_generation_energy", transmission="transmission_service",
        TEC="transmission_enhancement", reconciliation="bgs_reconciliation",
        NGC="non_utility_generation", ZEC="zero_emission_certificate",
        RP_ENJ="infrastructure_reliability", LRAM="lost_revenue_adjustment", CRC="covid_recovery")
    result = {key:lines[value] for key,value in mapping.items()}
    result["SBC"] = sum(v for k,v in lines.items() if k.startswith("sbc_"))
    result["RRC"] = sum(v for k,v in lines.items() if k.startswith("rggi_"))
    result["EGCC"] = lines["residential_generation_capacity_deferral"] if plan == "RS" else 0.
    return result


@pytest.mark.parametrize("plan", ["RS", "GS"])
@pytest.mark.parametrize("row", MONTHS, ids=[r[0] for r in MONTHS])
def test_every_month_independent_filed_component_stack_and_published_rider_totals(plan, row):
    month = row[0]
    a, idx = fixture(plan, month)
    p = power_for_energy(idx, 1000.)
    got = bill(plan, month, power=p)
    expected = independent_lines(idx, p, plan)
    actual = comparable_lines(got["lines"], plan)
    assert actual == pytest.approx(expected, abs=1e-9)
    assert sum(got["lines"].values()) == pytest.approx(sum(expected.values()), abs=1e-8)
    assert got["lines"]["bgs_reliability_must_run"] == 0.
    assert got["is_complete_bill"] is True and got["excluded_components"] == []
    assert got["rate_evidence_status"] == "verified" and got["rate_assumptions"] == []
    assert got["metrics"]["additional_tax_percentage_applied"] is False
    assert got["metrics"]["quantity_basis"] == "raw_import_energy_no_unsourced_quantity_rounding"
    assert got["metrics"]["monthly_charge_factor"] == 1.
    assert got["metrics"]["whole_cycle_block_kwh"] == (600. if plan == "RS" else 1000.)
    assert got["metrics"]["rounded_cash_optimum_claimed"] is False
    assert not {"sales_tax", "gross_receipts_tax", "supply_administration", "pjm_capacity", "wholesale_energy", "nspl"} & set(got["lines"])
    if plan == "GS":
        assert got["metrics"]["gs_minimum_inactive_verified"] is True
        assert got["lines"]["distribution_demand"] == got["lines"]["minimum_demand"] == got["lines"]["reactive_demand"] == 0.
        assert "residential_generation_capacity_deferral" not in got["lines"]


@pytest.mark.parametrize("plan,threshold,pair", [("RS",600.,(".020182",".079810")),("GS",1000.,(".075288",".006021"))])
@pytest.mark.parametrize("offset", [-.005,0.,.005,123.456])
def test_source_specific_summer_marginal_blocks_and_raw_energy(plan,threshold,pair,offset):
    energy=threshold+offset
    got=bill(plan,"2026-09",energy)
    expected=min(D(str(energy)),D(str(threshold)))*D(pair[0])+max(D(str(energy))-D(str(threshold)),D(0))*D(pair[1])
    assert got["lines"]["distribution_energy"] == pytest.approx(float(expected),abs=1e-9)
    assert got["metrics"]["raw_import_kwh"] == pytest.approx(energy,abs=1e-9)
    if plan == "RS":
        gen=min(energy,600)*.128815+max(energy-600,0)*.138040
        assert got["lines"]["bgs_generation_energy"] == pytest.approx(gen,abs=1e-9)
    else:
        assert got["lines"]["bgs_generation_energy"] == pytest.approx(energy*.124922,abs=1e-9)


@pytest.mark.parametrize("plan,month,energy,distribution", [
    ("RS","2025-01",1000.,"33.061"),
    ("RS","2026-09",1000.,"44.0332"),
    ("GS","2025-01",730.,"50.85326"),
])
def test_isolated_tariff_base_arithmetic_fixtures_not_claimed_as_published_invoices(plan,month,energy,distribution):
    got=bill(plan,month,energy)
    assert got["lines"]["distribution_energy"] == pytest.approx(float(D(distribution)),abs=1e-9)
    customer=4.27 if plan=="RS" else 4.65
    assert got["lines"]["distribution_customer"]+got["lines"]["distribution_energy"] == pytest.approx(customer+float(D(distribution)),abs=1e-9)


@pytest.mark.parametrize("plan", ["RS","GS"])
@pytest.mark.parametrize("month,day,expected_starts", [
    ("2025-09",15,["2025-09-01","2025-09-15"]),
    ("2026-07",15,["2026-07-01","2026-07-15"]),
    ("2026-02",15,["2026-02-01","2026-02-15"]),
])
def test_actual_interval_energy_across_adopted_linear_changes_not_days_weighting(plan,month,day,expected_starts):
    a,idx=fixture(plan,month)
    # Deliberately uneven load: daily uniformity would conceal a rate-allocation bug.
    p=np.where(idx.day<day,.4,2.4)
    got=bill(plan,month,power=p)
    expected=independent_lines(idx,p,plan)
    assert comparable_lines(got["lines"],plan)==pytest.approx(expected,abs=1e-8)
    first,prices,segments=jcpl.cycle_rates(idx,plan)
    assert [s["start_date"] for s in segments]==expected_starts
    assert got["metrics"]["whole_cycle_block_kwh"]==(600. if plan=="RS" else 1000.)
    for key,component in [("transmission_service","transmission"),("transmission_enhancement","TEC")]:
        assert prices[key]==pytest.approx(dated_linear_prices(idx,component),abs=1e-12)
        if len(set(prices[key]))>1:
            day_average=float(np.mean(prices[key]))*float(np.sum(p)*.25)
            assert abs(got["lines"][key]-day_average)>1e-4
    if month=="2026-02":
        assert got["lines"]["zero_emission_certificate"]==0.
        assert segments[-1]["rates"]["zec_status"].lower().find("reserved")>=0


@pytest.mark.parametrize("plan,month", [("RS","2025-07"),("RS","2025-09"),("RS","2026-07"),("GS","2025-09"),("GS","2026-07"),("GS","2026-10")])
def test_fixed_flow_numeric_and_convex_full_itemized_parity(plan,month):
    a,idx=fixture(plan,month)
    p=power_for_energy(idx,1000.004,5.14 if plan=="GS" else None)
    numeric=bill(plan,month,power=p)
    x,y=cp.Variable(len(idx)),cp.Variable(len(idx))
    math=BillingMath(idx,convex=True,power_bound=6.)
    math.register_power(x,np.zeros(len(idx)),np.full(len(idx),6.))
    got=jcpl.charge_lines(idx,x,y,a,math=math)
    problem=cp.Problem(cp.Minimize(sum(got["lines"].values())),[x==p,y==0,*math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status==cp.OPTIMAL
    for key,value in got["lines"].items():
        assert float(value.value if hasattr(value,"value") else value)==pytest.approx(numeric["lines"][key],abs=1e-7)
    assert got["metrics"]["objective_scope"]=="unrounded_ordinary_component_charges"
    assert got["metrics"]["rounded_cash_optimum_claimed"] is False


@pytest.mark.parametrize("day,plan,expected", [("2026-09-01","RS",(.158164,.167389)),("2026-09-01","GS",(.154271,.154271)),("2026-10-01","RS",(.170528,.170528)),("2026-10-01","GS",(.153662,.153662))])
def test_independent_official_september_ptc_and_explicit_october_tec_delta(day,plan,expected):
    # PTC original is explicitlySeptember1; October checked via tariff delta-.000006.
    r=jcpl.rates_on(day,plan)
    l=r["linear_rates"]
    surcharge=sum(l[k] for k in ["transmission_service","transmission_enhancement","bgs_reconciliation","bgs_reliability_must_run"])
    assert tuple(g+surcharge for g in r["generation_energy"])==pytest.approx(expected,abs=1e-12)


@pytest.mark.parametrize("before,after,raw,rounded", [
    ("2025-04-30","2025-05-01","1.58080","1.58"),
    ("2026-07-14","2026-07-15","1.36045","1.36"),
    ("2026-09-30","2026-10-01","-.00390","0.00"),
])
def test_independent_bpu_published_650kwh_transmission_bill_impacts(before,after,raw,rounded):
    def total(day):
        r=jcpl.rates_on(day)["linear_rates"]
        return D(str(r["transmission_service"]))+D(str(r["transmission_enhancement"]))
    delta=D(650)*(total(after)-total(before))
    assert delta==D(raw)
    assert abs(float(delta)-float(D(rounded)))<=.005


@pytest.mark.parametrize("month,amount", [("2025-06",0.),("2025-07",-30.),("2025-08",-30.),("2025-09",10.),("2026-02",10.),("2026-03",0.)])
def test_mandatory_residential_relief_and_recovery_endpoints(month,amount):
    assert bill(month=month)["lines"]["residential_generation_capacity_deferral"]==amount
    assert "residential_generation_capacity_deferral" not in bill("GS",month)["lines"]


def test_negative_relief_settlement_rejects_without_forced_grid_imports():
    with pytest.raises(ValueError,match="negative post-relief"):
        bill(month="2025-07",energy=0.)
    a,idx=fixture(month="2025-07")
    x,y=cp.Variable(len(idx)),cp.Variable(len(idx))
    math=BillingMath(idx,convex=True,power_bound=1.)
    math.register_power(x,np.zeros(len(idx)),np.ones(len(idx)))
    got=jcpl.charge_lines(idx,x,y,a,math=math)
    problem=cp.Problem(cp.Minimize(cp.sum(x)),[x==0,y==0,*math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status==cp.OPTIMAL
    assert sum(float(v.value if hasattr(v,"value") else v) for v in got["lines"].values())==pytest.approx(-25.73)


@pytest.mark.parametrize("day,asof", [("2025-01-01","2023-11-01"),("2025-05-31","2023-11-01"),("2025-06-01","2024-11-01"),("2026-05-31","2024-11-01"),("2026-06-01","2025-11-01")])
def test_pls_reference_year_comes_from_procurement_leaf_not_modeled_peak(day,asof):
    assert jcpl.pls_as_of(day)==asof


@pytest.mark.parametrize("change", [
    dict(gs_no_demand_meter_confirmed=False),dict(gs_minimum_domain_confirmed=False),
    dict(demand_method="metered"),dict(contract_demand_kw=10.001),
    dict(prior_11_actual_peak_upper_bound_kw=10.001),dict(prior_11_actual_peak_upper_bound_kw=True),
    dict(peak_load_share_kw=500.),dict(peak_load_share_kw=-1.),dict(peak_load_share_kw=True),
    dict(peak_load_share_kw=float("nan")),dict(peak_load_share_as_of="2026-11-01"),
    dict(gs_classification_source=""),dict(pls_source=""),
])
def test_gs_utility_assignment_history_contract_and_independent_pls_requirements(change):
    a,idx=fixture("GS")
    with pytest.raises(ValueError):
        jcpl.validate_account({**a,**change},idx)


def test_gs_current15minute_peak10_inclusive_without_borrowed_nearest_tenth_rounding():
    assert bill("GS",peak=10.)["metrics"]["actual_15_minute_peak_kw"]==pytest.approx(10.)
    assert bill("GS",peak=9.9999)["metrics"]["actual_15_minute_peak_kw"]==pytest.approx(9.9999)
    with pytest.raises(ValueError,match="actual15-minute"):
        bill("GS",peak=10.001)
    # One high15-minute import cannot hide behind a30-minute average.
    a,idx=fixture("GS")
    p=power_for_energy(idx);p[:2]=[12.,0.]
    with pytest.raises(ValueError):
        bill("GS",power=p)


def test_conservative_gs_history_carries_actual_peak_without_turning_billed_minimum_into_new_history():
    a,idx=fixture("GS")
    a.update(prior_11_actual_peak_upper_bound_kw=6.,contract_demand_kw=4.)
    first=bill("GS",account=a,peak=8.3)
    assert first["metrics"]["opening_conservative_peak_bound_kw"]==6.
    assert first["next_state"]==dict(gs_history_peak_upper_bound_kw=8.3,through_month="2026-09-01")
    a2,idx2=fixture("GS","2026-10")
    a2.update(prior_11_actual_peak_upper_bound_kw=6.,contract_demand_kw=4.)
    state=deepcopy(first["next_state"])
    second=bill("GS","2026-10",account=a2,state=state,peak=2.)
    assert second["next_state"]==dict(gs_history_peak_upper_bound_kw=8.3,through_month="2026-10-01")
    assert state==first["next_state"]
    assert second["metrics"]["gs_minimum_inactive_verified"] is True


@pytest.mark.parametrize("state", [
    {"gs_history_peak_upper_bound_kw":10.001,"through_month":"2026-08-01"},
    {"gs_history_peak_upper_bound_kw":True,"through_month":"2026-08-01"},
    {"gs_history_peak_upper_bound_kw":5.,"through_month":"2026-07-01"},
    {"gs_history_peak_upper_bound_kw":5.,"through_month":"2026-08-01","credit":0.},
    {"credit":1.},
])
def test_gs_state_requires_immediately_preceding_bounded_history_and_no_credit_bank(state):
    a,idx=fixture("GS")
    with pytest.raises(ValueError):
        jcpl.validate_state(a,idx,state=state)


def test_initial_gs_history_and_rs_no_state_or_demand_assignment():
    a,idx=fixture("GS");a["prior_history_through_month"]="2026-07-01"
    with pytest.raises(ValueError):jcpl.validate_state(a,idx)
    r,idx=fixture()
    with pytest.raises(ValueError):jcpl.validate_state(r,idx,{"credit":0.})
    with pytest.raises(ValueError):jcpl.validate_account({**r,"peak_load_share_kw":1.},idx)


@pytest.mark.parametrize("change", [
    dict(eligibility_confirmed=False),dict(ordinary_service_confirmed=False),
    dict(bgs_rscp_confirmed=False),dict(full_monthly_charges_confirmed=False),
    dict(no_special_provisions_confirmed=False),dict(supply="retail_supplier"),
    dict(export_mode="nem"),dict(tax_exempt=True),dict(phase="three"),
    dict(voltage="primary"),dict(power_factor=.95),dict(meter_count=2),
    dict(meter_count=True),dict(opening_credit_usd=1.),dict(cycle_source=""),
    dict(tax_source=""),dict(rate_evidence_mode="provisional"),
    dict(provisional_assumptions_accepted=True),dict(demand_interval_minutes=30),
])
def test_ordinary_account_facts_unsupported_scope_and_boolean_numeric_rejections(change):
    a,idx=fixture()
    with pytest.raises(ValueError):jcpl.validate_account({**a,**change},idx)


@pytest.mark.parametrize("flag", ["raw_objective_internal","quantity_objective_confirmed","bypass_eligibility"])
def test_no_external_account_flag_can_bypass_verified_contract(flag):
    a,idx=fixture("GS")
    with pytest.raises(ValueError,match="unsupported fields"):
        jcpl.validate_account({**a,flag:True},idx)


@pytest.mark.parametrize("plan", ["RS","GS"])
@pytest.mark.parametrize("change", [
    dict(der_ordinary_service_confirmed=False),dict(der_activation_date="2026-09-02"),
    dict(der_activation_date=""),dict(der_eligibility_source=""),
])
def test_der_requires_already_active_documented_ordinary_service(plan,change):
    a,idx=fixture(plan)
    with pytest.raises(ValueError):
        jcpl.validate_account({**a,**change},idx,equipment=dict(pv=True,battery=True,pv_dc_kw=3.,pv_ac_kw=3.,battery_kw=3.))


def test_small_gs_der_is_not_automatically_standby_exempt_and_pv_storage_can_be_approved():
    a,idx=fixture("GS")
    equipment=dict(pv=True,battery=True,pv_dc_kw=1.,pv_ac_kw=1.,battery_kw=1.)
    jcpl.validate_account(a,idx,equipment=equipment)
    for change in [dict(gs_standby_not_applicable_confirmed=False),dict(gs_standby_source="")]:
        with pytest.raises(ValueError):jcpl.validate_account({**a,**change},idx,equipment=equipment)
    with pytest.raises(ValueError):jcpl.validate_account(a,idx,equipment=dict(pv=False,battery=True,battery_kw=1.))
    # The documented studybound is not presented as an interconnection/STB exemption.
    with pytest.raises(ValueError):jcpl.validate_account(a,idx,equipment=dict(pv=True,pv_dc_kw=25.1,pv_ac_kw=25.1))
    a["der_ordinary_service_confirmed"]=False
    jcpl.validate_account(a,idx,equipment=dict(pv=False,battery=False))


def test_zero_export_settlement_is_enforced_on_numeric_dispatch():
    a,idx=fixture()
    with pytest.raises(ValueError,match="export"):
        jcpl.charge_lines(idx,power_for_energy(idx),np.ones(len(idx))*.001,a,math=BillingMath(idx))


@pytest.mark.parametrize("month,hours,transition_day,day_intervals", [
    ("2025-02",672,None,None),
    ("2025-03",743,"2025-03-09",92),
    ("2025-11",721,"2025-11-02",100),
    ("2026-03",743,"2026-03-08",92),
])
def test_full_calendar_cycles_keep_fixed_charges_through_dst_and_february(month,hours,transition_day,day_intervals):
    a,idx=fixture(month=month)
    assert len(idx)==hours*4
    if transition_day:assert sum(idx.date==pd.Timestamp(transition_day).date())==day_intervals
    review=jcpl.cycle_review(a,idx)
    assert review["elapsed_hours"]==hours
    assert review["monthly_charge_factor"]==1.
    assert review["partial_period_proration_applied"] is False
    assert bill(month=month)["lines"]["distribution_customer"]==4.27


def test_missing_duplicate_shifted_timezone_reversed_and_hourly_data_reject():
    a,idx=fixture(month="2025-03")
    for candidate in [idx[1:],idx[:-1],idx.delete(50),idx.insert(50,idx[50]),idx[::-1],
        idx.tz_convert("America/Chicago"),idx.tz_localize(None),idx+pd.Timedelta(minutes=15),idx[::4]]:
        with pytest.raises(ValueError):jcpl.validate_account(a,candidate)


@pytest.mark.parametrize("change", [dict(bill_date="2026-10-01"),dict(billing_month="2026-08-01"),dict(cycle_kind="final")])
def test_calendar_period_and_statement_dates_must_match_and_partial_cycles_reject(change):
    a,idx=fixture()
    with pytest.raises(ValueError):jcpl.validate_account({**a,**change},idx)
    with pytest.raises(ValueError):jcpl.validate_account(a,idx[96:])


@pytest.mark.parametrize("day", ["2024-12-31","2026-11-01","2027-01-01","2026-9-1","2025-02-29",None,20260901,True])
def test_missing_or_malformed_rate_dates_reject_without_fallback(day):
    with pytest.raises(ValueError):jcpl.rates_on(day)


@pytest.mark.parametrize("day", ["2025-01-01","2025-12-31","2026-01-01","2026-10-31"])
def test_verified_closed_rate_coverage_edges(day):
    assert jcpl.rates_on(day)["tax_basis"].find("retained once")>=0


def test_explicit_adopted_absence_and_deletion_keep_source_clocks_not_missing_rate_fallbacks():
    early=jcpl.rates_on("2025-04-30")
    assert early["linear_rates"]["covid_recovery"]==0.
    assert "not introduced" in early["crc_status"].lower()
    may=jcpl.rates_on("2025-05-01")
    assert may["linear_rates"]["covid_recovery"]==.000358
    assert may["component_versions"]["CRC"]["effective"]=="2025-05-01"
    feb14=jcpl.rates_on("2026-02-14")
    feb15=jcpl.rates_on("2026-02-15")
    assert feb14["linear_rates"]["zero_emission_certificate"]==feb15["linear_rates"]["zero_emission_certificate"]==0.
    assert "reserved" not in feb14["zec_status"].lower()
    assert "reserved" in feb15["zec_status"].lower()
    assert feb15["component_versions"]["ZEC"]["effective"]=="2026-02-15"
    assert jcpl.rates_on("2026-06-01")["linear_rates"]["zero_emission_certificate"]==-.004265
    assert jcpl.rates_on("2026-09-30")["infrastructure_program"]=="RP"
    oct=jcpl.rates_on("2026-10-01")
    assert oct["infrastructure_program"]=="ENJ"
    assert oct["linear_rates"]["infrastructure_reliability"]==.000135
    assert jcpl.rates_on("2026-10-01","GS")["linear_rates"]["infrastructure_reliability"]==.000148


@pytest.mark.parametrize("start,end", [("2025-05-20","2025-06-20"),("2025-08-20","2025-09-20"),("2026-09-20","2026-10-20")])
def test_unsourced_nonlinear_season_and_fixed_crossings_reject(start,end):
    index=build_interval_index(start,end,"America/New_York",15).index
    with pytest.raises(ValueError,match="nonlinear/fixed"):
        jcpl.cycle_rates(index,"RS")


def test_checked_in_official_receipts_and_component_original_pins_are_intact():
    ledger=json.loads((ROOT/"docs/utility_sources/jcpl_nj/sources.json").read_text())
    records=ledger["records"]
    by_source={r.get("source_id"):r for r in records if r.get("source_id")}
    delivery=[r for r in records if r.get("owner_stream")=="delivery"
              and r.get("status")=="official_adopted_tariff"
              and Path(r.get("original_path", "")).suffix.lower()==".pdf"]
    assert len(delivery)==15
    assert by_source["BPU14-Part-III-Eff-1-1-2025"]["original_sha256"]=="da7a42f3b0dcdd1986c143a6d5a116ddc1f98b06857175736946f1b99c7c14a9"
    assert by_source["BPU-14-Part-III-Eff-10-1-2026"]["original_sha256"]=="9b5ea4bbc19fb64214d21b181f6a14805f1b87c8efae9108619b6f4f84057749"
    original_pairs={(r["url"],r["original_sha256"]) for r in records if "original_sha256" in r}
    for record in records:
        for pin in record.get("checked_in_excerpts",[]):
            assert hashlib.sha256((ROOT/pin["path"]).read_bytes()).hexdigest()==pin["sha256"]
    for day in ["2025-01-01","2025-05-01","2026-02-15","2026-07-15","2026-10-01"]:
        r=jcpl.rates_on(day)
        for version in r["component_versions"].values():
            source=version["source"]
            assert (source["url"],source["original_sha256"]) in original_pairs
            if "excerpt_path" in source:
                assert hashlib.sha256((ROOT/source["excerpt_path"]).read_bytes()).hexdigest()==source["excerpt_sha256"]
        assert sum(D(t["per_kWh"]) for t in r["tec_components"])==D(str(r["linear_rates"]["transmission_enhancement"]))
    jul=jcpl.rates_on("2026-07-15")["component_versions"]["RS_base"]["source"]
    assert jul["source_id"]=="BPU-14-Part-III-Eff-7-15-2026" and jul["physical_page"]==4 and jul["printed_leaf"]=="3"
