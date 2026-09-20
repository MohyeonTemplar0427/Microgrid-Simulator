"""Interpretable weather-response surrogate, not an EnergyPlus/ResStock rerun.

For each component: nonnegative weekday/weekend hourly intercepts plus one
nonnegative heating OR cooling degree slope. Other components use schedules.
Temperature effects are identified from variation WITHIN schedule buckets.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd

from .core import ResidentialError, ResidentialProfile, regular_frame


@dataclass
class TemperatureWeather:
    frame: pd.DataFrame
    timestep_minutes: int
    region: str
    weather_id: str
    source: str
    diagnostics: dict = field(default_factory=dict)

    def __post_init__(self):
        if set(self.frame.columns) != {"temperature_c"}:
            raise ResidentialError("Temperature weather requires exactly temperature_c.")
        self.frame = regular_frame(self.frame, self.timestep_minutes)
        if not self.frame.temperature_c.between(-95, 65).all():
            raise ResidentialError("Weather temperature outside plausible Celsius range.")
        if not all(isinstance(v, str) and v.strip() for v in (self.region, self.weather_id, self.source)):
            raise ResidentialError("Weather region, weather_id and source are required.")


def _buckets(index, timezone):
    local = index.tz_convert(timezone)
    return local.hour.to_numpy() + 24 * (local.dayofweek.to_numpy() >= 5)


def _degree(temperature, kind, balance):
    if kind == "cooling":
        return np.maximum(temperature - balance, 0)
    if kind == "heating":
        return np.maximum(balance - temperature, 0)
    return np.zeros(len(temperature))


def _fit_nonnegative(x, y, buckets):
    counts = np.bincount(buckets, minlength=48)
    means_x = np.bincount(buckets, weights=x, minlength=48) / counts
    means_y = np.bincount(buckets, weights=y, minlength=48) / counts
    centered = x - means_x[buckets]
    if np.dot(centered, centered) < 1e-8:
        raise ResidentialError("Weather response is unidentifiable: insufficient within-hour temperature variation.")
    # Coordinate minimization of a convex two-block nonnegative least-squares
    # problem. Closed-form updates need no new numerical dependency.
    slope = max(0.0, float(np.dot(centered, y - means_y[buckets]) / np.dot(centered, centered)))
    for _ in range(10000):
        intercept = np.maximum(means_y - slope * means_x, 0)
        updated = max(0.0, float(np.dot(x, y - intercept[buckets]) / np.dot(x, x)))
        if abs(updated - slope) < 1e-10 * (1 + abs(slope)):
            slope = updated
            return np.maximum(means_y - slope * means_x, 0), slope
        slope = updated
    raise ResidentialError("Weather fit did not converge; revise training data or component mapping.")


@dataclass
class WeatherResponseModel:
    training_profile: ResidentialProfile
    coefficients: dict
    temperature_range_c: tuple[float, float]
    training_weather: dict

    @classmethod
    def fit(cls, profile, weather, *, response_by_end_use, heating_balance_c=18.0,
            cooling_balance_c=22.0):
        """Explicitly classify every end use as heating, cooling or schedule.

        Balance temperatures are study assumptions, not universal thresholds.
        Caller should select/validate them with held-out historical data.
        """
        if (profile.provenance.region != weather.region
                or profile.provenance.weather_id != weather.weather_id
                or profile.provenance.weather_kind != "actual"
                or profile.timestep_minutes != weather.timestep_minutes
                or not profile.end_uses_kw.index.equals(weather.frame.index)):
            raise ResidentialError("Training load and actual weather must match region, weather_id and interval grid.")
        if set(response_by_end_use) != set(profile.end_uses_kw):
            raise ResidentialError("Classify every end use explicitly, including unallocated if present.")
        if set(response_by_end_use.values()) - {"heating", "cooling", "schedule"}:
            raise ResidentialError("Response must be heating, cooling or schedule.")
        if not (-95 <= heating_balance_c <= cooling_balance_c <= 65):
            raise ResidentialError("Balance temperatures must be ordered and in Celsius range.")
        buckets = _buckets(profile.end_uses_kw.index, profile.provenance.timezone)
        if len(np.unique(buckets)) != 48:
            raise ResidentialError("Training must cover all weekday/weekend hours.")
        temperatures = weather.frame.temperature_c.to_numpy()
        coefficients = {}
        for name, kind in response_by_end_use.items():
            y = profile.end_uses_kw[name].to_numpy()
            balance = heating_balance_c if kind == "heating" else cooling_balance_c
            x = _degree(temperatures, kind, balance)
            if kind == "schedule" or not y.any():
                intercept = np.bincount(buckets, weights=y, minlength=48) / np.bincount(buckets, minlength=48)
                slope = 0.0
            else:
                intercept, slope = _fit_nonnegative(x, y, buckets)
            fitted = intercept[buckets] + slope * x
            coefficients[name] = dict(response=kind, balance_c=float(balance),
                intercept_kw=intercept.tolist(), slope_kw_per_c=slope,
                training_rmse_kw=float(np.sqrt(np.mean((fitted - y) ** 2))))
        return cls(profile, coefficients, (float(temperatures.min()), float(temperatures.max())),
                   dict(source=weather.source, weather_id=weather.weather_id, **weather.diagnostics))

    def predict(self, weather, *, allow_extrapolation=False):
        if weather.region != self.training_profile.provenance.region:
            raise ResidentialError("Prediction weather region must match the trained population.")
        if weather.timestep_minutes != self.training_profile.timestep_minutes:
            raise ResidentialError("Prediction resolution must match training resolution.")
        temp = weather.frame.temperature_c.to_numpy()
        low, high = self.temperature_range_c
        outside = (temp < low) | (temp > high)
        if outside.any() and not allow_extrapolation:
            raise ResidentialError("Temperature outside training range; explicitly allow_extrapolation to study it.")
        buckets = _buckets(weather.frame.index, self.training_profile.provenance.timezone)
        columns = {}
        for name, c in self.coefficients.items():
            columns[name] = (np.array(c["intercept_kw"])[buckets]
                             + c["slope_kw_per_c"] * _degree(temp, c["response"], c["balance_c"]))
        provenance = replace(self.training_profile.provenance, weather_id=weather.weather_id,
                             source=f"weather surrogate from {self.training_profile.provenance.source}")
        return ResidentialProfile(pd.DataFrame(columns, index=weather.frame.index),
            weather.timestep_minutes, provenance, self.training_profile.households,
            "weather_response_surrogate", diagnostics={
                "training_profile": self.training_profile.manifest(),
                "training_weather": self.training_weather,
                "prediction_weather": dict(source=weather.source, **weather.diagnostics),
                "coefficients": self.coefficients, "temperature_range_c": [low, high],
                "extrapolated_intervals": int(outside.sum()), "held_out_validated": False,
                "limitations": ["Temperature-only response; no humidity, thermal lag or equipment saturation.",
                                "Fixed population and equipment; no automatic adoption/growth trend.",
                                "Deterministic hourly schedules; not individual appliance event simulation."]})
