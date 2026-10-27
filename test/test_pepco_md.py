"""Independent Pepco Maryland filed components, published composites and scope."""
from decimal import Decimal as D, ROUND_HALF_UP

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import pepco_md as pepco
from src.billing.pepco_md_rates import distribution_versions, rates_on
from src.billing.regional_math import BillingMath
from src.timeseries import build_interval_index


def fixture(plan="R", month="2026-07", step=15):
    start = month + "-01"
    end = str((pd.Timestamp(start) + pd.offsets.MonthEnd()).date())
    account = pepco.hypothetical_defaults(plan)
    account.update(billing_month=start, bill_date=end)
    return account, build_interval_index(start, end, pepco.TIMEZONE, step).index


def bill(plan="R", month="2026-07", power=1.):
    account, idx = fixture(plan, month)
    pepco.validate_account(account, idx)
    imports = np.full(len(idx), power) if np.isscalar(power) else power
    return pepco.charge_lines(idx, imports, np.zeros(len(idx)), account, math=BillingMath(idx))


# Literal utility-published variable composites before county tax and GRT.
# Feb2025 CSEG physical R1/GS5; Oct2026 CSEG physical R1/GS4.
# Signs are retail charge signs, opposite the published community-solar credits.
COMPOSITES = [
    ("2025-01", ".18550650", ".15972880"),
    ("2025-02", ".18145860", ".16105280"),
    ("2026-07", ".24586150", ".21260160"),
    ("2026-08", ".24991550", ".21142420"),
    ("2026-09", ".23922230", ".21104700"),
    ("2026-10", ".26611460", ".22374430"),
]


@pytest.mark.parametrize("plan", ["R", "GS"])
@pytest.mark.parametrize("month,residential,commercial", COMPOSITES)
def test_independent_published_variable_composite(plan, month, residential, commercial):
    got = bill(plan, month)
    _, idx = fixture(plan, month)
    excluded = {"distribution_customer_net_rdm", "universal_service",
                "montgomery_county_surcharge", "distribution_gross_receipts_tax",
                "transmission_gross_receipts_tax"}
    variable = sum(value for key, value in got["lines"].items() if key not in excluded)
    assert variable / (len(idx) / 4) == pytest.approx(float(residential if plan == "R" else commercial), abs=1e-12)
    assert got["is_complete_bill"] is False
    assert got["rate_evidence_status"] == "verified" and got["rate_assumptions"] == []
    expected_exclusions = (["account_specific_legislative_relief_refund", "residential_rggi_rate_credit"]
                           if plan == "R" else ["maryland_state_sales_tax"])
    assert got["excluded_components"] == expected_exclusions
    assert "sales_tax" not in got["lines"]  # Excluded GS tax is unknown, not zero/exempt.


