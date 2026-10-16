"""Shared physical replay, explicit adapters, and failure/unsupported reporting."""
import opendssdirect as dss
import pandas as pd
import pytest

from src.local_web.electrical_replay import replay_study, scheduled_frame

BATTERY = dict(capacity_kWh=10,energy_kWh=5,SOC_min=.2,SOC_max=.8,
               max_charge_kw=3,max_discharge_kw=3,charge_efficiency=.95,discharge_efficiency=.95)


def schedule(start="2026-07-06 12:00", *, load=2., pv=0., imports=None):
    return pd.DataFrame(dict(timestamp=pd.date_range(start,periods=4,freq="15min",tz="America/Los_Angeles"),
        native_load_kw=load,pv_available_kw=pv,grid_import_kw=load if imports is None else imports,grid_export_kw=0.))


def account(phase="single",customer_class="residential",voltage="secondary"):
    return dict(phase=phase,customer_class=customer_class,voltage=voltage)


@pytest.mark.parametrize("phase,customer,network,kva",[
    ("single","residential","residential_split_phase_v1",25),
    ("single","commercial","single_phase_commercial_reference_v1",75),
    ("three","commercial","balanced_three_phase_480v_v1",750),
])
def test_network_selection_absent_equipment_and_measurements(phase,customer,network,kva):
    frame=schedule();before=frame.copy(deep=True)
    tables,rows,manifest,warnings=replay_study({"grid_only":(frame,None,0.)},account(phase,customer))
    ac=tables[0][2]
    assert manifest["status"]=="completed" and manifest["all_intervals_feasible"]
    assert manifest["network_configuration"]["id"]==network
    assert manifest["network_configuration"]["transformer_kva"]==kva
    assert ac.converged.all() and ac.feasible.all()
    assert ac.pcc_balance_error_kw.abs().max()<.01
    assert ac.network_real_loss_kw.gt(0).all()
    assert not dss.Storages.AllNames() and not dss.Generators.AllNames()
    assert rows[0]["replay_pcc_grid_import_energy_kWh"]>2.
    assert "grid_import_energy_kWh" not in rows[0]
    assert any("study assumptions" in w for w in warnings)
    pd.testing.assert_frame_equal(frame,before)


def test_implicit_nonexport_pv_output_preserves_curtailment_and_rating():
    frame=schedule(pv=5.,imports=.5);before=frame.copy(deep=True)
    tables,_,_,_=replay_study({"pv_only":(frame,None,5.)},account())
    ac=tables[0][2]
    assert ac.pv_actual_kw.to_numpy()==pytest.approx([1.5]*4,abs=.01)
    assert ac.scheduled_pv_curtailed_kw.eq(3.5).all()
    assert ac.scheduled_grid_import_kw.eq(.5).all()
    assert ac.scheduled_grid_export_kw.eq(0).all()
    assert not dss.Storages.AllNames() and dss.Generators.AllNames()
    pd.testing.assert_frame_equal(frame,before)


@pytest.mark.parametrize("residual",[-1e-12,1e-12])
def test_no_pv_balance_roundoff_does_not_create_a_generator(residual):
    frame=schedule(imports=2.+residual).assign(charge_kw=0.,discharge_kw=0.,
        energy_start_kwh=5.,energy_end_kwh=5.)
    before=frame.copy(deep=True)
    tables,_,manifest,_=replay_study({"cost_optimal":(frame,BATTERY,0.)},account())
    assert manifest["all_intervals_feasible"]
    assert tables[0][2].pv_kw.eq(0).all()
    assert tables[0][2].scheduled_pv_curtailed_kw.eq(0).all()
    assert not dss.Generators.AllNames()
    pd.testing.assert_frame_equal(frame,before)


def test_inferred_pv_does_not_hide_a_material_power_balance_error():
    with pytest.raises(ValueError,match="nonnegative"):
        replay_study({"grid_only":(schedule(imports=2.01),None,0.)},account())


