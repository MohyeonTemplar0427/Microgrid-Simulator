"""Independent PECO tariff arithmetic, chronology, dispatch and saved workflows."""
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.billing import peco
from src.billing.regional import calculate_cycle
from src.local_web.regional_study import defaults, prepare
from src.dispatch.regional import optimize_cycle
from src.timeseries import build_interval_index
from test_local_web import service, wait_for_study
from test_regional_study import browser_request


def account(plan="R", month=7, year=2025):
    start = f"{year}-{month:02d}-01"
    end = (pd.Timestamp(start)+pd.offsets.MonthEnd()).date().isoformat()
    idx = build_interval_index(start, end, peco.TIMEZONE, 15).index
    a = peco.hypothetical_defaults(plan)
    a.update(billing_month=start, bill_date=end)
    return a, idx


@pytest.mark.parametrize("month,kwh,fixed,distribution,gsa,tsc", [
    (1, 700, "11.29", ".09655", ".08429", ".00858"),
    (4, 1000, "11.30", ".09655", ".08381", ".00858"),
    (7, 700, "11.30", ".09655", ".09508", ".00892"),
    (12, 700, "11.30", ".09649", ".10237", ".00787")])
def test_residential_independent_dated_benchmark(month,kwh,fixed,distribution,gsa,tsc):
    a, idx = account(month=month)
    p = np.full(len(idx), kwh/(len(idx)*.25))
    b = calculate_cycle("peco",idx,p,p*0,a)
    expected = D(fixed)+D(kwh)*(D(distribution)+D(gsa)+D(tsc))
    assert b["unrounded_total_usd"] == pytest.approx(float(expected),abs=1e-8)
    assert b["lines"]["sales_tax"] == 0
    assert b["is_complete_bill"]
    assert b["rate_evidence_status"]=="verified" and b["rate_assumptions"]==[]
    # No embedded rider is also charged as an extra bill line.
    assert not {"icus", "fars", "nbt", "usfc", "eepc", "capacity", "lmp"} & set(b["lines"])


@pytest.mark.parametrize("month,gsa,distribution,tsc,eepc", [
    (1,".08336","11.35","2.13",".00899"),
    (3,".07170","11.35","2.13",".00899"),
    (7,".08651","11.34","2.05",".00392"),
    (12,".09325","11.24","1.57",".00392")])
def test_commercial_independent_benchmark_and_sales_tax(month,gsa,distribution,tsc,eepc):
    a,idx=account("GS",month); p=np.full(len(idx),10.)
    b=calculate_cycle("peco",idx,p,p*0,a)
    kwh=D(str(len(idx)*2.5))
    expected=(D("74.66")+D("10")*(D(distribution)+D(tsc))+kwh*(D(gsa)+D(eepc)-D(".0006")))*D("1.06")
    assert b["unrounded_total_usd"] == pytest.approx(float(expected),abs=1e-8)
    assert b["metrics"]["billing_demand_kw"] == 10.
    a["tax_jurisdiction"]="philadelphia"
    philly=calculate_cycle("peco",idx,p,p*0,a)
    assert philly["unrounded_lines"]["sales_tax"] == pytest.approx(float(expected/D("1.06")*D(".08")))


@pytest.mark.parametrize("day,peak",[("2025-01-20",False),("2025-02-17",False),
    ("2025-05-26",False),("2025-07-04",False),("2025-11-28",False),
    ("2025-06-19",True),("2025-11-11",True),("2025-07-03",True),("2025-07-05",False)])
def test_pjm_holidays_not_peco_general_or_nerc_calendar(day,peak):
    idx=pd.date_range(day+" 13:45",periods=18,freq="15min",tz=peco.TIMEZONE)
    masks=peco.periods(idx)
    assert not masks["peak"][0]
    assert masks["peak"][1:17].all() == peak
    assert not masks["peak"][-1]
    assert np.all(sum(mask.astype(int) for mask in masks.values())==1)


@pytest.mark.parametrize("plan",["R-TOU","GS-TOU"])
@pytest.mark.parametrize("month,prices",[(1,((.28141,.04336,.06157),(.22515,.04406,.06521))),
    (3,((.27978,.04311,.06122),(.19367,.03790,.05609))),
    (6,((.29688,.04899,.07055),(.22645,.04669,.06863))),
    (12,((.31960,.05274,.07595),(.24405,.05032,.07397)))])
