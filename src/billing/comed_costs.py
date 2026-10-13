"""Compile filed costs from authoritative ComEd bill lines, without new rates.

Dispatch uses the same line rates before final cent rounding. The declared
rounding bound accounts for independently rounded variable bill components.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .comed_residential import calculate_comed_residential_bill, ComEdResidentialAccount
from .comed_commercial import calculate_comed_commercial_bill, mkd_mask
from . import comed_rates

FIXED = {"customer", "standard_metering", "capacity", "low_income_discount_recovery"}
DEMAND = {"distribution_demand", "transformer_demand"}


def calculate(imports, account, prices=None):
    function = (calculate_comed_residential_bill if isinstance(account, ComEdResidentialAccount)
                else calculate_comed_commercial_bill)
    return function(imports, account, hourly_prices=prices)


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


def compile_costs(index, account, prices=None):
    zero = calculate(pd.Series(0., index=index), account, prices)
    marginal = np.zeros(len(index))
    fixed = demand = 0.
    variable_lines = 0
    for line in zero["lines"]:
        name = line["name"]
        if name in FIXED:
            fixed += line["amount_usd"]
        elif name in DEMAND:
            demand += line["rate_usd"]
            variable_lines += 1
        elif name == "hourly_electricity_supply":
            # The zero-import authoritative bill has already validated the
            # price basis, exact hourly coverage, units and source metadata.
            hours = index.tz_convert("UTC").floor("h")
            values = prices.values.copy()
            values.index = values.index.tz_convert("UTC")
            marginal += values.reindex(hours).to_numpy(dtype=float)/1000*float(comed_rates.HEC_MULTIPLIER)
            variable_lines += 1
        else:
            if line["rate_usd"] is None or line["quantity"] != 0:
                raise ValueError("Unclassified ComEd charge; refusing to omit it from dispatch.")
            marginal += line["rate_usd"]
            variable_lines += 1
    return ComEdCosts(index, (index[1]-index[0]).total_seconds()/3600,
                      marginal, fixed, demand, variable_lines*.005 + 1e-7)
