"""Independent official Delmarva monthly composites and bounded E3 demand scope."""
from decimal import Decimal as D

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import delmarva_md as dpl
from src.billing.delmarva_md_rates import rates_on
from src.billing.regional_math import BillingMath
from src.timeseries import build_interval_index


def fixture(plan="R", month="2026-09", step=15):
    start = month + "-01"
    end = str((pd.Timestamp(start) + pd.offsets.MonthEnd()).date())
    account = dpl.hypothetical_defaults(plan)
    account.update(billing_month=start, bill_date=end)
    return account, build_interval_index(start, end, dpl.TIMEZONE, step).index


def bill(plan="R", month="2026-09", power=1.):
    account, idx = fixture(plan, month)
    dpl.validate_account(account, idx)
    imports = np.full(len(idx), power) if np.isscalar(power) else power
    return dpl.charge_lines(idx, imports, np.zeros(len(idx)), account, math=BillingMath(idx))


# Official CSEG originals: May2025 and Sep2025 Rphysical1/SGS2;
# Oct2026 Rphysical1/SGS4. Retail signs reverse published credit signs.
# Composites omit fixed customer/USC, demand, RRC/refunds and state sales tax.
COMPOSITES = [
    ("2025-01", "0.21340320", "0.17833940"),
    ("2025-02", "0.20700160", "0.17093330"),
    ("2025-03", "0.20131260", "0.17264300"),
    ("2025-04", "0.19738450", "0.16687750"),
    ("2025-05", "0.20405540", "0.17404620"),
    ("2025-06", "0.21260700", "0.16759550"),
    ("2025-09", "0.20373650", "0.16727660"),
    ("2026-05", "0.20930940", "0.16963030"),
    ("2026-06", "0.21960090", "0.17925560"),
    ("2026-07", "0.22438190", "0.18331610"),
    ("2026-08", "0.22598030", "0.18157170"),
    ("2026-09", "0.22253980", "0.18053180"),
    ("2026-10", "0.24130430", "0.18806470"),
]


@pytest.mark.parametrize("plan", ["R", "SGS-S"])
@pytest.mark.parametrize("month,residential,commercial", COMPOSITES)
def test_independent_published_variable_composites(plan, month, residential, commercial):
    got = bill(plan, month)
    _, idx = fixture(plan, month)
    omitted = {"distribution_customer", "universal_service", "distribution_estimated_demand", "transmission_demand"}
    variable = sum(v for k, v in got["lines"].items() if k not in omitted)
    assert variable / (len(idx) / 4) == pytest.approx(float(residential if plan == "R" else commercial), abs=1e-12)
    assert got["is_complete_bill"] is False
    assert got["rate_evidence_status"] == "verified" and got["rate_assumptions"] == []
    assert got["excluded_components"] == (["account_specific_legislative_relief_refund", "residential_rggi_rate_credit"]
                                         if plan == "R" else ["maryland_state_sales_tax"])
    assert not {"distribution_gross_receipts_tax", "transmission_gross_receipts_tax", "psc_assessment",
                "pjm_capacity", "wholesale_energy", "sales_tax"} & set(got["lines"])


@pytest.mark.parametrize("plan,month,customer,energy,bsa,credit,empower,myp,pca,trans,usc", [
    ("R", "2025-01", "9.43", ".071482", ".007840", "-.001201", ".012649", "-.002647", ".0054462", ".019456", ".32"),
    ("SGS-S", "2025-02", "26", ".041549", "-.001825", "-.000461", ".011191", "-.001756", ".0006043", ".019838", "1.85"),
    ("R", "2026-10", "9.43", ".071482", ".008578", "-.001420", ".020055", "-.000256", ".0101653", ".021361", ".32"),
    ("SGS-S", "2026-07", "26", ".041549", ".003230", "-.000843", ".014937", "-.000171", ".0028041", ".018466", "1.85"),
])
def test_independent_component_literals_and_embedded_grt(plan, month, customer, energy, bsa,
        credit, empower, myp, pca, trans, usc):
    got = bill(plan, month)
    _, idx = fixture(plan, month)
    kwh = D(len(idx)) / 4
    assert got["lines"]["distribution_customer"] == float(customer)
    assert got["lines"]["universal_service"] == float(usc)
    for key, rate in [("distribution_energy", energy), ("bill_stabilization_adjustment", bsa),
            ("administrative_delivery_credit", credit), ("empower_maryland", empower),
            ("multi_year_plan_adjustment", myp), ("procurement_cost_adjustment", pca),
            ("transmission_energy", trans), ("franchise_tax", ".000620")]:
        assert got["lines"][key] == pytest.approx(float(kwh * D(rate)), abs=1e-10)
    assert got["metrics"]["additional_gross_receipts_tax_applied"] is False


