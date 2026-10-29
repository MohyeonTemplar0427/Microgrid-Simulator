"""Penn Power form/worker, native eligibility and state/completeness contracts."""
from copy import deepcopy
from io import BytesIO
import json
from zipfile import ZipFile
import numpy as np
import pandas as pd
import pytest

from src.billing.penn_power_pa import JANUARY_GS_EXCLUSION,history_through
from src.billing.regional import calculate_cycle,cycle_account,UTILITIES
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import capabilities,prepare
from tools.run_regional_validation import case_request,checked_bill_scope,selected_cases
from test_local_web import service,wait_for_study
from test_regional_study import browser_request

UTILITY="firstenergy_pa_penn_power"
CASES=(("residential","RS"),("commercial","GS-S"))


@pytest.mark.parametrize("kind,plan",CASES)
def test_form_roundtrip_district_supplier_tax_and_pjm_metadata(kind,plan):
    c=capabilities()["utilities"][UTILITY]
    assert (c["state"],c["grid_operator"],c["transmission_zone"])==("PA","PJM","ATSI")
    assert UTILITIES[UTILITY]["emergency_region"]=="FE-ATSI" and (UTILITY,kind,plan) in selected_cases([UTILITY])
    r=case_request(UTILITY,kind,"monthly",plan=plan);out=browser_request(r)
    assert out["account"]==r["account"] and out["billing_cycles"]==r["billing_cycles"]
    grid,load,cycles,e=prepare(out)
    assert len(grid.index)==len(load)==2880 and len(cycles)==1 and e["pv_dc_kw"]==5.
    assert out["operating_contract"]["renewable_only_charging"] is True
    assert out["operating_contract"]["grid_charging_confirmed"] is False
    assert out["account"]["gs_fixed_imputed_usage_excluded_confirmed"] is (plan=="GS-S")
    assert out["account"]["gs_no_demand_meter_confirmed"] is (plan=="GS-S")
    assert out["account"]["january_refund_eligibility_confirmed"] is False
    assert out["account"]["gs_no_qualifying_gsds_history_confirmed"] is (plan=="GS-S")
    assert out["account"]["legacy_gs_refund_entitlement_confirmed"] is False
    assert bool(out["account"]["gs_gsds_history_source"]) is (plan=="GS-S")
    for key,value in (("distribution_utility","firstenergy_pa_met_ed"),("transmission_zone","APS"),("state_jurisdiction","NJ"),("retail_supplier","competitive_supplier")):
        bad=deepcopy(out);bad["regional_account"][key]=value
        with pytest.raises(ValueError):prepare(bad)


@pytest.mark.parametrize("kind,plan",CASES)
def test_annual_2025_calendar_dst_refund_state_and_scope_are_preserved(kind,plan):
    r=browser_request(case_request(UTILITY,kind,"annual",plan=plan));grid,load,cycles,e=prepare(r)
    assert len(grid.index)==35040 and len(cycles)==12
    assert len(grid.index[cycles[2][1]])==2972 and len(grid.index[cycles[10][1]])==2884
    state=None;refunds=[]
    for _,block,cycle in cycles:
        a=cycle_account(r["account"],cycle);b=calculate_cycle(UTILITY,grid.index[block],load[block],np.zeros(len(load[block])),a,state=state,equipment=e)
        scope,excluded=checked_bill_scope(b,UTILITY,a,grid.index[block]);refunds.append(b["lines"]["january_refund"])
        expected=[JANUARY_GS_EXCLUSION] if plan=="GS-S" and cycle["billing_month"]=="2025-01-01" else []
        assert excluded==expected and b["is_complete_bill"] is (not expected)
        assert b["metrics"]["january_refund_entitlement_confirmed"] is (True if cycle["billing_month"]=="2025-01-01" else None)
        assert b["metrics"]["legacy_gs_refund_entitlement_confirmed"] is (True if plan=="GS-S" and cycle["billing_month"]=="2025-01-01" else None)
        if cycle["billing_month"]<"2025-04-01":
            assert b["unrounded_lines"]["led_conversion"]==0. and b["metrics"]["ledc_start_window_interpretation"]
        else:assert b["unrounded_lines"]["led_conversion"]>0.
        assert scope==("verified_charges_subtotal" if expected else "complete_utility_bill")
        state=b["next_state"]
    assert refunds==([-6.19] if plan=="RS" else [-4.84])+[0.]*11
    assert state["january_refund_applied"] is True and state["through_month"]=="2025-12-01"
    assert state["rs_peak_upper_bound_kw" if plan=="RS" else "gs_qualification_upper_bound_kwh"]==(25. if plan=="RS" else 1500.)


