"""Offline adapters for documented source exports; no inferred units or geography."""
from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from .core import ResidentialError, ResidentialProfile, EnergyBenchmark
from .weather_model import TemperatureWeather


def _timestamps(values, timezone):
    # Inspect each offset before converting: utc=True alone silently treats
    # naive local-standard-time ResStock timestamps as UTC.
    try:
        stamps = [pd.Timestamp(v) for v in values]
        if any(pd.isna(t) for t in stamps):
            raise ValueError("Missing timestamp")
        naive = [t.tz is None for t in stamps]
        if all(naive):
            if not timezone:
                raise ResidentialError("Naive source timestamps require explicit source_timezone.")
            return pd.DatetimeIndex(stamps).tz_localize(timezone, ambiguous="raise", nonexistent="raise").tz_convert("UTC")
        if any(naive):
            raise ResidentialError("Mixed naive and aware timestamps are ambiguous.")
        return pd.DatetimeIndex(pd.to_datetime(stamps, utc=True))
    except (TypeError, ValueError) as exc:
        raise ResidentialError(f"Invalid source timestamps: {exc}") from exc


def _fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_resstock_csv(path, *, provenance, end_use_columns, timestep_minutes,
                      unit, timestamp_convention, timestamp_column="timestamp",
                      source_timezone=None, total_column=None, rounding_tolerance_kw=1e-6):
    """Map disjoint electricity columns in one dwelling's exported CSV.

    end_use_columns maps canonical names to raw columns. kWh means energy per
    interval; kW means interval-average power. A total column checks closure
    and exposes unassigned consumption as `unallocated`, never double-counts it.
    Without a total, the caller's mapping must be exhaustive and is unverified.
    Source timestamps may use a fixed-offset zone for local standard time.
    """
    if unit not in {"kWh", "kW"} or timestamp_convention not in {"start", "end"}:
        raise ResidentialError("Explicit unit (kWh/kW) and timestamp_convention (start/end) required.")
    if not end_use_columns or len(set(end_use_columns.values())) != len(end_use_columns):
        raise ResidentialError("End-use mappings must be nonempty and disjoint.")
    if total_column in end_use_columns.values() or "unallocated" in end_use_columns:
        raise ResidentialError("Total cannot be an end use; unallocated is reserved for closure.")
    if not np.isfinite(rounding_tolerance_kw) or rounding_tolerance_kw < 0:
        raise ResidentialError("Rounding tolerance must be finite and nonnegative.")
    raw = pd.read_csv(path)
    required = {timestamp_column, *end_use_columns.values()}
    if total_column:
        required.add(total_column)
    if not required <= set(raw):
        raise ResidentialError(f"Missing source columns: {sorted(required - set(raw))}")
    if not np.isfinite(timestep_minutes) or timestep_minutes <= 0:
        raise ResidentialError("timestep_minutes must be positive.")
    index = _timestamps(raw[timestamp_column], source_timezone)
    if timestamp_convention == "end":
        index -= pd.Timedelta(minutes=timestep_minutes)
    factor = 60 / timestep_minutes if unit == "kWh" else 1
    rounding_adjustment_kwh = 0.0
    try:
        frame = pd.DataFrame({name: pd.to_numeric(raw[column], errors="raise").to_numpy() * factor
                              for name, column in end_use_columns.items()}, index=index)
        if not np.isfinite(frame.to_numpy()).all() or (frame.to_numpy() < 0).any():
            raise ResidentialError("End uses must be finite and nonnegative before closure adjustment.")
        if total_column:
            total = pd.to_numeric(raw[total_column], errors="raise").to_numpy() * factor
            residual = total - frame.sum(axis=1).to_numpy()
            if not np.isfinite(total).all() or (total < 0).any() or (residual < -rounding_tolerance_kw).any():
                raise ResidentialError("End uses exceed total or total is invalid; check overlapping mappings and units.")
            # Reconcile only bounded negative rounding residuals, proportionally
            # across mapped components. The gross total remains authoritative.
            negative = residual < 0
            rounding_adjustment_kwh = float(-residual[negative].sum() * timestep_minutes / 60)
            sums = frame.sum(axis=1).to_numpy()
            frame.loc[negative] = frame.loc[negative].mul(total[negative] / sums[negative], axis=0)
            frame["unallocated"] = np.maximum(residual, 0)
    except (TypeError, ValueError) as exc:
        raise ResidentialError(str(exc)) from exc
    return ResidentialProfile(frame, timestep_minutes, provenance, diagnostics={
        "input_sha256": _fingerprint(path), "end_use_columns": dict(end_use_columns),
        "input_unit": unit, "timestamp_convention": timestamp_convention,
        "source_timezone": source_timezone, "total_column": total_column,
        "total_closure_checked": total_column is not None,
        "rounding_tolerance_kw": rounding_tolerance_kw,
        "rounding_adjustment_kwh": rounding_adjustment_kwh,
    })


