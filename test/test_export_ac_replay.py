"""Offline export schedules, physical replay, persistence and old-result display."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess

import numpy as np
import opendssdirect as dss
import pandas as pd
import pytest

from src.dispatch.battery import Battery
from src.local_web import export_study
from src.local_web.contract import DEFAULT_SITE_REQUEST
from src.opendss.ac_replay import PVInverterReplay, PVReplayConfiguration
from src.opendss.solar_export_replay import SCENARIOS, export_handoff, replay_export_scenario
from test_export_settlement import account


BATTERY = dict(capacity_kWh=4, energy_kWh=.8, SOC_min=.2, SOC_max=.8,
               max_charge_kw=2, max_discharge_kw=2, charge_efficiency=.95, discharge_efficiency=.95)


def schedule(name):
    """Two daylight points then two dark points; charge returns to minimum SOC."""
    has_pv, storage = SCENARIOS[name]
    available = np.array([6., 6., 0., 0.]) if has_pv else np.zeros(4)
    charge = np.array([2., 0., 0., 0.]) if storage else np.zeros(4)
    discharge = np.array([0., 0., 1.805, 0.]) if storage else np.zeros(4)
    output = available.copy() if name.endswith('with_export') else np.minimum(available, 2. + charge)
    energy = np.array([.8, 1.275, 1.275, .8]) if storage else np.zeros(4)
    net = 2. + charge - discharge - output
    return pd.DataFrame(dict(timestamp=pd.date_range('2026-07-01 12:00', periods=4, freq='15min', tz='America/Los_Angeles'),
        native_load_kw=2., pv_available_kw=available, pv_output_kw=output, pv_curtailed_kw=available-output,
        grid_import_kw=np.maximum(net, 0), grid_export_kw=np.maximum(-net, 0),
        battery_charge_kw=charge, battery_discharge_kw=discharge, energy_kWh=energy))


def configuration(frame):
    return PVReplayConfiguration((PVInverterReplay('East', 4., 5.), PVInverterReplay('West', 2., 3.)),
        pd.DataFrame({'East': frame.pv_available_kw.to_numpy()*2/3, 'West': frame.pv_available_kw.to_numpy()/3},
                     index=pd.DatetimeIndex(frame.timestamp)))


@pytest.mark.parametrize('name', SCENARIOS)
def test_every_scenario_replays_scheduled_flows_and_only_its_equipment(name):
    frame = schedule(name)
    before = frame.copy(deep=True)
    # Even grid-only must ignore physical PV configuration supplied by the site.
    pv = configuration(schedule('pv_with_export'))
    ac = replay_export_scenario(name, frame, battery=BATTERY, pv_capacity_kw=6., pv_replay=pv)
    pd.testing.assert_frame_equal(frame, before)
    assert len(ac) == len(frame) and ac.feasible.all()
    assert bool(dss.Storages.AllNames()) == SCENARIOS[name][1]
    assert set(dss.Generators.AllNames()) == ({'east', 'west'} if SCENARIOS[name][0] else set())
    assert ac.pv_actual_kw.to_numpy() == pytest.approx(frame.pv_output_kw, abs=.01)
    assert ac.battery_actual_injection_kw.to_numpy() == pytest.approx(frame.battery_discharge_kw-frame.battery_charge_kw, abs=.01)
    assert ac.scheduled_grid_import_kw.to_numpy() == pytest.approx(frame.grid_import_kw)
    assert ac.scheduled_grid_export_kw.to_numpy() == pytest.approx(frame.grid_export_kw)
    assert ac.scheduled_grid_net_import_kw.to_numpy() == pytest.approx(frame.grid_import_kw-frame.grid_export_kw)
    assert ac.battery_soc_kWh.to_numpy() == pytest.approx(frame.energy_kWh)
    assert ac.pcc_balance_error_kw.abs().max() < .01
    assert ac.network_real_loss_kw.gt(0).all()
    if 'self_consumption' in name:
        assert ac.scheduled_pv_curtailed_kw.max() > 0
        assert not ac.reverse_power_flow.any()


def test_start_soc_mapping_allows_discharge_to_end_at_minimum():
    frame = schedule('storage_self_consumption')
    handoff = export_handoff(frame, battery=Battery(**BATTERY))
    assert handoff.battery_soc_start_kWh.tolist() == pytest.approx([.8, 1.275, 1.275, .8])
    assert handoff.battery_soc_end_kWh.tolist() == pytest.approx([1.275, 1.275, .8, .8])
    ac = replay_export_scenario('storage_self_consumption', frame, battery=BATTERY, pv_capacity_kw=6.)
    assert ac.loc[2, 'battery_actual_injection_kw'] == pytest.approx(1.805, abs=.01)
    assert ac.feasible.all()


@pytest.mark.parametrize('name', SCENARIOS)
def test_zero_pv_capacity_has_no_phantom_inverter(name):
    frame = schedule('grid_only')
    if SCENARIOS[name][1]: frame.energy_kWh = BATTERY['energy_kWh']
    ac = replay_export_scenario(name, frame, battery=BATTERY, pv_capacity_kw=0.)
    assert not dss.Generators.AllNames()
    assert bool(dss.Storages.AllNames()) == SCENARIOS[name][1]
    assert ac.feasible.all() and ac.pv_actual_kw.eq(0).all()


@pytest.mark.parametrize('change,match', [
    ('soc', 'SOC does not reconcile'), ('missing', 'continuous'),
    ('naive', 'timezone-aware'), ('curtailment', 'curtailment'), ('power', 'power balance'),
])
def test_bad_adapter_inputs_fail_explicitly(change, match):
    frame = schedule('storage_self_consumption')
    if change == 'soc': frame.loc[2, 'energy_kWh'] += .1
    if change == 'missing': frame = frame.drop(index=1)
    if change == 'naive': frame.timestamp = frame.timestamp.dt.tz_localize(None)
    if change == 'curtailment': frame.loc[0, 'pv_curtailed_kw'] += 1
    if change == 'power': frame.loc[0, 'grid_import_kw'] += 1
    with pytest.raises(ValueError, match=match):
        export_handoff(frame, battery=Battery(**BATTERY))


@pytest.mark.parametrize('start', ['2026-03-08 01:45-08:00', '2026-11-01 01:45-07:00'])
def test_adapter_keeps_dst_instants_and_interval_count(start):
    frame = schedule('grid_only')
    frame.timestamp = pd.date_range(start, periods=4, freq='15min').tz_convert('America/Los_Angeles')
    ac = replay_export_scenario('grid_only', frame, battery=None, pv_capacity_kw=0.)
    assert ac.timestamp.tolist() == frame.timestamp.tolist()
    assert ac.feasible.all()


def test_grid_only_ignores_equipment_but_rejects_nonzero_battery_flows():
    with pytest.raises(ValueError, match='without storage'):
        replay_export_scenario('pv_self_consumption', schedule('storage_self_consumption'), battery=BATTERY, pv_capacity_kw=6.)
    with pytest.raises(ValueError, match='without PV equipment'):
        replay_export_scenario('grid_only', schedule('pv_self_consumption'), battery=BATTERY, pv_capacity_kw=6.)
    with pytest.raises(ValueError, match='availability differs'):
        replay_export_scenario('pv_with_export', schedule('pv_with_export'), battery=None, pv_capacity_kw=6.,
                               pv_replay=configuration(schedule('grid_only')))


def test_overloaded_network_is_reported_even_when_powerflow_converges():
    frame = schedule('grid_only').assign(native_load_kw=1000., grid_import_kw=1000.)
    ac = replay_export_scenario('grid_only', frame, battery=None, pv_capacity_kw=0.)
    assert ac.converged.all() and not ac.feasible.any()
    assert ac.line_overload.all() and ac.transformer_overload.all()
    assert ac.voltage_violation.any()


def test_nonconvergence_retains_failed_intervals_and_masks_measurements(monkeypatch):
    from src.opendss import opendss_analysis as analysis
    original = analysis.apply_dispatch_operating_point
    def fail_solve(*args, **kwargs):
        original(*args, **kwargs)
        dss.Solution.Converged(False)
    monkeypatch.setattr(analysis, 'apply_dispatch_operating_point', fail_solve)
    ac = replay_export_scenario('grid_only', schedule('grid_only'), battery=None, pv_capacity_kw=0.)
    assert len(ac) == 4 and not ac.converged.any() and not ac.feasible.any()
    assert ac.network_real_loss_kw.isna().all() and ac.pcc_grid_import_kw.isna().all()
    assert ac.scheduled_grid_import_kw.eq(2.).all()


def request():
    r = deepcopy(DEFAULT_SITE_REQUEST)
    r.update(start_date='2026-07-01', end_date='2026-07-31', tariff_id=export_study.TARIFF, carbon_weight=0., pv_capacity_kw=6.)
    r['site']['utility'] = 'pge'
    r['site_profile'] = dict(site_type='residential', subtype='house')
    r['battery'] = deepcopy(BATTERY)
    r['solar_export'] = dict(account=account(), opening_balance=dict(generation=0, delivery=0, bonus=0), export_limit_kw=6.)
    return r


def fixture_results():
    # Only persistence tests use short precomputed dispatch/ledger fixtures.
    # test_export_settlement exercises the actual monthly optimizer and bills.
    result = {}
    for name in SCENARIOS:
        result[name] = dict(dispatch=schedule(name), bill=dict(amount_due=10.,
            import_charges=dict(generation=4., delivery=4., protected=2.),
            opening_balance=dict(generation=0., delivery=0., bonus=0.),
            closing_balance=dict(generation=0., delivery=0., bonus=0.),
            credits_used=dict(generation=0., delivery=0., bonus=0.),
            credits_earned=dict(generation=0., delivery=0., bonus=0.), warnings=[]),
            operating_cost=10., degradation_cost=0., objective_gap=None, optimization_scope='Synthetic persistence fixture')
    return result


@pytest.mark.parametrize('nonconverged', [False, True])
def test_completed_but_infeasible_result_preserves_bills_and_reports_failures(tmp_path, monkeypatch, nonconverged):
    results = fixture_results()
    for value in results.values():
        frame = value['dispatch']
        frame.native_load_kw += 1000.
        net = frame.native_load_kw + frame.battery_charge_kw - frame.pv_output_kw - frame.battery_discharge_kw
        frame.grid_import_kw = net.clip(lower=0)
        frame.grid_export_kw = (-net).clip(lower=0)
    if nonconverged:
        from src.opendss import opendss_analysis as analysis
        original = analysis.apply_dispatch_operating_point
        def fail_solve(*args, **kwargs):
            original(*args, **kwargs)
            dss.Solution.Converged(False)
        monkeypatch.setattr(analysis, 'apply_dispatch_operating_point', fail_solve)
    before = {k: {x: y for x, y in v.items() if x != 'dispatch'} for k, v in deepcopy(results).items()}
    monkeypatch.setattr(export_study, 'compare', lambda *args, **kwargs: results)
    (tmp_path/'engine.json').write_text('{"id":"test"}')
    export_study.execute(tmp_path, request(), schedule('grid_only'), {'warnings': []})
    manifest = json.loads((tmp_path/'result.json').read_text())
    validation = manifest['ac_validation']
    assert validation['status'] == 'completed' and validation['all_intervals_feasible'] is False
    assert len(validation['scenarios']) == 5
    for scenario in validation['scenarios']:
        assert scenario['checked_intervals'] == scenario['failed_intervals'] == 4
        assert ('OpenDSS did not converge' if nonconverged else 'Line overload') in scenario['failure_samples'][0]['reasons']
        assert (tmp_path/(scenario['interval_table']+'.csv')).exists()
        if nonconverged:
            assert scenario['network_loss_energy_kWh'] is None
            assert scenario['replay_pcc_grid_import_energy_kWh'] is None
            assert scenario['minimum_voltage_pu'] is None
            assert scenario['electrical_measurements_complete'] is False
        else:
            assert scenario['network_loss_energy_kWh'] > 0
    assert sum('Electrical validation failed for' in warning for warning in manifest['warnings']) == 5
    assert json.loads((tmp_path/'solar_bills.json').read_text()) == before
    assert pd.read_csv(tmp_path/'comparison.csv').amount_due.eq(10).all()


def test_worker_forwards_physical_replay_configuration(tmp_path, monkeypatch):
    from src.local_web import worker, site_inputs
    r = request()
    index = pd.date_range('2026-07-01', '2026-08-01', freq='15min', inclusive='left', tz='America/Los_Angeles')
    full = pd.DataFrame(dict(timestamp=index, load_kw=2., pv_kw=0.))
    sentinel = object()
    monkeypatch.setattr(worker, 'validate_request', lambda value: value)
    monkeypatch.setattr(site_inputs, 'build_site_inputs', lambda *args: (full, sentinel, {}, {'fixture': True}))
    captured = {}
    def capture(directory, request, frame, provenance, *, pv_replay=None):
        captured.update(replay=pv_replay, provenance=provenance, length=len(frame))
    monkeypatch.setattr(export_study, 'execute', capture)
    (tmp_path/'request.json').write_text(json.dumps(r))
    worker.execute(tmp_path)
    assert captured == dict(replay=sentinel, provenance={'fixture': True}, length=len(index))


def test_saved_result_downloads_and_legacy_manifest_remain_compatible(tmp_path, monkeypatch):
    from io import BytesIO
    from zipfile import ZipFile
    from test_local_web_pipeline import api_service
    from src.local_web.worker import write_json

    results = fixture_results()
    monkeypatch.setattr(export_study, 'compare', lambda *args, **kwargs: results)
    r = request()
    r.update(weather_source='clear_sky', weather_id=None)
    with api_service(tmp_path) as (app, call):
        study = app.store.submit(r, app.engine)
        directory = app.store.directory/'runs'/study['id']
        export_study.execute(directory, r, schedule('grid_only'), {'warnings': []})
        app.store.finish(study['id'])
        base = '/api/studies/'+study['id']
        saved = call(base)[1]
        assert saved['status'] == 'completed'
        assert saved['result']['ac_validation']['all_intervals_feasible'] is True
        for name in SCENARIOS:
            key = 'ac-'+name.replace('_', '-')
            page = call(base+'/tables/'+key+'?limit=2')[1]
            assert page['total'] == 4 and len(page['data']) == 2
            assert 'pcc_grid_net_import_kw' in page['columns']
            csv = call(base+'/tables/'+key+'.csv')[1]
            assert b'scheduled_pv_curtailed_kw' in csv
            assert b'battery_soc_start_kWh' in csv
        archive = ZipFile(BytesIO(call(base+'/tables.zip')[1]))
        assert any(path.endswith('ac-grid-only.csv') for path in archive.namelist())
        # Old results are read as originally stored; no validation is inferred.
        legacy = deepcopy(saved['result'])
        del legacy['ac_validation']
        legacy['tables'] = [table for table in legacy['tables'] if not table['id'].startswith('ac-')]
        write_json(directory/'result.json', legacy)
        assert 'ac_validation' not in call(base)[1]['result']


def test_saved_export_status_does_not_upgrade_legacy_results():
    source = (Path(__file__).parents[1]/'src/local_web/static/app.js').read_text()
    function = source.split('function solarExportCompletionMessage', 1)[1].split('\nasync function selectStudy', 1)[0]
    script = 'const message = function'+function+'; console.log(JSON.stringify(JSON.parse(process.argv[1]).map(message)));'
    manifests = [{}, {'ac_validation': {'all_intervals_feasible': True}},
        {'ac_validation': {'status': 'completed', 'all_intervals_feasible': True, 'scenarios': []}},
        {'ac_validation': {'status': 'completed', 'all_intervals_feasible': True, 'scenarios': [{'checked_intervals': 4}]}},
        {'ac_validation': {'status': 'completed', 'all_intervals_feasible': False, 'scenarios': [{'checked_intervals': 4}]}}]
    messages = json.loads(subprocess.check_output(['node', '-e', script, json.dumps(manifests)], text=True))
    assert all('was not evaluated' in message for message in messages[:3])
    assert 'All intervals passed' in messages[3]
    assert 'feasibility failures' in messages[4]
    assert 'solarExportCompletionMessage(study.result)' in source
