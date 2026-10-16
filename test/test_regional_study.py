"""Production main-form serialization, immutable worker and saved results."""
from copy import deepcopy
import json
import subprocess
from urllib.error import HTTPError

import numpy as np
import pandas as pd
import pytest

from src.local_web.regional_study import defaults,prepare,calendar_cycles
from test_local_web import service,wait_for_study
from test_local_web_hosting import hosted,signin


def request(utility="dominion_energy_virginia",kind="residential"):
    r=defaults(utility,kind)
    r["timestep_minutes"]=30
    r["operating_contract"].update(interconnection_confirmed=True,grid_charging_confirmed=True,
        reference="Explicit hypothetical approved non-export PV/storage account")
    if utility.endswith("virginia"):
        r["account"].update(parallel_service=True,parallel_operation_approved=True)
    if kind=="commercial":
        r["end_date"]=r["start_date"][:8]+"02"
        r["billing_cycles"]=calendar_cycles(r["start_date"],r["end_date"])
        if utility=="pseg":r["account"]["proration_denominator_days"]=31
    return r


def browser_request(r):
    v={**r["site"],**r["solar"],**(r["battery"] or {}),
        **{k:r[k] for k in ("site_profile","start_date","end_date","timestep_minutes","pv_capacity_kw","regional_account","account","electrical_service","weather_source","degradation_cost_per_kWh","include_degradation_in_optimization")},
        "cycles":r["billing_cycles"],"site_label":r["site"]["label"],"pv_choice":"yes" if r["solar"]["dc_capacity_kw"] else "storage" if r["battery"] else "no",
        "rg_battery":r["battery"] is not None,"rg_export":r["operating_contract"]["mode"],"rg_interconnection":True,
        "rg_grid_charge":r["operating_contract"]["grid_charging_confirmed"],"rg_pv_charge":r["operating_contract"]["renewable_only_charging"],
        "rg_operation_source":r["operating_contract"]["reference"],"rg_credit_policy":r["credit_objective_policy"],
        "load_mode":r["load"]["mode"],"load_power_kw":r["load"]["power_kw"],"archetype":r["load"]["archetype"],
        "rg_load_source":r["load"]["source"],"rg_native_confirmed":r["load"]["native_basis_confirmed"],
        "rg_alternative":r.get("tariff_comparisons",[""])[0] if r.get("tariff_comparisons") else "",
        "native_csv":r["load"]["csv"],"ess":r["ess"],"weather_id":r["weather_id"],"era5":r["weather"]}
    js="const fs=require('fs');const x=JSON.parse(fs.readFileSync(0,'utf8'));const {buildRegionalStudyRequest}=require('./src/local_web/static/regional.js');process.stdout.write(JSON.stringify(buildRegionalStudyRequest(x.base,x.values)));"
    return json.loads(subprocess.run(["node","-e",js],input=json.dumps({"base":r,"values":v}),text=True,capture_output=True,check=True).stdout)


@pytest.mark.parametrize("utility",["dominion_energy_virginia","dominion_energy_north_carolina","pseg"])
@pytest.mark.parametrize("kind",["residential","commercial"])
def test_main_form_to_pinned_worker_save_restore_download(service,utility,kind):
    app,call,headers=service
    r=browser_request(request(utility,kind))
    prepare(r)
    caps=call("/api/capabilities")
    assert caps["regional_simulation"]["schema_version"]==11
    assert b'regional.js' in call("/")
    assert "src/billing/pseg_rates.py" in app.engine["files"]
    study=call("/api/v1/regional/studies",r,headers)
    out=wait_for_study(call,study["id"])
    assert out["status"]=="completed",out.get("error")
    result=out["result"]
    assert result["engine_id"]==app.engine["id"]
    assert result["ac_validation"]["all_intervals_feasible"]
    assert len(result["ac_validation"]["scenarios"])==3
    base="/api/studies/"+study["id"]
    table=call(base+"/tables/comparison")
    records=[dict(zip(table["columns"],row)) for row in table["data"]]
    assert {row["scenario"] for row in records}=={"grid_only","pv_only","pv_battery"}
    assert all(row["is_complete_bill"] for row in records)
    assert max(row["maximum_reconciliation_difference_usd"] for row in records)<.0001
    assert all(row["all_intervals_feasible"] for row in records)
    assert next(row for row in records if row["scenario"]=="grid_only")["all_cycle_cost_optima_proven"] is None
    assert b"pv_curtailed_kw" in call(base+"/tables/dispatch-pv_battery.csv")
    assert b"scheduled_grid" in call(base+"/tables/ac-pv_battery.csv")
    assert len(call(base+"/tables.zip"))>0
    call(base+"/save",{"name":utility+" "+kind+" validation"},headers)
    reopened=call(base)
    assert reopened["saved"] and reopened["request"]["name"].endswith("validation")
    restored=call(base+"/request.json")
    assert restored["account"]==r["account"]
    assert restored["regional_account"]==r["regional_account"]
    assert browser_request(restored)["account"]==r["account"]


