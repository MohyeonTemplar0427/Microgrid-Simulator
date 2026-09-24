"""Measure annual browser-result sizes offline with synthetic San Francisco weather.

This exercises the current simulation adapter and result writers, but not NSRDB,
authentication, HTTP, or the hosted worker queue. All data is deleted on exit.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
from copy import deepcopy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from pvlib.location import Location

from src.local_web.contract import DEFAULT_SITE_REQUEST, validate_request
from src.local_web.worker import execute, write_json
from src.local_web.table_store import read_page
from src.profiles.nsrdb import save_weather_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval-minutes", type=int, choices=(5, 15, 30, 60), default=15)
    parser.add_argument("--strategies", choices=("baseline", "all"), default="all")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="microgrid-year-benchmark-") as root_name:
        root = Path(root_name)
        weather_dir, run_dir = root / "weather", root / "run"
        weather_dir.mkdir()
        run_dir.mkdir()
        index = pd.date_range("2025-01-01", "2026-01-01", freq=f"{args.interval_minutes}min",
                              inclusive="left", tz="America/Los_Angeles")
        midpoints = index + pd.Timedelta(minutes=args.interval_minutes / 2)
        irradiance = Location(37.7749, -122.4194, tz="America/Los_Angeles").get_clearsky(midpoints)
        weather = pd.DataFrame({
            "timestamp": index, "ghi_w_per_m2": irradiance.ghi.to_numpy(),
            "dni_w_per_m2": irradiance.dni.to_numpy(), "dhi_w_per_m2": irradiance.dhi.to_numpy(),
            "temperature_c": 20.0, "wind_speed_m_per_s": 1.0,
        })
        weather_path = save_weather_csv(weather, weather_dir / "weather.csv")
        request = deepcopy(DEFAULT_SITE_REQUEST)
        request.update(start_date="2025-01-01", end_date="2025-12-31",
                       timestep_minutes=args.interval_minutes, weather_source="nsrdb",
                       weather_id="b" * 64)
        if args.strategies == "baseline":
            request["strategies"] = ["no_battery"]
        validate_request(request)
        metadata = {
            "request": {"latitude": request["site"]["latitude"],
                        "longitude": request["site"]["longitude"], "year": 2025,
                        "timezone": request["timezone"], "timestep_minutes": args.interval_minutes},
            "sha256": hashlib.sha256(weather_path.read_bytes()).hexdigest(),
            "row_count": len(weather),
            "provenance": {"source": "synthetic_clear_sky_storage_benchmark"},
            "warnings": ["Synthetic benchmark weather; not historical observations."],
        }
        write_json(weather_dir / "weather.json", metadata)
        for name in ("weather.csv", "weather.json"):
            shutil.copyfile(weather_dir / name, run_dir / name)
        write_json(run_dir / "request.json", request)
        write_json(run_dir / "engine.json", {"id": "storage-benchmark", "kind": "test-only"})
        print(json.dumps({"stage": "prepared", "intervals": len(index),
                          "cached_weather_bytes": sum(p.stat().st_size for p in weather_dir.iterdir()),
                          "run_input_bytes": sum(p.stat().st_size for p in run_dir.iterdir())}), flush=True)
        started = time.monotonic()
        try:
            execute(run_dir)
        finally:
            late_page_seconds = None
            if (run_dir / "dispatch-cost_optimal.meta.json").is_file():
                page_started = time.monotonic()
                page = read_page(run_dir, "dispatch-cost_optimal", max(0, len(index) - 100), 100)
                assert len(page["data"]) == 100
                late_page_seconds = round(time.monotonic() - page_started, 3)
            files = sorted(((p.name, p.stat().st_size) for p in run_dir.iterdir() if p.is_file()),
                           key=lambda item: item[1], reverse=True)
            print(json.dumps({"stage": "finished_or_failed", "elapsed_seconds": round(time.monotonic() - started, 3),
                              "run_bytes": sum(size for _, size in files),
                              "largest_files": files[:15], "file_count": len(files),
                              "late_page_seconds": late_page_seconds}), flush=True)


if __name__ == "__main__":
    main()
