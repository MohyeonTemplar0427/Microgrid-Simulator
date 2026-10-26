"""Alliant retail configuration, main-form serialization and saved physics."""
from copy import deepcopy
from io import BytesIO
import json
import subprocess
from zipfile import ZipFile

import pytest

from src.billing.regional import account_region, adapter
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import capabilities, defaults, calendar_cycles, prepare
from tools.run_regional_validation import case_request, selected_cases
from test_local_web import service, wait_for_study
from test_regional_study import browser_request


UTILITY="alliant_energy_iowa"
PLANS=("400","407","427","600","607")


def test_browser_interval_choices_follow_plan_and_restore_without_resampling():
    script="""
    const {regionalIntervalSupport}=require('./src/local_web/static/regional.js');
    const select={value:'30',options:['','5','15','30','60'].map(value=>({value,disabled:false}))};
    const states=[];
    for(const plan of [{interval_minutes:[15]}, {}, {interval_minutes:[5,15,30,60]}]){
      states.push({allowed:regionalIntervalSupport(select,plan),value:select.value,
        enabled:select.options.filter(o=>!o.disabled).map(o=>o.value)});
    }
    process.stdout.write(JSON.stringify(states));
    """
    states=json.loads(subprocess.run(["node","-e",script],text=True,capture_output=True,check=True).stdout)
    assert states==[
        dict(allowed=[15],value="30",enabled=["15"]),
        dict(allowed=[15,30],value="30",enabled=["15","30"]),
        dict(allowed=[5,15,30,60],value="30",enabled=["5","15","30","60"])]


def request_for(plan,start="2026-08-01",end="2026-08-31"):
    kind="commercial" if plan in ("600","607") else "residential"
    r=defaults(UTILITY,kind,plan)
    r.update(start_date=start,end_date=end,billing_cycles=calendar_cycles(start,end))
    r["operating_contract"].update(interconnection_confirmed=True,grid_charging_confirmed=True,
        reference="Explicit hypothetical approved ordinary non-export installation; no export compensation")
    return r


def test_catalog_and_browser_defaults_keep_miso_and_retail_facts_separate():
    entry=capabilities()["utilities"][UTILITY]
    assert entry["state"]=="IA" and entry["grid_operator"]=="MISO"
    assert entry["resource_adequacy_zone"]=="LRZ3"
    assert entry["timezone"]=="America/Chicago"
    assert entry["transmission_zone"] is None and entry["transmission_owner"] is None
    assert set(entry["accounts"])==set(PLANS)
    assert set(entry["defaults"])=={"residential","commercial"}
    for plan in PLANS:
        r=request_for(plan)
        account_region(r["regional_account"],UTILITY)
        assert r["regional_account"]["distribution_utility"]==r["regional_account"]["retail_supplier"]==UTILITY
        assert r["regional_account"]["wholesale_pricing_location"] is None
        assert r["electrical_service"]["phase"]=="single" and r["electrical_service"]["nominal_voltage_v"]==240.
        assert (UTILITY,r["site_profile"]["site_type"],plan) in selected_cases([UTILITY])
        altered=deepcopy(r["regional_account"]);altered["state_jurisdiction"]="WI"
        with pytest.raises(ValueError):account_region(altered,UTILITY)


@pytest.mark.parametrize("plan",PLANS)
def test_same_request_builds_all_five_plans_without_source_fallback(plan):
    r=request_for(plan)
    restored=browser_request(r)
    assert restored["account"]==r["account"]
    grid,load,cycles,equipment=prepare(restored)
    assert len(grid.index)==2976 and len(cycles)==1
    assert len(load)==len(grid.index) and equipment["pv_dc_kw"]==5.
    assert r["load"]["power_kw"]==3.
    assert restored["operating_contract"]["mode"]=="non_export"
    # An absent-DER reference removes DG assertions, not rate eligibility.
    before=deepcopy(restored["account"])
    ref=grid_only_counterfactual(UTILITY,before)
    assert ref["account"]["tariff"]==plan and ref["account"]["dg_enrollment_confirmed"] is False
    assert before==restored["account"]


@pytest.mark.parametrize("plan",("427","607"))
def test_form_worker_reconciliation_replay_download_and_save_restore(service,plan):
    app,call,headers=service
    r=browser_request(request_for(plan));prepare(r)
    queued=call("/api/v1/regional/studies",r,headers)
    response=wait_for_study(call,queued["id"])
    assert response["status"]=="completed",response.get("error")
    result=response["result"]
    assert result["engine_id"]==app.engine["id"]
    assert result["rate_evidence_status"]=="verified"
    assert result["rate_evidence"]["assumption_ids"]==[]
    assert set(result["billing"])=={"grid_only","pv_only","pv_battery"}
    grid,native,cycles,equipment=prepare(r)
    for scenario,bills in result["billing"].items():
        assert len(bills)==1
        bill=bills[0]
        assert bill["is_complete_bill"] and bill["rate_evidence_status"]=="verified"
        assert bill["rate_assumptions"]==[] and bill["export_kwh"]<1e-5
        assert bill["metrics"]["dg_enrollment_confirmed"] is (scenario!="grid_only")
        assert bill["total_usd"]==pytest.approx(sum(bill["lines"].values()))
        assert not any("nem" in key or "export_credit" in key for key in bill["lines"])
        assert result["optimization"][scenario]["annual_optimum_proven"] is None
    ac=result["ac_validation"]
    assert ac["status"]=="completed"
    assert {x["scenario"] for x in ac["scenarios"]}==set(result["billing"])
    assert all(x["checked_intervals"]==2976 and x["all_intervals_feasible"] for x in ac["scenarios"])
    base="/api/studies/"+queued["id"]
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as z:
        assert z.testzip() is None
        assert json.loads(z.read("result-manifest.json"))["rate_evidence_status"]=="verified"
        for scenario in result["billing"]:
            assert "ac-"+scenario+".csv" in z.namelist()
    call(base+"/save",{"name":"Alliant Iowa "+plan+" integration"},headers)
    saved=call(base+"/request.json")
    assert saved["account"]==r["account"] and saved["billing_cycles"]==r["billing_cycles"]
    rebuilt=browser_request(saved);prepare(rebuilt)
    assert rebuilt["account"]==saved["account"]


def test_unapproved_provisional_mode_cannot_override_verified_history():
    # Unknown evidence modes cannot authorize an implicit extrapolation.
    r=request_for("400");r["account"].update(rate_evidence_mode="provisional_2025",provisional_assumptions_accepted=True)
    with pytest.raises(ValueError):prepare(r)
