"""Non-export ComEd operation; fixed histories/obligations and exclusive modes."""
import cvxpy as cp
import numpy as np
import pandas as pd

from .battery import Battery
from ..billing.comed_costs import compile_costs, calculate


def _exclusive_intervals(costs, n):
    """Only negative marginal energy can reward conversion-loss cycling.

    With nonnegative demand prices, removing a simultaneous pair at a
    nonnegative energy price cannot increase any billed component. Keep
    explicit binary modes elsewhere, including every interval if a future
    tariff ever has a negative demand component.
    """
    parts = getattr(costs, "blocks", [(slice(0,n),costs)])
    marginal = np.empty(n)
    for block, component in parts:
        if component.demand_per_kw < 0:
            return np.ones(n,dtype=bool)
        marginal[block] = component.marginal_per_kwh
    return marginal < 0


def _remove_dominated_cycles(c, d, g, p, battery, mask):
    """Preserve SOC while reducing imports and, if necessary, curtailing PV.

    Remove x of charging and eta_c*eta_d*x of discharging. Stored energy is
    unchanged; net supply falls by (1-eta_c*eta_d)*x. Reduce grid imports first,
    then PV. Discharge <= native load guarantees enough grid+PV to do so.
    Every nonnegative-price interval ends with one flow zero. Demand cannot
    increase. This gives a feasible exclusive schedule at the proven optimum.
    """
    ratio = battery.charge_efficiency*battery.discharge_efficiency
    removed = np.where(~mask, np.minimum(c,d/ratio),0.)
    c = c-removed; d = d-ratio*removed
    lost = (1-ratio)*removed
    grid_reduction = np.minimum(np.maximum(g,0.),lost)
    return c,d,g-grid_reduction,p-(lost-grid_reduction)


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
        energy = cp.Variable(n+1)
        exclusive = _exclusive_intervals(costs,n)
        discharge_limit = np.minimum(b.max_discharge_kw,load)
        constraints += [charge <= b.max_charge_kw, discharge <= discharge_limit,
                        energy[0] == b.energy_kWh, energy[-1] == b.energy_kWh,
                        energy >= b.minimum_energy_kWh, energy <= b.maximum_energy_kWh,
                        energy[1:] == energy[:-1]+dt*(charge*b.charge_efficiency-discharge/b.discharge_efficiency)]
        if exclusive.any():
            charging = cp.Variable(int(exclusive.sum()),boolean=True)
            constraints += [charge[exclusive] <= b.max_charge_kw*charging,
                discharge[exclusive] <= cp.multiply(discharge_limit[exclusive],1-charging)]
        throughput = dt*cp.sum(charge+discharge)
    else:
        charge = discharge = np.zeros(n)
        energy = np.zeros(n+1)
        throughput = 0.
    constraints += [grid+output+discharge == load+charge]
    subtotal = costs.subtotal(grid)
    objective = subtotal + (wear*throughput if include_wear else 0)
    # A twelve-cycle model has twelve separate billed demand peaks and up to
    # 35,136 battery-mode decisions. Keep monthly studies at 60 seconds, but
    # allow a bounded larger primary solve for explicitly linked cycles.
    # This changes the local resource budget, never the optimality criterion.
    primary_limit = min(300, 60 * len(billing_cycles)) if billing_cycles else 60
    options = {"time_limit": primary_limit, "mip_rel_gap": 1e-8}
    problem = cp.Problem(cp.Minimize(objective), constraints)
    problem.solve(solver="SCIPY", scipy_options=options)
    if problem.status != "optimal":
        raise ValueError(f"ComEd optimizer did not prove optimality within {primary_limit} seconds: " + str(problem.status))
    optimum = float(problem.value)
    def value(x):
        return np.asarray(x.value if isinstance(x, cp.Expression) else x, dtype=float)
    # A second solve can erase/replace Variable.value even on failure. Keep
    # independent copies of the already-proven primary optimum beforehand.
    selected = tuple(value(x).copy() for x in (charge, discharge, grid, output, energy))
    tie_status = "not_applicable"
    warnings = []
    # A bill-neutral tie break reduces unnecessary cycling. Negative-price
    # intervals retain binary modes; other flows are made exclusive below.
    if b is not None:
        tie = cp.Problem(cp.Minimize(throughput), constraints+[objective <= optimum+1e-6])
        try:
            tie.solve(solver="SCIPY", scipy_options={**options,"time_limit":60})
            tie_status = tie.status
        except cp.error.SolverError:
            tie_status = "solver_error"
        if tie_status == "optimal":
            selected = tuple(value(x).copy() for x in (charge, discharge, grid, output, energy))
        else:
            warnings.append("The cost solve proved optimal, but the cycling tie-break did not complete. "
                            "Dispatch retains the proven cost solution; minimum cycling among equally priced schedules is not established.")
    c, d, g, p, e = selected
    if b is not None:
        c,d,g,p = _remove_dominated_cycles(c,d,g,p,b,exclusive)
    if (np.minimum(c, d).max() > 1e-6 or g.min() < -1e-6 or p.min() < -1e-6
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
            "terminal_energy_kwh": float(e[-1]), "solver": f"SciPy HiGHS; proven cost optimum before cent rounding; primary limit {primary_limit}s, cycling limit 60s",
            "strategy": "historical perfect foresight", "cost_optimum_proven": True,
            "throughput_tie_break_status": tie_status, "warnings": warnings}
