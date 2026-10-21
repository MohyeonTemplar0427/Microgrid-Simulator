"""Ameren Illinois ordinary DS-1/DS-2, standard BGS and non-interval TS.

The same exact filled-block expression calculates numeric bills and dispatch.
This adapter does not implement hourly supply, optional demand billing or export
settlement. Account metering classification is separate from input resolution.
"""
from copy import deepcopy
from datetime import date

import numpy as np
import pandas as pd

from .ameren_il_rates import PLANS, SOURCES, THROUGH, BASE, MONTHLY, EEA

UTILITY = "ameren_illinois"
TIMEZONE = "America/Chicago"


def month_rates(month,plan,zone):
    """An exact, finite source month; nothing extrapolated beyond the archive."""
    key=str(month)[:7]
    if key not in MONTHLY or plan not in PLANS or zone not in ("I","II","III"):
        raise ValueError("Ameren Illinois verified DS-1/standard DS-2 coverage is January 2025–October 2026, Rate Zones I/II/III.")
    year,number=map(int,key.split("-"));c=0 if plan=="DS-1" else 1
    row=deepcopy(MONTHLY[key]);customer,meter,summer,first,tail,edt=BASE[year][plan]
    row.update(customer=customer,meter=meter,distribution_first=summer if 6<=number<=9 else first,
        distribution_tail=summer if 6<=number<=9 else tail,edt=edt,
        transmission=((.02272,.02208) if key<"2025-06" else (.02264,.02200) if key<"2026-01" else
                      (.02629,.02555) if key<"2026-06" else (.02765,.02688))[c],
        delivery_eua=((1.22,.72) if key<"2025-06" else (.24,1.18) if key<"2026-06" else (-.27,.33))[c],
        supplemental=(.05 if c==0 else .50)+((.64,6.40) if year==2025 else (.80,8.00))[c]
            +(0. if number<=3 else -.91 if year==2025 else -.99)+(.04 if c==0 else 0.),
        map_reconciliation=(.1277 if number<5 else .1286) if year==2025 else (0. if number<4 else .0001),
        pbr_reconciliation=0. if year==2025 else .0365,
        revenue_balancing=0. if year==2025 else (.0309,-.0067)[c],
        deferred_income_tax=-.0219 if year==2025 else 0.,
        environmental=0. if zone=="II" else EEA[zone][key][c],
        hazardous_materials=0.,
        clean_energy=(.00189 if key<"2025-06" else .00177 if key<"2025-09" else
                      .00183 if key<"2026-06" else .00175 if key<"2026-09" else .00071),
        renewable_energy=.00458 if key<"2026-06" else .00470,
        energy_efficiency=((.00559,.00763) if year==2025 else (.00644,.00816))[c],
        utility_solar_storage=.000083 if year==2025 else .000097,
        energy_transition=.00072 if year==2025 else .00084,
        coal_solar_storage=(.00008 if number<10 else .00007) if year==2025 else
            (.00008 if number<4 or number>=10 else .00009),
        customer_generation=((.16,2.48) if year==2025 else (.31,6.30))[c])
    return row


def account_fields(plan="DS-1"):
    return [
        dict(name="eligibility_confirmed",type="boolean",default=False,required=True,label="Ameren Illinois territory, DS-1 or standard DS-2 and BGS eligibility independently confirmed"),
        dict(name="rate_zone",type="text",choices=["I","II","III"],required=True,label="Utility-assigned Illinois Rate Zone (from account, not MISO LRZ4 or address inference)"),
        dict(name="ts_metering",type="text",choices=["non_interval"],required=True,label="Retail transmission billing: confirmed non-interval, non-lighting TS classification"),
        dict(name="ts_metering_source",type="text",required=True,label="TS classification evidence or explicit hypothetical assumption; input CSV resolution does not establish it"),
        dict(name="ordinary_service_confirmed",type="boolean",default=False,required=True,label="Ordinary BGS secondary service; no ARES, PSP/RTP, optional demand, rebates, special facilities, EE opt-outs, discounts or tax exemptions"),
        dict(name="local_charges_confirmed",type="boolean",default=False,required=True,label="No municipal tax, EF, GC or IMF applies (e.g. independently confirmed unincorporated service)"),
        dict(name="full_monthly_charges_confirmed",type="boolean",default=False,required=True,label="Complete calendar meter cycle with full monthly charges; no partial, initial, final or rerouted cycle"),
        dict(name="cycle_source",type="text",required=True,label="Meter-cycle evidence or explicit hypothetical calendar-cycle assumption"),
        dict(name="dg_enrollment_confirmed",type="boolean",default=False,label="PV/storage: approved non-export renewable installation, BGS eligibility and storage arrangement confirmed"),
        dict(name="dg_source",type="text",label="Dated DER/interconnection approval and BGS eligibility evidence or explicit hypothetical assumption; omit personal information"),
    ]


