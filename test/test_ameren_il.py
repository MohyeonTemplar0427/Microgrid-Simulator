"""Independent Ameren filed arithmetic, account guards and shared workflows."""
from copy import deepcopy
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.billing import ameren_il as ai
from src.billing.regional import UTILITIES,account_region,calculate_cycle
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.dispatch.regional import optimize_cycle
from src.local_web.regional_study import defaults,prepare,capabilities
from src.timeseries import build_interval_index
from test_local_web import service,wait_for_study
from test_regional_study import browser_request


def fixture(plan="DS-1",month="2025-07",zone="II",step=15):
    start=month+"-01";end=str((pd.Timestamp(start)+pd.offsets.MonthEnd()).date())
    a=ai.hypothetical_defaults(plan);a.update(billing_month=start,bill_date=end,rate_zone=zone)
    return a,build_interval_index(start,end,ai.TIMEZONE,step).index


def bill(plan="DS-1",month="2025-07",kwh=1000.,zone="II"):
    a,idx=fixture(plan,month,zone)
    return calculate_cycle(ai.UTILITY,idx,np.full(len(idx),kwh/(len(idx)/4)),np.zeros(len(idx)),a)


@pytest.mark.parametrize("plan",ai.PLANS)
@pytest.mark.parametrize("month,year,energy,pea,sca,eua,ts,dist,cust,meter,extra,fixed_eua,ceac,rea,ee,cgc,mapr,pbr,rba,edit",[
 ("2025-01",2025,(".05508",".06717"),"-.00073",(".00237",".00094"),(".00260",".00021"),(".02272",".02208"),(".04376",".03352"),("6.77","18.15"),("5.32","8.02"),(".73","6.90"),("1.22",".72"),".00189",".00458",(".00559",".00763"),(".16","2.48"),".1277","0",("0","0"),"-.0219"),
 ("2025-07",2025,(".09706",".12232"),"-.00270",(".00309",".00119"),("-.00099","-.00014"),(".02264",".02200"),(".07477",".06286"),("6.77","18.15"),("5.32","8.02"),("-.18","5.99"),(".24","1.18"),".00177",".00458",(".00559",".00763"),(".16","2.48"),".1286","0",("0","0"),"-.0219"),
 ("2026-01",2026,(".05927",".07109"),"-.00456",(".00312",".00121"),("-.00099","-.00014"),(".02629",".02555"),(".04572",".03551"),("7.42","22.74"),("5.96","8.94"),(".89","8.50"),(".24","1.18"),".00183",".00458",(".00644",".00816"),(".31","6.30"),"0",".0365",(".0309","-.0067"),"0"),
 ("2026-07",2026,(".08200",".10226"),"-.00095",(".00308",".00121"),(".00053",".00014"),(".02765",".02688"),(".07811",".06660"),("7.42","22.74"),("5.96","8.94"),("-.10","7.51"),("-.27",".33"),".00175",".00470",(".00644",".00816"),(".31","6.30"),".0001",".0365",(".0309","-.0067"),"0"),
])
def test_independent_complete_bill_benchmarks(plan,month,year,energy,pea,sca,eua,ts,dist,cust,meter,extra,fixed_eua,ceac,rea,ee,cgc,mapr,pbr,rba,edit):
    # Independent source transcription: exactly 600 kWh, below both winter
    # blocks and the first state-tax tier. Do not use production rate selectors.
    c=0 if plan=="DS-1" else 1;k=D(600);edt=D(".0012550" if year==2025 else ".0012567")
    base=D(cust[c])+D(meter[c])+k*(D(dist[c])+edt)
    expected={"customer":D(cust[c]),"meter":D(meter[c]),"supplemental_customer":D(extra[c]),
        "delivery_uncollectible":D(fixed_eua[c]),"distribution":k*D(dist[c]),"energy":k*D(energy[c]),
        "purchased_electricity_adjustment":k*D(pea),"supply_cost_adjustment":k*D(sca[c]),"supply_uncollectible":k*D(eua[c]),
        "transmission":k*D(ts[c]),"edt_cost_recovery":k*edt,"customer_generation":D(cgc[c]),
        "map_reconciliation":base*D(mapr),"pbr_reconciliation":base*D(pbr),"revenue_balancing":base*D(rba[c]),
        "deferred_income_tax":base*D(edit),"environmental":D(0),"hazardous_materials":D(0),
        "clean_energy":k*D(ceac),"renewable_energy":k*D(rea),"energy_efficiency":k*D(ee[c]),
        "utility_solar_storage":k*D(".000083" if year==2025 else ".000097"),
        "energy_transition":k*D(".00072" if year==2025 else ".00084"),
        "coal_solar_storage":k*D(".00008" if year==2025 or month=="2026-01" else ".00009"),
        "illinois_electricity_excise":k*D(".00330")}
    b=bill(plan,month,600.)
    assert b["unrounded_lines"]==pytest.approx({key:float(v) for key,v in expected.items()},abs=1e-8)
    assert b["unrounded_total_usd"]==pytest.approx(float(sum(expected.values())),abs=1e-7)
    assert b["is_complete_bill"] and b["rate_evidence_status"]=="verified"
    assert not b["metrics"]["measured_demand_charge"]
    assert not any("lmp" in k or "capacity" in k for k in b["lines"])


