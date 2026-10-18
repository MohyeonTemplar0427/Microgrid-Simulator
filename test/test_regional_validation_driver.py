"""Offline validation-driver inputs, privacy and saved-ledger audits."""
import hashlib
import io
import json
from types import SimpleNamespace
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from tools import run_regional_validation as driver
from src.local_web.regional_study import execute, prepare


@pytest.mark.parametrize("utility,kind,plan",driver.DEFAULT_CASES)
def test_representative_monthly_requests_are_explicit_native_nonexport(utility,kind,plan):
    r=driver.case_request(utility,kind,"monthly",plan=plan)
    grid,load,cycles,_=prepare(r)
    assert len(cycles)==1
    assert len(load)==len(grid.index)
    assert r["load"]["mode"]=="csv"
    assert "synthetic" in r["load"]["source"]
    assert r["operating_contract"]["mode"]=="non_export"
    assert r["regional_account"]["verification_kind"]=="hypothetical_case"
    assert r["regional_account"]["wholesale_pricing_location"] is None


def test_annual_pseg_has_dated_distinct_obligations_not_copied_july_validity():
    r=driver.case_request("pseg","commercial","annual",plan="GLP")
    grid,_,cycles,equipment=prepare(r)
    assert len(grid.index)==35040 and len(cycles)==12
    jan=r["billing_cycles"][0]["account_overrides"]
    june=r["billing_cycles"][5]["account_overrides"]
    assert jan["obligation_effective_start"]=="2024-06-01"
    assert june["obligation_effective_start"]=="2025-06-01"
    assert jan["generation_obligation_kw"]!=jan["transmission_obligation_kw"]
    combined=equipment["pv_ac_kw"]+equipment["battery_kw"]
    # Even perfect coincidence at the native40kW monthly peak cannot make
    # ordinary DER nameplate reach half the optimized maximum import.
    assert combined<.5*(40-combined)
    assert len(grid.index[grid.index.month==3])==743*4
    assert len(grid.index[grid.index.month==11])==721*4


def test_monthly_case_uses_the_same_native_intervals_as_the_full_year():
    annual=driver.case_request("pseg","residential","annual",plan="RS")
    month=driver.case_request("pseg","residential","monthly",plan="RS")
    a=pd.read_csv(io.StringIO(annual["load"]["csv"]))
    b=pd.read_csv(io.StringIO(month["load"]["csv"]))
    stamps=pd.DatetimeIndex(pd.to_datetime(a.timestamp,utc=True)).tz_convert("America/New_York")
    pd.testing.assert_frame_equal(a.loc[stamps.month==7].reset_index(drop=True),b)


def test_unverified_va_year_rejects_current_rate_substitution():
    with pytest.raises(ValueError,match="2025 composite retail rates are not verified"):
        driver.case_request("dominion_energy_virginia","residential","annual")


@pytest.mark.parametrize("kind,plan",[("residential","VA-1"),("commercial","VA-GS1")])
def test_va_2025_subtotal_is_explicit_and_keeps_prior_contract_facts(kind,plan):
    r=driver.case_request("dominion_energy_virginia",kind,"annual",plan=plan,allow_va_history=True)
    grid,native,cycles,equipment=prepare(r)
    assert len(grid.index)==35040 and len(cycles)==12
    assert r["start_date"]=="2025-01-01" and "subtotal" in r["name"]
    assert [row["billing_month"] for row in r["account"]["history"]]==list(range(2,13))
    if kind=="commercial":
        assert max(native)==pytest.approx(15.)
        assert r["account"]["contract_demand_kw"]==20.
        assert all(row["maximum_kw"]==20. for row in r["account"]["history"])
        assert equipment["battery_kw"]==5. and equipment["pv_ac_kw"]==8.
        assert r["electrical_service"]["phase"]=="single"
        assert r["electrical_service"]["nominal_voltage_v"]==240.


