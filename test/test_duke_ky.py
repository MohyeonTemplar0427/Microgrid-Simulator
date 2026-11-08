"""Independent Duke Kentucky literal billing, clocks and eligibility safeguards."""
from copy import deepcopy
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import duke_ky as duke
from src.billing import duke_ky_rates as rates
from src.billing.regional_math import BillingMath


# Separate literal source transcription. None of the benchmark functions read
# production rate tables, charge functions, or serialized expected totals.
FACTORS = {
    "2025-04-01": (".004559", ".0351", ".0548", ".001508"),
    "2025-05-01": ("-.006385", ".0149", ".0234", ".000806"),
    "2025-06-01": (".000627", ".0543", ".0855", ".000806"),
    "2026-04-01": (".006094", "-.0039", "-.0060", "-.005893"),
    "2026-05-01": ("-.009567", "-.0191", "-.0288", "-.003992"),
    "2026-06-01": ("-.001945", "-.0097", "-.0146", "-.003992"),
}


def cycle(month):
    start = pd.Timestamp(month, tz=duke.TIMEZONE)
    return pd.date_range(start, start+pd.offsets.MonthBegin(), freq="15min", inclusive="left")


def bill(plan, month, kwh, **changes):
    index = cycle(month)
    account = {**duke.hypothetical_defaults(plan, day=month), **changes}
    duke.validate_account(account, index)
    return duke.charge_lines(index, np.full(len(index), 4*kwh/len(index)), np.zeros(len(index)),
                             account, math=BillingMath(index))


def independent(plan, month, kwh):
    quantity = D(str(kwh))
    fac, rs_es, ds_es, psm = map(D, FACTORS[month])
    commercial, new = plan == "DS", month.startswith("2026")
    customer = D("15") if commercial else D("14.75" if new else "13")
    base = D(".126995" if new else ".114788") if commercial else D(".126104" if new else ".111639")
    dsm = D(".001154" if new else ".003409") if commercial else D(".005514" if new else ".002418")
    result = dict(bundled_customer=customer, bundled_energy=quantity*base,
                  bundled_demand=D(0), demand_side_management=quantity*dsm,
                  home_energy_assistance=D(0) if commercial else D(".30"),
                  fuel_adjustment=quantity*fac, profit_sharing=quantity*psm)
    if commercial:
        basis = customer+quantity*(base+dsm+psm-D(".033780"))
    else:
        basis = customer+D(".30")+quantity*(base+dsm+fac+psm)
    result["environmental"] = basis*(ds_es if commercial else rs_es)
    result["school_tax"] = sum(result.values())*D(".03")
    result["city_franchise"] = D(0)
    result["sales_tax"] = sum(result.values())*D(".06") if commercial else D(0)
    return result


@pytest.mark.parametrize("plan", ("RS", "DS"))
@pytest.mark.parametrize("month", FACTORS)
@pytest.mark.parametrize("kwh", (0, 0.001, 1000, 5999))
def test_independent_decimal_complete_components(plan, month, kwh):
    result = bill(plan, month, kwh)
    expected = independent(plan, month, kwh)
    assert result["lines"] == pytest.approx({k: float(v) for k, v in expected.items()}, abs=2e-9)
    assert result["next_state"] == {} and result["is_complete_bill"] is True
    assert result["excluded_components"] == [] and result["rate_evidence_status"] == "verified"
    assert result["rate_sources"] and not result["rate_assumptions"] and result["assumption_model"] is None


@pytest.mark.parametrize("plan", ("RS", "DS"))
@pytest.mark.parametrize("month", FACTORS)
@pytest.mark.parametrize("kwh", (0, 5999))
def test_numeric_symbolic_parity_with_negative_riders_and_zero_import(plan, month, kwh):
    index, account = cycle(month), duke.hypothetical_defaults(plan, day=month)
    power = cp.Variable(nonneg=True)
    imports = cp.multiply(np.ones(len(index)), power)
    math = BillingMath(index, convex=True, power_bound=25.)
    math.register_power(imports, np.zeros(len(index)), np.full(len(index), duke.MAX_KW[plan]),
                        energy_upper=duke.MAX_KWH[plan])
    math.constraints.append(power == 4*kwh/len(index))
    result = duke.charge_lines(index, imports, cp.Constant(np.zeros(len(index))), account, math=math)
    problem = cp.Problem(cp.Minimize(sum(result["lines"].values())), math.constraints)
    problem.solve(solver="SCIPY")
    assert problem.status == cp.OPTIMAL
    for name, expected in independent(plan, month, kwh).items():
        actual = result["lines"][name]
        assert float(actual.value if hasattr(actual, "value") else actual) == pytest.approx(float(expected), abs=2e-7)