def defaults(plan="DS-1"):
    if plan not in PLANS:
        raise ValueError("Choose Ameren Illinois DS-1 or standard DS-2.")
    res=plan=="DS-1"
    return dict(tariff=plan,supply="bgs",export_mode="none",rate_zone="II",ts_metering="non_interval",ts_metering_source="",
        eligibility_confirmed=False,ordinary_service_confirmed=False,local_charges_confirmed=False,
        full_monthly_charges_confirmed=False,dg_enrollment_confirmed=False,dg_source="",opening_credit_usd=0.,
        billing_month="2026-07-01",bill_date="2026-07-31",cycle_kind="regular",cycle_source="",
        voltage="secondary",phase="single" if res else "three",voltage_v=240. if res else 480.,power_factor=1.)


def hypothetical_defaults(plan="DS-1"):
    a=defaults(plan)
    a.update(eligibility_confirmed=True,ordinary_service_confirmed=True,local_charges_confirmed=True,
        full_monthly_charges_confirmed=True,hypothetical_account=True,
        ts_metering_source="Explicit hypothetical BGS non-interval retail TS billing classification, independently of native 15-minute simulation data",
        cycle_source="Explicit hypothetical full calendar meter cycle, not an actual statement",
        dg_enrollment_confirmed=True,dg_source="Hypothetical approved non-export renewable PV and storage, BGS eligible; no rebates, standby, opening credits or exports")
    return a


def catalog():
    return [dict(id=p,label="Ameren Illinois "+("Residential DS-1 / BGS-1" if p=="DS-1" else "Commercial standard DS-2 / BGS-2"),
        status="supported",customer_class="residential" if p=="DS-1" else "commercial",
        coverage=[dict(start="2025-01-01",end=THROUGH)],bill_month_coverage_required=True,
        voltage="secondary",solar_modes=["non_export"],supply_arrangements=["bgs"],
        equipment_modes=["grid_only","pv_only","pv_battery"],account_fields=account_fields(p),sources=SOURCES,
        representative_peak_kw=3. if p=="DS-1" else 25.,
        eligibility="Confirmed Ameren Illinois DS-1 ordinary residential or standard DS-2 secondary ≤600 V, BGS supply, non-interval retail TS billing. DS-2 historical eligibility and demand <150 kW required.",
        limitations=["Verified monthly supply archive January 2025–October 2026; no extrapolation to later months.",
            "Complete calendar billing months only; actual crossing-month, partial/initial/final and proration rules are not implemented.",
            "Seasonal declining energy blocks, no intraday TOU or measured demand charge in standard DS-2. Optional DS-2 demand service, PSP/RTP and third-party supply unsupported.",
            "Capacity included in BGS; dated non-interval Rider TS charged separately once. MISO LRZ4 and wholesale cpnode remain separate metadata.",
            "Rate Zone is an account input. Confirm absence of local/municipal charges; no exemptions or special contracts.",
            "Approved non-export PV/storage only, zero opening credits; no NMOS credit bank, export settlement, legacy netting, DER rebate or standalone storage."])
        for p in PLANS]


