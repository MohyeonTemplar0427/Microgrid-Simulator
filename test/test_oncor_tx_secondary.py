"""Sheet 1.3 delivery factors and independent REP/Decimal comparisons."""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import pytest

from src.billing.oncor_tx_secondary import secondary_rate_sheet, secondary_rates


@pytest.mark.parametrize("on, determinant, name, before, after", [
    ("2025-02-24", "per_ratchet_kw", "rate_case_expense", ".012192", "0"),
    ("2025-03-01", "per_kwh", "energy_efficiency_cost_recovery", ".000407", ".000223"),
    ("2025-03-01", "per_ncp_kw", "transmission_cost_recovery", "4.959012", "4.675281"),
    ("2025-05-10", "per_ratchet_kw", "distribution_cost_recovery", ".819305", "1.036859"),
    ("2025-09-01", "per_ncp_kw", "transmission_cost_recovery", "4.675281", "5.114972"),
    ("2025-12-01", "per_ratchet_kw", "mobile_generation", "0", ".156662"),
    ("2025-12-15", "per_ratchet_kw", "nuclear_decommissioning", ".045", "0"),
    ("2026-01-01", "per_ratchet_kw", "mobile_generation", ".156662", "0"),
    ("2026-03-01", "per_kwh", "energy_efficiency_cost_recovery", ".000223", ".000546"),
    ("2026-06-01", "monthly", "customer_charge", "11.13", "24.00"),
    ("2026-06-01", "monthly", "metering_charge", "21.30", "20.99"),
    ("2026-06-01", "per_ncp_kw", "distribution_system_charge", "5.121040", "6.931363"),
    ("2026-06-01", "per_ratchet_kw", "rate_case_expense", "0", ".016827"),
    ("2026-06-01", "per_ratchet_kw", "distribution_cost_recovery", "1.036859", "0"),
    ("2026-08-01", "per_ncp_kw", "transmission_cost_recovery", "5.114972", "5.022675"),
    ("2026-08-01", "per_ncp_kw", "interim_surcharge", "0", ".997891"),
    ("2026-10-04", "per_ncp_kw", "transmission_cost_recovery", "5.022675", "4.606104"),
    ("2026-10-04", "per_ratchet_kw", "distribution_cost_recovery", "0", "1.068522"),
])
def test_tariff_sheet_boundaries(on, determinant, name, before, after):
    day = date.fromisoformat(on)
    assert getattr(secondary_rate_sheet(day - timedelta(days=1)), determinant)[name] == Decimal(before)
    assert getattr(secondary_rate_sheet(day), determinant)[name] == Decimal(after)


@pytest.mark.parametrize("start, fixed, energy, demand", [
    ("2025-09-01", "32.43", ".000223", "11.317871"),  # TXU, updated September 19
    ("2026-04-01", "32.43", ".000546", "11.272871"),  # TXU, updated April 11
    ("2026-10-01", "44.99", ".000546", "13.620707"),  # Frontier, November 13, same filed factors
])
def test_independent_retailer_delivery_tables(start, fixed, energy, demand):
    first = date.fromisoformat(start)
    end = first.replace(day=monthrange(first.year, first.month)[1])
    rate = secondary_rates(first, end, bill_date=end)
    assert sum(rate.monthly.values()) == Decimal(fixed)
    assert sum(rate.per_kwh.values()) == Decimal(energy)
    # The comparison tables aggregate demand factors assuming equal billing kW.
    assert sum(rate.per_ncp_kw.values()) + sum(rate.per_ratchet_kw.values()) == Decimal(demand)


@pytest.mark.parametrize("start, expected", [
    ("2025-09-01", "172.90"), ("2026-06-01", "190.64"),
    ("2026-09-01", "201.50"), ("2026-10-01", "213.60"),
])
def test_ratcheted_decimal_delivery_benchmarks(start, expected):
    first = date.fromisoformat(start)
    end = first.replace(day=monthrange(first.year, first.month)[1])
    rate = secondary_rates(first, end, bill_date=end)
    # 1,500 kWh and 12 kW current peak. An actual 20 kW prior peak makes
    # the rider billing demand 16 kW, leaving distribution and TCRF at 12.
    charges = [*rate.monthly.values(), *(1500 * v for v in rate.per_kwh.values()),
               *(12 * v for v in rate.per_ncp_kw.values()), *(16 * v for v in rate.per_ratchet_kw.values())]
    assert sum(v.quantize(Decimal(".01"), rounding=ROUND_HALF_UP) for v in charges) == Decimal(expected)


@pytest.mark.parametrize("start", [date(2025, 2, 1), date(2025, 5, 1), date(2026, 10, 1)])
def test_bill_rendering_date_on_rider_change(start):
    end = start.replace(day=monthrange(start.year, start.month)[1])
    with pytest.raises(ValueError, match="documented delivery bill date"):
        secondary_rates(start, end)
    assert secondary_rates(start, end, bill_date=end) == secondary_rate_sheet(end)


@pytest.mark.parametrize("start, error", [
    (date(2024, 12, 1), "outside verified"), (date(2025, 12, 1), "mid-cycle"),
    (date(2026, 11, 1), "outside verified"), (date(2026, 12, 1), "outside verified"),
])
def test_unverified_cycles_rejected(start, error):
    end = start.replace(day=monthrange(start.year, start.month)[1])
    with pytest.raises(ValueError, match=error):
        secondary_rates(start, end, bill_date=end)
