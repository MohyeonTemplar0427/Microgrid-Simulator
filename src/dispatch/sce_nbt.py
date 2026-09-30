"""SCE NBT23–NBT26 PV-first, PV-charged storage dispatch."""
import cvxpy as cp
import numpy as np

from ..billing.sce_nbt import settlement
from ..billing.socal import bill, charge_lines, interval_index
from .battery import Battery


def optimize(key, inputs, account, start, end, battery, wear, *, include_degradation_in_optimization=False):
    index = interval_index(inputs, start, end)
    load = np.asarray(inputs.native_load_kw, dtype=float)
    pv = np.asarray(inputs.pv_available_kw, dtype=float)
    if not np.isfinite(load).all() or not np.isfinite(pv).all() or np.min(load) < 0 or np.min(pv) < 0:
        raise ValueError('SCE NBT needs finite nonnegative load and PV power.')
    if not np.any(pv > 0):
        raise ValueError('SCE NBT requires an eligible renewable generator.')
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
        return {'baseline_bill': baseline_bill, 'solar_bill': solar_bill, 'bill': solar_bill,
                'dispatch': solar, 'degradation_cost': 0., 'objective_gap': 0.,
                'optimization_method': 'PV-first metered allocation'}
    b = Battery(**battery)
    n = len(index)
    charge = cp.Variable(n, nonneg=True)
    discharge = cp.Variable(n, nonneg=True)
    energy = cp.Variable(n + 1)
    grid = residual - discharge
    exports = surplus - charge
    constraints = [charge <= np.minimum(surplus, b.max_charge_kw),
                   discharge <= np.minimum(residual, b.max_discharge_kw),
                   energy[0] == b.energy_kWh, energy[-1] == b.energy_kWh,
                   energy >= b.capacity_kWh * b.SOC_min,
                   energy <= b.capacity_kWh * b.SOC_max,
                   energy[1:] == energy[:-1] + .25 * (charge * b.charge_efficiency - discharge / b.discharge_efficiency)]
    lines = charge_lines(key, index, grid, account, convex=True, constraints=constraints)
    # Carried-in credits settle the bill but must not change this cycle's
    # operating schedule. Newly earned export credits still enter the objective.
    dispatch_account = dict(account)
    for name in ('nbt_opening_delivery_eec', 'nbt_opening_generation_eec',
                 'nbt_opening_acc_plus'):
        dispatch_account[name] = 0.
    due = settlement(lines, grid, exports, index, dispatch_account, convex=True)
    degradation = wear * .25 * cp.sum(charge + discharge)
    objective = due + (degradation if include_degradation_in_optimization else 0)
    problem = cp.Problem(cp.Minimize(objective), constraints)
    if not problem.is_dcp():
        raise ValueError('SCE NBT dispatch objective is not convex.')
    problem.solve(solver='CLARABEL')
    if problem.status != 'optimal':
        raise ValueError('SCE NBT dispatch did not reach an optimum: ' + str(problem.status))
    optimal = float(problem.value)
    if not include_degradation_in_optimization:
        tie = cp.Problem(cp.Minimize(cp.sum(charge + discharge)),
                         constraints + [due <= optimal + max(1e-5, abs(optimal) * 1e-8)])
        tie.solve(solver='CLARABEL')
        if tie.status != 'optimal':
            raise ValueError('SCE NBT dispatch tie-break did not converge.')
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
    gap = abs(dispatch_bill['total'] + (wear_cost if include_degradation_in_optimization else 0) - optimal)
    if gap > max(.02, abs(optimal) * 1e-6):
        raise ValueError(f'SCE NBT bill and dispatch objective disagree by ${gap:.4f}.')
    return {'baseline_bill': baseline_bill, 'solar_bill': solar_bill, 'bill': authoritative,
            'dispatch': out, 'degradation_cost': wear_cost, 'objective_gap': gap,
            'optimization_method': 'SCE NBT cycle cost before inherited credits'}
