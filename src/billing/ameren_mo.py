"""Ameren Missouri ordinary residential TOU and standard small commercial.

Retail prices, account history and taxes feed the same numeric/dispatch algebra.
No export settlement, wholesale price pass-through or invented cycle proration.
"""
from copy import deepcopy
from datetime import date, timedelta
from functools import lru_cache

from dateutil.easter import easter
import numpy as np
import pandas as pd

from ..tou_calendar import HolidayCalendar
from .ameren_mo_rates import PLANS, SOURCES, THROUGH, service_rates

UTILITY = "ameren_missouri"
TIMEZONE = "America/Chicago"


@lru_cache(maxsize=32)
def smart_holidays(year):
    """Sheet54.8: nine actual dates, no Friday/Monday substitute provision."""
    may=date(year,5,31);sep=date(year,9,1);nov=date(year,11,1)
    thanksgiving=nov+timedelta(days=(3-nov.weekday())%7+21)
    return frozenset((date(year,1,1),easter(year)-timedelta(days=2),
        may-timedelta(days=may.weekday()),date(year,7,4),
        sep+timedelta(days=(-sep.weekday())%7),thanksgiving,
        thanksgiving+timedelta(days=1),date(year,12,24),date(year,12,25)))


SMART_CALENDAR=HolidayCalendar("Ameren Missouri Smart Saver nine actual holidays; no substitute dates",smart_holidays,tuple(SOURCES[:3]))


def preceding_summer_month(month):
    """Last completed summer month, including the current year's Nov/Dec."""
    current=pd.Timestamp(month).replace(day=1)
    if current.month in (7,8,9,10):return current-pd.DateOffset(months=1)
    return current.replace(month=9,year=current.year if current.month>10 else current.year-1)


def periods(index,plan):
    idx=pd.DatetimeIndex(index)
    if plan not in PLANS or str(idx.tz)!=TIMEZONE:
        raise ValueError("Select a Missouri plan and America/Chicago local timestamps.")
    hour=idx.hour.to_numpy()+idx.minute.to_numpy()/60
    summer=np.asarray((idx.month>=6)&(idx.month<=9))
    peak=np.zeros(len(idx),bool);mid=np.zeros(len(idx),bool)
    if plan=="1M-EMS":peak=(hour>=9)&(hour<21)
    elif "OVERNIGHT" in plan:peak=(hour>=6)&(hour<22)
    elif "SMART" in plan:
        weekday=np.asarray(idx.dayofweek<5)&~SMART_CALENDAR.mask(idx).to_numpy()
        peak=weekday&np.where(summer,(hour>=15)&(hour<19),((hour>=6)&(hour<8))|((hour>=18)&(hour<20)))
        mid=(hour>=6)&(hour<22)&~peak
    return dict(summer=summer,peak=peak,mid=mid,off=~(peak|mid))


def interval_rates(index,plan):
    """Base marginal TOU price; winter block plans expose their first-block price.

    The cycle expression, not this diagnostic series, integrates declining blocks.
    """
    idx=pd.DatetimeIndex(index);p=periods(idx,plan)
    rates={d:service_rates(d,plan) for d in set(idx.date)}
    energy=[]
    for i,d in enumerate(idx.date):
        r=rates[d];summer=p["summer"][i]
        anytime=plan=="1M" or plan.endswith("-B") and not summer
        if plan=="2M":v=r["commercial"][0 if summer else 1]
        elif anytime:v=r["anytime"][0 if summer else 1]
        elif plan=="1M-EMS":v=r["ems"][0 if summer else 1]+r["ems_adder"][0 if summer else 1]*p["peak"][i]
        elif "SMART" in plan:v=r["smart_summer" if summer else "smart_winter"][0 if p["peak"][i] else 1 if p["mid"][i] else 2]
        else:v=r["overnight"][(0 if summer else 2)+(0 if p["peak"][i] else 1)]
        energy.append(v)
    return {"energy":np.asarray(energy),**{k:np.asarray([rates[d][k] for d in idx.date]) for k in
        ("fuel_adjustment","securitization","energy_efficiency","renewable_adjustment")}}


