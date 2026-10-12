"""Bounded bundled GS-2T bills; retail charges never use wholesale LMP.

This initial verified composite window is 2026-09-01..2026-10-11. The
general plan/version contract makes subsequent windows additive, not inferred.
"""
from dataclasses import dataclass
from datetime import date
import math
import numpy as np
import pandas as pd
from .plans import RatePlan, RatePlanIdentity

BASE_URL = "https://www.dominionenergy.com/-/media/content/rates-and-tariffs/pdfs/virginia/"
SOURCE_URLS = [BASE_URL + "large-business/schedule-gs2t.pdf",
               BASE_URL + "shared/exhibit-of-applicable-riders.pdf",
               BASE_URL + "shared/entire-filed-tariff.pdf"]
SOURCE_URLS += [BASE_URL + "shared/rider-" + k + ".pdf" for k in
               ("a", "c1a", "c4a", "cerc", "dist", "e", "gen", "rggi", "smr", "sna", "t1", "ccr", "ce", "osw", "rps", "pipp")]
SOURCE_URLS += ["https://henrico.gov/finance/approved-tax-rates-and-schedule/"]

# Energy rates below are dollars/kWh, demand rates dollars/kW. Conditional
# riders use actual meter load factor, not native building energy or PV output.
ENERGY_RIDERS = {"A": .037648, "C1A": .000335, "C4A": .000967,
                 "CCR": .001765, "RPS": .005520, "RGGI": 0., "PIPP": 0.}
CONDITIONAL_RIDERS = {"CE": (.004480, 1.633), "CERC": (.000574, .208),
                      "E": (.000502, .182), "GEN": (.004375, 1.581),
                      "OSW": (.009231, 3.366), "SMR": (.000130, .046),
                      "SNA": (.003674, 1.322)}


@dataclass(frozen=True)
class GS2TVersion:
    tariff_id: str = "dominion_gs2t_composite_2026_09_01"
    effective_start: date = date(2026, 9, 1)
    effective_end: date = date(2026, 10, 11)

    def is_effective_on(self, day):
        return self.effective_start <= day <= self.effective_end


PLAN = RatePlan(RatePlanIdentity("Dominion Energy Virginia", "GS-2T", "bundled", "commercial"), (GS2TVersion(),))


def validate_account(account):
    required = {"locality", "eligibility_confirmed", "history_peaks_kw", "power_factor",
                "metering_side", "special_riders", "parallel_operation_approved",
                "contract_demand_kw", "minimum_contract_charge", "billing_month", "facility"}
    if not isinstance(account, dict) or set(account) != required:
        raise ValueError("Supply all bounded GS-2T account facts: " + str(sorted(required)))
    if account["locality"] != "henrico" or account["eligibility_confirmed"] is not True or account["facility"] != "commercial_non_datacenter" or account["metering_side"] != "secondary" or account["special_riders"] is not False or account["parallel_operation_approved"] is not True:
        raise ValueError("Confirm ordinary non-data-center commercial GS-2T, Henrico locality, secondary metering, approved parallel operation and no special riders.")
    for key in ("power_factor", "contract_demand_kw", "minimum_contract_charge"):
        if isinstance(account[key], bool) or not isinstance(account[key], (int, float)) or not math.isfinite(account[key]):
            raise ValueError(key + " must be finite.")
    if not .85 <= account["power_factor"] <= 1 or not 30 <= account["contract_demand_kw"] < 500 or account["minimum_contract_charge"] != 0:
        raise ValueError("Candidate requires PF >=85%, contract demand 30–499 kW, and no separate contracted minimum/facilities charge.")
    peaks = account["history_peaks_kw"]
    if not isinstance(peaks, list) or len(peaks) != 11 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0 <= x < 500 for x in peaks):
        raise ValueError("Supply eleven ordered prior billing-cycle measured peaks below 500 kW; no ratchet history is inferred.")
    if sum(x >= 30 for x in peaks) < 3:
        raise ValueError("This existing-account case requires three qualifying >=30 kW demands in the supplied history.")
    if max(peaks) > account["contract_demand_kw"]:
        raise ValueError("Parallel-service contract demand must cover the 12-month distribution ratchet.")
    if type(account["billing_month"]) is not int or not 1 <= account["billing_month"] <= 12:
        raise ValueError("Specify the utility billing month; it is not inferred from interval timestamps.")


