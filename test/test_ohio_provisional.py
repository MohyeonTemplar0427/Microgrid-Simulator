"""Explicit assumed historical rates: arithmetic, provenance and worker contracts."""
from copy import deepcopy
from decimal import Decimal as D
import io
import json
import zipfile

import numpy as np
import pandas as pd
import pytest

from src.billing import firstenergy_oh as oh
from src.billing.firstenergy_oh_provisional import MODEL
from src.billing.regional import calculate_cycle, bill_scope
from src.local_web.regional_study import prepare
from test_firstenergy import account
from test_local_web import service, wait_for_study
from test_regional_study import browser_request
from tools import run_regional_validation as driver

OH=oh.UTILITY


def assumed_account(plan, start, end):
    a,idx=account(OH,plan,start,end)
    a.update(rate_evidence_mode="provisional_2025",provisional_assumptions_accepted=True,contract_demand_kw=10.)
    return a,idx


@pytest.mark.parametrize("plan",["RS","GS"])
@pytest.mark.parametrize("month",[2,4,7,8])
def test_independent_assumed_1000kwh_benchmark(plan,month):
    """Manual assumed composite, not evidence of actual historical bill accuracy."""
    start=f"2025-{month:02d}-01";end=(pd.Timestamp(start)+pd.offsets.MonthEnd()).date().isoformat()
    a,idx=assumed_account(plan,start,end)
    b=calculate_cycle(OH,idx,np.full(len(idx),1000/(len(idx)*.25)),np.zeros(len(idx)),a)
    rs=plan=="RS"; kwh=D("1000");demand=D("10")
    base=D("4")+kwh*D(".031898") if rs else D("7")+D("12.80")+D("5")*D("5.4635")
    if month==2:
        rates=[".073408","-.000167",".000409",".003073",".000030",".000483",".000022",".001151",".000436",".0028408"]
        rates += [".003080",".000006",".000252","-.001725",".003541",".021982",".009711"] if rs else [".002908",".000005",".002662","-.001028","-.000298",".0018007",".00029051"]
        fixed=D("2.185")-D(".51")+D("1.50")+D(".10") if rs else D("9.346")+demand*(D("6.2252")+D("3.2608"))
    elif month==4:
        rates=[".073408",".000207",".000920","-.002909",".000009",".000549",".000024",".001151",".000436",".0028408"]
        rates += [".003080",".000006",".000262","-.001725",".003541",".023602",".009711"] if rs else [".002908",".000004",".003090","-.001028","-.000298",".0018007",".00029051"]
        fixed=D("2.332")-D(".51")+D("1.50")+D(".10") if rs else D("9.081")+demand*(D("6.3482")+D("3.2608"))
    else:
        rates=[".073661",".000175",".000888","-.001206",".000015",".000709",".000026",".000462",".000476",".0028408"]
        rates += [".021953",".000002",".000190","-.001725",".003545",".023602",".009032"] if rs else [".021732",".000001",".001213","-.001028","-.000298"]
        fixed=D("1.514")-D(".51") if rs else D("5.450")+demand*(D("6.3482")+D("3.3606"))
        share=D("1") if month==7 else D("13")/D("31")
        if rs: fixed+=D("1.50")*share+(D(".10") if month==7 else 0)
        else:
            rates+=[str(D(".0018007")*share)]
            if month==7:rates += [".00029051"]
    expected=base+sum(map(D,rates))*kwh+fixed+D("4.65")/D(".9974")
    assert b["unrounded_total_usd"]==pytest.approx(float(expected),abs=1e-8)
    assert b["rate_evidence_status"]=="provisional" and b["is_complete_bill"]
    assert bill_scope(b)=="provisional_modeled_bill" and b["assumption_model"]==MODEL
    assert b["rate_assumptions"] and all(x["sources"] for x in b["rate_assumptions"])
    assert abs(b["total_usd"]-b["unrounded_total_usd"])<=b["rounding_bound_usd"]
    if month==8:
        assert b["unrounded_lines"]["legacy_generation"]==pytest.approx(1.5*13/31 if rs else 1000*.0018007*13/31)
        assert b["lines"]["solar_generation_fund"]==0


