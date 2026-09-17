"""Offline energy-boundary, provenance and integration regression tests."""
from copy import deepcopy
import json
import math

import pytest

from src.equipment.ess import detail, resolve, search, validate_resolution
from src.dispatch.battery import Battery
from src.local_web.contract import DEFAULT_CANDIDATE_REQUEST, validate_request

AP='franklinwh.apower2.apr10k15v2us.240'
PW='tesla.powerwall2.1092170.na'


def ap(**kwargs):
    return resolve(AP,efficiency_approximation=True,**kwargs)


def test_delivers_published_ac_energy_and_roundtrip():
    resolved=ap(initial_soc=1,backup_reserve=0)
    battery=Battery(**resolved['battery'])
    assert battery.capacity_kWh==pytest.approx(15/math.sqrt(.9))
    battery.update_energy(0,3,5)
    assert battery.energy_kWh==pytest.approx(0,abs=1e-12)
    input_energy=15/.9
    battery.update_energy(3,0,input_energy/3)
    assert battery.energy_kWh==pytest.approx(battery.maximum_energy_kWh)
    assert 15/input_energy==pytest.approx(.9)


def test_usable_window_initial_and_reserve_are_applied_once():
    resolved=ap(quantity=2,initial_soc=.6,backup_reserve=.1)
    b=Battery(**resolved['battery'])
    assert b.energy_kWh/b.capacity_kWh==pytest.approx(.6)
    assert resolved['dispatchable_ac_energy_kwh']==pytest.approx(27)
    assert (b.energy_kWh-b.minimum_energy_kWh)*b.discharge_efficiency==pytest.approx(15)
    assert b.max_charge_kw==16 and b.max_discharge_kw==20
    assert b.SOC_max==1


def test_powerwall_requires_explicit_energy_basis():
    r=resolve(PW,efficiency_approximation=True)
    assert not r['ready'] and 'measurement' in r['requirements'][0]
    r=resolve(PW,capacity_basis='ac_deliverable',efficiency_approximation=True,backup_reserve=0)
    assert r['usable_ac_energy_kwh']==pytest.approx(13.5)
    assert any('not a verified' in x for x in r['assumptions'])
    internal=resolve(PW,capacity_basis='usable_internal',efficiency_approximation=True)
    assert internal['battery']['capacity_kWh']==13.5
    assert internal['usable_ac_energy_kwh']==pytest.approx(13.5*math.sqrt(.9))


@pytest.mark.parametrize('change',[dict(quantity=0),dict(quantity=True),dict(quantity=1.5),dict(quantity=16),dict(initial_soc=float('nan')),dict(backup_reserve=1),dict(initial_soc=.1,backup_reserve=.2),dict(capacity_basis='usable_internal')])
def test_invalid_configurations(change):
    with pytest.raises(ValueError): ap(**change)


def test_overrides_are_derates_with_provenance():
    r=ap(overrides={'max_charge_kw':4})
    assert r['battery']['max_charge_kw']==4 and r['battery']['max_discharge_kw']==10
    assert r['provenance']['max_charge_kw']['status']=='user_overridden'
    validate_resolution(r)
    with pytest.raises(ValueError): ap(overrides={'max_charge_kw':9})
    with pytest.raises(ValueError): ap(overrides={'capacity_kWh':100})


def test_incomplete_and_hybrid_sources_do_not_become_presets():
    assert not resolve('tesla.powerwall3.1707000.na',efficiency_approximation=True)['ready']
    assert not resolve(AP)['ready']
    record=detail(AP);record['fields']['charge_kw']['value']=None
    r=resolve(AP,record=record,efficiency_approximation=True)
    assert not r['ready'] and 'charge_kw' in r['requirements'][0]
    record=detail(AP);record['fields']['efficiency_path']['value']='solar_battery_home'
    assert not resolve(AP,record=record,efficiency_approximation=True)['ready']


