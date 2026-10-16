"""Offline filed arithmetic, account boundaries, revisions and credit banks."""
from copy import deepcopy
import io

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import pseg
from src.billing.regional_math import BillingMath


def grid(start="2025-07-01", end="2025-08-01", minutes=15):
    return pd.date_range(start,end,freq=f"{minutes}min",inclusive="left",tz=pseg.TIMEZONE)


def account(plan="RS",year=2025,**changes):
    return {**pseg.hypothetical_defaults(plan,year),**changes}


def prices(index,value=33.278903,**changes):
    hours=index.tz_convert("UTC").floor("h").unique()
    df=pd.DataFrame({"datetime_beginning_utc":hours.strftime("%Y-%m-%d %H:%M:%S"),
        "pnode_id":116472957,"pnode_name":"PSEG_RESID_AGG","zone":"","type":"RESIDUAL_METERED_EDC",
        "total_lmp_rt":value,"version_nbr":1,"row_is_current":True})
    df=df.assign(**changes)
    return {"csv_text":df.to_csv(index=False),"metadata":{"market":"REAL_TIME_HOURLY",
        "source_url":"https://dataminer2.pjm.com/feed/rt_hrl_lmps","retrieved_at":"2026-10-15T00:00:00Z",
        "unit":"$/MWh","usage_permission":"internal_use_only"}}


def calculate(idx,a,power=1.,exports=0.,state=None):
    return pseg.bill(idx,np.broadcast_to(power,(len(idx),)),np.broadcast_to(exports,(len(idx),)),a,state)


def test_january_residential_independent_filed_benchmark():
    idx=grid("2025-01-01","2025-02-01")
    a=account(billing_month="2025-01-01",bill_date="2025-01-31")
    result=calculate(idx,a)
    # Original sheets93/57/60/61/64/65/66/69/75/76, Jan2025 GPRC,
    # Dec2024 quarterly reconciliation. All listed rates already include SUT.
    rate=.047773+.009911+.000026+.004265+.000061+.006599+.001546-.007763+.093408+.060444-.004790
    assert result["total_usd"]==pytest.approx(6+744*rate,abs=1e-9)
    assert result["metrics"]["sales_use_tax_included"]
    assert result["lines"]["covid"]==0
    assert result["lines"]["generation_capacity_deferral"]==0


def test_high_tension_customer_charges_preserve_official_thousands_separators():
    # Official sheets155/156, all retained2025/26books, including SUT:
    # $2,038.02 SUB and $1,834.22 HV; neither is a cents-only suffix.
    for book in pseg.DATA["ratebooks"]:
        assert book["rates"]["delivery"]["HTS_SUB"]["customer"]==2038.02
        assert book["rates"]["delivery"]["HTS_HV"]["customer"]==1834.22
    for plan,expected in (("HTS_SUB",2038.02),("HTS_HV",1834.22)):
        idx=grid();a=account(plan,market_data=prices(idx))
        assert calculate(idx,a,1.)["lines"]["customer"]==expected


def test_offline_source_compiler_preserves_grouping_and_matches_all_retained_books():
    from tools.compile_pseg_rates import values,compile_ratebooks
    assert values("$1,911.39 [$2,038.02 including SUT]")==[1911.39,2038.02]
    assert values("$1,720.25 [$1,834.22 including SUT]")==[1720.25,1834.22]
    assert values("$(0.002413)")==[-.002413]
    assert compile_ratebooks()==pseg.DATA["ratebooks"]


@pytest.mark.parametrize("plan",["RS","GLP"])
def test_nonexport_never_discards_carried_net_metering_credits(plan):
    idx=grid();a=account(plan)
    with pytest.raises(ValueError,match="cannot enter non-export"):
        calculate(idx,a,state={"credit_kwh":{"all":100.},"history_peaks_kw":[40.]*11})
    assert calculate(idx,a,state={"credit_kwh":{"all":0.},"history_peaks_kw":[40.]*11})["next_state"]["credit_kwh"]=={}


def test_july_residential_independent_filed_benchmark_and_deferral():
    result=calculate(grid(),account())
    distribution=600*.082602+144*.086677
    supply=600*.131800+144*.141148
    other=744*(.009822+.000026+0+.000002+.008049+.000518-.007763-.000229+.065877+.005408)
    assert result["lines"]["distribution_energy"]==pytest.approx(distribution)
    assert result["total_usd"]==pytest.approx(6+distribution+supply+other-30,abs=1e-9)
    assert result["total_usd"]==pytest.approx(198.24024)


