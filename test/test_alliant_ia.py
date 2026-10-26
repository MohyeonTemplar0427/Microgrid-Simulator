"""Independent filed arithmetic, eligibility, clocks and optimization parity."""
from copy import deepcopy
from datetime import date, timedelta, timezone
from decimal import Decimal as D

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import alliant_ia as ia
from src.billing.alliant_ia_rates import service_rates
from src.billing.regional_math import BillingMath
from src.timeseries import build_interval_index


def fixture(plan="400", month="2026-07", step=15):
    start=month+"-01";end=str((pd.Timestamp(start)+pd.offsets.MonthEnd()).date())
    a=ia.hypothetical_defaults(plan);a.update(billing_month=start,bill_date=end)
    return a,build_interval_index(start,end,ia.TIMEZONE,step).index


def bill(plan="400", month="2026-07", power=1.):
    a,idx=fixture(plan,month)
    ia.validate_account(a,idx)
    return ia.charge_lines(idx,np.full(len(idx),power),np.zeros(len(idx)),a,math=BillingMath(idx))


@pytest.mark.parametrize("plan",ia.PLANS)
@pytest.mark.parametrize("month,eac,rts_res,rts_gs,peak_hours,days",[
    ("2026-06","-.00334",".04494",".03568",110,30),
    ("2026-07",".00656",".04494",".03568",115,31),
    ("2026-08",".01076",".04456",".03539",105,31),
    ("2026-09",".01616",".04456",".03539",0,30),
    ("2026-10",".01676",".04456",".03539",0,31),
])
def test_literal_independent_flat_one_kw_bill(plan,month,eac,rts_res,rts_gs,peak_hours,days):
    res=plan in ("400","407","427");summer=int(month[-2:]) in (6,7,8)
    hours=D(days*24);peak=D(peak_hours)
    if plan=="400":energy=hours*D(".13398" if summer else ".09992")
    elif plan=="600":energy=hours*D(".16513" if summer else ".12041")
    elif plan=="407":energy=peak*D(".22269")+(hours-peak)*D(".11134" if summer else ".09992")
    elif plan=="607":energy=peak*D(".28232")+(hours-peak)*D(".14116" if summer else ".12041")
    else:
        super_hours=D(days*8)
        energy=peak*D(".24585")+super_hours*D(".06146" if summer else ".05829")+(hours-peak-super_hours)*D(".12293" if summer else ".11657")
    expected=dict(customer=D(days)*D(".5096" if res else ".7562"),energy=energy,
        energy_adjustment=hours*D(eac), energy_efficiency=hours*D(".0013" if res else ".0038"),
        demand_response=hours*D(".0042" if res else ".0023"),regional_transmission=hours*D(rts_res if res else rts_gs))
    base=sum(expected.values())
    expected.update(iowa_state_sales_tax=base*D("0" if res else ".06"),local_option_sales_tax=base*D(".01"))
    result=bill(plan,month)
    assert set(result["lines"])==set(expected)
    for key,value in expected.items():assert float(result["lines"][key])==pytest.approx(float(value),abs=1e-9)
    assert result["rate_evidence_status"]=="verified" and result["rate_assumptions"]==[]
    assert result["metrics"]["included_rce_usd_per_kwh"]==.00006
    assert result["metrics"]["tax_benefit_usd_per_kwh"]==0.
    # EAC's included six-hundredths of a mill must not become another line.
    assert not {"rate_case_expense","tax_benefit","alternative_energy","fuel"}&set(result["lines"])