@pytest.mark.parametrize("month,missing_consumption",[(1,True),(7,True),(9,False)])
def test_va_incomplete_scope_requires_exact_documented_exclusions(month,missing_consumption):
    r=driver.case_request("dominion_energy_virginia","residential","annual",plan="VA-1",allow_va_history=True)
    grid,native,cycles,_=prepare(r)
    _,block,cycle=cycles[month-1]
    account=driver.cycle_account(r["account"],cycle)
    bill=driver.calculate_cycle("dominion_energy_virginia",grid.index[block],native[block],np.zeros(block.stop-block.start),account)
    with pytest.raises(AssertionError,match="explicitly allowed"):
        driver.checked_bill_scope(bill,"dominion_energy_virginia",account,grid.index[block])
    scope,excluded=driver.checked_bill_scope(bill,"dominion_energy_virginia",account,grid.index[block],allow_va_history=True)
    assert scope=="verified_charges_subtotal"
    assert ("consumption_tax_before_2025_08_16" in excluded)==missing_consumption
    broken=deepcopy(bill);broken["excluded_components"].append("unverified_supply")
    with pytest.raises(AssertionError,match="explicitly allowed"):
        driver.checked_bill_scope(broken,"dominion_energy_virginia",account,grid.index[block],allow_va_history=True)


def test_va_history_reads_separate_actual_year_weather_artifacts(tmp_path,monkeypatch):
    monkeypatch.setattr(driver,"ROOT",tmp_path)
    parent=tmp_path/".cache"/"inputs"/"dominion_energy_virginia";parent.mkdir(parents=True)
    # Deliberately invalid current-month content must never be interpreted as
    # the2025 weather input or silently replace missing annual NSRDB records.
    (parent/"era5.json").write_text("not historical weather")
    app=SimpleNamespace(engine={"id":"fixture"},store=SimpleNamespace(directory=tmp_path/".cache"/"out"))
    r=driver.case_request("dominion_energy_virginia","residential","monthly",plan="VA-1",allow_va_history=True)
    with pytest.raises(FileNotFoundError):
        driver.attach_weather(app,r,parent.parent)
    child=parent/"nsrdb_2025";child.mkdir()
    content=b"actual-year weather fixture\n";(child/"weather.csv").write_bytes(content)
    metadata={"request":driver.weather_request("dominion_energy_virginia"),"sha256":hashlib.sha256(content).hexdigest()}
    (child/"weather.json").write_text(json.dumps(metadata))
    app.resource=lambda kind,weather:{"id":"f"*64}
    driver.attach_weather(app,r,parent.parent)
    assert r["weather_source"]=="nsrdb" and r["weather_id"]=="f"*64
    assert metadata["request"]["latitude"]==37.63 and metadata["request"]["longitude"]==-77.52


def test_historical_only_preparation_has_no_current_era5_dependency(tmp_path,monkeypatch):
    from src import credentials
    from src.local_web import site_inputs
    from src.profiles import era5
    monkeypatch.setattr(driver,"ROOT",tmp_path)
    monkeypatch.setattr(credentials,"load_credentials",lambda *a,**k:None)
    def unexpected_current_weather(**kwargs):
        pytest.fail("Historical-only preparation must not retrieve current-month ERA5")
    monkeypatch.setattr(era5,"fetch_era5",unexpected_current_weather)
    def retrieve(path,request):
        assert path.name=="nsrdb_2025" and request["year"]==2025
        return {"request":request,"sha256":"fixture"}
    monkeypatch.setattr(site_inputs,"retrieve_weather",retrieve)
    manifest=driver.prepare_inputs(tmp_path/".cache"/"weather",utilities=["dominion_energy_virginia"],
        include_va_history=True,va_history_only=True)
    assert set(manifest["sources"])=={"dominion_energy_virginia_2025"}