def test_tou_generation_bill_independent_interval_prices(plan,month,prices):
    a,idx=account(plan,month); power=np.full(len(idx),10. if plan.startswith("GS") else 1.)
    holiday_dates={"2025-01-01","2025-01-20","2025-12-25"}
    peak,super_off,off=prices[plan.startswith("GS")]
    rates=[super_off if t.hour<6 else peak if t.dayofweek<5 and t.strftime("%Y-%m-%d") not in holiday_dates and 14<=t.hour<18 else off for t in idx]
    b=calculate_cycle("peco",idx,power,power*0,a)
    assert b["unrounded_lines"]["generation"] == pytest.approx(np.dot(power,rates)*.25)
    assert sum(b["metrics"][p+"_kwh"] for p in ("peak","super_off_peak","off_peak")) == pytest.approx(b["import_kwh"])


@pytest.mark.parametrize("month,hours",[(3,743),(11,721)])
def test_dst_preserves_real_interval_hours(month,hours):
    a,idx=account("R-TOU",month); p=np.ones(len(idx))
    assert calculate_cycle("peco",idx,p,p*0,a)["import_kwh"] == hours
    if month==11:
        assert sum(idx.strftime("%Y-%m-%d %H:%M")=="2025-11-02 01:00")==2


def test_gs_demand_averaging_rounding_low_usage_and_minimum():
    a,idx=account("GS");p=np.full(len(idx),2.);p[0:2]=[18.,2.]
    b=calculate_cycle("peco",idx,p,p*0,a)
    assert b["metrics"]["measured_demand_kw"]==10.
    assert b["metrics"]["billing_demand_kw"]==10.
    p[:2]=10.049
    assert calculate_cycle("peco",idx,p,p*0,a)["metrics"]["billing_demand_kw"]==10.
    p[:2]=10.05
    assert calculate_cycle("peco",idx,p,p*0,a)["metrics"]["billing_demand_kw"]==10.1
    p[:]=0;p[:2]=20.
    b=calculate_cycle("peco",idx,p,p*0,a)
    assert b["metrics"]["billing_demand_kw"]==1.2
    p[:]=.8;p[:2]=20.
    b=calculate_cycle("peco",idx,p,p*0,a)
    assert b["metrics"]["billing_demand_kw"]==pytest.approx(b["import_kwh"]/175)


@pytest.mark.parametrize("plan",peco.PLANS)
def test_browser_serializes_full_year_and_driver_selects_every_plan(plan):
    from tools.run_regional_validation import case_request,selected_cases
    r=case_request("peco","residential" if plan.startswith("R") else "commercial",plan=plan)
    assert len(r["billing_cycles"])==12
    assert len(prepare(browser_request(r))[0].index)==35040
    assert len(selected_cases(["peco"]))==4


@pytest.mark.parametrize("field,value,match",[("eligibility_confirmed",False,"Confirm PECO"),
    ("ordinary_service_confirmed",False,"Confirm PECO"),("tou_eligibility_confirmed",False,"TOU"),
    ("supply","competitive","unsupported"),("tax_jurisdiction","unknown","jurisdiction"),
    ("tax_exempt",True,"exemptions")])
def test_account_guards(field,value,match):
    a,idx=account("R-TOU");a[field]=value
    with pytest.raises(ValueError,match=match):calculate_cycle("peco",idx,np.ones(len(idx)),np.zeros(len(idx)),a)


def test_reject_unverified_dates_crossings_partial_export_and_large_gs():
    for day in ("2024-12-31","2026-10-20", "2027-01-01"):
        with pytest.raises(ValueError,match="coverage"):peco.rates_on(day)
    a,idx=account()
    for start,end,match in [("2025-05-15","2025-06-14","rate-change"),("2025-07-01","2025-07-10","26–35")]:
        grid=build_interval_index(start,end,peco.TIMEZONE,15).index
        with pytest.raises(ValueError,match=match):calculate_cycle("peco",grid,np.ones(len(grid)),np.zeros(len(grid)),a)
    with pytest.raises(ValueError,match="export"):calculate_cycle("peco",idx,np.ones(len(idx)),np.ones(len(idx)),a)
    a,idx=account("GS")
    with pytest.raises(ValueError,match="≤100"):calculate_cycle("peco",idx,np.full(len(idx),101.),np.zeros(len(idx)),a)
    with pytest.raises(ValueError,match="capacity-reservation"):
        peco.validate_account(a,idx,equipment={"pv":True,"pv_ac_kw":100.})


@pytest.mark.parametrize("plan",peco.PLANS)
def test_bill_date_cannot_cross_an_applicable_rate_change(plan):
    a,idx=account(plan,5);a["bill_date"]="2025-06-01"
    with pytest.raises(ValueError,match="service/bill dates"):
        calculate_cycle("peco",idx,np.full(len(idx),2.),np.zeros(len(idx)),a)
    a,idx=account(plan,1);a["bill_date"]="2025-02-03"
    calculate_cycle("peco",idx,np.full(len(idx),2.),np.zeros(len(idx)),a)


