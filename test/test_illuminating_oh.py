"""CEI's source/date, account, meter and ordinary-service acceptance boundaries.

Literal full-bill benchmarks and fixed-flow symbolic parity are separate. These
checks focus on published rules and reject unsupported evidence or settlement.
"""
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from src.billing import illuminating_oh as cei
from src.billing.illuminating_oh_rates import rates_on
from src.billing.regional_math import BillingMath
from src.timeseries import build_interval_index


MONTHS = ["2025-01-01", "2025-06-01", "2025-09-01", "2025-10-01",
          "2025-11-01", "2025-12-01", "2026-10-01"]


def fixture(plan="RS", day="2026-10-01"):
    a = cei.hypothetical_defaults(plan, day=day)
    grid = build_interval_index(day, a["bill_date"], cei.TIMEZONE, 15)
    return a, grid.index


def meter(index, energy=600.):
    return np.full(len(index), energy * 4 / len(index))


def bill(plan="RS", day="2026-10-01", *, energy=600., imports=None, account=None):
    a, index = fixture(plan, day)
    if account is not None:
        a = account
    cei.validate_account(a, index)
    return cei.charge_lines(index, meter(index, energy) if imports is None else imports,
                            np.zeros(len(index)), a, math=BillingMath(index))


def test_defaults_require_independent_enrollment_and_account_evidence():
    a, index = fixture()
    unconfirmed = cei.defaults()
    for field in ("eligibility_confirmed", "sso_enrollment_confirmed",
                  "ordinary_service_confirmed", "no_local_tax_confirmed",
                  "full_monthly_charges_confirmed", "der_ordinary_service_confirmed"):
        assert unconfirmed[field] is False
    with pytest.raises(ValueError):
        cei.validate_account(unconfirmed, index)
    # An ordinary grid-only account does not depend on an unused DER approval.
    a["der_ordinary_service_confirmed"] = False
    a["der_activation_date"] = ""
    a["der_eligibility_source"] = ""
    cei.validate_account(a, index)


@pytest.mark.parametrize("plan", ["RS", "GS"])
@pytest.mark.parametrize("day", MONTHS)
def test_complete_verified_months_are_itemized_and_have_no_credit_bank(plan, day):
    result = bill(plan, day)
    assert result["is_complete_bill"] is True
    assert result["rate_evidence_status"] == "verified"
    assert result["rate_assumptions"] == [] and result["excluded_components"] == []
    assert result["next_state"] == {}
    m = result["metrics"]
    assert m["raw_import_kwh"] == pytest.approx(600.)
    assert m["monthly_charge_factor"] == 1.
    assert m["partial_period_proration_applied"] is False
    assert m["demand_history_ratchet_applied"] is False
    assert m["additional_tax_percentage_applied"] is False
    assert m["rounded_cash_optimum_claimed"] is False
    assert result["lines"]["sales_tax"] == 0.
    assert not {"pjm_lmp", "wholesale_capacity", "export_credit", "minimum_top_up"} & result["lines"].keys()


@pytest.mark.parametrize("plan", ["RS", "GS"])
@pytest.mark.parametrize("day", ["2024-12-01", "2025-02-01", "2025-03-01",
    "2025-04-01", "2025-05-01", "2025-07-01", "2025-08-01",
    "2026-01-01", "2026-03-01", "2026-06-01", "2026-09-01", "2026-11-01"])
def test_missing_components_reject_instead_of_using_a_neighboring_tariff(plan, day):
    with pytest.raises(ValueError, match="unavailable|verified"):
        rates_on(day, plan)
    with pytest.raises(ValueError, match="unavailable|verified"):
        bill(plan, day)


def test_known_rate_boundaries_keep_distribution_reset_and_bill_rendered_dcr_separate():
    # Filed DCR54/55 changes are selected by bill-rendered month; March2026
    # base rates are usable only where all other components are also verified.
    assert rates_on("2025-11-30", "RS")["dcr"] == .010814
    assert rates_on("2025-12-01", "RS")["dcr"] == .010831
    assert rates_on("2025-12-31", "GS")["first_5_kw"] == 13.68
    assert rates_on("2026-10-01", "GS")["first_5_kw"] == 26.6451
    with pytest.raises(ValueError, match="matching"):
        rates_on("2025-12-01", "GS", bill_date="2026-01-01")