def test_cli_plan_filter_applies_after_optional_ciep_case_is_added(monkeypatch):
    seen=[]
    monkeypatch.setattr(driver,"run",lambda *args,**kwargs:seen.append(kwargs))
    monkeypatch.setattr(driver.sys,"argv",["run_regional_validation.py","--execute","--include-ciep",
        "--utility","pseg","--plan","GLP_CIEP"])
    driver.main()
    assert seen[0]["cases"]==[("pseg","commercial","GLP_CIEP")]


def test_missing_ciep_file_never_substitutes_hub_or_flat_price(tmp_path,monkeypatch):
    monkeypatch.setattr(driver,"ROOT",tmp_path)
    folder=tmp_path/".cache"/"market";folder.mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        driver.case_request("pseg","commercial","monthly",plan="GLP",ciep_inputs=folder)
    with pytest.raises(ValueError,match="must stay"):
        driver.private_path(tmp_path/"public")


def test_prepared_weather_is_rebound_without_refreshing_bytes(tmp_path,monkeypatch):
    monkeypatch.setattr(driver,"ROOT",tmp_path)
    folder=tmp_path/".cache"/"inputs"/"pseg";folder.mkdir(parents=True)
    content=b"canonical saved weather fixture\n"
    (folder/"weather.csv").write_bytes(content)
    metadata={"request":driver.weather_request("pseg"),"sha256":hashlib.sha256(content).hexdigest()}
    (folder/"weather.json").write_text(json.dumps(metadata))
    store=tmp_path/".cache"/"output";store.mkdir()
    seen=[]
    def resource(kind,request):
        seen.append((kind,request))
        key=hashlib.sha256(json.dumps(["test-engine","weather",request,None],sort_keys=True).encode()).hexdigest()
        assert (store/"weather"/key/"weather.csv").read_bytes()==content
        return {"id":key}
    app=SimpleNamespace(engine={"id":"test-engine"},store=SimpleNamespace(directory=store),resource=resource)
    r=driver.case_request("pseg","residential","monthly",plan="RS")
    driver.attach_weather(app,r,folder.parent)
    assert r["weather_source"]=="nsrdb" and len(seen)==1
    (folder/"weather.csv").write_bytes(b"changed")
    with pytest.raises(AssertionError,match="checksum mismatch"):
        driver.attach_weather(app,r,folder.parent)


def test_offline_saved_three_scenario_audit_detects_a_changed_component(tmp_path):
    r=driver.case_request("pseg","residential","monthly",plan="RS")
    # A short initial service period keeps this a focused deterministic test.
    r.update(end_date="2025-07-02")
    r["billing_cycles"]=driver.calendar_cycles(r["start_date"],r["end_date"])
    r["billing_cycles"][0]["kind"]="initial"
    r["account"]["proration_denominator_days"]=31
    r["account"].update(residential_tier_block_factor=2/31,residential_tier_block_confirmed=True,
        residential_tier_block_source="Explicit synthetic test fixture for a confirmed two-day block allocation")
    native=pd.read_csv(io.StringIO(r["load"]["csv"]))
    r["load"]["csv"]=native.iloc[:192].to_csv(index=False)
    (tmp_path/"engine.json").write_text(json.dumps({"id":"offline-test"}))
    execute(tmp_path,r)
    rows,lines,physics=driver.audit(tmp_path,r,"offline-test")
    assert len(rows)==3 and set(rows.scenario)==set(driver.SCENARIOS)
    assert len(physics)==3 and all(x["checked_intervals"]==192 for x in physics)
    assert not lines.empty
    file=tmp_path/"billing-components.csv"
    broken=pd.read_csv(file);broken.loc[0,"amount_usd"]+=1;broken.to_csv(file,index=False)
    with pytest.raises(AssertionError,match="Saved bill component differs"):
        driver.audit(tmp_path,r,"offline-test")