def account_fields(plan="1M"):
    fields=[dict(name=k,type="boolean",default=False,required=True,label=label) for k,label in (
        ("eligibility_confirmed","Ameren Missouri territory and selected 1(M)/2(M) account eligibility independently confirmed"),
        ("ordinary_service_confirmed","Ordinary bundled secondary service; no special facilities, EE opt-outs/exemptions, rebates, community solar, standby, NEM agreement or special contracts"),
        ("local_charges_confirmed","Confirmed unincorporated Cole County jurisdiction 00000-051-000; no city/franchise/underground charge or tax exemption"),
        ("full_monthly_charges_confirmed","Complete calendar meter cycle, full monthly charges; no partial/initial/final/rerouted cycle"))]
    fields.extend([dict(name="tax_jurisdiction",type="text",choices=["cole_county_unincorporated"],label="Verified first-scope tax jurisdiction; confirm independently of map"),
        dict(name="tax_source",type="text",required=True,label="Jurisdiction evidence or explicit hypothetical account; Cole domestic utility 0%, ordinary commercial sales 5.6%"),
        dict(name="cycle_source",type="text",required=True,label="Meter-cycle evidence or explicit hypothetical calendar-cycle assumption"),
        dict(name="dg_enrollment_confirmed",type="boolean",default=False,label="PV/storage: written approved non-export interconnection, ordinary tariff retained and no NEM/standby agreement"),
        dict(name="dg_source",type="text",label="Non-export PV/storage approval evidence or explicit hypothetical assumption; omit personal identifiers")])
    if plan not in ("1M","2M"):
        fields.append(dict(name="tou_enrollment_confirmed",type="boolean",required=True,label="Selected TOU enrollment, AMI meter and applicable term/switching eligibility confirmed"))
    if plan=="2M":
        fields.append(dict(name="history",type="object",required=True,label="Documented preceding May/October kWh and maximum of any preceding summer month; dates, source, no invented missing history"))
    return fields


def defaults(plan="1M"):
    if plan not in PLANS:raise ValueError("Select an Ameren Missouri 1(M) or standard 2(M) plan.")
    res=plan!="2M"
    a=dict(tariff=plan,supply="bundled",export_mode="none",eligibility_confirmed=False,
        ordinary_service_confirmed=False,local_charges_confirmed=False,full_monthly_charges_confirmed=False,
        tax_jurisdiction="cole_county_unincorporated",tax_source="",tou_enrollment_confirmed=False,
        dg_enrollment_confirmed=False,dg_source="",opening_credit_usd=0.,billing_month="2026-07-01",
        bill_date="2026-07-31",cycle_kind="regular",cycle_source="",voltage="secondary",
        phase="single" if res else "three",voltage_v=240. if res else 480.,power_factor=1.)
    if not res:a["history"]={"may_month":"2026-05-01","may_kwh":0.,"october_month":"2025-10-01","october_kwh":0.,
        "summer_through":"2026-06-01","summer_max_kwh":0.,"source":""}
    return a


def hypothetical_defaults(plan="1M"):
    a=defaults(plan)
    a.update(eligibility_confirmed=True,ordinary_service_confirmed=True,local_charges_confirmed=True,
        full_monthly_charges_confirmed=True,tou_enrollment_confirmed=True,hypothetical_account=True,
        tax_source="Explicit hypothetical unincorporated Cole County account 00000-051-000; Missouri DOR dated rate tables, no additional city/district/franchise charges",
        cycle_source="Explicit hypothetical complete calendar meter cycle, not a customer statement",
        dg_enrollment_confirmed=True,dg_source="Hypothetical written approved non-export renewable PV/storage interconnection; ordinary bundled tariff, no NEM, standby, credits or rebates")
    if plan=="2M":a["history"].update(may_kwh=6000.,october_kwh=5500.,summer_max_kwh=9000.,
        source="Explicit hypothetical utility-confirmed prior monthly imports and maximum across all preceding summer months, not measured history")
    return a