@pytest.mark.parametrize("plan,threshold,first,tail,supply_first,supply_tail",[
 ("DS-1",800.,.04376,.02324,.05508,.04924),
 ("DS-2",2000.,.03352,.01717,.06717,.06717)])
@pytest.mark.parametrize("offset",[-.01,0.,.01,600.])
def test_exact_filled_winter_blocks_and_tax(plan,threshold,first,tail,supply_first,supply_tail,offset):
    k=threshold+offset;b=bill(plan,"2025-01",k)
    assert b["unrounded_lines"]["distribution"]==pytest.approx(min(k,threshold)*first+max(k-threshold,0)*tail)
    assert b["unrounded_lines"]["energy"]==pytest.approx(min(k,800)*supply_first+max(k-800,0)*supply_tail if plan=="DS-1" else k*supply_first)
    assert b["unrounded_lines"]["illinois_electricity_excise"]==pytest.approx(min(k,2000)*.0033+max(k-2000,0)*.00319)


@pytest.mark.parametrize("month,pea,ts,ceac,csesc",[
 ("2025-05",-.00327,.02272,.00189,.00008),("2025-06",-.00086,.02264,.00177,.00008),
 ("2025-09",-.00142,.02264,.00183,.00008),("2025-10",.00303,.02264,.00183,.00007),
 ("2025-12",-.04996,.02264,.00183,.00007),("2026-06",-.00055,.02765,.00175,.00009),
 ("2026-09",-.002,.02765,.00071,.00009),("2026-10",-.00028,.02765,.00071,.00008)])
def test_monthly_supply_and_rider_boundaries(month,pea,ts,ceac,csesc):
    b=bill(month=month,kwh=100.)["unrounded_lines"]
    for key,value in [("purchased_electricity_adjustment",pea),("transmission",ts),("clean_energy",ceac),("coal_solar_storage",csesc)]:
        assert b[key]==pytest.approx(100*value)


@pytest.mark.parametrize("year",[2025,2026])
@pytest.mark.parametrize("month",range(1,13))
def test_finite_verified_month_coverage(year,month):
    key=f"{year}-{month:02d}"
    if year==2026 and month>10:
        with pytest.raises(ValueError,match="coverage"):ai.month_rates(key,"DS-1","II")
    else:
        b=bill(month=key,kwh=0.)
        assert b["total_usd"]>0
        assert b["unrounded_lines"]["customer_generation"]==(.16 if year==2025 else .31)


