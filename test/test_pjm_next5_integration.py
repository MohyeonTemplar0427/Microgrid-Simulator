"""Bounded form/worker/artifact acceptance for the second PJM utility batch."""
from copy import deepcopy
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.error import HTTPError
from zipfile import ZipFile

import numpy as np
import pytest

from src.billing.regional import adapter
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import capabilities, defaults, prepare
from test_local_web import service, wait_for_study
from test_regional_study import browser_request
from tools.run_regional_validation import PJM_NEXT5_CASES, case_request, selected_cases

ROOT=Path(__file__).resolve().parents[1]
IDENTITY={
    "potomac_edison_west_virginia":("WV","APS"),
    "wheeling_power_west_virginia":("WV","AEP"),
    "kentucky_power_kentucky":("KY","AEP"),
    "northern_virginia_electric_cooperative":("VA","DOM"),
}


@pytest.mark.parametrize("utility,kind,plan",PJM_NEXT5_CASES)
def test_forms_preserve_identity_dates_eligibility_and_non_export(utility,kind,plan):
    raw=case_request(utility,kind,"monthly",plan=plan)
    r=browser_request(raw)
    assert r=={**raw,"name":"Untitled study"}
    c=capabilities()["utilities"][utility]
    assert (c["state"],c["transmission_zone"])==IDENTITY[utility]
    assert c["grid_operator"]=="PJM" and (utility,kind,plan) in selected_cases([utility])
    assert r["regional_account"]["retail_supplier"]==utility
    assert r["regional_account"]["wholesale_pricing_location"] is None
    assert r["operating_contract"]["renewable_only_charging"]
    prepare(r)
    initial=defaults(utility,kind,plan)
    assert initial["operating_contract"]["interconnection_confirmed"] is False
    initial["operating_contract"].update(interconnection_confirmed=True,
        reference="Explicit hypothetical approval for the exact PV and paired-storage installation")
    prepare(initial)
    for field,bad in (("distribution_utility","mon_power_west_virginia"),
                      ("state_jurisdiction","XX"),("transmission_zone","OTHER"),
                      ("retail_supplier","third_party")):
        altered=deepcopy(r);altered["regional_account"][field]=bad
        with pytest.raises(ValueError):prepare(altered)
    for target,key,bad in (("operating_contract","grid_charging_confirmed",True),
                           ("operating_contract","mode","net_metering"),
                           ("account","der_ordinary_service_confirmed",False)):
        altered=deepcopy(r);altered[target][key]=bad
        with pytest.raises(ValueError):prepare(altered)
    r["carbon"]={"source":"electricity_maps","region":"US-MIDA-PJM"}
    prepare(r)  # Compatibility only; no external carbon retrieval.


@pytest.mark.parametrize("utility,kind,plan",PJM_NEXT5_CASES)
def test_native_scope_and_grid_reference_keep_independent_obligations(utility,kind,plan):
    r=case_request(utility,kind,"monthly",plan=plan)
    with pytest.raises(ValueError):adapter(utility).validate_native_load(r["account"],np.full(3000,100.))
    reference=grid_only_counterfactual(utility,r["account"])
    assert reference["account"]["der_ordinary_service_confirmed"] is False
    assert reference["account"]["der_activation_date"]==reference["account"]["der_eligibility_source"]==""
    assert all(reference["account"][k]==v for k,v in r["account"].items()
               if k not in reference["changed_account_fields"])


def test_kentucky_cycle_clock_survives_form_round_trip_and_rejects_calendar_substitution():
    r=case_request("kentucky_power_kentucky","residential","custom",plan="RS",
                   start_date="2026-02-01",end_date="2026-03-31")
    assert [(c["billing_month"],c["bill_date"]) for c in r["billing_cycles"]]==[
        ("2026-03-01","2026-03-01"),("2026-04-01","2026-04-01")]
    assert browser_request(r)["billing_cycles"]==r["billing_cycles"]
    bad=deepcopy(r)
    bad["billing_cycles"][0].update(billing_month="2026-02-01",bill_date="2026-02-28")
    with pytest.raises(ValueError):prepare(bad)


def test_novec_annual_classification_facts_are_explicit_for_every_cycle():
    r=case_request("northern_virginia_electric_cooperative","commercial","annual",plan="SC-1")
    assert (r["start_date"],r["end_date"])==("2025-01-01","2025-12-31")
    assert len(r["billing_cycles"])==12
    for cycle in r["billing_cycles"]:
        facts=adapter(r["site"]["utility"]).hypothetical_defaults("SC-1",day=cycle["start_date"])
        assert cycle["account_overrides"]["sc_history_through_month"]==facts["sc_history_through_month"]
    prepare(browser_request(r))


