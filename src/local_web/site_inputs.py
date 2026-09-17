"""Adapt location, weather and existing profile models to browser studies.

Physics stays in src/profiles. This module owns application wiring only.
"""

from dataclasses import asdict
from datetime import date
import hashlib
import json
import os
from pathlib import Path

from .contract import NSRDB_YEARS, number

NSRDB_URL = "https://developer.nlr.gov/api/nsrdb/v2/solar/nsrdb-GOES-conus-v4-0-0-download.csv"


def location_suggestion(latitude, longitude):
    """A locality hint, NOT a service-territory or account lookup."""
    number(latitude, "Latitude", -90, 90)
    number(longitude, "Longitude", -180, 180)
    if 37.70 <= latitude <= 37.84 and -122.53 <= longitude <= -122.35:
        return {"utility": "pge", "timezone": "America/Los_Angeles", "message":
            "San Francisco area: PG&E delivery is a candidate. CleanPowerSF, Hetch Hetchy, and other service arrangements also exist. Confirm your account before selecting a bundled tariff."}
    return {"utility": None, "timezone": None, "message":
        "No automatic utility or timezone assignment is available here. Enter the site's timezone and confirm its electricity service; location search is not a service-territory lookup."}


def resolve_location(query, search=None):
    from ..simulation.geocoding import LocationSearch
    location = (search or LocationSearch()).search(query)
    return {**asdict(location), "suggestion": location_suggestion(location.latitude, location.longitude)}


def validate_weather_request(request):
    if not isinstance(request, dict) or set(request) != {"latitude", "longitude", "year", "timezone", "timestep_minutes"}:
        raise ValueError("Supply location, year, timezone, and interval for weather retrieval.")
    number(request["latitude"], "Latitude", -90, 90)
    number(request["longitude"], "Longitude", -180, 180)
    if type(request["year"]) is not int or request["year"] not in NSRDB_YEARS:
        raise ValueError("Historical CONUS weather is available for 2018–2025. Choose a past year or use a clear-sky estimate.")
    if type(request["timestep_minutes"]) is not int or request["timestep_minutes"] not in (5, 15, 30, 60):
        raise ValueError("Choose a 5, 15, 30, or 60 minute weather interval.")
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    try:
        ZoneInfo(request["timezone"])
    except (TypeError, ValueError, ZoneInfoNotFoundError):
        raise ValueError("Enter a valid IANA timezone for weather retrieval.") from None
    return request


def nsrdb_fetcher(request, api_key, email):
    """Reuse the GUI adapter with the provider's current official endpoint."""
    from pvlib.iotools import get_nsrdb_psm4_conus
    from ..profiles.nsrdb import NSRDB_PARAMETERS
    return get_nsrdb_psm4_conus(
        latitude=request.latitude, longitude=request.longitude, api_key=api_key,
        email=email, year=request.year, time_step=request.time_step_minutes,
        parameters=list(NSRDB_PARAMETERS), leap_day=True, map_variables=True,
        url=NSRDB_URL, timeout=120,
    )


def retrieve_weather(directory, request, fetcher=None):
    from ..profiles.nsrdb import NSRDBRequest, fetch_nsrdb_weather, save_weather_csv
    from .worker import write_json
    validate_weather_request(request)
    api_key, email = os.getenv("NSRDB_API_KEY"), os.getenv("NSRDB_API_EMAIL")
    if not api_key or not email:
        raise ValueError("NSRDB credentials are missing. Start the server with --env-file pointing to your existing src/.env, or set NSRDB_API_KEY and NSRDB_API_EMAIL in its environment.")
    weather = fetch_nsrdb_weather(NSRDBRequest(
        latitude=request["latitude"], longitude=request["longitude"],
        year=request["year"], timezone=request["timezone"],
        time_step_minutes=request["timestep_minutes"],
    ), api_key=api_key, email=email, fetcher=fetcher or nsrdb_fetcher)
    path = Path(directory) / "weather.csv"
    save_weather_csv(weather.frame, path)
    metadata = {"request": request, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "row_count": len(weather.frame), "provenance": weather.provenance,
                "warnings": list(weather.warnings), "provider_url": NSRDB_URL}
    write_json(Path(directory) / "weather.json", metadata)
    return metadata


def check_weather_matches(request, metadata):
    source = metadata["request"]
    expected = {"latitude": request["site"]["latitude"], "longitude": request["site"]["longitude"],
                "timezone": request["timezone"], "timestep_minutes": request["timestep_minutes"],
                "year": date.fromisoformat(request["start_date"]).year}
    if source != expected or date.fromisoformat(request["end_date"]).year != expected["year"]:
        raise ValueError("Saved weather does not match the site, year, timezone, or interval. Retrieve matching weather; historical years are never shifted onto other study dates.")


