"""Run an explicit local-file study: python -m src.profiles.residential study.json."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters import coarsen_profile, read_resstock_csv, read_noaa_global_hourly, read_benchmarks_csv
from .core import Provenance, ResidentialError, aggregate_population, calibrate
from .weather_model import WeatherResponseModel


def run_study(config_path, output_directory):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text())
    allowed = {"schema_version", "mode", "provenance", "profiles", "households",
               "timestep_minutes", "benchmarks_csv", "training_weather", "prediction_weather",
               "response_by_end_use", "heating_balance_c", "cooling_balance_c", "allow_extrapolation"}
    if set(config) - allowed or config.get("schema_version") != 1:
        raise ResidentialError("Unknown configuration fields or unsupported schema_version.")
    mode = config.get("mode")
    if mode not in {"published", "weather_response"}:
        raise ResidentialError("mode must be published or weather_response.")
    if not isinstance(config.get("allow_extrapolation", False), bool):
        raise ResidentialError("allow_extrapolation must be a JSON boolean.")
    if mode == "published" and any(k in config for k in (
            "training_weather", "prediction_weather", "response_by_end_use",
            "heating_balance_c", "cooling_balance_c", "allow_extrapolation")):
        raise ResidentialError("Published mode cannot apply weather-response settings.")
    provenance = Provenance(**config["provenance"])
    profiles, weights = [], []
    for member in config["profiles"]:
        spec = dict(member)
        path = config_path.parent / spec.pop("path")
        weights.append(spec.pop("weight"))
        profile = read_resstock_csv(path, provenance=provenance, **spec)
        if "timestep_minutes" in config:
            profile = coarsen_profile(profile, config["timestep_minutes"])
        profiles.append(profile)
    profile = aggregate_population(profiles, weights, households=config.get("households"))
    if "benchmarks_csv" in config:
        profile = calibrate(profile, read_benchmarks_csv(config_path.parent / config["benchmarks_csv"]))
    if mode == "weather_response":
        def weather(key):
            spec = dict(config[key])
            path = config_path.parent / spec.pop("path")
            return read_noaa_global_hourly(path, region=provenance.region, **spec)
        training = weather("training_weather")
        model = WeatherResponseModel.fit(profile, training,
            response_by_end_use=config["response_by_end_use"],
            heating_balance_c=config.get("heating_balance_c", 18),
            cooling_balance_c=config.get("cooling_balance_c", 22))
        profile = model.predict(weather("prediction_weather"),
            allow_extrapolation=config.get("allow_extrapolation", False))
    # No writes until the complete study has passed input and model validation.
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    profile.frame().to_csv(output / "residential_load.csv", index=False)
    (output / "manifest.json").write_text(json.dumps(profile.manifest(), indent=2, allow_nan=False) + "\n")
    return profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_study(args.config, args.output)
    except (ResidentialError, KeyError, TypeError, OSError, ValueError) as exc:
        parser.exit(2, f"Residential study rejected: {exc}\n")
    print(f"Wrote {len(result.end_uses_kw)} synthetic intervals to {args.output}")


if __name__ == "__main__":
    main()
