"""Consumers filed arithmetic, account eligibility, clock/calendar and worker tests."""
from copy import deepcopy
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.billing import consumers as ce
from src.billing.consumers_rates import service_rates, rendered_rates
from src.billing.regional import account_region, calculate_cycle
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.dispatch.regional import optimize_cycle
from src.local_web.regional_study import defaults, prepare
from src.timeseries import build_interval_index
from test_local_web import service, wait_for_study
from test_regional_study import browser_request


def account(plan="RSP",month="2025-07"):
    start=month+"-01";end=str((pd.Timestamp(start)+pd.offsets.MonthEnd()).date())
    a=ce.hypothetical_defaults(plan);a.update(billing_month=start,bill_date=end)
    return a,build_interval_index(start,end,ce.TIMEZONE,15).index


@pytest.mark.parametrize("plan",ce.PLANS)
def test_independent_july_2025_component_benchmark(plan):
    a,idx=account(plan)
    # Separately transcribed filed totals, not production selectors.
    rates={"RSP":(".099222",".099222",".150563"),"RSH":(".099222",".099222",".150563"),
           "GS":(".105382",)*3,"GSTU":(".080255",".109833",".143964")}[plan]
    weights=[D(0),D(0),D(0)]
    for t in idx:
        if plan in ("RSP","RSH"):
            slot=2 if t.weekday()<5 and 14<=t.hour<19 else 0
        elif plan=="GS":slot=0
        elif t.weekday()>=5 or t.date().isoformat()=="2025-07-04":slot=0
        elif 14<=t.hour<18:slot=2
        elif 7<=t.hour<23:slot=1
        else:slot=0
        weights[slot]+=D(".5") # two kW, quarter hour
    kwh=sum(weights);res=plan in ("RSP","RSH")
    common=(".078955",".002250",".000259",".000293",".001090",".01127",".001187",".004556") if res else (
            ".063166",".002106",".000211",".000274",".000889",".01127",".001263",".004103")
    subtotal=D(8 if res else 20)+sum(w*D(r) for w,r in zip(weights,rates))+kwh*sum(D(v) for v in common)
    subtotal+=kwh*D(".004529") if res else D("125.14")
    b=calculate_cycle(ce.UTILITY,idx,np.full(len(idx),2.),np.zeros(len(idx)),a)
    assert b["unrounded_total_usd"]==pytest.approx(float(subtotal*D("1.04" if res else "1.06")+D(".87")),abs=1e-8)
    assert b["unrounded_lines"]["energy"]+b["unrounded_lines"]["capacity"]==pytest.approx(float(sum(w*D(r) for w,r in zip(weights,rates))))
    assert b["metrics"]["peak_kwh"]==float(weights[2])
    assert not b["metrics"]["measured_demand_charge"]
    assert b["is_complete_bill"] and b["rate_evidence_status"]=="verified"
    assert not any("lmp" in k for k in b["lines"])


