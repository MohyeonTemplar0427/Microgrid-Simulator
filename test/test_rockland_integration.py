"""Rockland October2026 modeled form/worker and retained-account contracts."""
from copy import deepcopy
from io import BytesIO
import json
from zipfile import ZipFile

import numpy as np
import pytest

from src.billing.regional import calculate_cycle,cycle_account
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import capabilities,prepare
from tools.run_regional_validation import case_request,checked_bill_scope,selected_cases
from test_local_web import service,wait_for_study
from test_regional_study import browser_request

UTILITY="rockland_electric_new_jersey"
CASES=(("residential","SC1"),("commercial","SC2"))


@pytest.mark.parametrize("kind,plan",CASES)
def test_form_keeps_account_supplier_county_and_grid_identity_independent(kind,plan):
    c=capabilities()["utilities"][UTILITY]
    assert (c["state"],c["grid_operator"],c["transmission_zone"])==("NJ","PJM","RECO")
    assert (UTILITY,kind,plan) in selected_cases([UTILITY])
    r=case_request(UTILITY,kind,"monthly",plan=plan);out=browser_request(r)
    assert out["account"]==r["account"] and out["billing_cycles"]==r["billing_cycles"]
    assert out["weather_source"]=="clear_sky" and out["weather"] is None
    assert "peak_load_share_kw" not in out["account"]
    grid,load,cycles,equipment=prepare(out)
    assert len(grid.index)==len(load)==2976 and len(cycles)==1
    assert grid.index[0].isoformat()=="2026-10-01T00:00:00-04:00"
    assert grid.index[-1].isoformat()=="2026-10-31T23:45:00-04:00"
    assert equipment["pv_dc_kw"]==5.
    for key,value in (("state_jurisdiction","NY"),("retail_supplier","competitive_supplier"),("transmission_zone","JCPL")):
        bad=deepcopy(out);bad["regional_account"][key]=value
        with pytest.raises(ValueError):prepare(bad)
    for key,value in (("county","Passaic"),("service_division","central"),("no_ami_opt_out_fee_confirmed",False)):
        bad=deepcopy(out);bad["account"][key]=value
        with pytest.raises(ValueError):prepare(bad)


@pytest.mark.parametrize("kind,plan",CASES)
def test_counterfactual_preserves_non_demand_assignment_and_no_ciep_facts(kind,plan):
    a=case_request(UTILITY,kind,"monthly",plan=plan)["account"]
    grid=grid_only_counterfactual(UTILITY,a,state={})
    assert grid["account"]["der_ordinary_service_confirmed"] is False
    assert grid["account"]["der_activation_date"]==grid["account"]["der_eligibility_source"]==""
    for key in ("tariff","county","service_division","supply","supply_eligibility_source","bgs_rscp_confirmed","metering","sc2_non_demand_confirmed","sc2_classification_source","no_ami_opt_out_fee_confirmed"):
        assert grid["account"][key]==a[key]
    assert a["der_ordinary_service_confirmed"] is True and grid["state"]=={}


