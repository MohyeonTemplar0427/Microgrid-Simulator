"""Non-export ComEd operation; fixed histories/obligations and exclusive modes."""
import cvxpy as cp
import numpy as np
import pandas as pd

from .battery import Battery
from ..billing.comed_costs import compile_costs, calculate


def optimize(inputs, account, prices=None, battery=None, *, wear=0., include_wear=False, billing_cycles=None):
    index = pd.DatetimeIndex(inputs.timestamp)
    costs = compile_costs(index, account, prices, billing_cycles)
    if type(include_wear) is not bool or isinstance(wear, bool) or not np.isfinite(wear) or wear < 0:
        raise ValueError("Choose a nonnegative wear rate and explicit objective setting.")
    load, pv = (inputs[k].to_numpy(dtype=float) for k in ("native_load_kw", "pv_available_kw"))
    if not np.isfinite(load).all() or not np.isfinite(pv).all() or (load < 0).any() or (pv < 0).any():
        raise ValueError("Native load and available AC PV must be finite nonnegative kW.")
    n, dt = len(index), costs.hours
    grid, output = cp.Variable(n, nonneg=True), cp.Variable(n, nonneg=True)
    constraints = [output <= pv]
    b = Battery(**battery) if battery is not None else None
    if b is not None:
        charge, discharge = cp.Variable(n, nonneg=True), cp.Variable(n, nonneg=True)
        energy, charging = cp.Variable(n+1), cp.Variable(n, boolean=True)
        constraints += [charge <= b.max_charge_kw*charging,
                        discharge <= cp.multiply(np.minimum(b.max_discharge_kw, load), 1-charging),
                        energy[0] == b.energy_kWh, energy[-1] == b.energy_kWh,
                        energy >= b.minimum_energy_kWh, energy <= b.maximum_energy_kWh,
                        energy[1:] == energy[:-1]+dt*(charge*b.charge_efficiency-discharge/b.discharge_efficiency)]
        throughput = dt*cp.sum(charge+discharge)
    else:
        charge = discharge = np.zeros(n)
        energy = np.zeros(n+1)
        throughput = 0.
    constraints += [grid+output+discharge == load+charge]
    subtotal = costs.subtotal(grid)
    objective = subtotal + (wear*throughput if include_wear else 0)
    options = {"time_limit": 60, "mip_rel_gap": 1e-8}
    problem = cp.Problem(cp.Minimize(objective), constraints)
    problem.solve(solver="SCIPY", scipy_options=options)
    if problem.status != "optimal":
        raise ValueError("ComEd optimizer did not prove optimality within 60 seconds: " + str(problem.status))
    optimum = float(problem.value)
    def value(x):
        return np.asarray(x.value if isinstance(x, cp.Expression) else x, dtype=float)
    # A second solve can erase/replace Variable.value even on failure. Keep
    # independent copies of the already-proven primary optimum beforehand.
    selected = tuple(value(x).copy() for x in (charge, discharge, grid, output, energy))
    tie_status = "not_applicable"
    warnings = []
    # A bill-neutral tie break removes unnecessary cycling. Exclusivity is
    # enforced in the original MILP as well, including at negative prices.
    if b is not None:
        tie = cp.Problem(cp.Minimize(throughput), constraints+[objective <= optimum+1e-6])
        try:
            tie.solve(solver="SCIPY", scipy_options=options)
            tie_status = tie.status
        except cp.error.SolverError:
            tie_status = "solver_error"
        if tie_status == "optimal":
            selected = tuple(value(x).copy() for x in (charge, discharge, grid, output, energy))
        else:
            warnings.append("The cost solve proved optimal, but the cycling tie-break did not complete. "
                            "Dispatch retains the proven cost solution; minimum cycling among equally priced schedules is not established.")
    c, d, g, p, e = selected
    if (np.minimum(c, d).max() > 1e-6 or g.min() < -1e-6
            or np.max(abs(g+p+d-load-c)) > 1e-5
            or (b and (e.min() < b.minimum_energy_kWh-1e-5 or e.max() > b.maximum_energy_kWh+1e-5
                       or abs(e[-1]-b.energy_kWh) > 1e-5))):
        raise ValueError("ComEd dispatch violates a physical power or energy constraint.")
    # Remove solver-scale negatives only, then recalculate using Decimal bills.
    g, c, d, p = [np.maximum(x, 0.) for x in (g, c, d, p)]
    bill = calculate(pd.Series(g, index=index), account, prices, billing_cycles)
    raw_subtotal = costs.subtotal(g)
    rounding = bill["subtotal_usd"]-raw_subtotal
    if abs(rounding) > costs.rounding_bound_usd:
        raise ValueError("Authoritative ComEd subtotal and dispatch expressions do not reconcile.")
    degradation = float(wear*dt*(c+d).sum())
    actual_objective = raw_subtotal+(degradation if include_wear else 0)
    if abs(actual_objective-optimum) > max(1e-4, abs(optimum)*1e-7):
        raise ValueError("ComEd solver objective and evaluated schedule do not reconcile.")
    out = inputs.copy()
    for name, values in (("grid_import_kw", g), ("pv_output_kw", p), ("battery_charge_kw", c),
                         ("battery_discharge_kw", d), ("battery_soc_kWh", e[:-1])):
        out[name] = values
    out["grid_export_kw"] = 0.
    out["pv_curtailed_kw"] = np.maximum(pv-p, 0.)
    return {"dispatch": out, "bill": bill, "objective_usd": actual_objective,
            "unrounded_subtotal_usd": raw_subtotal, "degradation_cost_usd": degradation,
            "rounding_difference_usd": rounding, "rounding_bound_usd": costs.rounding_bound_usd,
            "recalculated_objective_usd": bill["subtotal_usd"]+(degradation if include_wear else 0),
            "solver_optimum_usd": optimum, "solver_gap_usd": actual_objective-optimum,
            "terminal_energy_kwh": float(e[-1]), "solver": "SciPy HiGHS; proven MILP optimum before cent rounding",
            "strategy": "historical perfect foresight", "cost_optimum_proven": True,
            "throughput_tie_break_status": tie_status, "warnings": warnings}
