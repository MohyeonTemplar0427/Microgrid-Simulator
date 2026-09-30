"""PV-first BWP EV TOU solar dispatch with cycle bill reconciliation."""

import cvxpy as cp
import numpy as np

from ..billing.bwp_net_billing import settlement
from ..billing.socal import bill, charge_lines, interval_index, number
from .battery import Battery


def optimize(key, inputs, account, start, end, battery, wear, *,
             include_degradation_in_optimization=False):
    index = interval_index(inputs, start, end)
    load = np.asarray(inputs.native_load_kw, dtype=float)
    pv = np.asarray(inputs.pv_available_kw, dtype=float)
    if not np.isfinite(load).all() or not np.isfinite(pv).all() or (load < 0).any() or (pv < 0).any():
        raise ValueError('BWP solar requires finite nonnegative load and PV power.')
    if not (pv > 0).any():
        raise ValueError('BWP net billing requires an eligible generator.')
    number(wear, 'Battery degradation cost', 0, 10)
    baseline = inputs.copy()
    baseline['grid_import_kw'] = load
    baseline['grid_export_kw'] = 0.
    baseline_bill = bill(key, baseline, account, start, end)
    residual = np.maximum(load - pv, 0.)
    surplus = np.maximum(pv - load, 0.)
    solar = inputs.copy()
    solar['grid_import_kw'] = residual
    solar['grid_export_kw'] = surplus
    solar['pv_output_kw'] = pv
    solar['pv_curtailed_kw'] = 0.
    solar_bill = bill(key, solar, account, start, end)
    if battery is None:
        return dict(baseline_bill=baseline_bill, solar_bill=solar_bill, bill=solar_bill,
                    dispatch=solar, degradation_cost=0., objective_gap=0.,
                    optimization_method='BWP solar PV-first metered allocation')
    b = Battery(**battery)
    n = len(index)
    charge = cp.Variable(n, nonneg=True)
    discharge = cp.Variable(n, nonneg=True)
    energy = cp.Variable(n+1)
    grid = residual - discharge
    exports = surplus - charge
    constraints = [charge <= np.minimum(surplus, b.max_charge_kw),
                   discharge <= np.minimum(residual, b.max_discharge_kw),
                   energy[0] == b.energy_kWh, energy[-1] == b.energy_kWh,
                   energy >= b.capacity_kWh*b.SOC_min,
                   energy <= b.capacity_kWh*b.SOC_max,
                   energy[1:] == energy[:-1] + .25*(charge*b.charge_efficiency
                                                   - discharge/b.discharge_efficiency)]
    import_lines = charge_lines(key, index, grid, account, convex=True,
                                constraints=constraints)
    # An inherited balance changes the payable bill, but not dispatch.
    dispatch_account = dict(account, bwp_first_cycle_confirmed=True,
                            bwp_opening_credit=0.)
    due = settlement(import_lines, grid, exports, index, dispatch_account,
                     convex=True)
    degradation = wear*.25*cp.sum(charge + discharge)
    objective = due + (degradation if include_degradation_in_optimization else 0)
    problem = cp.Problem(cp.Minimize(objective), constraints)
    if not problem.is_dcp():
        raise ValueError('BWP solar dispatch objective is not convex.')
    problem.solve(solver='CLARABEL')
    if problem.status != 'optimal':
        raise ValueError('BWP solar dispatch did not reach an optimum: '+str(problem.status))
    optimum = float(problem.value)
    if not include_degradation_in_optimization:
        tolerance = max(1e-5, abs(optimum)*1e-8)
        tie = cp.Problem(cp.Minimize(cp.sum(charge+discharge)),
                         constraints+[due <= optimum+tolerance])
        tie.solve(solver='CLARABEL')
        if tie.status != 'optimal':
            raise ValueError('BWP solar dispatch tie-break did not converge.')
    if np.max(np.minimum(charge.value, discharge.value)) > 1e-5:
        raise ValueError('BWP solar dispatch cannot charge and discharge together.')
    out = inputs.copy()
    out['grid_import_kw'] = np.maximum(np.asarray(grid.value).reshape(-1), 0.)
    out['grid_export_kw'] = np.maximum(np.asarray(exports.value).reshape(-1), 0.)
    out['pv_output_kw'] = pv
    out['pv_curtailed_kw'] = 0.
    out['battery_charge_kw'] = np.maximum(charge.value, 0.)
    out['battery_discharge_kw'] = np.maximum(discharge.value, 0.)
    out['energy_kWh'] = energy.value[:-1]
    authoritative = bill(key, out, account, start, end)
    dispatch_bill = bill(key, out, dispatch_account, start, end)
    wear_cost = float(degradation.value)
    gap = abs(dispatch_bill['total'] +
              (wear_cost if include_degradation_in_optimization else 0)-optimum)
    if gap > max(.02, abs(optimum)*1e-6):
        raise ValueError(f'BWP solar bill and dispatch disagree by ${gap:.4f}.')
    return dict(baseline_bill=baseline_bill, solar_bill=solar_bill,
                bill=authoritative, dispatch=out, degradation_cost=wear_cost,
                objective_gap=gap,
                optimization_method='BWP solar cycle cost before inherited credits')
