"""Optional PJM consumption accounting, separate from billing and dispatch.

Keep the provider's interval provenance, rather than passing through the legacy
two-column signal converter. Provider-returned 15-minute resolution is not a
claim of independently measured 15-minute generator emissions.
"""
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
import pandas as pd

ZONE = "US-MIDA-PJM"
NOTE = (
    "Electricity Maps PJM regional-average consumption intensity (US-MIDA-PJM), "
    "including interregional flows, with lifecycle emission factors. This is a "
    "regional accounting proxy, not a site measurement, utility/supplier product "
    "mix or marginal emissions signal. Grid imports only; exports receive no "
    "emissions credit. Differences from the grid reference are accounting "
    "differences, not proven avoided emissions. Carbon does not change bill "
    "optimization. PV/battery equipment lifecycle emissions are not assessed."
)
API_URL = "https://api.electricitymaps.com/v4/carbon-intensity/past-range"
METHOD_URL = "https://www.electricitymaps.com/data/methodology"
FIELDS = ("datetime", "carbonIntensity", "zone", "emissionFactorType",
          "flowTraced", "isEstimated", "estimationMethod", "createdAt", "updatedAt")


def validate(request):
    spec = request.get("carbon")
    if spec is None:
        return
    if not isinstance(spec, dict) or spec != {"source": "electricity_maps", "region": ZONE}:
        raise ValueError("Choose verified Electricity Maps PJM regional-average carbon or disable carbon.")
    from ..billing.regional import UTILITIES
    utility = request.get("site", {}).get("utility")
    if (utility not in UTILITIES or UTILITIES[utility].get("grid_operator", "PJM") != "PJM"
            or request.get("regional_account", {}).get("grid_operator") != "PJM"):
        raise ValueError("PJM carbon requires an independently confirmed PJM regional account; no other grid is substituted.")
    if request.get("timestep_minutes") not in (15, 30):
        raise ValueError("PJM carbon supports 15/30-minute studies; finer data is not inferred.")
    first, last = date.fromisoformat(request["start_date"]), date.fromisoformat(request["end_date"])
    today = pd.Timestamp.now(tz=request["timezone"]).date()
    if first < date(2025, 1, 1) or last > date(2026, 12, 31) or first > last or last >= today:
        raise ValueError("PJM historical carbon requires completed local days in 2025–2026; future data is unavailable.")


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _expected(request):
    start = pd.Timestamp(request["start_date"], tz=request["timezone"])
    end = pd.Timestamp(request["end_date"], tz=request["timezone"]) + pd.DateOffset(days=1)
    return pd.date_range(start, end, freq="15min", inclusive="left").tz_convert("UTC")


def _frame(responses, expected):
    rows = []
    for response in responses:
        if response.get("zone") != ZONE or response.get("temporalGranularity") != "15_minutes":
            raise ValueError("PJM carbon response zone or interval resolution does not match the requested source.")
        if not isinstance(response.get("data"), list) or not response["data"]:
            raise ValueError("PJM carbon response has no interval data.")
        for row in response["data"]:
            if not isinstance(row, dict) or set(FIELDS) - set(row):
                raise ValueError("PJM carbon response is missing required interval provenance.")
            if row["zone"] != ZONE or row["emissionFactorType"] != "lifecycle" or row["flowTraced"] is not True:
                raise ValueError("PJM carbon interval zone, lifecycle factor or consumption basis does not match.")
            if type(row["isEstimated"]) is not bool:
                raise ValueError("PJM carbon estimation status must be reported for every interval.")
            if row["estimationMethod"] is not None and not isinstance(row["estimationMethod"], str):
                raise ValueError("Invalid PJM carbon estimation method.")
            # Reject a timezone-free timestamp rather than silently assuming UTC.
            for key in ("datetime", "createdAt", "updatedAt"):
                stamp = pd.Timestamp(row[key])
                if pd.isna(stamp) or stamp.tzinfo is None:
                    raise ValueError("PJM carbon timestamps and revisions must include a timezone.")
            value = row["carbonIntensity"]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value < 0:
                raise ValueError("PJM carbon intensity must be finite and nonnegative.")
            rows.append({key: row[key] for key in FIELDS})
    frame = pd.DataFrame(rows, columns=FIELDS)
    stamps = pd.DatetimeIndex(pd.to_datetime(frame["datetime"], utc=True))
    if not stamps.equals(expected):
        raise ValueError("PJM carbon must cover every provider 15-minute interval exactly once in order; no gaps are filled.")
    frame.insert(0, "timestamp", stamps)
    return frame