def test_independent_1750kwh_utility_estimated_demand_fixture():
    account, idx = fixture("SGS-S", "2025-01")
    power = 1750 / (len(idx) / 4)
    got = bill("SGS-S", "2025-01", power)
    assert got["metrics"]["estimated_billing_demand_kw"] == pytest.approx(10.)
    assert got["lines"]["distribution_estimated_demand"] == pytest.approx(43.03679, abs=1e-10)
    assert got["lines"]["distribution_energy"] == pytest.approx(72.71075, abs=1e-10)
    assert got["lines"]["distribution_customer"] == 26.
    assert sum(got["lines"][k] for k in ["distribution_estimated_demand", "distribution_energy", "distribution_customer"]) == pytest.approx(141.74754)
    assert got["lines"]["transmission_demand"] == 0.
    assert got["lines"]["transmission_energy"] == pytest.approx(34.7165)
    assert got["lines"]["universal_service"] == 1.85
    assert got["metrics"]["metered_demand_rounding_applied"] is False
    assert got["metrics"]["demand_method"] == "utility_estimate"


@pytest.mark.parametrize("plan", ["R", "SGS-S"])
@pytest.mark.parametrize("month", ["2025-03", "2025-06", "2026-09", "2026-10"])
def test_numeric_convex_itemized_parity(plan, month):
    account, idx = fixture(plan, month)
    imports = .4 + 2.2 * (np.arange(len(idx)) % 17) / 16
    raw = dpl.charge_lines(idx, imports, np.zeros(len(idx)), account, math=BillingMath(idx))
    x, y = cp.Variable(len(idx)), cp.Variable(len(idx))
    math = BillingMath(idx, convex=True, power_bound=4.)
    math.register_power(x, np.zeros(len(idx)), np.full(len(idx), 4.))
    got = dpl.charge_lines(idx, x, y, account, math=math)
    problem = cp.Problem(cp.Minimize(sum(got["lines"].values())), [x == imports, y == 0, *math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status == cp.OPTIMAL
    for key, value in got["lines"].items():
        assert float(value.value if hasattr(value, "value") else value) == pytest.approx(raw["lines"][key], abs=1e-8)


@pytest.mark.parametrize("day", ["2024-12-31", "2025-07-01", "2025-08-01", "2025-10-01", "2025-12-31",
    "2026-01-01", "2026-04-30", "2026-11-01", "2027-01-01", "2025-1-1", None, 20250101])
def test_unverified_months_and_malformed_dates_reject(day):
    with pytest.raises(ValueError):
        rates_on(day)


@pytest.mark.parametrize("day", ["2025-01-01", "2025-06-30", "2025-09-01", "2025-09-30", "2026-05-01", "2026-10-31"])
def test_coverage_endpoints(day):
    assert rates_on(day)["component_month"] == day[:7]


def test_dst_march2025_uses743_elapsed_hours_and92_transition_day_intervals():
    account, idx = fixture(month="2025-03")
    assert len(idx) == 743 * 4
    assert sum(idx.date == pd.Timestamp("2025-03-09").date()) == 92
    review = dpl.cycle_review(account, idx)
    assert review["elapsed_hours"] == 743
    assert review["cycle_days"] == 31
    assert review["monthly_charge_factor"] == 1.
    assert bill(month="2025-03")["lines"]["distribution_customer"] == 9.43


def test_fall_dst_grid_is_valid_but_unsupported_month_rejects():
    account, idx = fixture(month="2025-11")
    assert len(idx) == 721 * 4
    assert sum(idx.date == pd.Timestamp("2025-11-02").date()) == 100
    with pytest.raises(ValueError):
        dpl.validate_account(account, idx)


@pytest.mark.parametrize("change", [
    dict(eligibility_confirmed=False), dict(ordinary_service_confirmed=False), dict(local_charges_confirmed=False),
    dict(full_monthly_charges_confirmed=False), dict(subtotal_scope_confirmed=False), dict(supply="retail_supplier"),
    dict(supply="pjm_lmp"), dict(export_mode="nem"), dict(phase="three"), dict(voltage="primary"),
    dict(voltage_v=208.), dict(tax_exempt=True), dict(tax_jurisdiction="delaware"), dict(meter_count=2),
    dict(service_line_count=2), dict(opening_credit_usd=1.), dict(cycle_source=""), dict(tax_source=""),
    dict(rate_evidence_mode="provisional"), dict(provisional_assumptions_accepted=True),
    dict(demand_interval_minutes=30), dict(relief_policy="estimated_refund"), dict(billing_month="2026-08-01"),
    dict(bill_date="2026-09-01"), dict(type_i_confirmed=True), dict(demand_method="utility_estimate"),
])
def test_independent_account_scope_confirmations(change):
    account, idx = fixture()
    with pytest.raises(ValueError):
        dpl.validate_account({**account, **change}, idx)


@pytest.mark.parametrize("month,year", [("2025-01", 2025), ("2026-09", 2026)])
def test_usc_year_and_utility_demand_assignment_must_be_documented(month, year):
    account, idx = fixture("SGS-S", month)
    for change in [dict(type_i_confirmed=False), dict(usc_band="1300_to_2599"), dict(demand_method="metered"),
            dict(estimated_demand_source=""), {f"usc_assignment_{year}_source":""}]:
        with pytest.raises(ValueError):
            dpl.validate_account({**account, **change}, idx)
    other = 2026 if year == 2025 else 2025
    dpl.validate_account({**account, f"usc_assignment_{other}_source":""}, idx)


def test_missing_duplicate_shifted_wrong_zone_and_hourly_data_reject():
    account, idx = fixture()
    for candidate in [idx[1:], idx[:-1], idx.delete(30), idx.insert(30, idx[30]), idx[::-1],
                      idx.tz_convert("America/Chicago"), idx + pd.Timedelta(days=1)]:
        with pytest.raises(ValueError):
            dpl.validate_account(account, candidate)
    _, hourly = fixture(step=60)
    with pytest.raises(ValueError):
        dpl.validate_account(account, hourly)


def test_sgs_actual_quarter_hour_peak_strictly_below20_even_when_estimated_bill_demand_is_small():
    _, idx = fixture("SGS-S")
    power = np.zeros(len(idx)); power[0] = 19.999
    assert bill("SGS-S", power=power)["metrics"]["actual_15_minute_peak_kw"] == pytest.approx(19.999)
    power[0] = 20.
    with pytest.raises(ValueError, match="below20kW"):
        bill("SGS-S", power=power)


def test_sgs3500kwh_cap_and_first20kw_transmission_block():
    _, idx = fixture("SGS-S")
    hours = len(idx) / 4
    got = bill("SGS-S", power=3500 / hours)
    assert got["metrics"]["estimated_billing_demand_kw"] == pytest.approx(20.)
    assert got["lines"]["transmission_demand"] == 0.
    assert got["lines"]["transmission_energy"] == pytest.approx(3500 * .018205)
    with pytest.raises(ValueError, match="3500kWh"):
        bill("SGS-S", power=3500.01 / hours)


def test_residential_study_cap_and_zero_import_customer_minimum():
    _, idx = fixture()
    hours = len(idx) / 4
    assert bill(power=7500 / hours)["lines"]["environmental_surcharge"] == pytest.approx(1.125)
    with pytest.raises(ValueError, match="7500kWh"):
        bill(power=7500.01 / hours)
    got = bill(power=0.)
    assert sum(got["lines"].values()) == pytest.approx(9.43 + .32)
    assert bill("SGS-S", power=0.)["lines"]["distribution_estimated_demand"] == 0.


def test_der_ordinary_service_export_and_opening_state_boundaries():
    account, idx = fixture()
    equipment = dict(pv=True, battery=True, pv_dc_kw=5., pv_ac_kw=4., battery_kw=3.)
    dpl.validate_account(account, idx, equipment)
    for change in [dict(der_ordinary_service_confirmed=False), dict(der_eligibility_source="")]:
        with pytest.raises(ValueError):
            dpl.validate_account({**account, **change}, idx, equipment)
    with pytest.raises(ValueError):
        dpl.validate_account(account, idx, dict(pv=False, battery=True))
    with pytest.raises(ValueError):
        dpl.validate_account(account, idx, {**equipment, "battery_kw":21.})
    with pytest.raises(ValueError):
        dpl.validate_state(account, idx, state={"credit":1})
    with pytest.raises(ValueError, match="exports"):
        dpl.charge_lines(idx, np.ones(len(idx)), np.ones(len(idx)), account, math=BillingMath(idx))


def test_source_metadata_follows_actual_monthly_original():
    for month,fragment,page in [("2025-01", "05012025", 2), ("2025-06", "09012025", 2), ("2026-09", "10_2026", 4)]:
        rates = rates_on(month + "-01", "SGS-S")
        assert fragment in rates["source"]
        assert rates["source_pdf_page"] == page


def test_catalog_keeps_subtotals_zero_export_and_eligibility_unconfirmed():
    for plan in dpl.PLANS:
        account, idx = fixture(plan)
        assert dpl.defaults(plan)["eligibility_confirmed"] is False
        assert dpl.defaults(plan)["subtotal_scope_confirmed"] is False
        assert dpl.evidence(idx, account)["objective_scope"] == "verified_charges_subtotal"
    for entry in dpl.catalog():
        assert entry["solar_modes"] == ["non_export"]
        assert entry["interval_minutes"] == [15]
        assert all(row["is_complete_bill"] is False for row in entry["coverage"])
