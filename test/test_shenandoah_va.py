"""SVEC base/PCA observations cannot bypass missing whole-bill evidence."""

import json
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import shenandoah_va as svec
from src.billing.regional_math import BillingMath
from src.billing.shenandoah_va_rates import BLOCKED_REASON, COVERAGE, PCA_OBSERVATIONS, rates_for_month, rates_on

EVIDENCE = Path(__file__).resolve().parents[1]/"docs/utility_sources/shenandoah_va"


def cycle(month):
    start = pd.Timestamp(month, tz=svec.TIMEZONE)
    return pd.date_range(start, start+pd.offsets.MonthBegin(), inclusive="left", freq="15min")


def confirmed(plan, month):
    account = svec.hypothetical_defaults(plan, day=month)
    account.update(dict.fromkeys(svec.CONFIRMATIONS, True))
    account.update(tax_source="Hypothetical account assertions cannot supply missing utility-period tax evidence",
                   der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
                   der_eligibility_source="Hypothetical exact ordinary-import approval cannot supply tariff evidence")
    if plan == "B-16":
        account.update(b_retained_assignment_confirmed=True,
                       b_demand_minimum_source="Hypothetical independent utility demand/minimum review",
                       b_rkva_source="Hypothetical independent utility RKVA review")
    return account


@pytest.mark.parametrize("plan", ("A-15", "B-16"))
@pytest.mark.parametrize("month", [f"{year}-{m:02}-01" for year in (2025, 2026) for m in range(1, 13)])
def test_all_requested_months_fail_closed_despite_account_confirmations(plan, month):
    index, account = cycle(month), confirmed(plan, month)
    for lookup in (rates_for_month, rates_on):
        with pytest.raises(ValueError, match="billing is unverified"):
            lookup(month, plan)
    with pytest.raises(ValueError, match="billing is unverified"):
        svec.validate_account(account, index, dict(pv=True, battery=True,
            renewable_only_charging=True, no_battery_export=True))
    with pytest.raises(ValueError, match="billing is unverified"):
        svec.charge_lines(index, np.ones(len(index)), np.zeros(len(index)), account, math=BillingMath(index))


def test_visible_catalog_retains_current_schedule_ids_without_enabled_billing():
    assert COVERAGE == ()
    assert svec.UTILITY == "shenandoah_valley_electric_cooperative"
    rows = svec.catalog()
    assert {r["id"] for r in rows} == {"A-15", "B-16"}
    for row in rows:
        assert row["status"] == "unsupported"
        assert row["billing_supported"] is row["dispatch_supported"] is False
        assert row["coverage"] == row["equipment_modes"] == row["solar_modes"] == []
        assert row["supply_arrangements"] == ["bundled"]
        assert row["base_effective_start"] == "2026-05-01"
        assert row["reason"] == BLOCKED_REASON
        assert row["coverage_gaps"][0]["start"] == "2025-01-01"
        assert row["coverage_gaps"][-1]["end"] == "2026-12-31"


def test_pca_source_observations_keep_every_boundary_and_no_december_extension():
    assert PCA_OBSERVATIONS == {
        "2025-12": .02818,
        "2026-01": .02299, "2026-02": .02299, "2026-03": .02299, "2026-04": .02299,
        "2026-05": .03411, "2026-06": .03411, "2026-07": .03411, "2026-08": .03411,
        "2026-09": .03411, "2026-10": .03411, "2026-11": .03411,
    }
    assert "2025-11" not in PCA_OBSERVATIONS and "2026-12" not in PCA_OBSERVATIONS
    # Observed PCA dates remain unavailable because they lack the full stack.
    for month in PCA_OBSERVATIONS:
        with pytest.raises(ValueError, match="STS-12"):
            rates_for_month(month)


@pytest.mark.parametrize("plan", ("A-15", "B-16"))
def test_defaults_and_hypothetical_labels_do_not_approve_der_or_account(plan):
    for account in (svec.defaults(plan), svec.hypothetical_defaults(plan)):
        assert all(account[key] is False for key in svec.CONFIRMATIONS)
        assert account["der_ordinary_service_confirmed"] is False
        assert account["der_activation_date"] == account["der_eligibility_source"] == ""
        if plan == "B-16":
            assert account["b_retained_assignment_confirmed"] is False


