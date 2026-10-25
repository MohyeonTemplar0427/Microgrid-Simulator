"""Regional ERA5 clocks, legacy caches and browser requests stay explicit/offline."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import threading
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.local_web.runtime import Application, CapacityError
from src.profiles import era5
from src.timeseries import build_interval_index

CLOCKS = ("America/New_York", "America/Chicago", "America/Indiana/Indianapolis")
BASE = dict(latitude=43.05, longitude=-88.25,
            start_date="2025-01-01", end_date="2025-01-01")


def weather_payload(start="2024-12-31", stop="2025-01-04", *, latitude=43.05, longitude=-88.25):
    # These are synthetic reported hour-ending radiation records in UTC.
    # Hour-varying values expose a wrong local-clock alignment.
    reported = pd.date_range(start, stop, freq="h", inclusive="left", tz="UTC")
    raw = dict(latitude=latitude, longitude=longitude, utc_offset_seconds=0, timezone="UTC",
        hourly_units={"time": "iso8601", **{k: v[1] for k, v in era5.VARIABLES.items()}},
        hourly={"time": reported.strftime("%Y-%m-%dT%H:%M").tolist(),
            **{k: ([20.] * len(reported) if k == "temperature_2m" else
                    [1.] * len(reported) if k == "wind_speed_10m" else
                    np.arange(len(reported), dtype=float).tolist()) for k in era5.VARIABLES}})
    return dict(provider="open_meteo_era5", raw_json=json.dumps(raw),
        retrieved_at="2026-10-24T00:00:00Z",
        request=dict(latitude=latitude, longitude=longitude, start_date=start, end_date=stop,
                     models="era5", timezone="UTC", wind_speed_unit="ms"))


def fake_app(tmp_path):
    """Exercise the real endpoint method without sockets, workers or snapshots."""
    grants, reservations = [], []
    store = SimpleNamespace(directory=tmp_path, max_weather_bytes=1024 * 1024,
        grant=lambda *args: grants.append(args),
        require_weather_storage=lambda *args: reservations.append(args))
    return SimpleNamespace(store=store, engine={"id": "offline-weather-engine"},
                           resource_lock=threading.RLock()), grants, reservations


def cache_key(app, request, owner):
    return hashlib.sha256(json.dumps(
        [app.engine["id"], "regional_era5", request, owner], sort_keys=True).encode()).hexdigest()


@pytest.mark.parametrize("clock", CLOCKS)
@pytest.mark.parametrize("day,intervals", [("2025-03-09", 92), ("2025-11-02", 100)])
def test_endpoint_validates_complete_dst_day_on_requested_clock(tmp_path, monkeypatch, clock, day, intervals):
    app, grants, reservations = fake_app(tmp_path)
    payload = weather_payload(str((pd.Timestamp(day)-pd.DateOffset(days=1)).date()),
                              str((pd.Timestamp(day)+pd.DateOffset(days=3)).date()))
    fetched, parsed = [], []
    original = era5.parse_era5

    def fetch(start, end, latitude, longitude, *, local_timezone):
        fetched.append((start, end, latitude, longitude, local_timezone))
        return payload

    def parse(text, grid, latitude, longitude):
        parsed.append(grid.index)
        return original(text, grid, latitude, longitude)

    monkeypatch.setattr(era5, "fetch_era5", fetch)
    monkeypatch.setattr(era5, "parse_era5", parse)
    request = {**BASE, "start_date": day, "end_date": day, "timezone": clock}
    out = Application.regional_weather(app, request, "owner-a")
    assert fetched == [(day, day, BASE["latitude"], BASE["longitude"], clock)]
    assert len(parsed) == 1 and len(parsed[0]) == intervals and str(parsed[0].tz) == clock
    assert parsed[0][0] == pd.Timestamp(day, tz=clock)
    assert parsed[0][-1].hour == 23 and parsed[0][-1].minute == 45
    assert out["weather"]["raw_json"] == payload["raw_json"] and out["cached"] is False
    assert out["provenance"]["native_interval_minutes"] == 60
    frame, _ = original(payload["raw_json"], build_interval_index(day, day, clock, 15),
                        BASE["latitude"], BASE["longitude"])
    raw = json.loads(payload["raw_json"])
    first_reported = parsed[0][0].tz_convert("UTC") + pd.Timedelta(hours=1)
    row = raw["hourly"]["time"].index(first_reported.strftime("%Y-%m-%dT%H:%M"))
    assert np.all(frame.ghi_w_per_m2.iloc[:4] == raw["hourly"]["shortwave_radiation"][row])
    assert frame.ghi_w_per_m2.iloc[4] == raw["hourly"]["shortwave_radiation"][row + 1]
    assert grants == [("weather", cache_key(app, request, "owner-a"), "owner-a")]
    assert reservations == [("owner-a", cache_key(app, request, "owner-a"))]


def test_legacy_cache_bytes_and_owner_engine_clock_separation(tmp_path, monkeypatch):
    app, grants, reservations = fake_app(tmp_path)
    payload, calls = weather_payload(), []

    def fetch(*args, **kwargs):
        calls.append(kwargs["local_timezone"])
        return payload

    monkeypatch.setattr(era5, "fetch_era5", fetch)
    legacy = deepcopy(BASE)
    first = Application.regional_weather(app, legacy, "owner-a")
    path = tmp_path / "weather" / cache_key(app, legacy, "owner-a") / "era5.json"
    original_bytes = path.read_bytes()
    second = Application.regional_weather(app, legacy, "owner-a")
    assert second == {**first, "cached": True}
    assert path.read_bytes() == original_bytes and calls == ["America/New_York"]
    # Explicit Eastern is a new request shape; Central, owner and engine are
    # independent cache dimensions. No old record is migrated or overwritten.
    requests = [(dict(BASE, timezone="America/New_York"), "owner-a"),
                (dict(BASE, timezone="America/Chicago"), "owner-a"),
                (dict(BASE, timezone="America/Chicago"), "owner-b")]
    for request, owner in requests:
        assert Application.regional_weather(app, request, owner)["cached"] is False
    app.engine["id"] = "different-offline-engine"
    assert Application.regional_weather(app, requests[1][0], "owner-a")["cached"] is False
    assert calls == ["America/New_York", "America/New_York", "America/Chicago", "America/Chicago", "America/Chicago"]
    assert len(reservations) == 5 and len(grants) == 6
    assert len({r[1] for r in reservations}) == 5
    assert path.read_bytes() == original_bytes


def test_explicit_central_rejects_an_eastern_only_weather_boundary(tmp_path, monkeypatch):
    app, _, _ = fake_app(tmp_path)
    # Reported06:00 Jan1 is the05:00 UTC start hour; final05:00 Jan2
    # covers04:00 UTC. This is complete Eastern coverage but misses Central's
    # final05:00 UTC start hour. The endpoint must not validate both as Eastern.
    payload = weather_payload("2025-01-01T06:00", "2025-01-02T06:00")
    monkeypatch.setattr(era5, "fetch_era5", lambda *args, **kwargs: payload)
    assert Application.regional_weather(app, BASE, "owner-a")["cached"] is False
    request = {**BASE, "timezone": "America/Chicago"}
    with pytest.raises(ValueError, match="entire requested period"):
        Application.regional_weather(app, request, "owner-a")
    assert not (tmp_path / "weather" / cache_key(app, request, "owner-a") / "era5.json").exists()


def test_cache_tampering_rejects_without_fetch_or_new_grant(tmp_path, monkeypatch):
    app, grants, _ = fake_app(tmp_path)
    monkeypatch.setattr(era5, "fetch_era5", lambda *args, **kwargs: weather_payload())
    request = {**BASE, "timezone": "America/Chicago"}
    Application.regional_weather(app, request, "owner-a")
    path = tmp_path / "weather" / cache_key(app, request, "owner-a") / "era5.json"
    data = json.loads(path.read_text())
    data["weather"]["raw_json"] += " "
    path.write_text(json.dumps(data))
    monkeypatch.setattr(era5, "fetch_era5", lambda *args, **kwargs: pytest.fail("No replacement weather"))
    with pytest.raises(ValueError, match="Cached ERA5 bytes changed"):
        Application.regional_weather(app, request, "owner-a")
    assert len(grants) == 1


@pytest.mark.parametrize("invalid", [None, True, 1, "", "UTC", "America/Los_Angeles", "Mars/No_Clock"])
def test_unconfigured_clock_rejects_before_any_retrieval(tmp_path, monkeypatch, invalid):
    app, _, reservations = fake_app(tmp_path)
    monkeypatch.setattr(era5, "fetch_era5", lambda *args, **kwargs: pytest.fail("Invalid clock must not fetch"))
    with pytest.raises(ValueError, match="configured regional utility timezone"):
        Application.regional_weather(app, {**BASE, "timezone": invalid})
    assert not reservations


@pytest.mark.parametrize("bad_request", [None, "not an object", {**BASE, "extra": True},
    {k: v for k, v in BASE.items() if k != "end_date"}])
def test_endpoint_rejects_unknown_or_missing_contract_fields(tmp_path, bad_request):
    app, _, _ = fake_app(tmp_path)
    with pytest.raises(ValueError, match="Supply ERA5"):
        Application.regional_weather(app, bad_request)


def test_weather_quota_still_applies_to_new_clock_request(tmp_path, monkeypatch):
    app, grants, reservations = fake_app(tmp_path)
    app.store.max_weather_bytes = 1
    monkeypatch.setattr(era5, "fetch_era5", lambda *args, **kwargs: weather_payload())
    request = {**BASE, "timezone": "America/Chicago"}
    with pytest.raises(CapacityError, match="weather-resource limit"):
        Application.regional_weather(app, request, "owner-a")
    assert not grants and len(reservations) == 1
    assert not list(tmp_path.rglob("era5.json"))


def test_profile_fetch_keeps_legacy_payload_and_explicit_utc_request():
    captured = []

    def getter(url, *, params, timeout):
        captured.append((url, deepcopy(params), timeout))
        return SimpleNamespace(text='{"synthetic":"raw source bytes"}', raise_for_status=lambda: None)

    legacy = era5.fetch_era5("2025-01-01", "2025-01-01", 43.05, -88.25, getter)
    eastern = era5.fetch_era5("2025-01-01", "2025-01-01", 43.05, -88.25, getter,
                             local_timezone="America/New_York")
    # A non-US clock demonstrates that UTC dates actually derive from the
    # caller's clock rather than from a hardcoded Eastern midnight.
    tokyo = era5.fetch_era5("2025-01-01", "2025-01-01", 35., 139., getter,
                           local_timezone="Asia/Tokyo")
    assert set(legacy) == {"provider", "raw_json", "request", "retrieved_at"}
    assert legacy["request"] == eastern["request"]
    assert legacy["request"]["start_date"] == "2025-01-01"
    assert legacy["request"]["end_date"] == "2025-01-02"
    assert tokyo["request"]["start_date"] == "2024-12-31"
    assert tokyo["request"]["end_date"] == "2025-01-01"
    assert all(p["timezone"] == "UTC" and p["models"] == "era5" and p["wind_speed_unit"] == "ms"
               for _, p, _ in captured)
    assert all(url == era5.URL for url, _, _ in captured)
    assert legacy["raw_json"] == '{"synthetic":"raw source bytes"}'


def run_node(code):
    return json.loads(subprocess.run(["node", "-e", code], text=True,
        capture_output=True, check=True, timeout=15).stdout)


@pytest.mark.parametrize("clock", CLOCKS)
def test_actual_browser_timezone_sync_uses_selected_utility(clock):
    # Execute the actual named function with mocked browser dependencies.
    # This covers the handler that runs before regionalUI.sync on input edits.
    source = Path("src/local_web/static/app.js").read_text()
    function = re.search(r"function syncLocationTimezone\(\) \{.*?\n\}", source, re.S).group()
    code = "const vm=require('vm');const fields={utility:{value:'selected'},timezone:{value:'America/New_York'}};"
    code += "const sandbox={template:{schema_version:2},window:{regionalUI:{active:()=>true}},field:k=>fields[k],capabilities:{regional_simulation:{utilities:{selected:{timezone:"+json.dumps(clock)+"}}}}};"
    code += "vm.createContext(sandbox);vm.runInContext("+json.dumps(function+";syncLocationTimezone();")+",sandbox);process.stdout.write(JSON.stringify(fields.timezone.value));"
    assert run_node(code) == clock


@pytest.mark.parametrize("clock", CLOCKS)
def test_actual_browser_weather_post_and_cache_key_include_clock(clock):
    source = Path("src/local_web/static/regional.js").read_text()
    weather_key = re.search(r"  function weatherKey\(\)\{.*?\n", source).group().strip()
    start = source.index('  $("regional-weather-fetch").addEventListener("click",async()=>')
    stop = source.index('  f("native_file").addEventListener', start)
    handler = source[start:stop]
    fields = {k: {"value": str(v)} for k, v in {**BASE, "timezone": clock}.items()}
    code = "const vm=require('vm');let callback,posted;const fields="+json.dumps(fields)+";const nodes={};"
    code += "const sandbox={field:k=>fields[k],$:k=>nodes[k]||(nodes[k]={addEventListener:(e,fn)=>{callback=fn;}}),api:async(url,data)=>{posted={url,data};return {weather:{fixture:true},cached:false,provenance:{attribution:'synthetic'}};},era5:null,era5Key:null};"
    code += "vm.createContext(sandbox);vm.runInContext("+json.dumps(weather_key+";"+handler)+",sandbox);"
    code += "(async()=>{const first=sandbox.weatherKey();await callback();fields.timezone.value='changed-clock';const second=sandbox.weatherKey();process.stdout.write(JSON.stringify({posted,first,second}));})();"
    out = run_node(code)
    assert out["posted"]["url"] == "/api/v1/regional/weather"
    assert out["posted"]["data"] == {**BASE, "timezone": clock}
    assert out["first"] != out["second"]
