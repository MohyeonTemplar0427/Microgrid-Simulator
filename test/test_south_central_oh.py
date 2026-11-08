"""South Central Power source evidence cannot enable unverified bill cycles."""

from decimal import Decimal as D, ROUND_HALF_UP
import json
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import south_central_oh as scp
from src.billing.regional_math import BillingMath
from src.billing.south_central_oh_rates import BLOCKED_REASON, COVERAGE, rates_for_month, rates_on


EVIDENCE = Path(__file__).resolve().parents[1]/"docs/utility_sources/south_central_oh"


def cycle(month):
    start = pd.Timestamp(month, tz=scp.TIMEZONE)
    return pd.date_range(start, start+pd.offsets.MonthBegin(), inclusive="left", freq="15min")


def confirmed(plan, month):
    account = scp.hypothetical_defaults(plan, day=month)
    account.update(dict.fromkeys(scp.CONFIRMATIONS, True))
    account.update(transformer_kva=5., transformer_source="Hypothetical utility transformer allocation",
                   tax_source="Hypothetical ordinary Ohio state tax and absent additional impositions",
                   der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
                   der_eligibility_source="Hypothetical exact installation approval cannot supply missing rates")
    if plan == "SGS":
        account.update(sgs_retained_assignment_confirmed=True,
                       sgs_classification_source="Hypothetical cooperative-retained SGS with independent actual history")
    return account


@pytest.mark.parametrize("plan", ("R", "SGS"))
@pytest.mark.parametrize("month", [f"{year}-{m:02}-01" for year in (2025, 2026) for m in range(1, 13)])
def test_all_requested_months_reject_missing_intersections(plan, month):
    index, account = cycle(month), confirmed(plan, month)
    for lookup in (rates_for_month, rates_on):
        with pytest.raises(ValueError, match="billing is unverified"):
            lookup(month, plan)
    with pytest.raises(ValueError, match="billing is unverified"):
        scp.validate_account(account, index, dict(pv=True, battery=True,
            renewable_only_charging=True, no_battery_export=True))
    with pytest.raises(ValueError, match="billing is unverified"):
        scp.charge_lines(index, np.ones(len(index)), np.zeros(len(index)), account, math=BillingMath(index))


def test_catalog_is_visible_unavailable_without_equipment_or_executable_dates():
    assert COVERAGE == ()
    assert scp.UTILITY == "south_central_power_ohio"
    rows = scp.catalog()
    assert {r["id"] for r in rows} == {"R", "SGS"}
    for row in rows:
        assert row["status"] == "unsupported"
        assert row["billing_supported"] is row["dispatch_supported"] is False
        assert row["coverage"] == row["equipment_modes"] == row["solar_modes"] == []
        assert row["supply_arrangements"] == ["bundled"]
        assert row["reason"] == BLOCKED_REASON
        assert row["coverage_gaps"][0]["start"] == "2025-01-01"
        assert row["coverage_gaps"][0]["end"] == "2026-12-31"


@pytest.mark.parametrize("plan", ("R", "SGS"))
def test_defaults_and_hypothetical_labels_never_approve_account_or_der(plan):
    for account in (scp.defaults(plan), scp.hypothetical_defaults(plan)):
        assert all(account[key] is False for key in scp.CONFIRMATIONS)
        assert account["der_ordinary_service_confirmed"] is False
        assert account["der_activation_date"] == account["der_eligibility_source"] == ""
        assert account["transformer_kva"] is None
        assert account["supply"] == "bundled"
        if plan == "SGS":
            assert account["sgs_retained_assignment_confirmed"] is False


@pytest.mark.parametrize("changes", [
    {"supply": "sso"}, {"supply": "competitive"}, {"export_mode": "net_metering"},
    {"export_mode": "net_billing"}, {"tariff": "GS"}, {"tariff": "MGS"},
])
def test_unsupported_supplier_settlement_and_classes_reject(changes):
    with pytest.raises(ValueError, match="R/SGS bundled"):
        scp.validate_account({**confirmed("SGS", "2026-06-01"), **changes}, cycle("2026-06-01"))


