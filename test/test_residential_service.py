"""Offline physical checks for the representative residential export circuit."""
import opendssdirect as dss
import pandas as pd
import pytest

from src.opendss.ac_replay import PVInverterReplay, PVReplayConfiguration
from src.opendss.residential_service import ResidentialService
from src.opendss.solar_export_replay import replay_export_scenario, SCENARIOS
from test_export_ac_replay import BATTERY, schedule, configuration


def test_center_tap_has_two_opposite_120_v_legs_and_240_v_between_them():
    service = ResidentialService()
    service.create_circuit()
    dss.Circuit.SetActiveBus('load_bus')
    values = dss.Bus.Voltages()
    nodes = dict(zip(dss.Bus.Nodes(), [complex(*values[i:i+2]) for i in range(0, len(values), 2)]))
    assert nodes[1] == pytest.approx(-nodes[2], abs=.01)
    measurements = service.measurements()
    assert measurements['voltage_l1_neutral_v'] == pytest.approx(120., abs=.1)
    assert measurements['voltage_l2_neutral_v'] == pytest.approx(120., abs=.1)
    assert measurements['voltage_l1_l2_v'] == pytest.approx(240., abs=.2)
    assert measurements['neutral_voltage_v'] < 1e-6
    dss.Transformers.Name('servicetransformer')
    assert dss.Transformers.NumWindings() == 3
    dss.Transformers.Wdg(1)
    assert dss.Transformers.kVA() == 25


@pytest.mark.parametrize('name', SCENARIOS)
def test_residential_scenarios_have_240_v_resources_and_original_scheduled_flows(name):
    frame = schedule(name)
    config = configuration(schedule('pv_with_export'))
    before = config.available_power_kw.copy()
    ac = replay_export_scenario(name, frame, battery=BATTERY, pv_capacity_kw=6., pv_replay=config)
    assert ac.feasible.all()
    assert ac.pv_actual_kw.to_numpy() == pytest.approx(frame.pv_output_kw, abs=.01)
    assert ac.pcc_balance_error_kw.abs().max() < .01
    assert ac.service_neutral_current_a.abs().max() < .001  # sub-mA numerical residual, balanced allocation
    assert ac.line_normal_rating_a.eq(100).all()
    assert set(dss.Loads.AllNames()) == {'buildingl1', 'buildingl2', 'building240'}
    for element in [f'Generator.{name}' for name in dss.Generators.AllNames()] + (
            ['Storage.Battery'] if SCENARIOS[name][1] else []):
        dss.Circuit.SetActiveElement(element)
        assert dss.CktElement.NumPhases() == 1
        assert dss.CktElement.BusNames() == ['load_bus.1.2']
        assert float(dss.Properties.Value('kV')) == .24
    pd.testing.assert_frame_equal(before, config.available_power_kw)
    assert config.inverters[0].voltage_kv == .48  # no mutation of profile metadata
    if name == 'grid_only':
        assert not dss.Generators.AllNames() and not dss.Storages.AllNames()
    # Core loss exists even at low loads and remains outside the bill flows.
    assert ac.transformer_real_loss_kw.min() >= .049


def test_120_v_imbalance_produces_neutral_current_and_distinct_leg_voltages():
    service = ResidentialService(l1_load_fraction=.8, l2_load_fraction=.1)
    frame = schedule('grid_only')
    ac = replay_export_scenario('grid_only', frame, battery=None, pv_capacity_kw=0., residential_service=service)
    assert ac.feasible.all()
    assert (ac.service_l1_current_a > ac.service_l2_current_a).all()
    assert ac.service_neutral_current_a.min() > 10
    assert ac.neutral_voltage_v.min() > .1
    assert (ac.voltage_l1_neutral_v < ac.voltage_l2_neutral_v).all()
    assert ac.minimum_voltage_pu.to_numpy() == pytest.approx(ac.voltage_l1_neutral_v / 120)
    assert ac.pcc_balance_error_kw.abs().max() < .01


def test_half_winding_overload_is_detected_despite_low_total_transformer_kva():
    service = ResidentialService(l1_load_fraction=1., l2_load_fraction=0.,
                                 service_length_km=.001, service_amps=200.)
    frame = schedule('grid_only').assign(native_load_kw=13., grid_import_kw=13., load_power_factor=1.)
    ac = replay_export_scenario('grid_only', frame, battery=None, pv_capacity_kw=0., residential_service=service)
    assert ac.converged.all()
    assert ac.transformer_primary_loading_percent.max() < 60
    assert ac.transformer_l1_loading_percent.min() > 100
    assert ac.transformer_overload.all() and not ac.feasible.any()


def test_service_overload_under_transformer_limit_is_reported():
    service = ResidentialService(transformer_kva=50., service_length_km=.001)
    frame = schedule('grid_only').assign(native_load_kw=26., grid_import_kw=26., load_power_factor=1.)
    ac = replay_export_scenario('grid_only', frame, battery=None, pv_capacity_kw=0., residential_service=service)
    assert ac.converged.all() and ac.line_overload.all()
    assert not ac.transformer_overload.any() and not ac.feasible.any()


def test_single_leg_export_uses_explicit_custom_wiring_rejection():
    frame = schedule('pv_with_export')
    cfg = PVReplayConfiguration((PVInverterReplay('Custom', 6., 6., bus='other_bus.1.0',
        phases=1, voltage_kv=.12),), pd.DataFrame({'Custom': frame.pv_available_kw.to_numpy()},
        index=pd.DatetimeIndex(frame.timestamp)))
    with pytest.raises(ValueError, match='240 V line-to-line'):
        replay_export_scenario('pv_with_export', frame, battery=None, pv_capacity_kw=6., pv_replay=cfg)


@pytest.mark.parametrize('kwargs', [dict(transformer_kva=0), dict(service_amps=float('nan')),
    dict(l1_load_fraction=.8,l2_load_fraction=.8),dict(l1_load_fraction=-.1),
    dict(conductor_x_ohm_per_km=-.1),dict(service_length_km=0)])
def test_invalid_physical_assumptions_are_rejected(kwargs):
    with pytest.raises(ValueError):
        ResidentialService(**kwargs)


def test_network_change_preserves_schedules_and_bills(tmp_path, monkeypatch):
    from src.local_web import export_study
    from test_export_ac_replay import fixture_results, request
    import json
    from copy import deepcopy
    result = fixture_results()
    before = deepcopy(result)
    monkeypatch.setattr(export_study, 'compare', lambda *a, **k: result)
    (tmp_path/'engine.json').write_text('{"id":"test"}')
    export_study.execute(tmp_path, request(), schedule('grid_only'), {'warnings': []})
    saved = json.loads((tmp_path/'result.json').read_text())
    assert saved['ac_validation']['version'] == 2
    assert saved['ac_validation']['network_configuration']['transformer_kva'] == 25
    assert saved['ac_validation']['network_configuration']['source'].startswith('https://opendss.epri.com/')
    assert len(saved['ac_validation']['scenarios']) == 5
    for name in SCENARIOS:
        pd.testing.assert_frame_equal(before[name]['dispatch'], result[name]['dispatch'])
        assert json.loads((tmp_path/'solar_bills.json').read_text())[name]['bill'] == before[name]['bill']
