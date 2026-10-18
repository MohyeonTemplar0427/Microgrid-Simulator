"""Independent filed arithmetic and physical/date contracts; no live requests."""
from copy import deepcopy
from decimal import Decimal as D
import io
import json

import numpy as np
import pandas as pd
import pytest

from src.billing.regional import calculate_cycle, cycle_account
from src.billing import firstenergy_pa as pa, firstenergy_oh as oh
from src.local_web.regional_study import defaults, prepare, calendar_cycles
from src.timeseries import build_interval_index
from test_local_web import service, wait_for_study
from test_regional_study import browser_request

PA, OH = pa.UTILITY, oh.UTILITY


def account(utility, plan, start, end):
    module = pa if utility == PA else oh
    a = module.hypothetical_defaults(plan)
    a.update(bill_date=end, billing_month=start[:8]+"01")
    idx = build_interval_index(start, end, "America/New_York", 15).index
    return a, idx


def bill_for_kwh(utility, plan, start, end, kwh, **changes):
    a, idx = account(utility, plan, start, end)
    a.update(changes)
    return calculate_cycle(utility, idx, np.full(len(idx), kwh/(len(idx)*.25)), np.zeros(len(idx)), a)


def test_pa_april_independent_tariff_arithmetic_includes_dsic_riders():
    # Manual1000-kWh benchmark from Supp14/15/16/18, PTC Supp11 and
    # original p241: DSIC includes nonbypassable distribution riders, not PTC.
    b = bill_for_kwh(PA, "RS", "2025-04-01", "2025-04-30", 1000)
    distribution = D("9")+D("43.06")+D("5.39")+D("1.61")-D(".04")+D("5.89")
    dsic = distribution*D(".0002")
    expected = (distribution+dsic+D("94.81"))*D("1.0001")
    assert b["unrounded_total_usd"] == pytest.approx(float(expected), abs=1e-8)
    assert b["unrounded_lines"]["distribution_dsic"] == pytest.approx(float(dsic))
    assert b["lines"]["sales_tax"] == 0


def test_pa_july_independent_commercial_benchmark_and_tax_order():
    a, idx = account(PA, "GS-M", "2025-07-01", "2025-07-31")
    a.update(history_billing_kw=[40.]*11, contract_demand_kw=12.)
    b = calculate_cycle(PA, idx, np.full(len(idx), 10.), np.zeros(len(idx)), a)
    #720h would be June; July has744h.50% of historical40kW beats
    # actual10kW and contract12kW. TCJA excludes rider revenues.
    kwh=D("7440")
    base=D("23.29")+kwh*D(".00531")+D("20")*D("3.46")
    subtotal=base*D(".9947")+kwh*(D(".10536")+D(".00407")+D(".002"))+D(".85")
    expected=subtotal*D("1.0001")*D("1.06")
    assert b["unrounded_total_usd"] == pytest.approx(float(expected), abs=1e-8)
    assert b["metrics"]["billing_demand_kw"] == 20.
    assert b["next_state"]["history_billing_kw"] == [40.]*10+[20.]


def test_january_refund_is_once_only_and_not_taxed_with_stas_again():
    a, idx = account(PA, "RS", "2025-01-01", "2025-01-31")
    p=np.ones(len(idx))
    first=calculate_cycle(PA,idx,p,p*0,a)
    second=calculate_cycle(PA,idx,p,p*0,a,state=first["next_state"])
    assert first["lines"]["january_refund"] == -4.45
    assert second["lines"]["january_refund"] == 0
    assert first["lines"]["state_tax_adjustment"] == second["lines"]["state_tax_adjustment"]
    assert second["total_usd"]-first["total_usd"] == pytest.approx(4.45)


@pytest.mark.parametrize("day,expected",[("2025-05-31",(.09481,.10013)),("2025-06-01",(.10317,.10536)),("2025-11-30",(.10317,.10536)),("2025-12-01",(.10947,.10993))])
def test_pa_filed_supply_dates_not_historical_workbook_june24(day,expected):
    assert pa.rates_on(day)["supply"] == expected