@pytest.mark.parametrize("month,hours",[("2025-03",743),("2025-11",721),("2026-03",743),("2026-09",720)])
def test_central_time_dst_no_missing_hours(month,hours):
    a,idx=fixture(month=month)
    b=calculate_cycle(ai.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert len(idx)==hours*4 and b["import_kwh"]==hours and b["metrics"]["elapsed_hours"]==hours
    with pytest.raises(ValueError,match="consecutive"):ai.validate_account(a,idx.delete(20))
    with pytest.raises(ValueError,match="Chicago"):ai.validate_account(a,idx.tz_convert("America/New_York"))


@pytest.mark.parametrize("zone,rate",[("I",-.0000467),("II",0.),("III",.0001061)])
def test_utility_rate_zone_is_not_miso_zone(zone,rate):
    b=bill(zone=zone,kwh=100.)
    assert b["unrounded_lines"]["environmental"]==pytest.approx(100*rate)
    assert b["lines"]["hazardous_materials"]==0.
    with pytest.raises(ValueError):ai.month_rates("2025-07","DS-1","LRZ4")


@pytest.mark.parametrize("key,value",[("eligibility_confirmed",False),("ordinary_service_confirmed",False),
    ("local_charges_confirmed",False),("ts_metering","interval"),("ts_metering_source",""),("rate_zone","LRZ4"),
    ("supply","rtp"),("export_mode","net_metering"),("opening_credit_usd",10.),("cycle_kind","initial"),
    ("bill_date","2025-08-01"),("full_monthly_charges_confirmed",False)])
def test_unsupported_account_is_rejected(key,value):
    a,idx=fixture();a[key]=value
    with pytest.raises(ValueError):ai.validate_account(a,idx)


def test_no_partial_crossing_or_export_and_ds2_eligibility_is_preserved():
    a,idx=fixture("DS-2")
    for grid in (idx[:-1],idx[96:],build_interval_index("2025-07-15","2025-08-14",ai.TIMEZONE,15).index):
        with pytest.raises(ValueError,match="complete calendar"):ai.validate_account(a,grid)
    with pytest.raises(ValueError,match="zero exports"):calculate_cycle(ai.UTILITY,idx,np.ones(len(idx)),np.ones(len(idx)),a)
    with pytest.raises(ValueError,match="150 kW"):calculate_cycle(ai.UTILITY,idx,np.full(len(idx),150.),np.zeros(len(idx)),a)
    equipment=dict(pv=True,battery=True,pv_dc_kw=10.,pv_ac_kw=8.,battery_kw=8.)
    ai.validate_account(a,idx,equipment)
    ref=grid_only_counterfactual(ai.UTILITY,a)
    assert not ref["account"]["dg_enrollment_confirmed"] and a["dg_enrollment_confirmed"]
    assert ref["account"]["rate_zone"]==a["rate_zone"]
    b=calculate_cycle(ai.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),ref["account"])
    assert b["lines"]["customer_generation"]==2.48
    with pytest.raises(ValueError,match="approved non-export"):ai.validate_account(ref["account"],idx,equipment)
    with pytest.raises(ValueError,match="50 kW"):ai.validate_account(a,idx,{**equipment,"battery_kw":45.})


def test_account_region_central_clock_and_existing_clocks():
    r=defaults(ai.UTILITY);region=r["regional_account"]
    assert r["timezone"]=="America/Chicago"
    assert region["state_jurisdiction"]=="IL" and region["grid_operator"]=="MISO"
    assert region["resource_adequacy_zone"]=="LRZ4" and region["transmission_owner"]=="Ameren Illinois"
    assert region["transmission_zone"] is None and region["wholesale_pricing_location"] is None
    account_region(region,ai.UTILITY)
    for key,val in [("grid_operator","PJM"),("resource_adequacy_zone","LRZ7"),("transmission_owner","METC")]:
        with pytest.raises(ValueError):account_region({**region,key:val},ai.UTILITY)
    with pytest.raises(ValueError,match="not a price node"):
        account_region({**region,"wholesale_pricing_location":dict(cpnode="LRZ4",node_type="zone",source="invalid zone")},ai.UTILITY)
    for utility in UTILITIES:
        expected=("America/Indiana/Indianapolis" if utility=="duke_energy_indiana" else
                  "America/Chicago" if utility in (ai.UTILITY,"ameren_missouri","xcel_energy_minnesota","we_energies_wisconsin","alliant_energy_iowa") else "America/New_York")
        assert defaults(utility)["timezone"]==expected
    assert capabilities()["utilities"][ai.UTILITY]["timezone"]=="America/Chicago"


@pytest.mark.parametrize("plan",ai.PLANS)
def test_dispatch_reconciliation_with_winter_declining_blocks(plan):
    a,idx=fixture(plan,"2025-01")
    pv=3.*np.maximum(0,np.sin((idx.hour.to_numpy()-6)*np.pi/12))
    inputs=pd.DataFrame(dict(timestamp=idx,native_load_kw=np.full(len(idx),2.),pv_available_kw=pv))
    battery=defaults(ai.UTILITY,"residential" if plan=="DS-1" else "commercial",plan)["battery"]
    out=optimize_cycle(inputs,ai.UTILITY,a,battery=battery,terminal_energy=battery["energy_kWh"],grid_charging=True,time_limit=30)
    assert out["cost_optimum_proven"] and out["reconciliation_difference_usd"]<.0001
    assert out["dispatch"].grid_export_kw.max()<1e-5
    assert out["bill"]["unrounded_total_usd"]==pytest.approx(sum(out["bill"]["unrounded_lines"].values()))


