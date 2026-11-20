"""Source benchmarks from NIMPA's August 2025 comparison, independent of tariff constants."""
from decimal import Decimal as D, ROUND_HALF_UP
import json
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import naperville_il as utility
from src.billing.regional import calculate_cycle
from src.billing.regional_math import BillingMath

INDEX = pd.date_range("2025-08-01", "2025-09-01", freq="15min", tz="America/Chicago", inclusive="left")
SOURCE = Path(__file__).resolve().parents[1]/"docs/utility_sources/naperville_il/sources.json"


def independent(plan, quantity):
    kwh = D(str(quantity))
    monthly, energy = (D("19.26"), D(".11433")) if plan == "FRS" else (D("37.71"), D(".11475"))
    ppa = kwh*D(".00535")
    subtotal = monthly+kwh*energy+ppa
    return dict(customer=monthly, bundled_energy=kwh*energy, purchased_power_adjustment=ppa,
                municipal_use_tax=subtotal/20, illinois_utility_tax=min(kwh*D(".0032"), subtotal/20))


@pytest.mark.parametrize("plan", ["FRS", "FGS"])
@pytest.mark.parametrize("kwh", [0, 100, 500, 1000])
def test_city_and_municipal_agency_published_bills(plan, kwh):
    target = D(str(json.loads(SOURCE.read_text())["survey"]["benchmark_usd"][plan][str(kwh)]))
    expected = independent(plan, kwh)
    assert sum(expected.values()).quantize(D(".01"), ROUND_HALF_UP) == target
    a = utility.hypothetical_defaults(plan)
    power = np.full(len(INDEX), kwh/(len(INDEX)*.25))
    bill = calculate_cycle(utility.UTILITY, INDEX, power, np.zeros_like(power), a)
    assert bill["unrounded_lines"] == pytest.approx({k: float(v) for k,v in expected.items()})
    assert abs(bill["total_usd"]-float(target)) <= .011
    assert bill["is_complete_bill"] and not bill["excluded_components"]
    symbolic = utility.charge_lines(INDEX, cp.Constant(power), cp.Constant(np.zeros_like(power)), a,
                                    math=BillingMath(INDEX, convex=True, power_bound=20., constraints=[]))
    assert {k: float(getattr(v, "value", v)) for k,v in symbolic["lines"].items()} == pytest.approx(bill["unrounded_lines"])


@pytest.mark.parametrize("date", ["2025-07-01", "2025-09-01", "2026-01-01", "2026-08-01", "2026-12-01"])
def test_missing_dated_ppa_blocks_both_classes(date):
    for plan in utility.PLANS:
        with pytest.raises(ValueError, match="monthly Naperville"):
            utility.rates_for_month(date, plan)


@pytest.mark.parametrize("changes", [
    {"gs_prior_peak_kw": 50}, {"gs_prior_peak_kw": float("nan")}, {"gs_review_year": 2024},
    {"gs_assignment_source": ""}, {"opening_credit_kwh": 1}, {"tax_status_confirmed": False},
    {"locality": "outside_city"}, {"export_mode": "net_metering"}, {"bill_date": "2025-09-01"},
])
def test_account_and_billing_clock(changes):
    a = {**utility.hypothetical_defaults("FGS"), **changes}
    with pytest.raises(ValueError):
        utility.validate_account(a, INDEX)


def test_missing_interval_storage_and_unsupported_solar_approval():
    a = utility.hypothetical_defaults()
    for grid in (INDEX.delete(6), INDEX.tz_convert("America/New_York"), INDEX[1:]):
        with pytest.raises(ValueError):
            utility.validate_account(a, grid)
    for eq in ({"battery": True}, {"pv": True, "pv_ac_kw": 10.01}):
        with pytest.raises(ValueError):
            utility.validate_account(a, INDEX, eq)
    with pytest.raises(ValueError):
        utility.validate_account({**a, "der_activation_date": "2025-08-02"}, INDEX, {"pv": True, "pv_ac_kw": 2.})
    with pytest.raises(ValueError):
        calculate_cycle(utility.UTILITY, INDEX, np.zeros(len(INDEX)), np.ones(len(INDEX)), a)