def test_pa_service_date_energy_and_bills_rendered_dsic_are_separate():
    a,idx=account(PA,"RS","2025-03-15","2025-04-14")
    b=calculate_cycle(PA,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert b["unrounded_lines"]["distribution_dsic"]>0  # all bill-rendered April
    a,idx=account(PA,"RS","2025-05-15","2025-06-14")
    b=calculate_cycle(PA,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    hours_before=int((idx.month==5).sum())*.25
    assert b["unrounded_lines"]["supply"] == pytest.approx(hours_before*.09481+(len(idx)*.25-hours_before)*.10317)


def test_pa_august_universal_service_transition_and_tcja_bill_date():
    a,idx=account(PA,"RS","2025-07-15","2025-08-14")
    b=calculate_cycle(PA,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert b["unrounded_lines"]["universal_service"] == pytest.approx(17*24*.00589+14*24*.0092)
    assert b["unrounded_lines"]["tcja"] == pytest.approx((9.+len(idx)*.25*.04306)*-.0053)


def test_ohio_october_independent_1000kwh_benchmark():
    b=bill_for_kwh(OH,"RS","2025-10-01","2025-10-31",1000)
    # Sheet10 + GEN, NMB, DCR + every nonzero ordinary rider, in dollars.
    per_kwh=sum(map(D,[".031898",".066966",".021953",".024468",".008770",
        ".000296","-.000001",".000247",".000841",".000048",".001000",
        ".000267",".000029","-.001725",".000462",".000476",".003545",".0028408"]))
    expected=D("4")+D("2.378")-D(".51")+D("1000")*per_kwh+D("4.65")/D(".9974")
    assert b["unrounded_total_usd"] == pytest.approx(float(expected), abs=1e-8)
    assert not any(k in b["lines"] for k in ("rdc","bdc","wholesale_lmp","plc"))


def test_ohio_gs_thirty_minute_demand_and_contract_floor():
    a,idx=account(OH,"GS","2025-10-01","2025-10-31")
    p=np.full(len(idx),2.);p[0]=18.
    b=calculate_cycle(OH,idx,p,p*0,a)
    assert b["metrics"]["measured_demand_kw"] == 10.
    assert b["metrics"]["billing_demand_kw"] == 10.
    assert b["unrounded_lines"]["distribution_demand"] == pytest.approx(12.8+5*5.4635)
    assert b["unrounded_lines"]["non_market_transmission"] == pytest.approx(10*7.1203)
    a["contract_demand_kw"]=15.
    assert calculate_cycle(OH,idx,p,p*0,a)["metrics"]["billing_demand_kw"] == 15.


@pytest.mark.parametrize("kwh",[1999.,2000.,2001.,14999.,15000.,15001.])
def test_ohio_kwh_tax_blocks_and_cat_not_sales_tax(kwh):
    b=bill_for_kwh(OH,"RS","2025-10-01","2025-10-31",kwh)
    tax=(min(kwh,2000)*.00465+max(0,min(kwh-2000,13000))*.00419+max(0,kwh-15000)*.00363)/.9974
    assert b["unrounded_lines"]["state_kwh_tax"] == pytest.approx(tax)


@pytest.mark.parametrize("utility,plan,month,hours",[(PA,"RS",3,743),(PA,"GS-M",11,721),(OH,"GS",11,721)])
def test_dst_billing_uses_physical_hours_and_complete_demand_blocks(utility,plan,month,hours):
    start=f"2025-{month:02d}-01";end=(pd.Timestamp(start)+pd.offsets.MonthEnd()).date().isoformat()
    b=bill_for_kwh(utility,plan,start,end,hours)
    assert b["import_kwh"] == hours
    if plan!="RS":assert b["metrics"]["measured_demand_kw"]==1.


@pytest.mark.parametrize("utility,kind,bounds",[(PA,"residential",None),(PA,"commercial",None),
    (OH,"residential",None),(OH,"commercial",None),
    (OH,"residential",("2025-01-01","2025-01-31")),
    (OH,"commercial",("2025-06-01","2025-06-30")),
    (OH,"residential",("2025-08-14","2025-09-13")),
    (OH,"commercial",("2025-08-14","2025-09-13"))])
def test_firstenergy_form_to_worker_saved_artifacts_and_restore(service,utility,kind,bounds):
    app,call,headers=service
    r=defaults(utility,kind)
    if bounds:
        start,end=bounds
        r.update(start_date=start,end_date=end)
        # One complete hypothetical meter cycle, even when it crosses a month.
        cycle=calendar_cycles(start,start)[0]
        cycle.update(end_date=end,bill_date=end,billing_month=end[:8]+"01",kind="regular",
                     source="Explicit hypothetical complete regular meter cycle, not an actual customer bill")
        r["billing_cycles"]=[cycle]
        r["account"].update(bill_date=end,billing_month=cycle["billing_month"])
    r["operating_contract"].update(interconnection_confirmed=True,reference="Explicit hypothetical approved ordinary renewable account")
    r=browser_request(r)
    study=call("/api/v1/regional/studies",r,headers)
    out=wait_for_study(call,study["id"])
    assert out["status"]=="completed",out.get("error")
    result=out["result"]
    assert result["engine_id"]==app.engine["id"]
    assert set(result["billing"])=={"grid_only","pv_only","pv_battery"}
    assert all(x["checked_intervals"]==len(prepare(r)[0].index) for x in result["ac_validation"]["scenarios"])
    assert result["ac_validation"]["all_intervals_feasible"]
    base="/api/studies/"+study["id"]
    table=call(base+"/tables/comparison")
    rows=[dict(zip(table["columns"],x)) for x in table["data"]]
    assert all(x["is_complete_bill"] and x["maximum_reconciliation_difference_usd"]<.0001 for x in rows)
    data=call(base+"/tables/dispatch-pv_battery.csv").decode()
    frame=pd.read_csv(io.StringIO(data))
    assert frame.grid_export_kw.abs().max()<1e-6
    assert (frame.battery_charge_kw<=frame.pv_output_kw+1e-5).all()
    assert len(call(base+"/tables.zip"))>0
    call(base+"/save",{"name":utility+" review"},headers)
    restored=call(base+"/request.json")
    assert call(base)["saved"] and browser_request(restored)["account"]==r["account"]


@pytest.mark.parametrize("utility",[PA,OH])
def test_firstenergy_rejects_unverified_equipment_accounts_exports_and_partial_cycles(utility):
    r=defaults(utility);r["operating_contract"].update(interconnection_confirmed=True,reference="hypothetical")
    r["account"]["der_ordinary_service_confirmed"]=False
    with pytest.raises(ValueError,match="ordinary|Partial"):prepare(r)
    r["account"]["der_ordinary_service_confirmed"]=True
    r["operating_contract"]["grid_charging_confirmed"]=True
    with pytest.raises(ValueError,match="PV-only"):prepare(r)
    r["operating_contract"]["grid_charging_confirmed"]=False
    r["end_date"]=r["start_date"][:8]+"02";r["billing_cycles"]=calendar_cycles(r["start_date"],r["end_date"])
    with pytest.raises(ValueError,match="25–35"):prepare(r)


@pytest.mark.parametrize("utility,day",[(PA,"2024-12-31"),(PA,"2026-01-01"),
    (OH,"2025-02-01"),(OH,"2025-03-01"),(OH,"2025-05-31"),
    (OH,"2025-07-01"),(OH,"2025-08-13"),(OH,"2026-01-01")])
def test_gaps_and_outside_coverage_never_use_nearest_rate(utility,day):
    with pytest.raises(ValueError,match="coverage"):(pa if utility==PA else oh).rates_on(day)


def test_ohio_crossing_fixed_or_demand_rate_change_requires_sourced_allocation():
    a,idx=account(OH,"GS","2025-09-15","2025-10-14")
    with pytest.raises(ValueError,match="allocation"):
        calculate_cycle(OH,idx,np.ones(len(idx)),np.zeros(len(idx)),a)


def test_driver_keeps_full_ohio_year_blocked_and_pa_full_year_executable():
    from tools.run_regional_validation import case_request, selected_cases
    r=case_request(PA,"commercial","annual",plan="GS-M")
    assert len(prepare(r)[0].index)==35040
    assert len(r["billing_cycles"])==12
    assert r["operating_contract"]["renewable_only_charging"]
    with pytest.raises(ValueError,match="coverage"):
        case_request(OH,"residential","annual",plan="RS")
    assert len(selected_cases([PA,OH]))==4


@pytest.mark.parametrize("plan",["RS","GS"])
def test_ohio_january_esp_v_independent_benchmark(plan):
    a,idx=account(OH,plan,"2025-01-01","2025-01-31")
    a["contract_demand_kw"]=10.
    b=calculate_cycle(OH,idx,np.full(len(idx),1000/(len(idx)*.25)),np.zeros(len(idx)),a)
    rs=plan=="RS"; kwh=D("1000"); demand=D("10")
    base=D("4")+kwh*D(".031898") if rs else D("7")+D("12.80")+D("5")*D("5.4635")
    # Sheet124 uses percent of base distribution, excluding every rider.
    dcr=base*D(".351979" if rs else ".285339")
    common=sum(map(D,[".073408","-.000167",".000409",".003073",".000030",".000483",".000027",".000436",".0028408"]))
    rates=common+sum(map(D,[".003080",".000006",".001044","-.001725",".003541",".021982",".000047"])) if rs else common+sum(map(D,[".002908",".000005",".003982","-.001028","-.000298",".0018007",".00029051"]))
    fixed=D("2.141")-D(".51")+D("1.50")+D(".10") if rs else D("9.118")+demand*(D("6.2252")+D(".0087"))
    expected=base+dcr+kwh*rates+fixed+D("4.65")/D(".9974")
    assert b["unrounded_total_usd"]==pytest.approx(float(expected),abs=1e-8)
    assert b["unrounded_lines"]["delivery_capital"]==pytest.approx(float(dcr))
    assert b["unrounded_lines"]["demand_side_efficiency"]==0
    assert b["unrounded_lines"]["vegetation_management"]==pytest.approx(.047 if rs else .087)


@pytest.mark.parametrize("plan",["RS","GS"])
def test_ohio_june_esp_iv_summer_independent_benchmark(plan):
    a,idx=account(OH,plan,"2025-06-01","2025-06-30")
    a["contract_demand_kw"]=10.
    b=calculate_cycle(OH,idx,np.full(len(idx),1000/(len(idx)*.25)),np.zeros(len(idx)),a)
    rs=plan=="RS"; kwh=D("1000"); demand=D("10")
    base=D("4")+kwh*D(".031898") if rs else D("7")+D("12.80")+D("5")*D("5.4635")
    rates=sum(map(D,[".073661",".000207",".000920","-.002909",".000009",".000549",".000024",".001151",".000436",".0028408"]))
    rates+=sum(map(D,[".021953",".000006",".000262","-.001725",".003541",".023602",".009032"])) if rs else sum(map(D,[".021732",".000004",".003090","-.001028","-.000298",".0018007",".00029051"]))
    fixed=D("2.332")-D(".51")+D("1.50")+D(".10") if rs else D("9.081")+demand*(D("6.3482")+D("3.3606"))
    assert b["unrounded_total_usd"]==pytest.approx(float(base+kwh*rates+fixed+D("4.65")/D(".9974")),abs=1e-8)
    assert b["unrounded_lines"]["supply_energy"]==pytest.approx(73.661)
    assert "vegetation_management" not in b["lines"]


def test_ohio_source_gaps_are_visible_and_esp_vi_proposals_not_applied():
    row=oh.catalog()[0]
    assert row["coverage"]==[{"start":start,"end":end} for start,end in oh.COMPLETE_COVERAGE]
    assert row["esp_transition"]["effective_date"]=="2025-02-01"
    assert row["esp_transition"]["current"]=="ESP IV"
    assert row["coverage_gaps"]==oh.GAPS
    assert oh.rates_on("2025-01-31")["dcr_basis"]=="base_distribution"
    assert oh.rates_on("2025-06-01")["dcr_basis"]=="energy_or_demand"
    for gap in row["coverage_gaps"]:
        with pytest.raises(ValueError,match="No rate extrapolation"):
            oh.rates_on(gap["start"])


@pytest.mark.parametrize("plan",["RS","GS"])
def test_ohio_august14_cycle_independent_benchmark_crosses_season_not_lgr(plan):
    a,idx=account(OH,plan,"2025-08-14","2025-09-13")
    a["contract_demand_kw"]=10.
    b=calculate_cycle(OH,idx,np.full(len(idx),1000/(len(idx)*.25)),np.zeros(len(idx)),a)
    rs=plan=="RS"; kwh=D("1000"); demand=D("10")
    base=D("4")+kwh*D(".031898") if rs else D("7")+D("12.80")+D("5")*D("5.4635")
    # GEN19:18 summer service days and13 winter service days. DCR53 applies
    # to August bills, but this September bill uses DCR54 on the whole cycle.
    generation=kwh*(D("18")*D(".073661")+D("13")*D(".066966"))/D("31")
    rates=sum(map(D,[".000175",".000888","-.001206",".000015",".000709",".000026",".000462",".000476",".0028408"]))
    rates+=sum(map(D,[".021953",".000002",".000190","-.001725",".003545",".023602",".008770"])) if rs else sum(map(D,[".021732",".000001",".001213","-.001028","-.000298"]))
    fixed=D("1.514")-D(".51") if rs else D("5.450")+demand*(D("6.3482")+D("3.2527"))
    expected=base+generation+kwh*rates+fixed+D("4.65")/D(".9974")
    assert b["unrounded_total_usd"]==pytest.approx(float(expected),abs=1e-8)
    assert b["unrounded_lines"]["supply_energy"]==pytest.approx(float(generation))
    assert b["lines"]["legacy_generation"]==b["lines"]["solar_generation_fund"]==0
    assert oh.rates_on("2025-08-14")["supply_energy"]==.073661
    assert oh.rates_on("2025-08-31")["dcr"]==(.009032,3.3606)
    assert oh.rates_on("2025-09-01")["dcr"]==(.008770,3.2527)


@pytest.mark.parametrize("plan",["RS","GS"])
def test_ohio_august_calendar_cycle_and_removal_crossing_still_reject(plan):
    # The zero rate fromAugust14 must never erase the unverified earlier days.
    for start,end in (("2025-08-01","2025-08-31"),("2025-08-13","2025-09-12")):
        with pytest.raises(ValueError,match="LGR Sheet135 revision12"):
            bill_for_kwh(OH,plan,start,end,1000)