def coarsen_profile(profile, timestep_minutes):
    """Explicit energy-conserving averaging; reject partial coarse intervals."""
    old = profile.timestep_minutes
    if timestep_minutes < old or timestep_minutes % old:
        raise ResidentialError("Coarse timestep must be an integer multiple of the input timestep.")
    rule = f"{timestep_minutes}min"
    frame = profile.end_uses_kw.tz_convert("UTC")
    groups = frame.resample(rule, origin="epoch")
    if (groups.size() != timestep_minutes // old).any():
        raise ResidentialError("Coarsening requires complete, aligned intervals.")
    return replace(profile, end_uses_kw=groups.mean(), timestep_minutes=timestep_minutes,
                   diagnostics={**profile.diagnostics, "coarsened_from_minutes": old})


def read_noaa_global_hourly(path, *, station, region, weather_id,
                            accepted_quality=("1", "5"), start=None, end=None):
    """Read NOAA Global Hourly DATE/STATION/TMP CSV, temperature only.

    DATE is UTC; TMP is signed tenths of Celsius followed by a quality flag.
    Default accepts passed-quality values (1/5). Repeated reports at the same
    instant are averaged before hourly averaging. No absent hour is filled.
    One explicit station is required; representativeness is a caller decision.
    """
    raw = pd.read_csv(path, dtype=str)
    if not {"DATE", "STATION", "TMP"} <= set(raw):
        raise ResidentialError("NOAA input needs DATE, STATION and TMP columns.")
    raw = raw.loc[raw.STATION == str(station)].copy()
    if raw.empty:
        raise ResidentialError("Selected NOAA station has no observations.")
    timestamps = _timestamps(raw.DATE, "UTC")
    if (start is None) != (end is None):
        raise ResidentialError("Supply both start and exclusive end for a NOAA study window.")
    if start is not None:
        start, end = pd.Timestamp(start), pd.Timestamp(end)
        if (start.tz is None or end.tz is None or end <= start
                or start != start.floor("h") or end != end.floor("h")):
            raise ResidentialError("NOAA window must be timezone-aware, hour-aligned and increasing.")
        keep = (timestamps >= start) & (timestamps < end)
        raw = raw.loc[keep].copy()
        timestamps = timestamps[keep]
        if raw.empty:
            raise ResidentialError("No NOAA observations in requested window.")
    parts = raw.TMP.str.split(",", expand=True)
    if parts.shape[1] != 2:
        raise ResidentialError("NOAA TMP must contain value,quality.")
    temperature = pd.to_numeric(parts[0], errors="coerce") / 10
    accepted = (parts[1].isin(accepted_quality) & temperature.between(-95, 65)).to_numpy()
    series = pd.Series(temperature.to_numpy()[accepted], index=timestamps[accepted])
    if series.empty:
        raise ResidentialError("No temperature observations pass NOAA quality screening.")
    hourly = series.groupby(level=0).mean().resample("1h").mean().to_frame("temperature_c")
    expected = (pd.date_range(start, end, freq="1h", inclusive="left").tz_convert("UTC")
                if start is not None else
                pd.date_range(timestamps.min().floor("h"), timestamps.max().floor("h"), freq="1h"))
    hourly = hourly.reindex(expected)
    return TemperatureWeather(hourly, 60, region, weather_id, str(path), diagnostics={
        "station": str(station), "accepted_quality": list(accepted_quality),
        "rejected_observations": int((~accepted).sum()), "input_sha256": _fingerprint(path),
        "window_start": None if start is None else start.isoformat(),
        "window_end_exclusive": None if end is None else end.isoformat(),
        "aggregation": "mean of accepted observations per UTC hour; not a time-weighted integral",
    })


def read_benchmarks_csv(path):
    """Read explicitly normalized RECS/local targets, not arbitrary EIA workbooks.

    Required columns match EnergyBenchmark fields (basis may be omitted).
    kwh_per_household uses ALL represented dwellings, not only equipment users.
    """
    frame = pd.read_csv(path, keep_default_na=False)
    required = {"region", "start", "end", "end_use", "kwh_per_household", "source"}
    if frame.empty or not required <= set(frame) or set(frame) - required - {"basis"}:
        raise ResidentialError("Benchmark CSV must contain only the documented normalized columns.")
    return [EnergyBenchmark(**row) for row in frame.to_dict("records")]
