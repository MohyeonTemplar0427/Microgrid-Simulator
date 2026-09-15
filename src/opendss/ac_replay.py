"""AC terminal replay: pvlib owns production; OpenDSS owns network physics.

The default connection is the representative balanced 480 V circuit. CEC
Paco provides kW, not kVA or installation wiring. Callers must explicitly
supply measured/nameplate kVA and connection details to replace assumptions.
"""
from dataclasses import dataclass
import math
import re

import numpy as np
import pandas as pd
import opendssdirect as dss


@dataclass(frozen=True)
class PVInverterReplay:
    name: str
    rated_ac_kw: float
    rated_kva: float
    bus: str = "load_bus.1.2.3"
    phases: int = 3
    voltage_kv: float = 0.48
    connection: str = "wye"

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", self.name):
            raise ValueError("Inverter name must be a safe OpenDSS identifier.")
        if not all(math.isfinite(v) and v > 0 for v in
                   (self.rated_ac_kw, self.rated_kva, self.voltage_kv)):
            raise ValueError("Inverter AC ratings and voltage must be finite and positive.")
        if self.rated_ac_kw > self.rated_kva:
            raise ValueError("Inverter kW rating cannot exceed its kVA rating.")
        if self.phases not in (1, 3) or self.connection not in ("wye", "delta"):
            raise ValueError("Unsupported inverter phase count or connection.")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[0-9]+)+", self.bus):
            raise ValueError("Inverter bus must include explicit node numbers.")


@dataclass(eq=False)
class PVReplayConfiguration:
    inverters: tuple[PVInverterReplay, ...]
    # Timestamp-indexed AC availability, one column per physical inverter.
    available_power_kw: pd.DataFrame

    def __post_init__(self):
        names = [item.name for item in self.inverters]
        if not names or len(set(n.lower() for n in names)) != len(names):
            raise ValueError("PV replay needs uniquely named physical inverters.")
        frame = self.available_power_kw.copy()
        if set(frame.columns) != set(names) or not frame.columns.is_unique:
            raise ValueError("PV availability columns must match physical inverters.")
        if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
            raise ValueError("PV availability must use timezone-aware timestamps.")
        if frame.empty or frame.index.hasnans or not frame.index.is_unique:
            raise ValueError("PV availability needs nonempty, unique valid timestamps.")
        for item in self.inverters:
            values = frame[item.name].to_numpy(dtype=float)
            if (not np.isfinite(values).all() or (values < 0).any()
                    or (values > item.rated_ac_kw + 1e-6).any()):
                raise ValueError(f"Invalid AC availability for inverter {item.name}.")
        self.available_power_kw = frame.astype(float)

    @property
    def rated_ac_kw(self):
        return sum(item.rated_ac_kw for item in self.inverters)

    def available_at(self, timestamp):
        timestamp = pd.Timestamp(timestamp)
        if timestamp.tz is None or timestamp not in self.available_power_kw.index:
            raise ValueError(f"Missing inverter availability at {timestamp}.")
        return self.available_power_kw.loc[timestamp]


def replay_inverters(pv_capacity_kw, configuration=None):
    if configuration is not None:
        return configuration.inverters
    if not math.isfinite(pv_capacity_kw) or pv_capacity_kw < 0:
        raise ValueError("PV capacity must be finite and nonnegative.")
    return (() if pv_capacity_kw == 0 else
            (PVInverterReplay("RooftopPV", pv_capacity_kw, pv_capacity_kw),))


def add_ac_inverters(inverters):
    for item in inverters:
        # Model 1 delivers specified P/Q. No second solar/efficiency model.
        # Outside its voltage range OpenDSS changes behavior; terminal errors
        # below expose that instead of claiming successful setpoint tracking.
        if item.bus.split(".")[0].lower() not in dss.Circuit.AllBusNames():
            raise ValueError(f"Inverter bus does not exist: {item.bus}.")
        dss.Text.Command(
            f"New Generator.{item.name} bus1={item.bus} phases={item.phases} "
            f"conn={item.connection} kv={item.voltage_kv} "
            f"kVA={item.rated_kva} kW=0 kvar=0 model=1 "
            "Vminpu=0.9 Vmaxpu=1.1 status=fixed"
        )


