"""Explicit ComEd meter cycles, separate from calendar-date rate selection.

GTC sheet197 defines the named billing month by the utility cycle schedule,
not by the service start date. Missing intervals are never a shortened bill.
"""
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd

TIMEZONE = "America/Chicago"
FIXED = {"customer", "standard_metering", "low_income_discount_recovery"}
DEMAND = {"distribution_demand", "transformer_demand"}


@dataclass(frozen=True)
class ComEdBillingCycle:
    start_date: date  # first service day, after the previous meter read
    end_date: date    # final service day, includes the current read day
    billing_month: date
    kind: str = "regular"
    source: str = ""
    charge_factors: dict | None = None

    def validate(self):
        if (any(type(v) is not date for v in (self.start_date, self.end_date, self.billing_month))
                or self.billing_month.day != 1):
            raise ValueError("Cycle dates must be calendar dates; billing_month must be its first day.")
        days = (self.end_date-self.start_date).days+1
        if not 1 <= days <= 45:
            raise ValueError("A ComEd cycle must contain 1–45 whole service days.")
        if abs((self.end_date-self.billing_month).days) > 45:
            raise ValueError("Billing month designation is inconsistent with the meter-cycle dates.")
        if self.kind not in ("regular", "short_service") or not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("Document the utility cycle designation or a labeled hypothetical cycle.")
        if self.kind == "regular":
            if days < 20 or self.charge_factors is not None:
                raise ValueError("A regular study cycle requires >=20 days and no invented charge proration; choose documented short_service for a shorter bill.")
        elif (not isinstance(self.charge_factors, dict) or not self.charge_factors
              or any(k not in FIXED | DEMAND | {"capacity"} for k in self.charge_factors)
              or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v)
                     or not 0 <= v <= 1 for v in self.charge_factors.values())):
            raise ValueError("Short-service bills require documented per-charge factors in [0,1]; no universal days/30 rule is assumed.")
        return self

    def factor(self, name):
        if self.kind == "regular" or name not in FIXED | DEMAND | {"capacity"}:
            return Decimal(1)
        if name not in self.charge_factors:
            raise ValueError("Document short-service allocation for charge: " + name)
        return Decimal(str(self.charge_factors[name]))

    def public(self):
        return {"start_date": self.start_date.isoformat(), "end_date": self.end_date.isoformat(),
                "billing_month": self.billing_month.isoformat(), "kind": self.kind,
                "source": self.source, "charge_factors": self.charge_factors,
                "billing_days": (self.end_date-self.start_date).days+1,
                "applicability_basis": "utility_billing_month", "rules_pdf_pages": [24, 27, 174, 178, 257, 258]}


def cycle_grid(index, cycle):
    cycle.validate()
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None or len(index) < 2:
        raise ValueError("Supply complete timezone-aware meter-cycle intervals.")
    utc = index.tz_convert("UTC")
    step = utc[1]-utc[0]
    if step not in tuple(pd.Timedelta(minutes=m) for m in (15, 30, 60)):
        raise ValueError("Supported meter intervals are 15, 30 or 60 minutes.")
    start = pd.Timestamp(cycle.start_date, tz=TIMEZONE)
    end = pd.Timestamp(cycle.end_date, tz=TIMEZONE)+pd.DateOffset(days=1)
    expected = pd.date_range(start, end, freq=step, inclusive="left").tz_convert("UTC")
    if not utc.equals(expected):
        raise ValueError("Meter-cycle data must cover every physical interval exactly once; missing data are not a partial bill.")
    return utc, Decimal(str(step.total_seconds()))/Decimal(3600)


def partitions(index, account, cycles, prices=None):
    """Validate exact consecutive cycle coverage and preserve price provenance."""
    from .comed_residential import ComEdHourlyPrices, _numeric_series
    if not isinstance(cycles, (list, tuple)) or not 1 <= len(cycles) <= 12:
        raise ValueError("Supply 1–12 explicit, consecutive utility billing cycles.")
    utc = index.tz_convert("UTC")
    if prices is not None:
        _numeric_series(prices.values, utc.floor("h").unique(), "hourly prices", nonnegative=False)
    consumed = 0; months = set()
    for cycle in cycles:
        cycle.validate()
        if cycle.billing_month in months:
            raise ValueError("Duplicate utility billing month; short-service split bills need a separate contract.")
        months.add(cycle.billing_month)
        start = pd.Timestamp(cycle.start_date, tz=TIMEZONE).tz_convert("UTC")
        end = (pd.Timestamp(cycle.end_date, tz=TIMEZONE)+pd.DateOffset(days=1)).tz_convert("UTC")
        positions = np.flatnonzero((utc >= start)&(utc < end))
        if not len(positions) or positions[0] != consumed:
            raise ValueError("Billing cycles must be ordered without overlaps or uncovered intervals.")
        block = slice(consumed, int(positions[-1])+1)
        cycle_grid(index[block], cycle)
        local_prices = None
        if prices is not None:
            series = prices.values.copy(); series.index = series.index.tz_convert("UTC")
            local_prices = ComEdHourlyPrices(series.reindex(utc[block].floor("h").unique()),
                prices.source, prices.zone, prices.price_basis, prices.unit, prices.timestamp_convention)
        yield block, replace(account, billing_month=cycle.billing_month), cycle, local_prices
        consumed = block.stop
    if consumed != len(index):
        raise ValueError("Billing cycles leave study intervals uncovered.")


def parse_cycles(values):
    if values is None:
        return None
    if not isinstance(values, list):
        raise ValueError("billing_cycles must be an explicit list.")
    fields = {"start_date", "end_date", "billing_month", "kind", "source", "charge_factors"}
    out = []
    for value in values:
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError("Supply exactly the documented billing-cycle fields.")
        try:
            out.append(ComEdBillingCycle(**{**value, **{k: date.fromisoformat(value[k])
                       for k in ("start_date", "end_date", "billing_month")}}).validate())
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid documented ComEd billing cycle: " + str(exc)) from exc
    return out