def catalog():
    labels={"1M":"Residential 1(M) Anytime","1M-EMS":"Residential 1(M) Evening/Morning Saver",
        "1M-SMART-A":"Residential 1(M) Smart Saver · year-round A","1M-SMART-B":"Residential 1(M) Smart Saver · summer-only B",
        "1M-OVERNIGHT-A":"Residential 1(M) Overnight Saver · year-round A","1M-OVERNIGHT-B":"Residential 1(M) Overnight Saver · summer-only B",
        "2M":"Commercial standard 2(M) Small General Service"}
    return [dict(id=p,label="Ameren Missouri "+labels[p],status="supported",customer_class="commercial" if p=="2M" else "residential",
        coverage=[dict(start="2025-01-01",end=THROUGH)],voltage="secondary",solar_modes=["non_export"],
        supply_arrangements=["bundled"],equipment_modes=["grid_only","pv_only","pv_battery"],
        representative_peak_kw=25. if p=="2M" else 3.,account_fields=account_fields(p),sources=SOURCES,
        eligibility="Confirmed ordinary Missouri secondary bundled account; complete calendar cycles and unincorporated Cole County tax jurisdiction only. TOU enrollment/AMI and non-export DER approval are explicit account facts.",
        limitations=["Verified service dates January2025–October21,2026; only complete calendar cycles (latest September2026). No inferred proration, crossing-month blocks or later prices.",
          "Standard2(M) winter Base/Seasonal energy uses documented preceding May/October and maximum any prior summer month; history evolves separately by scenario. No measured demand charge.",
          "Smart Saver has nine actual holidays, no substitute observance. EMS/Overnight periods apply all days. OptionB uses Anytime winter rates.",
          "ColeCounty domestic utility tax0%, ordinary commercial sales tax5.6%; other jurisdictions/extra fees/exemptions unsupported.",
          "No exports, NEM settlement, Ultimate Saver demand plan, legacy TOD pilot, commercial optional TOD/Overnight, missing-history refund, non-AMI meter or standalone storage.",
          "Bundled generation/transmission and applicable riders only; no MISO LMP, extra capacity/PLC charge or CAISO carbon substitution."])
        for p in PLANS]


def cycle_review(a,index):
    idx=pd.DatetimeIndex(index)
    if len(idx)<2 or str(idx.tz)!=TIMEZONE:raise ValueError("Ameren Missouri requires America/Chicago local intervals.")
    step=idx[1]-idx[0]
    if step not in (pd.Timedelta(minutes=15),pd.Timedelta(minutes=30)) or not np.all(idx[1:]-idx[:-1]==step):
        raise ValueError("Ameren Missouri requires consecutive 15/30-minute elapsed intervals without gaps.")
    stop=idx[-1]+step
    if idx[0]!=idx[0].normalize() or idx[0].day!=1 or stop!=idx[0]+pd.offsets.MonthBegin() or a.get("cycle_kind")!="regular" or a.get("full_monthly_charges_confirmed") is not True:
        raise ValueError("Ameren Missouri first scope needs a complete calendar meter cycle; partial/crossing/initial/final proration unsupported.")
    if a.get("billing_month")!=str(idx[0].date()) or a.get("bill_date")!=str(idx[-1].date()):
        raise ValueError("Missouri calendar billing month must match service, bill date on final service day.")
    service_rates(idx[0].date(),a["tariff"]);service_rates(idx[-1].date(),a["tariff"])
    return dict(cycle_days=(stop.date()-idx[0].date()).days,elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)),
        service_start=str(idx[0].date()),service_end=str(idx[-1].date()),billing_month=a["billing_month"],
        bill_date=a["bill_date"],monthly_charge_factor=1.,partial_period_proration_applied=False)


def _history(h):
    required={"may_month","may_kwh","october_month","october_kwh","summer_through","summer_max_kwh","source"}
    if not isinstance(h,dict) or set(h)!=required or not isinstance(h.get("source"),str) or not 1<=len(h["source"].strip())<=500:
        raise ValueError("Missouri2(M) needs documented May/October/summer history; missing-history and later refund rules unsupported.")
    for k in ("may_kwh","october_kwh","summer_max_kwh"):
        if isinstance(h[k],bool) or not isinstance(h[k],(float,int)) or not np.isfinite(h[k]) or h[k]<0:
            raise ValueError("History must contain finite nonnegative billed import kWh, not power or native load.")
    try:
        for key,months in (("may_month",(5,)),("october_month",(10,)),("summer_through",(6,7,8,9))):
            d=date.fromisoformat(h[key])
            if d.isoformat()!=h[key] or d.day!=1 or d.month not in months:raise ValueError
    except (ValueError,TypeError) as exc:raise ValueError("Document correctly dated prior May/October/summer billing months.") from exc
    return h


