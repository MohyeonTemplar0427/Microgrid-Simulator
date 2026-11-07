"""SMECO must not turn PTC history or pending factors into executable bills."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.billing import smeco_md
from src.billing.smeco_md_rates import BLOCKED_REASON, COVERAGE, rates_for_month


def cycle(month):
    start = pd.Timestamp(month, tz="America/New_York")
    return pd.date_range(start, start+pd.offsets.MonthBegin(), inclusive="left", freq="15min")


def confirmed(plan, month):
    account = smeco_md.hypothetical_defaults(plan, day=month)
    account.update(dict.fromkeys(smeco_md.CONFIRMATIONS, True))
    account.update(der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
                   der_eligibility_source="Hypothetical approval cannot supply missing filed rates")
    return account


@pytest.mark.parametrize("plan", ("R", "GSS"))
@pytest.mark.parametrize("month", [f"{year}-{month:02}-01" for year in (2025, 2026) for month in range(1, 13)])
def test_every_requested_month_rejects_missing_approved_full_stack(plan, month):
    account, index = confirmed(plan, month), cycle(month)
    with pytest.raises(ValueError, match="billing is unverified"):
        rates_for_month(month[:7], plan)
    with pytest.raises(ValueError, match="billing is unverified"):
        smeco_md.validate_account(account, index, dict(pv=True, battery=True,
            renewable_only_charging=True, no_battery_export=True))
    with pytest.raises(ValueError, match="billing is unverified"):
        smeco_md.charge_lines(index, np.zeros(len(index)), np.zeros(len(index)), account, math=None)


def test_catalog_does_not_advertise_supply_history_as_complete_billing():
    rows = smeco_md.catalog()
    assert {r["id"] for r in rows} == {"R", "GSS"} and COVERAGE == ()
    for row in rows:
        assert row["status"] == "unsupported"
        assert row["billing_supported"] is row["dispatch_supported"] is False
        assert row["coverage"] == row["equipment_modes"] == row["solar_modes"] == []
        assert row["coverage_gaps"][0]["start"] == "2025-01-01"
        assert row["coverage_gaps"][0]["end"] == "2026-12-31"
        assert row["reason"] == BLOCKED_REASON


def test_pending_or_assumed_account_inputs_cannot_enable_pricing():
    account = confirmed("R", "2026-11-01")
    account.update(pca=-.018214, bsa=-.006286, provisional_assumptions_accepted=True,
                   rate_evidence_mode="provisional", subtotal_scope_confirmed=True)
    with pytest.raises(ValueError, match="billing is unverified"):
        smeco_md.validate_account(account, cycle("2026-11-01"))
    assert smeco_md.defaults()["der_ordinary_service_confirmed"] is False
    assert smeco_md.hypothetical_defaults()["der_ordinary_service_confirmed"] is False


@pytest.mark.parametrize("bad", [{"supply": "competitive"}, {"export_mode": "net_metering"}, {"tariff": "GSM"}])
def test_unsupported_supplier_export_and_plan_reject(bad):
    account = confirmed("GSS", "2026-10-01")
    with pytest.raises(ValueError, match="R/GSS SOS"):
        smeco_md.validate_account({**account, **bad}, cycle("2026-10-01"))


def test_calendar_and_dst_validation_does_not_bypass_source_gap():
    for month, hours in (("2025-03-01", 743), ("2026-11-01", 721)):
        index, account = cycle(month), confirmed("R", month)
        assert len(index)/4 == hours
        with pytest.raises(ValueError, match="billing is unverified"):
            smeco_md.cycle_review(account, index)
        for malformed in (index.delete(100), index.insert(100, index[100]), index.tz_convert("UTC")):
            with pytest.raises(ValueError, match="consecutive"):
                smeco_md.cycle_review(account, malformed)


def test_ledger_keeps_pending_status_and_component_scope_explicit():
    ledger = json.loads(Path("docs/utility_sources/smeco_md/sources.json").read_text())
    assert ledger["executable_coverage"] == []
    assert ledger["billing_status"] == "blocked_missing_approved_component_intersections"
    assert ledger["pending_months"] == ["2026-11"]
    assert ledger["ptc_scope"] == "supply_only_base_sos_plus_pca"
    assert ledger["pjm_identity"]["emergency_transmission_zone"] == "SMECO"
    assert ledger["pjm_identity"]["market_forecast_aggregation"] == "PEPCO"