@pytest.mark.parametrize("plan",ia.PLANS)
@pytest.mark.parametrize("month",["2025-03","2025-06","2025-09","2025-11","2026-06","2026-09"])
def test_numeric_symbolic_billing_parity(plan,month):
    a,idx=fixture(plan,month)
    imports=.4+.5*(np.arange(len(idx))%17)/16
    raw=ia.charge_lines(idx,imports,np.zeros(len(idx)),a,math=BillingMath(idx))
    x=cp.Variable(len(idx));y=cp.Variable(len(idx))
    math=BillingMath(idx,convex=True,power_bound=2.)
    math.register_power(x,np.zeros(len(idx)),np.full(len(idx),2.))
    expr=ia.charge_lines(idx,x,y,a,math=math)
    objective=sum(expr["lines"].values())
    problem=cp.Problem(cp.Minimize(objective),[x==imports,y==0,*math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status==cp.OPTIMAL
    assert problem.value==pytest.approx(sum(raw["lines"].values()),abs=1e-8)
    for key,value in expr["lines"].items():
        actual=value.value if hasattr(value,"value") else value
        assert float(actual)==pytest.approx(float(raw["lines"][key]),abs=1e-8)


def at(stamp):
    return pd.DatetimeIndex([pd.Timestamp(stamp,tz=ia.TIMEZONE)])


@pytest.mark.parametrize("stamp,period",[
    ("2026-07-07 14:45","off"),("2026-07-07 15:00","peak"),
    ("2026-07-07 19:45","peak"),("2026-07-07 20:00","off"),
    ("2026-07-07 00:45","off"),("2026-07-07 01:00","super_off"),
    ("2026-07-07 08:45","super_off"),("2026-07-07 09:00","off"),
    ("2026-07-11 16:00","off"),("2026-09-01 16:00","off"),
    ("2026-06-19 16:00","peak"),("2026-07-03 16:00","peak"),
    ("2025-07-04 16:00","off"),("2027-07-05 16:00","peak"),
])
def test_filed_fixed_cst_tod_boundaries_and_exact_holiday(stamp,period):
    p=ia.periods(at(stamp),"427")
    assert p[period][0] and sum(int(p[k][0]) for k in ("peak","off","super_off"))==1


def test_three_part_holiday_keeps_daily_super_off_peak():
    assert ia.periods(at("2025-07-04 02:00"),"427")["super_off"][0]
    assert ia.periods(at("2025-07-04 16:00"),"427")["off"][0]
    assert ia.periods(at("2025-07-04 02:00"),"407")["off"][0]


def test_tod_clock_preserves_fold_and_spring_gap_without_rate_coverage_claim():
    spring=build_interval_index("2026-03-08","2026-03-08",ia.TIMEZONE,15).index
    fall=build_interval_index("2026-11-01","2026-11-01",ia.TIMEZONE,15).index
    assert len(spring)==92 and len(fall)==100
    assert spring.is_unique and fall.is_unique
    # Super-off follows eight fixed-clock elapsed hours even across the fold.
    assert ia.periods(fall,"427")["super_off"].sum()==32
    assert ia.periods(spring,"427")["super_off"].sum()==32
    assert not ia.periods(fall,"400")["peak"].any()
    with pytest.raises(ValueError,match="coverage"):
        service_rates("2026-11-01","427")


@pytest.mark.parametrize("plan",ia.PLANS)
@pytest.mark.parametrize("day",["2024-12-31","2026-01-01","2026-02-06","2026-05-31","2026-11-01","2026-12-31"])
def test_no_missing_history_or_future_eac_substitution(plan,day):
    with pytest.raises(ValueError,match="coverage"):
        service_rates(day,plan)


@pytest.mark.parametrize("day",["2026-6-1","2026-06-31",None,20260601])
def test_exact_iso_date_required(day):
    with pytest.raises(ValueError,match="ISO"):
        service_rates(day,"400")


def test_service_and_designated_bill_clock_must_align():
    with pytest.raises(ValueError,match="designated"):
        service_rates("2026-07-01","400",billing_month="2026-08-01")
    assert service_rates(date(2026,7,31),"400")["regional_transmission"]==.04494
    assert service_rates(date(2026,8,1),"400")["regional_transmission"]==.04456


@pytest.mark.parametrize("key,value",[
    ("eligibility_confirmed",False),("ordinary_service_confirmed",False),
    ("local_charges_confirmed",False),("tax_source",""),("cycle_source",""),
    ("tax_jurisdiction","cedar_rapids_city"),("meter_count",2),("service_line_count",2),
    ("supply","wholesale"),("export_mode","net_metering"),("opening_credit_usd",1.),
    ("phase","three"),("voltage_v",480.),("rate_evidence_mode","provisional_2025"),
    ("provisional_assumptions_accepted",True),
])
def test_account_scope_rejects_unconfirmed_or_unsupported_facts(key,value):
    a,idx=fixture();a[key]=value
    with pytest.raises(ValueError):ia.validate_account(a,idx)


@pytest.mark.parametrize("key",["tou_enrollment_confirmed","tou_clock_confirmed"])
def test_tod_requires_clock_and_enrollment_confirmation(key):
    a,idx=fixture("407");a[key]=False
    with pytest.raises(ValueError,match="TOD"):
        ia.validate_account(a,idx)


def test_general_service_classification_is_not_inferred_from_synthetic_usage():
    a,idx=fixture("600");a["small_general_confirmed"]=False
    with pytest.raises(ValueError,match="classification"):
        ia.validate_account(a,idx)
    a["small_general_confirmed"]=True
    with pytest.raises(ValueError,match="20,000"):
        ia.charge_lines(idx,np.full(len(idx),30.),np.zeros(len(idx)),a,math=BillingMath(idx))


@pytest.mark.parametrize("start,end",[("2026-07-02","2026-07-31"),("2026-07-01","2026-07-30"),("2026-07-15","2026-08-14")])
def test_partial_and_shifted_cycles_reject_unverified_allocation(start,end):
    a=ia.hypothetical_defaults();a.update(billing_month=start[:7]+"-01",bill_date=end)
    idx=build_interval_index(start,end,ia.TIMEZONE,15).index
    with pytest.raises(ValueError,match="complete calendar"):
        ia.validate_account(a,idx)


def test_missing_duplicate_and_wrong_zone_intervals_reject():
    a,idx=fixture()
    for damaged in (idx.delete(4),idx.insert(4,idx[4]),idx.tz_convert("America/New_York")):
        with pytest.raises(ValueError):ia.validate_account(a,damaged)


@pytest.mark.parametrize("plan",ia.PLANS)
def test_half_hour_cycles_cannot_replace_quarter_hour_io_meter_periods(plan):
    a,idx=fixture(plan,step=30)
    assert len(idx)==1488
    with pytest.raises(ValueError,match="15-minute meter"):
        ia.validate_account(a,idx)
    with pytest.raises(ValueError,match="15-minute meter"):
        ia.charge_lines(idx,np.ones(len(idx)),np.zeros(len(idx)),a,math=BillingMath(idx))


def test_non_export_der_requires_confirmed_applicable_ordinary_agreement():
    a,idx=fixture()
    equipment=dict(pv=True,battery=True,pv_dc_kw=5.,pv_ac_kw=4.,battery_kw=3.)
    ia.validate_account(a,idx,equipment)
    for changes in (dict(dg_enrollment_confirmed=False),dict(dg_source="")):
        bad={**a,**changes}
        with pytest.raises(ValueError,match="non-export"):
            ia.validate_account(bad,idx,equipment)
    with pytest.raises(ValueError,match="standalone"):
        ia.validate_account(a,idx,{**equipment,"pv":False})
    with pytest.raises(ValueError,match="20kW"):
        ia.validate_account(a,idx,{**equipment,"pv_dc_kw":20.})
    with pytest.raises(ValueError,match="non-export"):
        ia.charge_lines(idx,np.ones(len(idx)),np.ones(len(idx))*.1,a,math=BillingMath(idx))
    with pytest.raises(ValueError,match="credit"):
        ia.validate_state(a,idx,state={"opening_credit":1.})


def test_rates_catalog_explains_sources_and_keeps_provisional_disabled():
    for p in ia.catalog():
        a=ia.defaults(p["id"])
        assert not a["eligibility_confirmed"]
        assert p["coverage"]==[dict(start="2025-01-01",end="2025-12-31"),dict(start="2026-06-01",end="2026-10-31")]
        assert p["solar_modes"]==["non_export"]
        assert p["interval_minutes"]==[15]
        assert next(f for f in p["account_fields"] if f["name"]=="rate_evidence_mode")["choices"]==["verified"]
        assert any("alliantenergy.com" in s for s in p["sources"])
    a,idx=fixture();a.update(rate_evidence_mode="provisional_2025",provisional_assumptions_accepted=True)
    with pytest.raises(ValueError,match="no provisional"):
        ia.evidence(idx,a)


def test_absent_der_reporting_clears_io_claim_without_changing_charge_expressions():
    a,idx=fixture()
    imports=np.ones(len(idx));exports=np.zeros(len(idx))
    enrolled=ia.charge_lines(idx,imports,exports,a,math=BillingMath(idx))
    ordinary={**a,"dg_enrollment_confirmed":False,"dg_source":""}
    ia.validate_account(ordinary,idx,equipment=dict(pv=False,battery=False))
    reference=ia.charge_lines(idx,imports,exports,ordinary,math=BillingMath(idx))
    assert enrolled["metrics"]["dg_enrollment_confirmed"] is True
    assert reference["metrics"]["dg_enrollment_confirmed"] is False
    assert "Confirmed IO" in enrolled["metrics"]["generation_program"]
    assert "absent-DER" in reference["metrics"]["generation_program"]
    assert reference["lines"]==enrolled["lines"]


@pytest.mark.parametrize("plan",ia.PLANS)
@pytest.mark.parametrize("month,days,hours,super_hours,peak_hours,eac",[
    ("2025-01",31,744,248,0,".01160"),
    ("2025-02",28,672,224,0,".01020"),
    ("2025-03",31,743,248,0,".00020"),
    ("2025-04",30,720,240,0,"-.01100"),
    ("2025-05",31,744,248,0,"-.01050"),
    ("2025-06",30,720,240,105,".00180"),
    ("2025-07",31,744,248,110,".01240"),
    ("2025-08",31,744,248,105,".01810"),
    ("2025-09",30,720,240,0,".01976"),
    ("2025-10",31,744,248,0,".01496"),
    ("2025-11",30,721,240,0,".00666"),
    ("2025-12",31,744,248,0,"-.00034"),
])
def test_literal_2025_complete_month_bill_all_five_plans(plan,month,days,hours,super_hours,peak_hours,eac):
    """Independent literal calendar, filed prices and hand-calculated components.

    March and November have743/721 elapsed hours. Fixed-CST super-off hours
    remain248/240: the missing/extra boundary hour is at23:00 CST. These
    constants were counted in UTC independently of production periods().
    """
    res=plan in ("400","407","427");summer=month[5:] in ("06","07","08")
    h=D(hours);peak=D(peak_hours);super_h=D(super_hours)
    if plan=="400":energy=h*D(".13398" if summer else ".09992")
    elif plan=="600":energy=h*D(".16513" if summer else ".12041")
    elif plan=="407":energy=peak*D(".22269")+(h-peak)*D(".11134" if summer else ".09992")
    elif plan=="607":energy=peak*D(".28232")+(h-peak)*D(".14116" if summer else ".12041")
    else:
        energy=peak*D(".24585")+super_h*D(".06146" if summer else ".05829")+(h-peak-super_h)*D(".12293" if summer else ".11657")
    old_eecr=D(".0009" if res else ".0014");new_eecr=D(".0006" if res else ".0032")
    old_drcr=D(".0031" if res else ".0023");new_drcr=D(".0048" if res else ".0028")
    if month=="2025-06":
        eecr=(old_eecr*D(16)+new_eecr*D(14))/D(30)
        drcr=(old_drcr*D(16)+new_drcr*D(14))/D(30)
    elif month<"2025-06":eecr,drcr=old_eecr,old_drcr
    else:eecr,drcr=new_eecr,new_drcr
    rts=D((".04077" if res else ".03217") if month<"2025-09" else (".04055" if res else ".03196"))
    expected=dict(customer=D(days)*D(".5096" if res else ".7562"),energy=energy,
        energy_adjustment=h*D(eac),energy_efficiency=h*eecr,demand_response=h*drcr,
        regional_transmission=h*rts)
    tbr=D("-.00789" if res else "-.00592") if month<"2025-10" else D(0)
    if tbr:expected["tax_benefit"]=h*tbr
    subtotal=sum(expected.values())
    expected.update(iowa_state_sales_tax=subtotal*D("0" if res else ".06"),local_option_sales_tax=subtotal*D(".01"))
    result=bill(plan,month)
    assert result["metrics"]["cycle_days"]==days
    assert result["metrics"]["elapsed_hours"]==hours
    assert set(result["lines"])==set(expected)
    for key,value in expected.items():
        assert float(result["lines"][key])==pytest.approx(float(value),abs=1e-9)
    assert result["rate_evidence_status"]=="verified" and result["rate_assumptions"]==[]
    assert result["metrics"]["eac_includes_rce"] is (month>="2025-09")
    assert result["metrics"]["included_rce_usd_per_kwh"]==(.00006 if month>="2025-09" else 0.)
    assert result["metrics"]["tax_benefit_usd_per_kwh"]==float(tbr)
    assert not {"rate_case_expense","rts_refund","alternative_energy","fuel"}&set(result["lines"])


@pytest.mark.parametrize("plan",ia.PLANS)
def test_june_2025_rider_day_proration_is_independent_of_import_timing(plan):
    a,idx=fixture(plan,"2025-06")
    before=np.asarray(idx.day<=16)
    # Equal720kWh concentrated on opposite sides of June17. Each direction
    # must pay the same calendar-weighted recovery charges, despite distinct
    # actual kWh falling before and after the new factors.
    early=np.where(before,720./(16*24),0.)
    late=np.where(~before,720./(14*24),0.)
    math=BillingMath(idx)
    first=ia.charge_lines(idx,early,np.zeros(len(idx)),a,math=math)
    second=ia.charge_lines(idx,late,np.zeros(len(idx)),a,math=BillingMath(idx))
    res=plan in ("400","407","427")
    eecr=(D(".0009" if res else ".0014")*16+D(".0006" if res else ".0032")*14)/30
    drcr=(D(".0031" if res else ".0023")*16+D(".0048" if res else ".0028")*14)/30
    for key,factor in (("energy_efficiency",eecr),("demand_response",drcr)):
        assert first["lines"][key]==pytest.approx(float(D(720)*factor),abs=1e-9)
        assert second["lines"][key]==pytest.approx(first["lines"][key],abs=1e-9)
        segments=first["metrics"]["rider_allocation_segments"][key]
        assert [(s["start"],s["end"],s["calendar_days"]) for s in segments]==[
            ("2025-06-01","2025-06-16",16),("2025-06-17","2025-06-30",14)]
        assert first["metrics"]["billed_rider_factors_usd_per_kwh"][key]==pytest.approx(float(factor),abs=1e-14)
    # A fixed feasible CVXPY schedule must retain the same whole-cycle rule.
    x=cp.Variable(len(idx));y=cp.Variable(len(idx))
    convex=BillingMath(idx,convex=True,power_bound=3.)
    convex.register_power(x,np.zeros(len(idx)),np.full(len(idx),3.))
    expression=ia.charge_lines(idx,x,y,a,math=convex)
    problem=cp.Problem(cp.Minimize(sum(expression["lines"].values())),[x==late,y==0,*convex.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status==cp.OPTIMAL
    for key in ("energy_efficiency","demand_response"):
        assert float(expression["lines"][key].value)==pytest.approx(second["lines"][key],abs=1e-9)


def test_2025_component_boundaries_keep_independent_clocks():
    before=service_rates("2025-06-16","400")
    after=service_rates("2025-06-17","400")
    assert before["energy_efficiency"]==.0009 and after["energy_efficiency"]==.0006
    assert before["demand_response"]==.0031 and after["demand_response"]==.0048
    assert before["energy_adjustment"]==after["energy_adjustment"]==.0018
    assert service_rates("2025-08-31","600")["regional_transmission"]==.03217
    september=service_rates("2025-09-01","600")
    assert september["regional_transmission"]==.03196
    assert september["energy_adjustment"]==.01976 and september["eac_includes_rce"] is True
    assert september["tax_benefit"]==-.00592
    october=service_rates("2025-10-01","600")
    assert october["tax_benefit"]==0. and october["energy_adjustment"]==.01496


def test_interval_coefficients_cannot_blend_two_independent_cycles():
    idx=build_interval_index("2025-06-01","2025-07-31",ia.TIMEZONE,15).index
    with pytest.raises(ValueError,match="one calendar cycle"):
        ia.interval_rates(idx,"400")