def test_private_summary_preserves_failure_scope_and_excludes_raw_inputs(tmp_path,monkeypatch):
    monkeypatch.setattr(driver,"ROOT",tmp_path)
    root=tmp_path/".cache"/"summary";folder=root/"runs"/"one";folder.mkdir(parents=True)
    request=driver.case_request("pseg","residential","monthly",plan="RS")
    request["account"]["market_data"]={"csv_text":"RAW-INPUT-MUST-NOT-APPEAR"}
    (folder/"request.json").write_text(json.dumps(request))
    result={"is_complete_bill":False,"billing":{"grid_only":[{"excluded_components":["unverified_fixture_tax"],
        "source":{"url":"https://dataminer2.pjm.com/feed/rt_hrl_lmps?api_key=DUMMY-NOT-A-SECRET&year=2025"}}]},
        "input_provenance":{},"warnings":[],"optimization":{"grid_only":{"annual_optimum_proven":None,
            "cycles":[{"cost_optimum_proven":None,"minimum_cycling_proven":None,"reconciliation_difference_usd":0.}]}},
        "ac_validation":{"scenarios":[{"scenario":"grid_only","checked_intervals":1,"failed_intervals":0,
            "all_intervals_feasible":True,"electrical_measurements_complete":True}],"network_configuration":{"id":"fixture"}}}
    (folder/"result.json").write_text(json.dumps(result))
    pd.DataFrame([dict(scenario="grid_only",utility_bill_usd=10.,savings_vs_grid_usd=0.,import_kwh=.75,
        export_kwh=0.,estimated_battery_wear_usd=float("nan"))]).to_csv(folder/"comparison.csv",index=False)
    pd.DataFrame({"native_load_kw":[3.]}).to_csv(folder/"inputs.csv",index=False)
    manifest={"engine_id":"pinned-fixture","driver_sha256":"f"*64,"scope":"test",
        "cases":[{"case":"passed","utility":"pseg","class":"residential","period":"monthly",
                  "study_id":"one","status":"completed","validation":"passed"},
                 {"case":"failed","validation":"failed","error":"Primary optimum not proven"},
                 {"case":"pending","status":"queued"}]}
    (root/"validation.json").write_text(json.dumps(manifest))
    out=driver.summarize(root)
    assert (out["passed"],out["failed"],out["pending"])==(1,1,1)
    assert out["cases"][0]["is_complete_bill"] is False
    assert "subtotal" in out["cases"][0]["reported_amount_kind"]
    assert out["cases"][0]["excluded_components"]==["unverified_fixture_tax"]
    proof=out["cases"][0]["scenarios"][0]["optimization"]
    assert proof["primary_proof_methods"]=={"legacy_not_recorded":1}
    assert proof["maximum_primary_gap_usd"] is None
    saved=(root/"validation-summary.json").read_text()
    assert "RAW-INPUT-MUST-NOT-APPEAR" not in saved
    assert "DUMMY-NOT-A-SECRET" not in saved
    assert "NaN" not in saved
    assert "https://dataminer2.pjm.com/feed/rt_hrl_lmps?year=2025" in out["source_urls"]


@pytest.mark.parametrize("period,start,end,message",[
    ("custom",None,None,"together"),("custom","2026-01-01",None,"together"),
    ("custom",None,"2026-09-30","together"),("monthly","2026-01-01","2026-09-30","only for"),
    ("annual","2026-01-01","2026-09-30","only for"),
    ("custom","2026-1-1","2026-09-30","YYYY-MM-DD"),
    ("custom","2026-02-30","2026-09-30","YYYY-MM-DD"),
    ("custom","2026-09-30","2026-01-01","ordered"),
    ("custom","2025-12-15","2026-01-15","one calendar year"),
    ("custom","2025-01-01","2026-12-31","1–366"),
])
def test_custom_bounds_reject_ambiguous_or_shifted_periods(period,start,end,message):
    with pytest.raises(ValueError,match=message):
        driver.custom_bounds(period,start,end)


