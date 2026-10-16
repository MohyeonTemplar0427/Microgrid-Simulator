"""Shared post-dispatch electrical checks for Pacific utility study adapters.

Copies and explicit column mappings keep circuit measurements separate from
the schedules, tariff bills, and credit ledgers supplied by each workflow.
"""
import json

import numpy as np
import pandas as pd


def scheduled_frame(dispatch, *, battery=None, timestep_minutes=15, timezone="America/Los_Angeles"):
    """Normalize the two existing dispatch contracts without changing either.

    Municipal energy_start_kwh and SoCal energy_kWh both mean interval START.
    Missing PV output is calculated from explicit meter/battery power balance,
    rather than replaying available PV that a non-export study curtailed.
    """
    from ..dispatch.battery import Battery
    from ..opendss.solar_export_replay import TOLERANCE

    frame = dispatch.rename(columns={"charge_kw": "battery_charge_kw",
        "discharge_kw": "battery_discharge_kw", "energy_start_kwh": "energy_kWh"}).copy()
    if not frame.columns.is_unique:
        raise ValueError("Electrical replay has ambiguous duplicate scheduled columns.")
    required = {"timestamp", "native_load_kw", "pv_available_kw", "grid_import_kw", "grid_export_kw"}
    if battery is not None:
        required |= {"battery_charge_kw", "battery_discharge_kw", "energy_kWh"}
    if required-set(frame):
        raise ValueError(f"Electrical replay is missing scheduled columns: {sorted(required-set(frame))}")
    stamps = [pd.Timestamp(t) for t in frame.timestamp]
    if any(pd.isna(t) or t.tzinfo is None for t in stamps):
        raise ValueError("Electrical replay requires timezone-aware scheduled timestamps.")
    frame["timestamp"] = pd.DatetimeIndex([t.tz_convert("UTC") for t in stamps]).tz_convert(timezone)
    if battery is None:
        for column in ("battery_charge_kw", "battery_discharge_kw", "energy_kWh"):
            if column not in frame:
                frame[column] = 0.
    if "pv_output_kw" not in frame:
        output = (frame.native_load_kw+frame.battery_charge_kw+frame.grid_export_kw
                  -frame.grid_import_kw-frame.battery_discharge_kw)
        # Cancellation can leave e.g. -1.8e-15 kW on a no-PV schedule. Keep
        # the original dispatch intact and project only boundary roundoff
        # within the shared power-balance tolerance; larger errors still fail.
        bounded = output.clip(lower=0.,upper=frame.pv_available_kw)
        frame["pv_output_kw"] = output.where(~np.isclose(output,bounded,atol=TOLERANCE,rtol=0),bounded)
    if "pv_curtailed_kw" not in frame:
        frame["pv_curtailed_kw"] = frame.pv_available_kw-frame.pv_output_kw
    if battery is not None:
        b = Battery(**battery)
        end = frame.energy_kWh+timestep_minutes/60*(b.charge_efficiency*frame.battery_charge_kw
                                   -frame.battery_discharge_kw/b.discharge_efficiency)
        if "energy_end_kwh" in frame and not np.allclose(end,frame.energy_end_kwh,atol=1e-5,rtol=0):
            raise ValueError("Electrical replay interval-end energy does not reconcile.")
        if abs(end.iloc[-1]-b.energy_kWh)>1e-5:
            raise ValueError("Electrical replay cyclic terminal SOC does not reconcile.")
    return frame


def reference_network(account):
    """Select a declared study circuit from service facts, never from a tariff.

    'Secondary' does not establish nominal volts or equipment ratings. Those
    values below remain explicit representative assumptions, not account facts.
    """
    from ..opendss.residential_service import ResidentialService

    voltage, phase = account.get("voltage"), account.get("phase")
    customer = account.get("customer_class")
    if (voltage != "secondary" or phase not in ("single", "three")
            or customer not in ("residential","commercial","industrial")
            or (customer=="residential" and phase=="three")):
        return None, None, (f"No matching representative circuit for service voltage={voltage!r}, "
                            f"phase={phase!r}, class={customer!r}. Primary/high-voltage, three-phase residential "
                            "or unspecified service is not evaluated.")
    if phase == "single":
        residential = account.get("customer_class") == "residential"
        service = (ResidentialService() if residential else ResidentialService(
            transformer_kva=75., service_amps=400.,
            conductor_r_ohm_per_km=.1, conductor_x_ohm_per_km=.05))
        metadata = service.metadata()
        if not residential:
            metadata["id"] = "single_phase_commercial_reference_v1"
            metadata["rating_basis"] = ("75 kVA transformer, 400 A service and conductor impedance are study assumptions; "
                "the EPRI 25 kVA example supplies topology and reused per-unit transformer impedances, not a 75 kVA equipment specification")
        metadata["description"] = service.description
    else:
        service = None  # Shared existing balanced three-phase circuit.
        metadata = dict(id="balanced_three_phase_480v_v1", description="Representative balanced 480 V three-phase service",
            primary_voltage_kv=12.47, secondary_voltage_v=480, transformer_kva=750.,
            transformer_winding_r_percent=[.5,.5], transformer_xhl_percent=5.75,
            service_length_km=.1, conductor_r1_ohm_per_km=.02, conductor_x1_ohm_per_km=.04,
            conductor_r0_ohm_per_km=.04, conductor_x0_ohm_per_km=.08, service_amps=800.,
            voltage_limits_pu=[.95,1.05], source="Existing shared OpenDSS three-phase reference circuit")
    metadata.update(account_service_voltage=voltage, account_phase=phase,
        representative_circuit=True, site_specific_validation=False,
        nominal_voltage_basis="Representative study assumption; secondary tariff classification does not establish nominal volts",
        load_power_factor=.95, load_reactive_basis="Constant lagging study assumption; monthly billing PF is not an interval measurement",
        scope="Representative circuit only; no site wiring, protection, transient or dynamic validation")
    return service, metadata, None


