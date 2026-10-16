"""Post-optimization AC validation of the PG&E export comparison schedules.

Billing uses the original dispatch. This adapter owns a separate copy and never
feeds OpenDSS PCC measurements or network losses back into tariff settlement.
"""
import numpy as np

from ..dispatch.battery import Battery
from .opendss_handoff import create_opendss_handoff
from .opendss_analysis import replay_dispatch_timeseries
from .residential_service import ResidentialService


SCENARIOS = {
    "grid_only": (False, False),
    "pv_self_consumption": (True, False),
    "pv_with_export": (True, False),
    "storage_self_consumption": (True, True),
    "storage_with_export": (True, True),
}
TOLERANCE = 1e-5  # Match the export optimizer's energy/power reconciliation.


def export_handoff(dispatch, *, battery=None):
    """Map interval-start energy and positive directional powers explicitly.

    ``solar_export.compare`` records energy.value[:-1]: START of each interval.
    OpenDSS receives that energy before each snapshot solve. End energy is only
    a diagnostic, calculated using the same AC-side efficiencies as dispatch.
    """
    columns = {
        "native_load_kw", "pv_available_kw", "pv_output_kw", "pv_curtailed_kw",
        "battery_charge_kw", "battery_discharge_kw", "grid_import_kw",
        "grid_export_kw", "energy_kWh",
    }
    missing = columns - set(dispatch.columns)
    if missing:
        raise ValueError(f"Export replay is missing columns: {sorted(missing)}")
    values = dispatch[sorted(columns)].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < -TOLERANCE).any():
        raise ValueError("Export replay requires finite nonnegative scheduled values.")
    if not np.allclose(dispatch.pv_output_kw + dispatch.pv_curtailed_kw,
                       dispatch.pv_available_kw, atol=TOLERANCE, rtol=0):
        raise ValueError("Export replay PV output and curtailment do not reconcile.")
    if not np.allclose(dispatch.grid_import_kw + dispatch.pv_output_kw + dispatch.battery_discharge_kw,
                       dispatch.native_load_kw + dispatch.battery_charge_kw + dispatch.grid_export_kw,
                       atol=TOLERANCE, rtol=0):
        raise ValueError("Export replay scheduled power balance does not reconcile.")

    mapped = dispatch.rename(columns={"native_load_kw": "load_kw", "pv_output_kw": "pv_kw",
                                      "energy_kWh": "battery_soc_kWh"}).copy()
    handoff = create_opendss_handoff(mapped, timestep_minutes=15,
                                   expected_timezone="America/Los_Angeles")
    # The shared handoff intentionally selects a small core schema. Retain
    # availability, curtailment and optional electrical inputs for this replay.
    for column in mapped:
        if column in ("pv_available_kw", "pv_curtailed_kw", "load_kvar", "load_power_factor") or (
            column.startswith("pv_") and column.endswith("_requested_kvar")
        ):
            handoff[column] = mapped[column]
    start = handoff.battery_soc_kWh.to_numpy()
    if battery is None:
        if (np.abs(dispatch[["battery_charge_kw", "battery_discharge_kw", "energy_kWh"]]) > TOLERANCE).any().any():
            raise ValueError("Export scenario without storage must have zero battery power and energy.")
        end = start.copy()
    else:
        end = start + .25 * (battery.charge_efficiency * handoff.battery_charge_kw.to_numpy()
                            - handoff.battery_discharge_kw.to_numpy() / battery.discharge_efficiency)
        if not np.allclose(end[:-1], start[1:], atol=TOLERANCE, rtol=0):
            raise ValueError("Export replay interval-start SOC does not reconcile with the next interval.")
        if (min(start.min(), end.min()) < battery.minimum_energy_kWh - TOLERANCE
                or max(start.max(), end.max()) > battery.maximum_energy_kWh + TOLERANCE):
            raise ValueError("Export replay SOC is outside the battery's configured limits.")
        if abs(start[0] - battery.energy_kWh) > TOLERANCE:
            raise ValueError("Export replay starting SOC differs from the configured initial energy.")
    handoff["battery_soc_start_kWh"] = start
    handoff["battery_soc_end_kWh"] = end
    return handoff


def replay_export_scenario(name, dispatch, *, battery, pv_capacity_kw, pv_replay=None,
                           residential_service=ResidentialService()):
    """Replay every 15-minute operating point with only the scenario's equipment."""
    if name not in SCENARIOS:
        raise ValueError(f"Unknown export replay scenario: {name}")
    has_pv, has_storage = SCENARIOS[name]
    if has_storage and battery is None:
        raise ValueError("Storage scenario requires configured battery equipment.")
    storage = Battery(**battery) if has_storage else None
    capacity = pv_capacity_kw if has_pv else 0.
    configuration = pv_replay if capacity > 0 else None
    handoff = export_handoff(dispatch, battery=storage)
    if capacity == 0 and (handoff[["pv_kw", "pv_available_kw"]].abs() > TOLERANCE).any().any():
        raise ValueError("Export scenario without PV equipment must have zero solar power.")
    if configuration is not None:
        available = [configuration.available_at(t).sum() for t in handoff.timestamp]
        if not np.allclose(available, handoff.pv_available_kw, atol=TOLERANCE, rtol=0):
            raise ValueError("Export replay inverter availability differs from dispatch availability.")
    ac = replay_dispatch_timeseries(handoff, battery=storage, pv_capacity_kw=capacity,
                                   pv_replay=configuration, residential_service=residential_service)
    # Keep directional scheduled flows alongside distinct measured PCC flows.
    # The shared replay's legacy 'scheduled_grid_import_kw' is signed NET power.
    for column in ("grid_import_kw", "grid_export_kw", "grid_net_import_kw",
                   "battery_charge_kw", "battery_discharge_kw", "pv_available_kw", "pv_curtailed_kw"):
        ac["scheduled_" + column] = handoff[column].to_numpy()
    for column in ("battery_soc_start_kWh", "battery_soc_end_kWh"):
        ac[column] = handoff[column].to_numpy()
    # Nonconverged electrical measurements are diagnostic only. Exclude them
    # from numerical extrema/energy totals; convergence and failure flags remain.
    measured = [c for c in ac if (c.endswith(("_pu", "_v", "_a", "_percent", "_kva", "_kw", "_kvar"))
                and not c.startswith("scheduled_") and c not in ("load_kw", "pv_kw", "battery_net_injection_kw"))]
    ac.loc[~ac.converged, measured] = np.nan
    return ac
