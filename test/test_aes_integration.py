"""AES main-form, queued worker, independent account state and artifact scope."""
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

UTILITY="aes_ohio"
CASES=(("residential","D17"),("commercial","D19"))


def request(kind,plan,day="2025-06-01"):
    return case_request(UTILITY,kind,"custom",plan=plan,start_date=day,end_date=str((pd.Timestamp(day)+pd.offsets.MonthEnd()).date()))


@pytest.mark.parametrize("kind,plan",CASES)
def test_browser_serialization_keeps_utility_supplier_zone_and_history_separate(kind,plan):
    cap=capabilities()["utilities"][UTILITY]
    assert (cap["state"],cap["grid_operator"],cap["transmission_zone"])==("OH","PJM","DAY")
    assert UTILITIES[UTILITY]["emergency_region"]=="DAY"
    assert (UTILITY,kind,plan) in selected_cases([UTILITY])
    r=case_request(UTILITY,kind,"monthly",plan=plan)
    assert (r["start_date"],r["end_date"])==("2025-06-01","2025-06-30")
    out=browser_request(r)
    assert out=={**r,"name":"Untitled study"}
    grid,load,cycles,equipment=prepare(out)
    assert len(grid.index)==len(load)==2880 and len(cycles)==1
    assert out["regional_account"]["wholesale_pricing_location"] is None
    assert out["regional_account"]["retail_supplier"]==UTILITY and out["account"]["supply"]=="sso"
    assert out["account"]["demand_interval_minutes"]==30
    for key,value in (("distribution_utility","firstenergy_ohio_toledo"),("state_jurisdiction","PA"),
                      ("transmission_zone","ATSI"),("retail_supplier","competitive_supplier")):
        bad=deepcopy(out);bad["regional_account"][key]=value
        with pytest.raises(ValueError):prepare(bad)
    out["carbon"]={"source":"electricity_maps","region":"US-MIDA-PJM"}
    prepare(out) # Signal compatibility only; no new carbon observations or live call.


@pytest.mark.parametrize("kind,plan",CASES)
def test_multi_cycle_dst_history_continuity_and_explicit_source_gaps(kind,plan):
    r=case_request(UTILITY,kind,"custom",plan=plan,start_date="2025-03-01",end_date="2025-06-30")
    grid,load,cycles,equipment=prepare(r)
    assert len(grid.index)==11708 and len(cycles)==4
    assert [len(grid.index[block]) for _,block,_ in cycles]==[2972,2880,2976,2880]
    state=None
    for _,block,cycle in cycles:
        a=cycle_account(r["account"],cycle)
        out=calculate_cycle(UTILITY,grid.index[block],load[block],np.zeros(len(load[block])),a,state=state,equipment=equipment)
        assert checked_bill_scope(out,UTILITY,a,grid.index[block])==("complete_utility_bill",[])
        if plan=="D19":
            assert out["next_state"]["history"][-1]["maximum_kw"]==pytest.approx(out["metrics"]["actual_30_minute_peak_kw"])
        state=out["next_state"]
    assert (state=={})==(plan=="D17")
    with pytest.raises(ValueError,match="full-year2025"):case_request(UTILITY,kind,"annual",plan=plan)
    for first,last in (("2025-06-01","2025-07-31"),("2026-07-01","2026-09-30")):
        with pytest.raises(ValueError,match="complete verified"):
            case_request(UTILITY,kind,"custom",plan=plan,start_date=first,end_date=last)


@pytest.mark.parametrize("kind,plan",CASES)
def test_native_envelope_and_pv_only_charging_do_not_follow_reduced_imports(kind,plan):
    r=request(kind,plan)
    frame=pd.read_csv(BytesIO(r["load"]["csv"].encode()))
    frame.loc[0,"native_load_kw"]=26. if plan=="D17" else 101.
    r["load"]["csv"]=frame.to_csv(index=False)
    with pytest.raises(ValueError,match="native load"):prepare(r)
    r=request(kind,plan);r["operating_contract"]["grid_charging_confirmed"]=True
    with pytest.raises(ValueError,match="PV-only"):prepare(r)


@pytest.mark.parametrize("kind,plan",CASES)
def test_grid_only_keeps_actual_demand_and_prior_refund_facts_without_der(kind,plan):
    a=request(kind,plan,"2026-11-01")["account"]
    reference=grid_only_counterfactual(UTILITY,a,state=None)
    assert reference["account"]["der_ordinary_service_confirmed"] is False
    assert reference["account"]["der_activation_date"]==reference["account"]["der_eligibility_source"]==""
    for key,value in a.items():
        if key not in ("der_ordinary_service_confirmed","der_activation_date","der_eligibility_source"):
            assert reference["account"][key]==value


@pytest.mark.parametrize("kind,plan",CASES)
@pytest.mark.parametrize("day",["2025-06-01","2026-11-01"])
def test_pinned_worker_reconciles_bills_history_save_restore_and_csv_zip(service,kind,plan,day):
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
    for table in result["tables"]:
        assert call(base+"/tables/"+table["id"]+".csv")== (app.store.directory/"runs"/study["id"]/(table["id"]+".csv")).read_bytes()
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read("result-manifest.json"))==result
    call(base+"/save",{"name":"AES "+plan+" "+day+" acceptance"},headers)
    assert call(base)["saved"]
    restored=call(base+"/request.json")
    assert restored["account"]==r["account"] and browser_request(restored)["account"]==r["account"]