def test_glp_independent_benchmark_keeps_two_obligations_separate():
    idx=grid();a=account("GLP");result=calculate(idx,a,20.)
    kwh=14880.
    expected=7.93+20*(4.7173+16.2326+.8783)+kwh*(.016928+.009822+.000026+.000002+.008049+.000518-.002373+.005408+.087713)+15*8.7679+16*14.4285
    assert result["total_usd"]==pytest.approx(expected,abs=1e-8)
    b=deepcopy(a);b["generation_obligation_kw"]+=1
    assert calculate(idx,b,20.)["total_usd"]-result["total_usd"]==pytest.approx(8.7679)
    assert result["next_state"]["history_peaks_kw"]==[40.]*10+[20.]


@pytest.mark.parametrize("plan",sorted(pseg.PLANS-{"LPL_P","HTS_SUB","HTS_HV"}))
@pytest.mark.parametrize("year",[2025,2026])
def test_all_verified_rscp_structures_current_and_historical(plan,year):
    month=12 if plan=="RS_TOU_3P" and year==2025 else 7
    start=f"{year}-{month:02}-01";end=f"{year+1}-01-01" if month==12 else f"{year}-08-01"
    a=account(plan,year,billing_month=start,bill_date=f"{year}-{month:02}-31")
    result=calculate(grid(start,end),a,5.)
    assert np.isfinite(result["total_usd"])
    assert result["is_complete_bill"]
    assert result["metrics"]["source"]["sha256"]


def test_rate_gap_inception_and_tax_exemption_reject():
    for value in ["2024-12-31","2026-10-16","2030-01-01"]:
        with pytest.raises(ValueError,match="coverage"):
            pseg.version_on(value)
    with pytest.raises(ValueError,match="December 8"):
        calculate(grid(),account("RS_TOU_3P"))
    with pytest.raises(ValueError,match="taxable"):
        calculate(grid(),account(tax_exempt=True))


@pytest.mark.parametrize("plan",["RHS","RLM","HS"])
def test_legacy_enrollment_is_not_offered_as_open_plan(plan):
    with pytest.raises(ValueError,match="closed"):
        calculate(grid(),account(plan,legacy_enrollment_confirmed=False))
    entry=next(x for x in pseg.catalog() if x["id"]==plan)
    assert entry["closed_to_new_accounts"]


def test_billing_date_not_service_date_selects_independent_riders():
    # One actual cycle crosses the June base/supply/rider change. Rule9.10
    # selects the first regular bill issued on/after June1; no daily blending.
    idx=grid("2025-05-15","2025-06-15")
    a=account(billing_month="2025-06-01",bill_date="2025-06-14")
    b=calculate(idx,a)
    assert "20250601" in b["metrics"]["rate_version"]
    assert b["lines"]["zero_emission"]==0
    assert b["lines"]["green_programs"]==pytest.approx(744*.008049)
    assert b["metrics"]["monthly_charge_factor"]==1


def test_partial_initial_cycle_documented_month_day_proration():
    idx=grid("2025-07-01","2025-07-11")
    with pytest.raises(ValueError,match="proration"):
        calculate(idx,account(cycle_kind="initial"))
    b=calculate(idx,account(cycle_kind="initial",bill_date="2025-07-10",proration_denominator_days=31))
    assert b["lines"]["customer"]==pytest.approx(6*10/31)
    assert b["lines"]["generation_capacity_deferral"]==pytest.approx(-30*10/31)
    assert b["lines"]["distribution_energy"]==pytest.approx((600*10/31)*.082602+(240-600*10/31)*.086677)
    assert b["is_complete_bill"] is False
    assert b["metrics"]["residential_tier_block_interpretation"] is True
    assert any("tier-block allocation" in text for text in b["warnings"])