def validate_account(a,index,equipment=None):
    if not isinstance(a,dict) or a.get("tariff") not in PLANS or a.get("supply")!="bundled" or a.get("export_mode")!="none":
        raise ValueError("Ameren Missouri supports ordinary1(M)/standard2(M) bundled service with zero export only.")
    if any(a.get(k) is not True for k in ("eligibility_confirmed","ordinary_service_confirmed","local_charges_confirmed")) or a.get("tax_jurisdiction")!="cole_county_unincorporated":
        raise ValueError("Confirm Missouri tariff/ordinary service and unincorporated ColeCounty tax jurisdiction; other locality fees unsupported.")
    for key in ("tax_source","cycle_source"):
        if not isinstance(a.get(key),str) or not 1<=len(a[key].strip())<=500:raise ValueError("Document Missouri jurisdiction and calendar-cycle account facts.")
    if a.get("opening_credit_usd")!=0.:raise ValueError("Missouri opening credits must be zero; settlement unsupported.")
    res=a["tariff"]!="2M";allowed=(("single",240.),) if res else (("single",240.),("three",480.))
    if a.get("voltage")!="secondary" or a.get("power_factor")!=1. or (a.get("phase"),a.get("voltage_v")) not in allowed:
        raise ValueError("Missouri requires ordinary secondary-side240V split phase or commercial480V three phase; no billing PF/transformer adjustment.")
    if a["tariff"] not in ("1M","2M") and a.get("tou_enrollment_confirmed") is not True:raise ValueError("Confirm required AMI meter, selected TOU enrollment and switching eligibility.")
    cycle_review(a,index)
    if not res:_history(a.get("history"))
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("dg_enrollment_confirmed") is not True or not isinstance(a.get("dg_source"),str) or not 1<=len(a["dg_source"].strip())<=500:
            raise ValueError("Missouri requires approved non-export PV/storage with ordinary tariff retained; no NEM/standby enrollment or standalone storage.")
        if max(equipment.get("pv_dc_kw",0.),equipment.get("pv_ac_kw",0.))+equipment.get("battery_kw",0.)>50.+1e-8:
            raise ValueError("First Missouri DER scope conservatively bounds aggregate PV nameplate plus storage discharge to50kW, not a statutory enrollment limit.")


def validate_state(a,index,*,state=None,equipment=None):
    if a["tariff"]!="2M":
        if state not in (None,{}):raise ValueError("Residential Missouri has no carried credit/history ledger.")
        return
    if state is not None and (not isinstance(state,dict) or set(state)!={"history","next_billing_month"} or state["next_billing_month"]!=a["billing_month"]):
        raise ValueError("Missouri commercial history state must continue consecutively without replay or skipped cycles.")
    h=_history(a["history"] if state is None else state["history"])
    current=pd.Timestamp(a["billing_month"])
    for key,month in (("may_month",5),("october_month",10)):
        expected=current.replace(month=month)
        if expected>=current:expected-=pd.DateOffset(years=1)
        if h[key]!=str(expected.date()):raise ValueError("Missouri2(M) requires the immediately preceding May and October billing records.")
    if pd.Timestamp(h["summer_through"])>=current:
        raise ValueError("Summer history must precede the current cycle; no perfect-foresight future billing determinant.")
    expected_summer=preceding_summer_month(current)
    if h["summer_through"]!=str(expected_summer.date()):raise ValueError("Document summer maximum through the last preceding summer billing month.")


def _filled(volume,threshold,first,tail,math):
    lo,hi=math.bounds(volume) if math.convex else (float(volume),float(volume))
    used=volume if hi<=threshold else threshold if lo>=threshold else math.minimum(volume,threshold)
    return volume*tail+(first-tail)*used