def cycle_review(a,index):
    idx=pd.DatetimeIndex(index)
    if len(idx)<2 or str(idx.tz)!=TIMEZONE:
        raise ValueError("Ameren Illinois requires timezone-aware America/Chicago intervals.")
    step=idx[1]-idx[0]
    if step not in (pd.Timedelta(minutes=15),pd.Timedelta(minutes=30)) or not np.all(idx[1:]-idx[:-1]==step):
        raise ValueError("Ameren Illinois needs consecutive elapsed-time 15/30-minute averages, without missing intervals.")
    stop=idx[-1]+step
    if (idx[0].day!=1 or idx[0]!=idx[0].normalize() or stop!=idx[0]+pd.offsets.MonthBegin()
            or a.get("cycle_kind")!="regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Ameren Illinois first scope requires a complete calendar billing month with full monthly charges; crossing/partial/initial/final proration unsupported.")
    try:
        month=date.fromisoformat(a["billing_month"]);bill=date.fromisoformat(a["bill_date"])
        if (month.isoformat()!=a["billing_month"] or bill.isoformat()!=a["bill_date"]
                or str(month)!=str(idx[0].date()) or bill!=idx[-1].date()):
            raise ValueError
    except (KeyError,ValueError,TypeError) as exc:
        raise ValueError("Ameren calendar-cycle billing month must match service, with bill date on the final service day.") from exc
    month_rates(month,a["tariff"],a["rate_zone"])
    return dict(cycle_days=(stop.date()-idx[0].date()).days,elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)),
        bill_date=str(bill),billing_month=str(month),service_start=str(idx[0].date()),service_end=str(idx[-1].date()),
        monthly_charge_factor=1.,partial_period_proration_applied=False)


def validate_account(a,index,equipment=None):
    if (not isinstance(a,dict) or a.get("tariff") not in PLANS or a.get("supply")!="bgs"
            or a.get("export_mode")!="none" or a.get("ts_metering")!="non_interval" or a.get("rate_zone") not in ("I","II","III")):
        raise ValueError("Ameren Illinois supports DS-1/standard DS-2 BGS supply and confirmed non-interval retail TS, Rate Zone I/II/III, zero export only.")
    if any(a.get(k) is not True for k in ("eligibility_confirmed","ordinary_service_confirmed","local_charges_confirmed")):
        raise ValueError("Confirm Ameren Illinois territory, ordinary BGS/tariff eligibility and absence of local or special charges.")
    for key in ("ts_metering_source","cycle_source"):
        if not isinstance(a.get(key),str) or not 1<=len(a[key].strip())<=500:
            raise ValueError("Document Ameren retail TS classification and calendar meter cycle or explicit hypothetical assumptions.")
    if a.get("opening_credit_usd")!=0.:
        raise ValueError("Ameren opening credits must be zero; export settlement is unsupported.")
    res=a["tariff"]=="DS-1"
    allowed=(("single",240.),) if res else (("single",240.),("three",480.))
    if a.get("voltage")!="secondary" or a.get("power_factor")!=1. or (a.get("phase"),a.get("voltage_v")) not in allowed:
        raise ValueError("Ameren first scope requires ordinary secondary-side metering: residential 240-V split phase; commercial 240-V single or 480-V three phase; no transformation/PF adjustment.")
    cycle_review(a,index)
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if (not equipment.get("pv") or a.get("dg_enrollment_confirmed") is not True
                or not isinstance(a.get("dg_source"),str) or not 1<=len(a["dg_source"].strip())<=500):
            raise ValueError("Ameren PV/storage requires approved non-export renewable installation, BGS eligibility and documented storage arrangement; standalone storage unsupported.")
        aggregate=max(equipment.get("pv_dc_kw",0.),equipment.get("pv_ac_kw",0.))+equipment.get("battery_kw",0.)
        if aggregate>50.+1e-8:
            raise ValueError("Ameren first non-export implementation conservatively limits aggregate PV nameplate plus battery discharge to 50 kW; this is not a statutory eligibility limit.")


def filled_blocks(volume,limits,rates,math,cache):
    """Exact declining blocks, pruning thresholds outside proven physical bounds.

    r_last*v + sum((r_i-r_next)*min(v,limit_i)) is the filled-block
    integral for nonnegative volume. Unlike sequential remaining-volume graphs,
    it preserves the optimizer's aggregate energy bound at every tax threshold.
    Shared thresholds (e.g. both residential winter blocks) use one exact graph.
    """
    lo,hi=math.bounds(volume) if math.convex else (float(volume),float(volume))
    cost=volume*rates[-1]
    for limit,first,next_rate in zip(limits,rates,rates[1:]):
        if first==next_rate:continue
        if limit not in cache:
            cache[limit]=volume if hi<=limit else limit if lo>=limit else math.minimum(volume,limit)
        cost+=(first-next_rate)*cache[limit]
    return cost


