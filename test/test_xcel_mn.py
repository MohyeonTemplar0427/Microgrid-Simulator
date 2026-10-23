"""Independent Minnesota rate arithmetic, calendars and shared browser worker."""
from copy import deepcopy
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import xcel_mn as mn
from src.billing.regional import account_region, calculate_cycle
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.billing.regional_math import BillingMath
from src.billing.xcel_mn_rates import service_rates
from src.dispatch.regional import optimize_cycle
from src.local_web.regional_study import calendar_cycles, capabilities, defaults, prepare
from src.timeseries import build_interval_index
from test_local_web import service, wait_for_study
from test_regional_study import browser_request


def fixture(plan="A01", month="2026-07", step=15):
    start=month+"-01";end=str((pd.Timestamp(start)+pd.offsets.MonthEnd()).date())
    a=mn.hypothetical_defaults(plan);a.update(billing_month=start,bill_date=end)
    return a,build_interval_index(start,end,mn.TIMEZONE,step).index


@pytest.mark.parametrize("plan",mn.PLANS)
@pytest.mark.parametrize("month,fuel_res,fuel_ci,rdf,tcr_res,tcr_ci,cip,st_res,st_ci,res_factor",[
    ("2025-01",".02617",".02615",".001385",".004442",".003009","-.000389","-.00015",".00170",".0241"),
    ("2025-02",".02819",".02817",".001097",".004442",".003009","-.000389","-.00015",".00170",".0241"),
    ("2025-03",".02919",".02916",".001097",".004442",".003009","-.000389","-.00015",".00170",".0241"),
    ("2025-04",".00972",".00970",".001097",".004442",".003009","-.000389","-.00015",".00170",".0241"),
    ("2025-05",".02618",".02616",".001097",".004442",".003009","-.000389","-.00015",".00170",".0241"),
    ("2025-06",".02839",".02837",".001097",".004442",".003009","-.000389",".00570",".00518",".0241"),
    ("2025-07",".02787",".02783",".001097",".004442",".003009","-.000389",".00570",".00518",".0241"),
    ("2025-08",".02617",".02615",".001097",".004442",".003009","-.000389",".00570",".00518",".0241"),
    ("2025-09",".02300",".02299",".001097",".004442",".003009","-.000389",".00570",".00518",".0241"),
    ("2025-10",".02099",".02097",".001097",".004442",".003009","-.000389",".00570",".00518",".0241"),
    ("2025-11",".01839",".01837",".001097",".004442",".003009","-.000389",".00570",".00518",".0241"),
    ("2025-12",".01608",".01606",".001097",".004442",".003009",".001397",".00570",".00518",".0241"),
    ("2026-01",".01568",".01566",".001097",".004436",".003006",".001397",".00570",".00518",".0241"),
    ("2026-02",".01575",".01574",".001097",".004436",".003006",".001397",".00570",".00518",".0241"),
    ("2026-03",".01681",".01679",".001097",".004436",".003006",".001397",".00570",".00518",".0241"),
    ("2026-04",".02499",".02497",".001371",".006415",".004445",".001397",".00570",".00518",".0241"),
    ("2026-05",".02695",".02693",".001371",".006415",".004445",".001397",".00570",".00518",".02463"),
    ("2026-06",".02973",".02971",".001371",".006415",".004445",".001397",".00041",".00034",".02463"),
    ("2026-07",".02927",".02924",".001371",".006415",".004445",".001397",".00041",".00034",".02463"),
    ("2026-08",".02780",".02778",".001371",".006415",".004445",".001397",".00041",".00034",".02463"),
    ("2026-09",".02448",".02445",".001371",".006415",".004445",".001397",".00041",".00034",".02463"),
])
def test_independent_component_benchmark(plan,month,fuel_res,fuel_ci,rdf,tcr_res,tcr_ci,cip,st_res,st_ci,res_factor):
    a,idx=fixture(plan,month);res=plan in ("A01","A02");tou=plan in ("A02","A12")
    # Flat1kW, but TOU hours calculated independently with Python weekdays and
    # explicit fixture holiday dates, not the adapter's mask or price series.
    holiday_dates={"2025-01-01","2025-04-18","2025-05-26","2025-07-04","2025-09-01","2025-11-27","2025-12-25",
                   "2026-01-01","2026-04-03","2026-05-25","2026-07-03","2026-07-04","2026-09-07"}
    peak=sum(t.weekday()<5 and str(t.date()) not in holiday_dates and 9<=t.hour<21 for t in idx)/4
    hours=D(len(idx))/4;pk=D(str(peak));summer=6<=int(month[-2:])<=9
    unit=(".25879" if summer else ".21408") if res and tou else (".19782" if summer else ".16020") if tou else (".13069" if summer else ".11364") if res else (".11799" if summer else ".10094")
    energy=pk*D(unit)+(hours-pk)*D(".05171" if res else ".05182") if tou else hours*D(unit)
    expected=dict(customer=D(6),energy=energy,interim_rate_surcharge=(D(6)+energy)*D(".0714"),
        renewable_energy_standard=(D(6)+energy)*D(res_factor),affordability=D("2.12"),
        fuel=hours*D(fuel_res if res else fuel_ci),cip=hours*D(cip),rdf=hours*D(rdf),
        tcr=hours*D(tcr_res if res else tcr_ci),sales_true_up=hours*D(st_res if res else st_ci),
        mercury=D(0),environmental=D(0),state_energy_policy=D(0))
    expected["minnesota_sales_tax"]=sum(expected.values())*D(".07375")
    b=calculate_cycle(mn.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert b["unrounded_lines"]==pytest.approx({k:float(v) for k,v in expected.items()},abs=1e-8)
    assert b["unrounded_total_usd"]==pytest.approx(float(sum(expected.values())),abs=1e-8)
    assert b["total_usd"]==pytest.approx(sum(b["lines"].values()))
    assert b["is_complete_bill"] and b["rate_evidence_status"]=="verified"
    assert not b["metrics"]["measured_demand_charge"]
    assert b["metrics"]["fuel_category"]==("residential" if res else "commercial_non_demand")


@pytest.mark.parametrize("day,peak",[
    ("2025-01-01 12:00",False),("2025-04-18 12:00",False),
    ("2025-05-26 12:00",False),("2025-07-04 12:00",False),
    ("2025-09-01 12:00",False),("2025-11-27 12:00",False),
    ("2025-12-25 12:00",False),("2026-07-03 12:00",False),
    ("2027-07-05 12:00",False),("2021-12-31 12:00",False),
    ("2025-11-28 12:00",True),("2025-12-24 12:00",True),
    ("2025-06-19 12:00",True),("2026-07-02 12:00",True),
    ("2026-07-06 08:45",False),("2026-07-06 09:00",True),
    ("2026-07-06 20:45",True),("2026-07-06 21:00",False),
    ("2026-07-05 12:00",False)])
@pytest.mark.parametrize("plan",["A02","A12"])
def test_filed_tod_holidays_observance_and_boundaries(day,peak,plan):
    idx=pd.DatetimeIndex([pd.Timestamp(day,tz=mn.TIMEZONE)])
    assert bool(mn.periods(idx,plan)["peak"][0])==peak


def test_observed_holiday_bill_and_unaffected_standard():
    a,idx=fixture("A02");imp=np.zeros(len(idx))
    imp[(idx.day==2)&(idx.hour==12)]=1.;imp[(idx.day==3)&(idx.hour==12)]=1.
    b=calculate_cycle(mn.UTILITY,idx,imp,np.zeros(len(idx)),a)
    assert b["unrounded_lines"]["energy"]==pytest.approx(.25879+.05171)
    a["tariff"]="A01"
    assert calculate_cycle(mn.UTILITY,idx,imp,np.zeros(len(idx)),a)["unrounded_lines"]["energy"]==pytest.approx(2*.13069)


@pytest.mark.parametrize("day",["2024-12-31","2026-10-01","2027-01-01"])
def test_rate_gaps_and_future_coverage_reject(day):
    with pytest.raises(ValueError,match="coverage"):service_rates(day,"A01")


@pytest.mark.parametrize("key,value",[("eligibility_confirmed",False),("ordinary_service_confirmed",False),
    ("local_charges_confirmed",False),("tax_jurisdiction","minneapolis"),("tax_source",""),
    ("supply","miso_lmp"),("export_mode","net_metering"),("opening_credit_usd",10.),
    ("full_monthly_charges_confirmed",False),("cycle_kind","initial"),("phase","three")])
def test_account_eligibility_not_inferred(key,value):
    a,idx=fixture();a[key]=value
    with pytest.raises(ValueError):mn.validate_account(a,idx)


def test_cycle_resolution_dst_missing_data_and_classification():
    a,idx=fixture("A12","2025-03")
    assert len(idx)==2972 and calculate_cycle(mn.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)["import_kwh"]==743
    for bad in (idx.delete(20),idx.insert(20,idx[20]),idx.tz_convert("UTC"),idx[96:],idx[:-1]):
        with pytest.raises(ValueError):mn.validate_account(a,bad)
    aa,i30=fixture("A12","2025-03",30);mn.validate_account(aa,i30)
    with pytest.raises(ValueError,match="complete calendar"):
        mn.validate_account(a,build_interval_index("2025-03-15","2025-04-14",mn.TIMEZONE,15).index)
    a["small_general_confirmed"]=False
    with pytest.raises(ValueError,match="classification"):mn.validate_account(a,idx)
    a["small_general_confirmed"]=True
    with pytest.raises(ValueError,match="below25kW"):calculate_cycle(mn.UTILITY,idx,np.full(len(idx),25.),np.zeros(len(idx)),a)
    with pytest.raises(ValueError,match="non-export"):calculate_cycle(mn.UTILITY,idx,np.ones(len(idx)),np.ones(len(idx)),a)
    with pytest.raises(ValueError,match="carried"):calculate_cycle(mn.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a,state={"credit":1})


def test_non_export_equipment_and_counterfactual():
    a,idx=fixture("A10");equipment=dict(pv=True,battery=True,pv_dc_kw=10.,pv_ac_kw=8.,battery_kw=8.)
    mn.validate_account(a,idx,equipment)
    reference=grid_only_counterfactual(mn.UTILITY,a)
    assert reference["account"]["dg_enrollment_confirmed"] is False and a["dg_enrollment_confirmed"] is True
    with pytest.raises(ValueError,match="approved"):mn.validate_account(reference["account"],idx,equipment)
    with pytest.raises(ValueError,match="40kW"):mn.validate_account(a,idx,{**equipment,"pv_dc_kw":40.})
    with pytest.raises(ValueError,match="standalone"):mn.validate_account(a,idx,{**equipment,"pv":False})


@pytest.mark.parametrize("plan",mn.PLANS)
def test_fixed_schedule_symbolic_and_numeric_bill_agree(plan):
    a,idx=fixture(plan,"2025-04");n=len(idx);g=cp.Variable(n,nonneg=True)
    math=BillingMath(idx,convex=True,power_bound=3.)
    math.register_power(g,np.zeros(n),np.full(n,3.))
    result=mn.charge_lines(idx,g,cp.Constant(np.zeros(n)),a,math=math)
    problem=cp.Problem(cp.Minimize(sum(result["lines"].values())),[g==1.,*math.constraints])
    problem.solve(solver="SCIPY",scipy_options={"time_limit":20.})
    b=calculate_cycle(mn.UTILITY,idx,np.ones(n),np.zeros(n),a)
    assert problem.status=="optimal" and problem.value==pytest.approx(b["unrounded_total_usd"],abs=1e-6)


@pytest.mark.parametrize("plan",["A02","A12"])
def test_dispatch_bill_objective_and_flows(plan):
    a,idx=fixture(plan,"2025-04")
    pv=3*np.maximum(0,np.sin((idx.hour.to_numpy()-6)*np.pi/12))
    inputs=pd.DataFrame(dict(timestamp=idx,native_load_kw=np.full(len(idx),2.),pv_available_kw=pv))
    battery=defaults(mn.UTILITY,"residential" if plan=="A02" else "commercial",plan)["battery"]
    out=optimize_cycle(inputs,mn.UTILITY,a,battery=battery,terminal_energy=battery["energy_kWh"],grid_charging=True,time_limit=30.)
    assert out["cost_optimum_proven"] and out["reconciliation_difference_usd"]<.0001
    assert out["dispatch"].grid_export_kw.max()<1e-5


def test_separate_region_and_reproducible_case_contract():
    from tools.run_regional_validation import selected_cases,case_request
    r=defaults(mn.UTILITY);region=r["regional_account"];account_region(region,mn.UTILITY)
    assert r["timezone"]==mn.TIMEZONE and region["state_jurisdiction"]=="MN"
    assert region["resource_adequacy_zone"]=="LRZ1" and region["wholesale_pricing_location"] is None
    with pytest.raises(ValueError):account_region({**region,"resource_adequacy_zone":"LRZ5"},mn.UTILITY)
    assert len(capabilities()["utilities"][mn.UTILITY]["plans"])==4
    for _,kind,plan in selected_cases([mn.UTILITY]):
        q=case_request(mn.UTILITY,kind,plan=plan,period="monthly");prepare(q)
        assert q["start_date"]=="2025-04-01"
        annual=case_request(mn.UTILITY,kind,plan=plan,period="annual")
        prepare(annual)
        assert annual["start_date"]=="2025-01-01" and annual["end_date"]=="2025-12-31"
        assert len(annual["billing_cycles"])==12


@pytest.mark.parametrize("plan",mn.PLANS)
def test_browser_form_worker_scenarios_saved_bills_and_electrical_results(service,plan):
    app,call,headers=service
    r=defaults(mn.UTILITY,"residential" if plan in ("A01","A02") else "commercial",plan)
    r["operating_contract"].update(interconnection_confirmed=True,grid_charging_confirmed=True,reference="Explicit hypothetical approved Minnesota non-export account")
    r.update(start_date="2025-12-01",end_date="2025-12-31",billing_cycles=calendar_cycles("2025-12-01","2025-12-31"))
    r["account"].update(billing_month="2025-12-01",bill_date="2025-12-31")
    r=browser_request(r);prepare(r)
    study=call("/api/v1/regional/studies",r,headers);out=wait_for_study(call,study["id"])
    assert out["status"]=="completed",out.get("error")
    result=out["result"]
    assert result["engine_id"]==app.engine["id"] and result["ac_validation"]["all_intervals_feasible"]
    assert set(result["billing"])=={"grid_only","pv_only","pv_battery"}
    for bills in result["billing"].values():assert bills[0]["is_complete_bill"] and bills[0]["rate_evidence_status"]=="verified"
    base="/api/studies/"+study["id"]
    assert b"minnesota_sales_tax" in call(base+"/tables/billing-components.csv")
    assert b"scheduled_grid" in call(base+"/tables/ac-pv_battery.csv")
    assert call(base+"/tables.zip")[:2]==b"PK"
    call(base+"/save",{"name":"Minnesota "+plan+" acceptance"},headers)
    restored=call(base+"/request.json")
    assert restored["account"]==r["account"] and browser_request(restored)["account"]==r["account"]


def test_source_evidence_hashes():
    manifest=json.loads(Path("docs/utility_sources/xcel_mn/manifest.json").read_text())
    assert manifest["coverage_gap"]==[]
    for s in manifest["sources"]:
        if s.get("evidence_kind")=="browser_pdf_screenshot":
            assert s["original_pdf_sha256"] is None
            assert hashlib.sha256(Path(s["evidence_file"]).read_bytes()).hexdigest()==s["evidence_sha256"]
        else:
            assert len(s["sha256"])==64
        assert hashlib.sha256(Path(s["extracted_text"]).read_bytes()).hexdigest()==s["extracted_text_sha256"]


@pytest.mark.parametrize("plan,kwh,expected",[("A01",600.,3.42),("A02",600.,3.42),("A10",800.,4.14),("A12",800.,4.14)])
def test_filed_customer_notice_sales_true_up_example(plan,kwh,expected):
    # Docket25-56, clean Attachment L page2: independent published benchmark.
    a,idx=fixture(plan,"2025-06")
    imports=np.full(len(idx),kwh/(len(idx)*.25))
    b=calculate_cycle(mn.UTILITY,idx,imports,np.zeros(len(idx)),a)
    assert b["lines"]["sales_true_up"]==expected
    assert b["metrics"]["rider_versions"]["sales_true_up"]["start"]=="2025-06-01"


@pytest.mark.parametrize("component,before,after,previous,current",[
    ("sales_true_up","2025-05-31","2025-06-01",(-.00015,.00170),(.00570,.00518)),
    ("sales_true_up","2026-05-31","2026-06-01",(.00570,.00518),(.00041,.00034)),
    ("cip","2025-11-30","2025-12-01",(-.000389,-.000389),(.001397,.001397)),
    ("rdf","2025-01-31","2025-02-01",(.001385,.001385),(.001097,.001097)),
    ("rdf","2026-03-31","2026-04-01",(.001097,.001097),(.001371,.001371)),
    ("tcr","2025-12-31","2026-01-01",(.004442,.003009),(.004436,.003006)),
    ("tcr","2026-03-31","2026-04-01",(.004436,.003006),(.006415,.004445)),
    ("res_factor","2026-04-30","2026-05-01",(.0241,.0241),(.02463,.02463)),
])
def test_each_verified_rider_boundary(component,before,after,previous,current):
    for plan in mn.PLANS:
        c=0 if plan in ("A01","A02") else 1
        assert service_rates(before,plan)[component]==previous[c]
        assert service_rates(after,plan)[component]==current[c]
        if component in ("sales_true_up","cip","rdf","tcr"):
            # Local midnight date changes, rather than UTC-date assignment.
            idx=pd.DatetimeIndex([pd.Timestamp(before+" 23:45",tz=mn.TIMEZONE),pd.Timestamp(after+" 00:00",tz=mn.TIMEZONE)])
            assert mn.interval_rates(idx,plan)[component]==pytest.approx([previous[c],current[c]])


def test_coverage_and_rider_histories_are_continuous_and_unique():
    from src.billing.xcel_mn_rates import RIDER_HISTORY
    days=pd.date_range("2025-01-01","2026-09-30",freq="D")
    for day in days:
        key=str(day.date())
        for rows in RIDER_HISTORY.values():
            assert sum(start<=key<=end for start,end,_,_ in rows)==1
        for plan in mn.PLANS:
            assert np.isfinite(service_rates(key,plan)["sales_true_up"])


def test_fall_dst_bill_counts_repeated_hour_and_rejects_missing_fold():
    a,idx=fixture("A02","2025-11")
    assert len(idx)==2884
    assert sum(idx.date==pd.Timestamp("2025-11-02").date())==100
    b=calculate_cycle(mn.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert b["import_kwh"]==721.
    assert b["metrics"]["elapsed_hours"]==721.
    missing=idx.delete(np.flatnonzero((idx.day==2)&(idx.hour==1))[0])
    with pytest.raises(ValueError,match="missing/duplicate"):
        mn.validate_account(a,missing)


@pytest.mark.parametrize("plan",mn.PLANS)
def test_new_window_dispatch_objective_and_cip_bill_match(plan):
    a,idx=fixture(plan,"2025-12");n=len(idx)
    g=cp.Variable(n,nonneg=True);math=BillingMath(idx,convex=True,power_bound=3.)
    math.register_power(g,np.zeros(n),np.full(n,3.))
    out=mn.charge_lines(idx,g,cp.Constant(np.zeros(n)),a,math=math)
    problem=cp.Problem(cp.Minimize(sum(out["lines"].values())),[g==1.,*math.constraints])
    problem.solve(solver="SCIPY",scipy_options={"time_limit":20.})
    b=calculate_cycle(mn.UTILITY,idx,np.ones(n),np.zeros(n),a)
    assert problem.status=="optimal" and problem.value==pytest.approx(b["unrounded_total_usd"],abs=1e-6)
    assert b["unrounded_lines"]["cip"]==pytest.approx(744*.001397)
    assert b["unrounded_lines"]["sales_true_up"]==pytest.approx(744*(.00570 if plan in ("A01","A02") else .00518))
