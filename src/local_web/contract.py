"""Versioned, JSON-safe study requests shared by application adapters."""

from datetime import date
import re
from copy import deepcopy
import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from ..billing.services import SERVICES, validate_service_pairing

SCENARIOS = ("no_battery", "rule_based", "cost_optimal", "carbon_optimal", "combined_optimal")
DEFAULT_REQUEST = {
    "schema_version": 1,
    "name": "Small business study",
    "dataset_id": "",
    "start_date": "2026-08-01",
    "end_date": "2026-08-01",
    "timezone": "America/Los_Angeles",
    "timestep_minutes": 15,
    "strategies": list(SCENARIOS),
    "carbon_weight": 0.2,
    "degradation_cost_per_kWh": 0.03,
    "tariff_id": None,
    "pv_capacity_kw": 50.0,
    "battery": {
        "capacity_kWh": 100.0, "energy_kWh": 50.0,
        "max_charge_kw": 30.0, "max_discharge_kw": 30.0,
        "SOC_min": 0.2, "SOC_max": 0.8,
        "charge_efficiency": 0.95, "discharge_efficiency": 0.95,
    },
}

DEFAULT_SITE_REQUEST = {**deepcopy(DEFAULT_REQUEST),
    "schema_version": 2, "name": "San Francisco solar study",
    "site": {"label": "San Francisco, California", "latitude": 37.7749,
             "longitude": -122.4194, "utility": "unconfirmed"},
    "weather_source": "clear_sky", "weather_id": None,
    "solar": {"dc_capacity_kw": 60.0, "tilt_degrees": 20.0, "azimuth_degrees": 180.0,
              "system_losses_fraction": 0.14, "inverter_efficiency": 0.96,
              "temperature_c": 20.0, "wind_speed_m_per_s": 1.0},
    "load": {"mode": "constant", "power_kw": 60.0, "archetype": "office"},
    "fixed_price_per_kWh": 0.25, "carbon_intensity_g_per_kWh": 300.0,
}
del DEFAULT_SITE_REQUEST["dataset_id"]
DEFAULT_CANDIDATE_REQUEST = {**deepcopy(DEFAULT_SITE_REQUEST), "schema_version": 3, "ess": None, "solar_optimization": None}
NSRDB_YEARS = tuple(range(2018, 2026))  # Provider's published CONUS years, verified 2026-09-16.


