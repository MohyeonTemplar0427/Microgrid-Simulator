"""Load-only study adapter: no weather, PV, inverter, storage or optimization."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

FIELDS = {'schema_version', 'name', 'site', 'site_profile', 'start_date', 'end_date',
          'timezone', 'timestep_minutes', 'tariff_id', 'load', 'fixed_price_per_kWh',
          'carbon_intensity_g_per_kWh'}


def validate(request):
    from .contract import DEFAULT_SITE_REQUEST, validate_request
    if not isinstance(request, dict) or set(request) - {"carbon"} != FIELDS or type(request['schema_version']) is not int or request['schema_version'] != 5:
        raise ValueError('Supply exactly the schema 5 grid-only study fields.')
    # Reuse the existing shared site/date/load/account validation. Equipment
    # defaults exist only in this validation adapter, never in saved inputs or execution.
    common = deepcopy(DEFAULT_SITE_REQUEST)
    common.update({k: v for k, v in request.items() if k != 'schema_version'})
    validate_request(common)
    if request['tariff_id'] and any(part in request['tariff_id'] for part in ('_option_r_', '_option_s_')):
        raise ValueError('Renewable/storage option tariffs are incompatible with a grid-only study.')
    return request


def save_results(directory, request, tables, warnings, **metadata):
    from .worker import write_json
    directory = Path(directory)
    entries = []
    for key, label, frame in tables:
        payload = json.loads(frame.to_json(orient='split', index=False, date_format='iso', double_precision=15))
        payload['labels'] = [c.replace('_', ' ') for c in payload['columns']]
        write_json(directory / (key + '.json'), payload)
        frame.to_csv(directory / (key + '.csv'), index=False)
        entries.append(dict(id=key, label=label, row_count=len(frame)))
    write_json(directory / 'result.json', dict(schema_version=request['schema_version'],
        request=request, tables=entries, warnings=warnings,
        engine=json.loads((directory / 'engine.json').read_text()), **metadata))
    write_json(directory / 'progress.json', {'message': 'Grid-only billing complete'})


def execute(directory, request):
    import pandas as pd
    from ..timeseries import build_interval_index_from_days
    from ..profiles import ConstantLoad, SyntheticLoad, BuildingArchetype, LoadScaling
    from ..billing import get_tariff
    from ..billing.charges import calculate_meter_billing
    from ..simulation.interface_analysis import retail_tariff_ids_for_region
    validate(request)
    days = (date.fromisoformat(request['end_date']) - date.fromisoformat(request['start_date'])).days + 1
    grid = build_interval_index_from_days(request['start_date'], days, request['timezone'], request['timestep_minutes'])
    load = request['load']
    model = ConstantLoad(load['power_kw']) if load['mode'] == 'constant' else SyntheticLoad(
        archetype=BuildingArchetype(load['archetype']), scaling=LoadScaling.PEAK_KW,
        peak_kw=load['power_kw'], variability_fraction=0, random_seed=20260101)
    power = model.build_load_kw(grid).to_numpy()
    frame = pd.DataFrame(dict(timestamp=grid.index, native_load_kw=power,
                              grid_import_kw=power, grid_export_kw=0.0, pv_available_kw=0.0))
    frame.to_csv(Path(directory) / 'normalized.csv', index=False)
    hours = request['timestep_minutes'] / 60
    energy = float(power.sum() * hours)
    warnings = ['Grid-only study: no PV, battery, weather retrieval, inverter model or dispatch optimization.',
                'Load is a user-specified assumption, not measured demand.',
                'Grid carbon intensity is a constant user assumption, not retrieved regional data.',
                'No AC power-flow replay is performed; electrical network feasibility is not evaluated.']
    periods = []
    if request['tariff_id']:
        if request['tariff_id'] not in retail_tariff_ids_for_region('caiso_np15'):
            raise ValueError('Select a supported tariff.')
        tariff = get_tariff(request['tariff_id'])
        periods = calculate_meter_billing(frame, tariff, meter_id='site', timestep_hours=hours)
        warnings.extend([tariff.notes, *(w for period in periods for w in period.warnings)])
        energy_cost = sum(p.import_energy_charge for p in periods)
        demand = sum(p.demand_charge for p in periods)
        customer = sum(p.customer_charge for p in periods)
    else:
        energy_cost, demand, customer = energy * request['fixed_price_per_kWh'], 0, 0
        warnings.append('Flat energy-price assumption only; no utility tariff bill is calculated.')
    from .carbon import values as carbon_values
    carbon, carbon_provenance = carbon_values(request, directory, grid.index)
    frame['gCO2/kWh'] = carbon
    frame.to_csv(Path(directory) / 'normalized.csv', index=False)
    warnings = [w for w in warnings if not w.startswith('Grid carbon intensity')]
    warnings.append(carbon_provenance['warning'])
    total = energy_cost + demand + customer
    comparison = dict(scenario='no_battery', energy_cost=energy_cost, demand_charge=demand,
        customer_charge=customer, total_utility_charge=total, total_explicit_cost=total,
        degradation_cost=0.0, peak_grid_import_kw=float(power.max()), interval_count=len(frame),
        grid_import_kWh=energy, emissions_kgCO2=float((power * carbon).sum() * hours / 1000))
    for period in periods:
        for key, value in period.import_energy_charge_by_component.items():
            comparison[key + '_charge'] = comparison.get(key + '_charge', 0) + value
    costs = pd.DataFrame([dict(period=p.period_label, energy_cost=p.import_energy_charge,
        demand_charge=p.demand_charge, customer_charge=p.customer_charge,
        total_utility_charge=p.total_utility_charge, billed_peak_kw=p.billed_peak_kw) for p in periods])
    if costs.empty:
        costs = pd.DataFrame([comparison])
    save_results(directory, request, [('comparison', 'Grid-only operating cost', pd.DataFrame([comparison])),
        ('costs', 'Billing periods', costs), ('inputs', 'Grid-only load and imports', frame)], warnings, input_provenance={'carbon':carbon_provenance})
