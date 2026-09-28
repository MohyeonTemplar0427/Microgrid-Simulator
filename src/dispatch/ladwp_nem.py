"""Exact idle-storage optimum for the bounded LADWP R-1A NEM case."""
import numpy as np

from ..billing.socal import bill, interval_index, number
from .battery import Battery


def optimize(key, inputs, account, start, end, battery, wear, *, include_degradation_in_optimization=False):
    interval_index(inputs, start, end)
    load = np.asarray(inputs.native_load_kw, dtype=float)
    pv = np.asarray(inputs.pv_available_kw, dtype=float)
    if not np.isfinite(load).all() or not np.isfinite(pv).all() or np.min(load) < 0 or np.min(pv) < 0:
        raise ValueError('LADWP NEM requires finite nonnegative load and PV profiles.')
    if not np.any(pv > 0):
        raise ValueError('LADWP NEM requires a renewable generator.')
    number(wear, 'Battery degradation cost', 0, 10)
    baseline = inputs.copy()
    baseline['grid_import_kw'] = load
    baseline['grid_export_kw'] = 0.
    baseline_bill = bill(key, baseline, account, start, end)
    solar = inputs.copy()
    solar['grid_import_kw'] = np.maximum(load - pv, 0.)
    solar['grid_export_kw'] = np.maximum(pv - load, 0.)
    solar['pv_output_kw'] = pv
    solar['pv_curtailed_kw'] = 0.
    solar_bill = bill(key, solar, account, start, end)
    if battery is None:
        return {'baseline_bill': baseline_bill, 'solar_bill': solar_bill, 'bill': solar_bill,
                'dispatch': solar, 'degradation_cost': 0., 'objective_gap': 0.,
                'optimization_method': 'LADWP R-1A billing-cycle netting'}
    b = Battery(**battery)
    # On R-1A, each exported kWh offsets an imported kWh within this cycle at
    # the same net-energy price. With equal initial/final SOC and efficiency
    # <= 1, storage cannot lower net imports. Its zero-throughput schedule is
    # bill-optimal (and minimizes wear among tied schedules).
    out = solar.copy()
    out['battery_charge_kw'] = 0.
    out['battery_discharge_kw'] = 0.
    out['energy_kWh'] = b.energy_kWh
    return {'baseline_bill': baseline_bill, 'solar_bill': solar_bill, 'bill': solar_bill,
            'dispatch': out, 'degradation_cost': 0., 'objective_gap': 0.,
            'optimization_method': 'Analytic R-1A net-energy optimum: storage idle'}
