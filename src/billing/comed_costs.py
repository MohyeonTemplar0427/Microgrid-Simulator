"""Compile filed costs from authoritative ComEd bill lines, without new rates.

Dispatch uses the same line rates before final cent rounding. The declared
rounding bound accounts for independently rounded variable bill components.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .comed_residential import calculate_comed_residential_bill, ComEdResidentialAccount
from .comed_commercial import calculate_comed_commercial_bill, mkd_mask

FIXED = {"customer", "standard_metering", "capacity", "low_income_discount_recovery"}
DEMAND = {"distribution_demand", "transformer_demand"}


def calculate(imports, account, prices=None, billing_cycles=None):
    function = (calculate_comed_residential_bill if isinstance(account, ComEdResidentialAccount)
                else calculate_comed_commercial_bill)
    if billing_cycles is None:
        return function(imports, account, hourly_prices=prices)
    from .comed_cycles import partitions
    bills = [function(imports.iloc[block], a, hourly_prices=p, billing_cycle=c)
             for block, a, c, p in partitions(imports.index, account, billing_cycles, prices)]
    from decimal import Decimal
    lines = [{**line, "cycle_index": i, "billing_month": bill["billing_month"],
              "version_id": bill["version_id"]} for i, bill in enumerate(bills) for line in bill["lines"]]
    return {"plan_id": bills[0]["plan_id"], "version_id": [b["version_id"] for b in bills],
            "billing_month": [b["billing_month"] for b in bills], "timezone": "America/Chicago",
            "cycles": bills, "lines": lines,
            "import_kwh": sum(b["import_kwh"] for b in bills),
            "subtotal_usd": float(sum((Decimal(str(b["subtotal_usd"])) for b in bills), Decimal(0))),
            "overall_30min_peak_kw": max((b.get("overall_30min_peak_kw", 0) for b in bills)),
            "billed_mkd_kw": max((b.get("billed_mkd_kw", 0) for b in bills)),
            "total_usd": None, "is_complete_bill": False,
            "excluded_components": bills[0]["excluded_components"],
            "source": {"applicability_basis": "explicit_utility_billing_cycles",
                       "rate_sources": [b["source"] for b in bills]}}


@dataclass(frozen=True)
class ComEdCosts:
    index: pd.DatetimeIndex
    hours: float
    marginal_per_kwh: np.ndarray
    fixed_usd: float
    demand_per_kw: float
    rounding_bound_usd: float

    def half_hour_power(self, power):
        ratio = int(round(.5 / self.hours))
        if ratio < 1:
            return power  # Residential hourly data carry no demand charges.
        if isinstance(power, np.ndarray):
            return power.reshape(-1, ratio).mean(axis=1)
        import cvxpy as cp
        return cp.sum(cp.reshape(power, (len(self.index)//ratio, ratio), order="C"), axis=1)/ratio

    def billed_peak(self, power):
        if not self.demand_per_kw:
            return 0.
        mask = mkd_mask(self.index[::int(round(.5/self.hours))])
        if not mask.any():
            return 0.
        half = self.half_hour_power(power)
        if isinstance(power, np.ndarray):
            return float(half[mask].max())
        import cvxpy as cp
        return cp.max(half[mask])

    def subtotal(self, power):
        if isinstance(power, np.ndarray):
            energy = float(np.dot(power, self.marginal_per_kwh))*self.hours
        else:
            import cvxpy as cp
            energy = cp.sum(cp.multiply(power, self.marginal_per_kwh))*self.hours
        return self.fixed_usd + energy + self.demand_per_kw*self.billed_peak(power)


def compile_costs(index, account, prices=None, billing_cycles=None):
    if billing_cycles is not None:
        from .comed_cycles import partitions
        blocks = []
        for block, a, cycle, p in partitions(index, account, billing_cycles, prices):
            blocks.append((block, _compile(index[block], a, p, cycle)))
        return ComEdCycleCosts(index, blocks)
    return _compile(index, account, prices)


@dataclass(frozen=True)
class ComEdCycleCosts:
    index: pd.DatetimeIndex
    blocks: list

    @property
    def hours(self):
        return self.blocks[0][1].hours

    @property
    def rounding_bound_usd(self):
        return sum(c.rounding_bound_usd for _, c in self.blocks)

    def subtotal(self, power):
        return sum(c.subtotal(power[block]) for block, c in self.blocks)


def _compile(index, account, prices=None, billing_cycle=None):
    function = (calculate_comed_residential_bill if isinstance(account, ComEdResidentialAccount)
                else calculate_comed_commercial_bill)
    zero = function(pd.Series(0., index=index), account, hourly_prices=prices, billing_cycle=billing_cycle)
    marginal = np.zeros(len(index))
    fixed = demand = 0.
    variable_lines = 0
    for line in zero["lines"]:
        name = line["name"]
        if name in FIXED:
            fixed += line["amount_usd"]
        elif name in DEMAND:
            demand += line["rate_usd"]*line.get("billing_multiplier", 1.)
            variable_lines += 1
        elif name == "hourly_electricity_supply":
            # The zero-import authoritative bill has already validated the
            # price basis, exact hourly coverage, units and source metadata.
            hours = index.tz_convert("UTC").floor("h")
            values = prices.values.copy()
            values.index = values.index.tz_convert("UTC")
            marginal += values.reindex(hours).to_numpy(dtype=float)/1000*zero["source"]["hourly_energy_multiplier"]
            variable_lines += 1
        else:
            if line["rate_usd"] is None or line["quantity"] != 0:
                raise ValueError("Unclassified ComEd charge; refusing to omit it from dispatch.")
            marginal += line["rate_usd"]
            variable_lines += 1
    return ComEdCosts(index, (index[1]-index[0]).total_seconds()/3600,
                      marginal, fixed, demand, variable_lines*.005 + 1e-7)