@pytest.mark.parametrize("kind,plan",CASES)
def test_counterfactual_preserves_independent_history_and_refund_state(kind,plan):
    a=case_request(UTILITY,kind,"monthly",plan=plan)["account"]
    state={"january_refund_applied":True,"through_month":"2026-05-01",("rs_peak_upper_bound_kw" if plan=="RS" else "gs_qualification_upper_bound_kwh"):(25. if plan=="RS" else 1500.)}
    c=grid_only_counterfactual(UTILITY,a,state=state)
    assert c["account"]["der_ordinary_service_confirmed"] is False
    assert c["account"]["der_activation_date"]==c["account"]["der_eligibility_source"]==""
    assert c["state"]==state and a["der_ordinary_service_confirmed"] is True
    for k in a:
        if k not in ("der_ordinary_service_confirmed","der_activation_date","der_eligibility_source"):assert c["account"][k]==a[k]


@pytest.mark.parametrize("kind,plan",CASES)
def test_queued_worker_real_bills_saved_settings_and_csv_zip(service,kind,plan):
    app,call,headers=service;r=browser_request(case_request(UTILITY,kind,"monthly",plan=plan))
    queued=call("/api/v1/regional/studies",r,headers);study=wait_for_study(call,queued["id"])
    assert study["status"]=="completed",study.get("error")
    result=study["result"];assert result["engine_id"]==app.engine["id"] and result["is_complete_bill"] is True
    assert set(result["billing"])=={"grid_only","pv_only","pv_battery"}
    for scenario,bills in result["billing"].items():
        b=bills[0];assert len(bills)==1 and b["is_complete_bill"] and b["excluded_components"]==[] and b["export_kwh"]<1e-5
        assert b["total_usd"]==pytest.approx(sum(b["lines"].values()))
        assert b["rate_evidence_status"]=="verified" and b["metrics"]["rounded_cash_optimum_claimed"] is False
        assert result["optimization"][scenario]["annual_optimum_proven"] is None
    assert result["ac_validation"]["all_intervals_feasible"]
    assert all(x["checked_intervals"]==2880 and x["failed_intervals"]==0 for x in result["ac_validation"]["scenarios"])
    base="/api/studies/"+queued["id"]
    t=call(base+"/tables/comparison");rows=[dict(zip(t["columns"],r)) for r in t["data"]]
    assert max(r["maximum_reconciliation_difference_usd"] for r in rows)<.0001
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as z:
        assert z.testzip() is None and json.loads(z.read("result-manifest.json"))==result
        assert all("ac-"+s+".csv" in z.namelist() for s in result["billing"])
    call(base+"/save",{"name":"Penn Power "+plan+" targeted acceptance"},headers)
    saved=call(base+"/request.json");assert saved["account"]==r["account"] and saved["regional_account"]==r["regional_account"]
    assert browser_request(saved)["account"]==r["account"]


@pytest.mark.parametrize("kind,plan",CASES)
def test_native_quantity_guard_cannot_be_evaded_by_pv_reduced_imports(kind,plan):
    r=case_request(UTILITY,kind,"monthly",plan=plan);grid,_,_,_=prepare(r)
    native=np.full(len(grid.index),3. if plan=="GS-S" else 1.)
    if plan=="RS":native[0]=25.001
    assert plan=="RS" or native.sum()*.25>1500.
    r["load"].update(mode="csv",csv=pd.DataFrame({"timestamp":grid.index,"native_load_kw":native}).to_csv(index=False),source="Explicit hypothetical native-load eligibility boundary",native_basis_confirmed=True)
    with pytest.raises(ValueError,match="native"):prepare(r)
    r=case_request(UTILITY,kind,"monthly",plan=plan)
    field="rs_history_through_month" if plan=="RS" else "gs_history_through_month"
    assert r["account"][field]==history_through(r["start_date"])
    r["account"][field]="2026-04-01"
    with pytest.raises(ValueError,match="history"):prepare(r)


