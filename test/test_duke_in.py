"""Independent Duke Indiana billing arithmetic and strict supported-scope checks."""
from datetime import timedelta, timezone
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import duke_in as duke
from src.billing.duke_in_rates import service_rates
from src.billing.regional import calculate_cycle
from src.billing.regional_math import BillingMath
from src.dispatch.regional import optimize_cycle
from src.timeseries import build_interval_index


def fixture(plan="RS", step=15):
    return duke.hypothetical_defaults(plan), build_interval_index("2025-03-01", "2025-03-31", duke.TIMEZONE, step).index


@pytest.mark.parametrize("plan", duke.PLANS)
@pytest.mark.parametrize("kwh", [0, 150, 300, 450, 1000, 1500, 2500, 4000])
def test_independent_bill_benchmark(plan, kwh):
    a, idx = fixture(plan)
    residential = plan.startswith("RS")
    volume = D(kwh)
    if plan.endswith("-TOU"):
        counts = dict(peak=0, discount=0, off=0)
        # Independent local offset arithmetic, not the adapter's periods/rates.
        for stamp in idx.to_pydatetime():
            est = stamp.astimezone(timezone(timedelta(hours=-5)))
            hour = est.hour+est.minute/60
            is_peak = 17 <= hour < 21 or not stamp.dst() and 6 <= hour < 8
            counts["peak" if is_peak else "discount" if 0 <= hour < 4 else "off"] += 1
        prices = (".214198", ".142799", ".085679") if residential else (".169081", ".148754", ".097014")
        energy = volume*sum(D(counts[k])*D(price) for k, price in zip(("peak", "off", "discount"), prices))/D(len(idx))
    else:
        bounds = (300, 1000) if residential else (300, 1000, 2500)
        prices = (".186556", ".135777", ".123051") if residential else (".178612", ".165677", ".150517", ".122691")
        energy = D(0); previous = 0; remaining = kwh
        for limit, price in zip(bounds, prices):
            used = min(max(remaining, 0), limit-previous)
            energy += D(used)*D(price); remaining -= used; previous = limit
        energy += D(remaining)*D(prices[-1])
    rider_values = ("-.001521", ".003339", ".002259", ".002137", "-.014131", "-.000105", ".000984", "0", ".000038", "-.000206") if residential else ("-.001521", ".003699", ".001874", ".001669", "-.013589", "-.000073", ".001010", "0", ".000028", "-.000215")
    names = ("fuel", "environmental", "tdsic", "energy_efficiency", "credits_adjustment", "rto_non_fuel", "reliability", "federal_mandate", "renewable_projects", "load_control")
    expected = dict(customer=D("13.70" if residential else "13.91"), energy=energy)
    expected.update({name: volume*D(price) for name, price in zip(names, rider_values)})
    expected["indiana_sales_tax"] = sum(expected.values())*D(".07")
    load = np.full(len(idx), kwh/(len(idx)/4))
    result = calculate_cycle(duke.UTILITY, idx, load, np.zeros(len(idx)), a)
    assert result["unrounded_lines"] == pytest.approx({k: float(v) for k, v in expected.items()}, abs=1e-8)
    assert result["unrounded_total_usd"] == pytest.approx(float(sum(expected.values())), abs=1e-8)
    assert result["is_complete_bill"] and result["rate_evidence_status"] == "verified"
    assert result["total_usd"] == pytest.approx(sum(result["lines"].values()))
    assert not result["metrics"]["measured_demand_charge"]


