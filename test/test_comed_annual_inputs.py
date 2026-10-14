"""Annual imports retain physical hours, native consumption and weather evidence."""
from io import StringIO
import hashlib
import json
import subprocess

import numpy as np
import pandas as pd
import pytest

from src.local_web.comed_simulation import prepare
from src.local_web.comed_study import _csv_series
from src.local_web.site_inputs import build_site_generation
from tools.run_comed_year_validation import request
from test_local_web import service, wait_for_study


def imported(kind="residential", minutes=30):
    r = request(kind)
    r["timestep_minutes"] = minutes
    grid, load, _, _ = prepare(r)
    r["load"].update(mode="csv", power_kw=None, archetype=None,
        native_basis_confirmed=True, source="Synthetic annual import fixture; native demand",
        csv=pd.DataFrame({"timestamp": grid.index, "native_load_kw": load}).to_csv(index=False))
    hours = grid.index.tz_convert("UTC").floor("h").unique()
    r["account"].update(supply="BESH", capacity_obligation_kw=2.,
        capacity_source="Synthetic fixed obligation, not measured or inferred from load")
    r["prices"] = dict(mode="csv", usd_per_mwh=None, basis_confirmed=True,
        source="Synthetic COMED residual hourly price fixture; not observed market data",
        csv=pd.DataFrame({"timestamp": hours, "residual_lmp_usd_per_mwh":
                          np.where(hours.hour % 2, -5., 70.)}).to_csv(index=False))
    return r, grid, load


@pytest.mark.parametrize("kind,minutes", [("residential",15), ("residential",30),
                                          ("residential",60), ("commercial",30)])
def test_full_year_native_and_signed_hourly_imports(kind, minutes):
    r, expected, load = imported(kind, minutes)
    grid, actual, _, prices = prepare(r)
    assert np.allclose(actual, load, atol=1e-12, rtol=0)
    assert grid.index.equals(expected.index) and len(prices.values) == 8760
    assert (prices.values < 0).any()
    assert sum(grid.index.month == 3)*grid.timestep_hours == 743
    assert sum(grid.index.month == 11)*grid.timestep_hours == 721
    fold = prices.values.index.tz_convert("America/Chicago")
    assert len(fold[(fold.month == 11)&(fold.day == 2)&(fold.hour == 1)]) == 2


@pytest.mark.parametrize("target,error", [("load","missing"),("load","duplicate"),
    ("load","reordered"),("load","naive"),("load","negative"),("load","nonfinite"),
    ("prices","missing"),("prices","duplicate"),("prices","naive"),
    ("prices","nonfinite"),("prices","hour_ending")])
def test_annual_imports_never_fill_or_shift_records(target, error):
    r, _, _ = imported()
    frame = pd.read_csv(StringIO(r[target]["csv"]))
    value = frame.columns[1]
    if error == "missing": frame = frame.drop(5000)
    if error == "duplicate": frame.iloc[5000] = frame.iloc[4999]
    if error == "reordered": frame = frame.iloc[::-1]
    if error == "naive": frame["timestamp"] = pd.to_datetime(frame.timestamp,utc=True).dt.tz_localize(None)
    if error == "negative": frame.loc[5000,value] = -1
    if error == "nonfinite": frame.loc[5000,value] = float("inf")
    if error == "hour_ending": frame["timestamp"] = pd.to_datetime(frame.timestamp,utc=True)+pd.Timedelta(hours=1)
    r[target]["csv"] = frame.to_csv(index=False)
    with pytest.raises(ValueError): prepare(r)


def test_legacy_monthly_import_limit_and_leap_year_hourly_limit():
    frame = pd.DataFrame({"timestamp": pd.date_range("2024-01-01",periods=8784,freq="h",tz="UTC"),
                          "residual_lmp_usd_per_mwh": 1.})
    with pytest.raises(ValueError,match="6000"): _csv_series(frame.to_csv(index=False),frame.columns[1])
    assert len(_csv_series(frame.to_csv(index=False),frame.columns[1],max_rows=8784)) == 8784
    with pytest.raises(ValueError,match="MiB"): _csv_series("x"*(2*1024*1024+1),frame.columns[1],max_rows=8784)