@pytest.mark.parametrize("kind,plan",CASES)
def test_scope_audit_detects_tax_provenance_state_and_completeness_changes(kind,plan):
    r=case_request(UTILITY,kind,"monthly",plan=plan);grid,load,cycles,e=prepare(r);a=cycle_account(r["account"],cycles[0][2])
    b=calculate_cycle(UTILITY,grid.index,load,np.zeros(len(load)),a,equipment=e)
    assert checked_bill_scope(b,UTILITY,a,grid.index)==("complete_utility_bill",[])
    for key,value in (("is_complete_bill",False),("rate_evidence_status","provisional"),("excluded_components",["missing"])):
        bad=deepcopy(b);bad[key]=value
        with pytest.raises(AssertionError):checked_bill_scope(bad,UTILITY,a,grid.index)
    for key,value in (("rounded_cash_optimum_claimed",True),("additional_grt_percentage_applied",True),("source_versions",{}),("current_charge_minimum_domain_verified",False),("january_refund_sales_tax_status","assumed_zero"),("ledc_usd_kwh",0.),("ledc_applicability_status","conditional_conversion_only"),("ledc_start_window_interpretation","silently_assumed")):
        bad=deepcopy(b);bad["metrics"][key]=value
        with pytest.raises(AssertionError):checked_bill_scope(bad,UTILITY,a,grid.index)


@pytest.mark.parametrize("kind,plan",CASES)
def test_unsupported_dates_and_grid_charging_reject(kind,plan):
    for start,end in (("2024-12-01","2024-12-31"),("2026-07-01","2026-07-31"),("2026-09-01","2026-09-30"),("2026-11-01","2026-11-30"),("2026-06-01","2026-06-29")):
        with pytest.raises(ValueError):case_request(UTILITY,kind,"custom",plan=plan,start_date=start,end_date=end)
    r=case_request(UTILITY,kind,"monthly",plan=plan);r["operating_contract"].update(grid_charging_confirmed=True,renewable_only_charging=False)
    with pytest.raises(ValueError):prepare(r)


@pytest.mark.parametrize("kind,plan",CASES)
@pytest.mark.parametrize("stage",["dsic","stas"])
def test_scope_audit_rejects_internally_consistent_percentage_basis_omissions(kind,plan,stage):
    r=case_request(UTILITY,kind,"monthly",plan=plan);grid,load,cycles,e=prepare(r);a=cycle_account(r["account"],cycles[0][2])
    bad=calculate_cycle(UTILITY,grid.index,load,np.zeros(len(load)),a,equipment=e)
    raw=bad["unrounded_lines"];m=bad["metrics"];omitted=raw["led_conversion"];assert omitted>0.
    if stage=="dsic":
        m["dsic_basis_usd"]-=omitted;raw["distribution_dsic"]=m["dsic_basis_usd"]*m["dsic_fraction"]
        m["stas_basis_usd"]=sum(v for k,v in raw.items() if k not in ("state_tax_adjustment","sales_tax","january_refund"))
    else:m["stas_basis_usd"]-=omitted
    raw["state_tax_adjustment"]=m["stas_basis_usd"]*m["stas_fraction"]
    m["current_tariff_before_sales_tax_usd"]=sum(v for k,v in raw.items() if k not in ("sales_tax","january_refund"))
    raw["sales_tax"]=0. if plan=="RS" else m["current_tariff_before_sales_tax_usd"]*.06
    with pytest.raises(AssertionError,match="independently include"):checked_bill_scope(bad,UTILITY,a,grid.index)


@pytest.mark.parametrize("field",["gs_no_qualifying_gsds_history_confirmed","legacy_gs_refund_entitlement_confirmed"])
def test_browser_request_cannot_replace_gsds_or_legacy_refund_evidence_with_current_class(field):
    r=browser_request(case_request(UTILITY,"commercial","annual",plan="GS-S"));assert r["account"]["gs_small_confirmed"] is True
    assert r["account"][field] is True;r["account"][field]=False
    with pytest.raises(ValueError,match="history|historical|GSDS"):prepare(r)
