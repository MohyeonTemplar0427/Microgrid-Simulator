"""UGI dated bill benchmarks and ordinary-service eligibility boundaries."""
from decimal import Decimal as D, ROUND_HALF_UP

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import regional, ugi_pa as ugi
from src.billing.regional_math import BillingMath
from src.billing.ugi_pa_rates import rates_for_month

# Independently transcribed by calendar quarter / supply season in $/kWh and decimal
# fractions. The production chronology uses supplement-effective dates and source units.
DSIC = {2025: [".0032", ".0074", ".0123", ".0141"],
        2026: [".0183", ".0228", ".0325", ".0446"]}


def independent(plan, month, kwh):
    """Unrounded signed Decimal line items, independent of production rate lookups."""
    r = plan == "R"
    year, mo = map(int, month[:7].split("-"))
    if year not in DSIC or month[:7] in {"2025-01", "2025-09", "2026-01", "2026-07", "2026-10"}:
        raise ValueError("Unverified UGI interval")
    if month < "2025-06":
        supply, usp = ".10637", ".02121"
    elif month < "2025-12":
        supply, usp = (".11470" if r else ".11005"), ".02222"
    elif month < "2026-06":
        supply, usp = (".11211" if r else ".10758"), ".01868"
    elif month < "2026-12":
        supply, usp = (".12616" if r else ".12093"), ".02120"
    elif not r:
        supply, usp = ".11886", None
    else:
        raise ValueError("Unverified December 2026 residential USP")
    if month < "2025-09":
        efficiency = ".00151" if r else ".00122"
    elif month < "2026-09":
        efficiency = ".00181" if r else ".00233"
    else:
        efficiency = ".00170" if r else ".00343"
    if month < "2025-09" or "2026-02" <= month < "2026-07":
        stas = ".0001"
    elif month < "2026-02":
        stas = ".0002"
    elif month < "2026-10":
        stas = "0"
    else:
        stas = "-.0001"
    e = D(str(kwh))
    customer = D("10.75" if r else "17")
    delivery = e*D(".05290" if r else ".05987")
    conservation = e*D(efficiency)
    use = e*D(usp) if r else D("0")
    delivery_total = customer + delivery + conservation + use
    improvement = delivery_total*D(DSIC[year][(mo-1)//3])
    generation = e*D(supply)
    state = (delivery_total + improvement + generation)*D(stas)
    sale = D(0) if r else (delivery_total + improvement + generation + state)*D(".06")
    lines = dict(distribution_customer=customer, distribution_energy=delivery, energy_efficiency=conservation,
                 distribution_dsic=improvement, default_service_supply=generation,
                 state_tax_adjustment=state, sales_tax=sale)
    if r:
        lines["universal_service"] = use
    return lines


def fixture(plan, month):
    start = pd.Timestamp(month, tz=ugi.TIMEZONE)
    idx = pd.date_range(start, start+pd.offsets.MonthBegin(), inclusive="left", freq="15min")
    return ugi.hypothetical_defaults(plan, day=month), idx


MONTHS = {2025: [2, 3, 4, 5, 6, 7, 8, 10, 11, 12],
          2026: [2, 3, 4, 5, 6, 8, 9, 11]}
CASES = [(p, f"{year}-{m:02}-01") for p in ("R", "GS-1") for year, months in MONTHS.items() for m in months]
CASES.append(("GS-1", "2026-12-01"))


@pytest.mark.parametrize("plan,month", CASES)
def test_each_verified_cycle_and_independent_rounded_line_items(plan, month):
    a, idx = fixture(plan, month)
    kwh = 811.397
    power = np.full(len(idx), kwh * 4 / len(idx))
    bill = regional.calculate_cycle(ugi.UTILITY, idx, power, np.zeros(len(idx)), a)
    expected = independent(plan, month, kwh)
    assert bill["unrounded_lines"] == pytest.approx({k: float(v) for k, v in expected.items()}, abs=1e-9)
    cents = {k: float(v.quantize(D(".01"), rounding=ROUND_HALF_UP)) for k, v in expected.items()}
    assert bill["lines"] == cents and bill["total_usd"] == pytest.approx(sum(cents.values()))
    assert bill["is_complete_bill"] and bill["next_state"] == {} and bill["rate_evidence_status"] == "verified"
    if month == "2026-12-01":
        assert bill["metrics"]["coverage_timing"] == "published_forward_as_of_2026-11-19"
    elif month == "2026-11-01":
        assert bill["metrics"]["coverage_timing"] == "in_progress_as_of_2026-11-19"


@pytest.mark.parametrize("plan", ["R", "GS-1"])
@pytest.mark.parametrize("month", ["2024-12-01", "2025-01-01", "2025-09-01", "2026-01-01",
                                   "2026-07-01", "2026-10-01", "2027-01-01"])
def test_incomplete_or_transition_month_refuses(plan, month):
    a, idx = fixture(plan, month)
    with pytest.raises(ValueError, match="coverage"):
        ugi.validate_account(a, idx)


def test_residential_december_usp_and_source_units():
    with pytest.raises(ValueError, match="coverage"):
        rates_for_month("2026-12-01", "R")
    # Each website PTC includes signed STAS, rounded to three decimals in cents.
    for month, plan, expected in (("2026-11-01","R","12.615"), ("2026-11-01","GS-1","12.092"),
                                  ("2026-12-01","GS-1","11.885")):
        r = rates_for_month(month, plan)
        ptc = D(str(r["supply"]))*100*(1+D(str(r["stas"])))
        assert ptc.quantize(D(".001"), rounding=ROUND_HALF_UP) == D(expected)


def test_rate_case_workpaper_customer_example_and_both_classes():
    # March 2026 Book IV Exhibit E pp 2–3 uses projected 5% DSIC and 0.02% STAS.
    # Reconstruct its reported line revenue using printed volumes, independently
    # of our historical DSIC/ STAS selection.
    for energy, supplied, bills, r, reported in [
        (546871123, 541259042, 663984, True, (2307136, 21826)),
        (25191069, 21623599, 63936, False, (132690, 1023)),
    ]:
        base = D(bills)*D("10.75" if r else "17")+D(energy)*D(".05290" if r else ".05987")
        eec = D(energy)*D(".00181" if r else ".00233")
        usp = D(486379928)*D(".01868") if r else D(0)
        dsic = (base+eec+usp)*D(".05")
        stas = (base+eec+usp+dsic+D(supplied)*D(".11211" if r else ".10758"))*D(".0002")
        assert (round(dsic), round(stas)) == reported
    projected = ((D("10.75")+D("52.90")+D("18.68")+D("1.81"))*D("1.05")+D("112.11"))*D("1.0002")
    assert projected.quantize(D(".01"), rounding=ROUND_HALF_UP) == D("200.50")
    assert rates_for_month("2026-03-01","R")["dsic"] == pytest.approx(.0183)


@pytest.mark.parametrize("plan,month", [("R","2025-03-01"), ("GS-1","2025-11-01"),
                                       ("R","2026-11-01"), ("GS-1","2026-12-01")])
def test_affine_symbolic_and_numeric_lines_match(plan, month):
    a, idx = fixture(plan, month)
    p = np.linspace(.01, 2., len(idx))
    imports, exports = cp.Variable(len(idx)), cp.Variable(len(idx))
    math = BillingMath(idx, convex=True, power_bound=5.)
    math.register_power(imports, np.zeros(len(p)), np.full(len(p), 5.))
    symbolic = ugi.charge_lines(idx, imports, exports, a, math=math)
    problem = cp.Problem(cp.Minimize(sum(symbolic["lines"].values())),
                         [imports == p, *math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status == cp.OPTIMAL and np.max(np.abs(exports.value)) < 1e-9
    actual = {k: float(v.value if hasattr(v,"value") else v) for k, v in symbolic["lines"].items()}
    assert actual == pytest.approx({k: float(v) for k, v in independent(plan, month, p.sum()/4).items()})
    empty = ugi.charge_lines(idx, np.zeros(len(p)), np.zeros(len(p)), a, math=BillingMath(idx))
    assert empty["metrics"]["monthly_minimum_usd"] == (10.75 if plan == "R" else 17.)
    assert empty["lines"]["distribution_customer"] == empty["metrics"]["monthly_minimum_usd"]


@pytest.mark.parametrize("month,hours", [("2025-03-01",743), ("2025-11-01",721)])
def test_dst_and_exact_cycle_account(month, hours):
    a, idx = fixture("R", month)
    assert ugi.cycle_review(a, idx)[0]["elapsed_hours"] == hours
    for bad in (idx.delete(100), idx.insert(100, idx[100]), idx.tz_convert("UTC"), idx[1:]):
        with pytest.raises(ValueError):
            ugi.validate_account(a, bad)
    with pytest.raises(ValueError):
        ugi.validate_account({**a, "bill_date": str((idx[-1]+pd.Timedelta(days=1)).date())}, idx)


@pytest.mark.parametrize("key,value", [
    ("eligibility_confirmed", False), ("ordinary_service_confirmed", 1), ("fixed_default_supply_confirmed", False),
    ("supply","shopping"), ("tax_jurisdiction","allegheny"), ("tax_exempt",True),
    ("opening_credit_usd",2.), ("export_mode","net_metering"), ("meter_count",True),
    ("gs_non_demand_confirmed",False), ("gs_prior_peak_upper_bound_kw",5.01),
    ("gs_supply_peak_impact_kw",100.), ("gs_review_source",""), ("rate_evidence_mode","provisional"),
])
def test_reject_ineligible_or_unconfirmed_accounts(key, value):
    a, idx = fixture("GS-1","2025-06-01")
    with pytest.raises(ValueError):
        ugi.validate_account({**a, key:value}, idx)


def test_old_and_new_supply_classes_are_distinct():
    for month, allowed in (("2025-05-01",True), ("2025-06-01",False)):
        a, idx = fixture("GS-1", month)
        a.update(gs_prior_peak_upper_bound_kw=5., gs_supply_peak_impact_kw=None)
        if allowed:
            ugi.validate_account(a, idx)
        else:
            with pytest.raises(ValueError, match="supply peak"):
                ugi.validate_account(a, idx)
    a, idx = fixture("R","2025-06-01")
    with pytest.raises(ValueError):
        ugi.validate_account({**a, "residential_use_confirmed":False}, idx)
    with pytest.raises(ValueError):
        ugi.validate_account(ugi.defaults("R"), idx)


def test_native_load_imports_bank_and_settlement_boundaries():
    a, idx = fixture("GS-1","2025-03-01")
    for p in (np.full(len(idx), 3.), np.r_[5.001, np.zeros(len(idx)-1)],
              np.r_[np.nan, np.zeros(len(idx)-1)], np.array([-1.])):
        with pytest.raises(ValueError):
            ugi.validate_native_load(a, p)
    ugi.validate_native_load(a, np.r_[5., np.zeros(len(idx)-1)])
    with pytest.raises(ValueError):
        ugi.validate_state(a, idx, {"credit":1.})
    with pytest.raises(ValueError, match="exports"):
        ugi.charge_lines(idx, np.ones(len(idx)), np.ones(len(idx)), a, math=BillingMath(idx))
    with pytest.raises(ValueError, match="2,000"):
        ugi.charge_lines(idx, np.full(len(idx), 3.), np.zeros(len(idx)), a, math=BillingMath(idx))


def test_approved_pv_and_paired_battery_only():
    a, idx = fixture("R","2025-03-01")
    system = dict(pv=True, pv_dc_kw=2., pv_ac_kw=1.5, battery=True, battery_kw=1.,
                  renewable_only_charging=True, no_battery_export=True)
    ugi.validate_account(a, idx, system)
    for account_change, system_change in [
        ({"der_ordinary_service_confirmed":False}, {}), ({"der_activation_date":"2025-03-02"}, {}),
        ({"battery_interconnection_confirmed":False}, {}), ({"der_eligibility_source":""}, {}),
        ({}, {"pv":False}), ({}, {"renewable_only_charging":False}), ({}, {"no_battery_export":False}),
        ({}, {"battery_kw":9.}), ({}, {"pv_dc_kw":float("nan")}),
    ]:
        with pytest.raises(ValueError):
            ugi.validate_account({**a, **account_change}, idx, {**system, **system_change})
