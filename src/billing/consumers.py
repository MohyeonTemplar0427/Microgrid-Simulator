"""Consumers Energy Michigan ordinary RSP/RSH/GS/GSTU full-service bills.

Consumer-specific calendars, billing-month seasons, assigned EE tiers and dated
rider clocks feed both numeric billing and dispatch's authoritative expression.
Non-export DG only; wholesale MISO costs are not added to bundled retail rates.
"""
from copy import deepcopy
from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd

from ..tou_calendar import HolidayCalendar
from .consumers_rates import PLANS, SOURCES, THROUGH, service_rates, rendered_rates

UTILITY = "consumers_energy"
TIMEZONE = "America/New_York"


@lru_cache(maxsize=32)
def commercial_holidays(year):
    """D-49/C14: six actual dates; no Friday/Monday substitute observance."""
    may = date(year,5,31)
    september = date(year,9,1)
    november = date(year,11,1)
    return frozenset((date(year,1,1), may-timedelta(days=may.weekday()),date(year,7,4),
        september+timedelta(days=(-september.weekday())%7),
        november+timedelta(days=(3-november.weekday())%7+21),date(year,12,25)))


GSTU_CALENDAR = HolidayCalendar("Consumers GSTU six actual holidays; no observed substitutes",commercial_holidays,tuple(SOURCES[:3]))


def periods(index, plan, billing_month=None):
    idx = pd.DatetimeIndex(index)
    if plan not in PLANS:
        raise ValueError("Choose Consumers RSP, RSH, GS or GSTU.")
    residential = plan in ("RSP", "RSH")
    # Residential seasons use calendar dates. Commercial sheets explicitly use
    # billing months, including a normal meter cycle spanning two calendar months.
    if residential:
        summer = np.asarray((idx.month>=6)&(idx.month<=9))
    else:
        if billing_month is None:
            raise ValueError("Consumers commercial seasons require the utility billing-month designation.")
        month = date.fromisoformat(billing_month).month
        summer = np.full(len(idx),6<=month<=9)
    weekday = np.asarray(idx.dayofweek<5)
    hour = idx.hour.to_numpy()+idx.minute.to_numpy()/60
    peak = np.zeros(len(idx),bool)
    mid = np.zeros(len(idx),bool)
    if residential:
        peak = weekday & (hour>=14) & (hour<19) & (summer if plan=="RSP" else True)
    elif plan=="GSTU":
        eligible = weekday & ~GSTU_CALENDAR.mask(idx).to_numpy()
        peak = eligible & np.where(summer,(hour>=14)&(hour<18),(hour>=7)&(hour<23))
        mid = eligible & summer & (hour>=7) & (hour<23) & ~peak
    slot = np.where(summer,np.where(peak,2,np.where(mid,1,0)),np.where(peak,4,3))
    return dict(peak=peak,mid=mid,off=~(peak|mid),summer=summer,slot=slot)


def interval_rates(index, plan, billing_month=None):
    idx = pd.DatetimeIndex(index)
    slot = periods(idx,plan,billing_month)["slot"]
    versions = {d:service_rates(d,plan) for d in set(idx.date)}
    rates = {k:np.array([versions[d][k][i] for d,i in zip(idx.date,slot)]) for k in ("energy","capacity")}
    rates.update({k:np.array([versions[d][k] for d in idx.date]) for k in
                  ("distribution","demand_response","irm","fcm","deferral")})
    return rates