def test_revenue_bases_and_printed_psm_sign_convention():
    rs = bill("RS", "2025-04-01", 1000)["lines"]
    ordinary = sum(v for k, v in rs.items() if k not in ("environmental", "school_tax", "city_franchise", "sales_tax"))
    assert rs["environmental"] == pytest.approx(ordinary*.0351)
    assert rs["profit_sharing"] == pytest.approx(1.508)  # Printed (0.001508) is a charge.
    ds = bill("DS", "2026-04-01", 1000)["lines"]
    nonfuel = 15.+126.995+1.154-5.893-33.780
    assert ds["environmental"] == pytest.approx(nonfuel*-.006)
    assert ds["profit_sharing"] == pytest.approx(-5.893)  # Printed 0.005893 is a credit.
    assert ds["school_tax"] == pytest.approx((sum(ds.values())-ds["school_tax"]-ds["sales_tax"])*.03)
    assert ds["sales_tax"] == pytest.approx((sum(ds.values())-ds["sales_tax"])*.06)
    assert ds["bundled_demand"] == 0.


@pytest.mark.parametrize("month,expected_bill", [
    ("2025-04-01", "2025-05-01"), ("2025-05-01", "2025-06-02"),
    ("2025-06-01", "2025-07-01"), ("2026-04-01", "2026-05-01"),
    ("2026-05-01", "2026-06-01"), ("2026-06-01", "2026-07-01"),
])
def test_service_billing_and_factor_clocks(month, expected_bill):
    index = cycle(month)
    account = duke.hypothetical_defaults("DS", day=month)
    review, data = duke.cycle_review(account, index)
    assert review["service_start"] == month and review["bill_date"] == expected_bill
    assert review["billing_month"] == expected_bill[:7]+"-01"
    assert account["ds_history_through_month"] == month
    assert data["base_effective_start"] == ("2026-01-02" if month.startswith("2026") else "2024-10-01")
    assert data["dsm_effective_start"] == ("2026-04-01" if month.startswith("2026") else "2025-03-03")
    assert review["elapsed_hours"] == len(index)*.25


@pytest.mark.parametrize("month", [f"{y}-{m:02}-01" for y in (2025, 2026) for m in range(1, 13)
                                    if f"{y}-{m:02}-01" not in FACTORS]+["2024-06-01", "2027-06-01"])
def test_reject_missing_rate_stacks_and_transitions(month):
    with pytest.raises(ValueError, match="unverified"):
        bill("RS", month, 1000)


@pytest.mark.parametrize("month", ("2026", "2026-4", "2026-00", "2026-13", "2026-04-01", "x", None))
def test_rate_lookup_rejects_noncanonical_months(month):
    with pytest.raises(ValueError):
        rates.rates_for_cycle(month)


@pytest.mark.parametrize("changes", [
    {"billing_month": "2026-04-01"}, {"billing_month": "2026-06-01", "bill_date": "2026-06-01"},
    {"bill_date": "2026-05-02"}, {"bill_date": "2026-05-01T00:00"},
    {"billing_month": None}, {"bill_date": None}, {"cycle_kind": "initial"},
    {"billing_assignment_confirmed": False}, {"billing_assignment_source": " "},
])
def test_no_inferred_or_misaligned_utility_billing_month(changes):
    with pytest.raises(ValueError):
        bill("RS", "2026-04-01", 1000, **changes)


@pytest.mark.parametrize("plan", ("RS", "DS"))
def test_defaults_are_unconfirmed_and_inputs_remain_unchanged(plan):
    index, account = cycle("2026-04-01"), duke.defaults(plan)
    with pytest.raises(ValueError):
        duke.validate_account(account, index)
    account = duke.hypothetical_defaults(plan)
    before = deepcopy(account)
    duke.validate_account(account, index)
    duke.charge_lines(index, np.ones(len(index)), np.zeros(len(index)), account, math=BillingMath(index))
    assert account == before
    assert {f["name"] for f in duke.account_fields(plan)} >= set(duke.CONFIRMATIONS)