def test_smeco_unavailable_catalog_and_browser_reason_do_not_create_a_bill(service):
    utility="southern_maryland_electric_cooperative"
    c=capabilities()["utilities"][utility]
    assert c["transmission_zone"]=="SMECO" and not c["defaults"] and not c["accounts"]
    assert {p["id"] for p in c["plans"]}=={"R","GSS"}
    assert all(p["status"]!="supported" and not p["coverage"] for p in c["plans"])
    with pytest.raises(ValueError):defaults(utility)
    with pytest.raises(ValueError):selected_cases([utility])
    script="const fs=require('node:fs');const {regionalUnavailableReason}=require('./src/local_web/static/regional.js');const x=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(['residential','commercial'].map(k=>regionalUnavailableReason(x,k))));"
    reasons=json.loads(subprocess.run(["node","-e",script],input=json.dumps(c),text=True,capture_output=True,check=True,cwd=ROOT).stdout)
    assert all("unavailable" in r and "SMECO" in r and "BSA" in r for r in reasons)
    app,call,headers=service
    r=case_request("potomac_edison_west_virginia","residential","monthly",plan="R")
    r["site"]["utility"]=utility
    r["regional_account"].update(distribution_utility=utility,retail_supplier=utility,
                                 state_jurisdiction="MD",transmission_zone="SMECO")
    r["account"]=adapter(utility).hypothetical_defaults("R",day=r["start_date"])
    with pytest.raises(HTTPError) as error:
        call("/api/v1/regional/studies",r,headers)
    assert error.value.code==400
    response=json.loads(error.value.read())
    assert "error" in response and "id" not in response


def test_actual_browser_date_callback_handles_an_unavailable_provider_and_keeps_service_clock():
    # Exercise the registered callback itself without a browser or simulated
    # DOM. A disabled provider has no base request; blank dates must stay blank.
    script=r'''const fs=require('node:fs');
const source=fs.readFileSync('./src/local_web/static/regional.js','utf8');
const start=source.indexOf('dateDefaults:')+'dateDefaults:'.length;
const end=source.indexOf(',\n    reset:',start);
if(end<start)throw new Error('Missing date callback');
const factory=new Function('active','base','field','return ('+source.slice(start,end)+')');
const blank=()=>({value:''});
const unavailable=factory(()=>true,()=>undefined,blank)();
const inactive=factory(()=>false,()=>{throw new Error('Inactive base called');},blank)();
const service=factory(()=>true,()=>({start_date:'2026-08-01',end_date:'2026-08-31',billing_month:'2026-09-01'}),blank)();
process.stdout.write(JSON.stringify({unavailable,inactive,service}));'''
    got=json.loads(subprocess.run(["node","-e",script],text=True,capture_output=True,check=True,cwd=ROOT).stdout)
    assert got["unavailable"]==got["inactive"]=={"start":"","end":""}
    assert got["service"]=={"start":"2026-08-01","end":"2026-08-31"}


@pytest.mark.parametrize("utility,kind,plan",PJM_NEXT5_CASES)
def test_queued_worker_save_reopen_and_csv_zip_bytes(service,utility,kind,plan):
    app,call,headers=service
    dates={
        "potomac_edison_west_virginia":("2026-10-01","2026-10-31"),
        "wheeling_power_west_virginia":("2026-10-01","2026-10-31"),
        "kentucky_power_kentucky":("2026-08-01","2026-08-31"),
        "northern_virginia_electric_cooperative":("2025-11-01","2025-11-30"),
    }
    start,end=dates[utility]
    r=browser_request(case_request(utility,kind,"custom",plan=plan,start_date=start,end_date=end))
    run=call("/api/v1/regional/studies",r,headers)
    result=wait_for_study(call,run["id"])
    assert result["status"]=="completed",result.get("error")
    out=result["result"]
    assert out["engine_id"]==app.engine["id"] and out["is_complete_bill"]
    assert out["ac_validation"]["all_intervals_feasible"]
    assert all(c["cost_optimum_proven"] is True for s in ("pv_only","pv_battery") for c in out["optimization"][s]["cycles"])
    base="/api/studies/"+run["id"]
    run_dir=app.store.directory/"runs"/run["id"]
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read("result-manifest.json"))==out
        for table in out["tables"]:
            filename=table["id"]+".csv"
            assert archive.read(filename)==call(base+"/tables/"+filename)==(run_dir/filename).read_bytes()
    call(base+"/save",{"name":utility+" "+plan+" targeted acceptance"},headers)
    assert call(base)["saved"]
    reopened=call(base+"/request.json")
    rebuilt=browser_request(reopened)
    assert rebuilt["account"]==r["account"] and rebuilt["billing_cycles"]==r["billing_cycles"]
    retained=os.environ.get("PJM_NEXT5_WORKER_EVIDENCE")
    if retained:
        target=(ROOT/retained).resolve()
        assert target.is_relative_to(ROOT/".cache")
        target=target/"runs"/run["id"]
        target.parent.mkdir(exist_ok=True,parents=True)
        shutil.copytree(run_dir,target)
