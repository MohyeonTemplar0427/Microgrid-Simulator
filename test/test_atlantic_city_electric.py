"""Independent filed ACE NJ arithmetic, quantity rules and bounded cycles."""
from copy import deepcopy
from decimal import Decimal as D, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import atlantic_city_electric as ace
from src.billing.atlantic_city_electric_rates import rates_on
from src.billing.regional_math import BillingMath
from src.billing import regional
from src.timeseries import build_interval_index

UTILITY = "atlantic_city_electric_new_jersey"
MGS = "MGS-SECONDARY"


def fixture(plan="RS", start="2026-09-01", days=30, step=15):
    end = str((pd.Timestamp(start) + pd.DateOffset(days=days-1)).date())
    a = ace.hypothetical_defaults(plan, day=start)
    a.update(billing_month=start[:7]+"-01", bill_date=end)
    return a, build_interval_index(start, end, ace.TIMEZONE, step).index


def flows(idx, energy=1000., peak=None):
    x = np.full(len(idx), energy/(len(idx)/4))
    if peak is not None:
        x[0] = peak
        x[1:] = (energy*4-peak)/(len(idx)-1)
    return x


def bill(plan="RS", start="2026-09-01", energy=1000., peak=None, account=None):
    a, idx = fixture(plan, start)
    a = a if account is None else account
    ace.validate_account(a, idx)
    return ace.charge_lines(idx, flows(idx, energy, peak), np.zeros(len(idx)), a, math=BillingMath(idx))


# Direct primary-table literals: old physical RS7/MGS16, current RS7/MGS12.
# SBC/RGGI totals are independently published, never added to their components.
# Supply includes CBT/SUT, generation capacity/ancillary/admin. Negative is credit.
# start,RSdistribution pair,RSgeneration pair,Rtrans,MGSenergy/demand/trans,
# SBC,RGGI/EECEC,NGC,IIPR/IIPG/IIPkW,CIPR/CIPG,ZEC,recon,TECR/TECG,RSrelief,Gcustomer.
CASES = [
    ("2025-04-01", [".074735"]*2, [".094339"]*2, ".041092", ".050317", "2.86", "7.86", ".011455", ".005660", ".003672", ".001711", ".001475", ".05", ".004224", "-.013181", ".004265", "-.005854", ".002709", ".002031", "0", "12.55"),
    ("2025-05-01", [".074735"]*2, [".094339"]*2, ".041092", ".050317", "2.86", "7.86", ".011455", ".005660", ".003672", ".001711", ".001475", ".05", ".004224", "-.013181", ".004265", "-.005854", ".002997", ".002144", "0", "12.55"),
    ("2025-06-01", [".082119", ".096411"], [".130407", ".140360"], ".041092", ".056849", "3.49", "8.24", ".009300", ".007121", "0", ".001711", ".001475", ".05", ".008859", "-.009008", "0", ".004652", ".002997", ".002144", "0", "12.55"),
    ("2025-07-01", [".082119", ".096411"], [".130407", ".140360"], ".041092", ".056849", "3.49", "8.24", ".009300", ".007121", "0", ".001711", ".001475", ".05", ".008859", "-.009008", "0", ".004652", ".002997", ".002144", "-30", "12.55"),
    ("2025-10-01", [".074735"]*2, [".139134"]*2, ".035260", ".050317", "2.86", "5.53", ".010839", ".007121", "0", ".001711", ".001475", ".05", ".008859", "-.009008", "0", ".009954", ".002979", ".002027", "10", "12.55"),
    ("2025-11-01", [".074735"]*2, [".139134"]*2, ".035260", ".050317", "2.86", "5.53", ".010839", ".007121", "0", ".001711", ".001475", ".05", ".008859", "-.009008", "0", ".009954", ".002979", ".002027", "10", "12.55"),
    ("2026-09-01", [".095030", ".111568"], [".130325", ".140300"], ".035260", ".061560", "3.89", "5.92", ".010672", ".007121", "0", "0", "0", "0", ".007279", ".002392", "-.004265", "0", ".003144", ".001862", "0", "13.99"),
    ("2026-10-01", [".086485"]*2, [".140672"]*2, ".037688", ".054488", "3.19", "6.49", ".009749", ".010510", "0", ".000442", ".000269", ".02", ".001819", ".002096", "-.004265", "0", ".003174", ".001905", "0", "13.99"),
]