def test_custom_bounds_allow_one_complete_leap_year_but_do_not_call_it_annual():
    assert driver.custom_bounds("custom","2024-01-01","2024-12-31")==("2024-01-01","2024-12-31")
    with pytest.raises(ValueError,match="custom alone"):
        driver.validation_periods(("monthly","custom"),"2025-01-01","2025-03-31")


def test_custom_pseg_reuses_full_year_native_intervals_and_recomputes_obligations():
    annual=driver.case_request("pseg","commercial","annual",plan="GLP")
    r=driver.case_request("pseg","commercial","custom",plan="GLP",start_date="2025-04-01",end_date="2025-07-31")
    a=pd.read_csv(io.StringIO(annual["load"]["csv"]))
    c=pd.read_csv(io.StringIO(r["load"]["csv"]))
    timestamps=pd.DatetimeIndex(pd.to_datetime(a.timestamp,utc=True)).tz_convert("America/New_York")
    pd.testing.assert_frame_equal(a.loc[(timestamps.month>=4)&(timestamps.month<=7)].reset_index(drop=True),c)
    assert len(r["billing_cycles"])==4 and "custom" in r["name"] and "annual" not in r["name"]
    assert "2025-04-01" in r["name"] and "2025-07-31" in r["name"]
    first,june=r["billing_cycles"][0],r["billing_cycles"][2]
    assert first["account_overrides"]["obligation_effective_start"]=="2024-06-01"
    assert june["account_overrides"]["obligation_effective_start"]=="2025-06-01"
    assert "synthetic" in r["load"]["source"]


def test_custom_nc_midmonth_history_uses_billing_month_and_preserves_dst():
    r=driver.case_request("dominion_energy_north_carolina","residential","custom",plan="1T",
        start_date="2025-02-15",end_date="2025-04-14")
    grid,_,cycles,_=prepare(r)
    assert r["account"]["history_billing_months"]==[3,4,5,6,7,8,9,10,11,12,1]
    assert len(cycles)==3 and len(grid.index)==59*96-4
    stamps=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(io.StringIO(r["load"]["csv"])).timestamp,utc=True))
    assert stamps.is_unique and np.all(np.diff(stamps.asi8)==pd.Timedelta(minutes=15).value)
    assert r["billing_cycles"][0]["source"].startswith("Explicit hypothetical")


@pytest.mark.parametrize("kind,plan,allow_history",[("residential","VA-1G",False),("commercial","VA-GS2T",False),("residential","VA-1",True)])
def test_all_va_custom_opening_histories_rebase_without_relabeling_2026_as_2025_tax_gap(monkeypatch,kind,plan,allow_history):
    # This fixture verifies request construction independently of the separate
    # reconstruction of historical tariffs. It does not enable unsupported dates.
    monkeypatch.setattr(driver,"prepare",lambda request:None)
    original=driver.defaults("dominion_energy_virginia",kind,plan)
    r=driver.case_request("dominion_energy_virginia",kind,"custom",plan=plan,allow_va_history=allow_history,
        start_date="2026-01-01",end_date="2026-09-30")
    assert [row["billing_month"] for row in r["account"]["history"]]==list(range(2,13))
    assert [row["maximum_kw"] for row in r["account"]["history"]]==[row["maximum_kw"] for row in original["account"]["history"]]
    assert r["account"]["contract_demand_kw"]==original["account"]["contract_demand_kw"]
    assert len(r["billing_cycles"])==9 and "subtotal" not in r["name"]
    native=pd.read_csv(io.StringIO(r["load"]["csv"]))
    assert len(native)==273*96-4 and r["load"]["mode"]=="csv"


def test_custom_va2025_still_requires_explicit_subtotal_opt_in():
    with pytest.raises(ValueError,match="include-va-history"):
        driver.case_request("dominion_energy_virginia","residential","custom",plan="VA-1",
            start_date="2025-01-01",end_date="2025-03-31")


