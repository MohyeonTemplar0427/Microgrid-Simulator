"""DTE independent arithmetic, dated rider clocks, MISO and worker contracts."""
from copy import deepcopy
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import pytest

from src.billing import dte
from src.billing.dte_rates import rendered_rates, service_rates
from src.billing.regional import account_region, calculate_cycle
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.billing.regional_math import BillingMath
from src.dispatch.regional import optimize_cycle
from src.local_web.regional_study import defaults, prepare
from src.timeseries import build_interval_index
from test_local_web import service, wait_for_study
from test_regional_study import browser_request


def account(plan="D1.11", month="2025-07"):
    start = month+"-01"
    end = str((pd.Timestamp(start)+pd.offsets.MonthEnd()).date())
    idx = build_interval_index(start, end, dte.TIMEZONE, 15).index
    a = dte.hypothetical_defaults(plan)
    a.update(billing_month=start, bill_date=end)
    return a, idx


@pytest.mark.parametrize("month,dist,capacity,energy,ns,irm,pscr,river,tcsc,secur,ewr,lieaf", [
    ("2025-01",".08137",(".01438",".01241"),(".08518",".07354"),".000882",".000941",".0025",".000255",".001862",".001575",".002699",".87"),
    ("2025-07",".08907",(".05649",".03403"),(".08838",".05325"),".000911",".000941",".0025",".000242",".001862",".001749",".002699",".87"),
    ("2025-12",".08907",(".03984",".03403"),(".06233",".05325"),".000911",".000941",".0025",".000242",".002292",".001749",".002699","1.25"),
    ("2026-07",".09726",(".05360",".03240"),(".09047",".05469"),".000890",".002762",".01877",".000221",".002292",".001617",".004488","1.25"),
    ("2026-09",".09726",(".05360",".03240"),(".09047",".05469"),".000890",".002762",".01877",".000221",".002292",".001617",".004488","1.50"),
])
def test_independent_residential_benchmark(month,dist,capacity,energy,ns,irm,pscr,river,tcsc,secur,ewr,lieaf):
    a,idx = account(month=month)
    peak = sum(t.dayofweek<5 and 15<=t.hour<19 for t in idx)
    on,off = D(peak)/4,D(len(idx)-peak)/4
    kwh = on+off
    subtotal = D("8.50")+kwh*sum(D(v) for v in (dist,ns,irm,pscr,river,tcsc,secur,ewr))
    subtotal += on*(D(capacity[0])+D(energy[0]))+off*(D(capacity[1])+D(energy[1]))
    bill = calculate_cycle("dte_electric",idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert bill["unrounded_total_usd"] == pytest.approx(float(subtotal*D("1.04")+D(lieaf)),abs=1e-8)
    assert bill["unrounded_lines"]["sales_tax"] == pytest.approx(float(subtotal*D(".04")))
    assert bill["metrics"]["peak_kwh"] == float(on)
    assert bill["is_complete_bill"] and bill["rate_evidence_status"] == "verified"
    assert not any("demand" in k or "lmp" in k for k in bill["lines"])


@pytest.mark.parametrize("plan",["D3","D3.11"])
@pytest.mark.parametrize("month",["2025-07","2026-07"])
def test_commercial_independent_benchmark(plan,month):
    a,idx = account(plan,month)
    year = month[:4]
    # Independent filed cents, no calls to the production rate selector.
    cap = ("2.763","2.763") if plan=="D3" else ("4.347","2.593")
    gen = ("5.413","5.413") if plan=="D3" else ("8.516","5.079")
    if year=="2026":
        cap = ("2.603","2.603") if plan=="D3" else ("4.086","2.496")
        gen = ("5.562","5.562") if plan=="D3" else ("8.730","5.332")
    dist,ns,irm,pscr,river,tcsc,secur,ewr = (("5.858",".0911",".0595",".250",".0197",".1521",".1145","33.51") if year=="2025" else
                                           ("6.670",".0890",".1796","1.877",".0180",".1867",".1058","29.81"))
    on = D(sum(plan!="D3" and t.dayofweek<5 and 13<=t.hour<17 for t in idx))*D(".5")
    kwh = D(len(idx))*D(".5")
    subtotal = D("11.25")+D(ewr)+kwh*sum(D(v) for v in (dist,ns,irm,pscr,river,tcsc,secur))/100
    subtotal += (on*(D(cap[0])+D(gen[0]))+(kwh-on)*(D(cap[1])+D(gen[1])))/100
    b=calculate_cycle("dte_electric",idx,np.full(len(idx),2.),np.zeros(len(idx)),a)
    assert b["unrounded_total_usd"] == pytest.approx(float(subtotal*D("1.06")+D(".87" if year=="2025" else "1.25")),abs=1e-8)
    assert b["metrics"]["measured_demand_charge"] is False


@pytest.mark.parametrize("month,fees",[("2025-01",(5.53,33.51,140.98)),("2026-01",(5.75,34.85,146.61)),("2026-02",(4.91,29.81,125.39))])
@pytest.mark.parametrize("kwh,band",[(849.,0),(850.,0),(851.,1),(1650.,1),(1651.,2)])
def test_ewr_bands_numeric_and_fixed_schedule_optimizer(month,fees,kwh,band):
    import cvxpy as cp
    a,idx=account("D3",month)
    power=np.full(len(idx),kwh/(len(idx)*.25))
    energy=float(power.sum()*.25)
    # Use exact threshold energy for the mathematical band test.
    assert dte.commercial_ewr(kwh,np.array(fees),BillingMath(idx)) == fees[band]
    if kwh not in (850.,1650.):
        bill=calculate_cycle("dte_electric",idx,power,power*0,a)
        assert bill["lines"]["energy_waste_reduction"]==fees[band]
    math=BillingMath(idx,convex=True,power_bound=10.)
    variable=cp.Variable()
    # Numeric constants can eliminate the disjunction exactly at a boundary.
    math.register(variable,kwh,kwh)
    math.constraints.append(variable==kwh)
    objective=dte.commercial_ewr(variable,np.array(fees),math)
    problem=cp.Problem(cp.Minimize(objective),math.constraints)
    problem.solve(solver="SCIPY")
    assert problem.status=="optimal"
    assert problem.value==pytest.approx(fees[band])


@pytest.mark.parametrize("lower,threshold,expected",[(800.,850.,4.91),(850.,850.,4.91),(1650.,1650.,29.81)])
def test_ewr_exact_boundary_remains_feasible_with_nonconstant_bounds(lower,threshold,expected):
    import cvxpy as cp
    _,idx=account("D3")
    math=BillingMath(idx,convex=True,power_bound=10.)
    x=math.register(cp.Variable(),lower,1800.)
    math.constraints.append(x==threshold)
    fee=dte.commercial_ewr(x,np.array([4.91,29.81,125.39]),math)
    problem=cp.Problem(cp.Minimize(fee),math.constraints)
    problem.solve(solver="SCIPY")
    assert problem.value==pytest.approx(expected)
    assert dte.commercial_ewr(threshold+5e-7,np.array([4.91,29.81,125.39]),BillingMath(idx))==expected
    assert dte.commercial_ewr(threshold+2e-6,np.array([4.91,29.81,125.39]),BillingMath(idx))>expected


@pytest.mark.parametrize("threshold",[850.,1650.])
@pytest.mark.parametrize("offset",[-5e-7,0.,5e-7,1e-6,2e-6])
def test_ewr_numeric_shortcut_and_fixed_milp_share_cutoff(threshold,offset):
    import cvxpy as cp
    _,idx=account("D3")
    fees=np.array([4.91,29.81,125.39]);value=threshold+offset
    expected=dte.commercial_ewr(value,fees,BillingMath(idx))
    for lower,upper in [(value,value),(value,value+100.),(value-100.,value+100.)]:
        math=BillingMath(idx,convex=True,power_bound=10.)
        x=math.register(cp.Variable(),lower,upper)
        math.constraints.append(x==value)
        fee=dte.commercial_ewr(x,fees,math)
        problem=cp.Problem(cp.Minimize(fee),math.constraints)
        # Exercise geometry at sub-mWh distances using HiGHS's MIP (rather
        # than LP) feasibility option. SciPy forwards this supported native
        # HiGHS option while issuing an unrecognized-SciPy-option notice.
        # Production dispatch separately rejects any authoritative rebill
        # mismatch; this fixture does not relax that acceptance check.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore",message="Unrecognized options detected",category=RuntimeWarning)
            problem.solve(solver="SCIPY",scipy_options={"mip_feasibility_tolerance":1e-9,"mip_rel_gap":0.})
        assert problem.status=="optimal"
        assert problem.value==pytest.approx(expected)


@pytest.mark.parametrize("date,pscr,river,tcsc,secur,ewr,lieaf",[
    ("2025-03-31",.0025,.000209,.001521,.000996,5.53,.87),
    ("2025-04-01",.0025,.000197,.001521,.001145,5.53,.87),
    ("2025-11-30",.0025,.000197,.001521,.001145,5.53,1.25),
    ("2025-12-01",.0025,.000197,.001867,.001145,5.53,1.25),
    ("2026-01-01",.0025,.000197,.001867,.001145,5.75,1.25),
    ("2026-02-01",.0025,.000197,.001867,.001145,4.91,1.25),
    ("2026-03-01",.01877,.000197,.001867,.001145,4.91,1.25),
    ("2026-04-01",.01877,.000180,.001867,.001058,4.91,1.25),
    ("2026-09-01",.01877,.000180,.001867,.001058,4.91,1.50)])
def test_bills_rendered_rider_boundaries(date,pscr,river,tcsc,secur,ewr,lieaf):
    r=rendered_rates(date,False)
    assert [r[k] for k in ("pscr","river_rouge","tcsc","delivery_securitization","lieaf")] == pytest.approx([pscr,river,tcsc,secur,lieaf])
    assert r["commercial_ewr"][0]==ewr


def test_optimizer_respects_ewr_step_when_energy_can_change():
    import cvxpy as cp
    _,idx=account("D3")
    math=BillingMath(idx,convex=True,power_bound=10.)
    energy=math.register(cp.Variable(),800.,1800.)
    math.constraints.extend([energy>=800.,energy<=1800.])
    fees=np.array([4.91,29.81,125.39])
    surcharge=dte.commercial_ewr(energy,fees,math)
    problem=cp.Problem(cp.Minimize(-.01*energy+surcharge),math.constraints)
    problem.solve(solver="SCIPY")
    assert problem.status=="optimal" and float(energy.value)==pytest.approx(850.,abs=2e-5)
    assert float(surcharge.value)==dte.commercial_ewr(float(energy.value),fees,BillingMath(idx))


@pytest.mark.parametrize("plan",dte.PLANS)
@pytest.mark.parametrize("day,is_peak",[("2025-07-04",True),("2025-07-05",False),("2026-01-01",True),("2026-07-03",True)])
def test_weekday_holidays_keep_plan_periods_and_boundaries(plan,day,is_peak):
    start=15 if plan=="D1.11" else 13
    idx=pd.date_range(day+f" {start-1}:45",periods=18,freq="15min",tz=dte.TIMEZONE)
    peak,_=dte.periods(idx,plan)
    assert not peak[0] and not peak[-1]
    assert peak[1:17].all() == (is_peak and plan!="D3")


@pytest.mark.parametrize("month,hours",[("2025-03",743),("2025-11",721)])
def test_dst_and_missing_intervals(month,hours):
    a,idx=account(month=month)
    assert calculate_cycle("dte_electric",idx,np.ones(len(idx)),np.zeros(len(idx)),a)["import_kwh"]==hours
    with pytest.raises(ValueError,match="consecutive"):
        dte.validate_account(a,idx.delete(5))
    with pytest.raises(ValueError,match="Eastern"):
        dte.validate_account(a,idx.tz_convert("UTC"))


@pytest.mark.parametrize("start,end,boundary,old,new",[
    ("2025-01-20","2025-02-19","2025-02-06",.05288,.05858),
    ("2026-02-15","2026-03-17","2026-03-05",.05858,.06670)])
def test_crossing_cycle_service_dates_and_bill_month_riders(start,end,boundary,old,new):
    idx=build_interval_index(start,end,dte.TIMEZONE,15).index
    a=dte.hypothetical_defaults("D3");a.update(bill_date=end,billing_month=end[:7]+"-01")
    b=calculate_cycle("dte_electric",idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    before=idx<pd.Timestamp(boundary,tz=dte.TIMEZONE)
    assert b["unrounded_lines"]["distribution"]==pytest.approx((sum(before)*old+sum(~before)*new)*.25)
    assert b["unrounded_lines"]["pscr"]==pytest.approx(len(idx)*.25*(.0025 if start.startswith("2025") else .01877))
    assert b["lines"]["service"]==11.25 and len(b["metrics"]["base_versions"])==2


def test_guards_and_coverage_not_authorized_maximum_or_legacy_credit():
    a,idx=account("D3")
    for key,value in [("eligibility_confirmed",False),("ordinary_service_confirmed",False),("local_charges_confirmed",False),
                      ("opening_credit_usd",1.),("export_mode","nem"),("supply","choice"),("full_monthly_charges_confirmed",False)]:
        bad={**a,key:value}
        with pytest.raises(ValueError):dte.validate_account(bad,idx)
    for day in ("2024-12-31","2026-10-01"):
        with pytest.raises(ValueError):service_rates(day,"D3")
    with pytest.raises(ValueError,match="actual billed"):
        rendered_rates("2026-10-01",True)
    with pytest.raises(ValueError,match="2025-06-01"):
        service_rates("2025-05-31","D3.11")
    with pytest.raises(ValueError,match="26–35"):
        dte.validate_account(a,idx[:96*10])
    with pytest.raises(ValueError,match="zero exports"):
        calculate_cycle("dte_electric",idx,np.ones(len(idx)),np.ones(len(idx)),a)
    with pytest.raises(ValueError,match="≤1000"):
        calculate_cycle("dte_electric",idx,np.full(len(idx),1001.),np.zeros(len(idx)),a)
    with pytest.raises(ValueError,match="credit"):
        calculate_cycle("dte_electric",idx,np.ones(len(idx)),np.zeros(len(idx)),a,state={"credits":1.})


def test_dg_eligibility_and_absent_equipment_counterfactual():
    a,idx=account()
    equipment=dict(pv=True,battery=True,pv_dc_kw=5.,pv_ac_kw=4.,battery_kw=3.)
    dte.validate_account(a,idx,equipment)
    with pytest.raises(ValueError,match="20 kW"):
        dte.validate_account(a,idx,{**equipment,"pv_dc_kw":20.})
    ref=grid_only_counterfactual("dte_electric",a)
    assert a["dg_enrollment_confirmed"] and not ref["account"]["dg_enrollment_confirmed"]
    assert ref["account"]["tariff"]==a["tariff"]
    dte.validate_account(ref["account"],idx,dict(pv=False,battery=False))
    with pytest.raises(ValueError,match="Rider 18"):
        dte.validate_account(ref["account"],idx,equipment)
    with pytest.raises(ValueError,match="renewable-PV"):
        dte.validate_account(a,idx,dict(pv=False,battery=True))


def test_miso_identity_does_not_select_wholesale_node_or_territory():
    r=defaults("dte_electric")
    region=r["regional_account"]
    assert region["grid_operator"]=="MISO" and region["transmission_zone"] is None
    assert region["resource_adequacy_zone"]=="LRZ7" and region["wholesale_pricing_location"] is None
    account_region(region,"dte_electric")
    for key,value in [("grid_operator","PJM"),("transmission_zone","LRZ7"),("state_jurisdiction","IL")]:
        with pytest.raises(ValueError,match="independently consistent"):
            account_region({**region,key:value},"dte_electric")
    with pytest.raises(ValueError,match="cpnode"):
        account_region({**region,"wholesale_pricing_location":{"pnode_id":1}},"dte_electric")
    explicit={"cpnode":"USER_VERIFIED_NODE","node_type":"Loadzone","source":"Explicit fixture provenance; not actual market data"}
    assert account_region({**region,"wholesale_pricing_location":explicit},"dte_electric")["wholesale_pricing_location"]==explicit


@pytest.mark.parametrize("plan",dte.PLANS)
def test_dispatch_rebills_all_components_and_zero_export(plan):
    a,idx=account(plan)
    inputs=pd.DataFrame(dict(timestamp=idx,native_load_kw=np.full(len(idx),1. if plan=="D1.11" else 2.),
                             pv_available_kw=np.maximum(0,np.sin((idx.hour.to_numpy()-6)*np.pi/12))*2.))
    battery=defaults("dte_electric","residential" if plan=="D1.11" else "commercial",plan)["battery"]
    result=optimize_cycle(inputs,"dte_electric",a,battery=battery,terminal_energy=battery["energy_kWh"],grid_charging=True,time_limit=30)
    assert result["cost_optimum_proven"]
    assert result["reconciliation_difference_usd"]<.0001
    assert result["dispatch"].grid_export_kw.max()<1e-6


@pytest.mark.parametrize("plan",dte.PLANS)
def test_form_to_worker_results_save_restore_and_artifacts(service,plan):
    app,call,headers=service
    r=defaults("dte_electric","residential" if plan=="D1.11" else "commercial",plan)
    r["operating_contract"].update(interconnection_confirmed=True,grid_charging_confirmed=True,
        reference="Hypothetical utility-approved zero-export DG/storage arrangement")
    r=browser_request(r)
    prepare(r)
    capabilities=call("/api/capabilities")["regional_simulation"]["utilities"]["dte_electric"]
    assert capabilities["grid_operator"]=="MISO"
    assert capabilities["resource_adequacy_zone"]=="LRZ7"
    study=call("/api/v1/regional/studies",r,headers)
    out=wait_for_study(call,study["id"])
    assert out["status"]=="completed",out.get("error")
    result=out["result"]
    assert set(result["billing"])=={"grid_only","pv_only","pv_battery"}
    assert result["ac_validation"]["all_intervals_feasible"]
    assert result["engine_id"]==app.engine["id"]
    assert all(b[0]["rate_evidence_status"]=="verified" for b in result["billing"].values())
    base="/api/studies/"+study["id"]
    assert b"energy_waste_reduction" in call(base+"/tables/billing-components.csv")
    assert b"scheduled_grid" in call(base+"/tables/ac-pv_battery.csv")
    assert len(call(base+"/tables.zip"))>0
    call(base+"/save",{"name":"DTE "+plan+" acceptance"},headers)
    restored=call(base+"/request.json")
    assert browser_request(restored)["regional_account"]==r["regional_account"]
    assert restored["account"]==r["account"]


def test_reproducible_driver_coverage_and_source_manifest():
    from tools.run_regional_validation import selected_cases, case_request
    assert {row[2] for row in selected_cases(["dte_electric"])}==set(dte.PLANS)
    assert len(case_request("dte_electric","residential",plan="D1.11")["billing_cycles"])==12
    assert len(case_request("dte_electric","commercial",plan="D3")["billing_cycles"])==12
    with pytest.raises(ValueError,match="June"):
        case_request("dte_electric","commercial",plan="D3.11")
    manifest=json.loads(Path("docs/utility_sources/dte/manifest.json").read_text())
    for source in manifest["sources"]:
        assert hashlib.sha256(Path(source["extracted_text"]).read_bytes()).hexdigest()==source["extracted_text_sha256"]