@pytest.mark.parametrize("kind,plan",CASES)
def test_queued_worker_modeled_clear_sky_bills_save_and_csv_zip(service,kind,plan):
    app,call,headers=service
    r=browser_request(case_request(UTILITY,kind,"monthly",plan=plan))
    queued=call("/api/v1/regional/studies",r,headers);study=wait_for_study(call,queued["id"])
    assert study["status"]=="completed",study.get("error")
    result=study["result"]
    assert result["engine_id"]==app.engine["id"] and result["is_complete_bill"] is True
    assert set(result["billing"])=={"grid_only","pv_only","pv_battery"}
    for scenario,bills in result["billing"].items():
        b=bills[0];assert len(bills)==1 and b["is_complete_bill"] and b["excluded_components"]==[]
        assert b["rate_evidence_status"]=="verified" and b["export_kwh"]<1e-5
        assert b["total_usd"]==pytest.approx(sum(b["lines"].values()))
        assert b["metrics"]["minimum_inactive_domain_verified"] and b["metrics"]["rounded_cash_optimum_claimed"] is False
        assert result["optimization"][scenario]["annual_optimum_proven"] is None
    assert result["ac_validation"]["all_intervals_feasible"]
    assert all(x["checked_intervals"]==2976 and x["failed_intervals"]==0 for x in result["ac_validation"]["scenarios"])
    base="/api/studies/"+queued["id"]
    comparison=call(base+"/tables/comparison")
    rows=[dict(zip(comparison["columns"],row)) for row in comparison["data"]]
    assert max(row["maximum_reconciliation_difference_usd"] for row in rows)<.0001
    assert b"pv_curtailed_kw" in call(base+"/tables/dispatch-pv_battery.csv")
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as archive:
        assert archive.testzip() is None and json.loads(archive.read("result-manifest.json"))==result
        assert all("ac-"+s+".csv" in archive.namelist() for s in result["billing"])
    call(base+"/save",{"name":"Rockland "+plan+" modeled acceptance"},headers)
    restored=call(base+"/request.json")
    assert restored["account"]==r["account"] and restored["regional_account"]==r["regional_account"]
    assert browser_request(restored)["account"]==r["account"]


@pytest.mark.parametrize("kind,plan",CASES)
def test_scope_audit_rejects_hidden_minimum_rounding_or_complete_bill_changes(kind,plan):
    r=case_request(UTILITY,kind,"monthly",plan=plan);grid,load,cycles,e=prepare(r);a=cycle_account(r["account"],cycles[0][2])
    b=calculate_cycle(UTILITY,grid.index,load,np.zeros(len(load)),a,equipment=e)
    assert checked_bill_scope(b,UTILITY,a,grid.index)==("complete_utility_bill",[])
    for key,value in (("is_complete_bill",False),("rate_evidence_status","provisional"),("excluded_components",["transmission"]),("next_state",{"credit":1.})):
        bad=deepcopy(b);bad[key]=value
        with pytest.raises(AssertionError):checked_bill_scope(bad,UTILITY,a,grid.index)
    for key,value in (("monthly_charge_factor",.9),("minimum_inactive_domain_verified",False),("rounded_cash_optimum_claimed",True),("additional_tax_percentage_applied",True),("reconciliation_clock","service-time average")):
        bad=deepcopy(b);bad["metrics"][key]=value
        with pytest.raises(AssertionError):checked_bill_scope(bad,UTILITY,a,grid.index)


@pytest.mark.parametrize("kind,plan",CASES)
def test_unverified_history_partial_cycles_and_native_csv_gaps_reject(kind,plan):
    with pytest.raises(ValueError,match="full-year2025"):
        case_request(UTILITY,kind,"annual",plan=plan)
    for start,end in (("2025-10-01","2025-10-31"),("2026-07-01","2026-07-31"),("2026-09-01","2026-09-30"),("2026-10-01","2026-10-30"),("2026-11-01","2026-11-30")):
        with pytest.raises(ValueError):
            case_request(UTILITY,kind,"custom",plan=plan,start_date=start,end_date=end)
    r=case_request(UTILITY,kind,"monthly",plan=plan)
    lines=r["load"]["csv"].splitlines();r["load"]["csv"]="\n".join(lines[:30]+lines[31:])+"\n"
    with pytest.raises(ValueError):prepare(r)


def test_sc2_retained_billing_and_active_der_approval_reach_real_prepare():
    base=case_request(UTILITY,"commercial","monthly",plan="SC2")
    for key,value in (("sc2_non_demand_confirmed",False),("sc2_classification_source",""),("metering","demand_billed"),("der_activation_date","2026-10-02"),("supply_eligibility_source",""),("der_eligibility_source","")):
        bad=deepcopy(base);bad["account"][key]=value
        with pytest.raises(ValueError):prepare(bad)
