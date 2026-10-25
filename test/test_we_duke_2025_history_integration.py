"""Historical study assumptions are explicit and preserve exact interval coverage."""
from copy import deepcopy
from io import BytesIO
import json
import subprocess
from urllib.error import HTTPError
from zipfile import ZipFile

import pandas as pd
import pytest

from src.billing.regional import adapter, cycle_partitions
from src.local_web.regional_study import calendar_cycles, defaults, prepare
from src.local_web.runtime import Store
from src.timeseries import build_interval_index
from tools.run_regional_validation import duke_2025_regular_cycles
from test_local_web import service, wait_for_study
from test_regional_study import browser_request


WE="we_energies_wisconsin"
DUKE="duke_energy_indiana"


def historical_request(utility, plan, kind, start="2025-07-01", end="2025-07-31"):
    r=defaults(utility,kind,plan)
    r.update(start_date=start,end_date=end,billing_cycles=calendar_cycles(start,end))
    r["account"].update(rate_evidence_mode="provisional_2025",provisional_assumptions_accepted=True)
    r["operating_contract"].update(interconnection_confirmed=True,grid_charging_confirmed=True,
        reference="Explicit hypothetical utility-approved non-export account; no actual customer bill")
    return r


def browser_evidence(plan, account, start, end):
    script="const fs=require('fs');const x=JSON.parse(fs.readFileSync(0,'utf8'));const {regionalRateEvidenceContext}=require('./src/local_web/static/regional.js');process.stdout.write(JSON.stringify(regionalRateEvidenceContext(x.plan,x.account,x.start,x.end)));"
    return json.loads(subprocess.run(["node","-e",script],input=json.dumps(dict(
        plan=plan,account=account,start=start,end=end)),text=True,capture_output=True,check=True).stdout)


@pytest.mark.parametrize("utility,plan,kind",[(WE,"Rg1","residential"),(DUKE,"RS","residential")])
@pytest.mark.parametrize("mode,accepted",[("provisional_2025",False),("provisional_2025","true"),
    ("provisional_2025",1),("verified","true"),("unknown",True)])
def test_invalid_evidence_opt_in_rejects_before_queue_or_saved_files(tmp_path,utility,plan,kind,mode,accepted):
    r=historical_request(utility,plan,kind)
    r["account"].update(rate_evidence_mode=mode,provisional_assumptions_accepted=accepted)
    store=Store(tmp_path)
    with pytest.raises(ValueError,match="explicitly accept|rate evidence"):
        store.submit(r,{"id":"not-executed"})
    assert store.list()==[] and not list((tmp_path/"runs").iterdir())


@pytest.mark.parametrize("utility,plan,kind",[(WE,"Rg1","residential"),(WE,"Cg1","commercial"),
    (DUKE,"RS","residential"),(DUKE,"CS","commercial")])
def test_full_year_prepare_requires_acceptance_and_keeps_verified_default(utility,plan,kind):
    r=historical_request(utility,plan,kind,"2025-01-01","2025-12-31")
    if utility==DUKE:r["billing_cycles"]=duke_2025_regular_cycles()
    serialized=browser_request(r)
    assert serialized["account"]==r["account"]
    grid,_,cycles,_=prepare(serialized)
    assert len(grid.index)==35040 and len(cycles)==12
    verified=deepcopy(r)
    verified["account"].update(rate_evidence_mode="verified",provisional_assumptions_accepted=False)
    with pytest.raises(ValueError,match="coverage|verified|ECC|March|window"):
        prepare(verified)
    # Saved requests created before evidence fields existed remain verified-only.
    verified["account"].pop("rate_evidence_mode")
    verified["account"].pop("provisional_assumptions_accepted")
    with pytest.raises(ValueError,match="coverage|verified|ECC|March|window"):
        prepare(verified)


def test_browser_provisional_controls_are_period_scoped_and_preserve_verified_coverage():
    plan=next(p for p in adapter(WE).catalog() if p["id"]=="Rg1")
    verified=dict(rate_evidence_mode="verified",provisional_assumptions_accepted=False)
    accepted=dict(rate_evidence_mode="provisional_2025",provisional_assumptions_accepted=True)
    original=deepcopy(plan)
    current=browser_evidence(plan,verified,"2026-07-01","2026-07-31")
    assert not current["show_controls"] and not current["assumptions"]
    missing=browser_evidence(plan,verified,"2025-07-01","2025-07-31")
    assert missing["show_controls"] and missing["relevant"] and len(missing["assumptions"])==1
    assert not any(w["start"]<="2025-07-01"<=w["end"] for w in missing["coverage"])
    enabled=browser_evidence(plan,accepted,"2025-01-01","2025-12-31")
    assert any(w["start"]<="2025-07-01"<=w["end"] for w in enabled["coverage"])
    # Opting in does not discard verified2026 windows or silently hide a saved opt-in.
    later=browser_evidence(plan,accepted,"2026-07-01","2026-07-31")
    assert later["show_controls"] and not later["relevant"] and not later["assumptions"]
    assert any(w["start"]<="2026-07-01"<=w["end"] for w in later["coverage"])
    assert plan==original
    duke=next(p for p in adapter(DUKE).catalog() if p["id"]=="RS")
    december=browser_evidence(duke,verified,"2025-12-20","2025-12-31")
    assert "DEI25-DECEMBER-CREDIT67" in {a["id"] for a in december["assumptions"]}