def test_another_customer_class_change_does_not_block_gs_cycle():
    idx=build_interval_index("2025-03-15","2025-04-14",peco.TIMEZONE,15).index
    a=peco.hypothetical_defaults("GS");a["bill_date"]="2025-04-14"
    calculate_cycle("peco",idx,np.full(len(idx),10.),np.zeros(len(idx)),a)
    a["tariff"]="R"
    with pytest.raises(ValueError,match="rate-change"):
        calculate_cycle("peco",idx,np.ones(len(idx)),np.zeros(len(idx)),a)


@pytest.mark.parametrize("plan,power",[("R-TOU",1.),("GS-TOU",4.),("GS",.8)])
def test_dispatch_reconciles_rounded_demand_and_low_usage(plan,power):
    a,idx=account(plan); hour=idx.hour.to_numpy()
    inputs=pd.DataFrame(dict(timestamp=idx,native_load_kw=np.full(len(idx),power),
                             pv_available_kw=np.maximum(0,np.sin((hour-6)*np.pi/12))*2))
    b=defaults("peco","residential" if plan.startswith("R") else "commercial",plan)["battery"]
    result=optimize_cycle(inputs,"peco",a,battery=b,terminal_energy=b["energy_kWh"],grid_charging=True,time_limit=30)
    assert result["cost_optimum_proven"]
    assert abs(result["reconciliation_difference_usd"])<.0001
    assert np.max(result["dispatch"]["grid_export_kw"])<1e-5
    # Saved SOC is the START of the interval; the terminal state is separate.
    assert result["terminal_energy_kwh"]==pytest.approx(b["energy_kWh"])
    delta=.25*(result["dispatch"]["battery_charge_kw"].iloc[-1]*b["charge_efficiency"]-
               result["dispatch"]["battery_discharge_kw"].iloc[-1]/b["discharge_efficiency"])
    assert result["dispatch"]["energy_kWh"].iloc[-1]+delta==pytest.approx(b["energy_kWh"])


@pytest.mark.parametrize("plan,kind",[("R-TOU","residential"),("GS-TOU","commercial")])
@pytest.mark.parametrize("dates",[None,("2025-07-01","2025-07-31"),("2026-09-20","2026-10-19")])
def test_form_worker_save_restore_electrical_and_downloads(service,plan,kind,dates):
    app,call,headers=service
    r=defaults("peco",kind,plan)
    r["timestep_minutes"]=30
    if dates:
        from src.local_web.regional_study import calendar_cycles
        r.update(start_date=dates[0],end_date=dates[1])
        r["billing_cycles"]=calendar_cycles(*dates) if dates[0].startswith("2025") else [dict(
            start_date=dates[0],end_date=dates[1],billing_month="2026-10-01",bill_date=dates[1],
            kind="regular",source="Explicit hypothetical30-day cycle crossing DSIC only",account_overrides={})]
    r["operating_contract"].update(interconnection_confirmed=True,grid_charging_confirmed=True,reference="Explicit hypothetical approved PECO non-export case")
    r=browser_request(r)
    assert "peco" in call("/api/capabilities")["regional_simulation"]["utilities"]
    study=call("/api/v1/regional/studies",r,headers)
    out=wait_for_study(call,study["id"])
    assert out["status"]=="completed",out.get("error")
    assert out["result"]["rate_evidence_status"]=="verified"
    assert out["result"]["ac_validation"]["all_intervals_feasible"]
    assert len(out["result"]["ac_validation"]["scenarios"])==3
    base="/api/studies/"+study["id"]
    comparison=call(base+"/tables/comparison.csv")
    assert b"grid_only" in comparison and b"verified" in comparison and b"not_recorded" not in comparison
    assert b"scheduled_grid" in call(base+"/tables/ac-pv_battery.csv")
    if dates and dates[0].startswith("2026"):
        assert b"0.0105" in call(base+"/tables/billing-cycles.csv")
    assert len(call(base+"/tables.zip"))>1000
    call(base+"/save",{"name":"PECO "+plan+" acceptance"},headers)
    assert call(base)["saved"]
    restored=call(base+"/request.json")
    assert browser_request(restored)["account"]==r["account"]