@pytest.mark.parametrize("plan", ["RS", MGS])
@pytest.mark.parametrize("row", CASES, ids=[r[0] for r in CASES])
def test_independent_component_stack_and_primary_published_rider_totals(plan, row):
    (start, rd, rg, rt, ge, gd, gt, sbc, rggi, ngc, ir, ig, ik, cr, cg, zec,
     recon, tr, tg, relief, gc) = row
    got = bill(plan, start, energy=1000., peak=5.14 if plan == MGS else None)
    lines = got["lines"]; e = D("1000"); peak = D("5.1")
    def tier(pair):
        return e*D(pair[0]) if pair[0] == pair[1] else D("750")*D(pair[0])+D("250")*D(pair[1])
    assert lines["distribution_customer"] == float("6.75" if plan == "RS" else gc)
    assert lines["distribution_energy"] == pytest.approx(float(tier(rd) if plan == "RS" else e*D(ge)))
    expected_gen = tier(rg) if plan == "RS" else e*D(".091262" if start < "2025-06" else ".121496" if start < "2025-09" else ".114061" if start < "2026" else ".119776" if start < "2026-10" else ".113017")
    assert lines["generation_energy"] == pytest.approx(float(expected_gen))
    assert sum(v for k,v in lines.items() if k.startswith("societal_")) == pytest.approx(float(e*D(sbc)))
    assert sum(v for k,v in lines.items() if k.startswith(("rggi_", "eecec_"))) == pytest.approx(float(e*D(rggi)))
    expected = dict(non_utility_generation=ngc, infrastructure_energy=ir if plan == "RS" else ig,
        conservation_incentive=cr if plan == "RS" else cg, zero_emission_certificate=zec,
        bgs_reconciliation=recon, transmission_enhancement=tr if plan == "RS" else tg)
    for key, value in expected.items():
        assert lines[key] == pytest.approx(float(e*D(value)), abs=1e-9)
    assert lines["transition_bond"] == lines["market_transition_tax"] == lines["excess_deferred_income_tax"] == lines["reliability_must_run"] == 0.
    if plan == "RS":
        assert lines["transmission_energy"] == pytest.approx(float(e*D(rt)))
        assert lines["residential_capacity_deferral"] == float(relief)
    else:
        assert lines["distribution_demand"] == pytest.approx(float(peak*D(gd)))
        assert lines["infrastructure_demand"] == pytest.approx(float(peak*D(ik)))
        assert lines["transmission_demand"] == pytest.approx(float((peak-D("3"))*D(gt)))
        assert lines["reactive_demand"] == lines["minimum_bill_adjustment"] == 0.
    assert got["is_complete_bill"] is True and got["excluded_components"] == []
    assert got["rate_evidence_status"] == "verified" and got["rate_assumptions"] == []
    assert got["metrics"]["additional_tax_percentage_applied"] is False
    assert not {"sales_tax", "gross_receipts_tax", "supply_administration", "pjm_capacity", "wholesale_energy", "nspl"} & set(lines)


@pytest.mark.parametrize("energy", [749.99, 750., 750.01, 1000.])
@pytest.mark.parametrize("start,distribution,generation", [
    ("2025-06-01", [".082119", ".096411"], [".130407", ".140360"]),
    ("2026-09-01", [".095030", ".111568"], [".130325", ".140300"]),
])
def test_rs750kwh_tier_inclusive_distribution_and_supply(start, distribution, generation, energy):
    got = bill(start=start, energy=energy)
    for key,pair in [("distribution_energy",distribution),("generation_energy",generation)]:
        expected = min(D(str(energy)),D("750"))*D(pair[0])+max(D(str(energy))-D("750"),D("0"))*D(pair[1])
        assert got["lines"][key] == pytest.approx(float(expected), abs=1e-9)


