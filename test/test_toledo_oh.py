"""Toledo account/date restrictions and source-specific billing invariants.

Independent literal price-vector benchmarks live separately. These tests focus
on consequential scope, units and input boundaries, especially Toledo's
15-minute demand measurement rather than CEI's 30-minute measurement.
"""
import numpy as np
import pandas as pd
import pytest

from src.billing import toledo_oh as te
from src.billing.toledo_oh_rates import rates_on
from src.billing.regional_math import BillingMath
from src.timeseries import build_interval_index


MONTHS = ("2025-01-01", "2025-06-01", "2025-09-01", "2025-10-01",
          "2025-11-01", "2026-10-01")


def fixture(plan="RS", day="2026-10-01"):
    account = te.hypothetical_defaults(plan, day=day)
    index = build_interval_index(day, account["bill_date"], te.TIMEZONE, 15).index
    return account, index


def load(index, energy=600., peak=None):
    p = np.full(len(index), energy * 4 / len(index))
    if peak is not None:
        p[0] = peak
        p[1:] = (energy * 4 - peak) / (len(index) - 1)
    return p


def bill(plan="RS", day="2026-10-01", energy=600., peak=None, account=None):
    a, index = fixture(plan, day)
    if account is not None:
        a = account
    te.validate_account(a, index)
    return te.charge_lines(index, load(index, energy, peak), np.zeros(len(index)), a,
                           math=BillingMath(index))


@pytest.mark.parametrize("day", MONTHS)
@pytest.mark.parametrize("plan", ("RS", "GS"))
def test_complete_verified_months_preserve_source_scope_and_whole_charges(day, plan):
    b = bill(plan, day)
    assert b["is_complete_bill"] is True and b["excluded_components"] == []
    assert b["rate_evidence_status"] == "verified" and b["rate_assumptions"] == []
    assert b["assumption_model"] is None and b["next_state"] == {}
    m = b["metrics"]
    assert m["monthly_charge_factor"] == 1.
    assert m["partial_period_proration_applied"] is False
    assert m["rounded_cash_optimum_claimed"] is False
    assert m["demand_history_ratchet_applied"] is False
    assert m["additional_tax_percentage_applied"] is False
    assert m["contract_demand_kw"] == (0. if plan == "RS" else 12.)
    assert b["lines"]["distribution_customer"] == ((6.5 if plan == "RS" else 10.)
        if day.startswith("2026") else (4. if plan == "RS" else 7.))
    assert b["lines"]["sales_tax"] == 0.
    assert not {"pjm_lmp", "pjm_capacity", "nspl_demand", "gross_receipts_tax",
                "export_credit", "minimum_top_up"} & b["lines"].keys()


@pytest.mark.parametrize("day", ("2024-12-31", "2025-02-01", "2025-05-31",
    "2025-07-01", "2025-08-31", "2025-12-01", "2025-12-31", "2026-01-01",
    "2026-03-01", "2026-05-01", "2026-09-30", "2026-11-01", "2027-01-01"))
def test_missing_component_intersections_never_use_current_or_adjacent_rates(day):
    with pytest.raises(ValueError, match="complete verified"):
        rates_on(day)


@pytest.mark.parametrize("field,value", [
    ("eligibility_confirmed", False), ("eligibility_confirmed", 1),
    ("ordinary_service_confirmed", False), ("sso_enrollment_confirmed", False),
    ("no_local_tax_confirmed", False), ("full_monthly_charges_confirmed", False),
    ("supply", "shopping"), ("supply", "hourly"), ("export_mode", "net_metering"),
    ("tax_jurisdiction", "municipal"), ("self_assessor", True),
    ("self_assessor", 0), ("voltage", "primary"), ("phase", "three"),
    ("voltage_v", 208.), ("power_factor", .95), ("meter_count", 2),
    ("meter_count", True), ("opening_credit_usd", 1.),
    ("demand_interval_minutes", 30), ("supply_source", ""),
    ("tax_source", " "), ("cycle_source", None),
    ("bill_date", "2026-11-01"), ("billing_month", "2026-09-01"),
    ("cycle_kind", "initial"), ("rate_evidence_mode", "provisional"),
    ("provisional_assumptions_accepted", True),
])
def test_unverified_service_supplier_tax_equipment_and_cycle_facts_reject(field, value):
    a, index = fixture()
    a[field] = value
    with pytest.raises(ValueError):
        te.validate_account(a, index)