def test_partial_residential_confirmed_block_is_independent_from_charge_proration():
    idx=grid("2025-07-01","2025-07-11")
    a=account(cycle_kind="initial",bill_date="2025-07-10",proration_denominator_days=31,
        residential_tier_block_factor=1.,residential_tier_block_confirmed=True,
        residential_tier_block_source="Explicit synthetic fixture: utility-confirmed full600kWh block")
    b=calculate(idx,a)
    assert b["is_complete_bill"] is True
    assert b["metrics"]["residential_tier_block_interpretation"] is False
    assert b["lines"]["customer"]==pytest.approx(6*10/31)
    assert b["lines"]["distribution_energy"]==pytest.approx(240*.082602)
    a["residential_tier_block_source"]=""
    with pytest.raises(ValueError,match="utility-confirmed allocation"):
        calculate(idx,a)


def test_full_calendar_residential_bill_needs_no_partial_block_interpretation():
    b=calculate(grid(),account())
    assert b["is_complete_bill"] is True
    assert b["metrics"]["residential_tier_block_factor"]==1
    assert not b["metrics"]["residential_tier_block_interpretation"]


@pytest.mark.parametrize("start,end,count",[("2025-03-01","2025-04-01",2972),("2025-11-01","2025-12-01",2884)])
def test_dst_bills_count_physical_intervals(start,end,count):
    idx=grid(start,end);a=account(billing_month=start,bill_date=str((pd.Timestamp(end)-pd.Timedelta(days=1)).date()))
    b=calculate(idx,a)
    assert len(idx)==count
    assert b["metrics"]["import_kwh"]==count*.25


def test_tou_boundaries_and_distinct_holiday_calendars():
    idx=pd.DatetimeIndex(["2026-01-19T16:00:00-05:00","2026-01-20T15:45:00-05:00","2026-01-20T16:00:00-05:00","2026-01-20T21:00:00-05:00"]).tz_convert(pseg.TIMEZONE)
    assert pseg.periods(idx,"RS_TOU_3P")["on_peak"].tolist()==[False,False,True,False]
    # LPL weekday periods have no holiday exception; RLM explicitly uses EST.
    assert pseg.periods(idx,"LPL_S")["on_peak"].tolist()==[True,True,True,True]
    summer=pd.DatetimeIndex(["2025-07-07T07:30:00-04:00","2025-07-07T08:00:00-04:00"]).tz_convert(pseg.TIMEZONE)
    assert pseg.periods(summer,"RLM")["on_peak"].tolist()==[False,True]


def test_glp_half_hour_averaging_demand_and_night_use():
    idx=grid();p=np.ones(len(idx))*2
    p[(idx.day==2)&(idx.hour==22)&(idx.minute==0)]=10
    b=calculate(idx,account("GLP"),p)
    assert b["metrics"]["monthly_peak_kw"]==6
    night=calculate(idx,account("GLP_NIGHT"),p)
    assert night["metrics"]["monthly_peak_kw"]==6
    assert night["metrics"]["summer_peak_kw"]==2


def test_self_generator_uses_ratchet_and_actual_system_peak_hour():
    idx=grid();a=account("GLP",self_generation_standby=True,system_peak_source="Synthetic monthly peak fixture")
    with pytest.raises(ValueError,match="peak hour"):
        calculate(idx,a,10.)
    a["system_peak_hour"]="2025-07-08T17:00:00-04:00"
    b=calculate(idx,a,10.)
    assert b["metrics"]["monthly_peak_kw"]==10
    assert b["metrics"]["annual_peak_kw"]==40
    assert b["metrics"]["summer_peak_kw"]==10
    assert b["lines"]["distribution_annual_demand"]==pytest.approx(40*4.7173)


def test_estimated_glp_and_ordinary_class_thresholds():
    a=account("GLP",demand_metering="estimated",estimated_demand_enrollment_confirmed=True,history_peaks_kw=[5.]*11)
    b=calculate(grid(),a,1.)
    assert b["metrics"]["monthly_peak_kw"]==7.44
    assert b["metrics"]["summer_peak_kw"]==7.44
    with pytest.raises(ValueError,match="1,000"):
        calculate(grid(),a,2.)
    with pytest.raises(ValueError,match="150"):
        calculate(grid(),account("GLP"),151.)
    with pytest.raises(ValueError,match="500"):
        calculate(grid(),account("LPL_S",peak_load_share_kw=500.))


def test_net_metering_carryover_does_not_reduce_demand_measurement():
    a=account("GLP",export_mode="net_metering",net_metering_confirmed=True,net_metering_size_confirmed=True,
              opening_credit_kwh={"all":1000.})
    b=calculate(grid(),a,1.)
    assert b["metrics"]["billed_kwh"]==0
    assert b["metrics"]["monthly_peak_kw"]==1
    assert b["next_state"]["credit_kwh"]["all"]==256
    assert b["lines"]["supply_capacity"]>0
    assert b["lines"]["supply_transmission"]>0