def test_rs_raw_energy_does_not_borrow_mgs_quantity_rounding():
    got = bill(start="2026-10-01", energy=1000.005)
    assert got["metrics"]["billed_import_kwh"] == pytest.approx(1000.005)
    assert got["metrics"]["quantity_basis"] == "raw_rs_energy"
    assert got["lines"]["distribution_energy"] == pytest.approx(1000.005*.086485)


@pytest.mark.parametrize("peak,expected", [(2.94,0.),(3.,0.),(3.04,0.),(3.06,.1)])
def test_mgs_transmission_first3kw_only_while_distribution_and_iip_charge_all_kw(peak, expected):
    got = bill(MGS, "2026-10-01", peak=peak)
    billed = got["metrics"]["billed_peak_kw"]
    assert got["lines"]["transmission_demand"] == pytest.approx(expected*6.49)
    assert got["lines"]["distribution_demand"] == pytest.approx(billed*3.19)
    assert got["lines"]["infrastructure_demand"] == pytest.approx(billed*.02)


def test_mgs_final_quantities_raw_proxy_and_bounded_difference_without_cash_optimum_claim():
    a, idx = fixture(MGS)
    x = flows(idx,1000.004,5.14)
    final = ace.charge_lines(idx,x,np.zeros(len(idx)),a,math=BillingMath(idx))
    proxy_a, state = ace.objective_inputs(a)
    raw = ace.charge_lines(idx,x,np.zeros(len(idx)),proxy_a,math=BillingMath(idx),state=state)
    assert final["metrics"]["raw_import_kwh"] == pytest.approx(1000.004)
    assert final["metrics"]["raw_peak_kw"] == pytest.approx(5.14)
    assert final["metrics"]["billed_import_kwh"] == pytest.approx(1000.)
    assert final["metrics"]["billed_peak_kw"] == pytest.approx(5.1)
    assert raw["metrics"]["billed_import_kwh"] == pytest.approx(1000.004)
    assert raw["metrics"]["quantity_basis"] == "raw_objective_proxy"
    assert final["metrics"]["optimization_objective_scope"] == ace.RAW_OBJECTIVE
    assert final["metrics"]["rounded_cash_optimum_claimed"] is False
    difference = abs(sum(final["lines"].values())-sum(raw["lines"].values()))
    assert 0 < difference <= final["metrics"]["quantity_rounding_charge_error_bound_usd"]
    # Losing the internal type through JSON-like serialization restores final rounding.
    copied = ace.charge_lines(idx,x,np.zeros(len(idx)),dict(proxy_a),math=BillingMath(idx))
    assert copied["metrics"]["quantity_basis"] == "filed_nearest_quantities_no_half_ties"
    assert a == ace.hypothetical_defaults(MGS) | {"billing_month":"2026-09-01","bill_date":"2026-09-30"}


@pytest.mark.parametrize("energy,peak", [(1000.005,5.14),(1000.004,5.15)])
def test_mgs_exact_half_ties_reject_without_unsourced_tie_convention(energy,peak):
    with pytest.raises(ValueError,match="half ties"):
        bill(MGS,energy=energy,peak=peak)


@pytest.mark.parametrize("flag,value", [("quantity_basis","raw_objective_proxy"),("skip_rounding",True),("_raw_quantity_objective",True)])
def test_external_account_cannot_forge_internal_rounding_bypass(flag,value):
    a,idx=fixture(MGS)
    with pytest.raises(ValueError,match="unsupported fields"):
        ace.validate_account({**a,flag:value},idx)