@pytest.mark.parametrize("key,value", [
    ("tariff", "DT"), ("supply", "third_party"), ("export_mode", "net_billing"),
    ("voltage", "primary"), ("phase", "three"), ("voltage_v", 120.), ("voltage_v", True),
    ("meter_count", 2), ("meter_count", True), ("opening_credit_usd", 1.), ("opening_credit_kwh", 1.),
    ("tax_jurisdiction", "ky_boone_city"), ("rate_evidence_mode", "provisional"),
    ("provisional_assumptions_accepted", True), ("domicile_exemption_confirmed", False),
    ("eligibility_confirmed", False), ("boone_tax_scope_confirmed", False), ("ordinary_service_confirmed", 1),
    ("account_source", ""), ("tax_source", ""), ("cycle_source", ""),
])
def test_fail_closed_account_scope(key, value):
    with pytest.raises(ValueError):
        bill("RS", "2026-04-01", 1000, **{key: value})


@pytest.mark.parametrize("key,value", [
    ("ds_retained_assignment_confirmed", False), ("ds_billing_demand_ceiling_kw", 15.01),
    ("ds_billing_demand_ceiling_kw", 0), ("ds_billing_demand_ceiling_kw", True),
    ("ds_billing_demand_ceiling_kw", float("nan")), ("ds_monthly_demands_kw", [8.]*11),
    ("ds_monthly_demands_kw", [8.]*11+[15.01]), ("ds_monthly_demands_kw", [8.]*11+[float("nan")]),
    ("ds_monthly_demands_kw", [8.]*11+[True]), ("ds_monthly_demands_kw", [8.]*11+[-1]),
    ("ds_monthly_demands_kw", [8.]*11+[float("inf")]), ("ds_history_through_month", "2026-03-01"),
    ("ds_review_source", ""),
])
def test_independent_ds_history_and_ratchet_scope(key, value):
    with pytest.raises(ValueError):
        bill("DS", "2026-04-01", 1000, **{key: value})


def test_multi_cycle_hypothetical_history_cutoff_is_explicit_and_refreshes():
    account = duke.hypothetical_defaults("DS", day="2026-04-01")
    before = deepcopy(account)
    fields = duke.hypothetical_cycle_fields("2026-05-01")
    updated = {**account, **fields["account_overrides"], "billing_month": fields["billing_month"],
               "bill_date": fields["bill_date"], "cycle_kind": fields["kind"], "cycle_source": fields["source"]}
    duke.validate_account(updated, cycle("2026-05-01"))
    assert updated["ds_history_through_month"] == "2026-05-01" and account == before


@pytest.mark.parametrize("mutate", [
    lambda i: i.delete(100), lambda i: i.insert(100, i[100]), lambda i: i[:-1],
    lambda i: i[1:], lambda i: i[::-1], lambda i: i.tz_convert("UTC"),
    lambda i: i.tz_localize(None), lambda i: i+pd.Timedelta(minutes=15),
    lambda i: i[::2],
])
def test_missing_duplicate_naive_wrong_zone_or_partial_cycle_rejects(mutate):
    with pytest.raises(ValueError):
        duke.cycle_review(duke.hypothetical_defaults(), mutate(cycle("2026-04-01")))