@pytest.mark.parametrize("field,value", [
    ("measured_demand_confirmed", False), ("measured_demand_confirmed", 1),
    ("contract_demand_confirmed", False), ("contract_source", ""),
    ("contract_demand_kw", -1.), ("contract_demand_kw", 101.),
    ("contract_demand_kw", True), ("contract_demand_kw", np.nan),
    ("contract_demand_kw", np.inf),
])
def test_gs_contract_and_actual_meter_method_must_be_independent_account_facts(field, value):
    a, index = fixture("GS")
    a[field] = value
    with pytest.raises(ValueError):
        te.validate_account(a, index)


@pytest.mark.parametrize("field,value", [
    ("measured_demand_confirmed", True), ("contract_demand_confirmed", True),
    ("contract_demand_kw", 5.), ("contract_source", "A commercial contract"),
])
def test_rs_does_not_silently_inherit_commercial_account_facts(field, value):
    a, index = fixture()
    a[field] = value
    with pytest.raises(ValueError):
        te.validate_account(a, index)


@pytest.mark.parametrize("contract,peak,expected", [(0., 0., 5.), (0., 4., 5.),
    (0., 9., 9.), (12., 3., 12.), (7., 15., 15.)])
def test_gs_first_five_is_flat_and_billing_peak_retains_contract_floor(contract, peak, expected):
    a, index = fixture("GS")
    a["contract_demand_kw"] = contract
    te.validate_account(a, index)
    p = np.full(len(index), peak)
    b = te.charge_lines(index, p, np.zeros(len(index)), a, math=BillingMath(index))
    assert b["metrics"]["billing_demand_kw"] == expected
    assert b["lines"]["distribution_customer"] == 10.
    assert b["lines"]["distribution_demand"] == pytest.approx(17.5166 + (expected - 5.) * 8.2769)
    assert b["lines"]["non_market_transmission"] == pytest.approx(expected * 4.8415)


def test_single_fifteen_minute_spike_is_not_averaged_over_thirty_minutes():
    a, index = fixture("GS")
    a["contract_demand_kw"] = 0.
    p = np.zeros(len(index)); p[0] = 20.
    b = te.charge_lines(index, p, np.zeros(len(index)), a, math=BillingMath(index))
    assert p[:2].mean() == 10.
    assert b["metrics"]["actual_15_minute_peak_kw"] == 20.
    assert b["metrics"]["billing_demand_kw"] == 20.
    assert b["lines"]["distribution_demand"] == pytest.approx(17.5166 + 15 * 8.2769)


@pytest.mark.parametrize("state", [{"billing_demand_kw": 100.},
    {"history_billing_kw": [100.] * 11}, {"credit_kwh": 0.}, {"opening_credit_usd": 1.}])
@pytest.mark.parametrize("plan", ("RS", "GS"))
def test_no_invented_trailing_demand_ratchet_or_credit_bank(state, plan):
    a, index = fixture(plan)
    with pytest.raises(ValueError):
        te.validate_state(a, index, state=state)


@pytest.mark.parametrize("plan", ("RS", "GS"))
def test_january_dcr_uses_only_base_distribution_and_correct_vmc(plan):
    b = bill(plan, "2025-01-01", peak=18.)
    lines = b["lines"]
    base = sum(lines[k] for k in ("distribution_customer", "distribution_energy", "distribution_demand"))
    rate = .199630 if plan == "RS" else .171107
    assert lines["delivery_capital"] == pytest.approx(base * rate)
    quantity = b["metrics"]["raw_import_kwh"] if plan == "RS" else b["metrics"]["billing_demand_kw"]
    assert lines["vegetation_management"] == pytest.approx(quantity * (.001331 if plan == "RS" else .2806))
    assert lines["phase_in_recovery"] == pytest.approx(b["metrics"]["raw_import_kwh"] * .000318)
    assert lines["consumer_rate_credit"] == pytest.approx(-.51 if plan == "RS" else -.000298 * b["metrics"]["raw_import_kwh"])
    assert lines["tax_savings"] < 0.
    assert lines["residential_heating_recovery"] == pytest.approx(.001393 * b["metrics"]["raw_import_kwh"] if plan == "RS" else 0.)


@pytest.mark.parametrize("plan", ("RS", "GS"))
def test_october_2026_signed_riders_and_ccr_do_not_double_charge_old_rer(plan):
    b = bill(plan)
    e = b["metrics"]["raw_import_kwh"]
    assert b["lines"]["distribution_uncollectible"] == pytest.approx(-.000107 * e)
    assert b["lines"]["pipp_uncollectible"] == pytest.approx(-.000060 * e)
    assert b["lines"]["customer_credit_recovery"] == pytest.approx(e * (.002838 if plan == "RS" else .000201))
    assert b["lines"]["residential_heating_recovery"] == 0.
    assert b["lines"]["consumer_rate_credit"] == 0.