def identifier(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def validate_site_fields(data):
    site, solar, load = data["site"], data["solar"], data["load"]
    for value, template, label in ((site, DEFAULT_SITE_REQUEST["site"], "site"),
                                   (solar, DEFAULT_SITE_REQUEST["solar"], "solar"),
                                   (load, DEFAULT_SITE_REQUEST["load"], "load")):
        if not isinstance(value, dict) or set(value) != set(template):
            raise ValueError(f"Supply all supported {label} settings.")
    if not isinstance(site["label"], str) or not 1 <= len(site["label"]) <= 500:
        raise ValueError("Provide a site description.")
    number(site["latitude"], "Latitude", -90, 90)
    number(site["longitude"], "Longitude", -180, 180)
    if not isinstance(site["utility"], str) or (site["utility"] not in ("unconfirmed", "other", *(s["id"] for s in SERVICES)) and not re.fullmatch(r"cec:(distribution|other):[0-9]+", site["utility"])):
        raise ValueError("Choose a supported utility selection.")
    if data["tariff_id"]:
        validate_service_pairing(data["tariff_id"], site["utility"])
    if data["weather_source"] not in ("clear_sky", "nsrdb"):
        raise ValueError("Choose clear-sky estimates or historical NSRDB weather.")
    if data["weather_source"] == "nsrdb":
        if not identifier(data["weather_id"]):
            raise ValueError("Retrieve historical weather for the selected location and year before running.")
    elif data["weather_id"] is not None:
        raise ValueError("Clear-sky studies must not reference historical weather.")
    number(solar["dc_capacity_kw"], "PV DC capacity")
    number(solar["tilt_degrees"], "Tilt", 0, 90)
    number(solar["azimuth_degrees"], "Azimuth", 0, 359.999999)
    number(solar["system_losses_fraction"], "System losses", 0, 0.999999)
    number(solar["inverter_efficiency"], "PV inverter efficiency", 0.000001, 1)
    number(solar["temperature_c"], "Assumed air temperature", -95, 65)
    number(solar["wind_speed_m_per_s"], "Assumed wind speed", 0, 120)
    if data["pv_capacity_kw"] <= 0:
        raise ValueError("PV inverter AC rating must be positive.")
    if load["mode"] not in ("constant", "synthetic") or load["archetype"] not in ("office", "retail", "school", "multifamily", "industrial", "residential"):
        raise ValueError("Choose a supported load model and archetype.")
    number(load["power_kw"], "Load power", 0.000001)
    number(data["fixed_price_per_kWh"], "Assumed electricity price")
    number(data["carbon_intensity_g_per_kWh"], "Assumed grid carbon intensity")


def number(value, label, minimum=0, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{label} must be a number.")
    if not math.isfinite(value) or value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"{label} is outside the allowed range.")
    return float(value)


def validate_request(data):
    """Reject unknown fields and unsupported versions rather than dropping inputs."""
    if isinstance(data, dict) and type(data.get("schema_version")) is int and data["schema_version"] == 6:
        from .socal_study import validate
        return validate(data)
    if isinstance(data, dict) and type(data.get("schema_version")) is int and data["schema_version"] == 5:
        from .grid_only import validate
        return validate(data)
    if isinstance(data, dict) and type(data.get("schema_version")) is int and data["schema_version"] == 4:
        from .municipal_study import validate_study
        return validate_study(data)
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] not in (1, 2, 3):
        raise ValueError("Unsupported study schema version; this application accepts versions 1, 2 and 3.")
    template = {1: DEFAULT_REQUEST, 2: DEFAULT_SITE_REQUEST, 3: DEFAULT_CANDIDATE_REQUEST}[data["schema_version"]]
    optional = {"site_profile", "carbon", "solar_export", "pv_battery_connection", "include_degradation_in_optimization"}
    if set(data) - optional != set(template) or (data["schema_version"] == 1 and ((optional - {"include_degradation_in_optimization"}) & set(data))):
        raise ValueError(f"Supply exactly the fields in the version {data['schema_version']} study request.")
    if type(data.get("include_degradation_in_optimization", False)) is not bool:
        raise ValueError("Choose whether battery degradation is included in optimization.")
    if "pv_battery_connection" in data and data["pv_battery_connection"] != "ac_coupled":
        raise ValueError("Only AC-coupled PV and battery operation is currently modeled.")
    if not isinstance(data["name"], str) or not 1 <= len(data["name"].strip()) <= 120:
        raise ValueError("Study name must contain 1–120 characters.")
    if data["schema_version"] == 1 and not identifier(data["dataset_id"]):
        raise ValueError("Choose a validated dataset.")
    try:
        start, end = date.fromisoformat(data["start_date"]), date.fromisoformat(data["end_date"])
        ZoneInfo(data["timezone"])
    except (ValueError, TypeError, ZoneInfoNotFoundError) as exc:
        raise ValueError("Use valid dates and an IANA timezone, such as America/Los_Angeles.") from exc
    if not 0 <= (end - start).days <= 365:
        raise ValueError("Choose an inclusive study horizon of 1–366 days.")
    if type(data["timestep_minutes"]) is not int or data["timestep_minutes"] not in (5, 15, 30, 60):
        raise ValueError("Choose a 5, 15, 30, or 60 minute interval.")
    strategies = data["strategies"]
    if not isinstance(strategies, list) or not all(isinstance(s, str) for s in strategies):
        raise ValueError("Strategies must be a list of names.")
    if ("no_battery" not in strategies or len(set(strategies)) != len(strategies)
            or set(strategies) - set(SCENARIOS)):
        raise ValueError("Select supported strategies once each, including the no-battery baseline.")
    if data["tariff_id"] is not None and not isinstance(data["tariff_id"], str):
        raise ValueError("Tariff must be a supported identifier or null.")
    if data["tariff_id"]:
        from ..billing import get_tariff
        tariff = get_tariff(data["tariff_id"])
        if not tariff.is_effective_on(start) or not tariff.is_effective_on(end):
            raise ValueError(
                f"Billing Plan coverage is {tariff.effective_start} through "
                f"{tariff.effective_end or 'the current catalog window'}; "
                f"it does not cover {start} through {end}. "
                "Choose a verified version covering the entire study."
            )
    if data["tariff_id"] and data["tariff_id"].startswith("hetch_hetchy_c2"):
        from ..billing import get_tariff
        get_tariff(data["tariff_id"]).validate_demand_interval(data["timestep_minutes"])
    for key in ("carbon_weight", "degradation_cost_per_kWh", "pv_capacity_kw"):
        number(data[key], key)
    battery = data["battery"]
    if not isinstance(battery, dict) or set(battery) != set(DEFAULT_REQUEST["battery"]):
        raise ValueError("Supply all eight battery settings.")
    for key, value in battery.items():
        number(value, key)
    if not 0 <= battery["SOC_min"] < battery["SOC_max"] <= 1:
        raise ValueError("Battery SOC bounds must satisfy 0 ≤ minimum < maximum ≤ 1.")
    for key in ("capacity_kWh", "max_charge_kw", "max_discharge_kw"):
        if battery[key] <= 0:
            raise ValueError(f"{key} must be positive.")
    for key in ("charge_efficiency", "discharge_efficiency"):
        if not 0 < battery[key] <= 1:
            raise ValueError(f"{key} must be greater than zero and at most one.")
    if not battery["capacity_kWh"] * battery["SOC_min"] <= battery["energy_kWh"] <= battery["capacity_kWh"] * battery["SOC_max"]:
        raise ValueError("Initial battery energy must be within the SOC bounds.")
    if data["schema_version"] >= 2:
        validate_site_fields(data)
    if data["schema_version"] == 3:
        if data["ess"] is not None:
            from ..equipment.ess import validate_resolution
            resolved = validate_resolution(data["ess"])
            if data["battery"] != resolved["battery"]:
                raise ValueError("Battery fields differ from reviewed ESS resolution; resolve again or use manual mode.")
        if data["solar_optimization"] is not None:
            result = data["solar_optimization"]
            if not isinstance(result, dict) or result.get("scope") != "full_historical_calendar_year":
                raise ValueError("Invalid annual solar optimization provenance.")
            for key in ("tilt_degrees", "azimuth_degrees"):
                if type(result.get(key)) is not int or result[key] != data["solar"][key]:
                    raise ValueError("Optimized angles changed; clear optimization provenance for manual settings.")
    from .site_profile import validate_profile_request
    validate_profile_request(data)
    from .carbon import validate as validate_carbon
    validate_carbon(data)
    if "solar_export" in data:
        from .export_study import validate as validate_export
        validate_export(data)
    return data