def account_fields(plan="RSP"):
    fields = [
        dict(name="eligibility_confirmed",type="boolean",default=False,required=True,label="Consumers Energy Michigan territory and selected tariff eligibility independently confirmed"),
        dict(name="ordinary_service_confirmed",type="boolean",default=False,required=True,label="Ordinary full service: no discounts, special minimums, DR, retail choice, self-directed EE or primary-side metering"),
        dict(name="local_charges_confirmed",type="boolean",default=False,required=True,label="No additional locality/franchise charges, exemptions or special facilities apply"),
        dict(name="full_monthly_charges_confirmed",type="boolean",default=False,required=True,label="Complete regular monthly cycle; full system-access and assigned monthly surcharges apply"),
        dict(name="bill_date",type="date",required=True,label="Bill rendered date in designated utility billing month"),
        dict(name="cycle_source",type="text",required=True,label="Meter-cycle evidence or explicit hypothetical calendar-cycle assumption"),
        dict(name="dg_enrollment_confirmed",type="boolean",default=False,label="PV/storage: approved Consumers C11.3 DG enrollment, historical sizing and storage arrangement"),
        dict(name="dg_source",type="text",label="DG approval and sizing evidence or explicit hypothetical assumption; omit personal identifiers"),
    ]
    if plan in ("RSH","GSTU"):
        fields.append(dict(name="tou_enrollment_confirmed",type="boolean",default=False,required=True,
                           label="Required TOU metering, supporting infrastructure and enrollment confirmed"))
    if plan in ("GS","GSTU"):
        fields.extend([
            dict(name="ee_tier",type="number",min=1,max=10,step=1,required=True,label="Utility-assigned EE surcharge tier (1–10); annual review, not this cycle's consumption"),
            dict(name="ee_tier_source",type="text",required=True,label="Assigned EE tier evidence, effective period, or explicit hypothetical assumption"),
        ])
    return fields


def defaults(plan="RSP"):
    if plan not in PLANS:
        raise ValueError("Choose Consumers RSP, RSH, GS or GSTU.")
    res = plan in ("RSP","RSH")
    return dict(tariff=plan,supply="full_service",export_mode="none",eligibility_confirmed=False,
        ordinary_service_confirmed=False,local_charges_confirmed=False,full_monthly_charges_confirmed=False,
        tou_enrollment_confirmed=False,dg_enrollment_confirmed=False,dg_source="",opening_credit_usd=0.,
        billing_month="2026-06-01",bill_date="2026-06-30",
        cycle_kind="regular",cycle_source="",voltage="secondary",phase="single" if res else "three",
        voltage_v=240. if res else 480.,power_factor=1.,
        **({"ee_tier":1,"ee_tier_source":""} if not res else {}))


def hypothetical_defaults(plan="RSP"):
    a=defaults(plan)
    a.update(eligibility_confirmed=True,ordinary_service_confirmed=True,local_charges_confirmed=True,
        full_monthly_charges_confirmed=True,tou_enrollment_confirmed=True,hypothetical_account=True,
        cycle_source="Hypothetical full monthly calendar meter cycle, not an actual statement",
        dg_enrollment_confirmed=True,dg_source="Hypothetical approved C11.3 DG, aggregate DER ≤20 kW; utility-approved historical annual sizing and storage; zero exports/credits")
    if plan in ("GS","GSTU"):
        a.update(ee_tier=3,ee_tier_source="Hypothetical utility-assigned tier 3 throughout study; prior-year average 5,001–10,000 kWh/month; unchanged by present dispatch")
    return a


def catalog():
    labels={"RSP":"Residential Summer On-Peak Basic RSP","RSH":"Residential Smart Hours RSH",
            "GS":"Commercial General Service Secondary GS","GSTU":"Commercial Secondary TOU GSTU"}
    return [dict(id=p,label="Consumers "+labels[p],status="supported",
        customer_class="residential" if p in ("RSP","RSH") else "commercial",
        coverage=[dict(start="2025-01-01",end=THROUGH)],bill_month_coverage_required=True,
        voltage="secondary",solar_modes=["non_export"],supply_arrangements=["full_service"],
        equipment_modes=["grid_only","pv_only","pv_battery"],account_fields=account_fields(p),sources=SOURCES,
        representative_peak_kw=2. if p in ("RSP","RSH") else 20.,
        eligibility="Independently confirmed ordinary Consumers Michigan secondary full service; no special contracts. DER requires approved C11.3 DG, historical annual sizing/storage and aggregate ≤20 kW in this first scope.",
        limitations=["Verified January 2025–June 2026 actual PSCR; later factors are not inferred from authorized maxima.",
            "26–35-day complete regular cycles, confirmed full monthly fixed charges only. Partial/initial/final proration unsupported.",
            "RSP/RSH calendar seasons and weekday holidays included. GS/GSTU billing-month seasons; GSTU six actual holidays off-peak, no observed substitutes.",
            "Commercial EE is an explicitly assigned annual-review tier; no automatic reclassification from current dispatch.",
            "Capacity/transmission bundled; no additional MISO LMP/PLC charge. These GS/GSTU plans have no measured demand charge; GSD is not implemented.",
            "Non-export DG only; no legacy NEM, export-credit settlement, standby/SG, primary-side metering adjustment, EV/discount/DR programs or retail choice."])
        for p in PLANS]