@pytest.mark.parametrize("day,days,hours,first,second", [
    ("2025-06-01", 30, 720, 2000., 15000.),
    ("2025-11-01", 30, 721, 2000., 15000.),
    ("2026-10-01", 31, 744, 2077., 15500.),
])
def test_tax_measurement_days_are_local_days_not_elapsed_twenty_four_hour_blocks(day, days, hours, first, second):
    a, index = fixture("GS", day)
    c = te.cycle_review(a, index)
    assert len(index) == hours * 4
    assert c["cycle_days"] == days and c["elapsed_hours"] == hours
    assert c["state_tax_thresholds_kwh"] == [first, second]
    b = bill("GS", day, energy=3000.)
    assert b["lines"]["state_kwh_tax"] == pytest.approx((first * .00465 + (3000 - first) * .00419) / .9974)


@pytest.mark.parametrize("day", ("2025-03-01", "2026-03-01"))
def test_spring_dst_grid_is_correct_but_unverified_tariff_month_still_rejects(day):
    a, index = fixture("GS", day)
    assert len(index) == 743 * 4
    with pytest.raises(ValueError, match="complete verified"):
        te.validate_account(a, index)


@pytest.mark.parametrize("kind", ("missing", "duplicate", "hourly", "utc", "naive", "partial", "reverse", "shifted"))
def test_incomplete_or_wrong_clock_cycles_are_not_billable(kind):
    a, index = fixture()
    if kind == "missing": index = index.delete(10)
    elif kind == "duplicate": index = index.insert(11, index[10])
    elif kind == "hourly": index = index[::4]
    elif kind == "utc": index = index.tz_convert("UTC")
    elif kind == "naive": index = index.tz_localize(None)
    elif kind == "partial": index = index[:-1]
    elif kind == "reverse": index = index[::-1]
    else: index = build_interval_index("2026-10-02", "2026-11-01", te.TIMEZONE, 15).index
    with pytest.raises(ValueError):
        te.validate_account(a, index)


@pytest.mark.parametrize("plan,bound", [("RS", 25.), ("GS", 100.)])
def test_zero_export_and_declared_peak_envelope_are_hard_bounds(plan, bound):
    a, index = fixture(plan)
    p = np.zeros(len(index)); exports = np.zeros(len(index)); exports[0] = .01
    with pytest.raises(ValueError):
        te.charge_lines(index, p, exports, a, math=BillingMath(index))
    p[0] = bound + .01
    with pytest.raises(ValueError):
        te.charge_lines(index, p, np.zeros(len(index)), a, math=BillingMath(index))


@pytest.mark.parametrize("mutation", ("unapproved", "late", "missing_date", "bad_date", "missing_evidence",
    "standalone", "grid_charging", "battery_export", "oversized"))
def test_der_requires_existing_ordinary_approval_for_exact_paired_configuration(mutation):
    a, index = fixture("GS")
    eq = dict(pv=True, battery=True, pv_dc_kw=5., pv_ac_kw=4., battery_kw=3.,
              renewable_only_charging=True, no_battery_export=True)
    if mutation == "unapproved": a["der_ordinary_service_confirmed"] = False
    elif mutation == "late": a["der_activation_date"] = "2026-11-01"
    elif mutation == "missing_date": a["der_activation_date"] = ""
    elif mutation == "bad_date": a["der_activation_date"] = "not-a-date"
    elif mutation == "missing_evidence": a["der_eligibility_source"] = ""
    elif mutation == "standalone": eq["pv"] = False
    elif mutation == "grid_charging": eq["renewable_only_charging"] = False
    elif mutation == "battery_export": eq["no_battery_export"] = False
    else: eq["pv_dc_kw"] = 26.
    with pytest.raises(ValueError):
        te.validate_account(a, index, equipment=eq)


def test_grid_only_does_not_require_a_pretend_renewable_approval():
    a, index = fixture("GS")
    a.update(der_ordinary_service_confirmed=False, der_activation_date="", der_eligibility_source="")
    te.validate_account(a, index, equipment={"pv": False, "battery": False})
    te.validate_state(a, index, state={})
    assert a["contract_demand_kw"] == 12.
