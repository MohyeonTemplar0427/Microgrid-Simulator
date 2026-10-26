"""Independent BGE published component/composite checks and bounded contracts."""
from decimal import Decimal, ROUND_HALF_UP

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import bge_md as bge
from src.billing.bge_md_rates import rates_on
from src.billing.regional_math import BillingMath
from src.timeseries import build_interval_index


def fixture(plan="R", month="2025-07", step=15):
    start = month + "-01"
    end = str((pd.Timestamp(start) + pd.offsets.MonthEnd()).date())
    account = bge.hypothetical_defaults(plan)
    account.update(billing_month=start, bill_date=end)
    return account, build_interval_index(start, end, bge.TIMEZONE, step).index


def bill(plan="R", month="2025-07", power=1.0):
    account, idx = fixture(plan, month)
    bge.validate_account(account, idx)
    imports = np.full(len(idx), power) if np.isscalar(power) else power
    return bge.charge_lines(idx, imports, np.zeros(len(idx)), account, math=BillingMath(idx))


# Utility-published CSEG composite rows, not sums copied from production tables.
# Original Rdr32_CS_Current_Rates_12.pdf, pages2/6/12/16 (one-based).
# These verify recurring variable charges, never authorize export settlement.
COMPOSITES = {
    (2025, "R"): [.18265, .18332, .17635, .18025, .18129, .18052,
                    .18668, .18465, .21448, .22966, .22016, .19441],
    (2025, "G"): [.19423, .19179, .18399, .18392, .18534, .18512,
                    .18969, .19115, .20949, .21860, .21046, .18944],
    (2026, "R"): [.19998, .19514, .22670, .22526, .23341, .20865,
                    .21044, .20829, .20682, .20191],
    (2026, "G"): [.20887, .21438, .24128, .23381, .23571, .21725,
                    .22118, .22499, .22422, .21754],
}


@pytest.mark.parametrize("plan,month,published", [
    (plan, f"{year}-{month:02}", value)
    for (year, plan), values in COMPOSITES.items()
    for month, value in enumerate(values, 1)
])
def test_independent_published_monthly_variable_composite(plan, month, published):
    got = bill(plan, month)
    _, idx = fixture(plan, month)
    energy = len(idx) / 4
    excluded = {"distribution_customer", "universal_service", "county_energy_tax", "sales_tax"}
    observed = sum(value for name, value in got["lines"].items() if name not in excluded)
    assert observed / energy == pytest.approx(published, abs=1e-12)
    assert got["rate_evidence_status"] == "verified"
    assert got["rate_assumptions"] == []
    assert got["is_complete_bill"] is (plan == "G")
    assert got["excluded_components"] == ([] if plan == "G" else ["account_specific_legislative_relief_refund"])


@pytest.mark.parametrize("plan,month,customer,delivery,generation,transmission,eca,r25,aca,myp,ee,dr,ptr,usc", [
    ("R", "2025-01", "9.65", ".04751", ".10405", ".01682", "-.00165", ".00330", "-.00097", ".00254", ".00764", ".00251", ".00013", ".32"),
    ("G", "2025-01", "15.10", ".04819", ".10027", ".01413", ".00422", ".00419", "-.00065", ".00241", ".02059", "0", ".00011", "1.85"),
    ("R", "2026-02", "10.00", ".04859", ".11115", ".02322", "-.00049", "-.00095", "-.00111", ".00086", ".01097", ".00198", ".00015", ".32"),
    ("G", "2026-02", "15.60", ".04965", ".10372", ".01986", ".00736", "-.00243", "-.00062", ".00041", ".03526", ".00027", ".00013", "1.85"),
])
def test_literal_component_bill_and_state_tax_base(plan, month, customer, delivery, generation,
        transmission, eca, r25, aca, myp, ee, dr, ptr, usc):
    got = bill(plan, month)
    _, idx = fixture(plan, month)
    energy = Decimal(len(idx)) / 4
    expected = dict(distribution_customer=Decimal(customer), universal_service=Decimal(usc))
    names = ["distribution_energy", "generation_supply", "transmission_service", "energy_cost_adjustment",
             "monthly_rate_adjustment", "administrative_cost_credit", "multi_year_plan_adjustment",
             "energy_efficiency", "demand_response", "peak_time_rebate", "franchise_tax"]
    for name, rate in zip(names, [delivery, generation, transmission, eca, r25, aca, myp, ee, dr, ptr, ".00062"]):
        expected[name] = energy * Decimal(rate)
    taxable = sum(expected.values())
    expected["environmental_surcharge"] = energy * Decimal(".000150")
    expected["county_energy_tax"] = energy * Decimal("0" if plan == "R" else ".0025")
    expected["sales_tax"] = taxable * Decimal("0" if plan == "R" else ".06")
    assert set(got["lines"]) == set(expected)
    for name, amount in expected.items():
        assert got["lines"][name] == pytest.approx(float(amount), abs=1e-9)
    assert got["metrics"]["sales_tax_base_usd"] == pytest.approx(float(taxable))
    assert not {"pjm_capacity", "pjm_transmission", "wholesale_energy", "psc_assessment"} & set(got["lines"])