def cycle_review(a,index):
    idx=pd.DatetimeIndex(index)
    if len(idx)<2 or str(idx.tz)!=TIMEZONE:
        raise ValueError("Consumers requires at least two Eastern-time intervals.")
    step=idx[1]-idx[0]
    if step not in (pd.Timedelta(minutes=15),pd.Timedelta(minutes=30)) or not np.all(idx[1:]-idx[:-1]==step):
        raise ValueError("Consumers requires consecutive elapsed-time 15/30-minute averages; no missing intervals.")
    stop=idx[-1]+step
    days=(stop.date()-idx[0].date()).days
    if (idx[0]!=idx[0].normalize() or stop!=stop.normalize() or not 26<=days<=35
            or a.get("cycle_kind")!="regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Consumers bounded scope needs a complete regular 26–35-day cycle with full monthly charges; partial/initial/final proration unsupported.")
    try:
        bill=date.fromisoformat(a["bill_date"]);month=date.fromisoformat(a["billing_month"])
        if (bill.isoformat()!=a["bill_date"] or month.isoformat()!=a["billing_month"] or month.day!=1
            or (bill.year,bill.month)!=(month.year,month.month) or bill<idx[-1].date()):
            raise ValueError
    except (KeyError,TypeError,ValueError) as exc:
        raise ValueError("Consumers requires an ISO bill date on/after service and its matching first-of-month utility billing designation.") from exc
    service_rates(idx[0].date(),a["tariff"]);service_rates(idx[-1].date(),a["tariff"])
    rendered_rates(month,a["tariff"] in ("RSP","RSH"))
    return dict(cycle_days=days,elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)),
        bill_date=str(bill),billing_month=str(month),service_start=str(idx[0].date()),service_end=str(idx[-1].date()),
        base_versions=sorted({service_rates(d,a["tariff"])["version"] for d in set(idx.date)}),
        monthly_charge_factor=1.,partial_period_proration_applied=False)


def validate_account(a,index,equipment=None):
    if not isinstance(a,dict) or a.get("tariff") not in PLANS or a.get("supply")!="full_service" or a.get("export_mode")!="none":
        raise ValueError("Consumers supports ordinary RSP/RSH/GS/GSTU full service with zero export; no choice or export settlement.")
    if any(a.get(k) is not True for k in ("eligibility_confirmed","ordinary_service_confirmed","local_charges_confirmed")):
        raise ValueError("Confirm Consumers territory/tariff, ordinary service and absence of additional locality/special charges.")
    if not isinstance(a.get("cycle_source"),str) or not a["cycle_source"].strip():
        raise ValueError("Document the full monthly meter cycle or explicit hypothetical assumption.")
    if a.get("opening_credit_usd")!=0.:
        raise ValueError("Consumers opening export-credit bank must be zero; settlement unsupported.")
    res=a["tariff"] in ("RSP","RSH")
    allowed=(("single",240.),) if res else (("single",240.),("three",480.))
    if a.get("voltage")!="secondary" or a.get("power_factor")!=1. or (a.get("phase"),a.get("voltage_v")) not in allowed:
        raise ValueError("Consumers first replay supports secondary 240-V single-phase residential/commercial or 480-V three-phase commercial, unity billing PF and secondary-side meter.")
    if a["tariff"] in ("RSH","GSTU") and a.get("tou_enrollment_confirmed") is not True:
        raise ValueError("Confirm Consumers TOU enrollment, required metering and supporting infrastructure.")
    if not res and (type(a.get("ee_tier")) is not int or not 1<=a["ee_tier"]<=10
                   or not isinstance(a.get("ee_tier_source"),str) or not a["ee_tier_source"].strip()):
        raise ValueError("Commercial Consumers needs a documented utility-assigned EE tier 1–10; do not infer it from current usage.")
    cycle_review(a,index)
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if (not equipment.get("pv") or a.get("dg_enrollment_confirmed") is not True
            or not isinstance(a.get("dg_source"),str) or not a["dg_source"].strip()):
            raise ValueError("Consumers DER requires approved C11.3 renewable-PV DG, historical annual sizing and storage approval; non-export alone does not waive SG/standby rules.")
        aggregate=max(equipment.get("pv_dc_kw",0.),equipment.get("pv_ac_kw",0.))+equipment.get("battery_kw",0.)
        if aggregate>20.+1e-8:
            raise ValueError("Consumers first DG scope conservatively limits PV nameplate plus battery discharge to 20 kW aggregate.")


