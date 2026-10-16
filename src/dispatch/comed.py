"""Non-export ComEd operation; fixed histories/obligations and exclusive modes."""
import cvxpy as cp
import numpy as np
import pandas as pd
import time

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


def _validated_refinement(values, *, load, pv, battery, costs, mask,
                          optimum, wear, include_wear, maximum_throughput):
    """Accept only cost-neutral, physically feasible independent array copies."""
    if any(v is None for v in values):
        return None
    c,d,g,p,e = (np.asarray(v, dtype=float).copy() for v in values)
    n,dt = len(load),costs.hours
    if (any(v.shape != (n,) for v in (c,d,g,p)) or e.shape != (n+1,)
            or any(not np.isfinite(v).all() for v in (c,d,g,p,e))):
        return None
    c,d,g,p = _remove_dominated_cycles(c,d,g,p,battery,mask)
    if (min(c.min(),d.min(),g.min(),p.min()) < -1e-7
            or np.max(np.minimum(c,d)) > 1e-6
            or c.max() > battery.max_charge_kw+1e-6
            or np.max(d-np.minimum(battery.max_discharge_kw,load)) > 1e-6
            or np.max(p-pv) > 1e-6
            or np.max(abs(g+p+d-load-c)) > 1e-5
            or e.min() < battery.minimum_energy_kWh-1e-5
            or e.max() > battery.maximum_energy_kWh+1e-5
            or abs(e[0]-battery.energy_kWh) > 1e-5
            or abs(e[-1]-battery.energy_kWh) > 1e-5
            or np.max(abs(np.diff(e)-dt*(c*battery.charge_efficiency-d/battery.discharge_efficiency))) > 1e-5):
        return None
    throughput = float(dt*np.sum(c+d))
    objective = costs.subtotal(g)+(wear*throughput if include_wear else 0.)
    if (objective > optimum+1.1e-6
            or abs(objective-optimum) > max(1e-4,abs(optimum)*1e-7)
            or throughput > maximum_throughput+1e-6):
        return None
    return c,d,g,p,e