@pytest.mark.parametrize("field,value", [
    ("eligibility_confirmed", False), ("ordinary_service_confirmed", False),
    ("sso_enrollment_confirmed", False), ("no_local_tax_confirmed", False),
    ("full_monthly_charges_confirmed", False), ("eligibility_confirmed", 1),
    ("sso_enrollment_confirmed", "yes"), ("supply", "shopping"),
    ("supply", "aggregation"), ("export_mode", "net_metering"),
    ("voltage", "primary"), ("phase", "three"), ("voltage_v", 208.),
    ("power_factor", .95), ("meter_count", 2), ("meter_count", True),
    ("tax_jurisdiction", "municipal_franchise"), ("self_assessor", True),
    ("self_assessor", 0), ("opening_credit_usd", 1.),
    ("opening_credit_usd", False), ("demand_interval_minutes", 15),
    ("supply_source", ""), ("tax_source", " "), ("cycle_source", None),
    ("cycle_source", "x" * 501), ("cycle_kind", "initial"),
    ("bill_date", "2026-11-01"), ("bill_date", "2026-10-30"),
    ("billing_month", "2026-09-01"), ("rate_evidence_mode", "provisional_2025"),
    ("provisional_assumptions_accepted", True),
])
def test_unverified_account_supplier_tax_and_cycle_facts_reject(field, value):
    a, index = fixture()
    a[field] = value
    with pytest.raises((ValueError, TypeError)):
        cei.validate_account(a, index)


@pytest.mark.parametrize("field,value", [
    ("measured_demand_confirmed", False), ("contract_demand_confirmed", False),
    ("measured_demand_confirmed", 1), ("contract_source", ""),
    ("contract_demand_kw", True), ("contract_demand_kw", -1.),
    ("contract_demand_kw", 100.01), ("contract_demand_kw", float("nan")),
    ("contract_demand_kw", float("inf")),
])
def test_gs_requires_measured_demand_and_an_independent_documented_contract(field, value):
    a, index = fixture("GS")
    a[field] = value
    with pytest.raises(ValueError):
        cei.validate_account(a, index)


@pytest.mark.parametrize("field,value", [
    ("measured_demand_confirmed", True), ("contract_demand_confirmed", True),
    ("contract_demand_kw", 5.), ("contract_demand_kw", False),
    ("contract_source", "Commercial contract does not establish residential eligibility"),
])
def test_rs_rejects_mixed_commercial_contract_assertions(field, value):
    a, index = fixture()
    a[field] = value
    with pytest.raises(ValueError):
        cei.validate_account(a, index)


@pytest.mark.parametrize("bad", ["missing", "duplicate", "reverse", "naive", "utc",
                                  "wrong_zone", "hourly", "partial", "shifted"])
def test_incomplete_or_wrong_clock_meter_indices_reject(bad):
    a, index = fixture()
    if bad == "missing": index = index.delete(100)
    elif bad == "duplicate": index = index.insert(100, index[99])
    elif bad == "reverse": index = index[::-1]
    elif bad == "naive": index = index.tz_localize(None)
    elif bad == "utc": index = index.tz_convert("UTC")
    elif bad == "wrong_zone": index = index.tz_convert("America/Chicago")
    elif bad == "hourly": index = index[::4]
    elif bad == "partial": index = index[:-1]
    else: index = index + pd.Timedelta(minutes=15)
    with pytest.raises(ValueError):
        cei.cycle_review(a, index)


def test_fall_dst_uses_every_physical_interval_but_thirty_local_tax_days():
    a, index = fixture(day="2025-11-01")
    cycle = cei.cycle_review(a, index)
    assert len(index) == 721 * 4
    assert cycle["elapsed_hours"] == 721.
    assert cycle["cycle_days"] == 30
    assert cycle["state_tax_thresholds_kwh"] == [2000., 15000.]
    assert bill(day="2025-11-01")["metrics"]["raw_import_kwh"] == pytest.approx(600.)


@pytest.mark.parametrize("day", ["2025-03-01", "2026-03-01"])
def test_spring_dst_grid_is_valid_but_missing_tariff_evidence_still_rejects(day):
    a, index = fixture(day=day)
    assert len(index) == 743 * 4
    with pytest.raises(ValueError, match="unavailable"):
        cei.cycle_review(a, index)


@pytest.mark.parametrize("day", ["2025-01-01", "2025-10-01", "2026-10-01"])
def test_thirty_one_day_state_tax_uses_statutory_daily_bands(day):
    a, index = fixture(day=day)
    m = cei.cycle_review(a, index)
    assert m["cycle_days"] == 31
    assert m["state_tax_thresholds_kwh"] == [2077., 15500.]


def test_thirty_minute_demand_does_not_bill_a_fifteen_minute_spike():
    a, index = fixture("GS")
    a["contract_demand_kw"] = 5.
    p = np.ones(len(index))
    p[:4] = [20., 0., 2., 18.]
    r = bill("GS", account=a, imports=p)
    assert r["metrics"]["actual_30_minute_peak_kw"] == 10.
    assert r["metrics"]["billing_demand_kw"] == 10.
    assert r["lines"]["distribution_demand"] == pytest.approx(26.6451 + 5 * 12.5319)