def inverter_setpoints(row, inverters, configuration=None):
    requested = float(row["pv_kw"])
    if configuration is not None:
        available = configuration.available_at(row["timestamp"])
    else:
        # Legacy inputs already supply an AC schedule, not a weather envelope.
        value = float(row.get("pv_available_kw", requested))
        rating = sum(item.rated_ac_kw for item in inverters)
        if not math.isfinite(value) or value < 0 or value > rating + 1e-6:
            raise ValueError("PV AC availability exceeds its rating or is invalid.")
        available = pd.Series({item.name: value for item in inverters}, dtype=float)
    total = float(available.sum())
    if not math.isfinite(requested) or requested < 0 or requested > total + 1e-6:
        raise ValueError("PV requested AC power exceeds available power or is invalid.")
    fraction = min(requested / total, 1.0) if total else 0.0
    points = []
    for item in inverters:
        p = float(available[item.name]) * fraction
        q = float(row.get(f"pv_{item.name}_requested_kvar", 0.0))
        if not math.isfinite(q) or math.hypot(p, q) > item.rated_kva + 1e-6:
            raise ValueError(f"Inverter {item.name} P/Q exceeds its kVA capability.")
        points.append((item, float(available[item.name]), p, q))
    return points


def terminal_power(element):
    if dss.Circuit.SetActiveElement(element) <= 0:
        raise RuntimeError(f"OpenDSS element was not found: {element}.")
    values = dss.CktElement.Powers()[:2 * dss.CktElement.NumConductors()]
    return sum(values[::2]), sum(values[1::2])


def replay_measurements(row, points, tolerance_kw=0.01):
    load_p, load_q = terminal_power("Load.Building")
    requested_load = float(row["load_kw"])
    requested_q = load_reactive_power(row)
    battery_p, _ = terminal_power("Storage.Battery")
    result = {
        "load_requested_kvar": requested_q,
        "load_actual_kw": load_p, "load_actual_kvar": load_q,
        "load_error_kw": load_p - requested_load,
        "load_error_kvar": load_q - requested_q,
        "battery_actual_injection_kw": -battery_p,
        "battery_error_kw": -battery_p - float(row["battery_net_injection_kw"]),
    }
    mismatch = any(not math.isfinite(result[key]) or abs(result[key]) > tolerance_kw for key in
                   ("load_error_kw", "load_error_kvar", "battery_error_kw"))
    actual_p = actual_q = 0.0
    capability_violation = False
    for item, available, p, q in points:
        terminal_p, terminal_q = terminal_power(f"Generator.{item.name}")
        delivered_p, delivered_q = -terminal_p, -terminal_q
        apparent = math.hypot(delivered_p, delivered_q)
        prefix = f"pv_{item.name}_"
        result.update({prefix + "rated_ac_kw": item.rated_ac_kw,
                       prefix + "rated_kva": item.rated_kva,
                       prefix + "available_kw": available,
                       prefix + "requested_kw": p, prefix + "requested_kvar": q,
                       prefix + "actual_kw": delivered_p, prefix + "actual_kvar": delivered_q,
                       prefix + "error_kw": delivered_p - p,
                       prefix + "error_kvar": delivered_q - q,
                       prefix + "loading_percent": apparent / item.rated_kva * 100})
        mismatch |= (not math.isfinite(delivered_p) or not math.isfinite(delivered_q)
                     or abs(delivered_p - p) > tolerance_kw or abs(delivered_q - q) > tolerance_kw)
        capability_violation |= apparent > item.rated_kva + tolerance_kw
        actual_p += delivered_p
        actual_q += delivered_q
    result.update(pv_actual_kw=actual_p, pv_actual_kvar=actual_q,
                  pv_error_kw=actual_p - float(row["pv_kw"]),
                  setpoint_mismatch=bool(mismatch),
                  inverter_capability_violation=bool(capability_violation))
    return result


def load_reactive_power(row):
    if "load_kvar" in row:
        value = float(row["load_kvar"])
    else:
        pf = float(row.get("load_power_factor", 0.95))
        if not math.isfinite(pf) or not 0 < pf <= 1:
            raise ValueError("Load power factor must be in (0, 1].")
        value = float(row["load_kw"]) * math.tan(math.acos(pf))
    if not math.isfinite(value):
        raise ValueError("Load reactive power must be finite.")
    return value