def cents(value):
    return Decimal(str(value)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)


def test_actual_901_kwh_example_delivery_and_taxes_only():
    # Maryland legislative energy briefing Jan22,2026, presentationp10.
    # Supply uses the original customer's shifted cycle, not calendar September.
    account, idx = fixture(month="2025-09")
    got = bge.charge_lines(idx, np.full(len(idx), 901 / (len(idx) / 4)),
                           np.zeros(len(idx)), account, math=BillingMath(idx))
    lines = got["lines"]
    assert cents(lines["distribution_customer"]) == Decimal("9.65")
    assert cents(sum(lines[k] for k in ["distribution_energy", "monthly_rate_adjustment",
                    "multi_year_plan_adjustment", "administrative_cost_credit"])) == Decimal("40.61")
    assert cents(sum(lines[k] for k in ["energy_efficiency", "demand_response", "peak_time_rebate"])) == Decimal("9.26")
    assert cents(lines["universal_service"]) == Decimal(".32")
    assert cents(lines["environmental_surcharge"]) == Decimal(".14")
    assert cents(lines["franchise_tax"]) == Decimal(".56")


@pytest.mark.parametrize("plan", bge.PLANS)
@pytest.mark.parametrize("month", ["2025-03", "2025-11", "2026-02", "2026-10"])
def test_numeric_convex_itemized_parity(plan, month):
    account, idx = fixture(plan, month)
    imports = .4 + 2.2 * (np.arange(len(idx)) % 17) / 16
    raw = bge.charge_lines(idx, imports, np.zeros(len(idx)), account, math=BillingMath(idx))
    x, y = cp.Variable(len(idx)), cp.Variable(len(idx))
    math = BillingMath(idx, convex=True, power_bound=4.)
    math.register_power(x, np.zeros(len(idx)), np.full(len(idx), 4.))
    expression = bge.charge_lines(idx, x, y, account, math=math)
    problem = cp.Problem(cp.Minimize(sum(expression["lines"].values())), [x == imports, y == 0, *math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status == cp.OPTIMAL
    for name, value in expression["lines"].items():
        actual = value.value if hasattr(value, "value") else value
        assert float(actual) == pytest.approx(raw["lines"][name], abs=1e-8)


@pytest.mark.parametrize("month,transition,count,hours", [
    ("2025-03", "2025-03-09", 92, 743),
    ("2025-11", "2025-11-02", 100, 721),
])
def test_dst_uses_elapsed_intervals_not_days_times_96(month, transition, count, hours):
    account, idx = fixture(month=month)
    bge.validate_account(account, idx)
    assert sum(idx.date == pd.Timestamp(transition).date()) == count
    assert len(idx) == hours * 4
    assert bge.cycle_review(account, idx)["elapsed_hours"] == hours


@pytest.mark.parametrize("day", ["2024-12-31", "2026-11-01", "2027-01-01", "2025-6-1", None, 20250601])
def test_unverified_date_or_malformed_date_rejected(day):
    with pytest.raises(ValueError):
        rates_on(day)


@pytest.mark.parametrize("change", [
    dict(eligibility_confirmed=False), dict(ordinary_service_confirmed=False),
    dict(local_charges_confirmed=False), dict(full_monthly_charges_confirmed=False),
    dict(supply="retail_supplier"), dict(supply="pjm_lmp"), dict(export_mode="nem"),
    dict(phase="three"), dict(voltage="primary"), dict(voltage_v=208.), dict(tax_exempt=True),
    dict(tax_jurisdiction="annapolis"), dict(meter_count=2), dict(service_line_count=2),
    dict(opening_credit_usd=1.), dict(cycle_source=""), dict(tax_source=""),
    dict(rate_evidence_mode="provisional"), dict(provisional_assumptions_accepted=True),
    dict(demand_interval_minutes=15), dict(relief_policy="apply_estimated_80_dollars"),
    dict(billing_month="2025-08-01"), dict(bill_date="2025-08-01"),
])
def test_account_facts_must_be_explicit_and_supported(change):
    account, idx = fixture()
    with pytest.raises(ValueError):
        bge.validate_account({**account, **change}, idx)


@pytest.mark.parametrize("change", [dict(type_i_confirmed=False), dict(usc_band="1300_to_14999"), dict(usc_source="")])
def test_small_modeled_usage_never_proves_type_i_or_assigned_usc_band(change):
    account, idx = fixture("G")
    with pytest.raises(ValueError):
        bge.validate_account({**account, **change}, idx)


def test_partial_shifted_missing_duplicate_reordered_and_wrong_zone_reject():
    account, idx = fixture()
    invalid = [idx[1:], idx[:-1], idx.delete(30), idx.insert(30, idx[30]),
               idx[::-1], idx.tz_convert("America/Chicago"), idx + pd.Timedelta(days=1)]
    for candidate in invalid:
        with pytest.raises(ValueError):
            bge.validate_account(account, candidate)
    _, hourly = fixture(step=60)
    with pytest.raises(ValueError):
        bge.validate_account(account, hourly)


def test_g_eligibility_uses_half_hour_peak_instead_of_quarter_hour_peak():
    _, idx = fixture("G")
    power = np.zeros(len(idx))
    power[:2] = [49., 0.]
    got = bill("G", power=power)
    assert got["metrics"]["measured_demand_kw"] == 24.5
    power[:2] = [49., 1.]
    with pytest.raises(ValueError, match="below25kW"):
        bill("G", power=power)


@pytest.mark.parametrize("month,limit", [("2025-05", 6000.), ("2025-06", 7500.), ("2025-10", 6000.)])
def test_type_i_energy_domain_accepts_limit_and_rejects_above(month, limit):
    _, idx = fixture("G", month)
    hours = len(idx) / 4
    assert bill("G", month, power=limit / hours)["metrics"]["type_i_monthly_energy_limit_kwh"] == limit
    with pytest.raises(ValueError, match="6000/7500"):
        bill("G", month, power=(limit + .01) / hours)


def test_unsupported_der_export_and_opening_state_reject():
    account, idx = fixture()
    equipment = dict(pv=True, battery=True, pv_dc_kw=5., pv_ac_kw=4., battery_kw=3.)
    bge.validate_account(account, idx, equipment)
    for changed in [dict(der_ordinary_service_confirmed=False), dict(der_eligibility_source="")]:
        with pytest.raises(ValueError):
            bge.validate_account({**account, **changed}, idx, equipment)
    with pytest.raises(ValueError):
        bge.validate_account(account, idx, dict(pv=False, battery=True))
    with pytest.raises(ValueError):
        bge.validate_account(account, idx, {**equipment, "battery_kw":21.})
    with pytest.raises(ValueError):
        bge.validate_state(account, idx, state={"credit":1})
    with pytest.raises(ValueError, match="exports"):
        bge.charge_lines(idx, np.ones(len(idx)), np.ones(len(idx)), account, math=BillingMath(idx))


def test_residential_refunds_are_excluded_explicitly_and_defaults_are_unconfirmed():
    account, idx = fixture()
    assert bge.evidence(idx, account)["objective_scope"] == "verified_charges_subtotal"
    assert bge.evidence(idx, fixture("G")[0])["objective_scope"] == "complete_utility_bill"
    for plan in bge.PLANS:
        assert bge.defaults(plan)["eligibility_confirmed"] is False
        assert bge.defaults(plan)["local_charges_confirmed"] is False
    assert {p["id"] for p in bge.catalog()} == {"R", "G"}
    assert all(p["solar_modes"] == ["non_export"] for p in bge.catalog())


def test_environmental_surcharge_monthly_cap_is_applied_once():
    got = bill(power=10000.)
    assert got["lines"]["environmental_surcharge"] == 1000.
