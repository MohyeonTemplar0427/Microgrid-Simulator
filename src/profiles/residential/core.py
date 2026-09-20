"""Gross electricity end uses on regular, interval-start grids.

No implicit geographic mapping, annualization, PV subtraction, or weather
replacement. Household weights represent dwelling units, not utility accounts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace

import numpy as np
import pandas as pd

from ..load_sources import LoadProfileSource, LoadSourceMode
from ...timeseries.interval_table import IntervalIndex


class ResidentialError(ValueError):
    pass


def finite_number(value, label, *, positive=False):
    try:
        value = float(value)
    except (ValueError, TypeError) as exc:
        raise ResidentialError(f"{label} must be numeric.") from exc
    if not np.isfinite(value) or value < 0 or (positive and value == 0):
        raise ResidentialError(f"{label} must be finite and {'positive' if positive else 'nonnegative'}.")
    return value


def regular_frame(frame, minutes):
    minutes = finite_number(minutes, "timestep_minutes", positive=True)
    result = frame.copy(deep=True)
    index = result.index
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None:
        raise ResidentialError("A timezone-aware DatetimeIndex is required.")
    if index.hasnans or index.has_duplicates or not index.is_monotonic_increasing:
        raise ResidentialError("Timestamps must be valid, unique, and increasing.")
    if len(index) == 0 or len(result.columns) == 0 or result.columns.has_duplicates:
        raise ResidentialError("A nonempty frame with unique columns is required.")
    if len(index) > 1 and not np.all(np.diff(index.asi8) == pd.Timedelta(minutes=minutes).value):
        raise ResidentialError("Missing or irregular intervals; implicit filling is forbidden.")
    try:
        result = result.astype(float)
    except (ValueError, TypeError) as exc:
        raise ResidentialError("All values must be numeric.") from exc
    if not np.isfinite(result.to_numpy()).all():
        raise ResidentialError("All values must be finite; missing data must be resolved explicitly.")
    return result


@dataclass(frozen=True)
class Provenance:
    region: str
    release: str
    weather_id: str
    source: str
    timezone: str
    weather_kind: str = "actual"

    def __post_init__(self):
        if any(not isinstance(v, str) or not v.strip() for v in asdict(self).values()):
            raise ResidentialError("Provenance fields must be nonempty strings.")
        if self.weather_kind not in {"actual", "typical"}:
            raise ResidentialError("weather_kind must be actual or typical.")
        try:
            pd.Timestamp("2020-01-01", tz=self.timezone)
        except Exception as exc:
            raise ResidentialError("Invalid schedule timezone.") from exc


@dataclass
class ResidentialProfile:
    end_uses_kw: pd.DataFrame
    timestep_minutes: int
    provenance: Provenance
    households: float = 1.0
    method: str = "published_resstock"
    diagnostics: dict = field(default_factory=dict)

    def __post_init__(self):
        self.end_uses_kw = regular_frame(self.end_uses_kw, self.timestep_minutes)
        if any(not isinstance(c, str) or not c or c in {"timestamp", "native_load_kw"}
               for c in self.end_uses_kw.columns):
            raise ResidentialError("End uses need distinct names, excluding timestamp/native_load_kw.")
        if (self.end_uses_kw.to_numpy() < 0).any():
            raise ResidentialError("Gross end-use loads cannot be negative.")
        self.households = finite_number(self.households, "households", positive=True)

    @property
    def native_load_kw(self):
        return self.end_uses_kw.sum(axis=1).rename("native_load_kw")

    @property
    def end(self):
        return self.end_uses_kw.index[-1] + pd.Timedelta(minutes=self.timestep_minutes)

    def energy_kwh(self):
        return self.end_uses_kw.sum() * self.timestep_minutes / 60

    def frame(self):
        frame = self.end_uses_kw.copy()
        frame["native_load_kw"] = self.native_load_kw
        return frame.rename_axis("timestamp").reset_index()

    def manifest(self):
        return dict(schema_version=1, is_synthetic=True, basis="gross_electricity",
                    method=self.method, provenance=asdict(self.provenance),
                    households=self.households, timestep_minutes=self.timestep_minutes,
                    start=self.end_uses_kw.index[0].isoformat(), end_exclusive=self.end.isoformat(),
                    energy_kwh=self.energy_kwh().to_dict(), diagnostics=self.diagnostics)


def aggregate_population(profiles, weights, *, households=None):
    """Weights are represented dwelling counts; optionally normalize to a community.

    Every input must represent one dwelling on the same actual-weather grid.
    Large-area TMY aggregation is intentionally unsupported.
    """
    profiles, weights = list(profiles), list(weights)
    if not profiles or len(profiles) != len(weights):
        raise ResidentialError("Supply one population weight per profile.")
    weights = np.array([finite_number(w, "weight") for w in weights])
    if weights.sum() == 0:
        raise ResidentialError("Population weights cannot all be zero.")
    first = profiles[0]
    for profile in profiles:
        if profile.households != 1:
            raise ResidentialError("Population inputs must each represent one dwelling.")
        if (profile.provenance.region != first.provenance.region
                or profile.provenance.release != first.provenance.release
                or profile.provenance.timezone != first.provenance.timezone
                or profile.provenance.weather_id != first.provenance.weather_id
                or profile.provenance.weather_kind != "actual"
                or profile.timestep_minutes != first.timestep_minutes
                or not profile.end_uses_kw.index.equals(first.end_uses_kw.index)
                or set(profile.end_uses_kw) != set(first.end_uses_kw)):
            raise ResidentialError("Population profiles need matching region, release, actual weather, grid and end uses.")
    count = weights.sum() if households is None else finite_number(households, "households", positive=True)
    weights = weights * count / weights.sum()
    values = sum(p.end_uses_kw * w for p, w in zip(profiles, weights))
    return ResidentialProfile(values, first.timestep_minutes, first.provenance, count,
                              "weighted_population", {"weights": weights.tolist(),
                              "members": [p.manifest() for p in profiles]})


@dataclass(frozen=True)
class EnergyBenchmark:
    """A normalized EIA/local energy target for a matched population and period."""
    region: str
    start: str
    end: str
    end_use: str
    kwh_per_household: float
    source: str
    basis: str = "gross_electricity"


def calibrate(profile, benchmarks):
    """End-use energy scaling only; does not validate shape or infer stock weights."""
    benchmarks = list(benchmarks)
    values = profile.end_uses_kw.copy()
    factors, seen = {}, set()
    for target in benchmarks:
        if target.end_use in seen:
            raise ResidentialError("Duplicate benchmark end use.")
        seen.add(target.end_use)
        if target.region != profile.provenance.region or target.basis != "gross_electricity":
            raise ResidentialError("Benchmark region/basis must match gross household consumption.")
        start, end = pd.Timestamp(target.start), pd.Timestamp(target.end)
        if (start.tz is None or end.tz is None or start != values.index[0] or end != profile.end):
            raise ResidentialError("Benchmark period must exactly match the profile; no implicit annualization.")
        if not target.source or target.end_use not in values:
            raise ResidentialError("Benchmark needs a source and a known, disjoint end use.")
        goal = finite_number(target.kwh_per_household, "benchmark kWh") * profile.households
        energy = float(profile.energy_kwh()[target.end_use])
        if energy == 0 and goal > 0:
            raise ResidentialError("Cannot create an absent end use by scaling a zero profile.")
        factor = goal / energy if energy else 1.0
        values[target.end_use] *= factor
        factors[target.end_use] = factor
    return replace(profile, end_uses_kw=values, diagnostics={**profile.diagnostics,
                   "calibration": {"factors": factors, "benchmarks": [asdict(b) for b in benchmarks],
                                   "shape_validated": False}})


def compare_profiles(predicted, reference):
    """Held-out aggregate metrics; reference can be a measured gross-load series."""
    if not predicted.native_load_kw.index.equals(reference.index):
        raise ResidentialError("Validation requires exactly aligned timestamps.")
    actual = regular_frame(reference.to_frame("actual"), predicted.timestep_minutes)["actual"]
    if (actual < 0).any():
        raise ResidentialError("Validation reference must be gross nonnegative load.")
    error = predicted.native_load_kw - actual
    return dict(rmse_kw=float(np.sqrt(np.mean(error ** 2))),
                mae_kw=float(np.mean(np.abs(error))),
                energy_bias_kwh=float(error.sum() * predicted.timestep_minutes / 60),
                peak_bias_kw=float(predicted.native_load_kw.max() - actual.max()))


@dataclass
class ResidentialLoad(LoadProfileSource):
    """Opt-in adapter for existing dispatch code. Never registered in the UI."""
    profile: ResidentialProfile
    mode = LoadSourceMode.SYNTHETIC
    is_synthetic = True

    def build_load_kw(self, interval_index: IntervalIndex):
        # Exact resolution prevents interpolation from inventing demand peaks.
        if interval_index.timestep_minutes != self.profile.timestep_minutes:
            raise ResidentialError("Load and analysis resolution must match explicitly.")
        values = self.profile.native_load_kw.reindex(interval_index.index)
        if values.isna().any():
            raise ResidentialError("Published/generated profile does not cover the requested horizon.")
        return pd.Series(values.to_numpy(), name="native_load_kw")

    def describe(self):
        return f"Residential {self.profile.method}: {self.profile.provenance.region} (SYNTHETIC DATA)"