@pytest.mark.parametrize("plan",ai.PLANS)
def test_browser_form_worker_three_scenarios_save_restore_and_electrical(service,plan):
    app,call,headers=service
    r=defaults(ai.UTILITY,"residential" if plan=="DS-1" else "commercial",plan)
    r["operating_contract"].update(interconnection_confirmed=True,grid_charging_confirmed=True,reference="Hypothetical approved Ameren BGS non-export PV and storage")
    r=browser_request(r);prepare(r)
    assert r["timezone"]==ai.TIMEZONE
    study=call("/api/v1/regional/studies",r,headers);out=wait_for_study(call,study["id"])
    assert out["status"]=="completed",out.get("error")
    result=out["result"]
    assert set(result["billing"])=={"grid_only","pv_only","pv_battery"}
    assert result["ac_validation"]["all_intervals_feasible"]
    assert result["engine_id"]==app.engine["id"]
    assert all(b[0]["rate_evidence_status"]=="verified" for b in result["billing"].values())
    base="/api/studies/"+study["id"]
    assert b"customer_generation" in call(base+"/tables/billing-components.csv")
    assert b"scheduled_grid" in call(base+"/tables/ac-pv_battery.csv")
    assert len(call(base+"/tables.zip"))>0
    call(base+"/save",{"name":"Ameren "+plan+" acceptance"},headers)
    restored=call(base+"/request.json")
    assert browser_request(restored)["account"]==r["account"]
    assert restored["regional_account"]==r["regional_account"]


def test_source_integrity_and_reproducible_selection():
    from tools.run_regional_validation import selected_cases,case_request
    assert {row[2] for row in selected_cases([ai.UTILITY])}==set(ai.PLANS)
    for kind,p in [("residential","DS-1"),("commercial","DS-2")]:
        r=case_request(ai.UTILITY,kind,plan=p)
        assert len(r["billing_cycles"])==12 and r["timezone"]==ai.TIMEZONE
    manifest=json.loads(Path("docs/utility_sources/ameren_il/manifest.json").read_text())
    for source in manifest["sources"]:
        assert hashlib.sha256(Path(source["extracted_text"]).read_bytes()).hexdigest()==source["extracted_text_sha256"]


@pytest.mark.parametrize("kwh",[0.,1999.99,2000.,2000.01,49999.99,50000.,50000.01,100000.,100001.])
def test_full_state_excise_blocks_independent_numeric(kwh):
    # Standalone arithmetic tests may exceed this first tariff's DS-2 demand
    # eligibility. They verify the reusable exact block integral, not enrollment.
    from src.billing.regional_math import BillingMath
    _,idx=fixture()
    expected=min(kwh,2000)*.00330+min(max(kwh-2000,0),48000)*.00319+min(max(kwh-50000,0),50000)*.00303+max(kwh-100000,0)*.00297
    actual=ai.filled_blocks(kwh,[2000.,50000.,100000.],[.00330,.00319,.00303,.00297],BillingMath(idx),{})
    assert actual==pytest.approx(expected)


@pytest.mark.parametrize("kwh",[500.,800.,1200.])
def test_declining_block_fixed_schedule_milp_parity_and_tight_bounds(kwh):
    import cvxpy as cp
    from src.billing.regional_math import BillingMath
    _,idx=fixture();constraints=[]
    math=BillingMath(idx,convex=True,power_bound=5.,constraints=constraints)
    volume=math.register(cp.Variable(),0.,1500.);constraints.append(volume==kwh)
    cache={}
    expression=ai.filled_blocks(volume,[800.],[.10,.05],math,cache)
    expression+=ai.filled_blocks(volume,[2000.,50000.],[.0033,.00319,.00303],math,cache)
    problem=cp.Problem(cp.Minimize(expression),constraints);problem.solve(solver="SCIPY")
    assert problem.status=="optimal"
    assert problem.value==pytest.approx(min(kwh,800)*.10+max(kwh-800,0)*.05+kwh*.0033)
    # Both tax thresholds are beyond the proven 1,500-kWh upper bound.
    assert cache[2000.] is volume and cache[50000.] is volume