def test_source_manifest_excerpts_are_present_and_immutable():
    folder=Path(__file__).resolve().parents[1]/"docs/utility_sources/peco"
    manifest=json.loads((folder/"manifest.json").read_text())
    assert manifest["reviewed_on"]=="2026-10-19"
    for s in manifest["sources"]:
        if "excerpt" in s:
            assert hashlib.sha256((folder/s["excerpt"]).read_bytes()).hexdigest()==s["excerpt_sha256"]
    assert {s["url"] for s in manifest["sources"]}==set(peco.SOURCES)


def test_grid_only_counterfactual_removes_only_der_assumptions():
    from src.billing.regional_counterfactual import grid_only_counterfactual
    a=peco.hypothetical_defaults("GS-TOU")
    ref=grid_only_counterfactual("peco",a)
    assert not ref["account"]["der_ordinary_service_confirmed"]
    assert ref["account"]["der_eligibility_source"]==""
    assert ref["account"]["tariff"]=="GS-TOU"
    assert a["der_ordinary_service_confirmed"]


@pytest.mark.parametrize("plan",peco.PLANS)
@pytest.mark.parametrize("month,fixed,dist,tsc,gsa,eepc,dsic",[
    (1, "11.30", ".10276", ".00787", ".10237", ".00176", "0"),
    (4, "11.29", ".10276", ".00787", ".10237", ".00176", ".0011"),
    (5, "11.29", ".10276", ".00787", ".10237", ".00176", ".0011"),
    (6, "11.29", ".10246", ".00974", ".10785", ".00232", ".0011"),
    (7, "11.29", ".10236", ".00974", ".10785", ".00232", ".0042"),
    (9, "11.29", ".10236", ".00974", ".10785", ".00232", ".0042"),
])
def test_2026_independent_benchmarks_all_plans_and_riders(plan,month,fixed,dist,tsc,gsa,eepc,dsic):
    a,idx=account(plan,month,2026);res=plan.startswith("R")
    power=np.full(len(idx),1. if res else 10.)
    kwh=D(str(power.sum()*.25))
    if not res:
        dist="11.50" if month<6 else "11.48"
        tsc="1.57" if month<6 else "2.20"
        gsa=".09325" if month<6 else ".10728"
        eepc=".00392" if month<6 else ".00121"
    distribution=(D(fixed)+kwh*D(dist) if res else
                  D("74.66")+D("10")*D(dist)+kwh*(D(eepc)-D(".0006")))
    if plan.endswith("TOU"):
        rprices=(.31960,.05274,.07595) if month<6 else (.31430,.05767,.08362)
        cprices=(.24405,.05032,.07397) if month<6 else (.26264,.06010,.08835)
        peak,sop,off=rprices if res else cprices
        holidays={"2026-01-01","2026-01-19","2026-05-25","2026-07-04","2026-09-07"}
        prices=[sop if t.hour<6 else peak if t.dayofweek<5 and 14<=t.hour<18 and t.strftime("%Y-%m-%d") not in holidays else off for t in idx]
        generation=D(str(np.dot(power,prices)*.25))
    else:
        generation=kwh*D(gsa)
    stas=distribution*D("-.0004")
    surcharge=(distribution+stas)*D(dsic)
    pretax=distribution+stas+surcharge+generation+(kwh if res else D("10"))*D(tsc)
    b=calculate_cycle("peco",idx,power,power*0,a)
    assert b["unrounded_total_usd"]==pytest.approx(float(pretax*(D(1) if res else D("1.06"))),abs=1e-7)
    assert b["unrounded_lines"]["state_tax_adjustment"]==pytest.approx(float(stas))
    assert b["unrounded_lines"]["distribution_dsic"]==pytest.approx(float(surcharge))
    assert b["unrounded_lines"]["generation"]==pytest.approx(float(generation))
    assert b["rate_evidence_status"]=="verified"
    if not res:
        a["tax_jurisdiction"]="philadelphia"
        assert calculate_cycle("peco",idx,power,power*0,a)["unrounded_total_usd"]==pytest.approx(float(pretax*D("1.08")))


@pytest.mark.parametrize("plan",peco.PLANS)
def test_october_dsic_crossing_uses_bill_date_without_splitting_demand(plan):
    idx=build_interval_index("2026-09-20","2026-10-19",peco.TIMEZONE,15).index
    a=peco.hypothetical_defaults(plan);a["bill_date"]="2026-10-19"
    power=np.full(len(idx),1. if plan.startswith("R") else 10.)
    b=calculate_cycle("peco",idx,power,power*0,a)
    distribution=sum(v for k,v in b["unrounded_lines"].items() if k.startswith("distribution_") and k!="distribution_dsic")+b["unrounded_lines"].get("energy_efficiency",0)
    assert b["unrounded_lines"]["state_tax_adjustment"]==pytest.approx(-.0004*distribution)
    assert b["unrounded_lines"]["distribution_dsic"]==pytest.approx(distribution*.9996*.0105)
    assert b["metrics"]["dsic_bill_date"]=="2026-10-19"
    assert b["metrics"]["dsic_fraction"]==.0105
    if plan.startswith("GS"):
        assert b["metrics"]["billing_demand_kw"]==10.
    a["bill_date"]="2026-10-20"
    with pytest.raises(ValueError,match="coverage"):
        calculate_cycle("peco",idx,power,power*0,a)