@pytest.mark.parametrize("month,supply,dist,dr,irm,fcm,deferral,pscr,sec,karn,ee,lieaf,recon",[
 ("2025-01",".087554",".074267","0",".000150","0",".000430",".00794",".001187",".004556",".004529",".87","0"),
 ("2025-02",".087554",".074267","0",".000150","0",".000430",".00758",".001187",".004556",".004529",".87","-.14"),
 ("2026-01",".085252",".078955",".002250",".000259",".000243",".001090",".01456",".001131",".004049",".003777","1.25","0"),
 ("2026-05",".082996",".093333",".002224",".000699",".000243",".001221",".01456",".001131",".004049",".004617","1.25","-.02"),
])
def test_independent_winter_residential_benchmark(month,supply,dist,dr,irm,fcm,deferral,pscr,sec,karn,ee,lieaf,recon):
    a,idx=account(month=month)
    kwh=D(len(idx))/4
    subtotal=D(8)+D(recon)+kwh*sum(D(v) for v in (supply,dist,dr,irm,fcm,deferral,pscr,sec,karn,ee))
    b=calculate_cycle(ce.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert b["unrounded_total_usd"]==pytest.approx(float(subtotal*D("1.04")+D(lieaf)),abs=1e-8)
    assert b["unrounded_lines"]["sales_tax"]==pytest.approx(float(subtotal*D(".04")))


@pytest.mark.parametrize("day,old,new,key",[
 ("2025-04-04",.074267,.078955,"distribution"),
 ("2025-04-25",0.,.000293,"fcm"),
 ("2026-03-01",.000259,0.,"irm"),
 ("2026-04-04",.001090,0.,"deferral"),
 ("2026-05-01",.078955,.093333,"distribution"),
])
def test_precise_service_boundaries(day,old,new,key):
    assert service_rates(pd.Timestamp(day)-pd.Timedelta(days=1),"RSP")[key]==old
    assert service_rates(day,"RSP")[key]==new


@pytest.mark.parametrize("month,ee,sec,karn,lieaf,pscr",[
 ("2025-07",125.14,.001263,.004103,.87,.01127),
 ("2025-08",125.14,.001222,.004103,.87,.01127),
 ("2025-09",125.14,.001222,.004103,1.25,.01023),
 ("2025-10",125.14,.001222,.003662,1.25,.00909),
 ("2026-01",104.61,.001222,.003662,1.25,.01456),
 ("2026-02",129.62,.001222,.003662,1.25,.01456),
 ("2026-03",128.73,.001222,.003662,1.25,.01597),
 ("2026-06",128.73,.001222,.003662,1.25,.01337),
])
def test_assigned_ee_tier_and_monthly_riders(month,ee,sec,karn,lieaf,pscr):
    a,idx=account("GS",month)
    # Same account fee at very different current consumption; no MILP fee cliff.
    for power in (0.,1.,20.):
        b=calculate_cycle(ce.UTILITY,idx,np.full(len(idx),power),np.zeros(len(idx)),a)
        assert b["lines"]["energy_efficiency"]==ee
        assert b["metrics"]["ee_assigned_tier"]==3
    r=rendered_rates(month,False)
    assert (r["power_plant_securitization"],r["karn_securitization"],r["lieaf"],r["pscr"])==(sec,karn,lieaf,pscr)


@pytest.mark.parametrize("year",[2025,2026])
def test_calendar_holiday_and_observed_dates(year):
    def slot(day,hour,plan):
        return ce.periods(pd.DatetimeIndex([pd.Timestamp(f"{day} {hour}",tz=ce.TIMEZONE)]),plan,day[:7]+"-01")["slot"][0]
    # July4,2025 is Friday. Residential includes holidays; GSTU is off peak.
    if year==2025:
        assert slot("2025-07-04","14:00","RSP")==2
        assert slot("2025-07-04","14:00","RSH")==2
        assert slot("2025-07-04","14:00","GSTU")==0
        assert slot("2025-07-03","14:00","GSTU")==2
    else:
        assert slot("2026-07-03","14:00","GSTU")==2 # no Friday substitute
    for day in ce.commercial_holidays(year):
        assert slot(str(day),"15:00","GSTU") in (0,3)
    assert slot("2027-12-27","15:00","GSTU")==4 # no Monday substitute
    assert slot(f"{year}-01-01","15:00","RSP")==3 # flat winter


@pytest.mark.parametrize("clock,summer_slot,winter_slot",[("06:45",0,3),("07:00",1,4),("13:45",1,4),
 ("14:00",2,4),("17:45",2,4),("18:00",1,4),("22:45",1,4),("23:00",0,3)])
def test_gstu_exact_tou_boundaries(clock,summer_slot,winter_slot):
    for day,expected in [("2025-07-08",summer_slot),("2025-01-07",winter_slot)]:
        idx=pd.DatetimeIndex([pd.Timestamp(f"{day} {clock}",tz=ce.TIMEZONE)])
        assert ce.periods(idx,"GSTU",day[:7]+"-01")["slot"][0]==expected


def test_crossing_cycle_has_distinct_calendar_and_bill_month_seasons():
    idx=build_interval_index("2025-05-15","2025-06-14",ce.TIMEZONE,15).index
    for plan in ("RSP","GSTU"):
        a=ce.hypothetical_defaults(plan);a.update(billing_month="2025-06-01",bill_date="2025-06-14")
        b=calculate_cycle(ce.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
        p=ce.periods(idx,plan,a["billing_month"])
        assert np.all(p["summer"]) if plan=="GSTU" else not np.any(p["summer"][idx.month==5])
        assert b["unrounded_lines"]["pscr"]==pytest.approx(len(idx)*.25*.01084)
        assert b["lines"]["system_access"]==(8. if plan=="RSP" else 20.)
    # A normal cycle across base change allocates actual interval imports.
    idx=build_interval_index("2026-04-15","2026-05-14",ce.TIMEZONE,15).index
    a=ce.hypothetical_defaults("GS");a.update(billing_month="2026-05-01",bill_date="2026-05-14")
    b=calculate_cycle(ce.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    before=idx.month==4
    assert b["unrounded_lines"]["distribution"]==pytest.approx((sum(before)*.063166+sum(~before)*.069433)*.25)
    assert len(b["metrics"]["base_versions"])==2
    assert b["lines"]["irm_reconciliation"]==-.05


@pytest.mark.parametrize("month,hours",[("2025-03",743),("2025-11",721)])
def test_dst_missing_and_timezone(month,hours):
    a,idx=account(month=month)
    assert calculate_cycle(ce.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)["import_kwh"]==hours
    for minutes in (15,30):
        selected=idx[::minutes//15]
        ce.validate_account(a,selected)
    with pytest.raises(ValueError,match="consecutive"):ce.validate_account(a,idx.delete(2))
    with pytest.raises(ValueError,match="Eastern"):ce.validate_account(a,idx.tz_convert("UTC"))


def test_guard_eligibility_credits_der_and_coverage():
    a,idx=account("GSTU")
    for key,value in [("eligibility_confirmed",False),("ordinary_service_confirmed",False),
        ("full_monthly_charges_confirmed",False),("local_charges_confirmed",False),("tou_enrollment_confirmed",False),
        ("ee_tier",3.5),("ee_tier",True),("ee_tier",0),("ee_tier_source",""),("export_mode","net_metering"),
        ("opening_credit_usd",1.),("supply","choice")]:
        with pytest.raises(ValueError):ce.validate_account({**a,key:value},idx)
    with pytest.raises(ValueError,match="26–35"):ce.validate_account(a,idx[:100])
    with pytest.raises(ValueError,match="zero exports"):
        calculate_cycle(ce.UTILITY,idx,np.ones(len(idx)),np.ones(len(idx)),a)
    for day in ("2024-12-31","2026-07-01"):
        with pytest.raises(ValueError):service_rates(day,"RSP")
    with pytest.raises(ValueError,match="actual billed PSCR"):rendered_rates("2026-07",True)
    with pytest.raises(ValueError,match="settlement state"):
        calculate_cycle(ce.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a,state={"credit":1.})
    equipment=dict(pv=True,battery=True,pv_dc_kw=10.,pv_ac_kw=8.,battery_kw=8.)
    ce.validate_account(a,idx,equipment)
    with pytest.raises(ValueError,match="20 kW"):ce.validate_account(a,idx,{**equipment,"pv_dc_kw":13.})
    ref=grid_only_counterfactual(ce.UTILITY,a)
    assert not ref["account"]["dg_enrollment_confirmed"] and a["dg_enrollment_confirmed"]
    assert ref["account"]["ee_tier"]==a["ee_tier"]
    with pytest.raises(ValueError,match="C11.3"):ce.validate_account(ref["account"],idx,equipment)


def test_miso_identity_has_no_default_node_or_dte_owner():
    r=defaults(ce.UTILITY);region=r["regional_account"]
    assert region["grid_operator"]=="MISO" and region["transmission_zone"] is None
    assert region["resource_adequacy_zone"]=="LRZ7" and "METC" in region["transmission_owner"]
    assert region["wholesale_pricing_location"] is None
    account_region(region,ce.UTILITY)
    with pytest.raises(ValueError):account_region({**region,"transmission_owner":"ITC Transmission"},ce.UTILITY)


@pytest.mark.parametrize("plan",ce.PLANS)
def test_dispatch_authoritative_bill_reconciliation(plan):
    a,idx=account(plan)
    solar=np.maximum(0,np.sin((idx.hour.to_numpy()-6)*np.pi/12))*2.
    inputs=pd.DataFrame(dict(timestamp=idx,native_load_kw=np.full(len(idx),1.),pv_available_kw=solar))
    battery=defaults(ce.UTILITY,"residential" if plan in ("RSP","RSH") else "commercial",plan)["battery"]
    out=optimize_cycle(inputs,ce.UTILITY,a,battery=battery,terminal_energy=battery["energy_kWh"],grid_charging=True,time_limit=30)
    assert out["cost_optimum_proven"] and out["reconciliation_difference_usd"]<.0001
    assert out["dispatch"].grid_export_kw.max()<1e-6
    if plan in ("GS","GSTU"):
        assert out["bill"]["lines"]["energy_efficiency"]==125.14


@pytest.mark.parametrize("plan",ce.PLANS)
def test_main_form_worker_save_restore_and_ac_artifacts(service,plan):
    app,call,headers=service
    r=defaults(ce.UTILITY,"residential" if plan in ("RSP","RSH") else "commercial",plan)
    r["operating_contract"].update(interconnection_confirmed=True,grid_charging_confirmed=True,
        reference="Hypothetical approved Consumers zero-export DG/storage arrangement")
    r=browser_request(r);prepare(r)
    caps=call("/api/capabilities")["regional_simulation"]["utilities"][ce.UTILITY]
    assert caps["grid_operator"]=="MISO" and len(caps["plans"])==4
    study=call("/api/v1/regional/studies",r,headers);out=wait_for_study(call,study["id"])
    assert out["status"]=="completed",out.get("error")
    result=out["result"]
    assert set(result["billing"])=={"grid_only","pv_only","pv_battery"}
    assert result["ac_validation"]["all_intervals_feasible"]
    assert result["engine_id"]==app.engine["id"]
    assert all(b[0]["rate_evidence_status"]=="verified" for b in result["billing"].values())
    base="/api/studies/"+study["id"]
    assert b"energy_efficiency" in call(base+"/tables/billing-components.csv")
    assert b"scheduled_grid" in call(base+"/tables/ac-pv_battery.csv")
    assert len(call(base+"/tables.zip"))>0
    call(base+"/save",{"name":"Consumers "+plan+" acceptance"},headers)
    restored=call(base+"/request.json")
    assert browser_request(restored)["account"]==r["account"]
    assert restored["regional_account"]==r["regional_account"]


def test_reproducible_selection_and_source_hashes():
    from tools.run_regional_validation import selected_cases,case_request
    assert {row[2] for row in selected_cases([ce.UTILITY])}==set(ce.PLANS)
    for kind,plan in [("residential","RSP"),("commercial","GSTU")]:
        assert len(case_request(ce.UTILITY,kind,plan=plan)["billing_cycles"])==12
    manifest=json.loads(Path("docs/utility_sources/consumers/manifest.json").read_text())
    for s in manifest["sources"]:
        assert hashlib.sha256(Path(s["extracted_text"]).read_bytes()).hexdigest()==s["extracted_text_sha256"]