@pytest.mark.parametrize("plan,month,customer,delivery,generation,admin,pca,transmission,bsa,credit,empower,myp,mcs,usc", [
    ("R", "2025-01", "8.49", ".04566", ".10115", ".00391", "-.0017815", ".01951", ".003928", "-.001630", ".013790", ".00020", ".0113205", ".32"),
    ("GS", "2025-02", "12.69", ".04385", ".10050", ".00530", "-.0162402", ".01302", ".005659", "0", ".008044", ".00015", ".0202459", "1.85"),
    ("R", "2026-10", "8.44", ".08760", ".12266", ".00415", ".0054696", ".02007", ".004347", "-.001250", ".020618", ".00168", ".0113242", ".32"),
    ("GS", "2026-08", "12.66", ".08130", ".10675", ".00362", "-.0176268", ".01423", ".009855", "-.000690", ".011986", ".00123", ".0202525", "1.85"),
])
def test_independent_literal_itemization_and_grt_bases(plan, month, customer, delivery,
        generation, admin, pca, transmission, bsa, credit, empower, myp, mcs, usc):
    got = bill(plan, month)
    _, idx = fixture(plan, month)
    energy = D(len(idx)) / 4
    expected = dict(distribution_customer_net_rdm=D(customer), universal_service=D(usc))
    names = ["distribution_energy_net_rdm", "generation_energy", "supply_administration",
             "procurement_cost_adjustment", "transmission_service", "bill_stabilization_adjustment",
             "administrative_delivery_credit", "empower_maryland", "multi_year_plan_adjustment",
             "montgomery_county_surcharge", "delivery_tax", "environmental_surcharge"]
    for key, value in zip(names, [delivery, generation, admin, pca, transmission, bsa,
                                  credit, empower, myp, mcs, ".000620", ".000150"]):
        expected[key] = energy * D(value)
    # Original CSEG footnote(1): AC is unmarked, despite being a delivery credit.
    grt_base = D(customer) + D(usc) + energy * sum(D(v) for v in [delivery, bsa, empower, myp, ".000620", ".000150"])
    expected["distribution_gross_receipts_tax"] = grt_base * D(".020408")
    expected["transmission_gross_receipts_tax"] = energy * D(transmission) * D(".020408")
    assert set(got["lines"]) == set(expected)
    for key, amount in expected.items():
        assert got["lines"][key] == pytest.approx(float(amount), abs=1e-9)
    assert got["metrics"]["grt_delivery_base_usd"] == pytest.approx(float(grt_base))
    assert "administrative_delivery_credit" not in got["metrics"]["grt_delivery_components"]
    assert not {"pjm_capacity", "pjm_transmission", "wholesale_energy", "psc_assessment"} & set(got["lines"])


@pytest.mark.parametrize("plan,ordinary,temporary,offset", [
    ("R", ["8.44", ".08760", ".04328"], ["8.67", ".09713", ".05469"], ["-.23", "-.00953", "-.01141"]),
    ("GS", ["12.66", ".08130", ".04272"], ["13.02", ".09220", ".05447"], ["-.36", "-.01090", "-.01175"]),
])
def test_august_filed_same_clock_cancellation_preserves_raw_versions(plan, ordinary, temporary, offset):
    raw = distribution_versions(plan)
    assert (raw["temporary_start"], raw["temporary_end"], raw["restored_start"], raw["verified_end"]) == (
        "2026-08-11", "2026-08-27", "2026-08-28", "2026-10-31")
    assert raw["clock"] == "Identical usage-date applicability for base and RDM"
    for key, old, increased, credit in zip(["customer", "summer", "winter"], ordinary, temporary, offset):
        assert raw["ordinary"][key] == float(old)
        assert raw["temporary"][key] == float(increased)
        assert raw["temporary_rdm"][key] == float(credit)
        assert D(increased) + D(credit) == D(old)
        # Cancellation holds under any shared linear allocation; no chosen17/30.
        for weight in [D("0"), D(".3"), D(".7"), D("1")]:
            assert (1 - weight) * D(old) + weight * (D(increased) + D(credit)) == D(old)
    got = bill(plan, "2026-08")
    assert got["metrics"]["distribution_netting"]["separate_base_rdm_invoice_rounding_verified"] is False
    assert got["metrics"]["partial_period_proration_applied"] is False
    assert "net" in got["metrics"]["distribution_netting"]["basis"].lower() or "cancel" in got["metrics"]["distribution_netting"]["basis"].lower()