def test_historical_weather_requires_matching_id_year_and_unchanged_bytes(tmp_path):
    r = request("residential")
    r.update(start_date="2025-03-01", end_date="2025-03-31")
    r.pop("billing_cycles");r["account"]["billing_month"] = "2025-03-01"
    grid, _, _, _ = prepare(r)
    r["weather_source"] = "nsrdb"
    with pytest.raises(ValueError,match="Retrieve matching"): prepare(r)
    r["weather_id"] = "a"*64
    prepare(r)
    frame = pd.DataFrame({"timestamp": grid.index, "ghi_w_per_m2":0., "dni_w_per_m2":0.,
        "dhi_w_per_m2":0., "temperature_c":10., "wind_speed_m_per_s":2.})
    path = tmp_path/"weather.csv";frame.to_csv(path,index=False)
    meta = dict(request=dict(latitude=r["site"]["latitude"],longitude=r["site"]["longitude"],
        timezone=r["timezone"],year=2025,timestep_minutes=30),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        provenance={"source":"Synthetic weather fixture"},warnings=[])
    (tmp_path/"weather.json").write_text(json.dumps(meta))
    pv, _, provenance, _ = build_site_generation(r,tmp_path,grid)
    assert pv.pv_available_kw.eq(0).all() and provenance["saved_weather_sha256"] == meta["sha256"]
    meta["request"]["year"] = 2024;(tmp_path/"weather.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError,match="never shifted"): build_site_generation(r,tmp_path,grid)
    meta["request"]["year"] = 2025;(tmp_path/"weather.json").write_text(json.dumps(meta))
    path.write_text(path.read_text()+"\n")
    with pytest.raises(ValueError,match="checksum changed"): build_site_generation(r,tmp_path,grid)


@pytest.mark.parametrize("mode", ["csv","pjm_csv"])
def test_browser_annual_builder_declares_cycles_and_preserves_full_inputs(mode):
    r, grid, _ = imported()
    if mode=="pjm_csv":pjm_prices(r,grid.index.tz_convert("UTC").floor("h").unique())
    js = "const b=require('./src/local_web/static/comed_simulation.js').buildComedSimulationRequest;const fs=require('fs');const x=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(b(x.r,x.v)));"
    v = {**r["solar"], **r["battery"], **r["site"], "site_profile":r["site_profile"],
        "site_label":r["site"]["label"], "start_date":r["start_date"], "end_date":r["end_date"],
        "timestep_minutes":30,"ce_cycle_mode":"calendar_year","tariff_id":"comed_BESH",
        "ce_verification":"hypothetical_case","ce_reference":r["regional_account"]["reference"],
        "ce_class":r["account"]["delivery_class"],"ce_account_confirmed":True,
        "ce_capacity":2,"ce_capacity_source":r["account"]["capacity_source"],
        "ce_price_mode":mode,"price_csv":r["prices"]["csv"],"ce_price_source":r["prices"]["source"],
        "ce_price_retrieved_at":"2026-10-13T18:00:00Z",
        "ce_price_confirmed":True,"load_mode":"csv","native_csv":r["load"]["csv"],
        "ce_load_source":r["load"]["source"],"ce_native_confirmed":True,
        "pv_choice":"yes","pv_capacity_kw":r["pv_capacity_kw"],"ce_include_battery":True,
        "weather_source":"nsrdb","weather_id":"a"*64,"ess":None,
        "ce_nonexport":True,"ce_standard":True,"ce_grid_charge":True,
        "ce_operation_reference":r["operating_contract"]["reference"],
        "degradation_cost_per_kWh":.03,"include_degradation_in_optimization":False}
    result = json.loads(subprocess.run(["node","-e",js],input=json.dumps(dict(r=r,v=v)),
        text=True,capture_output=True,check=True).stdout)
    assert len(result["billing_cycles"]) == 12
    assert result["load"]["csv"] == r["load"]["csv"] and result["prices"]["csv"] == r["prices"]["csv"]
    assert result["weather_id"] == "a"*64
    prepare(result)


def pjm_prices(r, hours):
    frame = pd.DataFrame({"datetime_beginning_utc":hours,"pnode_id":116472935,
        "pnode_name":"COMED_RESID_AGG","zone":"","type":"RESIDUAL_METERED_EDC",
        "total_lmp_rt": np.where(hours.hour % 2, -5., 70.),
        "version_nbr":1,"row_is_current":True})
    r["prices"].update(mode="pjm_csv",usd_per_mwh=None,csv=frame.to_csv(index=False),pjm_metadata={
        "market":"REAL_TIME_HOURLY","source_url":"https://dataminer2.pjm.com/feed/rt_hrl_lmps",
        "retrieved_at":"2026-10-13T18:00:00Z","unit":"$/MWh","usage_permission":"internal_use_only"})
    return frame


def test_full_year_pjm_residual_import_preserves_revisions_and_cost_basis():
    r, grid, _ = imported()
    frame = pjm_prices(r,grid.index.tz_convert("UTC").floor("h").unique())
    old=frame.iloc[[0]].copy();old.row_is_current=False
    frame.loc[0,"version_nbr"]=2
    r["prices"]["csv"]=pd.concat([old,frame]).to_csv(index=False)
    _, _, _, prices = prepare(r)
    assert len(prices.values)==8760 and prices.values.iloc[0]==frame.total_lmp_rt.iloc[0]
    assert prices.provenance["revision_numbers"]==[1,2]
    assert prices.provenance["pricing_location"]["zone"]==""
    assert prices.provenance["raw_sha256"]==hashlib.sha256(r["prices"]["csv"].encode()).hexdigest()
    assert prices.provenance["public_download_allowed"] is False


def test_annual_compute_budget_still_rejects_unproven_primary_schedule(monkeypatch):
    import cvxpy as cp
    from src.dispatch.comed import optimize
    from src.billing.comed_cycles import parse_cycles
    r, _, _=imported("commercial")
    grid,load,account,prices=prepare(r)
    def unproven(problem,*args,**kwargs):
        assert kwargs["scipy_options"]["time_limit"]==300
        problem._status=cp.OPTIMAL_INACCURATE
    monkeypatch.setattr(cp.Problem,"solve",unproven)
    with pytest.raises(ValueError,match="did not prove optimality within 300 seconds"):
        optimize(pd.DataFrame({"timestamp":grid.index,"native_load_kw":load,"pv_available_kw":0.}),
            account,prices,r["battery"],billing_cycles=parse_cycles(r["billing_cycles"]))


@pytest.mark.parametrize("error", ["wrong_node","generic_zone","wrong_type","five_minute","missing","stale"])
def test_pjm_file_must_be_exact_residual_hourly_series(error):
    r,grid,_=imported();frame=pjm_prices(r,grid.index.tz_convert("UTC").floor("h").unique())
    if error=="wrong_node":frame.loc[0,"pnode_id"]=51288
    if error=="generic_zone":frame.loc[0,"zone"]="COMED"
    if error=="wrong_type":frame.loc[0,"type"]="ZONE"
    if error=="five_minute":r["prices"]["pjm_metadata"]["market"]="REAL_TIME_5_MIN"
    if error=="missing":frame=frame.drop(7000)
    if error=="stale":frame.loc[0,"row_is_current"]=False
    r["prices"]["csv"]=frame.to_csv(index=False)
    with pytest.raises(ValueError):prepare(r)


@pytest.mark.parametrize("kind", ["residential","commercial"])
def test_owned_historical_weather_and_pjm_file_through_immutable_worker(service,kind):
    app,call,headers=service
    r=request(kind);r.update(start_date="2025-03-01",end_date="2025-03-31")
    r.pop("billing_cycles");r["account"].update(billing_month="2025-03-01",supply="BESH",
        capacity_obligation_kw=2.,capacity_source="Synthetic fixed account obligation")
    r["prices"]=dict(mode="constant_example",usd_per_mwh=50.,csv=None,basis_confirmed=True,
        source="Synthetic PJM file fixture, not observed prices")
    grid,load,_,_=prepare(r)
    pjm_prices(r,grid.index.tz_convert("UTC").floor("h").unique())
    r["load"].update(mode="csv",power_kw=None,archetype=None,native_basis_confirmed=True,
        csv=pd.DataFrame({"timestamp":grid.index,"native_load_kw":load}).to_csv(index=False))
    r.update(weather_source="nsrdb",weather_id="b"*64)
    cache=app.store.directory/"weather"/r["weather_id"];cache.mkdir(exist_ok=True)
    pd.DataFrame({"timestamp":grid.index,"ghi_w_per_m2":0.,"dni_w_per_m2":0.,
        "dhi_w_per_m2":0.,"temperature_c":10.,"wind_speed_m_per_s":2.}).to_csv(cache/"weather.csv",index=False)
    meta=dict(request=dict(latitude=r["site"]["latitude"],longitude=r["site"]["longitude"],
        timezone=r["timezone"],year=2025,timestep_minutes=30),
        sha256=hashlib.sha256((cache/"weather.csv").read_bytes()).hexdigest(),
        provenance={"source":"Synthetic weather fixture"},warnings=[])
    (cache/"weather.json").write_text(json.dumps(meta));app.store.grant("weather",r["weather_id"],None)
    job=call("/api/v1/comed/simulations",r,headers)
    out=wait_for_study(call,job["id"])
    assert out["status"]=="completed",out.get("error")
    result=out["result"]
    assert result["input_provenance"]["pv"]["weather"]["saved_weather_sha256"]==meta["sha256"]
    assert result["input_provenance"]["wholesale_pricing_location"]["file_provenance"]["selected_rows"]==743
    assert result["ac_validation"]["all_intervals_feasible"]
    assert result["optimization"]["pv_battery"]["cost_optimum_proven"]