def test_manual_sample_factors_or_assumptions_cannot_enable_pricing_or_dispatch():
    index, account = cycle("2026-06-01"), confirmed("R", "2026-06-01")
    account.update(generation=.078845, transmission=.030777, rider_A=0.,
                   rate_evidence_mode="provisional", provisional_assumptions_accepted=True,
                   subtotal_scope_confirmed=True, opening_credit_usd=10.)
    for operation in (
        lambda: scp.validate_account(account, index),
        lambda: scp.validate_native_load(account, np.zeros(len(index))),
        lambda: scp.validate_state(account, index, {"credit": 10.}),
    ):
        with pytest.raises(ValueError, match="billing is unverified"):
            operation()
    power = cp.Variable(len(index), nonneg=True)
    math = BillingMath(index, convex=True, power_bound=25.)
    with pytest.raises(ValueError, match="billing is unverified"):
        scp.charge_lines(index, power, cp.Constant(np.zeros(len(index))), account, math=math)
    assert math.constraints == []


def test_calendar_dst_and_missing_intervals_do_not_bypass_rate_gap():
    for month, hours in (("2025-03-01", 743), ("2025-11-01", 721), ("2026-03-01", 743), ("2026-11-01", 721)):
        index, account = cycle(month), confirmed("R", month)
        assert len(index)/4 == hours
        with pytest.raises(ValueError, match="billing is unverified"):
            scp.cycle_review(account, index)
        for malformed in (index.delete(100), index.insert(100, index[100]), index[::2], index.tz_convert("UTC")):
            with pytest.raises(ValueError, match="consecutive"):
                scp.cycle_review(account, malformed)
        with pytest.raises(ValueError, match="complete calendar"):
            scp.cycle_review(account, index[1:])
        with pytest.raises(ValueError, match="matching service/billing"):
            scp.cycle_review({**account, "bill_date": "2026-06-02"}, index)


def test_dated_sample_invoice_reconciles_with_literal_decimal_arithmetic_only():
    sample = json.loads((EVIDENCE/"sample_bill_benchmark.json").read_text())
    # Independent literal transcription of the official two-page example bill,
    # deliberately not a call to tariff pricing or production rate constants.
    energy = D("1201")
    raw = dict(delivery_customer=D("34.00"), delivery_energy=energy*D("0.026"),
               generation=energy*D("0.078845"), transmission=energy*D("0.030777"),
               ohio_kwh_tax=energy*D("0.00465"))
    rounded = {key: value.quantize(D(".01"), rounding=ROUND_HALF_UP) for key, value in raw.items()}
    assert rounded == dict(delivery_customer=D("34.00"), delivery_energy=D("31.23"),
                           generation=D("94.69"), transmission=D("36.96"), ohio_kwh_tax=D("5.58"))
    assert sum(rounded.values()) == D("202.46")
    assert raw == {key: D(value) for key, value in sample["independent_unrounded_lines_usd"].items()}
    assert rounded == {key: D(value) for key, value in sample["printed_lines_usd"].items()}
    assert sample["service_start"] == "2026-04-30" and sample["service_end"] == "2026-05-29"
    assert sample["bill_date"] == "2026-06-02"
    assert sample["broader_cycle_applicability_established"] is sample["SGS_applicability_established"] is False
    assert sample["executable_coverage"] == []


def test_source_ledger_retains_base_minimum_and_monthly_applicability_gaps():
    ledger = json.loads((EVIDENCE/"sources.json").read_text())
    assert ledger["billing_status"] == "blocked_missing_complete_monthly_component_intersections"
    assert ledger["coverage"] == ledger["executable_coverage"] == []
    assert ledger["retail_supplier"] == "South Central Power Company"
    assert ledger["wholesale_supplier_context"] == "Buckeye Power"
    rows = ledger["base_component_observations_not_executable_bills"]
    assert [(r["effective"], r["R_customer_usd"], r["SGS_customer_usd"]) for r in rows] == [
        ("2024-04-01", "27.00", "38.00"), ("2025-04-01", "29.00", "41.00"), ("2026-04-01", "34.00", "48.00")]
    assert all(r["distribution_usd_per_kwh"] == "0.0260" for r in rows)
    assert ledger["DER_scope"]["enabled"] is False
    assert len(ledger["sources"]) == 24
    for source in ledger["sources"]:
        assert source["url"].startswith("https://") and len(source["sha256"]) == 64
        assert int(source["sha256"], 16) >= 0 and source["bytes"] > 0
    examples = [s for s in ledger["sources"] if s["evidence_kind"] == "dated_example_invoice_only"]
    assert len(examples) == 1 and examples[0]["filename"] == "Residential-Bill-Example-2026.pdf"


@pytest.mark.parametrize("operation", [scp.defaults, scp.hypothetical_defaults, scp.account_fields])
def test_unknown_plan_cannot_create_account_controls(operation):
    with pytest.raises(ValueError, match="R or SGS"):
        operation("MGS")
