"""Duquesne account/history boundaries and numeric/symbolic contract checks.

Independent literal source-price benchmarks live in a separate module. These
tests bound the supported account domain and prove that fixed meter flows use
the same charge expressions without manufacturing minimum-bill purchases.
"""
from copy import deepcopy

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import duquesne_pa as dl
from src.billing.duquesne_pa_rates import COVERAGE, rates_on
from src.billing.regional_math import BillingMath
from src.timeseries import build_interval_index


def covered(day):
    end = str((pd.Timestamp(day) + pd.offsets.MonthEnd()).date())
    return any(start <= day and end <= stop for start, stop in COVERAGE)


MONTHS = [f"{year}-{month:02d}-01" for year in (2025, 2026)
          for month in range(1, 13) if covered(f"{year}-{month:02d}-01")]


def fixture(plan="RS", day="2026-06-01"):
    account = dl.hypothetical_defaults(plan, day=day)
    grid = build_interval_index(account["billing_month"], account["bill_date"], dl.TIMEZONE, 15)
    return account, grid.index


def power(index, energy=600., peak=None):
    values = np.full(len(index), energy * 4 / len(index))
    if peak is not None:
        values[0] = peak
        values[1:] = (energy * 4 - peak) / (len(index) - 1)
    return values


def bill(plan="RS", day="2026-06-01", energy=600., peak=None, state=None, account=None):
    a, index = fixture(plan, day)
    if account is not None:
        a = account
    dl.validate_account(a, index)
    dl.validate_state(a, index, state=state)
    return dl.charge_lines(index, power(index, energy, peak), np.zeros(len(index)), a,
                           math=BillingMath(index), state=state)


@pytest.mark.parametrize("plan", ["RS", "GS"])
@pytest.mark.parametrize("day", MONTHS)
def test_supported_full_months_preserve_charge_bases_and_units(plan, day):
    result = bill(plan, day)
    lines, metrics = result["lines"], result["metrics"]
    # Customer levels and GS non-demand structure are separately published facts.
    assert lines["distribution_customer"] == (13. if plan == "RS" else 18.)
    if plan == "GS":
        assert lines["distribution_energy"] == pytest.approx(600 * .084601)
    before_dsic = sum(lines[k] for k in ("distribution_customer", "distribution_energy",
        "retail_market_enhancement", "universal_service", "energy_efficiency", "smart_meter"))
    assert metrics["dsic_basis_usd"] == pytest.approx(before_dsic)
    assert metrics["stas_distribution_basis_usd"] == pytest.approx(before_dsic + lines["distribution_dsic"])
    assert metrics["stas_all_basis_usd"] == pytest.approx(before_dsic + lines["distribution_dsic"]
        + lines["distribution_state_tax_adjustment"] + lines["default_service_supply"])
    assert lines["sales_tax"] == pytest.approx(0. if plan == "RS" else
        .06 * sum(v for key, v in lines.items() if key != "sales_tax"))
    assert metrics["raw_import_kwh"] == pytest.approx(600.)
    assert metrics["monthly_charge_factor"] == 1.
    assert metrics["partial_period_proration_applied"] is False
    assert metrics["additional_grt_percentage_applied"] is False
    assert metrics["rounded_cash_optimum_claimed"] is False
    assert metrics["tax_jurisdiction"] == "pa_state_only"
    assert result["is_complete_bill"] is True and result["rate_evidence_status"] == "verified"
    assert not {"gross_receipts_tax", "pjm_lmp", "pjm_capacity", "distribution_demand",
                "minimum_top_up", "export_credit"} & set(lines)