def test_default_and_saved_legacy_accounts_stay_strict_and_acceptance_is_explicit():
    a,idx=account(OH,"RS","2025-02-01","2025-02-28")
    assert a["rate_evidence_mode"]=="verified" and not a["provisional_assumptions_accepted"]
    for changes,match in [({},"No rate extrapolation"),({"rate_evidence_mode":"provisional_2025"},"acceptance"),
                          ({"rate_evidence_mode":"provisional_2025","provisional_assumptions_accepted":1},"acceptance"),
                          ({"rate_evidence_mode":"nearest"},"explicit mode")]:
        with pytest.raises(ValueError,match=match):calculate_cycle(OH,idx,np.ones(len(idx)),np.zeros(len(idx)),{**a,**changes})
    a.pop("rate_evidence_mode");a.pop("provisional_assumptions_accepted")
    with pytest.raises(ValueError,match="No rate extrapolation"):calculate_cycle(OH,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    for day in ("2024-12-31","2026-01-01"):
        with pytest.raises(ValueError,match="No rate extrapolation"):oh.rates_on(day,mode="provisional_2025")


@pytest.mark.parametrize("day",["2025-01-31","2025-06-01","2025-08-14","2025-09-01","2025-10-01","2025-12-31"])
def test_provisional_mode_does_not_replace_verified_dates(day):
    assert oh.rates_on(day)==oh.rates_on(day,mode="provisional_2025")


def test_dated_assumptions_do_not_blur_bill_date_and_service_date():
    assert oh.rates_on("2025-01-31")["dcr_basis"]=="base_distribution"
    assert oh.rates_on("2025-02-01",mode="provisional_2025")["dcr_basis"]=="energy_or_demand"
    assert oh.rates_on("2025-05-31",mode="provisional_2025")["supply_energy"]==.073408
    assert oh.rates_on("2025-06-01")["supply_energy"]==.073661
    a,idx=assumed_account("RS","2025-05-01","2025-05-31");a["bill_date"]="2025-06-01"
    b=calculate_cycle(OH,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert b["unrounded_lines"]["delivery_capital"]==pytest.approx(744*.009032)
    assert {v["id"] for v in b["rate_assumptions"]}=={"OE25-GEN18"}
    a,idx=assumed_account("RS","2025-03-01","2025-03-31")
    assert len(idx)==743*4
    b=calculate_cycle(OH,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert b["import_kwh"]==743 and b["unrounded_lines"]["advanced_meter"]==2.185


def test_provisional_scope_keeps_other_account_and_allocation_guards():
    a,idx=assumed_account("GS","2025-03-15","2025-04-14")
    with pytest.raises(ValueError,match="allocation"):calculate_cycle(OH,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    a,idx=assumed_account("RS","2025-02-01","2025-02-28")
    with pytest.raises(ValueError,match="zero export"):calculate_cycle(OH,idx,np.ones(len(idx)),np.ones(len(idx)),a)
    a["ordinary_service_confirmed"]=False
    with pytest.raises(ValueError,match="ordinary service"):calculate_cycle(OH,idx,np.ones(len(idx)),np.zeros(len(idx)),a)


@pytest.mark.parametrize("kind,plan",[("residential","RS"),("commercial","GS")])
def test_annual_preparation_and_validator_require_explicit_opt_in(kind,plan):
    with pytest.raises(ValueError,match="No rate extrapolation"):driver.case_request(OH,kind,plan=plan)
    r=driver.case_request(OH,kind,plan=plan,allow_ohio_provisional=True)
    grid,_,cycles,_=prepare(r)
    assert len(grid.index)==35040 and len(cycles)==12 and r["account"]["provisional_assumptions_accepted"]
    assert len(grid.index[grid.index.month==3])==743*4 and len(grid.index[grid.index.month==11])==721*4
    r["billing_cycles"][0]["account_overrides"]={"rate_evidence_mode":"verified"}
    with pytest.raises(ValueError,match="cannot change"):prepare(r)


@pytest.mark.parametrize("kind,plan,month",[("residential","RS",2),("commercial","GS",8)])
def test_provisional_form_worker_artifacts_save_restore_and_audit(service,kind,plan,month):
    app,call,headers=service
    start=f"2025-{month:02d}-01";end=(pd.Timestamp(start)+pd.offsets.MonthEnd()).date().isoformat()
    r=driver.case_request(OH,kind,"custom",plan=plan,start_date=start,end_date=end,allow_ohio_provisional=True)
    r=browser_request(r)
    study=call("/api/v1/regional/studies",r,headers)
    out=wait_for_study(call,study["id"])
    assert out["status"]=="completed",out.get("error")
    result=out["result"];assert result["rate_evidence_status"]=="provisional"
    path=app.store.directory/"runs"/study["id"]
    rows,_,_=driver.audit(path,r,app.engine["id"],allow_ohio_provisional=True)
    assert rows.rate_evidence_status.eq("provisional").all()
    with pytest.raises(AssertionError,match="opt-in"):driver.audit(path,r,app.engine["id"])
    base="/api/studies/"+study["id"]
    csv=call(base+"/tables/billing-assumptions.csv")
    assumptions=pd.read_csv(io.BytesIO(csv))
    assert set(assumptions.scenario)=={"grid_only","pv_only","pv_battery"}
    assert assumptions.assumption_model.eq(MODEL).all()
    comparison=call(base+"/tables/comparison")
    records=[dict(zip(comparison["columns"],row)) for row in comparison["data"]]
    assert all(x["objective_scope"]=="provisional_modeled_bill" and x["rate_evidence_status"]=="provisional" for x in records)
    with zipfile.ZipFile(io.BytesIO(call(base+"/tables.zip"))) as z:
        name=next(n for n in z.namelist() if n.endswith("billing-assumptions.csv"))
        assert z.read(name)==csv
    call(base+"/save",{"name":"Ohio provisional review"},headers)
    restored=call(base+"/request.json")
    assert call(base)["saved"] and browser_request(restored)["account"]==r["account"]
    manifest=json.loads((path/"result.json").read_text());manifest["billing"]["grid_only"][0]["rate_evidence_status"]="verified"
    (path/"result.json").write_text(json.dumps(manifest))
    with pytest.raises(AssertionError,match="provenance"):driver.audit(path,r,app.engine["id"],allow_ohio_provisional=True)