@pytest.mark.parametrize("contract,expected", [(0., 5.), (5., 5.), (12., 12.), (40., 40.)])
def test_low_imports_retain_actual_contract_and_five_kw_floor(contract, expected):
    a, index = fixture("GS")
    a["contract_demand_kw"] = contract
    result = bill("GS", account=a, imports=np.ones(len(index)))
    assert result["metrics"]["billing_demand_kw"] == expected
    assert result["lines"]["distribution_demand"] == pytest.approx(26.6451 + (expected - 5) * 12.5319)
    assert result["lines"]["non_market_transmission"] == pytest.approx(expected * 6.6568)


@pytest.mark.parametrize("plan", ["RS", "GS"])
@pytest.mark.parametrize("state", [{"credit_usd": 1.}, {"history_billing_kw": [50.] * 11},
                                    {"through_month": "2026-09-01"}])
def test_no_export_bank_or_invented_trailing_ratchet_is_accepted(plan, state):
    a, index = fixture(plan)
    before = deepcopy(state)
    with pytest.raises(ValueError, match="bank|ratchet"):
        cei.validate_state(a, index, state=state)
    assert state == before


@pytest.mark.parametrize("plan", ["RS", "GS"])
def test_zero_energy_does_not_remove_published_fixed_and_demand_obligations(plan):
    a, _ = fixture(plan, "2025-01-01")
    if plan == "GS": a["contract_demand_kw"] = 0.
    r = bill(plan, "2025-01-01", energy=0., account=a)
    if plan == "RS":
        assert r["lines"]["distribution_customer"] == 4.
        assert r["lines"]["consumer_rate_credit"] == -.51
        assert r["lines"]["legacy_generation"] == 1.5
    else:
        assert r["lines"]["distribution_demand"] == 13.68
        assert r["metrics"]["billing_demand_kw"] == 5.
    assert r["lines"]["state_kwh_tax"] == pytest.approx(0.)
    assert "minimum_top_up" not in r["lines"]


def test_january_dcr_excludes_all_riders_and_rer_is_mandatory_for_ordinary_rs():
    r = bill(day="2025-01-01", energy=1000.)
    assert r["lines"]["delivery_capital"] == pytest.approx((4 + 1000 * .02951) * .478156)
    assert r["lines"]["phase_in_recovery"] == pytest.approx(.427)
    assert r["lines"]["residential_heating_recovery"] == pytest.approx(1.172)
    assert r["lines"]["consumer_rate_credit"] == -.51
    assert r["lines"]["tax_savings"] == pytest.approx(-1.865)


@pytest.mark.parametrize("plan,peak", [("RS", 25.01), ("GS", 100.01)])
def test_conservative_study_power_envelopes_are_enforced(plan, peak):
    a, index = fixture(plan)
    p = np.zeros(len(index))
    p[100] = peak
    with pytest.raises(ValueError, match="envelope"):
        bill(plan, account=a, imports=p)


@pytest.mark.parametrize("plan", ["RS", "GS"])
def test_positive_exports_are_rejected_without_a_settlement_credit(plan):
    a, index = fixture(plan)
    x = np.zeros(len(index))
    x[10] = 1.
    with pytest.raises(ValueError, match="zero exports"):
        cei.charge_lines(index, meter(index), x, a, math=BillingMath(index))


@pytest.mark.parametrize("kind", ["no_approval", "late", "missing_date", "missing_source",
    "standalone", "grid_charge", "battery_export", "oversize"])
def test_der_requires_active_ordinary_approval_for_the_exact_bounded_configuration(kind):
    a, index = fixture()
    equipment = dict(pv=True, battery=True, pv_dc_kw=5., pv_ac_kw=4., battery_kw=3.,
                     renewable_only_charging=True, no_battery_export=True)
    if kind == "no_approval": a["der_ordinary_service_confirmed"] = False
    elif kind == "late": a["der_activation_date"] = "2026-10-02"
    elif kind == "missing_date": a["der_activation_date"] = ""
    elif kind == "missing_source": a["der_eligibility_source"] = ""
    elif kind == "standalone": equipment["pv"] = False
    elif kind == "grid_charge": equipment["renewable_only_charging"] = False
    elif kind == "battery_export": equipment["no_battery_export"] = False
    else: equipment["pv_dc_kw"] = 23.
    with pytest.raises(ValueError):
        cei.validate_account(a, index, equipment=equipment)
