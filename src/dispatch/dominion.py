"""GS-2T perfect-foresight non-export storage, with explicit scope proofs."""
import cvxpy as cp
import numpy as np
import pandas as pd
import math
from ..billing.dominion import bill, charge_lines, validate_index, validate_account
from .battery import Battery


def optimize(inputs, account, battery_config, wear=0., include_wear=False):
    if isinstance(wear, bool) or not isinstance(wear, (int, float)) or not math.isfinite(wear) or wear < 0 or type(include_wear) is not bool:
        raise ValueError("Provide a nonnegative wear rate and explicit Boolean objective choice.")
    index = pd.DatetimeIndex(inputs.timestamp)
    days = validate_index(index)
    validate_account(account)
    load, pv = (np.asarray(inputs[k], dtype=float) for k in ("native_load_kw", "pv_available_kw"))
    if not np.isfinite(load).all() or not np.isfinite(pv).all() or (load < 0).any() or (pv < 0).any():
        raise ValueError("Load and PV must be finite, nonnegative AC-side kW.")
    b = Battery(**battery_config)
    n = len(index)
    # Proven bounds for every feasible terminal-neutral AC schedule. These
    # make the tariff's conditional rider regime constant across dispatch,
    # rather than allowing a peak epigraph to fabricate the load factor.
    lower_import = np.maximum(load-pv-b.max_discharge_kw, 0)
    lower_peak = float(lower_import.max())
    lower_energy = float(lower_import.sum()*.5)
    upper_energy = float(load.sum()*.5 + n*.5*b.max_charge_kw*(1-b.charge_efficiency*b.discharge_efficiency))
    if lower_peak <= 0 or upper_energy > .5*days*24*lower_peak:
        raise ValueError("Dispatch could cross the 50% rider load-factor boundary. This candidate rejects that nonconvex regime; no globally optimal savings are claimed.")
    if lower_energy <= (10-1.15)/.00713:
        raise ValueError("Dispatch could cross the Henrico utility-tax cap. This candidate requires a provably capped commercial tax.")
    charge, discharge, grid, output = [cp.Variable(n, nonneg=True) for _ in range(4)]
    energy = cp.Variable(n+1)
    constraints = [charge <= b.max_charge_kw, discharge <= b.max_discharge_kw, output <= pv,
                   grid <= account["contract_demand_kw"], grid+output+discharge == load+charge,
                   energy[0] == b.energy_kWh, energy[-1] == b.energy_kWh,
                   energy >= b.minimum_energy_kWh, energy <= b.maximum_energy_kWh,
                   energy[1:] == energy[:-1]+.5*(charge*b.charge_efficiency-discharge/b.discharge_efficiency)]
    volume = cp.sum(grid)*.5
    degradation = wear*.5*cp.sum(charge+discharge)
    candidates = []
    for band, (lo, hi) in enumerate(((0, 2500), (2500, 50000), (50000, float("inf")))):
        if upper_energy < lo or lower_energy > hi:
            continue
        extra = [volume >= lo] + ([volume <= hi] if np.isfinite(hi) else [])
        lines = charge_lines(index, grid, account, convex=True, tax_band=band)
        expression = sum(lines.values())
        score = expression+(degradation if include_wear else 0)
        problem = cp.Problem(cp.Minimize(score), constraints+extra)
        problem.solve(solver="CLARABEL")
        if problem.status == "infeasible":
            continue
        if problem.status != "optimal":
            raise ValueError("Storage optimization did not converge: "+str(problem.status))
        optimum = float(problem.value)
        tie = cp.Problem(cp.Minimize(cp.sum(charge+discharge)), constraints+extra+[score <= optimum+max(1e-5, abs(optimum)*1e-8)])
        tie.solve(solver="CLARABEL")
        if tie.status != "optimal":
            raise ValueError("Storage tie-break failed.")
        c, d, g, p, e = (np.asarray(v.value).copy() for v in (charge, discharge, grid, output, energy))
        if np.max(np.minimum(c, d)) > 1e-5:
            raise ValueError("Simultaneous charging/discharging is physically rejected.")
        authoritative = bill(index, g, account)
        actual_wear = float(wear*.5*np.sum(c+d))
        gap = abs(authoritative["total"]+(actual_wear if include_wear else 0)-optimum)
        if gap > max(.01, abs(optimum)*1e-6):
            raise ValueError("Dispatch objective and authoritative tariff bill do not reconcile.")
        out = inputs.copy()
        for key, values in (("grid_import_kw", g), ("pv_output_kw", p), ("battery_charge_kw", c), ("battery_discharge_kw", d), ("battery_soc_kWh", e[:-1])):
            out[key] = np.maximum(values, 0)
        out["grid_export_kw"] = 0.
        out["pv_curtailed_kw"] = pv-out.pv_output_kw
        candidates.append((authoritative["total"]+(actual_wear if include_wear else 0), out, authoritative, actual_wear, gap))
    if not candidates:
        raise ValueError("No feasible tariff regime.")
    _, out, authoritative, actual_wear, gap = min(candidates, key=lambda item: item[0])
    return {"dispatch": out, "bill": authoritative, "degradation_cost": actual_wear,
            "objective_gap": gap, "terminal_energy_kWh": b.energy_kWh,
            "strategy": "historical_perfect_foresight", "load_factor_proof": {"upper_import_kWh": upper_energy, "lower_peak_kw": lower_peak}}