def test_separate_tou_banks_and_explicit_payout_dependency():
    idx=grid("2026-07-01","2026-08-01");a=account("RS_TOU_3P",2026,export_mode="net_metering",net_metering_confirmed=True,net_metering_size_confirmed=True)
    masks=pseg.periods(idx,"RS_TOU_3P")
    imp=np.zeros(len(idx));exp=np.zeros(len(idx));imp[masks["on_peak"]]=1;exp[masks["off_peak"]]=2
    b=pseg.bill(idx,imp,exp,a)
    assert b["metrics"]["billed_kwh"]==masks["on_peak"].sum()*.25
    assert b["next_state"]["credit_kwh"]["off_peak"]==masks["off_peak"].sum()*.5
    a["anniversary_true_up"]=True
    with pytest.raises(ValueError,match="avoided-wholesale"):
        pseg.bill(idx,imp,exp,a)
    a["true_up_rate"]={"usd_per_kwh":.04,"source":"Synthetic utility payout fixture only","effective_start":"2026-07-01","effective_end":"2026-07-31","customer_class":"residential","voltage":"secondary"}
    paid=pseg.bill(idx,imp,exp,a)
    assert paid["lines"]["net_metering_annual_payout"]==-b["next_state"]["credit_kwh"]["off_peak"]*.04
    assert sum(paid["next_state"]["credit_kwh"].values())==0


@pytest.mark.parametrize("plan",["GLP","LPL_S","LPL_P","HTS_SUB","HTS_HV"])
def test_ciep_correct_residual_import_and_independent_supply_obligations(plan):
    idx=grid();a=account(plan,supply="bgs_ciep",obligation_enrollment_confirmed=True)
    with pytest.raises(ValueError,match="market_data"):
        calculate(idx,a,10.)
    a["market_data"]=prices(idx)
    b=calculate(idx,a,10.)
    assert b["metrics"]["market_provenance"]["pricing_location"]["pnode_id"]=="116472957"
    assert b["lines"]["supply_hourly_energy"]>0
    assert b["lines"]["supply_ancillary"]>0
    assert b["lines"]["supply_capacity"]>0
    assert b["lines"]["supply_transmission"]>0
    assert b["metrics"]["market_provenance"]["public_download_allowed"] is False


def test_ciep_official_worksheet_arithmetic_and_revision_selection():
    idx=grid("2025-01-01","2025-02-01");a=account("LPL_S",supply="bgs_ciep",obligation_enrollment_confirmed=True,billing_month="2025-01-01",bill_date="2025-01-31",**pseg.hypothetical_obligation_overrides("LPL_S","2025-01-01"))
    a["market_data"]=prices(idx)
    book,_=pseg.version_on("2025-01-31")
    hourly,ancillary,factor,_=pseg._ciep_prices(idx,a,book["rates"]["ciep"])
    assert factor==pytest.approx((1-.007969)/(1-.058327))
    assert (hourly[0]+ancillary)*30==pytest.approx(1.32366,abs=1e-8)
    text=a["market_data"]["csv_text"];df=pd.read_csv(io.StringIO(text));old=df.iloc[[0]].copy();old["row_is_current"]=False;old["total_lmp_rt"]=999.;old["version_nbr"]=1
    df["version_nbr"]=2;a["market_data"]["csv_text"]=pd.concat([old,df]).to_csv(index=False)
    _,_,_,provenance=pseg._ciep_prices(idx,a,book["rates"]["ciep"])
    assert provenance["revision_numbers"]==[2]


def test_equal_winter_residential_blocks_are_linear_without_tier_selectors(monkeypatch):
    idx=grid("2025-04-01","2025-05-01")
    a=account(billing_month="2025-04-01",bill_date="2025-04-30")
    math=BillingMath(idx)
    def unnecessary(*args,**kwargs):
        raise AssertionError("Equal rates must not create a tier selection graph")
    monkeypatch.setattr(math,"tiered",unnecessary)
    b=pseg.charge_lines(idx,np.ones(len(idx)),np.zeros(len(idx)),a,math=math)
    assert b["lines"]["distribution_energy"]==pytest.approx(720*.047773)
    assert b["lines"]["supply_energy_capacity"]==pytest.approx(720*.093408)