@pytest.mark.parametrize("plan", ["R", "GS"])
@pytest.mark.parametrize("month", ["2025-01", "2025-02", "2026-07", "2026-08", "2026-09", "2026-10"])
def test_numeric_convex_itemized_parity(plan, month):
    account, idx = fixture(plan, month)
    imports = .4 + 2.2 * (np.arange(len(idx)) % 17) / 16
    raw = pepco.charge_lines(idx, imports, np.zeros(len(idx)), account, math=BillingMath(idx))
    x, y = cp.Variable(len(idx)), cp.Variable(len(idx))
    math = BillingMath(idx, convex=True, power_bound=4.)
    math.register_power(x, np.zeros(len(idx)), np.full(len(idx), 4.))
    expression = pepco.charge_lines(idx, x, y, account, math=math)
    problem = cp.Problem(cp.Minimize(sum(expression["lines"].values())), [x == imports, y == 0, *math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status == cp.OPTIMAL
    for key, value in expression["lines"].items():
        actual = value.value if hasattr(value, "value") else value
        assert float(actual) == pytest.approx(raw["lines"][key], abs=1e-8)


def cents(value):
    return D(str(value)).quantize(D(".01"), rounding=ROUND_HALF_UP)


def test_official_2025_bill_transmission_example_only():
    # Pepco bill_education_2025.pdf physical3:987kWh, Jan29–Feb25 shifted bill.
    # Transmission price unchanged across that actual cycle; no whole-bill claim.
    account, idx = fixture(month="2025-02")
    got = pepco.charge_lines(idx, np.full(len(idx), 987 / (len(idx) / 4)),
                             np.zeros(len(idx)), account, math=BillingMath(idx))
    assert cents(got["lines"]["transmission_service"]) == D("19.26")
    assert cents(got["lines"]["transmission_gross_receipts_tax"]) == D(".39")
    assert got["is_complete_bill"] is False


@pytest.mark.parametrize("day", ["2024-12-31", "2025-03-01", "2025-06-01", "2025-12-31",
    "2026-01-01", "2026-04-01", "2026-05-01", "2026-06-01", "2026-11-01", "2027-01-01",
    "2025-1-1", None, 20250101])
def test_unverified_component_intersections_and_malformed_dates_reject(day):
    with pytest.raises(ValueError):
        rates_on(day)


@pytest.mark.parametrize("day,plan", [("2025-02-28", "R"), ("2026-07-01", "GS"), ("2026-10-31", "R")])
def test_supported_coverage_edges_are_closed(day, plan):
    assert rates_on(day, plan)["component_month"] == day[:7]


@pytest.mark.parametrize("month,day,count,hours", [("2025-03", "2025-03-09", 92, 743), ("2025-11", "2025-11-02", 100, 721)])
def test_dst_grid_retains_elapsed_intervals_but_unverified_billing_rejects(month, day, count, hours):
    account, idx = fixture(month=month)
    assert sum(idx.date == pd.Timestamp(day).date()) == count
    assert len(idx) == hours * 4
    with pytest.raises(ValueError, match="intersections"):
        pepco.validate_account(account, idx)


@pytest.mark.parametrize("change", [
    dict(eligibility_confirmed=False), dict(ordinary_service_confirmed=False),
    dict(local_charges_confirmed=False), dict(full_monthly_charges_confirmed=False),
    dict(subtotal_scope_confirmed=False), dict(supply="retail_supplier"), dict(supply="pjm_lmp"),
    dict(export_mode="nem"), dict(phase="three"), dict(voltage="primary"), dict(voltage_v=208.),
    dict(tax_exempt=True), dict(tax_jurisdiction="district_of_columbia"), dict(meter_count=2),
    dict(service_line_count=2), dict(opening_credit_usd=1.), dict(cycle_source=""), dict(tax_source=""),
    dict(rate_evidence_mode="provisional"), dict(provisional_assumptions_accepted=True),
    dict(demand_interval_minutes=15), dict(relief_policy="estimated_80_dollars"),
    dict(billing_month="2026-08-01"), dict(bill_date="2026-08-01"),
])
def test_independent_account_confirmations_and_supported_scope(change):
    account, idx = fixture()
    with pytest.raises(ValueError):
        pepco.validate_account({**account, **change}, idx)


@pytest.mark.parametrize("month,year", [("2025-01", 2025), ("2026-07", 2026)])
def test_usc_assignment_requires_applicable_year_source(month, year):
    account, idx = fixture("GS", month)
    for change in [dict(type_i_confirmed=False), dict(usc_band="1300_to_2599"),
                   {f"usc_assignment_{year}_source":""}]:
        with pytest.raises(ValueError):
            pepco.validate_account({**account, **change}, idx)
    # The other year's source cannot substitute for this year's classification.
    other = 2026 if year == 2025 else 2025
    pepco.validate_account({**account, f"usc_assignment_{other}_source":""}, idx)


def test_missing_duplicate_shifted_wrong_zone_and_hourly_intervals_reject():
    account, idx = fixture()
    invalid = [idx[1:], idx[:-1], idx.delete(30), idx.insert(30, idx[30]),
               idx[::-1], idx.tz_convert("America/Chicago"), idx + pd.Timedelta(days=1)]
    for candidate in invalid:
        with pytest.raises(ValueError):
            pepco.validate_account(account, candidate)
    _, hourly = fixture(step=60)
    with pytest.raises(ValueError):
        pepco.validate_account(account, hourly)


def test_gs_demand_uses_half_hour_average_and_excludes_25_kw():
    _, idx = fixture("GS")
    power = np.zeros(len(idx))
    power[:2] = [49., 0.]
    assert bill("GS", power=power)["metrics"]["measured_demand_kw"] == 24.5
    power[:2] = [49., 1.]
    with pytest.raises(ValueError, match="below25kW"):
        bill("GS", power=power)


@pytest.mark.parametrize("month,limit", [("2025-01", 6000.), ("2026-07", 7500.), ("2026-10", 7500.)])
def test_gs_energy_domain_uses_november_to_may_winter_and_june_to_october_summer(month, limit):
    _, idx = fixture("GS", month)
    hours = len(idx) / 4
    assert bill("GS", month, power=limit / hours)["metrics"]["type_i_monthly_energy_limit_kwh"] == limit
    with pytest.raises(ValueError, match="6000/7500"):
        bill("GS", month, power=(limit + .01) / hours)


def test_residential_import_study_cap_does_not_become_tariff_eligibility():
    _, idx = fixture()
    hours = len(idx) / 4
    assert bill(power=7500 / hours)["lines"]["environmental_surcharge"] == pytest.approx(1.125)
    with pytest.raises(ValueError, match="study domain"):
        bill(power=7500.01 / hours)
    assert any("not a residential tariff eligibility" in item for item in pepco.catalog()[0]["limitations"])


def test_der_ordinary_service_export_and_opening_state_boundaries():
    account, idx = fixture()
    equipment = dict(pv=True, battery=True, pv_dc_kw=5., pv_ac_kw=4., battery_kw=3.)
    pepco.validate_account(account, idx, equipment)
    for changed in [dict(der_ordinary_service_confirmed=False), dict(der_eligibility_source="")]:
        with pytest.raises(ValueError):
            pepco.validate_account({**account, **changed}, idx, equipment)
    with pytest.raises(ValueError):
        pepco.validate_account(account, idx, dict(pv=False, battery=True))
    with pytest.raises(ValueError):
        pepco.validate_account(account, idx, {**equipment, "battery_kw":21.})
    with pytest.raises(ValueError):
        pepco.validate_state(account, idx, state={"credit":1})
    with pytest.raises(ValueError, match="exports"):
        pepco.charge_lines(idx, np.ones(len(idx)), np.ones(len(idx)), account, math=BillingMath(idx))


def test_catalog_defaults_and_objective_scope_preserve_both_subtotals():
    for plan in pepco.PLANS:
        account, idx = fixture(plan)
        assert pepco.evidence(idx, account)["objective_scope"] == "verified_charges_subtotal"
        assert pepco.defaults(plan)["eligibility_confirmed"] is False
        assert pepco.defaults(plan)["subtotal_scope_confirmed"] is False
    for record in pepco.catalog():
        assert record["solar_modes"] == ["non_export"]
        assert record["interval_minutes"] == [15]
        assert [(r["start"], r["end"]) for r in record["coverage"]] == [
            ("2025-01-01", "2025-02-28"), ("2026-07-01", "2026-10-31")]
        assert all(row["is_complete_bill"] is False for row in record["coverage"])