def replay_study(scenarios, account, *, progress=None, timestep_minutes=15, timezone="America/Los_Angeles"):
    """Return interval tables, comparison additions and a saved manifest.

    Each scenario supplies (scheduled frame, battery settings or None, AC PV kW).
    The same reference circuit is used for all scenarios. The existing export
    replay adapter supplies strict power/SOC checks and directional measurements.
    """
    from ..opendss.solar_export_replay import replay_export_scenario
    from ..opendss.qsts_analysis import create_qsts_scenario_comparison
    from .worker import summarize_ac_validation

    service, network, unsupported = reference_network(account)
    warnings = []
    if unsupported:
        rows = [{"scenario":name,"electrical_validation_status":"unsupported",
                 "all_intervals_feasible":None,"failed_intervals":None,
                 "electrical_measurements_complete":None} for name in scenarios]
        manifest = dict(status="unsupported",all_intervals_feasible=None,scenarios=[],
                        expected_scenarios=list(scenarios),reason=unsupported,network_configuration=None)
        warnings.append("Electrical network feasibility was not evaluated: "+unsupported)
        return [("ac-summary","Electrical validation · unsupported service",pd.DataFrame(rows))], rows, manifest, warnings

    replays = {}
    for name,(dispatch,battery,capacity) in scenarios.items():
        if progress:
            progress("Validating electrical feasibility: "+name.replace("_"," "))
        frame = scheduled_frame(dispatch,battery=battery,timestep_minutes=timestep_minutes,timezone=timezone)
        # Equipment choices are explicit, independent of the public label.
        alias = ("storage_with_export" if battery is not None else
                 "pv_with_export" if capacity>0 else "grid_only")
        replays[name] = replay_export_scenario(alias,frame,battery=battery,
            pv_capacity_kw=capacity,residential_service=service,timestep_minutes=timestep_minutes,timezone=timezone)
    # The legacy QSTS summarizer expects signed net scheduled grid power.
    summary = create_qsts_scenario_comparison({name:table.assign(
        scheduled_grid_import_kw=table.scheduled_grid_net_import_kw) for name,table in replays.items()},timestep_hours=timestep_minutes/60)
    summary = summary.rename(columns={"grid_import_energy_kWh":"replay_pcc_grid_import_energy_kWh",
        "grid_export_energy_kWh":"replay_pcc_grid_export_energy_kWh",
        "peak_grid_import_kw":"scheduled_peak_grid_net_import_kw",
        "minimum_grid_power_kw":"scheduled_minimum_grid_net_import_kw"})
    summary["failed_intervals"] = summary.interval_count-summary.feasible_intervals
    summary["all_intervals_feasible"] = summary.failed_intervals.eq(0)
    summary["electrical_measurements_complete"] = summary.converged_intervals.eq(summary.interval_count)
    summary["electrical_validation_status"] = "completed"
    # Partial or absent electrical measurements must not look like full-period energy.
    summary["network_loss_energy_kWh"] = [replays[name].network_real_loss_kw.sum(min_count=1)*timestep_minutes/60
                                        for name in summary.scenario]
    energy = [c for c in summary if c.endswith("energy_kWh")]
    summary.loc[~summary.electrical_measurements_complete,energy] = np.nan
    rows = json.loads(summary.to_json(orient="records",double_precision=15))
    manifest = summarize_ac_validation(replays)
    for item,stats in zip(manifest["scenarios"],rows):
        item.update(stats,interval_table="ac-"+item["scenario"])
        if item["failed_intervals"]:
            first = item["failure_samples"][0]
            warnings.append(f"{item['scenario']}: {item['failed_intervals']} intervals failed representative electrical checks. "
                            f"First failure {first['timestamp']}: {', '.join(first['reasons'])}. Billing still uses scheduled flows.")
    manifest.update(status="completed",method="OpenDSS quasi-static power flow",version=1,timestep_minutes=timestep_minutes,
        timezone=timezone,
        soc_convention="start_of_interval",billing_basis="original scheduled meter flows",
        network_configuration=network,inverter_model="AC constant P/Q; kVA equals AC kW, Q=0; externally dispatched storage")
    warnings.append(network["description"]+". Nominal volts, ratings, wiring and 0.95 lagging load PF are study assumptions; "
                    "replay does not change dispatch, bills or credit banks. Circuit losses and PCC measurements are separate diagnostics.")
    tables = [("ac-"+name,"Electrical validation · "+name,table) for name,table in replays.items()]
    tables.append(("ac-summary","Representative electrical validation",summary))
    return tables, rows, manifest, warnings