def validate_index(index):
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None or str(index.tz) != "America/New_York" or index.empty:
        raise ValueError("GS-2T requires a timezone-aware America/New_York interval grid.")
    if not index.is_unique or not index.is_monotonic_increasing or not (np.diff(index.asi8) == pd.Timedelta(minutes=30).value).all():
        raise ValueError("GS-2T requires complete ordered 30-minute demand intervals; no coarser peak inference.")
    if index[0] != index[0].normalize() or index[-1] + pd.Timedelta(minutes=30) != (index[-1].normalize()+pd.DateOffset(days=1)):
        raise ValueError("Supply complete local service dates for one confirmed billing cycle.")
    days = len(index.normalize().unique())
    if not 1 <= days <= 40:
        raise ValueError("Supply one confirmed billing cycle of 1–40 service days.")
    PLAN.version_on(index[0].date())
    PLAN.version_on(index[-1].date())
    return days


def on_peak(index):
    summer = (index.month >= 6) & (index.month <= 9)
    return (index.dayofweek < 5) & (index.hour >= np.where(summer, 10, 7)) & (index.hour < 22)


def charge_lines(index, grid, account, *, convex=False, tax_band=None):
    """Shared arithmetic; convex calls require a proven low-load-factor scope.

    A constant contract demand covers parallel generation in every comparison.
    No additional PJM capacity PLC/NSPL charge is levied on this bundled plan.
    """
    import cvxpy as cp
    days = validate_index(index)
    validate_account(account)
    total = cp.sum(grid)*.5 if convex else float(np.sum(grid)*.5)
    peak = cp.max(grid) if convex else float(np.max(grid))
    mask = on_peak(index)
    supply_peak = (cp.max(grid[mask]) if convex else float(np.max(grid[mask]))) if mask.any() else 0.
    supply_rate = 4.526 if 6 <= account["billing_month"] <= 9 else 2.215
    factor = days / 30
    distribution = account["contract_demand_kw"]
    low_factor = True if convex else (total <= days*24*peak*.5 + 1e-8)
    energy_rate = np.where(mask, .020278, .009928)
    lines = {"customer": 37.08*factor,
             "distribution_demand": distribution*4.963*factor,
             "distribution_energy": total*.000079,
             "generation_demand": supply_peak*supply_rate*factor,
             "generation_adjustment_demand": 0.,
             "generation_energy": (cp.sum(cp.multiply(grid, energy_rate)) if convex else float(np.dot(grid, energy_rate)))*.5,
             "transmission_demand": supply_peak*2.313*factor,
             "rider_DIST": distribution*1.169*factor,
             "rider_T1": supply_peak*4.554*factor}
    lines.update({"rider_"+k: total*v for k, v in ENERGY_RIDERS.items()})
    lines.update({"rider_"+k: total*rates[0] if low_factor else supply_peak*rates[1]*factor
                  for k, rates in CONDITIONAL_RIDERS.items()})
    if convex:
        # Declining consumption taxes and the capped local tax are affine on
        # each enumerated energy band; never convexify them into wrong rates.
        slopes = (.001565, .001055, .000845)
        offsets = (0., 2500*(.001565-.001055),
                   2500*(.001565-.000845)+47500*(.001055-.000845))
        lines["consumption_tax"] = total*slopes[tax_band] + offsets[tax_band]
        lines["henrico_utility_tax"] = 10.  # Scope proof requires >1,242 kWh.
    else:
        lines["consumption_tax"] = min(total, 2500)*.001565 + min(max(total-2500, 0), 47500)*.001055 + max(total-50000, 0)*.000845
        lines["henrico_utility_tax"] = min(1.15 + total*.00713, 10.)
    return lines


def bill(index, grid, account):
    grid = np.asarray(grid, dtype=float)
    validate_index(index)
    validate_account(account)
    if grid.shape != (len(index),) or not np.isfinite(grid).all() or (grid < -1e-7).any():
        raise ValueError("Provide finite nonnegative meter imports matching the full grid; export is unsupported.")
    grid = np.maximum(grid, 0)
    if grid.max() > account["contract_demand_kw"]+1e-5:
        raise ValueError("Measured import exceeds parallel-service contract demand; an account/ratchet update is required.")
    lines = charge_lines(index, grid, account)
    total = float(grid.sum()*.5)
    return {"total": sum(lines.values()), "lines": lines, "import_kWh": total,
            "peak_kw": float(grid.max()), "on_peak_kw": float(grid[on_peak(index)].max()) if on_peak(index).any() else 0.,
            "distribution_demand_kw": account["contract_demand_kw"],
            "load_factor": total/(len(index.normalize().unique())*24*grid.max()) if grid.max() else 0.,
            "rate_version": PLAN.versions[0].tariff_id}