@pytest.mark.parametrize("stamp,period", [
    ("2025-03-08 05:45", "off"), ("2025-03-08 06:00", "peak"),
    ("2025-03-08 07:45", "peak"), ("2025-03-08 08:00", "off"),
    ("2025-03-08 17:00", "peak"), ("2025-03-08 21:00", "off"),
    ("2025-03-09 06:00", "off"), ("2025-03-09 17:45", "off"),
    ("2025-03-09 18:00", "peak"), ("2025-03-09 21:45", "peak"),
    ("2025-03-09 22:00", "off"), ("2025-03-10 00:45", "off"),
    ("2025-03-10 01:00", "discount"), ("2025-03-10 04:45", "discount"),
    ("2025-03-10 05:00", "off"), ("2025-07-04 00:00", "off"),
    ("2025-07-04 02:00", "off"), ("2025-07-04 19:00", "off"),
    ("2026-07-03 19:00", "off"), ("2027-07-05 19:00", "off"),
    ("2021-12-31 19:00", "off"), ("2025-06-19 19:00", "peak"),
    ("2025-11-02 06:00", "peak"), ("2025-11-02 17:00", "peak"),
])
@pytest.mark.parametrize("plan", ["RS-TOU", "CS-TOU"])
def test_filed_clock_holidays_observed_days_and_boundaries(stamp, period, plan):
    idx = pd.DatetimeIndex([pd.Timestamp(stamp, tz=duke.TIMEZONE)])
    masks = duke.periods(idx, plan)
    assert [k for k, v in masks.items() if v[0]] == [period]


def test_dst_elapsed_hours_fold_and_unaffected_standard_plans():
    a, idx = fixture()
    assert len(idx) == 2972 and duke.cycle_review(a, idx)["elapsed_hours"] == 743.
    fold = pd.date_range("2025-11-02", "2025-11-03", freq="15min", tz=duke.TIMEZONE, inclusive="left")
    assert len(fold) == 100 and len(set(fold.asi8)) == 100
    mask = duke.periods(fold, "RS-TOU")
    assert sum(mask["discount"]) == 16  # A fixed-standard-time window remains four elapsed hours.
    for plan in ("RS", "CS"):
        p = duke.periods(idx, plan)
        assert p["off"].all() and not p["peak"].any() and not p["discount"].any()
        assert "energy" not in duke.interval_rates(idx, plan)


@pytest.mark.parametrize("day", ["2025-01-01", "2025-02-26", "2025-02-27", "2025-04-01", "2025-12-31", "2026-01-01", "2026-09-30"])
def test_no_rate_extrapolation(day):
    with pytest.raises(ValueError, match="coverage"):
        service_rates(day, "RS")


@pytest.mark.parametrize("day", ["20250301", "2025-3-01", "2025-03-01T00:00", None, 20250301])
def test_exact_iso_dates(day):
    with pytest.raises(ValueError, match="ISO"):
        service_rates(day, "RS")


def test_missing_data_wrong_clocks_partial_cycles_and_eligibility_reject():
    a, idx = fixture()
    for altered in (idx.delete(10), idx.insert(10, idx[10]), idx[4:], idx.tz_convert("America/Chicago"), idx.tz_localize(None)):
        with pytest.raises(ValueError):
            duke.validate_account(a, altered)
    for updates in (dict(eligibility_confirmed=False), dict(ordinary_service_confirmed=False), dict(local_charges_confirmed=False),
                    dict(voltage_v=208.), dict(phase="three", voltage_v=480.), dict(supply="competitive"), dict(export_mode="nem"),
                    dict(opening_credit_usd=10.), dict(tax_source=""), dict(cycle_kind="initial"), dict(bill_date="2025-04-01")):
        with pytest.raises(ValueError):
            duke.validate_account({**a, **updates}, idx)
    with pytest.raises(ValueError, match="TOU"):
        duke.validate_account({**duke.hypothetical_defaults("RS-TOU"), "tou_enrollment_confirmed": False}, idx)
    with pytest.raises(ValueError, match="ratchet"):
        duke.validate_state(a, idx, state={"demand_history": [1]})


@pytest.mark.parametrize("plan", ["RS", "CS"])
def test_confirmed_regular_meter_cycle_uses_full_blocks_and_connection(plan):
    full_account, full = fixture(plan)
    short = build_interval_index("2025-03-06", "2025-03-31", duke.TIMEZONE, 15).index
    assert (short[-1].date()-short[0].date()).days+1 == 26
    short_account = {**full_account, "cycle_source": "Explicit hypothetical complete26day regular meter cycle; not a partial statement"}
    result = []
    for index, account in ((full, full_account), (short, short_account)):
        load = np.full(len(index), 700./(len(index)/4))
        bill = calculate_cycle(duke.UTILITY, index, load, np.zeros(len(index)), account)
        result.append(bill)
        assert bill["metrics"]["monthly_charge_factor"] == 1.
        assert not bill["metrics"]["partial_period_proration_applied"]
    assert result[0]["unrounded_lines"] == pytest.approx(result[1]["unrounded_lines"], abs=1e-8)
    assert result[1]["metrics"]["cycle_days"] == 26