@pytest.mark.parametrize("arguments",[
    ["--period","custom"],
    ["--period","custom","--start-date","2026-01-01"],
    ["--period","monthly","--start-date","2026-01-01","--end-date","2026-09-30"],
    ["--period","custom","--period","annual","--start-date","2026-01-01","--end-date","2026-09-30"],
    ["--prepare-inputs","--period","custom","--start-date","2026-01-01","--end-date","2026-09-30"],
])
def test_cli_custom_contract_rejects_before_any_execution_or_weather(monkeypatch,arguments):
    monkeypatch.setattr(driver,"run",lambda *args,**kwargs:pytest.fail("Invalid custom request must not run"))
    monkeypatch.setattr(driver,"prepare_inputs",lambda *args,**kwargs:pytest.fail("Custom weather must not silently retrieve default September"))
    monkeypatch.setattr(driver.sys,"argv",["driver","--execute",*arguments])
    with pytest.raises(SystemExit) as error:
        driver.main()
    assert error.value.code==2


def test_cli_custom_forwards_dates_and_keeps_its_period_label(monkeypatch):
    seen=[]
    monkeypatch.setattr(driver,"run",lambda *args,**kwargs:seen.append(kwargs))
    monkeypatch.setattr(driver.sys,"argv",["driver","--execute","--utility","dominion_energy_virginia",
        "--plan","VA-1G","--plan","VA-GS2T","--period","custom","--start-date","2026-01-01","--end-date","2026-09-30"])
    driver.main()
    assert seen[0]["periods"]==("custom",)
    assert seen[0]["start_date"]=="2026-01-01" and seen[0]["end_date"]=="2026-09-30"
    assert {row[2] for row in seen[0]["cases"]}=={"VA-1G","VA-GS2T"}


def test_run_checks_custom_bounds_before_creating_store(tmp_path,monkeypatch):
    from src.local_web import runtime
    monkeypatch.setattr(runtime,"Application",lambda *args,**kwargs:pytest.fail("No store before date validation"))
    with pytest.raises(ValueError,match="together"):
        driver.run(tmp_path,tmp_path,periods=("custom",),start_date="2026-01-01")


def era5_period(start,end):
    from src.profiles.era5 import VARIABLES
    timestamps=pd.date_range(start,end,freq="h",inclusive="left",tz="UTC")
    raw={"latitude":37.63,"longitude":-77.52,"utc_offset_seconds":0,"timezone":"UTC",
        "hourly_units":{"time":"iso8601",**{key:spec[1] for key,spec in VARIABLES.items()}},
        "hourly":{"time":timestamps.strftime("%Y-%m-%dT%H:%M").tolist(),
            **{key:([20.]*len(timestamps) if key=="temperature_2m" else [1.]*len(timestamps) if key=="wind_speed_10m" else [0.]*len(timestamps)) for key in VARIABLES}}}
    return {"provider":"open_meteo_era5","raw_json":json.dumps(raw),"retrieved_at":"2026-10-15T00:00:00Z",
        "request":{"latitude":37.63,"longitude":-77.52,"start_date":start,"end_date":end,"models":"era5","timezone":"UTC","wind_speed_unit":"ms"}}


def test_custom_va_era5_uses_unchanged_long_source_and_rejects_missing_period(tmp_path,monkeypatch):
    from src.profiles import era5
    monkeypatch.setattr(driver,"ROOT",tmp_path)
    monkeypatch.setattr(era5,"fetch_era5",lambda **kwargs:pytest.fail("No live weather or fallback"))
    parent=tmp_path/".cache"/"weather";source=parent/"dominion_energy_virginia";source.mkdir(parents=True)
    path=source/"era5.json";path.write_text(json.dumps(era5_period("2026-08-01","2026-10-02")))
    original=path.read_bytes()
    r=driver.case_request("dominion_energy_virginia","residential","custom",plan="VA-1G",
        start_date="2026-09-01",end_date="2026-09-30")
    app=SimpleNamespace(resource=lambda *args,**kwargs:pytest.fail("ERA5 never substitutes NSRDB"))
    driver.attach_weather(app,r,parent)
    assert r["weather_source"]=="era5" and r["weather_id"] is None
    assert r["weather"]["raw_json"]==json.loads(original)["raw_json"]
    assert path.read_bytes()==original
    path.write_text(json.dumps(era5_period("2026-09-01","2026-09-20")))
    with pytest.raises(ValueError,match="entire requested period"):
        driver.attach_weather(app,r,parent)
    assert r["weather_source"]=="era5"