def test_explicit_output_exports_and_municipal_soc_aliases_are_respected():
    frame=schedule(load=2.,pv=6.,imports=0.)
    frame["grid_export_kw"]=1.
    frame["pv_output_kw"]=3.;frame["pv_curtailed_kw"]=3.
    ac=replay_study({"pv_only":(frame,None,6.)},account())[0][0][2]
    assert ac.pv_actual_kw.to_numpy()==pytest.approx([3.]*4,abs=.01)
    assert ac.scheduled_grid_export_kw.eq(1).all() and ac.reverse_power_flow.all()
    stored=schedule(imports=[4.,.195,2.,2.]).assign(charge_kw=[2.,0,0,0],discharge_kw=[0,1.805,0,0],
        energy_start_kwh=[5.,5.475,5.,5.],energy_end_kwh=[5.475,5.,5.,5.])
    before=stored.copy(deep=True)
    tables,rows,manifest,_=replay_study({"cost_optimal":(stored,BATTERY,0.)},account())
    ac=tables[0][2]
    assert ac.battery_soc_start_kWh.tolist()==pytest.approx([5.,5.475,5.,5.])
    assert ac.battery_soc_end_kWh.tolist()==pytest.approx([5.475,5.,5.,5.])
    assert ac.battery_actual_injection_kw.tolist()==pytest.approx([-2.,1.805,0,0],abs=.01)
    assert manifest["all_intervals_feasible"] and dss.Storages.AllNames()
    assert not dss.Generators.AllNames()
    pd.testing.assert_frame_equal(stored,before)
    stored.loc[0,"energy_end_kwh"]+=.1
    with pytest.raises(ValueError,match="interval-end"):
        scheduled_frame(stored,battery=BATTERY)


@pytest.mark.parametrize("start",["2026-03-08 01:45-08:00","2026-11-01 01:45-07:00"])
def test_dst_uses_exact_instants(start):
    frame=schedule();frame.timestamp=pd.date_range(start,periods=4,freq="15min")
    ac=replay_study({"grid_only":(frame,None,0.)},account())[0][0][2]
    assert ac.timestamp.tolist()==frame.timestamp.tolist()
    frame.timestamp=frame.timestamp.dt.tz_localize(None)
    with pytest.raises(ValueError,match="timezone-aware"):
        replay_study({"grid_only":(frame,None,0.)},account())


@pytest.mark.parametrize("voltage,phase",[("primary_12kv","three"),("ladwp_4.8kv","three"),
    ("ladwp_34.5kv","three"),("secondary",None),(None,"single")])
def test_unsupported_service_never_becomes_a_passing_circuit(monkeypatch,voltage,phase):
    from src.opendss import solar_export_replay
    def forbidden(*args,**kwargs):raise AssertionError("No fabricated circuit")
    monkeypatch.setattr(solar_export_replay,"replay_export_scenario",forbidden)
    tables,rows,manifest,warnings=replay_study({"grid_only":(schedule(),None,0.)},account(phase,voltage=voltage))
    assert manifest["status"]=="unsupported" and manifest["all_intervals_feasible"] is None
    assert manifest["scenarios"]==[] and rows[0]["failed_intervals"] is None
    assert [t[0] for t in tables]==["ac-summary"]
    assert warnings and rows[0]["electrical_validation_status"]=="unsupported"


def test_electrical_failure_is_a_completed_check_with_a_trace():
    tables,rows,manifest,warnings=replay_study({"grid_only":(schedule(load=60.),None,0.)},account())
    assert manifest["status"]=="completed" and not manifest["all_intervals_feasible"]
    assert rows[0]["failed_intervals"]==4 and rows[0]["maximum_transformer_loading_percent"]>100
    assert manifest["scenarios"][0]["failure_samples"][0]["reasons"]
    assert any("failed representative" in w for w in warnings)


def test_three_phase_individual_residence_is_not_silently_mapped_to_480v():
    _,rows,manifest,_=replay_study({"grid_only":(schedule(),None,0.)},account("three"))
    assert manifest["status"]=="unsupported" and rows[0]["all_intervals_feasible"] is None


def test_failed_solves_do_not_report_zero_loss_or_complete_energy(monkeypatch):
    from src.opendss import opendss_analysis
    original=opendss_analysis.apply_dispatch_operating_point
    def fail(*args,**kwargs):
        original(*args,**kwargs);dss.Solution.Converged(False)
    monkeypatch.setattr(opendss_analysis,"apply_dispatch_operating_point",fail)
    tables,rows,manifest,_=replay_study({"grid_only":(schedule(),None,0.)},account())
    assert manifest["status"]=="completed" and not manifest["all_intervals_feasible"]
    assert rows[0]["converged_intervals"]==0 and rows[0]["failed_intervals"]==4
    assert rows[0]["network_loss_energy_kWh"] is None
    assert rows[0]["replay_pcc_grid_import_energy_kWh"] is None
    assert tables[0][2].network_real_loss_kw.isna().all()