def test_cycle_lengths_billing_clock_and_reset_crossing_remain_explicit():
    a, _ = fixture()
    for start, end in (("2025-03-07", "2025-03-31"), ("2025-03-01", "2025-04-04")):
        idx = build_interval_index(start, end, duke.TIMEZONE, 15).index
        with pytest.raises(ValueError, match="26–34"):
            duke.cycle_review({**a, "bill_date": end}, idx)
    idx = build_interval_index("2025-02-01", "2025-02-28", duke.TIMEZONE, 15).index
    with pytest.raises(ValueError, match="reset"):
        duke.cycle_review({**a, "billing_month": "2025-02-01", "bill_date": "2025-02-28"}, idx)
    with pytest.raises(ValueError, match="billing designation"):
        service_rates("2025-03-15", "RS", billing_month="2025-04-01")
    for month in ("2025-03-15", "20250301", None, 3):
        if month is None:
            assert service_rates("2025-03-15", "RS")["designated_billing_month"] == "2025-03-01"
        else:
            with pytest.raises(ValueError, match="billing designation"):
                service_rates("2025-03-15", "RS", billing_month=month)


def test_non_export_approved_ordinary_service_and_capacity_bound():
    a, idx = fixture()
    equipment = dict(pv=True, battery=True, pv_dc_kw=5., pv_ac_kw=4., battery_kw=3.)
    duke.validate_account(a, idx, equipment)
    for updates, equip in ((dict(dg_enrollment_confirmed=False), equipment), (dict(dg_source=""), equipment),
                            ({}, {**equipment, "pv": False}), ({}, {**equipment, "pv_dc_kw": 40.})):
        with pytest.raises(ValueError):
            duke.validate_account({**a, **updates}, idx, equip)
    for imports, exports in ((np.full(len(idx), 75.001), np.zeros(len(idx))), (np.ones(len(idx)), np.full(len(idx), .1))):
        with pytest.raises(ValueError, match="zero export"):
            calculate_cycle(duke.UTILITY, idx, imports, exports, a)


@pytest.mark.parametrize("plan", duke.PLANS)
def test_fixed_schedule_symbolic_and_numeric_bill_agree(plan):
    a, idx = fixture(plan, 30)
    load = 4.+np.sin(np.arange(len(idx))*2*np.pi/48)
    imp, exp = cp.Variable(len(idx), nonneg=True), cp.Variable(len(idx), nonneg=True)
    math = BillingMath(idx, convex=True, power_bound=10.)
    math.register(imp, 0., 10.); math.register(exp, 0., 10.)
    symbolic = duke.charge_lines(idx, imp, exp, a, math=math)
    problem = cp.Problem(cp.Minimize(sum(symbolic["lines"].values())), math.constraints+[imp == load, exp == 0])
    problem.solve(solver="SCIPY", scipy_options={"time_limit": 20.})
    numeric = calculate_cycle(duke.UTILITY, idx, load, np.zeros(len(idx)), a)
    assert problem.status == "optimal"
    assert problem.value == pytest.approx(numeric["unrounded_total_usd"], abs=1e-6)


@pytest.mark.parametrize("plan", ["RS-TOU", "CS-TOU"])
def test_dispatch_bill_reconciliation(plan):
    a, idx = fixture(plan)
    hour = idx.hour.to_numpy()+idx.minute.to_numpy()/60
    pv = 3*np.maximum(0, np.sin((hour-6)*np.pi/12))
    inputs = pd.DataFrame(dict(timestamp=idx, native_load_kw=np.full(len(idx), 2.), pv_available_kw=pv))
    battery = dict(capacity_kWh=10., energy_kWh=5., SOC_min=.1, SOC_max=.9,
                   max_charge_kw=3., max_discharge_kw=3., charge_efficiency=.95, discharge_efficiency=.95)
    out = optimize_cycle(inputs, duke.UTILITY, a, battery=battery, terminal_energy=5., grid_charging=True, time_limit=30.)
    assert out["cost_optimum_proven"]
    assert abs(out["reconciliation_difference_usd"]) < .0001
    assert out["dispatch"].grid_export_kw.max() < 1e-5