@pytest.mark.parametrize("day,peak",[("2026-01-19",False),("2026-02-16",False),
    ("2026-05-25",False),("2026-07-03",True),("2026-07-04",False),
    ("2026-06-19",True),("2026-09-07",False),("2026-11-27",False)])
def test_pjm_2026_published_dates_without_invented_friday_observance(day,peak):
    idx=pd.date_range(day+" 13:45",periods=18,freq="15min",tz=peco.TIMEZONE)
    masks=peco.periods(idx)
    assert not masks["peak"][0] and not masks["peak"][-1]
    assert masks["peak"][1:17].all()==peak


@pytest.mark.parametrize("month,field,old,new",[(1,"usfc",.00045,.00287),
    (4,"consumer_education",.05,.04),(6,"gsa",(.10237,.09325),(.10785,.10728)),
    (7,"icus",(0.,0.),(-.00009,0.)),(10,"dsic",.0042,.0105)])
def test_2026_exact_rate_boundaries(month,field,old,new):
    boundary=pd.Timestamp(f"2026-{month:02d}-01")
    assert peco.rates_on((boundary-pd.Timedelta(days=1)).date())[field]==old
    assert peco.rates_on(boundary.date())[field]==new


@pytest.mark.parametrize("plan",peco.PLANS)
def test_unverified_other_component_crossings_still_reject(plan):
    for start,end in [("2025-12-20","2026-01-18"),("2026-05-20","2026-06-18")]:
        idx=build_interval_index(start,end,peco.TIMEZONE,15).index
        a=peco.hypothetical_defaults(plan);a["bill_date"]=end
        with pytest.raises(ValueError,match="rate-change"):
            calculate_cycle("peco",idx,np.ones(len(idx)),np.zeros(len(idx)),a)


@pytest.mark.parametrize("plan",["R-TOU","GS-TOU"])
def test_2026_dispatch_reconciles_nonzero_dsic_and_stas(plan):
    a,idx=account(plan,9,2026)
    hour=idx.hour.to_numpy();kind="residential" if plan.startswith("R") else "commercial"
    power=(1.+(hour>=14)*1.)*(1 if kind=="residential" else 4)
    inputs=pd.DataFrame(dict(timestamp=idx,native_load_kw=power,
                             pv_available_kw=np.maximum(0,np.sin((hour-6)*np.pi/12))*2))
    b=defaults("peco",kind,plan)["battery"]
    result=optimize_cycle(inputs,"peco",a,battery=b,terminal_energy=b["energy_kWh"],grid_charging=True,time_limit=30)
    assert result["cost_optimum_proven"]
    assert abs(result["reconciliation_difference_usd"])<.0001
    assert result["bill"]["unrounded_lines"]["distribution_dsic"]>0
    assert result["bill"]["unrounded_lines"]["state_tax_adjustment"]<0


def test_browser_coverage_defaults_and_previous_2025_request_remain_valid():
    current=defaults("peco","residential","R-TOU")
    assert current["start_date"]=="2026-09-01"
    assert current["end_date"]=="2026-09-30"
    assert peco.catalog()[0]["coverage"]==[{"start":"2025-01-01","end":"2026-10-19"}]
    # Full 2025 driver requests still explicitly select that year, despite new defaults.
    from tools.run_regional_validation import case_request
    prior=browser_request(case_request("peco","residential",plan="R-TOU"))
    assert prior["start_date"]=="2025-01-01" and prior["end_date"]=="2025-12-31"
    assert len(prepare(prior)[0].index)==35040


def test_2026_spring_dst_and_independent_published_ptc():
    a,idx=account("R-TOU",3,2026)
    assert calculate_cycle("peco",idx,np.ones(len(idx)),np.zeros(len(idx)),a)["import_kwh"]==743.
    # Official PTC table is independently printed in cents, including GRT once.
    for day,expected in [("2026-05-31",.11024),("2026-06-01",.11759)]:
        r=peco.rates_on(day)
        assert r["gsa"][0]+r["tsc"][0]==pytest.approx(expected)