@pytest.mark.parametrize("lmp,expected",[(.0005,.000001),(-.0005,-.000001)])
def test_ciep_excel_six_decimal_half_ties_round_away_from_zero(lmp,expected):
    idx=grid();a=account("LPL_P",market_data=prices(idx,value=lmp))
    rates=pseg.version_on(a["bill_date"])[0]["rates"]["ciep"]
    hourly,_,_,_=pseg._ciep_prices(idx,a,rates)
    # $0.0005/MWh is exactly $0.0000005/kWh before the worksheet's
    # ROUND(...,6). Excel rounds that midpoint away from zero, not to even.
    assert np.all(hourly==expected)


@pytest.mark.parametrize("changes",[{"pnode_id":51288,"pnode_name":"WESTERN HUB"},{"type":"ZONE"},{"pnode_id":116472935,"pnode_name":"COMED_RESID_AGG"}])
def test_ciep_wrong_location_or_type_reject(changes):
    idx=grid();a=account("LPL_P",market_data=prices(idx,**changes))
    with pytest.raises(ValueError):
        calculate(idx,a,10.)


def test_no_export_and_complete_supply_validation():
    idx=grid()
    with pytest.raises(ValueError,match="curtail"):
        calculate(idx,account(),0.,1.)
    with pytest.raises(ValueError,match="Third-party"):
        calculate(idx,account(supply="third_party"))
    with pytest.raises(ValueError,match="obligation"):
        calculate(idx,account("GLP",transmission_obligation_kw=None),5.)


@pytest.mark.parametrize("plan",["RS","RHS","RLM","GLP","GLP_NIGHT","LPL_S"])
def test_same_math_optimizer_reconciles_without_new_tariff_arithmetic(plan):
    idx=grid("2025-07-01","2025-07-03");a=account(plan,cycle_kind="initial",proration_denominator_days=31,bill_date="2025-07-02")
    native=np.full(len(idx),3.);native[(idx.hour>=17)&(idx.hour<21)]=6.
    p=cp.Variable(len(idx));constraints=[p>=0,p<=10,cp.sum(p)==native.sum()]
    math=BillingMath(idx,convex=True,power_bound=10,constraints=constraints);math.register(p,0,10)
    exports=cp.Constant(np.zeros(len(idx)))
    result=pseg.charge_lines(idx,p,exports,a,math=math)
    problem=cp.Problem(cp.Minimize(sum(result["lines"].values())),math.constraints)
    problem.solve(solver="SCIPY")
    assert problem.status=="optimal"
    numeric=pseg.bill(idx,np.maximum(p.value,0),np.zeros(len(idx)),a)
    assert problem.value==pytest.approx(numeric["total_usd"],abs=1e-5)


def test_inputs_and_state_are_not_mutated():
    idx=grid();a=account("GLP");state={"history_peaks_kw":[30.]*11,"credit_kwh":{}}
    before=(deepcopy(a),deepcopy(state));calculate(idx,a,10.,state=state)
    assert (a,state)==before


def test_objective_policy_removes_only_inherited_credits():
    a=account("GLP",opening_credit_kwh={"all":50.})
    s={"credit_kwh":{"all":80.},"history_peaks_kw":[30.]*11}
    aa,ss=pseg.objective_inputs(a,s)
    assert aa["opening_credit_kwh"]=={"all":0.}
    assert ss["credit_kwh"]=={"all":0.}
    assert ss["history_peaks_kw"]==s["history_peaks_kw"]
    assert aa["generation_obligation_kw"]==a["generation_obligation_kw"]
    assert a["opening_credit_kwh"]["all"]==50.
    assert pseg.objective_inputs(a,s,"explicit_cash_bill")== (a,s)


