"""Toledo main-form, source scope, pinned worker and saved-artifact acceptance."""
from copy import deepcopy
from io import BytesIO
import json
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest

from src.billing.regional import UTILITIES, calculate_cycle, cycle_account
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import capabilities, prepare
from tools.run_regional_validation import case_request, checked_bill_scope, selected_cases
from test_local_web import service, wait_for_study
from test_regional_study import browser_request

UTILITY = "firstenergy_ohio_toledo"
CASES = (("residential","RS"),("commercial","GS"))


def request(kind, plan, day="2025-06-01"):
    end=str((pd.Timestamp(day)+pd.offsets.MonthEnd()).date())
    return case_request(UTILITY,kind,"custom",plan=plan,start_date=day,end_date=end)


@pytest.mark.parametrize("kind,plan",CASES)
def test_form_roundtrip_separates_utility_supplier_jurisdiction_zone_and_carbon(kind,plan):
    cap=capabilities()["utilities"][UTILITY]
    assert (cap["state"],cap["grid_operator"],cap["transmission_zone"])==("OH","PJM","ATSI")
    assert UTILITIES[UTILITY]["emergency_region"]=="FE-ATSI"
    assert (UTILITY,kind,plan) in selected_cases([UTILITY])
    r=case_request(UTILITY,kind,"monthly",plan=plan)
    assert (r["start_date"],r["end_date"])==("2025-06-01","2025-06-30")
    out=browser_request(r)
    assert out=={**r,"name":"Untitled study"}
    grid,load,cycles,equipment=prepare(out)
    assert len(grid.index)==len(load)==2880 and len(cycles)==1
    assert out["regional_account"]["retail_supplier"]==UTILITY
    assert out["account"]["supply"]=="sso"
    assert out["regional_account"]["wholesale_pricing_location"] is None
    assert equipment["pv_dc_kw"]==(5. if plan=="RS" else 10.)
    assert out["operating_contract"]["renewable_only_charging"] is True
    assert out["operating_contract"]["grid_charging_confirmed"] is False
    for key,value in (("distribution_utility","firstenergy_ohio_edison"),("state_jurisdiction","PA"),
                      ("transmission_zone","DLCO"),("retail_supplier","competitive_supplier")):
        bad=deepcopy(out);bad["regional_account"][key]=value
        with pytest.raises(ValueError):
            prepare(bad)
    out["carbon"]={"source":"electricity_maps","region":"US-MIDA-PJM"}
    prepare(out) # Optional signal compatibility only; no live API call or new carbon coverage claim.


@pytest.mark.parametrize("kind,plan",CASES)
def test_complete_multi_cycle_history_dst_and_no_annual_gap_substitution(kind,plan):
    r=case_request(UTILITY,kind,"custom",plan=plan,start_date="2025-09-01",end_date="2025-11-30")
    grid,load,cycles,equipment=prepare(r)
    assert len(grid.index)==8740 and len(cycles)==3
    assert [len(grid.index[block]) for _,block,_ in cycles]==[2880,2976,2884]
    state=None
    for _,block,cycle in cycles:
        a=cycle_account(r["account"],cycle)
        b=calculate_cycle(UTILITY,grid.index[block],load[block],np.zeros(len(load[block])),a,state=state,equipment=equipment)
        assert checked_bill_scope(b,UTILITY,a,grid.index[block])==("complete_utility_bill",[])
        assert b["metrics"]["contract_demand_kw"]==(0. if plan=="RS" else 12.)
        state=b["next_state"]
    assert state=={}
    with pytest.raises(ValueError,match="full-year2025"):
        case_request(UTILITY,kind,"annual",plan=plan)
    with pytest.raises(ValueError,match="complete verified"):
        case_request(UTILITY,kind,"custom",plan=plan,start_date="2025-01-01",end_date="2025-12-31")


@pytest.mark.parametrize("kind,plan",CASES)
def test_native_study_envelope_and_grid_charging_cannot_be_hidden_by_der(kind,plan):
    r=request(kind,plan)
    frame=pd.read_csv(BytesIO(r["load"]["csv"].encode()))
    frame.loc[0,"native_load_kw"]=26. if plan=="RS" else 101.
    r["load"]["csv"]=frame.to_csv(index=False)
    with pytest.raises(ValueError,match="native load"):
        prepare(r)
    r=request(kind,plan);r["operating_contract"]["grid_charging_confirmed"]=True
    with pytest.raises(ValueError,match="PV-only"):
        prepare(r)


@pytest.mark.parametrize("kind,plan",CASES)
def test_absent_der_keeps_actual_contract_and_removes_approval_assertions(kind,plan):
    a=request(kind,plan)["account"]
    reference=grid_only_counterfactual(UTILITY,a,state={})
    assert reference["state"]=={}
    assert reference["account"]["der_ordinary_service_confirmed"] is False
    assert reference["account"]["der_activation_date"]==reference["account"]["der_eligibility_source"]==""
    for key,value in a.items():
        if key not in ("der_ordinary_service_confirmed","der_activation_date","der_eligibility_source"):
            assert reference["account"][key]==value


@pytest.mark.parametrize("day",["2025-06-01","2026-10-01"])
@pytest.mark.parametrize("kind,plan",CASES)
def test_pinned_worker_itemized_bills_save_restore_csv_and_zip(service,day,kind,plan):
    app,call,headers=service
    r=browser_request(request(kind,plan,day))
    study=call("/api/v1/regional/studies",r,headers)
    out=wait_for_study(call,study["id"])
    assert out["status"]=="completed",out.get("error")
    result=out["result"]
    assert result["engine_id"]==app.engine["id"]
    assert result["is_complete_bill"] and result["ac_validation"]["all_intervals_feasible"]
    base="/api/studies/"+study["id"]
    page=call(base+"/tables/comparison")
    rows=[dict(zip(page["columns"],row)) for row in page["data"]]
    assert {row["scenario"] for row in rows}=={"grid_only","pv_only","pv_battery"}
    assert max(row["maximum_reconciliation_difference_usd"] for row in rows)<.0001
    assert result["input_provenance"]["carbon"]["status"]=="not_requested"
    for table in result["tables"]:
        data=call(base+"/tables/"+table["id"]+".csv")
        assert data==(app.store.directory/"runs"/study["id"]/(table["id"]+".csv")).read_bytes()
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read("result-manifest.json"))==result
    call(base+"/save",{"name":"Toledo "+plan+" "+day+" integration"},headers)
    assert call(base)["saved"]
    saved=call(base+"/request.json")
    assert saved["account"]==r["account"]
    assert browser_request(saved)["account"]==r["account"]
