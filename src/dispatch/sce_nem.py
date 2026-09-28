"""PV-first bounded SCE legacy NEM cycle comparison, without paired storage."""
import numpy as np

from ..billing.socal import bill, interval_index


def optimize(key, inputs, account, start, end, battery, wear,
             *, include_degradation_in_optimization=False):
    interval_index(inputs, start, end)
    if battery is not None:
        raise ValueError('SCE legacy NEM paired-storage settlement is not implemented.')
    load = np.asarray(inputs.native_load_kw, dtype=float)
    pv = np.asarray(inputs.pv_available_kw, dtype=float)
    if not np.isfinite(load).all() or not np.isfinite(pv).all() or np.min(load) < 0 or np.min(pv) < 0:
        raise ValueError('SCE NEM needs finite nonnegative load and PV power.')
    if not np.any(pv > 0):
        raise ValueError('SCE legacy NEM requires an eligible renewable generator.')
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
    return {'baseline_bill': baseline_bill, 'solar_bill': solar_bill, 'bill': solar_bill,
            'dispatch': solar, 'degradation_cost': 0., 'objective_gap': 0.,
            'optimization_method': 'SCE legacy NEM PV-first metered allocation'}