def charge_lines(index,imports,exports,a,*,math,state=None):
    idx=pd.DatetimeIndex(index)
    if state not in (None,{}):
        raise ValueError("Ameren carried settlement state unsupported.")
    if math.convex:
        math.constraints.append(exports==0)
        if a["tariff"]=="DS-2":math.constraints.append(imports<=149.999)
    elif np.max(exports)>1e-5 or a["tariff"]=="DS-2" and np.max(imports)>=150.:
        raise ValueError("Ameren standard DS-2 must remain below 150 kW; every case requires zero exports.")
    res=a["tariff"]=="DS-1";c=0 if res else 1
    r=month_rates(a["billing_month"],a["tariff"],a["rate_zone"])
    volume=math.hours*math.sum(imports)
    cache={}
    delivery=filled_blocks(volume,[800. if res else 2000.],[r["distribution_first"],r["distribution_tail"]],math,cache)
    supply=filled_blocks(volume,[800.],[r["supply_first"],r["supply_tail"]],math,cache) if res else volume*r["commercial_supply"]
    lines=dict(customer=r["customer"],meter=r["meter"],supplemental_customer=r["supplemental"],
        delivery_uncollectible=r["delivery_eua"],distribution=delivery,energy=supply,
        purchased_electricity_adjustment=volume*r["pea"],supply_cost_adjustment=volume*r["supply_adjustment"][c],
        supply_uncollectible=volume*r["supply_eua"][c],transmission=volume*r["transmission"],
        edt_cost_recovery=volume*r["edt"],customer_generation=r["customer_generation"])
    # PBR-R/MAP-R/RBA/EDITA independently apply to the SAME base, including
    # EDT but excluding supplemental charges and every other rider. No compounding.
    base=r["customer"]+r["meter"]+delivery+lines["edt_cost_recovery"]
    for key in ("map_reconciliation","pbr_reconciliation","revenue_balancing","deferred_income_tax"):
        lines[key]=base*r[key]
    for key in ("environmental","hazardous_materials","clean_energy","renewable_energy","energy_efficiency",
                "utility_solar_storage","energy_transition","coal_solar_storage"):
        lines[key]=volume*r[key]
    # Tax Additions: ordinary customer electricity excise, USD/kWh. EDT above
    # is a different cost recovery; neither is a percent tax on the whole bill.
    lines["illinois_electricity_excise"]=filled_blocks(volume,
        [2000.,50000.,100000.,500000.,1000000.,3000000.,5000000.,10000000.,20000000.],
        [.00330,.00319,.00303,.00297,.00286,.00270,.00254,.00233,.00207,.00202],math,cache)
    return dict(lines=lines,metrics={**cycle_review(a,idx),"rate_zone":a["rate_zone"],"retail_ts_classification":a["ts_metering"],
        "measured_demand_charge":False,"intraday_time_of_use_pricing":False,
        "distribution_initial_block_kwh":800. if res else 2000.,
        "base_adjustment_revenues_usd":base,
        "rate_effective_basis":"Complete calendar months only; dated PBR-R annual delivery, monthly BGS supply/PEA/SCA and designated-billing-month riders. No proration or crossed-month block-allocation inference.",
        "capacity_transmission_treatment":"Capacity included in BGS; non-interval Rider TS separately billed once; no MISO LMP or additional PLC/transmission tag charge"},
        next_state=deepcopy(state or {}),is_complete_bill=True,rate_evidence_status="verified",assumption_model=None,
        rate_assumptions=[],rate_sources=SOURCES,warnings=[
            "Bounded ordinary Ameren Illinois estimate: independently confirmed Rate Zone, BGS/non-interval TS classification and no local/special charges.",
            "Complete calendar cycles only; zero export/opening credits. Customer-generation charge applies to grid-only accounts too.",
            "DS-2 historical account eligibility remains an explicit confirmation; the optimizer's <150-kW limit does not establish it.",
            "Historical per-cycle perfect foresight, not a forecast or annual optimum. No MISO carbon/price substitution or site-specific electrical validation claim."])