def values(request, directory, timestamps):
    """Retrieve or re-audit this study's immutable source, then aggregate means."""
    validate(request)
    if request.get("carbon") is None:
        return None, {"status": "not_requested", "warning": "Regional carbon accounting was not requested; emissions are not calculated."}
    from ..signal_pipeline import electricity_maps_data as provider
    from .worker import write_json
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    csv_path, meta_path = directory / "carbon-source.csv", directory / "carbon-source.json"
    identity = {"zone": ZONE, "start_date": request["start_date"], "end_date": request["end_date"],
                "timezone": request["timezone"], "factor_type": "lifecycle", "flow_traced": True,
                "provider_interval_minutes": 15}
    expected = _expected(request)
    responses = []
    reused = csv_path.exists() or meta_path.exists()
    if reused:
        if not csv_path.is_file() or not meta_path.is_file():
            raise ValueError("Saved PJM carbon source is incomplete; no silent refetch or fallback is allowed.")
        metadata = json.loads(meta_path.read_text())
        if metadata.get("request") != identity or metadata.get("sha256") != _sha(csv_path):
            raise ValueError("Saved PJM carbon data does not match this study or its checksum.")
        sources = metadata.get("raw_responses", [])
        if not sources:
            raise ValueError("Saved PJM carbon is missing raw source provenance.")
        for source in sources:
            name = source.get("file", "")
            # Metadata cannot escape the study source directory.
            if Path(name).name != name or not name.endswith(".json"):
                raise ValueError("Invalid saved PJM carbon source path.")
            path = directory / "carbon-source" / name
            if not path.is_file() or source.get("sha256") != _sha(path):
                raise ValueError("Saved PJM carbon raw response checksum does not match.")
            responses.append(json.loads(path.read_text()))
    else:
        key = os.getenv("ELECTRICITY_MAPS_API_KEY")
        if not key:
            raise ValueError("Electricity Maps credentials are missing. Historical PJM carbon requires ELECTRICITY_MAPS_API_KEY; no constant fallback is available.")
        raw_dir = directory / "carbon-source"
        raw_dir.mkdir(exist_ok=True)
        days = (date.fromisoformat(request["end_date"]) - date.fromisoformat(request["start_date"])).days + 1
        sources = []
        for offset in range(0, days, provider.CARBON_API_CHUNK_DAYS_15_MINUTES):
            if offset:
                time.sleep(0.5)  # Stay below the provider's default 150 requests/minute.
            chunk_start = (pd.Timestamp(request["start_date"]) + pd.DateOffset(days=offset)).date().isoformat()
            chunk_days = min(provider.CARBON_API_CHUNK_DAYS_15_MINUTES, days - offset)
            start, end = provider.create_utc_time_range(chunk_start, chunk_days, request["timezone"])
            write_json(directory / "progress.json", {"message": f"Retrieving PJM regional-average carbon · {chunk_start}; no assumed fallback"})
            response = provider.get_carbon_intensity_range(key, ZONE, start, end,
                flow_traced=True, emission_factor_type="lifecycle")
            chunk_request = {**request, "start_date": chunk_start,
                "end_date": (pd.Timestamp(chunk_start) + pd.DateOffset(days=chunk_days - 1)).date().isoformat()}
            _frame([response], _expected(chunk_request))
            responses.append(response)
            path = raw_dir / (chunk_start + ".json")
            write_json(path, response)
            sources.append({"file": path.name, "sha256": _sha(path),
                "start_utc": start, "end_exclusive_utc": end,
                "retrieved_at": datetime.now(timezone.utc).isoformat()})
        metadata = {"request": identity, "raw_responses": sources,
                    "retrieved_at": datetime.now(timezone.utc).isoformat()}
    frame = _frame(responses, expected)
    if reused:
        # Reconstruct the normalized source from raw responses, not metadata claims.
        if csv_path.read_text() != frame.to_csv(index=False):
            raise ValueError("Saved PJM carbon CSV does not reconcile to its raw provenance.")
    else:
        frame.to_csv(csv_path, index=False)
        metadata["sha256"] = _sha(csv_path)
        write_json(meta_path, metadata)
    series = pd.Series(frame["carbonIntensity"].to_numpy(dtype=float), index=expected)
    aligned = series.resample(f"{request['timestep_minutes']}min").mean()
    target = pd.DatetimeIndex(timestamps)
    if target.tz is None or not aligned.index.equals(target.tz_convert("UTC")):
        raise ValueError("PJM carbon timestamps do not match the simulation horizon.")
    coverage = {"start_utc": expected[0].isoformat(),
                "end_exclusive_utc": (expected[-1] + pd.Timedelta(minutes=15)).isoformat(),
                "interval_count": len(expected), "estimated_interval_count": int(frame["isEstimated"].sum())}
    return aligned.to_numpy(), {**metadata, "status": "verified", "source": "electricity_maps",
        "zone": ZONE, "label": "PJM regional average", "factor_type": "lifecycle", "flow_traced": True,
        "units": "gCO2e/kWh", "provider_interval_minutes": 15,
        "study_interval_minutes": request["timestep_minutes"], "coverage": coverage,
        "estimation_methods": {str(key) if pd.notna(key) else "not_reported": int(count)
                               for key, count in frame["estimationMethod"].value_counts(dropna=False).items()},
        "source_url": API_URL, "methodology_url": METHOD_URL,
        "aggregation": "Mean of complete provider-returned 15-minute intervals; no interpolation or gap filling.",
        "warning": NOTE}
