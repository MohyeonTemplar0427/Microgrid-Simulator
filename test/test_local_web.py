"""Local web contract, persistence, process isolation, and real HTTP/engine parity."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pandas as pd
import pytest

from src.local_web.contract import DEFAULT_REQUEST, validate_request
from src.local_web.runtime import Application, ROOT, Store, inspect_csv, snapshot
from src.local_web.server import make_server
from src.local_web.table_store import read_page, save_table
from src.local_web.worker import summarize_ac_validation


def request_for(dataset_id):
    request = deepcopy(DEFAULT_REQUEST)
    request["dataset_id"] = dataset_id
    request["strategies"] = ["no_battery", "cost_optimal"]
    return request


@pytest.mark.parametrize("change", [
    {"schema_version": 2}, {"unrecognized": 1}, {"carbon_weight": float("nan")},
    {"strategies": ["cost_optimal"]}, {"strategies": ["no_battery", "no_battery"]},
    {"end_date": "2026-07-31"}, {"timezone": "invalid/zone"}, {"timestep_minutes": True},
])
def test_reject_invalid_or_incompatible_requests(change):
    request = request_for("a" * 64)
    request.update(change)
    with pytest.raises(ValueError):
        validate_request(request)


def test_reject_initial_energy_outside_soc():
    request = request_for("a" * 64)
    request["battery"]["energy_kWh"] = 90
    with pytest.raises(ValueError, match="Initial battery energy"):
        validate_request(request)


def test_ac_validation_keeps_bounded_failure_examples():
    frame = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=8, freq="15min", tz="UTC"),
        "feasible": [True, False, False, False, False, False, False, False],
        "converged": [True, False, True, True, True, True, True, True],
        "voltage_violation": [False, False, True, False, False, False, False, False],
        "line_overload": [False] * 8,
        "transformer_overload": [False] * 8,
        "setpoint_mismatch": [False] * 8,
        "inverter_capability_violation": [False] * 8,
    })
    summary = summarize_ac_validation({"test": frame})
    assert summary["all_intervals_feasible"] is False
    scenario = summary["scenarios"][0]
    assert (scenario["checked_intervals"], scenario["passed_intervals"], scenario["failed_intervals"]) == (8, 1, 7)
    assert len(scenario["failure_samples"]) == 5
    assert scenario["failure_samples"][0] == {
        "timestamp": "2025-01-01T00:15:00+00:00", "reasons": ["OpenDSS did not converge"]}
    assert scenario["failure_samples"][1]["reasons"] == ["Voltage outside limits"]
    assert summarize_ac_validation({"test": frame.iloc[:1]})["all_intervals_feasible"] is True


def test_csv_only_result_pages_keep_types_and_nulls(tmp_path):
    frame = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=3, freq="15min", tz="UTC"),
        "feasible": [True, False, True], "count": [1, 2, 3],
        "value": [1.25, None, 3.5], "scenario": ["a", "b", "c"],
    })
    save_table(tmp_path, "example", list(frame.columns), frame)
    assert not (tmp_path / "example.json").exists()
    page = read_page(tmp_path, "example", 1, 2)
    assert page["total"] == 3 and page["offset"] == 1
    assert page["data"] == [
        ["2025-01-01 00:15:00+00:00", False, 2, None, "b"],
        ["2025-01-01 00:30:00+00:00", True, 3, 3.5, "c"],
    ]


def test_battery_wear_objective_choice_defaults_off_and_requires_boolean():
    request = request_for("a" * 64)
    assert "include_degradation_in_optimization" not in validate_request(request)
    request["include_degradation_in_optimization"] = True
    assert validate_request(request)["include_degradation_in_optimization"] is True
    request["include_degradation_in_optimization"] = "true"
    with pytest.raises(ValueError, match="battery degradation"):
        validate_request(request)


def test_csv_preserves_repeated_dst_hour_by_instant():
    csv = b"timestamp,load_kw,pv_kw,price_per_kWh,gCO2/kWh\n2026-11-01T01:00:00-07:00,10,0,0.2,200\n2026-11-01T01:00:00-08:00,10,0,0.2,200\n"
    assert inspect_csv(csv)["timestep_minutes"] == 60
    with pytest.raises(ValueError, match="unique"):
        inspect_csv(csv.replace(b"-08:00", b"-07:00"))
    with pytest.raises(ValueError, match="UTC offset"):
        inspect_csv(csv.replace(b"-07:00", b"").replace(b"-08:00", b""))


@pytest.mark.parametrize("replacement", [b"nan", b"inf", b"-1"])
def test_upload_rejects_invalid_load(replacement):
    content = (ROOT / "data/default_small_business_week.csv").read_bytes()
    with pytest.raises(ValueError):
        inspect_csv(content.replace(b"12.714", replacement, 1))


def test_snapshot_requires_explicit_refresh_and_detects_tampering(tmp_path):
    root, storage = tmp_path / "source", tmp_path / "storage"
    (root / "src").mkdir(parents=True)
    storage.mkdir()
    module = root / "src/module.py"
    module.write_text("VERSION = 1\n")
    first = snapshot(root, storage)
    module.write_text("VERSION = 2\n")
    assert snapshot(root, storage)["id"] == first["id"]
    second = snapshot(root, storage, refresh=True)
    assert second["id"] != first["id"]
    (storage / "engines" / second["id"] / "src/module.py").write_text("changed")
    with pytest.raises(ValueError, match="modified"):
        snapshot(root, storage)


def test_saved_request_and_inputs_are_immutable_and_claimed_once(tmp_path):
    store = Store(tmp_path)
    content = (ROOT / "data/default_small_business_week.csv").read_bytes()
    dataset = store.add_dataset(content, "sample.csv")
    request = request_for(dataset["id"])
    request["include_degradation_in_optimization"] = True
    study = store.submit(request, {"id": "test-engine"})
    request["battery"]["capacity_kWh"] = 900
    assert store.get(study["id"])["request"]["battery"]["capacity_kWh"] == 100
    assert hashlib.sha256((tmp_path / "runs" / study["id"] / "input.csv").read_bytes()).hexdigest() == dataset["id"]
    assert store.claim()["id"] == study["id"]
    assert store.claim() is None
    assert Store(tmp_path).get(study["id"])["status"] == "running"


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    application = Application(tmp_path_factory.mktemp("local-web"))
    server = make_server(application, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def call(path, body=None, headers=None):
        payload = None if body is None else json.dumps(body).encode()
        request = Request(base + path, data=payload, headers=headers or {})
        with urlopen(request, timeout=10) as response:
            content = response.read()
            return json.loads(content) if response.headers["Content-Type"] == "application/json" else content

    caps = call("/api/capabilities")
    yield application, call, {"Content-Type": "application/json", "X-Study-Token": caps["token"]}
    server.shutdown()
    thread.join()
    server.server_close()
    application.close()


def wait_for_study(call, study_id):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        study = call(f"/api/studies/{study_id}")
        if study["status"] in {"completed", "failed"}:
            return study
        time.sleep(0.1)
    pytest.fail("Local simulation did not complete within 90 seconds")


def test_http_blocks_cross_origin_and_missing_token(service):
    _, call, headers = service
    for bad_headers in ({"Host": "attacker.example"}, {"Origin": "https://attacker.example"}):
        with pytest.raises(HTTPError) as error:
            call("/api/capabilities", headers=bad_headers)
        assert error.value.code == 403
    with pytest.raises(HTTPError) as error:
        call("/api/studies", DEFAULT_REQUEST, {"Content-Type": "application/json"})
    assert error.value.code == 403


def test_real_run_matches_existing_engine_and_returns_paged_tables(service):
    from src.dispatch.battery import Battery
    from src.simulation.model_specifications import MicrogridSpecification
    from src.simulation.interface_analysis import run_integrated_csv_analysis

    application, call, headers = service
    content = (ROOT / "data/default_small_business_week.csv").read_text()
    dataset = call("/api/datasets", {"csv": content, "name": "browser-upload.csv"}, headers)
    request = request_for(dataset["id"])
    # Exercise actual utility billing as well as optimization and AC replay.
    request["include_degradation_in_optimization"] = True
    request["tariff_id"] = next(t["id"] for t in application.capabilities["tariffs"] if "b6" in t["id"])
    study = call("/api/studies", request, headers)
    finished = wait_for_study(call, study["id"])
    assert finished["status"] == "completed", finished.get("error")
    assert finished["result"]["engine"]["id"] == application.engine["id"]
    comparison = call(f'/api/studies/{study["id"]}/tables/comparison')
    actual = pd.DataFrame(comparison["data"], columns=comparison["columns"])
    direct = run_integrated_csv_analysis(
        MicrogridSpecification(Battery(**request["battery"]), 50, 54),
        ROOT / "data/default_small_business_week.csv",
        start_date=request["start_date"], number_of_days=1, timestep_minutes=15,
        expected_timezone=request["timezone"], selected_scenarios=tuple(request["strategies"]),
        carbon_weights=(request["carbon_weight"],), degradation_cost_per_kWh=0.03,
        include_degradation_in_optimization=True,
        tariff_id=request["tariff_id"],
    )
    pd.testing.assert_frame_equal(actual, direct.comparison, check_dtype=False, atol=1e-7, rtol=1e-7)
    table = call(f'/api/studies/{study["id"]}/tables/dispatch-cost_optimal?offset=90&limit=20')
    assert table["total"] == 96 and len(table["data"]) == 6
    download = call(f'/api/studies/{study["id"]}/tables/comparison.csv')
    assert b"scenario" in download and b"cost_optimal" in download
    with pytest.raises(HTTPError) as error:
        call(f'/api/studies/{study["id"]}/tables/../../request.json')
    assert error.value.code == 404
    assert call(f'/api/studies/{study["id"]}/request.json') == request


def test_bad_horizon_fails_without_blocking_next_queued_study(service):
    application, call, headers = service
    request = request_for(call("/api/capabilities")["defaults"]["dataset_id"])
    request["start_date"] = request["end_date"] = "2025-01-01"
    failed = call("/api/studies", request, headers)
    request["start_date"] = request["end_date"] = "2026-08-01"
    request["strategies"] = ["no_battery"]
    good = call("/api/studies", request, headers)
    failed_result = wait_for_study(call, failed["id"])
    good_result = wait_for_study(call, good["id"])
    assert failed_result["status"] == "failed"
    assert good_result["status"] == "completed"
    assert failed_result["runtime_seconds"] is not None and failed_result["runtime_seconds"] > 0
    assert good_result["runtime_seconds"] is not None and good_result["runtime_seconds"] > 0


def test_startup_marks_interrupted_run_failed_and_keeps_history(tmp_path):
    store = Store(tmp_path)
    dataset = store.add_dataset((ROOT / "data/default_small_business_week.csv").read_bytes(), "sample.csv")
    interrupted = store.submit(request_for(dataset["id"]), {"id": "test-engine"})
    store.claim()
    application = Application(tmp_path)
    try:
        recovered = application.store.get(interrupted["id"])
        assert recovered["status"] == "failed"
        assert "server stopped" in recovered["error"]
        with pytest.raises(ValueError, match="Another local server"):
            Application(tmp_path)
    finally:
        application.close()


from src.local_web.contract import DEFAULT_SITE_REQUEST
from src.local_web.site_inputs import build_site_inputs, check_weather_matches, resolve_location, validate_weather_request


def site_request(day="2026-08-01"):
    request = deepcopy(DEFAULT_SITE_REQUEST)
    request.update(start_date=day, end_date=day, strategies=["no_battery", "cost_optimal"])
    return request


@pytest.mark.parametrize("day,count", [("2026-08-01",96),("2026-03-08",92),("2026-11-01",100)])
def test_clear_sky_uses_site_daylight_and_dst_grid(tmp_path,day,count):
    request=site_request(day)
    frame, replay, tables, provenance=build_site_inputs(request,tmp_path)
    assert len(frame)==len(tables["weather"])==len(tables["pv"])==count
    assert frame.pv_kw.min()==0 and 0 < frame.pv_kw.max() <= request["pv_capacity_kw"]
    assert frame.timestamp.is_unique and frame.load_kw.eq(60).all()
    assert replay.available_power_kw.RooftopPV.to_list()==frame.pv_kw.to_list()
    assert any("not a weather forecast" in w for w in provenance["warnings"])
    request["solar"]["dc_capacity_kw"]=30
    smaller,_,_,_=build_site_inputs(request,tmp_path)
    assert smaller.pv_kw.sum()<frame.pv_kw.sum()
    request["solar"]["azimuth_degrees"]=0
    north,_,_,_=build_site_inputs(request,tmp_path)
    assert not north.pv_kw.equals(smaller.pv_kw)


def test_site_contract_historical_requires_weather_and_bundled_service():
    request=site_request()
    validate_request(request)
    request["weather_source"]="nsrdb"
    with pytest.raises(ValueError,match="Retrieve historical"):
        validate_request(request)
    request["weather_id"]="a"*64
    request["tariff_id"]="pge_b1_secondary_single_phase_bundled_2026_03_01"
    with pytest.raises(ValueError,match="Confirm PG&E"):
        validate_request(request)
    with pytest.raises(ValueError,match="2018"):
        validate_weather_request(dict(latitude=37,longitude=-122,year=2026,timezone="America/Los_Angeles",timestep_minutes=15))


def test_location_result_is_a_hint_not_account_assignment():
    from src.simulation.geocoding import GeocodedLocation
    class Search:
        def search(self, query):
            return GeocodedLocation(query,"San Francisco",37.7749,-122.4194,"test")
    result=resolve_location("SF",Search())
    assert result["suggestion"]["utility"]=="pge"
    assert "Confirm your account" in result["suggestion"]["message"]
    from src.local_web.site_inputs import location_suggestion
    assert location_suggestion(40,-74)["utility"] is None


def test_historical_inputs_are_copied_and_never_shifted(tmp_path):
    from src.local_web.worker import write_json
    from src.profiles.nsrdb import save_weather_csv
    store=Store(tmp_path)
    request=site_request("2025-08-01")
    _,_,tables,_=build_site_inputs(request,tmp_path)
    request.update(weather_source="nsrdb",weather_id="a"*64)
    cached=tmp_path/"weather"/request["weather_id"]
    cached.mkdir()
    save_weather_csv(tables["weather"],cached/"weather.csv")
    metadata={"request":dict(latitude=request["site"]["latitude"],longitude=request["site"]["longitude"],year=2025,timezone=request["timezone"],timestep_minutes=15),"sha256":hashlib.sha256((cached/"weather.csv").read_bytes()).hexdigest(),"provenance":{"source":"test_weather_fixture"},"warnings":[]}
    write_json(cached/"weather.json",metadata)
    study=store.submit(request,{"id":"test"})
    directory=tmp_path/"runs"/study["id"]
    (cached/"weather.csv").write_text("changed original")
    frame,_,tables,provenance=build_site_inputs(request,directory)
    assert len(frame)==96 and provenance["weather"]["source"]=="test_weather_fixture"
    request["start_date"]=request["end_date"]="2026-08-01"
    with pytest.raises(ValueError,match="never shifted"):
        check_weather_matches(request,metadata)
    request["start_date"]=request["end_date"]="2025-08-01"
    (directory/"weather.csv").write_text("modified saved copy")
    with pytest.raises(ValueError,match="checksum"):
        build_site_inputs(request,directory)


def test_site_http_run_returns_weather_solar_and_actual_tariff_prices(service):
    application,call,headers=service
    request=site_request()
    request["site"]["utility"]="pge"
    request["tariff_id"]=next(t["id"] for t in application.capabilities["tariffs"] if "b6" in t["id"])
    request["load"]["mode"]="synthetic"
    study=call("/api/studies",request,headers)
    finished=wait_for_study(call,study["id"])
    assert finished["status"]=="completed",finished.get("error")
    result=finished["result"]
    assert {"inputs","pv","weather"} <= {t["id"] for t in result["tables"]}
    assert not any(w.startswith("CSV load and PV") or w.startswith("Dispatch was optimized against") for w in result["warnings"])
    table=call(f'/api/studies/{study["id"]}/tables/inputs')
    inputs=pd.DataFrame(table["data"],columns=table["columns"])
    from src.billing import get_tariff
    index=pd.DatetimeIndex(pd.to_datetime(inputs.timestamp,utc=True)).tz_convert(request["timezone"])
    expected=get_tariff(request["tariff_id"]).energy_rates(index)
    assert inputs.price_per_kWh.to_list()==expected.to_list()
    assert inputs.load_kw.nunique()>1
    assert result["input_provenance"]["weather"]["source"]=="pvlib_ineichen_clear_sky"
    request["start_date"]=request["end_date"]="2025-08-01"
    with pytest.raises(HTTPError) as rejected:
        call("/api/studies",request,headers)
    assert rejected.value.code == 400
    assert "Billing Plan coverage" in rejected.value.read().decode()


def test_location_cache_and_weather_validation_without_network(service,monkeypatch):
    from src.local_web.worker import write_json
    import src.local_web.runtime as runtime
    application,call,headers=service
    invocations=[]
    def run(command,**kwargs):
        directory=Path(command[-1]); invocations.append(directory)
        write_json(directory/"resource.json",{"display_name":"fixture SF","latitude":37.77,"longitude":-122.42,"suggestion":{"utility":"pge"}})
        from types import SimpleNamespace
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runtime.subprocess,"run",run)
    first=call("/api/location",{"query":"unique fixture search"},headers)
    second=call("/api/location",{"query":"unique fixture search"},headers)
    assert not first["cached"] and second["cached"] and len(invocations)==1
    with pytest.raises(HTTPError) as error:
        call("/api/weather",dict(latitude=37,longitude=-122,year=2026,timezone="America/Los_Angeles",timestep_minutes=15),headers)
    assert error.value.code==400 and len(invocations)==1


def test_retrieve_weather_reuses_adapter_and_excludes_credentials(tmp_path,monkeypatch):
    from src.local_web.site_inputs import retrieve_weather
    from src.profiles.nsrdb import PVLIB_TO_CANONICAL
    monkeypatch.setenv("NSRDB_API_KEY","secret-key-for-test")
    monkeypatch.setenv("NSRDB_API_EMAIL","private@example.com")
    request=site_request("2025-08-01")
    _,_,tables,_=build_site_inputs(request,tmp_path)
    canonical=tables["weather"]
    provider=pd.DataFrame({name:canonical[column].to_numpy() for name,column in PVLIB_TO_CANONICAL.items()},index=pd.DatetimeIndex(canonical.timestamp))
    calls=[]
    def fetcher(request,key,email):
        calls.append((request,key,email))
        return provider,{"email":email,"api_key":key}
    metadata=retrieve_weather(tmp_path,dict(latitude=37.7749,longitude=-122.4194,year=2025,timezone="America/Los_Angeles",timestep_minutes=15),fetcher=fetcher)
    assert len(calls)==1 and metadata["row_count"]==96
    assert metadata["provenance"]["source"]=="nsrdb_psm4"
    serialized=(tmp_path/"weather.json").read_text()
    assert "secret-key" not in serialized and "private@example" not in serialized
    assert metadata["sha256"]==hashlib.sha256((tmp_path/"weather.csv").read_bytes()).hexdigest()


def test_resource_worker_does_not_log_provider_credentials(tmp_path,monkeypatch,capsys):
    import src.local_web.worker as worker
    import src.local_web.site_inputs as site_inputs
    worker.write_json(tmp_path/"resource-request.json",{"kind":"weather","request":{}})
    def fail(*args):
        raise RuntimeError("https://provider.example?api_key=secret-private-key")
    monkeypatch.setattr(site_inputs,"retrieve_weather",fail)
    monkeypatch.setattr(worker.sys,"argv",["worker","resource",str(tmp_path)])
    with pytest.raises(SystemExit):
        worker.main()
    assert "secret-private-key" not in (tmp_path/"error.json").read_text()
    captured=capsys.readouterr()
    assert "secret-private-key" not in captured.err+captured.out


def test_historical_worker_runs_from_saved_weather_without_provider(service):
    from src.local_web.worker import write_json
    from src.profiles.nsrdb import save_weather_csv
    application,call,headers=service
    request=site_request("2025-08-01")
    _,_,tables,_=build_site_inputs(request,application.store.directory)
    request.update(weather_source="nsrdb",weather_id="b"*64)
    cached=application.store.directory/"weather"/request["weather_id"]
    cached.mkdir()
    save_weather_csv(tables["weather"],cached/"weather.csv")
    digest=hashlib.sha256((cached/"weather.csv").read_bytes()).hexdigest()
    write_json(cached/"weather.json",{"request":dict(latitude=37.7749,longitude=-122.4194,year=2025,timezone=request["timezone"],timestep_minutes=15),"sha256":digest,"provenance":{"source":"synthetic_test_fixture"},"warnings":["Synthetic weather fixture for integration testing."]})
    study=call("/api/studies",request,headers)
    finished=wait_for_study(call,study["id"])
    assert finished["status"]=="completed",finished.get("error")
    assert finished["result"]["input_provenance"]["weather"]["saved_weather_sha256"]==digest
    weather=call(f'/api/studies/{study["id"]}/tables/weather')
    assert weather["total"]==96


def test_nsrdb_wrapper_uses_current_endpoint_and_requested_resolution(monkeypatch):
    import pvlib.iotools
    from src.local_web.site_inputs import nsrdb_fetcher, NSRDB_URL
    from src.profiles.nsrdb import NSRDBRequest
    kwargs_seen={}
    def fetch(**kwargs):
        kwargs_seen.update(kwargs)
        return "fixture"
    monkeypatch.setattr(pvlib.iotools,"get_nsrdb_psm4_conus",fetch)
    assert nsrdb_fetcher(NSRDBRequest(37,-122,2025,"America/Los_Angeles",15),"key","email")=="fixture"
    assert kwargs_seen["url"]==NSRDB_URL
    assert kwargs_seen["year"]==2025 and kwargs_seen["time_step"]==15
    assert kwargs_seen["map_variables"] is True and kwargs_seen["leap_day"] is True


@pytest.mark.parametrize("quantity,reserve", [(1, .2), (2, 0)])
def test_catalog_study_retains_resolution_and_compact_ac_validation(service,quantity,reserve):
    from src.equipment.ess import resolve
    from src.local_web.contract import DEFAULT_CANDIDATE_REQUEST
    application,call,headers=service
    selection=dict(equipment_id='franklinwh.apower2.apr10k15v2us.240',quantity=quantity,initial_soc=.5,backup_reserve=reserve,efficiency_approximation=True)
    resolved=call('/api/ess/resolve',selection,headers)
    assert resolved['ready'] and resolved['battery']['SOC_min']==reserve
    request=deepcopy(DEFAULT_CANDIDATE_REQUEST)
    request.update(ess=resolved,battery=resolved['battery'])
    request['load']['power_kw']=5
    request['solar']['dc_capacity_kw']=20
    study=call('/api/studies',request,headers)
    finished=wait_for_study(call,study['id'])
    assert finished['status']=='completed',finished.get('error')
    assert finished['result']['ess']==resolved
    assert not any(item['id'].startswith('ac-') for item in finished['result']['tables'])
    assert not list((application.store.directory/'runs'/study['id']).glob('ac-*.json'))
    assert not list((application.store.directory/'runs'/study['id']).glob('ac-*.csv'))
    assert (application.store.directory/'runs'/study['id']/'comparison.meta.json').is_file()
    assert not (application.store.directory/'runs'/study['id']/'comparison.json').exists()
    with pytest.raises(HTTPError) as missing:
        call(f"/api/studies/{study['id']}/tables/ac-cost_optimal")
    assert missing.value.code==404
    validation=next(item for item in finished['result']['ac_validation']['scenarios'] if item['scenario']=='cost_optimal')
    assert validation['checked_intervals']==96
    assert validation['passed_intervals']+validation['failed_intervals']==96
    comparison=call(f"/api/studies/{study['id']}/tables/comparison")
    costs=pd.DataFrame(comparison['data'],columns=comparison['columns'])
    selected=costs.loc[costs.scenario=='cost_optimal'].iloc[0]
    assert selected.setpoint_mismatch_intervals==0
    assert selected.inverter_capability_violation_intervals==0
    dispatch=call(f"/api/studies/{study['id']}/tables/dispatch-cost_optimal")
    frame=pd.DataFrame(dispatch['data'],columns=dispatch['columns'])
    assert frame.battery_net_injection_kw.abs().max()>1
    assert any('not residential split-phase' in x for x in finished['result']['warnings'])
    with pytest.raises(HTTPError):call('/api/studies',{**request,'battery':{**request['battery'],'max_charge_kw':100}},headers)


@pytest.mark.parametrize("provider,product,vintage", [
    ("peninsula", "eco100", 2016), ("svce", "greenprime", 2017), ("sjce", "totalgreen", 2019)])
def test_bay_area_cca_http_run_prices_and_exported_bill(service, provider, product, vintage):
    from src.billing.bay_area_cca import build_b1
    application, call, headers = service
    request = site_request()
    t = build_b1(provider=provider, product=product, vintage=vintage, phase="polyphase")
    request["site"]["utility"] = provider
    request["tariff_id"] = t.tariff_id
    study = call("/api/studies", request, headers)
    finished = wait_for_study(call, study["id"])
    assert finished["status"] == "completed", finished.get("error")
    table = call(f'/api/studies/{study["id"]}/tables/inputs')
    inputs = pd.DataFrame(table["data"], columns=table["columns"])
    stamps = pd.DatetimeIndex(pd.to_datetime(inputs.timestamp, utc=True)).tz_convert(request["timezone"])
    assert inputs.price_per_kWh.to_list() == t.energy_rates(stamps).to_list()
    table = call(f'/api/studies/{study["id"]}/tables/costs')
    costs = pd.DataFrame(table["data"], columns=table["columns"])
    parts = ["cca_generation_charge", "cca_product_premium_charge", "pge_delivery_charge", "pcia_charge", "franchise_fee_charge"]
    if provider == "sjce":
        parts.append("cca_vintage_adjustment_charge")
        assert (costs.cca_vintage_adjustment_charge <= 0).all()
    assert costs[parts].sum(axis=1).to_numpy() == pytest.approx(costs.energy_cost.to_numpy())
    assert (costs.energy_cost+costs.customer_charge).to_numpy() == pytest.approx(costs.total_utility_charge.to_numpy())
    assert costs.demand_charge.eq(0).all()


def test_municipal_api_uses_saved_resolution_and_pinned_engine(service):
    from src.local_web.worker import write_json
    application, call, headers = service
    caps=call('/api/capabilities')
    assert caps['municipal']['interface_version']==1
    assert len(caps['municipal']['tariffs'])==8
    # A deterministic saved resolver result avoids live APIs in tests. The bill
    # itself runs through HTTP and the real pinned subprocess, not a stub.
    resolution_id='9'*32
    directory=application.store.directory/'candidate'/resolution_id
    directory.mkdir(parents=True,exist_ok=True)
    write_json(directory/'resource-request.json',{'kind':'utility-resolution','request':{'latitude':37.7652,'longitude':-122.2416}})
    write_json(directory/'resource.json',{'status':'verified','delivery_utility':'amp','manual_confirmation':{'reference':'fixture bill'}})
    df=pd.DataFrame({'timestamp':pd.date_range('2026-08-01','2026-09-01',tz='America/Los_Angeles',freq='15min',inclusive='left'), 'grid_import_kw':1})
    df['timestamp']=df.timestamp.map(lambda t:t.isoformat())
    body=dict(interface_version=1,mode='actual_service',resolution_id=resolution_id,
        arrangement=dict(delivery_utility='amp',generation_provider='amp',tariff_id='amp_a1_2026_07_01',export_program='none'),
        account=dict(customer_class='commercial',phase='single',voltage='secondary',metered=True,
            onsite_generation=False,special_riders=[],billing_cycle_confirmed=True,state_surcharge_exempt=False,
            confirmed_schedule='A-1',schedule_confirmation_reference='Fixture August electricity bill',uut_status='standard'),
        start='2026-08-01',end='2026-09-01',dispatch=df.to_dict('records'))
    result=call('/api/v1/municipal/bill',body,headers)
    assert result['engine_id']==application.engine['id']
    assert result['bill']['total']==pytest.approx((41.99+744*.20946)*1.075+744*.0003)
    saved=json.loads((application.store.directory/'candidate'/result['resource_id']/'resource-request.json').read_text())
    assert saved['request']['resolution']['manual_confirmation']['reference']=='fixture bill'
    body['resolution']={'status':'verified','delivery_utility':'svp'}
    with pytest.raises(HTTPError) as error:
        call('/api/v1/municipal/bill',body,headers)
    assert error.value.code==400


def test_municipal_queued_study_csv_exports_and_evidence(service):
    from src.local_web.worker import write_json
    from test_municipal import account, frame
    from test_municipal_dispatch import BATTERY
    application,call,headers=service
    rid='8'*32
    directory=application.store.directory/'candidate'/rid
    directory.mkdir(parents=True,exist_ok=True)
    resolution={'status':'verified','delivery_utility':'amp','coordinates':{'latitude':37.7652,'longitude':-122.2416},
        'manual_confirmation':{'reference':'Municipal integration fixture'}}
    write_json(directory/'resource-request.json',{'kind':'utility-resolution'})
    write_json(directory/'resource.json',resolution)
    data=frame(kw=20)
    data.loc[(data.timestamp.dt.hour>=17)&(data.timestamp.dt.hour<19),'grid_import_kw']=90
    body=dict(schema_version=4,site_profile={'site_type':'commercial','subtype':None},name='Municipal queued CSV study',resolution_id=rid,mode='actual_service',
        arrangement=dict(delivery_utility='amp',generation_provider='amp',tariff_id='amp_a2_2026_07_01',export_program='none'),
        account=account('A-2'),start_date='2026-08-01',end_date='2026-08-31',timezone='America/Los_Angeles',
        timestep_minutes=15,battery=BATTERY,load={'mode':'csv','csv':data.to_csv(index=False)},degradation_cost_per_kWh=.03)
    for invalid in ({**body,'resolution':resolution},{**body,'resolution_id':'f'*32},
                    {**body,'load':{'mode':'csv','csv':'timestamp,grid_import_kw\n2026-08-01,20'}}):
        with pytest.raises(HTTPError):
            call('/api/v1/municipal/studies',invalid,headers)
    with pytest.raises(HTTPError):
        call('/api/studies',body,headers)
    study=call('/api/v1/municipal/studies',body,headers)
    finished=wait_for_study(call,study['id'])
    assert finished['status']=='completed',finished.get('error')
    assert finished['request']['site_profile']==body['site_profile']
    assert finished['request']['resolution']==resolution
    assert finished['engine_id']==application.engine['id']
    result=finished['result']
    assert result['schema_version']==4
    assert result['bills']['cost_optimal']['total']<result['bills']['no_battery']['total']
    assert any('No AC' in warning for warning in result['warnings'])
    table=call(f"/api/studies/{study['id']}/tables/dispatch-cost_optimal")
    assert table['total']==2976
    table=call(f"/api/studies/{study['id']}/tables/comparison")
    comparison=pd.DataFrame(table['data'],columns=table['columns'])
    assert (comparison.total_utility_charge+comparison.degradation_cost).tolist()==pytest.approx(comparison.total_explicit_cost.tolist())
    assert comparison.peak_grid_import_kw.iloc[1]<90
    assert (application.store.directory/'runs'/study['id']/'dispatch-cost_optimal.csv').is_file()