def test_anniversary_without_payout_enforces_zero_bank_in_optimizer():
    idx=grid("2025-07-01","2025-07-03")
    a=account(export_mode="net_metering",net_metering_confirmed=True,net_metering_size_confirmed=True,
              anniversary_true_up=True,cycle_kind="initial",proration_denominator_days=31,bill_date="2025-07-02")
    imp=cp.Variable(len(idx));exp=cp.Variable(len(idx));constraints=[imp>=0,imp<=2,exp>=0,exp<=2,imp==1,exp==0]
    m=BillingMath(idx,convex=True,power_bound=2,constraints=constraints);m.register(imp,0,2);m.register(exp,0,2)
    r=pseg.charge_lines(idx,imp,exp,a,math=m)
    problem=cp.Problem(cp.Minimize(sum(r["lines"].values())),m.constraints)
    problem.solve(solver="SCIPY")
    assert problem.status=="optimal"
    assert r["next_state"]["credit_kwh"]=={"all":0.}
    assert any("constrained to zero" in s for s in r["warnings"])
    assert pseg.bill(idx,imp.value,exp.value,a)["lines"]["net_metering_annual_payout"]==0


def test_current_zero_bill_minimum_and_separate_deferral_credit():
    assert calculate(grid(),account(),0.)["total_usd"]==-24.
    idx=grid("2026-07-01","2026-08-01")
    assert calculate(idx,account(year=2026),0.)["total_usd"]==6.


def test_known_der_rating_requires_appropriate_account_classification():
    idx=grid();a=account("GLP")
    pseg.validate_account(a,idx,equipment={"pv":True,"battery":True,"pv_ac_kw":8.,"battery_kw":5.})
    with pytest.raises(ValueError,match="50%"):
        pseg.validate_account(a,idx,equipment={"pv":True,"battery":True,"pv_ac_kw":15.,"battery_kw":10.})
    with pytest.raises(ValueError,match="parallel"):
        pseg.validate_account({**a,"parallel_operation_confirmed":False},idx,equipment={"pv_ac_kw":1.})


@pytest.mark.parametrize("plan",["RS","GLP"])
def test_complete_2025_monthly_state_and_independently_dated_obligations(plan):
    state=None;total=0.;rows=[]
    for month in range(1,13):
        start=pd.Timestamp(year=2025,month=month,day=1)
        stop=start+pd.DateOffset(months=1)
        idx=grid(str(start.date()),str(stop.date()))
        a=account(plan,billing_month=str(start.date()),bill_date=str((stop-pd.Timedelta(days=1)).date()),
                  **pseg.hypothetical_obligation_overrides(plan,str(start.date())))
        baseline=1. if plan=="RS" else 10.
        demand=baseline+baseline*.5*((idx.hour>=17)&(idx.hour<21))
        b=calculate(idx,a,demand,state=state)
        rows.append(b);total+=b["total_usd"];state=b["next_state"]
    assert len(rows)==12 and np.isfinite(total)
    assert sum(r["metrics"]["import_kwh"] for r in rows)==pytest.approx((8760+365*2)*baseline)
    assert len({r["metrics"]["rate_version"] for r in rows})>=7
    if plan=="GLP":
        assert state["history_peaks_kw"]==[15.]*11
        assert rows[4]["lines"]["supply_capacity"]!=rows[5]["lines"]["supply_capacity"]


def test_real_time_negative_prices_are_preserved_not_clipped():
    idx=grid();a=account("LPL_P",market_data=prices(idx,value=-150.))
    b=calculate(idx,a,10.)
    assert b["lines"]["supply_hourly_energy"]<0
    assert b["lines"]["supply_ancillary"]>0
    # This commercial schedule does not gain an invented monthly service floor.
    assert b["lines"]["minimum_bill_adjustment"]==0


def test_ciep_loss_factors_are_independently_dated():
    assert pseg.version_on("2025-05-31")[0]["rates"]["ciep"]["mean_marginal_loss_pct"]==.79690
    assert pseg.version_on("2025-06-01")[0]["rates"]["ciep"]["mean_marginal_loss_pct"]==.91210
    assert pseg.version_on("2026-06-01")[0]["rates"]["ciep"]["mean_marginal_loss_pct"]==.92504


def test_evolving_der_classification_cannot_freeze_original_peak_history():
    a=account("GLP");idx=grid();eq={"pv_ac_kw":8.,"battery_kw":5.}
    pseg.validate_state(a,idx,{"history_peaks_kw":[40.]*11},eq)
    with pytest.raises(ValueError,match="cannot be frozen"):
        pseg.validate_state(a,idx,{"history_peaks_kw":[20.]*11},eq)
    # Pure grid-only operation does not inherit an invented DER obligation.
    pseg.validate_state(a,idx,{"history_peaks_kw":[20.]*11},{"pv_ac_kw":0.,"battery_kw":0.})
