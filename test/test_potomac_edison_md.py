"""Independent Potomac Edison Maryland literals, published bills and scope."""
from copy import deepcopy
from decimal import Decimal as D, ROUND_HALF_UP

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import potomac_edison_md as pe
from src.billing import regional
from src.billing.potomac_edison_md_rates import rates_on
from src.billing.regional_math import BillingMath
from src.timeseries import build_interval_index


def fixture(plan="R", month="2026-09", step=15):
    start = month + "-01"
    end = str((pd.Timestamp(start) + pd.offsets.MonthEnd()).date())
    account = pe.hypothetical_defaults(plan)
    account.update(billing_month=start, bill_date=end)
    if plan == "G":
        account["history"] = pe.hypothetical_history(start)
    return account, build_interval_index(start, end, pe.TIMEZONE, step).index


def power_for_energy(idx, energy, peak=None):
    power = np.full(len(idx), energy / (len(idx) / 4))
    if peak is not None:
        power[:2] = peak
        power[2:] = (energy * 4 - 2 * peak) / (len(idx) - 2)
    return power


def bill(plan="R", month="2026-09", energy=1000., *, account=None, state=None, peak=None):
    a, idx = fixture(plan, month)
    a = a if account is None else account
    pe.validate_account(a, idx)
    return pe.charge_lines(idx, power_for_energy(idx, energy, peak), np.zeros(len(idx)), a,
                           math=BillingMath(idx), state=state)


# Current adopted book physical R62, G69/70; combined2026 adjustment sheet p1.
# Supply energy prices include admin; the adapter must split, not add it twice.
@pytest.mark.parametrize("plan,month,supply,trans,pca,credit,admin", [
    ("R", "2026-09", [.10824], [.00396], .01716, -.00234, .004),
    ("R", "2026-10", [.10209], [.00396], .01828, -.00210, .004),
    ("G", "2026-09", [.13108, .06067], [.00440, .00214], .01841, -.00230, .00550),
    ("G", "2026-10", [.15064, .06977], [.00440, .00214], -.00338, -.00224, .00550),
])
def test_independent_dated_supply_delivery_adjustment_literals(plan, month, supply, trans, pca, credit, admin):
    got = bill(plan, month)
    e = 1000.
    expected_supply = e * supply[0] if plan == "R" else 700 * supply[0] + 300 * supply[1]
    expected_trans = e * trans[0] if plan == "R" else 700 * trans[0] + 300 * trans[1]
    assert got["lines"]["generation_energy"] + got["lines"]["supply_administration"] == pytest.approx(expected_supply)
    assert got["lines"]["supply_administration"] == pytest.approx(e * admin)
    assert got["lines"]["transmission_energy"] == pytest.approx(expected_trans)
    assert got["lines"]["procurement_energy_cost_adjustment"] == pytest.approx(e * pca)
    assert got["lines"]["administrative_delivery_credit"] == pytest.approx(e * credit)
    assert got["lines"]["distribution_customer"] == (6. if plan == "R" else 4.85)
    assert got["lines"]["universal_service"] == (.32 if plan == "R" else 1.84)
    assert got["lines"]["empower_maryland"] == pytest.approx(e * (.01376 if plan == "R" else .01142))
    assert got["lines"]["purpa_termination_surcharge"] == pytest.approx(e * (.00806 if plan == "R" else .00953))
    assert got["lines"]["franchise_tax"] == pytest.approx(e * .000620)
    assert got["lines"]["environmental_surcharge"] == pytest.approx(e * .000149)
    assert got["metrics"]["additional_gross_receipts_tax_applied"] is False
    assert not {"edis", "pjm_capacity", "pjm_transmission", "wholesale_energy", "psc_assessment",
                "distribution_gross_receipts_tax", "transmission_gross_receipts_tax"} & set(got["lines"])


@pytest.mark.parametrize("month,generation,pca,credit,total", [
    ("2026-09", "104.24", "17.16", "-2.34", "178.799"),
    ("2026-10", "98.09", "18.28", "-2.10", "174.009"),
])
def test_full_residential_raw_independent1000kwh_arithmetic(month, generation, pca, credit, total):
    got = bill(month=month)
    expected = dict(distribution_customer=D("6"), distribution_energy=D("22.87"),
        universal_service=D(".32"), residential_rggi_credit=D("0"),
        procurement_energy_cost_adjustment=D(pca), administrative_delivery_credit=D(credit),
        purpa_termination_surcharge=D("8.06"), empower_maryland=D("13.76"),
        franchise_tax=D(".620"), environmental_surcharge=D(".149"),
        generation_energy=D(generation), transmission_energy=D("3.96"), supply_administration=D("4"))
    assert set(got["lines"]) == set(expected)
    for key, amount in expected.items():
        assert got["lines"][key] == pytest.approx(float(amount), abs=1e-10)
    assert sum(expected.values()) == D(total)
    assert sum(got["lines"].values()) == pytest.approx(float(total))
    assert got["is_complete_bill"] is True and got["excluded_components"] == []
    assert got["rate_evidence_status"] == "verified" and got["rate_assumptions"] == []