@pytest.mark.parametrize("plan", ["RS", MGS])
@pytest.mark.parametrize("start", ["2025-04-01","2025-06-01","2026-09-01","2026-10-01"])
def test_fixed_flow_numeric_symbolic_parity_on_disclosed_objective(plan,start):
    a,idx=fixture(plan,start)
    objective,state=ace.objective_inputs(a)
    imports=flows(idx,1000.004,5.14 if plan==MGS else None)
    raw=ace.charge_lines(idx,imports,np.zeros(len(idx)),objective,math=BillingMath(idx),state=state)
    x,y=cp.Variable(len(idx)),cp.Variable(len(idx))
    math=BillingMath(idx,convex=True,power_bound=6.)
    math.register_power(x,np.zeros(len(idx)),np.full(len(idx),6.))
    got=ace.charge_lines(idx,x,y,objective,math=math,state=state)
    problem=cp.Problem(cp.Minimize(sum(got["lines"].values())),[x==imports,y==0,*math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status==cp.OPTIMAL
    for key,value in got["lines"].items():
        assert float(value.value if hasattr(value,"value") else value)==pytest.approx(raw["lines"][key],abs=1e-8)


@pytest.mark.parametrize("start,amount", [("2025-06-01",0.),("2025-07-01",-30.),("2025-08-01",-30.),("2025-10-01",10.),("2025-11-01",10.),("2026-09-01",0.)])
def test_mandatory_residential_capacity_deferral_recovery_dates(start,amount):
    assert bill(start=start)["lines"]["residential_capacity_deferral"]==amount
    assert "residential_capacity_deferral" not in bill(MGS,start)["lines"]


def test_negative_post_relief_balance_rejects_without_extra_import_constraints():
    with pytest.raises(ValueError,match="negative post-relief"):
        bill(start="2025-07-01",energy=0.)
    a,idx=fixture(start="2025-07-01")
    x,y=cp.Variable(len(idx)),cp.Variable(len(idx))
    math=BillingMath(idx,convex=True,power_bound=1.)
    math.register_power(x,np.zeros(len(idx)),np.ones(len(idx)))
    got=ace.charge_lines(idx,x,y,a,math=math)
    problem=cp.Problem(cp.Minimize(cp.sum(x)),[x==0,y==0,*math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status==cp.OPTIMAL
    assert float(sum(v.value if hasattr(v,"value") else v for v in got["lines"].values())) == pytest.approx(-23.25)


@pytest.mark.parametrize("day,assignment", [("2025-04-01","2023-11-01"),("2025-05-31","2023-11-01"),("2025-06-01","2024-11-01"),("2025-11-01","2024-11-01"),("2026-09-01","2025-11-01")])
def test_pls_year_is_prior_annual_assignment_independent_of_monthly_demand(day,assignment):
    assert ace.pls_as_of(day)==assignment


@pytest.mark.parametrize("change", [dict(peak_load_share_kw=500.),dict(peak_load_share_kw=-1.),dict(peak_load_share_kw=True),dict(peak_load_share_kw=float("nan")),dict(peak_load_share_as_of="2026-11-01"),dict(pls_source=""),dict(bgs_rscp_confirmed=False),dict(demand_method="unmetered"),dict(quantity_objective_confirmed=False)])
def test_independent_mgs_pls_enrollment_and_metering_requirements(change):
    a,idx=fixture(MGS)
    with pytest.raises(ValueError):
        ace.validate_account({**a,**change},idx)


@pytest.mark.parametrize("start,hours,day,count", [("2025-03-02",719,"2025-03-09",92),("2025-11-01",721,"2025-11-02",100)])
def test_exact30_local_days_preserve_dst_elapsed_intervals(start,hours,day,count):
    a,idx=fixture(start=start)
    assert len(idx)==hours*4
    assert sum(idx.date==pd.Timestamp(day).date())==count
    review=ace.cycle_review(a,idx)
    assert review["cycle_days"]==30 and review["elapsed_hours"]==hours
    assert review["partial_period_proration_applied"] is False
    assert bill(start=start)["lines"]["distribution_customer"]==6.75


@pytest.mark.parametrize("start,days", [("2025-02-01",28),("2025-02-01",30),("2025-06-01",29),("2026-10-01",31),("2025-08-20",30),("2025-09-01",30),("2025-12-01",30),("2026-08-01",30)])
def test_non30day_crossmonth_and_unverified_cycles_reject(start,days):
    a,idx=fixture(start=start,days=days)
    with pytest.raises(ValueError):
        ace.validate_account(a,idx)


@pytest.mark.parametrize("day", ["2025-01-31","2025-09-01","2025-12-01","2026-01-01","2026-08-31","2026-11-01","2027-01-01","2026-9-1",None,20260901])
def test_missing_rate_windows_and_malformed_dates_reject(day):
    with pytest.raises(ValueError):
        rates_on(day)


@pytest.mark.parametrize("change", [dict(eligibility_confirmed=False),dict(ordinary_service_confirmed=False),dict(full_monthly_charges_confirmed=False),dict(no_special_provisions_confirmed=False),dict(supply="retail_supplier"),dict(export_mode="nem"),dict(tax_exempt=True),dict(phase="three"),dict(voltage="primary"),dict(power_factor=.95),dict(meter_count=2),dict(service_line_count=2),dict(opening_credit_usd=1.),dict(cycle_source=""),dict(tax_source=""),dict(rate_evidence_mode="provisional"),dict(provisional_assumptions_accepted=True),dict(demand_interval_minutes=30)])
def test_ordinary_account_and_supported_scope_confirmations(change):
    a,idx=fixture()
    with pytest.raises(ValueError):
        ace.validate_account({**a,**change},idx)


def test_missing_duplicate_shifted_timezone_hourly_grid_rejects():
    a,idx=fixture()
    for candidate in [idx[1:],idx[:-1],idx.delete(30),idx.insert(30,idx[30]),idx[::-1],idx.tz_convert("America/Chicago"),idx+pd.Timedelta(minutes=15)]:
        with pytest.raises(ValueError):
            ace.validate_account(a,candidate)
    _,hourly=fixture(step=60)
    with pytest.raises(ValueError):
        ace.validate_account(a,hourly)


def test_der_historical_mgs_boundary_approval_size_and_export_rejections():
    equipment=dict(pv=True,battery=True,pv_dc_kw=5.,pv_ac_kw=4.,battery_kw=3.)
    for plan in ("RS",MGS):
        a,idx=fixture(plan)
        ace.validate_account(a,idx,equipment)
        for change in [dict(der_ordinary_service_confirmed=False),dict(der_eligibility_source="")]:
            with pytest.raises(ValueError):ace.validate_account({**a,**change},idx,equipment)
        with pytest.raises(ValueError):ace.validate_account(a,idx,{**equipment,"battery_kw":21.})
        with pytest.raises(ValueError):ace.validate_account(a,idx,dict(pv=False,battery=True))
        with pytest.raises(ValueError):ace.charge_lines(idx,np.ones(len(idx)),np.ones(len(idx)),a,math=BillingMath(idx))
        with pytest.raises(ValueError):ace.validate_state(a,idx,state={"credit":1.})
    a,idx=fixture(MGS,"2025-06-01")
    with pytest.raises(ValueError,match="MGS2025"):
        ace.validate_account(a,idx,equipment)
    a,idx=fixture("RS","2025-06-01")
    ace.validate_account(a,idx,equipment)


def test_independent650kwh_transmission_tec_change_and_regional_monetary_rounding():
    # Filed Sep/Oct2026 transmission+TEC delta, consistent with BPU1.60 example.
    old= bill(start="2026-09-01",energy=650.)
    new= bill(start="2026-10-01",energy=650.)
    component=lambda g:g["lines"]["transmission_energy"]+g["lines"]["transmission_enhancement"]
    assert component(new)-component(old)==pytest.approx(1.5977,abs=1e-10)
    assert D("650")*((D(".037688")+D(".003174"))-(D(".035260")+D(".003144")))==D("1.597700")
    rounded=[]
    for start in ["2026-09-01","2026-10-01"]:
        a,idx=fixture(start=start)
        got=regional.calculate_cycle(UTILITY,idx,flows(idx,650.),np.zeros(len(idx)),a)
        rounded.append(got["lines"]["transmission_energy"]+got["lines"]["transmission_enhancement"])
        assert got["is_complete_bill"] is True
        assert abs(got["total_usd"]-got["unrounded_total_usd"])<=got["rounding_bound_usd"]
    assert rounded[1]-rounded[0]==pytest.approx(1.60)


@pytest.mark.parametrize("day,sha", [
    ("2025-04-01","c53ed2072e2c04d1150722b1fc9399ea7199bd1fba5ecb99d8631772ec7acb98"),
    ("2025-06-01","a032686b1816d6b813ee262a0855b32ed9bb0bc91440dad3dbaaa85ca7bc9d93"),
    ("2025-10-01","c081b6e50e5ae4cefad05b12414c4b18f4febdad32b84194f45debaa0d9ec08e"),
    ("2026-09-01","438ba7ab5a72a022a7813dac8efbb4faf45fba057cd9f5efad4c2e60d783ff92"),
    ("2026-10-01","b46c4e1786734a0e4307f47cfbada8818262601b65270ebc026dfd94e06016d3"),
])
def test_source_identity_is_pinned_to_independent_original_receipt(day,sha):
    got=rates_on(day)
    assert got["source"]["sha256"]==sha
    root=Path(__file__).resolve().parents[1]
    ledger=json.loads((root/"docs/utility_sources/atlantic_city_electric/sources.json").read_text())
    assert any(r["original_sha256"]==sha for r in ledger["records"])


def test_checked_in_original_excerpt_sha_receipts_are_intact():
    root=Path(__file__).resolve().parents[1]
    ledger=json.loads((root/"docs/utility_sources/atlantic_city_electric/sources.json").read_text())
    checked=0
    for record in ledger["records"]:
        for excerpt in record.get("checked_in_excerpts",[]):
            assert hashlib.sha256((root/excerpt["path"]).read_bytes()).hexdigest()==excerpt["sha256"]
            checked+=1
    assert checked>=10


def test_may_tec_is_new_adopted_source_without_repricing_base_riders():
    april=rates_on("2025-04-30");may=rates_on("2025-05-01")
    assert april["energy_rates"]["transmission_enhancement"]==.002709
    assert may["energy_rates"]["transmission_enhancement"]==.002997
    assert may["source_components"]["supply"]["TEC"]["effective"]=="2025-05-01"
    assert april["distribution_energy"]==may["distribution_energy"]==(.074735,.074735)


def test_catalog_objective_and_default_account_scope():
    for plan in ace.PLANS:
        assert ace.defaults(plan)["eligibility_confirmed"] is False
    for entry in ace.catalog():
        assert entry["solar_modes"]==["non_export"] and entry["interval_minutes"]==[15]
        assert all(c["is_complete_bill"] is True for c in entry["coverage"])
        assert any("Exactly30" in x for x in entry["limitations"])
    with pytest.raises(ValueError):
        ace.objective_inputs(ace.hypothetical_defaults(),policy="cash_bill")


def test_july_relief_rejects_negative_component_cents_even_when_raw_total_is_zero():
    a, idx = fixture(start="2025-07-01")
    imports = flows(idx, 80.65691151676623)
    # This source-valued boundary has raw charges approximately zero, but
    # independent half-up rounding of its components produces a negative cent.
    # Refund/carry handling is unsupported; acceptance must reject that balance.
    with pytest.raises(ValueError, match="negative"):
        regional.calculate_cycle(UTILITY, idx, imports, np.zeros(len(idx)), a)


def test_may_tec_provenance_points_to_june_original_not_february_book():
    may = rates_on("2025-05-01")
    source = may["source_components"]["supply"]["TEC"]["source"]
    assert source["id"] == "section_iv_jun2025"
    assert source["sha256"] == "a032686b1816d6b813ee262a0855b32ed9bb0bc91440dad3dbaaa85ca7bc9d93"
    assert "683f33006dffb339d38ca110" in source["url"]
