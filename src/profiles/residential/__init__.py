"""Opt-in residential modeling backend; no browser registration or defaults."""

from .core import (
    ResidentialError, Provenance, ResidentialProfile, EnergyBenchmark,
    ResidentialLoad, aggregate_population, calibrate, compare_profiles,
)
from .adapters import coarsen_profile, read_resstock_csv, read_noaa_global_hourly, read_benchmarks_csv
from .weather_model import TemperatureWeather, WeatherResponseModel

__all__ = [
    "ResidentialError", "Provenance", "ResidentialProfile", "EnergyBenchmark",
    "ResidentialLoad", "aggregate_population", "calibrate", "compare_profiles",
    "coarsen_profile", "read_resstock_csv", "read_noaa_global_hourly", "read_benchmarks_csv",
    "TemperatureWeather", "WeatherResponseModel",
]