def build_site_inputs(request, directory):
    import pandas as pd
    from pvlib.location import Location
    from ..timeseries import build_interval_index_from_days
    from ..profiles import ConstantLoad, SyntheticLoad, BuildingArchetype, LoadScaling, WeatherDerivedPV, WeatherDerivedPVConfiguration
    from ..profiles.weather import load_weather_csv
    from ..opendss.ac_replay import PVInverterReplay, PVReplayConfiguration
    from ..billing import get_tariff

    site, solar, load = request["site"], request["solar"], request["load"]
    count = (date.fromisoformat(request["end_date"]) - date.fromisoformat(request["start_date"])).days + 1
    grid = build_interval_index_from_days(request["start_date"], count, request["timezone"], request["timestep_minutes"])
    warnings = []
    if request["weather_source"] == "nsrdb":
        metadata = json.loads((directory / "weather.json").read_text())
        check_weather_matches(request, metadata)
        if hashlib.sha256((directory / "weather.csv").read_bytes()).hexdigest() != metadata["sha256"]:
            raise ValueError("Saved weather checksum changed; refusing to use modified input.")
        weather = load_weather_csv(directory / "weather.csv")
        provenance = {**metadata["provenance"], "saved_weather_sha256": metadata["sha256"]}
        warnings.extend(metadata["warnings"])
        source_name = "NSRDB historical satellite weather"
    else:
        midpoints = grid.index + pd.Timedelta(minutes=request["timestep_minutes"] / 2)
        location = Location(site["latitude"], site["longitude"], tz=request["timezone"])
        irradiance = location.get_clearsky(midpoints, model="ineichen")
        weather = pd.DataFrame({"timestamp": grid.index,
            "ghi_w_per_m2": irradiance.ghi.to_numpy(), "dni_w_per_m2": irradiance.dni.to_numpy(),
            "dhi_w_per_m2": irradiance.dhi.to_numpy(), "temperature_c": solar["temperature_c"],
            "wind_speed_m_per_s": solar["wind_speed_m_per_s"]})
        source_name = "Clear-sky estimate (not observed weather or a forecast)"
        provenance = {"source": "pvlib_ineichen_clear_sky", "latitude": site["latitude"],
            "longitude": site["longitude"], "altitude_m": float(location.altitude),
            "temperature_c_assumed": solar["temperature_c"], "wind_speed_m_per_s_assumed": solar["wind_speed_m_per_s"],
            "irradiance_sampling": "interval midpoint", "timezone": request["timezone"]}
        warnings.append(f"Clear-sky irradiance ignores actual clouds. Air temperature is assumed {solar['temperature_c']:g} °C and wind {solar['wind_speed_m_per_s']:g} m/s throughout; this is not a weather forecast.")
    pv = WeatherDerivedPV(WeatherDerivedPVConfiguration(
        latitude=site["latitude"], longitude=site["longitude"], rated_pv_capacity_kw=solar["dc_capacity_kw"],
        inverter_ac_capacity_kw=request["pv_capacity_kw"], tilt_degrees=solar["tilt_degrees"],
        azimuth_degrees=solar["azimuth_degrees"], system_losses_fraction=solar["system_losses_fraction"],
        nominal_inverter_efficiency=solar["inverter_efficiency"],
    ), weather_data=weather, weather_source=source_name).build_detailed(grid)
    warnings.extend(pv.warnings)
    if load["mode"] == "constant":
        values = ConstantLoad(load["power_kw"]).build_load_kw(grid)
        warnings.append("Building demand is the user-specified constant load; it is not estimated from location or weather.")
    else:
        values = SyntheticLoad(archetype=BuildingArchetype(load["archetype"]), scaling=LoadScaling.PEAK_KW,
                               peak_kw=load["power_kw"], variability_fraction=0, random_seed=20260101).build_load_kw(grid)
        warnings.append("Building load uses the existing synthetic daily archetype. It is not measured demand and does not model weather-driven HVAC response.")
    prices = request["fixed_price_per_kWh"]
    if request["tariff_id"]:
        tariff = get_tariff(request["tariff_id"], grid.index[0].date())
        if not tariff.is_effective_on(grid.index[-1].date()):
            raise ValueError("The selected tariff does not cover the study dates. Select supported dates or use an explicit flat energy-price assumption.")
        prices = tariff.energy_rates(grid.index).to_numpy()
    else:
        warnings.append("Energy price is a user assumption; no utility tariff bill is calculated.")
    warnings.append("Grid carbon intensity is a constant user assumption, not location-retrieved emissions data.")
    warnings.append("PV replay assumes inverter kVA equals its AC kW rating and Q = 0; it is steady-state grid-following validation.")
    frame = pd.DataFrame({"timestamp": grid.index, "load_kw": values.to_numpy(),
        "pv_kw": pv.pv_available_kw.to_numpy(), "price_per_kWh": prices,
        "gCO2/kWh": request["carbon_intensity_g_per_kWh"]})
    replay = PVReplayConfiguration((PVInverterReplay("RooftopPV", request["pv_capacity_kw"], request["pv_capacity_kw"]),),
                                   pd.DataFrame({"RooftopPV": pv.pv_available_kw.to_numpy()}, index=grid.index))
    weather_table = weather.copy()
    weather_table["timestamp"] = pd.to_datetime(weather_table["timestamp"], utc=True)
    weather_table = weather_table.loc[weather_table.timestamp.isin(grid.index)].reset_index(drop=True)
    return frame, replay, {"weather": weather_table, "pv": pv.diagnostics}, {
        "site": site, "weather": provenance, "pv": pv.provenance, "load": load,
        "price_source": "tariff" if request["tariff_id"] else "fixed_assumption",
        "warnings": warnings,
    }