def test_official_current_distribution_bill_benchmarks_only():
    # Sep4,2026 filing ExhibitRV13 CURRENT column Rphysical172/G173.
    # Proposed prices are not effective. Both published cases have inactive minima.
    r = bill(energy=1000.)
    assert r["lines"]["distribution_customer"] + r["lines"]["distribution_energy"] == pytest.approx(28.87)
    g = bill("G", energy=730., peak=5.)
    base = g["lines"]["distribution_customer"] + g["lines"]["distribution_energy"]
    assert D(str(base)).quantize(D(".01"), rounding=ROUND_HALF_UP) == D("21.22")
    assert g["metrics"]["actual_30_minute_peak_kw"] == pytest.approx(5.)
    assert g["metrics"]["distribution_minimum_inactive_verified"] is True
    # Adding1.70*5 to this ordinary branch would contradict the published21.22.
    assert base == pytest.approx(4.85 + .02243 * 730)


@pytest.mark.parametrize("month,supply,trans", [
    ("2026-09", [.13108, .06067], [.00440, .00214]),
    ("2026-10", [.15064, .06977], [.00440, .00214]),
])
@pytest.mark.parametrize("energy", [699.999, 700., 700.001])
def test_g700kwh_inclusive_supply_admin_and_transmission_tiers(month, supply, trans, energy):
    got = bill("G", month, energy)
    low, high = min(energy, 700), max(energy - 700, 0)
    assert got["lines"]["generation_energy"] + got["lines"]["supply_administration"] == pytest.approx(low*supply[0] + high*supply[1], abs=1e-9)
    assert got["lines"]["transmission_energy"] == pytest.approx(low*trans[0] + high*trans[1], abs=1e-9)