def test_source_evidence_hashes_and_explicit_limited_coverage():
    manifest = json.loads(Path("docs/utility_sources/duke_in/manifest.json").read_text())
    assert manifest["supported_coverage"] == [{"start": "2025-03-01", "end": "2025-03-31"}]
    assert manifest["coverage_gaps"] and not manifest["full_year_2025_supported"]
    for source in manifest["sources"]:
        path = Path(source["extracted_text"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["extracted_text_sha256"]
    for source in manifest.get("support_images", []):
        assert hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest() == source["sha256"]
    plans = duke.catalog()
    assert {p["id"] for p in plans} == set(duke.PLANS)
    assert all(p["status"] == "supported" and p["solar_modes"] == ["non_export"] for p in plans)
    defaults = duke.defaults()
    assert not defaults["eligibility_confirmed"] and not defaults["dg_enrollment_confirmed"]


@pytest.mark.parametrize("plan", duke.PLANS)
def test_tou_interpretation_is_disclosed_without_affecting_standard_bills(plan):
    a, idx = fixture(plan)
    bill = calculate_cycle(duke.UTILITY, idx, np.ones(len(idx)), np.zeros(len(idx)), a)
    metrics = bill["metrics"]
    warnings = [w for w in bill["warnings"] if "calendar evidence discrepancy" in w]
    if plan.endswith("-TOU"):
        assert metrics["calendar_evidence_status"] == "filed_sheet_interpretation_utility_confirmation_required"
        assert metrics["calendar_confirmation_required"] and len(warnings) == 1
        assert "utility confirmation" in metrics["calendar_evidence_note"]
        assert len(metrics["calendar_source_references"]) == 4
    else:
        assert metrics["calendar_evidence_status"] == "not_time_of_use"
        assert metrics["calendar_evidence_note"] is None and not metrics["calendar_confirmation_required"]
        assert not metrics["calendar_source_references"] and not warnings
    # Source-discrepancy disclosure does not invent alternate numeric prices.
    assert bill["rate_evidence_status"] == "verified"


def provisional_fixture(plan="RS", start="2025-01-01", end="2025-01-31", step=15):
    account = {**duke.hypothetical_defaults(plan), "rate_evidence_mode": "provisional_2025",
               "provisional_assumptions_accepted": True, "bill_date": end,
               "billing_month": end[:7]+"-01", "cycle_source": "Explicit hypothetical regular meter cycle with accepted Duke2025 study assumptions"}
    return account, build_interval_index(start, end, duke.TIMEZONE, step).index


@pytest.mark.parametrize("changes", [
    dict(rate_evidence_mode="verified"), dict(rate_evidence_mode="provisional_2025", provisional_assumptions_accepted=False),
    dict(rate_evidence_mode="provisional_2025", provisional_assumptions_accepted="true"),
    dict(rate_evidence_mode="provisional_2025", provisional_assumptions_accepted=1), dict(rate_evidence_mode="unknown"),
])
def test_provisional_dates_need_explicit_mode_and_real_boolean_acceptance(changes):
    a, idx = provisional_fixture()
    with pytest.raises(ValueError):
        calculate_cycle(duke.UTILITY, idx, np.ones(len(idx)), np.zeros(len(idx)), {**a, **changes})


@pytest.mark.parametrize("plan,customer,energy,rider_total", [
    ("RS", "10.54", "120.4476", ".010508"),
    ("CS", "10.70", "133.4450", ".011369"),
])
def test_provisional_old_base_and_known_old_riders_independent_benchmark(plan, customer, energy, rider_total):
    a, idx = provisional_fixture(plan)
    volume = D(1000)
    expected_pre_tax = D(customer)+D(energy)+volume*D(rider_total)
    bill = calculate_cycle(duke.UTILITY, idx, np.full(len(idx), 1000/(len(idx)/4)), np.zeros(len(idx)), a)
    assert bill["unrounded_total_usd"] == pytest.approx(float(expected_pre_tax*D("1.07")), abs=1e-8)
    assert bill["unrounded_lines"]["fuel"] == pytest.approx(5.902)
    assert bill["unrounded_lines"]["energy_efficiency"] == pytest.approx(3.851 if plan == "RS" else 3.882)
    assert bill["unrounded_lines"]["load_control"] == pytest.approx(1.406 if plan == "RS" else 1.446)
    assert bill["rate_evidence_status"] == "provisional"
    assert bill["objective_scope"] == "provisional_modeled_bill"
    assert [v["id"] for v in bill["rate_assumptions"]] == ["DEI25-PRE-RESET-RIDERS"]
    assert "reallocated" in bill["rate_assumptions"][0]["explanation"]
    assert any("cannot validate" in w for w in bill["warnings"])


@pytest.mark.parametrize("month,fuel,credit", [
    ("2025-03", -.001521, -.014131), ("2025-04", -.004801, -.014131),
    ("2025-06", -.004801, -.014131), ("2025-07", .004042, -.014131),
    ("2025-09", .004042, -.013516), ("2025-10", .000372, -.013516),
    ("2025-12", .000372, -.013516),
])
def test_provisional_billing_month_fuel_and_credit_boundaries(month, fuel, credit):
    day = month+"-15"
    rates = service_rates(day, "RS", mode="provisional_2025")
    assert rates["fuel"] == fuel and rates["credits_adjustment"] == credit
    assert rates["energy"] == (.186556, .135777, .123051)


def test_provisional_july_does_not_force_agreement_with_official_rounded_snapshot():
    a, idx = provisional_fixture(start="2025-07-01", end="2025-07-31")
    bill = calculate_cycle(duke.UTILITY, idx, np.full(len(idx), 1000/(len(idx)/4)), np.zeros(len(idx)), a)
    modeled_pre_tax = bill["unrounded_total_usd"]/1.07
    # Independent IURC July1,2025 snapshot: 1000kWh157.98USD before tax.
    # Our explicitly held62/73 factors are NOT the actual July rates.
    assert modeled_pre_tax == pytest.approx(163.0677, abs=1e-8)
    assert modeled_pre_tax-157.98 == pytest.approx(5.0877, abs=1e-8)
    assert "DEI25-JULY-RIDER-CONTINUITY" in {v["id"] for v in bill["rate_assumptions"]}
    assert bill["rate_evidence_status"] == "provisional"


def test_calendar_crossing_uses_explicit_billing_month_without_blended_riders():
    a, idx = provisional_fixture(start="2025-03-16", end="2025-04-15")
    bill = calculate_cycle(duke.UTILITY, idx, np.ones(len(idx)), np.zeros(len(idx)), a)
    rates = duke.interval_rates(idx, "RS", billing_month="2025-04-01", mode="provisional_2025")
    assert np.all(rates["fuel"] == -.004801)
    assert bill["unrounded_lines"]["fuel"] == pytest.approx(-.004801*len(idx)/4)
    assert bill["unrounded_lines"]["customer"] == 13.70
    assert {v["id"] for v in bill["rate_assumptions"]} == {"DEI25-FAC143-SIGN", "DEI25-BILL-MONTH-ALLOCATION"}
    assert not bill["metrics"]["partial_period_proration_applied"]
    with pytest.raises(ValueError, match="billing month"):
        duke.validate_account({**a, "billing_month": "2025-03-01"}, idx)


def test_annual_twelve_cycle_scope_and_no_pre_inception_tou_or_2026_backcast():
    ends = [("2025-01-01", "2025-01-26"), ("2025-01-27", "2025-02-26"), ("2025-02-27", "2025-03-31")]
    ends += [(str(d.date()), str((d+pd.offsets.MonthEnd()).date())) for d in pd.date_range("2025-04-01", "2025-12-01", freq="MS")]
    for plan in ("RS", "CS"):
        intervals = []
        for start, end in ends:
            a, idx = provisional_fixture(plan, start, end)
            duke.validate_account(a, idx)
            intervals.extend(idx.asi8)
            assert 26 <= duke.cycle_review(a, idx)["cycle_days"] <= 34
        assert len(intervals) == len(set(intervals)) == 35040
    for plan in ("RS-TOU", "CS-TOU"):
        with pytest.raises(ValueError, match="pre-February27"):
            service_rates("2025-01-31", plan, mode="provisional_2025")
        a, idx = provisional_fixture(plan, "2025-02-27", "2025-03-31")
        duke.validate_account(a, idx)
    for day in ("2024-12-31", "2026-01-01"):
        with pytest.raises(ValueError, match="coverage"):
            service_rates(day, "RS", mode="provisional_2025")
    a, idx = provisional_fixture(start="2025-02-01", end="2025-02-28")
    with pytest.raises(ValueError, match="reset"):
        duke.validate_account(a, idx)


@pytest.mark.parametrize("plan,start,end", [("RS", "2025-01-01", "2025-01-31"), ("CS", "2025-07-01", "2025-07-31")])
def test_provisional_fixed_schedule_symbolic_numeric_parity(plan, start, end):
    a, idx = provisional_fixture(plan, start, end, step=30)
    load = 3.+np.sin(np.arange(len(idx))*2*np.pi/48)
    imp, exp = cp.Variable(len(idx), nonneg=True), cp.Variable(len(idx), nonneg=True)
    math = BillingMath(idx, convex=True, power_bound=10.)
    math.register(imp, 0., 10.); math.register(exp, 0., 10.)
    symbolic = duke.charge_lines(idx, imp, exp, a, math=math)
    problem = cp.Problem(cp.Minimize(sum(symbolic["lines"].values())), math.constraints+[imp == load, exp == 0])
    problem.solve(solver="SCIPY", scipy_options={"time_limit": 20.})
    numeric = calculate_cycle(duke.UTILITY, idx, load, np.zeros(len(idx)), a)
    assert problem.status == "optimal"
    assert problem.value == pytest.approx(numeric["unrounded_total_usd"], abs=1e-6)
    assert symbolic["rate_assumptions"] == numeric["rate_assumptions"]


@pytest.mark.parametrize("plan", duke.PLANS)
def test_march_verified_bill_unchanged_by_provisional_selection(plan):
    a, idx = fixture(plan)
    base = calculate_cycle(duke.UTILITY, idx, np.full(len(idx), 2.), np.zeros(len(idx)), a)
    opted = calculate_cycle(duke.UTILITY, idx, np.full(len(idx), 2.), np.zeros(len(idx)),
                            {**a, "rate_evidence_mode": "provisional_2025", "provisional_assumptions_accepted": True})
    assert base["unrounded_lines"] == opted["unrounded_lines"]
    assert opted["rate_evidence_status"] == "verified" and opted["rate_assumptions"] == []
    assert opted["assumption_model"] is None and opted["objective_scope"] == "complete_utility_bill"


def test_provisional_evidence_catalog_and_return_values_are_isolated():
    a, idx = provisional_fixture(start="2025-12-01", end="2025-12-31")
    proof = duke.evidence(idx, a)
    assert {v["id"] for v in proof["rate_assumptions"]} == {
        "DEI25-JULY-RIDER-CONTINUITY", "DEI25-DECEMBER-CREDIT67", "DEI25-ORDINARY-BASE-CONTINUITY"}
    assert all(v["sources"] and v["components"] and v["assumed_values"] for v in proof["rate_assumptions"])
    proof["rate_assumptions"][0]["assumed_values"]["environmental"]["RS"] = 100.
    assert duke.evidence(idx, a)["rate_assumptions"][0]["assumed_values"]["environmental"]["RS"] == .003339
    plans = duke.catalog()
    assert plans[0]["provisional_coverage"] == [dict(start="2025-01-01", end="2025-12-31")]
    assert plans[1]["provisional_coverage"] == [dict(start="2025-02-27", end="2025-12-31")]
    assert duke.defaults()["rate_evidence_mode"] == "verified"
    assert duke.defaults()["provisional_assumptions_accepted"] is False