@pytest.mark.parametrize("utility,plan,start,end",[(WE,"Rg1","2026-07-01","2026-07-31"),
    (DUKE,"RS","2025-03-01","2025-03-31")])
def test_legacy_requests_and_opted_in_verified_dates_keep_actual_evidence(utility,plan,start,end):
    r=historical_request(utility,plan,"residential",start,end)
    grid,_,cycles,equipment=prepare(r)
    from src.billing.regional import cycle_account
    evidence=adapter(utility).evidence(grid.index,cycle_account(r["account"],cycles[0][2]))
    assert evidence["rate_evidence_status"]=="verified" and not evidence["rate_assumptions"]
    assert evidence["assumption_model"] is None
    legacy=deepcopy(r)
    legacy["account"].pop("rate_evidence_mode")
    legacy["account"].pop("provisional_assumptions_accepted")
    assert prepare(legacy)[0].index.equals(grid.index)


@pytest.mark.parametrize("utility,plan,kind",[(WE,"Rg1","residential"),(DUKE,"RS","residential")])
def test_http_rejects_unaccepted_provisional_request_without_queueing(service,utility,plan,kind):
    app,call,headers=service
    r=historical_request(utility,plan,kind)
    r["account"]["provisional_assumptions_accepted"]=False
    before={s["id"] for s in app.store.list()}
    with pytest.raises(HTTPError) as exc:call("/api/v1/regional/studies",r,headers)
    assert exc.value.code==400
    assert "provisional" in json.loads(exc.value.read())["error"].lower()
    assert {s["id"] for s in app.store.list()}==before


@pytest.mark.parametrize("utility,plan,kind,model",[
    (WE,"Rg1","residential","we_energies_wi_2025_provisional_v1"),
    (WE,"Cg1","commercial","we_energies_wi_2025_provisional_v1"),
    (DUKE,"RS","residential","duke_indiana_2025_provisional_v1"),
    (DUKE,"CS","commercial","duke_indiana_2025_provisional_v1")])
def test_provisional_form_worker_artifacts_and_reopen_preserve_evidence(service,utility,plan,kind,model):
    app,call,headers=service
    r=browser_request(historical_request(utility,plan,kind))
    saved=call("/api/v1/regional/studies?draft=1",r,headers)
    study=wait_for_study(call,saved["id"])
    assert study["status"]=="completed",study.get("error")
    result=study["result"]
    assert result["engine_id"]==app.engine["id"]
    assert result["rate_evidence_status"]=="provisional"
    evidence=result["rate_evidence"]
    assert evidence["selected_mode"]=="provisional_2025" and evidence["provisional_assumptions_accepted"] is True
    assert evidence["status"]=="provisional" and evidence["assumption_models"]==[model] and evidence["assumption_ids"]
    assert any("Provisional historical estimate" in w for w in result["warnings"])
    assert "Provisional" in next(t["label"] for t in result["tables"] if t["id"]=="comparison")
    assert set(result["billing"])=={"grid_only","pv_only","pv_battery"}
    for bills in result["billing"].values():
        bill=bills[0]
        assert bill["rate_evidence_status"]=="provisional" and bill["assumption_model"]==model
        assert bill["objective_scope"]=="provisional_modeled_bill" and bill["rate_assumptions"]
        assert bill["total_usd"]==pytest.approx(sum(bill["lines"].values())) and bill["export_kwh"]<1e-5
    assert result["ac_validation"]["status"]=="completed" and len(result["ac_validation"]["scenarios"])==3
    base="/api/studies/"+saved["id"]
    components=call(base+"/tables/billing-components")
    items=[dict(zip(components["columns"],row)) for row in components["data"]]
    assert {item["rate_evidence_status"] for item in items}=={"verified","provisional"}
    assert all(json.loads(item["rate_assumption_ids"]) for item in items if item["rate_evidence_status"]=="provisional")
    assumptions=call(base+"/tables/billing-assumptions.csv")
    assert model.encode() in assumptions
    comparison=call(base+"/tables/comparison")
    rows=[dict(zip(comparison["columns"],row)) for row in comparison["data"]]
    assert all(row["rate_evidence_status"]=="provisional" and json.loads(row["rate_assumption_ids"]) for row in rows)
    assert max(row["maximum_reconciliation_difference_usd"] for row in rows)<1e-4
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as archive:
        assert archive.read("billing-assumptions.csv")==assumptions
        assert json.loads(archive.read("result-manifest.json"))["rate_evidence"]==evidence
    call(base+"/save",{"name":utility+" "+plan+" provisional historical estimate"},headers)
    reopened=call(base)
    assert reopened["saved"] and reopened["result"]["rate_evidence"]==evidence
    restored=call(base+"/request.json")
    assert browser_request(restored)["account"]==r["account"]