@pytest.mark.parametrize("plan", ["R", "G"])
@pytest.mark.parametrize("month", ["2026-09", "2026-10"])
def test_numeric_convex_itemized_parity(plan, month):
    a, idx = fixture(plan, month)
    imports = .6 + 1.6 * (np.arange(len(idx)) % 17) / 16
    raw = pe.charge_lines(idx, imports, np.zeros(len(idx)), a, math=BillingMath(idx))
    x, y = cp.Variable(len(idx)), cp.Variable(len(idx))
    math = BillingMath(idx, convex=True, power_bound=3.)
    math.register_power(x, np.zeros(len(idx)), np.full(len(idx), 3.))
    got = pe.charge_lines(idx, x, y, a, math=math)
    problem = cp.Problem(cp.Minimize(sum(got["lines"].values())), [x == imports, y == 0, *math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status == cp.OPTIMAL
    for key, value in got["lines"].items():
        assert float(value.value if hasattr(value, "value") else value) == pytest.approx(raw["lines"][key], abs=1e-8)
    if plan == "G":
        assert got["metrics"]["distribution_minimum_inactive_verified"] is None
        assert float(got["next_state"]["history"][-1]["import_kwh"].value) == pytest.approx(sum(imports)/4)


def test_g_history_carries_imports_and_cannot_reset_after_pv_reduction():
    september = bill("G", energy=1500.)
    history = september["next_state"]["history"]
    assert len(history) == 12
    assert history[0] == {"month":"2025-10", "import_kwh":1000.}
    assert history[-1] == {"month":"2026-09", "import_kwh":pytest.approx(1500.)}
    # October200kWh passes with1000kWh hypothetical history, but not carried1500.
    assert bill("G", "2026-10", energy=200.)["metrics"]["distribution_minimum_inactive_verified"] is True
    with pytest.raises(ValueError, match="inactive domain"):
        bill("G", "2026-10", energy=200., state=september["next_state"])
    accepted = bill("G", "2026-10", energy=1000., state=september["next_state"])
    assert accepted["metrics"]["unmetered_minimum_capacity_raw_kw"] == pytest.approx(4.)
    assert accepted["next_state"]["history"][-1]["month"] == "2026-10"
    assert september["next_state"]["history"] == history


def test_distribution_minimum_guard_boundary_rejects_instead_of_forcing_imports():
    # priorMax1000=>M=2kW for E<500; conservative bound1.70*(2+.25)=3.825.
    threshold = 3.825 / .02243
    assert bill("G", energy=threshold+.01)["metrics"]["distribution_minimum_inactive_verified"] is True
    with pytest.raises(ValueError, match="inactive domain"):
        bill("G", energy=threshold-.01)
    with pytest.raises(ValueError, match="inactive domain"):
        bill("G", energy=0.)
    a, idx = fixture("G")
    x, y = cp.Variable(len(idx)), cp.Variable(len(idx))
    math = BillingMath(idx, convex=True, power_bound=1.)
    math.register_power(x, np.zeros(len(idx)), np.ones(len(idx)))
    pe.charge_lines(idx, x, y, a, math=math)
    problem = cp.Problem(cp.Minimize(cp.sum(x)), [x == 0, y == 0, *math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status == cp.OPTIMAL  # No artificial minimum-import constraint.
    with pytest.raises(ValueError, match="inactive domain"):
        pe.charge_lines(idx, np.zeros(len(idx)), np.zeros(len(idx)), a, math=BillingMath(idx))


def test_unmetered_capacity_upper_bound_rejects_before_excess7_5_formula_is_assumed():
    # Actual peak can be small while the energy-based capacity is above7.5.
    with pytest.raises(ValueError):
        bill("G", energy=2000.)
    a, _ = fixture("G")
    a["history"][0]["import_kwh"] = 4000.
    with pytest.raises(ValueError):
        bill("G", energy=1000., account=a)
    assert bill("G", energy=1500.)["metrics"]["minimum_capacity_conservative_upper_kw"] == pytest.approx(6.25)


def test_g_excluded_charges_are_absent_unknowns_and_not_zero_or_complete():
    got = bill("G")
    assert got["excluded_components"] == ["g_transmission_minimum_capacity_charge", "maryland_state_sales_tax"]
    assert got["is_complete_bill"] is False
    assert "transmission_minimum_capacity_status" in got["metrics"]
    assert not {"transmission_capacity", "transmission_minimum", "sales_tax"} & set(got["lines"])
    a, idx = fixture("G")
    assert pe.evidence(idx, a)["objective_scope"] == "verified_charges_subtotal"
    assert any("unknown charges can change dispatch ranking" in x for x in pe.catalog()[1]["limitations"])


def test_g_actual_half_hour_average_and7_5kw_boundary():
    a, idx = fixture("G")
    power = power_for_energy(idx, 1000.)
    power[:2] = [14.998, 0.]
    got = pe.charge_lines(idx, power, np.zeros(len(idx)), a, math=BillingMath(idx))
    assert got["metrics"]["actual_30_minute_peak_kw"] == pytest.approx(7.499)
    power[:2] = [15., 0.]
    with pytest.raises(ValueError, match="below7.5kW"):
        pe.charge_lines(idx, power, np.zeros(len(idx)), a, math=BillingMath(idx))


@pytest.mark.parametrize("day", ["2025-01-01", "2025-12-31", "2026-01-01", "2026-05-31", "2026-06-01",
    "2026-08-31", "2026-11-01", "2027-01-01", "2026-9-1", None, 20260901])
def test_unverified_dates_and_nonexact_iso_reject(day):
    with pytest.raises(ValueError):
        rates_on(day)


@pytest.mark.parametrize("day", ["2026-09-01", "2026-09-30", "2026-10-01", "2026-10-31"])
def test_supported_closed_date_edges(day):
    assert rates_on(day)["component_month"] == day[:7]


@pytest.mark.parametrize("month,day,hours,count", [("2026-03", "2026-03-08", 743, 92), ("2026-11", "2026-11-01", 721, 100)])
def test_dst_elapsed_grids_are_preserved_but_unsupported_billing_rejects(month, day, hours, count):
    a, idx = fixture(month=month)
    assert len(idx) == hours*4
    assert sum(idx.date == pd.Timestamp(day).date()) == count
    with pytest.raises(ValueError, match="intersections"):
        pe.validate_account(a, idx)


@pytest.mark.parametrize("change", [dict(eligibility_confirmed=False), dict(ordinary_service_confirmed=False),
    dict(local_charges_confirmed=False), dict(full_monthly_charges_confirmed=False), dict(supply="retail_supplier"),
    dict(supply="pjm_lmp"), dict(export_mode="nem"), dict(tax_source=""), dict(cycle_source=""),
    dict(tax_jurisdiction="west_virginia"), dict(tax_exempt=True), dict(phase="three"), dict(voltage="primary"),
    dict(voltage_v=208.), dict(power_factor=.9), dict(meter_count=2), dict(service_line_count=2),
    dict(opening_credit_usd=1.), dict(demand_interval_minutes=15), dict(type_i_confirmed=True),
    dict(demand_method="unmetered"), dict(history=[{}]), dict(rate_evidence_mode="provisional"),
    dict(provisional_assumptions_accepted=True), dict(bill_date="2026-10-01")])
def test_account_scope_independent_confirmations(change):
    a, idx = fixture()
    with pytest.raises(ValueError):
        pe.validate_account({**a, **change}, idx)


@pytest.mark.parametrize("change", [dict(type_i_confirmed=False), dict(demand_method="metered"),
    dict(unmetered_source=""), dict(history_confirmed=False), dict(history_source=""),
    dict(usc_band="1300_to_2599"), dict(usc_assignment_2026_source=""), dict(subtotal_scope_confirmed=False)])
def test_g_utility_history_usc_and_subtotal_approval_required(change):
    a, idx = fixture("G")
    with pytest.raises(ValueError):
        pe.validate_account({**a, **change}, idx)


@pytest.mark.parametrize("kind", ["short", "duplicate", "gap", "unordered", "nan", "negative", "above_domain", "bool", "wrong_month", "extra_key"])
def test_g_history_rejects_missing_or_invalid_observations(kind):
    a, idx = fixture("G")
    h = deepcopy(a["history"])
    if kind == "short": h.pop()
    elif kind == "duplicate": h[-1]["month"] = h[-2]["month"]
    elif kind == "gap": h[4]["month"] = "2025-01"
    elif kind == "unordered": h.reverse()
    elif kind == "nan": h[0]["import_kwh"] = float("nan")
    elif kind == "negative": h[0]["import_kwh"] = -1.
    elif kind == "above_domain": h[0]["import_kwh"] = 6000.01
    elif kind == "bool": h[0]["import_kwh"] = True
    elif kind == "wrong_month": h[0]["month"] = "2025-9"
    elif kind == "extra_key": h[0]["capacity_kw"] = 4.
    with pytest.raises(ValueError):
        pe.validate_account({**a, "history":h}, idx)


def test_g_carried_history_must_immediately_precede_cycle():
    a, idx = fixture("G", "2026-10")
    with pytest.raises(ValueError, match="immediately before"):
        pe.validate_state(a, idx, state={"history":pe.hypothetical_history("2026-09-01")})
    with pytest.raises(ValueError):
        pe.validate_state(a, idx, state={"credit":1.})


def test_missing_duplicate_shifted_wrong_timezone_hourly_data_reject():
    a, idx = fixture()
    for candidate in [idx[1:], idx[:-1], idx.delete(30), idx.insert(30, idx[30]), idx[::-1],
                      idx.tz_convert("America/Chicago"), idx+pd.Timedelta(days=1)]:
        with pytest.raises(ValueError):
            pe.validate_account(a, candidate)
    _, hourly = fixture(step=60)
    with pytest.raises(ValueError):
        pe.validate_account(a, hourly)


def test_der_ordinary_approval_export_and_state_rejections():
    a, idx = fixture()
    equipment = dict(pv=True, battery=True, pv_dc_kw=5., pv_ac_kw=4., battery_kw=3.)
    pe.validate_account(a, idx, equipment)
    for change in [dict(der_ordinary_service_confirmed=False), dict(der_eligibility_source="")]:
        with pytest.raises(ValueError):
            pe.validate_account({**a, **change}, idx, equipment)
    with pytest.raises(ValueError):
        pe.validate_account(a, idx, dict(pv=False, battery=True))
    with pytest.raises(ValueError):
        pe.validate_account(a, idx, {**equipment, "battery_kw":21.})
    with pytest.raises(ValueError):
        pe.charge_lines(idx, np.ones(len(idx)), np.ones(len(idx)), a, math=BillingMath(idx))
    with pytest.raises(ValueError):
        pe.validate_state(a, idx, state={"history":[]})


def test_authoritative_regional_bill_rounds_mes_components_and_retains_raw_arithmetic():
    a, idx = fixture()
    power = power_for_energy(idx, 1000.)
    got = regional.calculate_cycle(pe.UTILITY, idx, power, np.zeros(len(idx)), a)
    assert got["unrounded_lines"]["environmental_surcharge"] == pytest.approx(.149)
    assert got["lines"]["environmental_surcharge"] == .15
    assert got["unrounded_total_usd"] == pytest.approx(178.799)
    assert got["total_usd"] == pytest.approx(178.80)
    assert abs(got["total_usd"] - got["unrounded_total_usd"]) <= got["rounding_bound_usd"]
    assert "unrounded" in got["metrics"]["objective_rounding_scope"].lower()
    assert got["is_complete_bill"] is True


def test_catalog_defaults_keep_account_eligibility_unconfirmed_and_scope_separate():
    for plan in pe.PLANS:
        assert pe.defaults(plan)["eligibility_confirmed"] is False
        a, idx = fixture(plan)
        assert pe.evidence(idx, a)["objective_scope"] == ("complete_utility_bill" if plan == "R" else "verified_charges_subtotal")
    for row in pe.catalog():
        assert row["solar_modes"] == ["non_export"] and row["interval_minutes"] == [15]
        assert [(x["start"], x["end"]) for x in row["coverage"]] == [("2026-09-01", "2026-10-31")]
        assert row["coverage"][0]["is_complete_bill"] is (row["id"] == "R")