@pytest.mark.parametrize("plan", ["RS", "GS"])
@pytest.mark.parametrize("day", [day for day in ("2025-01-01", "2025-06-01", "2026-06-01") if covered(day)])
def test_fixed_flows_have_numeric_symbolic_itemized_parity(plan, day):
    account, index = fixture(plan, day)
    p = power(index)
    numeric = bill(plan, day)
    imports, exports = cp.Variable(len(index)), cp.Variable(len(index))
    math = BillingMath(index, convex=True, power_bound=5.)
    math.register_power(imports, np.zeros(len(index)), np.full(len(index), 5.))
    symbolic = dl.charge_lines(index, imports, exports, account, math=math)
    problem = cp.Problem(cp.Minimize(sum(symbolic["lines"].values())),
                         [imports == p, exports == 0, *math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status == cp.OPTIMAL
    for key, value in symbolic["lines"].items():
        actual = float(value.value if hasattr(value, "value") else value)
        assert actual == pytest.approx(numeric["lines"][key], abs=1e-8)


@pytest.mark.parametrize("field,value", [
    ("eligibility_confirmed", False), ("ordinary_service_confirmed", False),
    ("full_monthly_charges_confirmed", False), ("fixed_default_supply_confirmed", False),
    ("local_charges_confirmed", False), ("eligibility_confirmed", 1),
    ("supply", "shopping"), ("export_mode", "net_metering"),
    ("tax_jurisdiction", "allegheny"), ("tax_exempt", True),
    ("voltage", "primary"), ("phase", "three"), ("voltage_v", 208.),
    ("power_factor", .95), ("meter_count", 2), ("meter_count", True),
    ("service_line_count", 2), ("opening_credit_usd", 1.),
    ("demand_interval_minutes", 30), ("supply_source", ""),
    ("tax_source", " "), ("cycle_source", None),
    ("bill_date", "2026-07-01"), ("billing_month", "2026-05-01"),
    ("cycle_kind", "initial"), ("rate_evidence_mode", "provisional"),
    ("provisional_assumptions_accepted", True),
])
def test_unverified_account_supplier_tax_service_and_cycle_facts_reject(field, value):
    account, index = fixture()
    account[field] = value
    with pytest.raises((ValueError, TypeError)):
        dl.validate_account(account, index)


@pytest.mark.parametrize("field,value", [
    ("solely_residential_use_confirmed", False), ("gs_small_confirmed", True),
    ("gs_no_demand_minimum_confirmed", True), ("gs_qualification_upper_bound_kwh", 1000.),
    ("gs_prior_peak_upper_bound_kw", 5.), ("gs_history_through_month", "2026-05-01"),
    ("gs_qualification_source", "Commercial facts do not belong to RS"),
])
def test_rs_does_not_infer_whole_meter_tax_exemption_for_mixed_use(field, value):
    account, index = fixture()
    account[field] = value
    with pytest.raises(ValueError):
        dl.validate_account(account, index)


@pytest.mark.parametrize("field,value", [
    ("gs_small_confirmed", False), ("gs_no_demand_minimum_confirmed", False),
    ("gs_qualification_source", ""), ("gs_qualification_upper_bound_kwh", 1000.01),
    ("gs_qualification_upper_bound_kwh", True), ("gs_qualification_upper_bound_kwh", float("nan")),
    ("gs_prior_peak_upper_bound_kw", 5.01), ("gs_prior_peak_upper_bound_kw", -1.),
    ("solely_residential_use_confirmed", True),
])
def test_gs_company_assignment_and_prior_qualification_are_independent_facts(field, value):
    account, index = fixture("GS")
    account[field] = value
    with pytest.raises(ValueError):
        dl.validate_account(account, index)


def test_gs_history_carries_adjacent_months_without_mutating_input():
    june = bill("GS")
    state = deepcopy(june["next_state"])
    july = bill("GS", "2026-07-01", state=state)
    assert state == june["next_state"]
    assert july["next_state"]["through_month"] == "2026-07-01"
    assert july["next_state"]["gs_qualification_upper_bound_kwh"] >= state["gs_qualification_upper_bound_kwh"]
    assert july["next_state"]["gs_peak_upper_bound_kw"] >= state["gs_peak_upper_bound_kw"]
    account, index = fixture("GS", "2026-08-01")
    with pytest.raises(ValueError, match="adjacent|history"):
        dl.validate_state(account, index, state=state)
    account, index = fixture("GS")
    account["gs_history_through_month"] = "2026-04-01"
    with pytest.raises(ValueError, match="history"):
        dl.validate_state(account, index)


@pytest.mark.parametrize("bad", [
    {"through_month": "2026-05-01", "gs_qualification_upper_bound_kwh": 1001., "gs_peak_upper_bound_kw": 5.},
    {"through_month": "2026-05-01", "gs_qualification_upper_bound_kwh": 1000., "gs_peak_upper_bound_kw": 5.01},
    {"through_month": "2026-05-01", "gs_qualification_upper_bound_kwh": 1000., "gs_peak_upper_bound_kw": 5., "credit": 1.},
])
def test_gs_does_not_reset_or_accept_unsupported_carried_history(bad):
    account, index = fixture("GS")
    with pytest.raises(ValueError):
        dl.validate_state(account, index, state=bad)


@pytest.mark.parametrize("day,hours", [("2025-03-01", 743), ("2025-11-01", 721), ("2026-03-01", 743)])
def test_calendar_dst_hours_come_from_actual_index(day, hours):
    if not covered(day):
        with pytest.raises(ValueError):
            bill("RS", day)
        return
    account, index = fixture("RS", day)
    result = dl.cycle_review(account, index)
    assert len(index) == hours * 4 and result["elapsed_hours"] == hours
    assert bill("RS", day, energy=600.)["metrics"]["raw_import_kwh"] == pytest.approx(600.)


@pytest.mark.parametrize("bad", ["missing", "duplicate", "reverse", "naive", "wrong_clock", "hourly", "partial"])
def test_missing_duplicate_nonlocal_or_incomplete_cycles_reject(bad):
    account, index = fixture()
    if bad == "missing": index = index.delete(100)
    elif bad == "duplicate": index = index.insert(100, index[99])
    elif bad == "reverse": index = index[::-1]
    elif bad == "naive": index = index.tz_localize(None)
    elif bad == "wrong_clock": index = index.tz_convert("America/Chicago")
    elif bad == "hourly": index = index[::4]
    else: index = index[:-1]
    with pytest.raises(ValueError):
        dl.cycle_review(account, index)


@pytest.mark.parametrize("energy,peak", [(1000.01, None), (600., 5.01)])
def test_gs_current_import_reclassification_domain_rejects(energy, peak):
    with pytest.raises(ValueError, match="reclassification"):
        bill("GS", energy=energy, peak=peak)


@pytest.mark.parametrize("energy", [0., 100., 200.])
def test_gs_low_import_minimum_is_rejected_without_inventing_a_bill(energy):
    with pytest.raises(ValueError, match="minimum-charge"):
        bill("GS", energy=energy)


def test_positive_dsic_cannot_mask_a_negative_eec_minimum_domain_failure():
    # January2026's positive DSIC can lift a low-import total above the
    # conservative guard even when delivery excluding DSIC is below it.
    # DSIC is explicitly outside the tariff minimum and cannot cure that gap.
    with pytest.raises(ValueError, match="minimum-charge"):
        bill("GS", day="2026-01-01", energy=18./.084601)


def test_symbolic_model_does_not_force_purchases_to_satisfy_unknown_gs_minimum():
    account, index = fixture("GS")
    imports, exports = cp.Variable(len(index)), cp.Variable(len(index))
    math = BillingMath(index, convex=True, power_bound=5.)
    math.register_power(imports, np.zeros(len(index)), np.full(len(index), 5.))
    symbolic = dl.charge_lines(index, imports, exports, account, math=math)
    problem = cp.Problem(cp.Minimize(sum(symbolic["lines"].values())),
                         [imports == 0, exports == 0, *math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status == cp.OPTIMAL
    assert np.max(abs(imports.value)) < 1e-8
    with pytest.raises(ValueError, match="minimum-charge"):
        bill("GS", energy=0.)


@pytest.mark.parametrize("plan", ["RS", "GS"])
def test_unsupported_export_and_state_do_not_become_credits(plan):
    account, index = fixture(plan)
    with pytest.raises(ValueError, match="export"):
        dl.charge_lines(index, power(index), np.ones(len(index)), account, math=BillingMath(index))
    if plan == "RS":
        with pytest.raises(ValueError, match="state"):
            dl.validate_state(account, index, state={"credit": 1.})


@pytest.mark.parametrize("kind", ["no_approval", "future_activation", "standalone", "grid_charge", "battery_export", "oversize"])
def test_der_requires_active_ordinary_renewable_approval_and_bounded_operation(kind):
    account, index = fixture()
    equipment = {"pv": True, "battery": True, "pv_dc_kw": 5., "pv_ac_kw": 4., "battery_kw": 3.,
                 "renewable_only_charging": True, "no_battery_export": True}
    if kind == "no_approval": account["der_ordinary_service_confirmed"] = False
    elif kind == "future_activation": account["der_activation_date"] = "2026-06-02"
    elif kind == "standalone": equipment["pv"] = False
    elif kind == "grid_charge": equipment["renewable_only_charging"] = False
    elif kind == "battery_export": equipment["no_battery_export"] = False
    else: equipment["pv_dc_kw"] = 26.
    with pytest.raises(ValueError):
        dl.validate_account(account, index, equipment=equipment)


def test_declared_coverage_does_not_extend_to_unverified_years_or_plans():
    for day in ("2024-12-01", "2027-01-01"):
        with pytest.raises(ValueError): rates_on(day, "RS", bill_date=day)
    with pytest.raises(ValueError): dl.defaults("GM")
    assert {entry["id"] for entry in dl.catalog()} == {"RS", "GS"}
    assert all(entry["interval_minutes"] == [15] and entry["solar_modes"] == ["non_export"] for entry in dl.catalog())