def test_custom_non_va_never_relabels_prepared2025_nsrdb_as2026(tmp_path,monkeypatch):
    monkeypatch.setattr(driver,"ROOT",tmp_path)
    r=driver.case_request("pseg","residential","custom",plan="RS",start_date="2026-01-01",end_date="2026-02-28")
    app=SimpleNamespace(resource=lambda *args,**kwargs:pytest.fail("Wrong-year resource cannot be bound"))
    with pytest.raises(ValueError,match="no weather-year substitution"):
        driver.attach_weather(app,r,tmp_path/".cache"/"inputs")


def test_run_custom_identity_forwarding_and_catalog_based_scope(tmp_path,monkeypatch):
    """Orchestration only: mocked worker does not establish tariff coverage."""
    from src.local_web import runtime
    monkeypatch.setattr(driver,"ROOT",tmp_path)
    src=tmp_path/"src";src.mkdir();(src/"fixture.py").write_text("# immutable source fixture\n")
    output=tmp_path/".cache"/"run";seen=[];closed=[]
    identity="a"*32
    class App:
        def __init__(self,directory):
            self.engine={"id":"frozen-fixture","files":{"src/fixture.py":driver.digest(src/"fixture.py")}}
            self.store=SimpleNamespace(submit=self.submit,get=lambda study:{"status":"completed","progress":"done"})
        def submit(self,request,engine):
            run=output/"runs"/identity;run.mkdir(parents=True)
            (run/"request.json").write_text(json.dumps(request))
            (run/"result.json").write_text(json.dumps({"engine_id":engine["id"]}))
            pd.DataFrame([{"scenario":"grid_only","utility_bill_usd":10.}]).to_csv(run/"comparison.csv",index=False)
            return {"id":identity}
        def close(self):
            closed.append(True)
    def request(utility,kind,period,**kwargs):
        seen.append((utility,kind,period,kwargs))
        return {"start_date":kwargs["start_date"],"end_date":kwargs["end_date"]}
    monkeypatch.setattr(runtime,"Application",App)
    monkeypatch.setattr(driver,"case_request",request)
    monkeypatch.setattr(driver,"attach_weather",lambda *args:None)
    monkeypatch.setattr(driver,"summarize",lambda *args:None)
    monkeypatch.setattr(driver,"audit",lambda *args,**kwargs:(
        pd.DataFrame([{"scenario":"grid_only","is_complete_bill":True,"objective_scope":"complete_utility_bill","rate_evidence_status":"not_recorded"}]),
        pd.DataFrame([{"scenario":"grid_only","component":"customer","amount_usd":10.}]),[]))
    result=driver.run(output,tmp_path/".cache"/"weather",cases=[("dominion_energy_virginia","residential","VA-1G")],
        periods=("custom",),start_date="2026-01-01",end_date="2026-06-30")
    assert seen[0][2]=="custom" and seen[0][3]["start_date"]=="2026-01-01" and seen[0][3]["end_date"]=="2026-06-30"
    assert result["cases"][0]["period"]=="custom"
    assert result["cases"][0]["case"].endswith("custom-2026-01-01_to_2026-06-30")
    assert result["custom_date_bounds"]["interpretation"].endswith("not an annual case")
    scope=result["blocked_scope"]["dominion_energy_virginia_2025"]
    assert "2026 January-August remain unavailable" not in scope
    assert "2026 coverage follows the pinned Virginia catalog" in scope
    assert "rejects missing intermediate component versions" in scope
    assert closed==[True]
