"""Open-Meteo ERA5 hourly reanalysis, explicitly converted to interval starts."""
import hashlib
import json
import numpy as np
import pandas as pd

URL = "https://archive-api.open-meteo.com/v1/archive"
VARIABLES = {"shortwave_radiation": ("ghi_w_per_m2", "W/m²"),
             "direct_normal_irradiance": ("dni_w_per_m2", "W/m²"),
             "diffuse_radiation": ("dhi_w_per_m2", "W/m²"),
             "temperature_2m": ("temperature_c", "°C"),
             "wind_speed_10m": ("wind_speed_m_per_s", "m/s")}


def parse_era5(text, interval_index, latitude, longitude):
    raw = json.loads(text)
    if raw.get("utc_offset_seconds") != 0 or raw.get("timezone") not in ("GMT", "UTC"):
        raise ValueError("ERA5 input must explicitly be UTC.")
    if abs(raw["latitude"]-latitude) > .26 or abs(raw["longitude"]-longitude) > .26:
        raise ValueError("ERA5 grid cell does not match the requested site.")
    times = pd.to_datetime(raw["hourly"]["time"], utc=True, errors="raise")
    if times.has_duplicates or not times.is_monotonic_increasing or not (np.diff(times.asi8) == pd.Timedelta(hours=1).value).all():
        raise ValueError("Historical weather must contain ordered, complete hourly records.")
    columns = {}
    for key, (column, unit) in VARIABLES.items():
        if raw["hourly_units"].get(key) != unit:
            raise ValueError("Unexpected ERA5 units for "+key)
        columns[column] = raw["hourly"][key]
    # Radiation is the mean of the PREVIOUS hour. Meteorological endpoint
    # samples approximate that hour's conditions; this is disclosed below.
    hourly = pd.DataFrame(columns, index=times-pd.Timedelta(hours=1))
    targets = interval_index.index.tz_convert("UTC").floor("h")
    if not targets.isin(hourly.index).all():
        raise ValueError("Historical weather does not cover the entire requested period.")
    weather = hourly.loc[targets].reset_index(drop=True)
    if not np.isfinite(weather.to_numpy(dtype=float)).all():
        raise ValueError("Missing historical weather; no gap filling.")
    weather.insert(0, "timestamp", interval_index.index)
    minutes = interval_index.timestep_hours*60
    provenance = {"source": "ERA5 hourly reanalysis via Open-Meteo", "source_url": URL,
                  "raw_sha256": hashlib.sha256(text.encode()).hexdigest(), "requested_coordinates": [latitude, longitude],
                  "grid_coordinates": [raw["latitude"], raw["longitude"]], "native_interval_minutes": 60,
                  "sampling": f"Previous-hour radiation means shifted to interval starts and held over {60/minutes:g} {minutes:g}-minute intervals; endpoint meteorology approximates that hour. Not on-site observations.",
                  "license": "CC BY 4.0 attribution; hosted free API is for noncommercial use",
                  "attribution": "Open-Meteo and Copernicus Climate Change Service ERA5"}
    return weather, provenance


def fetch_era5(start_date, end_date, latitude, longitude, getter=None, *, local_timezone="America/New_York"):
    import requests
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    # Preserve the historical default for existing callers. New regional
    # workflows supply their configured clock; the provider request and raw
    # records remain UTC, with a full end date for previous-hour means.
    ZoneInfo(local_timezone)
    start = pd.Timestamp(start_date, tz=local_timezone).tz_convert("UTC")
    end = (pd.Timestamp(end_date, tz=local_timezone)+pd.DateOffset(days=1)).tz_convert("UTC")
    params = {"latitude": latitude, "longitude": longitude, "start_date": start.strftime("%Y-%m-%d"),
              "end_date": end.strftime("%Y-%m-%d"), "hourly": ",".join(VARIABLES),
              "timezone": "UTC", "wind_speed_unit": "ms", "models": "era5"}
    response = (getter or requests.get)(URL, params=params, timeout=60)
    response.raise_for_status()
    return {"provider": "open_meteo_era5", "raw_json": response.text,
            "request": params, "retrieved_at": datetime.now(timezone.utc).isoformat()}