def test_regions_do_not_derive_account_identity_from_state_or_node():
    r=request()
    r["regional_account"]["state_jurisdiction"]="NC"
    with pytest.raises(ValueError,match="independently consistent"):prepare(r)
    r=request();r["regional_account"]["retail_supplier"]="third_party"
    with pytest.raises(ValueError,match="contract"):prepare(r)


def test_va_defaults_keep_the_hypothetical_account_and_history_month():
    r=defaults("dominion_energy_virginia","residential")
    assert r["start_date"]=="2026-09-01"
    assert r["end_date"]=="2026-09-30"
    assert r["account"]["billing_month"]==9
    assert r["account"]["history"][-1]["billing_month"]==8
    # January is supported; it does not replace the declared reference month.
    from src.billing.regional import adapter
    plan=next(p for p in adapter("dominion_energy_virginia").catalog() if p["id"]==r["account"]["tariff"])
    assert plan["coverage"][-1]["start"]=="2026-01-01"


def test_incomplete_cycles_and_primary_service_mismatch_reject():
    r=request()
    r["billing_cycles"][0]["end_date"]=(pd.Timestamp(r["end_date"])-pd.DateOffset(days=1)).date().isoformat()
    with pytest.raises(ValueError,match="uncovered"):prepare(r)
    r=request();r["electrical_service"]["voltage"]="primary"
    with pytest.raises(ValueError,match="classification"):prepare(r)
    r=request();r["electrical_service"]["nominal_voltage_v"]=208
    with pytest.raises(ValueError,match="nominal volts"):prepare(r)


def test_native_csv_and_absent_equipment_are_explicit(tmp_path):
    from src.local_web.regional_study import execute
    r=request("pseg")
    grid,load,*_=prepare(r)
    r["load"].update(mode="csv",power_kw=None,archetype=None,native_basis_confirmed=True,
        csv=pd.DataFrame({"timestamp":grid.index,"native_load_kw":load}).to_csv(index=False))
    r["solar"]["dc_capacity_kw"]=r["pv_capacity_kw"]=0;r["battery"]=None
    (tmp_path/"engine.json").write_text(json.dumps({"id":"offline-absence-test"}))
    execute(tmp_path,r)
    result=json.loads((tmp_path/"result.json").read_text())
    assert len(result["billing"])==1
    assert result["ac_validation"]["all_intervals_feasible"]
    dispatch=pd.read_csv(tmp_path/"dispatch-grid_only.csv")
    assert dispatch[["pv_output_kw","pv_curtailed_kw","energy_kWh","battery_charge_kw","battery_discharge_kw"]].eq(0).all().all()
    with pytest.raises(ValueError,match="native consumption"):
        prepare({**r,"load":{**r["load"],"native_basis_confirmed":False}})


@pytest.mark.parametrize("utility",["dominion_energy_virginia","dominion_energy_north_carolina","pseg"])
def test_main_form_storage_only_reconciles_without_pv_or_weather(service,utility):
    """The absence of PV must survive serialization, queueing and AC replay."""
    from io import StringIO
    app,call,headers=service
    r=request(utility)
    r["end_date"]=r["start_date"][:8]+"02"
    r["billing_cycles"]=calendar_cycles(r["start_date"],r["end_date"])
    r["billing_cycles"][0].update(kind="initial",source="Explicit hypothetical complete initial two-day cycle")
    if utility=="pseg":
        r["account"].update(proration_denominator_days=31,residential_tier_block_factor=1.,
            residential_tier_block_confirmed=True,
            residential_tier_block_source="Explicit hypothetical utility-confirmed full initial-cycle block")
    r["solar"]["dc_capacity_kw"]=r["pv_capacity_kw"]=0.
    r=browser_request(r)
    assert r["battery"] is not None and r["solar"]["dc_capacity_kw"]==0
    study=call("/api/v1/regional/studies",r,headers)
    out=wait_for_study(call,study["id"])
    assert out["status"]=="completed",out.get("error")
    result=out["result"]
    assert result["engine_id"]==app.engine["id"]
    assert set(result["billing"])=={"grid_only","storage_only"}
    assert result["ac_validation"]["all_intervals_feasible"]
    base="/api/studies/"+study["id"]
    frame=pd.read_csv(StringIO(call(base+"/tables/dispatch-storage_only.csv").decode()))
    assert frame[["pv_available_kw","pv_output_kw","pv_curtailed_kw","grid_export_kw"]].eq(0).all().all()
    assert np.max(abs(frame.grid_import_kw+frame.battery_discharge_kw-frame.native_load_kw-frame.battery_charge_kw))<1e-5
    assert np.max(np.minimum(frame.battery_charge_kw,frame.battery_discharge_kw))<1e-5
    proof=result["optimization"]["storage_only"]["cycles"][0]
    assert proof["cost_optimum_proven"]
    assert proof["reconciliation_difference_usd"]<.0001
    changes=.5*(frame.battery_charge_kw*r["battery"]["charge_efficiency"]-frame.battery_discharge_kw/r["battery"]["discharge_efficiency"])
    assert np.max(abs(np.r_[frame.energy_kWh.to_numpy()[1:],proof["terminal_energy_kwh"]]-frame.energy_kWh-changes))<1e-5
    assert proof["terminal_energy_kwh"]==pytest.approx(r["battery"]["energy_kWh"],abs=1e-5)