def test_export_preserves_gaps_and_requires_explicit_assumptions():
    from tools.export_ess_catalog import build_export
    raw = build_export()
    assert len(raw['resolutions']) == 3
    assert all(not r['ready'] and r['battery'] is None for r in raw['resolutions'])
    configured = build_export(accept_efficiency_approximation=True,
                              powerwall2_capacity_basis='ac_deliverable')
    ready = [r for r in configured['resolutions'] if r['ready']]
    assert {r['equipment']['id'] for r in ready} == {AP, PW}
    for r in ready:
        validate_resolution(json.loads(json.dumps(r)))
    hybrid = configured['resolutions'][-1]
    assert not hybrid['ready'] and hybrid['battery'] is None
    facts = hybrid['equipment']['fields']
    assert facts['round_trip_efficiency']['value'] is None
    assert facts['solar_battery_home_efficiency']['value'] == .89
    assert facts['shared_ac_output_kw']['value'] == 11.5
    assert facts['discharge_kw']['value'] is None


def test_resolution_is_self_contained_after_catalog_update(monkeypatch):
    import src.equipment.ess as service
    saved=json.loads(json.dumps(ap()))
    changed=detail(AP);changed['catalog_revision']='future';changed['fields']['usable_energy_kwh']['value']=18
    monkeypatch.setattr(service,'CATALOG',[changed])
    assert validate_resolution(saved)==saved
    assert ap()['battery']['capacity_kWh']!=saved['battery']['capacity_kWh']
    saved['battery']['max_discharge_kw']=100
    with pytest.raises(ValueError,match='changed'): validate_resolution(saved)


def test_every_populated_fact_retains_source_and_revision():
    for record in search():
        assert record['catalog_revision']
        for fact in [record['architecture'],*record['fields'].values()]:
            assert fact['source_url'].startswith('https://')
            assert fact['document_revision'] and fact['section'] and fact['retrieved_on']
            assert fact['status'] in ('published','derived','assumed','user_overridden')
    assert len(search(manufacturer='Tesla'))==2


@pytest.mark.parametrize('change',[{'SOC_min':-.01},{'SOC_min':.8,'SOC_max':.2},{'SOC_max':1.1},{'energy_kWh':float('nan')},{'capacity_kWh':float('inf')},{'max_discharge_kw':True}])
def test_battery_validation(change):
    with pytest.raises(ValueError): Battery(**change)


def test_nonfinite_commands_preserve_state():
    b=Battery()
    for change in ({'charge_kw':float('nan'),'discharge_kw':0},{'charge_kw':0,'discharge_kw':0,'dt_hours':float('inf')}):
        with pytest.raises(ValueError): b.update_energy(**change)
        assert b.energy_kWh==10


def test_candidate_manual_and_equipment_contract():
    r=deepcopy(DEFAULT_CANDIDATE_REQUEST)
    validate_request(r)
    r['ess']=ap();r['battery']=r['ess']['battery']
    validate_request(r)
    r['battery']=deepcopy(r['battery']);r['battery']['max_charge_kw']=1
    with pytest.raises(ValueError,match='differ'): validate_request(r)


@pytest.mark.parametrize('energy,valid',[(-1e-7,True),(15.811388300841898+8.2e-8,True),(-.001,False),(15.82,False),(float('nan'),False),(float('inf'),False)])
def test_replay_energy_boundary_roundoff_only(monkeypatch,energy,valid):
    import pandas as pd
    from types import SimpleNamespace
    from src.opendss import opendss_analysis as module
    commands=[]
    monkeypatch.setattr(module,'dss',SimpleNamespace(Text=SimpleNamespace(Command=commands.append),Solution=SimpleNamespace(Solve=lambda:None)))
    row=pd.Series(dict(load_kw=5,pv_kw=0,battery_net_injection_kw=0,battery_soc_kWh=energy))
    if valid:
        module.apply_dispatch_operating_point(row,pv_rated_kw=0,battery_capacity_kWh=15.811388300841898)
        assert any('%stored=0.0 ' in x or '%stored=100.0 ' in x for x in commands)
    else:
        with pytest.raises(ValueError):module.apply_dispatch_operating_point(row,pv_rated_kw=0,battery_capacity_kWh=15.811388300841898)
        assert commands==[]