def _refine_throughput(*, variables, constraints, modes, primary_modes,
                       throughput, selected, validate, time_limit, hours,
                       relaxation_constraints=None):
    """Keep a validated incumbent if the global secondary solve is interrupted.

    The first LP fixes only the negative-price binary choices from the proven
    primary solution. Its scope is conditional on those choices. An outer LP
    can certify a validated incumbent that matches its lower bound. Otherwise
    the full MILP retains every original binary, the original cost bound and
    full-year SOC coupling. Unmatched bounds never establish minimum cycling.
    """
    started = time.monotonic()
    def measure(values):
        return float(hours*np.sum(values[0]+values[1]))
    initial = measure(selected)
    metadata = dict(method="cost_neutral_incumbent_and_global_refinement", status="retained_primary",
                    minimum_throughput_proven=False, selected_solution="primary",
                    fixed_mode_status="not_needed", global_status="not_started",
                    relaxation_status="not_needed", proof_method="not_proven",
                    global_lower_bound_source=None,
                    primary_throughput_kwh=initial, selected_throughput_kwh=initial,
                    throughput_reduction_kwh=0., global_lower_bound_kwh=None,
                    optimality_gap_kwh=None, time_limit_seconds=time_limit)
    def candidate(maximum):
        checked = validate(tuple(v.value for v in variables))
        tolerance=max(1e-5,abs(maximum)*1e-8)
        return checked if checked is not None and measure(checked)<=maximum+tolerance else None
    # Numeric mode assignments make this auxiliary problem an LP. The full
    # original binary variables are retained in the global solve below.
    if modes is not None:
        # Do not fix mutable variable attributes or relax integrality. The
        # caller supplies an independent linear model for the fixed modes.
        fixed_constraints = modes[1](primary_modes)
        local = cp.Problem(cp.Minimize(throughput), constraints+fixed_constraints)
        try:
            local.solve(solver="SCIPY", scipy_options={"time_limit":min(10.,time_limit)})
            metadata["fixed_mode_status"] = local.status
            if local.status in ("optimal", "optimal_inaccurate"):
                improved = candidate(initial)
                if improved is not None:
                    selected = improved
                    metadata["selected_solution"] = "primary_modes_refined"
                else:
                    metadata["fixed_mode_status"] = "invalid_solution"
        except cp.error.SolverError:
            metadata["fixed_mode_status"] = "solver_error"
    # Dropping mode integrality gives an outer relaxation, not an executable
    # dispatch. Its optimum is a lower bound for every physical schedule. A
    # validated incumbent that meets this bound certifies the original problem,
    # even if the relaxed optimizer itself contains simultaneous flows.
    def record_bound(lower, source):
        actual = measure(selected)
        tolerance = max(1e-5, abs(actual)*1e-8)
        if lower is None or not np.isfinite(lower) or lower > actual+tolerance:
            return False
        previous = metadata["global_lower_bound_kwh"]
        if previous is None or lower > previous:
            metadata["global_lower_bound_kwh"] = float(lower)
            metadata["global_lower_bound_source"] = source
        return actual-metadata["global_lower_bound_kwh"] <= tolerance

    remaining = time_limit-(time.monotonic()-started)
    if relaxation_constraints is not None and remaining > 0:
        relaxed = cp.Problem(cp.Minimize(throughput), constraints+relaxation_constraints)
        try:
            relaxed.solve(solver="SCIPY", scipy_options={"time_limit":min(10.,remaining)})
            metadata["relaxation_status"] = relaxed.status
            # An interrupted/inaccurate primal objective is not a lower bound.
            if relaxed.status == "optimal" and np.isfinite(relaxed.value):
                lower = float(relaxed.value)
                improved = candidate(measure(selected))
                if improved is not None and measure(improved) < measure(selected):
                    selected = improved
                    metadata["selected_solution"] = "physical_relaxation_incumbent"
                if record_bound(lower, "continuous_relaxation"):
                    metadata.update(minimum_throughput_proven=True, global_status="optimal",
                                    proof_method="continuous_relaxation_bound",
                                    selected_solution="global_minimum_throughput")
                elif lower > measure(selected)+max(1e-5,abs(measure(selected))*1e-8):
                    metadata["relaxation_status"] = "inconsistent_bound"
        except cp.error.SolverError:
            metadata["relaxation_status"] = "solver_error"
    remaining = time_limit-(time.monotonic()-started)
    if remaining > 0 and not metadata["minimum_throughput_proven"]:
        bound = measure(selected)
        global_constraints = constraints+(modes[0] if modes is not None else [])
        tie = cp.Problem(cp.Minimize(throughput),global_constraints+[throughput <= bound+1e-6])
        try:
            tie.solve(solver="SCIPY",scipy_options={"time_limit":remaining,"mip_rel_gap":1e-8})
            metadata["global_status"] = tie.status
            if tie.status in ("optimal", "optimal_inaccurate", "user_limit"):
                improved = candidate(bound)
                if improved is not None:
                    # Keep the lower-throughput feasible incumbent when the
                    # globally optimal point differs only by solver tolerance.
                    if measure(improved)<measure(selected):
                        selected = improved
                    metadata["selected_solution"] = ("global_minimum_throughput" if tie.status=="optimal"
                                                     else "global_feasible_incumbent")
                    metadata["minimum_throughput_proven"] = tie.status=="optimal"
                    if tie.status=="optimal":
                        metadata["proof_method"] = "full_milp"
                elif tie.status=="optimal":
                    metadata["global_status"] = "invalid_solution"
            stats = tie.solver_stats.extra_stats if tie.solver_stats else None
            lower = stats.get("mip_dual_bound") if isinstance(stats,dict) else None
            if metadata["minimum_throughput_proven"]:
                lower = float(tie.value)
            record_bound(lower, "full_milp")
        except cp.error.SolverError:
            metadata["global_status"] = "solver_error"
    elif not metadata["minimum_throughput_proven"]:
        metadata["global_status"] = "time_limit"
    actual = measure(selected)
    metadata.update(selected_throughput_kwh=actual,
                    throughput_reduction_kwh=max(0.,initial-actual),
                    proof_tolerance_kwh=max(1e-5,abs(actual)*1e-8),
                    status="optimal" if metadata["minimum_throughput_proven"] else
                           "improved_unproven" if actual < initial-1e-6 else "retained_primary",
                    elapsed_seconds=time.monotonic()-started)
    if metadata["global_lower_bound_kwh"] is not None:
        metadata["optimality_gap_kwh"] = max(0.,actual-metadata["global_lower_bound_kwh"])
    return selected,metadata


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
    mode_constraints = []
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
            mode_constraints = [charge[exclusive] <= b.max_charge_kw*charging,
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
    problem = cp.Problem(cp.Minimize(objective), constraints+mode_constraints)
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
    refinement = dict(status="not_applicable", minimum_throughput_proven=None,
                      primary_throughput_kwh=0., selected_throughput_kwh=0.,
                      throughput_reduction_kwh=0., optimality_gap_kwh=None)
    warnings = []
    # A bill-neutral tie break reduces unnecessary cycling. Negative-price
    # intervals retain binary modes; other flows are made exclusive below.
    if b is not None:
        c,d,g,p,e = selected
        c,d,g,p = _remove_dominated_cycles(c,d,g,p,b,exclusive)
        selected = c,d,g,p,e
        initial_throughput = float(dt*np.sum(c+d))
        def validate(candidate):
            return _validated_refinement(candidate,load=load,pv=pv,battery=b,costs=costs,
                mask=exclusive,optimum=optimum,wear=wear,include_wear=include_wear,
                maximum_throughput=initial_throughput)
        def fixed_modes(assignment):
            return [charge[exclusive]<=b.max_charge_kw*assignment,
                    discharge[exclusive]<=cp.multiply(discharge_limit[exclusive],1-assignment)]
        relaxation = None
        if exclusive.any():
            relaxed_modes = cp.Variable(int(exclusive.sum()))
            # Valid for every exclusive schedule: energy available at interval
            # start bounds discharge, and empty space bounds charging. These
            # cuts strengthen the relaxation without fixing an incumbent mode
            # or introducing artificial month-end SOC boundaries.
            relaxation = fixed_modes(relaxed_modes)+[
                relaxed_modes >= 0, relaxed_modes <= 1,
                charge <= (b.maximum_energy_kWh-energy[:-1])/(dt*b.charge_efficiency),
                discharge <= (energy[:-1]-b.minimum_energy_kWh)*b.discharge_efficiency/dt]
        selected,refinement = _refine_throughput(variables=(charge,discharge,grid,output,energy),
            constraints=constraints+[objective<=optimum+1e-6],
            modes=(mode_constraints,fixed_modes) if exclusive.any() else None,
            primary_modes=np.rint(value(charging)) if exclusive.any() else None,
            throughput=throughput,selected=selected,validate=validate,
            time_limit=primary_limit,hours=dt,relaxation_constraints=relaxation)
        tie_status = refinement["global_status"]
        if not refinement["minimum_throughput_proven"]:
            warnings.append("The cost solve proved optimal, but the global cycling tie-break did not complete. "
                "Dispatch uses a validated cost-neutral incumbent with no more throughput than the primary solution; "
                "minimum cycling among all equally priced schedules is not established. "
                "Inspect throughput_refinement for the selected solution and proof scope.")
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
            "terminal_energy_kwh": float(e[-1]), "solver": f"SciPy HiGHS; proven cost optimum before cent rounding; primary limit {primary_limit}s, cycling budget {primary_limit}s",
            "strategy": "historical perfect foresight", "cost_optimum_proven": True,
            "throughput_tie_break_status": tie_status, "throughput_refinement": refinement, "warnings": warnings}