def charge_lines(index,imports,exports,a,*,math,state=None):
    idx=pd.DatetimeIndex(index)
    if math.convex:
        math.constraints.append(exports==0)
    elif np.max(exports)>1e-5:
        raise ValueError("Consumers first scope requires zero exports.")
    if state not in (None,{}):
        raise ValueError("Consumers carried credits/settlement state unsupported.")
    res=a["tariff"] in ("RSP","RSH")
    r=interval_rates(idx,a["tariff"],a["billing_month"])
    rendered=rendered_rates(a["billing_month"],res)
    volume=math.hours*math.sum(imports)
    lines={k:math.hours*math.dot(imports,r[k]) for k in r}
    lines["system_access"]=8. if res else 20.
    for k in ("pscr","power_plant_securitization","karn_securitization"):
        lines[k]=volume*rendered[k]
    lines["energy_efficiency"]=volume*rendered["residential_ee"] if res else rendered["commercial_ee"][a["ee_tier"]-1]
    for k in ("refund_reconciliation","irm_reconciliation"):
        lines[k]=rendered[k]
    # Michigan Treasury 2013-5: separately stated LIEAF tax is exempt.
    lines["sales_tax"]=sum(lines.values())*(.04 if res else .06)
    lines["lieaf"]=rendered["lieaf"]
    p=periods(idx,a["tariff"],a["billing_month"])
    return dict(lines=lines,metrics={**cycle_review(a,idx),
        **{k+"_kwh":math.hours*math.dot(imports,p[k].astype(float)) for k in ("peak","mid","off")},
        "measured_demand_charge":False,"ee_assigned_tier":None if res else a["ee_tier"],
        "ee_tier_source":None if res else a["ee_tier_source"],"pscr_usd_per_kwh":rendered["pscr"],
        "sales_tax_fraction":.04 if res else .06,
        "rate_effective_basis":"Base/DR/IRM/FCM/deferral: local service date; PSCR/EE/securitization/reconciliations/LIEAF: designated utility billing month. Residential season: calendar date; commercial season: billing month.",
        "capacity_transmission_treatment":"Bundled full service; no additional MISO wholesale, PLC or transmission-tag charges"},
        next_state=deepcopy(state or {}),is_complete_bill=True,rate_evidence_status="verified",assumption_model=None,
        rate_assumptions=[],rate_sources=SOURCES,warnings=[
            "Consumers bounded ordinary full-service monthly estimate; confirmed zero exports/credits and independent DG sizing/storage approval.",
            "26–35-day complete-cycle guard is an implementation boundary, not a filed universal proration rule. Assigned EE tier is an account input, unchanged by dispatch.",
            "Historical per-cycle perfect foresight; MISO metadata is separate from retail economics. No MISO carbon, live market prices or site-specific circuit claim."])
