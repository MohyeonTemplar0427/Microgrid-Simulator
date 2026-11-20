"""Choptank source arithmetic and rejection through every billing entry point."""

import json
from decimal import Decimal
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import choptank_md as choptank
from src.billing.choptank_md_rates import BLOCKED_REASON, C, COVERAGE, PLANS, R, S, rates_for_month, rates_on
from src.billing.regional_math import BillingMath

LEDGER = Path(__file__).resolve().parents[1] / "docs/utility_sources/choptank_md/sources.json"


def month_intervals(day):
    start = pd.Timestamp(day, tz=choptank.TIMEZONE)
    return pd.date_range(start, start + pd.offsets.MonthBegin(), freq="15min", inclusive="left")


@pytest.mark.parametrize("plan", [R, C, S])
def test_all_2025_and_2026_months_reject_with_valid_cycles_and_account_claims(plan):
    for month in pd.date_range("2025-01-01", "2026-12-01", freq="MS"):
        day = str(month.date())
        index = month_intervals(day)
        account = choptank.hypothetical_defaults(plan, day=day)
        account.update(full_monthly_charges_confirmed=True, eligibility_confirmed=True,
                       der_ordinary_service_confirmed=True, der_eligibility_source="Example",
                       account_source="Example", cycle_source="Example", pca=.02994,
                       environmental_surcharge=.00015, subtotal_scope_confirmed=True)
        for check in (lambda: rates_for_month(day, plan), lambda: rates_on(index[-1], plan),
                      lambda: choptank.cycle_review(account, index),
                      lambda: choptank.validate_account(account, index)):
            with pytest.raises(ValueError, match="utility-specific environmental surcharge"):
                check()


def test_catalog_and_account_defaults_advertise_observed_schedules_only():
    assert COVERAGE == ()
    assert set(PLANS) == {R, C, S}
    rows = choptank.catalog()
    assert {p["id"]: p["customer_class"] for p in rows} == {R: "residential", C: "commercial", S: "commercial"}
    assert "902 Schedule C" in PLANS[C] and "Small Power" in PLANS[S]
    for row in rows:
        assert row["reason"] == BLOCKED_REASON and row["status"] == "unsupported"
        assert row["coverage"] == row["equipment_modes"] == row["solar_modes"] == []
        assert row["billing_supported"] is row["dispatch_supported"] is False
        assert row["coverage_gaps"][0]["start"] == "2025-01-01"
        assert row["coverage_gaps"][-1]["end"] == "2026-12-31"
        assert row["supply_arrangements"] == ["sos"]
        for account in (choptank.defaults(row["id"]), choptank.hypothetical_defaults(row["id"])):
            assert account["export_mode"] == "none"
            assert account["full_monthly_charges_confirmed"] is account["der_ordinary_service_confirmed"] is False


@pytest.mark.parametrize("day,hours", [("2025-03-01", 743), ("2025-11-01", 721),
                                       ("2026-03-01", 743), ("2026-11-01", 721)])
def test_calendar_requires_eastern_dst_complete_cycle_and_final_day_bill(day, hours):
    index = month_intervals(day)
    assert len(index) == hours * 4
    account = choptank.hypothetical_defaults(R, day=day)
    account["full_monthly_charges_confirmed"] = True
    for invalid in (index.delete(100), index.insert(100, index[100]), index[::2], index.tz_convert("UTC")):
        with pytest.raises(ValueError, match="consecutive 15-minute"):
            choptank.cycle_review(account, invalid)
    with pytest.raises(ValueError, match="complete calendar"):
        choptank.cycle_review(account, index[:-1])
    with pytest.raises(ValueError, match="matching service"):
        choptank.cycle_review({**account, "bill_date": day}, index)


@pytest.mark.parametrize("change", [{"tariff": "RS"}, {"tariff": "M"}, {"supply": "third_party"},
                                    {"supply": "ODEC"}, {"export_mode": "nem"}])
def test_unverified_supply_and_settlement_reject(change):
    with pytest.raises(ValueError, match="cooperative SOS and zero export"):
        choptank.validate_account({**choptank.defaults(R), **change}, month_intervals("2026-07-01"))


def test_no_numeric_or_optimizer_path_can_substitute_a_factor():
    index = month_intervals("2026-07-01")
    account = choptank.hypothetical_defaults(C, day="2026-07-01")
    account.update(environmental_surcharge=0, environmental_surcharge_confirmed=True,
                   provisional_assumptions_accepted=True, opening_credit_usd=5)
    zero = np.zeros(len(index))
    for imports, math in ((zero, BillingMath(index)),
                          (cp.Variable(len(index), nonneg=True), BillingMath(index, convex=True, power_bound=20))):
        with pytest.raises(ValueError, match="utility-specific environmental surcharge"):
            choptank.charge_lines(index, imports, zero, account, math=math)
        assert math.constraints == []
    for check in (lambda: choptank.validate_state(account, index, {"credit": 5}),
                  lambda: choptank.validate_native_load(account, zero)):
        with pytest.raises(ValueError, match="utility-specific environmental surcharge"):
            check()


def test_preserved_receipts_reconcile_literal_component_benchmarks_only():
    evidence = json.loads(LEDGER.read_text())
    assert evidence["billing_status"] == "blocked_missing_complete_dated_component_intersections"
    assert evidence["executable_coverage"] == []
    env = evidence["environmental_surcharge"]
    assert env["assigned_numeric_values"] == {} and not env["substitution_from_cap_or_other_utility"]
    assert [n["fiscal_year"] for n in env["notices"]] == ["FY2025", "FY2026", "FY2027"]
    assert evidence["pricing_node"] is None and not evidence["retail_wholesale_lmp_used"]
    for source in evidence["sources"]:
        assert source["url"].startswith("https://") and source["bytes"] > 0
        assert len(source["sha256"]) == 64 and int(source["sha256"], 16) > 0

    base = evidence["base_observations"]
    charges = evidence["shared_charges_observed"]
    info25, info26 = evidence["supply_observations"]
    pca26 = Decimal(info26["published_pca_per_kwh"])
    generation = Decimal(base[R]["sos_supply_capacity_energy_per_kwh"])
    transmission = Decimal(base[R]["sos_transmission_per_kwh"])
    assert Decimal(info25["published_residential_price_to_compare_per_kwh"]) - generation - transmission == Decimal("0.02449")
    assert generation + transmission + pca26 == Decimal(info26["published_residential_price_to_compare_per_kwh"])
    assert generation + transmission + pca26 == Decimal("0.10442")

    for plan, expected in [(R, "180.62"), (C, "187.07"), (S, "249.20")]:
        # 1,000 kWh; independent $1.85 commercial USP assignment. For S the
        # fixture stipulates 10 billed kW for each demand line and 0 billed RKVAh.
        schedule = base[plan]
        usp = "residential_usp_usd_per_month" if plan == R else "commercial_usp_example_usd_per_month"
        subtotal = Decimal(schedule["customer_usd"]) + Decimal(charges[usp])
        energy_rates = [Decimal(v) for k, v in schedule.items() if k.endswith("_per_kwh")]
        subtotal += 1000 * (sum(energy_rates) + pca26 + Decimal(charges["franchise_usd_per_kwh"]))
        subtotal += 10 * sum(Decimal(v) for k, v in schedule.items() if k.endswith("_per_kw"))
        assert subtotal == Decimal(expected)