@pytest.mark.parametrize("changes", [
    {"supply": "sso"}, {"supply": "competitive"}, {"export_mode": "net_metering"},
    {"export_mode": "net_billing"}, {"tariff": "A-14"}, {"tariff": "B-15"}, {"tariff": "LP-16"},
])
def test_unsupported_supplier_export_and_historical_plan_ids_reject(changes):
    with pytest.raises(ValueError, match="A-15/B-16 bundled"):
        svec.validate_account({**confirmed("B-16", "2026-11-01"), **changes}, cycle("2026-11-01"))


def test_forced_surcharge_and_zero_cooperative_tax_factor_cannot_enable_billing():
    index, account = cycle("2026-11-01"), confirmed("A-15", "2026-11-01")
    account.update(sts=1.25, sts_successor_applicability_confirmed=True, federal_power_tax_reduction=0.,
                   federal_power_exemption_absent_confirmed=True, pca=.03411,
                   rate_evidence_mode="provisional", provisional_assumptions_accepted=True,
                   subtotal_scope_confirmed=True, opening_credit_usd=5.)
    for operation in (
        lambda: svec.validate_account(account, index),
        lambda: svec.validate_native_load(account, np.zeros(len(index))),
        lambda: svec.validate_state(account, index, {"credit": 5.}),
    ):
        with pytest.raises(ValueError, match="utility-period evidence"):
            operation()
    power = cp.Variable(len(index), nonneg=True)
    math = BillingMath(index, convex=True, power_bound=25.)
    with pytest.raises(ValueError, match="utility-period evidence"):
        svec.charge_lines(index, power, cp.Constant(np.zeros(len(index))), account, math=math)
    assert math.constraints == []


def test_calendar_dst_missing_duplicate_timezone_and_shifted_dates_reject():
    for month, hours in (("2025-03-01", 743), ("2025-11-01", 721), ("2026-03-01", 743), ("2026-11-01", 721)):
        index, account = cycle(month), confirmed("A-15", month)
        assert len(index)/4 == hours
        with pytest.raises(ValueError, match="billing is unverified"):
            svec.cycle_review(account, index)
        for bad in (index.delete(100), index.insert(100, index[100]), index[::2], index.tz_convert("UTC")):
            with pytest.raises(ValueError, match="consecutive"):
                svec.cycle_review(account, bad)
        with pytest.raises(ValueError, match="complete calendar"):
            svec.cycle_review(account, index[1:])
        with pytest.raises(ValueError, match="matching calendar"):
            svec.cycle_review({**account, "billing_month": "2026-06-01"}, index)


def test_ledger_retains_explicit_sts_tax_and_historical_gaps():
    ledger = json.loads((EVIDENCE/"sources.json").read_text())
    assert ledger["billing_status"] == "blocked_missing_complete_dated_component_intersections"
    assert ledger["coverage"] == ledger["executable_coverage"] == []
    assert ledger["retail_supplier"] == "Shenandoah Valley Electric Cooperative"
    assert ledger["wholesale_supplier_context"] == "Old Dominion Electric Cooperative"
    surcharge = ledger["surcharge_observation_not_applied"]
    assert surcharge["schedule"] == "STS-12" and surcharge["effective"] == "2026-01-05"
    assert surcharge["monthly_usd"] == "1.25"
    assert {"A-14", "B-14"} <= set(surcharge["expressly_named_schedules"])
    assert surcharge["successor_applicability_established"] is False
    assert ledger["cooperative_tax_factor"]["dated_numeric_factor_established"] is False
    assert ledger["cooperative_tax_factor"]["zero_factor_from_checkbox_allowed"] is False
    assert ledger["DER_scope"]["enabled"] is False
    for source in ledger["sources"]:
        assert source["url"].startswith("https://") and len(source["sha256"]) == 64
        assert int(source["sha256"], 16) >= 0 and source["bytes"] > 0


@pytest.mark.parametrize("operation", [svec.defaults, svec.hypothetical_defaults, svec.account_fields])
def test_unknown_plan_does_not_create_account_controls(operation):
    with pytest.raises(ValueError, match="A-15 or B-16"):
        operation("LP-16")