def test_eastern_replay_retains_dst_and_soc_end_convention():
    from src.local_web.electrical_replay import scheduled_frame
    from src.local_web.regional_study import _json_value
    idx=pd.date_range("2025-11-02",periods=100,freq="15min",tz="America/New_York")
    frame=pd.DataFrame({"timestamp":idx,"native_load_kw":1.,"pv_available_kw":0.,"grid_import_kw":1.,"grid_export_kw":0.})
    replay=scheduled_frame(frame,timezone="America/New_York")
    assert len(replay)==100 and replay.timestamp.iloc[0].utcoffset()!=replay.timestamp.iloc[-1].utcoffset()
    assert _json_value({"number":np.float64(1),"when":idx[0]})["number"]==1


def test_hosted_mode_cannot_expose_new_private_candidate(hosted):
    app,auth,call,_=hosted;headers,caps=signin(call,"regional-reviewer")
    r=request()
    assert call("/api/v1/regional/studies",r,headers)[0]==400
    assert call("/api/v1/regional/weather",{},headers)[0]==400
    from src.local_web.auth import digest
    job=app.store.submit(r,app.engine,digest("regional-reviewer"))
    for suffix in ("","/request.json","/result.json","/tables.zip"):
        assert call("/api/studies/"+job["id"]+suffix,headers=headers)[0]==403


def test_alternative_tariff_uses_same_inputs_and_distinct_reconciled_ledgers(tmp_path):
    from src.local_web.regional_study import execute
    import hashlib
    r=request("dominion_energy_north_carolina")
    r["start_date"]="2025-07-01";r["end_date"]="2025-07-02"
    r["billing_cycles"]=calendar_cycles(r["start_date"],r["end_date"])
    r["tariff_comparisons"]=["1"]
    r["solar"]["dc_capacity_kw"]=r["pv_capacity_kw"]=0.;r["battery"]=None
    assert browser_request(r)["tariff_comparisons"]==["1"]
    (tmp_path/"engine.json").write_text(json.dumps({"id":"offline-alternative-test"}))
    execute(tmp_path,r)
    result=json.loads((tmp_path/"result.json").read_text())
    assert result["input_provenance"]["request_sha256"]==hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()
    table=pd.read_csv(tmp_path/"comparison.csv")
    assert set(table.tariff)=={"1T","1"}
    assert set(table.scenario)=={"grid_only","alt1-grid_only"}
    assert table.import_kwh.nunique()==1
    assert result["tariff_comparison"]["same_schedule_repricing"] is False
    assert len(result["ac_validation"]["scenarios"])==2
    assert (tmp_path/"alt1-ac-grid_only.csv").exists()
    assert set(result["billing"])==set(table.scenario)


@pytest.mark.parametrize("utility",["dominion_energy_virginia","dominion_energy_north_carolina","pseg"])
def test_net_metering_has_explicit_absent_pv_grid_reference(tmp_path,utility):
    from src.local_web.regional_study import execute
    from src.billing.regional import adapter
    r=request(utility)
    if utility.endswith("virginia"):
        # Ordinary2026 coverage now starts in January, while the verified NEM
        # terms start February5. Exercise the solar counterfactual within its
        # separately supported enrollment period.
        r["start_date"]="2026-09-01"
    r["end_date"]=r["start_date"][:8]+"02"
    r["billing_cycles"]=calendar_cycles(r["start_date"],r["end_date"])
    r["billing_cycles"][0].update(kind="initial",source="Explicit hypothetical complete two-day initial meter cycle")
    r["battery"]=None
    r["operating_contract"].update(mode="net_metering",grid_charging_confirmed=False)
    a=r["account"]
    if utility.endswith("virginia"):
        a.update(solar_mode="net_metering",nem=adapter(utility).nem_defaults(a["tariff"],r["start_date"]))
    elif utility.endswith("carolina"):
        a.update(solar_program="net_metering",net_metering_confirmed=True,recs_assignment_confirmed=True)
    else:
        a.update(export_mode="net_metering",net_metering_confirmed=True,net_metering_size_confirmed=True,
            residential_tier_block_factor=1.,residential_tier_block_confirmed=True,
            residential_tier_block_source="Explicit hypothetical utility-confirmed full block")
        a["proration_denominator_days"]=31
    (tmp_path/"engine.json").write_text(json.dumps({"id":"offline-nem-counterfactual"}))
    execute(tmp_path,r)
    result=json.loads((tmp_path/"result.json").read_text())
    assert result["grid_only_reference"]["applied"]
    assert set(result["billing"])=={"grid_only","pv_only"}
    assert result["ac_validation"]["all_intervals_feasible"]
    assert pd.read_csv(tmp_path/"dispatch-grid_only.csv").pv_output_kw.eq(0).all()
    assert any("counterfactual" in w for w in result["warnings"])
