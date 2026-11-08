"""REC must not turn known components or assumed tax factors into executable bills."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.billing import rappahannock_va
from src.billing.rappahannock_va_rates import BLOCKED_REASON, COVERAGE, rates_for_month


def cycle(month):
    start = pd.Timestamp(month, tz="America/New_York")
    return pd.date_range(start, start+pd.offsets.MonthBegin(), inclusive="left", freq="15min")


def confirmed(plan, month):
    account = rappahannock_va.hypothetical_defaults(plan, day=month)
    account.update(dict.fromkeys(rappahannock_va.CONFIRMATIONS, True))
    account.update(der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
                   der_eligibility_source="Hypothetical approval cannot supply missing filed rates")
    return account


@pytest.mark.parametrize("plan", ("A-1", "B-1"))
@pytest.mark.parametrize("month", [f"{year}-{month:02}-01" for year in (2025, 2026) for month in range(1, 13)])
def test_every_requested_month_rejects_missing_approved_full_stack(plan, month):
    account, index = confirmed(plan, month), cycle(month)
    with pytest.raises(ValueError, match="complete billing is unverified"):
        rates_for_month(month[:7], plan)
    with pytest.raises(ValueError, match="complete billing is unverified"):
        rappahannock_va.validate_account(account, index, dict(pv=True, battery=True,
            renewable_only_charging=True, no_battery_export=True))
    with pytest.raises(ValueError, match="complete billing is unverified"):
        rappahannock_va.charge_lines(index, np.zeros(len(index)), np.zeros(len(index)), account, math=None)


def test_catalog_does_not_advertise_supply_history_as_complete_billing():
    rows = rappahannock_va.catalog()
    assert {r["id"] for r in rows} == {"A-1", "B-1"} and COVERAGE == ()
    for row in rows:
        assert row["status"] == "unsupported"
        assert row["billing_supported"] is row["dispatch_supported"] is False
        assert row["coverage"] == row["equipment_modes"] == row["solar_modes"] == []
        assert row["coverage_gaps"][0]["start"] == "2025-01-01"
        assert row["coverage_gaps"][0]["end"] == "2026-12-31"
        assert row["reason"] == BLOCKED_REASON


def test_zero_tax_assumptions_and_confirmations_cannot_enable_pricing():
    account = confirmed("A-1", "2026-11-01")
    account.update(pca=.03426, federal_power_tax_reduction=0., provisional_assumptions_accepted=True,
                   rate_evidence_mode="provisional", subtotal_scope_confirmed=True)
    with pytest.raises(ValueError, match="complete billing is unverified"):
        rappahannock_va.validate_account(account, cycle("2026-11-01"))
    assert rappahannock_va.defaults()["der_ordinary_service_confirmed"] is False
    assert rappahannock_va.hypothetical_defaults()["der_ordinary_service_confirmed"] is False


@pytest.mark.parametrize("bad", [{"supply": "competitive"}, {"export_mode": "net_metering"}, {"tariff": "GSM"}])
def test_unsupported_supplier_export_and_plan_reject(bad):
    account = confirmed("B-1", "2026-10-01")
    with pytest.raises(ValueError, match="A-1/B-1 bundled"):
        rappahannock_va.validate_account({**account, **bad}, cycle("2026-10-01"))


def test_calendar_and_dst_validation_does_not_bypass_source_gap():
    for month, hours in (("2025-03-01", 743), ("2026-11-01", 721)):
        index, account = cycle(month), confirmed("A-1", month)
        assert len(index)/4 == hours
        with pytest.raises(ValueError, match="complete billing is unverified"):
            rappahannock_va.cycle_review(account, index)
        for malformed in (index.delete(100), index.insert(100, index[100]), index.tz_convert("UTC")):
            with pytest.raises(ValueError, match="consecutive"):
                rappahannock_va.cycle_review(account, malformed)


def test_ledger_keeps_tax_gap_and_nonexecutable_components_explicit():
    ledger = json.loads(Path("docs/utility_sources/rappahannock_va/sources.json").read_text())
    assert ledger["executable_coverage"] == []
    assert ledger["billing_status"] == "blocked_unverified_tax_intersections"
    assert ledger["component_observations_not_executable_bills"]["pca_from_may2026"] == ".03426"
    assert "checkbox" in ledger["independent_review"]["finding"]
    for source in ledger["sources"]:
        import hashlib
        assert hashlib.sha256(Path(source["original_path"]).read_bytes()).hexdigest() == source["sha256"]
