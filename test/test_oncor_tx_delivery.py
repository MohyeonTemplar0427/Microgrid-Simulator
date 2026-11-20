"""Oncor published-rate and independent REP checks, without supply or tax."""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.billing.oncor_tx_delivery import delivery_rate_sheet, delivery_rates


@pytest.mark.parametrize("on, res_kwh, secondary_kwh", [
    ("2025-01-01", ".052974", ".044705"), ("2025-02-24", ".052920", ".044650"),
    ("2025-03-01", ".050029", ".044602"), ("2025-05-10", ".051248", ".046202"),
    ("2025-09-01", ".056032", ".045753"), ("2025-12-01", ".057059", ".046359"),
    ("2025-12-15", ".056860", ".046229"), ("2026-01-01", ".055833", ".045623"),
    ("2026-03-01", ".056183", ".045874"), ("2026-06-01", ".061196", ".049532"),
    ("2026-08-01", ".060295", ".051227"), ("2026-10-04", ".068673", ".053843"),
])
def test_dated_factor_totals_and_fixed_charges(on, res_kwh, secondary_kwh):
    day = date.fromisoformat(on)
    for schedule, expected in (("residential", res_kwh), ("secondary_le_10_kw", secondary_kwh)):
        rates = delivery_rate_sheet(schedule, day)
        assert sum(rates.per_kwh.values()) == Decimal(expected)
        legacy, new = ("4.23", "4.06") if schedule == "residential" else ("6.87", "6.70")
        assert sum(rates.monthly.values()) == Decimal(legacy if day < date(2026, 6, 1) else new)
        assert all(source.startswith("https://") for source in rates.sources)
        if day > date(2025, 1, 1):
            assert delivery_rate_sheet(schedule, day - timedelta(days=1)).per_kwh != rates.per_kwh


@pytest.mark.parametrize("year, month", [(2025, 2), (2025, 5), (2026, 10)])
def test_documented_final_day_bill_uses_new_factor_for_entire_cycle(year, month):
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    with pytest.raises(ValueError, match="documented delivery bill date"):
        delivery_rates("residential", start, end)
    assert delivery_rates("residential", start, end, bill_date=end) == delivery_rate_sheet("residential", end)
    with pytest.raises(ValueError, match="final-day"):
        delivery_rates("residential", start, end, bill_date=end + timedelta(days=1))


def test_december_transition_and_unsupported_periods():
    end = date(2025, 12, 31)
    with pytest.raises(ValueError, match="mid-cycle"):
        delivery_rates("secondary_le_10_kw", end.replace(day=1), end, bill_date=end)
    for month in (date(2024, 12, 1), date(2026, 11, 1), date(2026, 12, 1)):
        with pytest.raises(ValueError, match="outside verified"):
            delivery_rates("residential", month, month.replace(day=monthrange(month.year, month.month)[1]))
    with pytest.raises(ValueError, match="complete calendar"):
        delivery_rates("residential", date(2025, 11, 1), date(2025, 11, 29))
    with pytest.raises(ValueError, match="schedule"):
        delivery_rate_sheet("secondary_gt_10_kw", date(2025, 3, 1))


def test_december_only_rider_and_negative_efficiency_factor():
    def lookup(on):
        return delivery_rate_sheet("secondary_le_10_kw", date.fromisoformat(on)).per_kwh

    assert lookup("2025-05-31")["energy_efficiency_cost_recovery"] == Decimal("-.000196")
    assert lookup("2025-11-30")["mobile_generation"] == 0
    assert lookup("2025-12-01")["mobile_generation"] == Decimal(".000606")
    assert lookup("2025-12-14")["nuclear_decommissioning"] == Decimal(".000130")
    assert lookup("2025-12-15")["nuclear_decommissioning"] == 0
    assert lookup("2026-01-01")["mobile_generation"] == 0


@pytest.mark.parametrize("schedule, month, benchmark", [
    ("residential", date(2025, 8, 1), "55.48"),  # Oncor, 2025 TDU summary
    ("secondary_le_10_kw", date(2025, 10, 1), "52.62"),  # NEC October EFL
    ("secondary_le_10_kw", date(2026, 9, 1), "57.93"),  # SFE September table
])
def test_published_delivery_only_1000_kwh_benchmarks(schedule, month, benchmark):
    end = month.replace(day=monthrange(month.year, month.month)[1])
    rates = delivery_rates(schedule, month, end)
    delivery = sum(rates.monthly.values()) + 1000 * sum(rates.per_kwh.values())
    assert delivery.quantize(Decimal(".01")) == Decimal(benchmark)