def charge_lines(index,imports,exports,a,*,math,state=None):
    idx=pd.DatetimeIndex(index);validate_state(a,idx,state=state)
    commercial=a["tariff"]=="2M";p=periods(idx,a["tariff"])
    if math.convex:
        math.constraints.append(exports==0)
        if commercial:math.constraints.append(imports<=100.)
    elif np.max(exports)>1e-5 or commercial and np.max(imports)>100.+1e-5:
        raise ValueError("Missouri non-export standard2(M) scope requires imports at most100kW; historical eligibility still independently confirmed.")
    r=service_rates(idx[0].date(),a["tariff"]);v=math.hours*math.sum(imports);summer=bool(p["summer"][0])
    # Complete calendar cycles prevent fabricated block allocation at season/base-rate crossings.
    anytime=a["tariff"]=="1M" or a["tariff"].endswith("-B") and not summer
    threshold=None;h=deepcopy((state or {}).get("history",a.get("history")))
    if commercial:
        threshold=max(1000.,min(h["may_kwh"],h["october_kwh"],h["summer_max_kwh"]))
        energy=v*r["commercial"][0] if summer else _filled(v,threshold,*r["commercial"][1:],math)
    elif anytime or a["tariff"]=="1M-EMS":
        key="anytime" if anytime else "ems";prices=r[key]
        energy=v*prices[0] if summer else _filled(v,750.,*prices[1:],math)
        if not anytime:energy+=math.hours*math.dot(imports,p["peak"]*r["ems_adder"][0 if summer else 1])
    else:energy=math.hours*math.dot(imports,interval_rates(idx,a["tariff"])["energy"])
    lines=dict(customer=r["commercial_customer"][a["phase"]=="three"] if commercial else r["residential_customer"],
        low_income_pilot=r["commercial_pilot"] if commercial else r["residential_pilot"],energy=energy)
    rates=interval_rates(idx,a["tariff"])
    for key in ("fuel_adjustment","securitization","energy_efficiency","renewable_adjustment"):
        lines[key]=math.hours*math.dot(imports,rates[key])
    tax_rate=.056 if commercial else 0.
    tax_base=sum(lines.values());lines["missouri_sales_tax"]=tax_base*tax_rate
    next_state={}
    if commercial and not math.convex:
        month=idx[0].month;key=a["billing_month"]
        if month==5:h.update(may_month=key,may_kwh=float(v))
        if month==10:h.update(october_month=key,october_kwh=float(v))
        if 6<=month<=9:h.update(summer_through=key,summer_max_kwh=max(h["summer_max_kwh"],float(v)))
        next_state=dict(history=h,next_billing_month=str((idx[0]+pd.offsets.MonthBegin()).date()))
    return dict(lines=lines,metrics={**cycle_review(a,idx),"winter_base_threshold_kwh":threshold,
        "history_used":deepcopy((state or {}).get("history",a.get("history"))) if commercial else None,
        "measured_demand_charge":False,"intraday_time_of_use_pricing":a["tariff"] not in ("1M","2M") and not anytime,
        "tax_jurisdiction":a["tax_jurisdiction"],"sales_tax_rate":tax_rate,"sales_tax_base_usd":tax_base,
        "base_version":r["base_version"],"rider_versions":{k:sorted({service_rates(d,a["tariff"])[k+"_version"] for d in set(idx.date)}) for k in ("fuel_adjustment","securitization","energy_efficiency","renewable_adjustment")},
        "capacity_transmission_treatment":"Bundled base rates and FAC; no separate MISO LMP, PLC or transmission-tag adder",
        "rate_effective_basis":"Exact service dates; complete calendar months only, no proration"},
        next_state=next_state,is_complete_bill=True,rate_evidence_status="verified",assumption_model=None,rate_assumptions=[],rate_sources=SOURCES,
        warnings=["Ordinary bundled, unincorporated ColeCounty account only; verify territory, eligibility and local taxes independently.",
            "Zero exports/NEM credits. Complete calendar cycles; no partial or cross-month allocation. No Ultimate Saver or optional commercial TOU.",
            "Historical rolling-cycle perfect foresight; 2(M) uses scenario-specific prior billed-import history, not a joint annual optimum.",
            "Representative OpenDSS replay remains separate from billed scheduled flows; no site-specific approval or CAISO carbon substitution."])
