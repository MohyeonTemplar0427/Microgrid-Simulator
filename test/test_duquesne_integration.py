"""Duquesne form, worker, native eligibility, artifacts and history contracts."""
from copy import deepcopy
from io import BytesIO
import json
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest

from src.billing.regional import UTILITIES,calculate_cycle,cycle_account
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import capabilities,prepare
from tools.run_regional_validation import case_request,checked_bill_scope,selected_cases
from test_local_web import service,wait_for_study
from test_regional_study import browser_request

UTILITY="duquesne_light_pennsylvania"
CASES=(("residential","RS"),("commercial","GS"))


@pytest.mark.parametrize("kind,plan",CASES)
def test_form_roundtrip_account_pjm_clock_and_supply(kind,plan):
    c=capabilities()["utilities"][UTILITY]
    assert (c["state"],c["grid_operator"],c["transmission_zone"])==("PA","PJM","DLCO")
    assert UTILITIES[UTILITY]["emergency_region"]=="DUQ"
    assert (UTILITY,kind,plan) in selected_cases([UTILITY])
    r=case_request(UTILITY,kind,"monthly",plan=plan);out=browser_request(r)
    assert out=={**r,"name":"Untitled study"}
    grid,load,cycles,equipment=prepare(out)
    assert len(grid.index)==len(load)==2880 and len(cycles)==1
    assert out["operating_contract"]["renewable_only_charging"] is True
    assert out["operating_contract"]["grid_charging_confirmed"] is False
    assert equipment["pv_dc_kw"]==(5. if plan=="RS" else 1.5)
    for k,value in (("distribution_utility","ppl_electric_pennsylvania"),("state_jurisdiction","NJ"),
                    ("transmission_zone","ATSI"),("retail_supplier","competitive_supplier")):
        bad=deepcopy(out);bad["regional_account"][k]=value
        with pytest.raises(ValueError):prepare(bad)


@pytest.mark.parametrize("kind,plan",CASES)
def test_annual_calendar_state_dst_and_component_scope(kind,plan):
    r=case_request(UTILITY,kind,"annual",plan=plan);grid,load,cycles,equipment=prepare(r)
    assert len(grid.index)==35040 and len(cycles)==12
    assert [len(grid.index[cycles[i][1]]) for i in (2,10)]==[2972,2884]
    state=None
    for _,block,cycle in cycles:
        a=cycle_account(r["account"],cycle)
        b=calculate_cycle(UTILITY,grid.index[block],load[block],np.zeros(len(load[block])),a,state=state,equipment=equipment)
        assert checked_bill_scope(b,UTILITY,a,grid.index[block])==("complete_utility_bill",[])
        assert b["metrics"]["additional_grt_percentage_applied"] is False
        state=b["next_state"]
    assert state==({} if plan=="RS" else {"through_month":"2025-12-01","gs_qualification_upper_bound_kwh":1000.,"gs_peak_upper_bound_kw":5.})


def test_native_gs_limits_are_independent_of_pv_reduced_imports():
    r=case_request(UTILITY,"commercial","monthly",plan="GS")
    frame=pd.read_csv(BytesIO(r["load"]["csv"].encode()))
    for loads in (np.full(len(frame),1.5),np.r_[6.,np.zeros(len(frame)-1)]):
        bad=deepcopy(r);frame["native_load_kw"]=loads;bad["load"]["csv"]=frame.to_csv(index=False)
        with pytest.raises(ValueError,match="native monthly"):prepare(bad)
    r["carbon"]={"source":"electricity_maps","region":"US-MIDA-PJM"}
    prepare(r) # Same independently identified PJM signal; no API retrieval at validation.
    bad=deepcopy(r);bad["operating_contract"]["grid_charging_confirmed"]=True
    with pytest.raises(ValueError,match="PV-only"):prepare(bad)


@pytest.mark.parametrize("kind,plan",CASES)
def test_absent_der_reference_preserves_classification_history(kind,plan):
    a=case_request(UTILITY,kind,"monthly",plan=plan)["account"]
    state={} if plan=="RS" else {"through_month":"2026-05-01","gs_qualification_upper_bound_kwh":1000.,"gs_peak_upper_bound_kw":5.}
    result=grid_only_counterfactual(UTILITY,a,state=state)
    assert result["account"]["der_ordinary_service_confirmed"] is False
    assert result["account"]["der_activation_date"]==result["account"]["der_eligibility_source"]==""
    assert result["state"]==state
    for k in a:
        if k not in ("der_ordinary_service_confirmed","der_activation_date","der_eligibility_source"):
            assert result["account"][k]==a[k]


@pytest.mark.parametrize("kind,plan",CASES)
def test_pinned_worker_save_restore_csv_zip(service,kind,plan):
    app,call,headers=service;r=browser_request(case_request(UTILITY,kind,"monthly",plan=plan))
    study=call("/api/v1/regional/studies",r,headers);out=wait_for_study(call,study["id"])
    assert out["status"]=="completed",out.get("error")
    result=out["result"];assert result["engine_id"]==app.engine["id"]
    assert result["is_complete_bill"] and result["ac_validation"]["all_intervals_feasible"]
    base="/api/studies/"+study["id"];page=call(base+"/tables/comparison")
    rows=[dict(zip(page["columns"],row)) for row in page["data"]]
    assert {row["scenario"] for row in rows}=={"grid_only","pv_only","pv_battery"}
    assert max(row["maximum_reconciliation_difference_usd"] for row in rows)<.0001
    assert result["input_provenance"]["carbon"]["status"]=="not_requested"
    for table in result["tables"]:
        assert call(base+"/tables/"+table["id"]+".csv")== (app.store.directory/"runs"/study["id"]/(table["id"]+".csv")).read_bytes()
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read("result-manifest.json"))==result
    call(base+"/save",{"name":"Duquesne "+plan+" integration"},headers)
    assert call(base)["saved"]
    saved=call(base+"/request.json");assert saved["account"]==r["account"]
    assert browser_request(saved)["account"]==r["account"]