def test_duke_annual_reading_schedule_has_twelve_complete_regular_cycles():
    cycles=duke_2025_regular_cycles()
    grid=build_interval_index("2025-01-01","2025-12-31","America/Indiana/Indianapolis",15)
    parts=list(cycle_partitions(grid.index,cycles))
    assert len(parts)==12
    assert sum(len(grid.index[block]) for _,block,_ in parts)==len(grid.index)==35040
    assert [c["billing_month"] for c in cycles]==pd.date_range("2025-01-01",periods=12,freq="MS").strftime("%Y-%m-%d").tolist()
    assert cycles[0]["start_date"]=="2025-01-01" and cycles[-1]["end_date"]=="2025-12-31"
    for _,block,cycle in parts:
        first=pd.Timestamp(cycle["start_date"])
        last=pd.Timestamp(cycle["end_date"])
        assert 26<=(last-first).days+1<=34
        assert cycle["kind"]=="regular" and "hypothetical" in cycle["source"]
        assert cycle["bill_date"]==cycle["end_date"] and cycle["account_overrides"]=={}
        local_dates=grid.index[block].date
        assert not (min(local_dates)<pd.Timestamp("2025-02-27").date()<=max(local_dates))
    # Avoiding a rate crossing does not add a thirteenth monthly charge.
    assert [(c["start_date"],c["end_date"]) for c in cycles[:3]]==[
        ("2025-01-01","2025-01-26"),("2025-01-27","2025-02-26"),
        ("2025-02-27","2025-03-31")]


def test_duke_regular_readings_keep_spring_gap_and_fall_fold():
    grid=build_interval_index("2025-01-01","2025-12-31","America/Indiana/Indianapolis",15)
    parts=list(cycle_partitions(grid.index,duke_2025_regular_cycles()))
    march=grid.index[parts[2][1]]
    november=grid.index[parts[10][1]]
    assert sum(march.date==pd.Timestamp("2025-03-09").date())==92
    assert sum(november.date==pd.Timestamp("2025-11-02").date())==100
    assert len(march)==3164
    assert len(november)==2884


@pytest.mark.parametrize("plan,kind",[("RS","residential"),("CS","commercial")])
def test_documented_26_day_cycle_form_worker_bill_and_replay(service,plan,kind):
    app,call,headers=service
    r=defaults("duke_energy_indiana",kind,plan)
    r.update(start_date="2025-03-01",end_date="2025-03-26",billing_cycles=[dict(
        start_date="2025-03-01",end_date="2025-03-26",billing_month="2025-03-01",
        bill_date="2025-03-26",kind="regular",source="Explicit hypothetical regular26-day meter reading cycle, full monthly charges confirmed under filed GTC12.4; not a measured customer bill",account_overrides={})])
    r["operating_contract"].update(interconnection_confirmed=True,grid_charging_confirmed=True,
        reference="Explicit hypothetical utility-approved non-export account")
    r=browser_request(r)
    prepare(r)
    study=call("/api/v1/regional/studies",r,headers)
    result=wait_for_study(call,study["id"])
    assert result["status"]=="completed",result.get("error")
    result=result["result"]
    assert result["engine_id"]==app.engine["id"]
    assert set(result["billing"])=={"grid_only","pv_only","pv_battery"}
    for bills in result["billing"].values():
        bill=bills[0]
        assert bill["is_complete_bill"] and bill["rate_evidence_status"]=="verified"
        assert bill["metrics"]["cycle_days"]==26
        assert bill["metrics"]["monthly_charge_factor"]==1.
        assert bill["lines"]["customer"]=={"RS":13.70,"CS":13.91}[plan]
        assert bill["total_usd"]==pytest.approx(sum(bill["lines"].values()))
    assert result["ac_validation"]["status"]=="completed"
    for scenario in result["ac_validation"]["scenarios"]:
        assert scenario["interval_count"]==2492
        assert scenario["all_intervals_feasible"]