@pytest.mark.parametrize("month,hours", [("2025-03-01", 743), ("2025-11-01", 721)])
def test_dst_full_grid_reaches_source_gate_without_fabricated_coverage(month, hours):
    index, account = cycle(month), duke.hypothetical_defaults(day=month)
    assert len(index)*.25 == hours
    with pytest.raises(ValueError, match="unverified"):
        duke.cycle_review(account, index)
    with pytest.raises(ValueError, match="15-minute"):
        duke.cycle_review(account, index.delete(len(index)//2))


@pytest.mark.parametrize("equipment", [
    {"pv": True}, {"pv": True, "battery": True, "renewable_only_charging": True, "no_battery_export": True},
])
def test_explicit_approved_nonexport_equipment(equipment):
    account = duke.hypothetical_defaults("DS")
    duke.validate_account(account, cycle("2026-04-01"), equipment=equipment)


@pytest.mark.parametrize("equipment,changes", [
    ({"battery": True}, {}), ({"pv": True}, {"der_ordinary_service_confirmed": False}),
    ({"pv": True}, {"der_eligibility_source": ""}), ({"pv": True}, {"der_activation_date": "2026-04-02"}),
    ({"pv": True}, {"der_activation_date": "2026-04-01T00:00"}),
    ({"pv": True, "battery": True}, {}),
    ({"pv": True, "battery": True, "no_battery_export": True}, {}),
    ({"pv": True, "battery": True, "renewable_only_charging": True}, {}),
])
def test_der_approval_does_not_infer_ordinary_rates_or_storage_permission(equipment, changes):
    account = {**duke.hypothetical_defaults(), **changes}
    with pytest.raises(ValueError):
        duke.validate_account(account, cycle("2026-04-01"), equipment=equipment)


def test_meter_and_native_limits_cannot_be_satisfied_by_solar_reduced_imports():
    index, account = cycle("2026-04-01"), duke.hypothetical_defaults("DS")
    zeros = np.zeros(len(index))
    for imported, exported in [(np.full(len(index), 15.), zeros), (zeros, np.ones(len(index))),
                               (np.full(len(index), np.nan), zeros), (-np.ones(len(index)), zeros),
                               (np.ones(len(index)-1), zeros), (zeros, -np.ones(len(index)))]:
        with pytest.raises(ValueError):
            duke.charge_lines(index, imported, exported, account, math=BillingMath(index))
    with pytest.raises(ValueError):
        bill("DS", "2026-04-01", 6000)
    with pytest.raises(ValueError):
        duke.validate_native_load(account, np.full(len(index), 15.))
    with pytest.raises(ValueError):
        duke.validate_native_load(account, np.full(len(index), 6000/(len(index)*.25)))
    duke.validate_native_load(account, np.full(len(index), 5999/(len(index)*.25)))
    with pytest.raises(ValueError, match="credit bank"):
        duke.validate_state(account, index, {"opening_credit_usd": 1})


def test_symbolic_export_energy_and_power_caps_are_constraints():
    index, account = cycle("2026-04-01"), duke.hypothetical_defaults("DS")
    for power, exported in [(15., 0.), (6000/(len(index)*.25), 0.), (1., .1), (-1., 0.)]:
        math = BillingMath(index, convex=True, power_bound=25.)
        result = duke.charge_lines(index, cp.Constant(np.full(len(index), power)),
                                   cp.Constant(np.full(len(index), exported)), account, math=math)
        problem = cp.Problem(cp.Minimize(sum(result["lines"].values())), math.constraints)
        problem.solve(solver="SCIPY")
        assert problem.status == cp.INFEASIBLE


def test_reviewed_current_demand_ceiling_also_bounds_native_and_import_power():
    index, account = cycle("2026-04-01"), duke.hypothetical_defaults("DS")
    account["ds_billing_demand_ceiling_kw"] = 5.
    duke.validate_account(account, index)
    duke.validate_native_load(account, np.full(len(index), 5.))
    with pytest.raises(ValueError):
        duke.validate_native_load(account, np.full(len(index), 5.01))
    with pytest.raises(ValueError):
        duke.charge_lines(index, np.full(len(index), 5.01), np.zeros(len(index)), account,
                          math=BillingMath(index))


def test_source_receipts_and_portable_transcriptions():
    directory = Path(__file__).resolve().parents[1]/"docs/utility_sources/duke_ky"
    ledger = json.loads((directory/"sources.json").read_text())
    assert ledger["utility"] == duke.UTILITY
    assert ledger["coverage"] == [dict(start=a, end=b) for a, b in duke.COVERAGE]
    assert len(ledger["monthly_components"]) == 6
    for source in ledger["sources"]:
        assert source["url"].startswith("https://")
        if source.get("sha256"):
            assert len(source["sha256"]) == 64 and source["bytes"] > 0
    for excerpt in ledger["excerpts"]:
        content = (directory/excerpt["path"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == excerpt["sha256"]
    for month, factors in FACTORS.items():
        row = next(v for v in ledger["monthly_components"] if v["service_month"] == month)
        assert tuple(map(D, row["independent_factor_literals"])) == tuple(map(D, factors))
        assert row["fac_source_page"] > 0 and row["esm_cells"] == ["FORM 1.00!E19", "FORM 1.00!E28"]
    workbooks = json.loads((directory/"monthly_workbook_evidence.json").read_text())
    for year, district_cell, rate_cell in [(2025, "A19", "P19"), (2026, "A19", "P19"), (2027, "A8", "P8")]:
        record = next(row for row in workbooks if row["filename"] == f"school_tax_{year}.xlsx")
        assert record["cells"][district_cell] == "035 Boone County"
        assert record["cells"][rate_cell] == 3
