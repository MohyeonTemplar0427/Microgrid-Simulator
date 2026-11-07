"""Potomac Edison WV R/G with the non-demand-metered capacity minimum."""
import numpy as np
import pandas as pd

from .potomac_edison_wv_rates import BOOK, COVERAGE, DER, GAPS, SOURCES, TAX, rates_on

UTILITY="potomac_edison_west_virginia"
TIMEZONE="America/New_York"
PLANS=("R","G")
MAX_KW={"R":25.,"G":9.9}
HISTORY_LIMIT_KWH=6000.
CONFIRMATIONS={
    "eligibility_confirmed":"Potomac Edison confirmed West Virginia Schedule R residential or G general service",
    "ordinary_service_confirmed":"One ordinary secondary single-phase meter, no special rates, assistance, optional charges or credits",
    "full_monthly_charges_confirmed":"Complete calendar meter cycle, matching bill month and full monthly charges",
    "no_local_tax_confirmed":"Location is outside municipalities and local electric-tax districts, confirmed independently",
}


def account_fields(plan_id="R"):
    fields=[dict(name=k,type="boolean",required=True,label=v) for k,v in CONFIRMATIONS.items()]
    fields += [
        dict(name="account_source",type="text",required=True,label="Potomac Edison service, tariff and tax-location evidence"),
        dict(name="der_ordinary_service_confirmed",type="boolean",label="Written Company agreement retains ordinary import rates and excludes standby/AGS charges for this exact non-export installation"),
        dict(name="der_activation_date",type="date",label="Final interconnection approval active by"),
        dict(name="der_eligibility_source",type="text",label="Exact equipment and ordinary-rate continuation agreement reference"),
    ]
    if plan_id=="G":
        fields += [
            dict(name="g_no_demand_meter_confirmed",type="boolean",required=True,label="Company confirmed G without a demand meter or pending reclassification"),
            dict(name="g_capacity_requirements_kw",type="number",required=True,label="Independent normal maximum electrical requirement below 10 kW"),
            dict(name="history",type="object",required=True,label="12 actual prior calendar bills, oldest first, with month YYYY-MM and import_kwh"),
            dict(name="history_source",type="text",required=True,label="Actual meter history and non-demand capacity-method evidence"),
        ]
    return fields


def hypothetical_history(day):
    return [dict(month=str(m.date())[:7],import_kwh=1000.)
            for m in pd.date_range(end=pd.Timestamp(day)-pd.offsets.MonthBegin(),periods=12,freq="MS")]


def defaults(plan_id="R"):
    if plan_id not in PLANS:raise ValueError("Select Potomac Edison WV R or G.")
    a=dict(tariff=plan_id,supply="bundled",export_mode="none",voltage="secondary",phase="single",
           voltage_v=240.,meter_count=1,opening_credit_usd=0.,tax_jurisdiction="wv_unincorporated",
           rate_evidence_mode="verified",billing_month="2026-11-01",bill_date="2026-11-30",
           cycle_kind="regular",cycle_source="",account_source="",der_ordinary_service_confirmed=False,
           der_activation_date="",der_eligibility_source="")
    a.update(dict.fromkeys(CONFIRMATIONS,False))
    if plan_id=="G":
        a.update(g_no_demand_meter_confirmed=False,g_capacity_requirements_kw=None,history=[],history_source="")
    return a


def hypothetical_defaults(plan_id="R",*,day=None):
    a=defaults(plan_id)
    month=pd.Timestamp(day or a["billing_month"]).replace(day=1)
    a.update(dict.fromkeys(CONFIRMATIONS,True))
    a.update(hypothetical_account=True,billing_month=str(month.date()),bill_date=str((month+pd.offsets.MonthEnd()).date()),
             cycle_source="Hypothetical complete calendar meter cycle and matching bill month",
             account_source="Hypothetical ordinary Potomac Edison account in an independently declared unincorporated West Virginia location",
             der_ordinary_service_confirmed=True,der_activation_date="2024-12-31",
             der_eligibility_source="Hypothetical written special agreement approving exact non-export PV and paired PV-charged storage, ordinary rates without standby or other charges")
    if plan_id=="G":
        a.update(g_no_demand_meter_confirmed=True,g_capacity_requirements_kw=5.,
                 history=hypothetical_history(str(month.date())),
                 history_source="Hypothetical twelve prior actual 1,000 kWh meter bills and Company-approved non-demand capacity method")
    return a


def catalog():
    return [dict(id=p,label="Potomac Edison WV "+("Residential R" if p=="R" else "General Service G"),
                 customer_class="residential" if p=="R" else "commercial",status="supported",
                 coverage=[dict(start=s,end=e) for s,e in COVERAGE],
                 coverage_gaps=[dict(start=s,end=e,reason=r) for s,e,r in GAPS],
                 voltage="secondary",interval_minutes=[15],supply_arrangements=["bundled"],
                 representative_peak_kw=3. if p=="R" else 5.,account_fields=account_fields(p),sources=SOURCES,
                 equipment_modes=["grid_only","pv_only","pv_battery"],solar_modes=["non_export"],
                 eligibility="Company-confirmed single-meter ordinary West Virginia service, outside local tax districts. G requires non-demand metering and normal requirements below 10 kW.",
                 limitations=["Only listed complete calendar intersections, with actual prior meter history for G.",
                              "G capacity minimum uses maximum current or preceding twelve-month kWh divided by 120.",
                              "The 6,000 kWh G history/import envelope is an implementation limit. Qualification requires separate Company facts.",
                              "Approved PV and paired storage require ordinary-rate continuation by written special agreement."])
            for p in PLANS]


def _reference(a,key):
    value=a.get(key)
    if not isinstance(value,str) or not 1<=len(value.strip())<=500:
        raise ValueError("Document Potomac Edison "+key+" without personal identifiers.")


def _history(value):
    if not isinstance(value,list) or len(value)!=12:
        raise ValueError("Potomac Edison G requires twelve actual prior monthly meter bills.")
    checked=[]
    for item in value:
        if not isinstance(item,dict) or set(item)!={"month","import_kwh"} or not isinstance(item["month"],str):
            raise ValueError("Potomac Edison G history requires month YYYY-MM and import_kwh.")
        try:month=pd.Timestamp(item["month"]+"-01")
        except (ValueError,TypeError):raise ValueError("Use exact YYYY-MM history dates.") from None
        kwh=item["import_kwh"]
        if str(month.date())[:7]!=item["month"] or type(kwh) not in (int,float) or not 0<=kwh<=HISTORY_LIMIT_KWH:
            raise ValueError("Potomac Edison G history must be finite, exact and within the 6,000 kWh study limit.")
        if checked and month!=pd.Timestamp(checked[-1]["month"]+"-01")+pd.offsets.MonthBegin():
            raise ValueError("Potomac Edison G history must be consecutive without duplicate or missing months.")
        checked.append(dict(month=item["month"],import_kwh=float(kwh)))
    return checked


def cycle_review(a,index):
    idx=pd.DatetimeIndex(index)
    step=pd.Timedelta(minutes=15)
    if len(idx)<2 or str(idx.tz)!=TIMEZONE or idx.hasnans or not np.all(idx[1:]-idx[:-1]==step):
        raise ValueError("Potomac Edison requires complete consecutive Eastern-time 15-minute intervals.")
    first,stop=idx[0],idx[-1]+step
    if (first!=first.normalize() or first.day!=1 or stop!=first+pd.offsets.MonthBegin()
            or a.get("cycle_kind")!="regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Potomac Edison requires a complete calendar cycle and full monthly charges.")
    month,last=str(first.date()),str(idx[-1].date())
    if a.get("billing_month")!=month or a.get("bill_date")!=last:
        raise ValueError("Potomac Edison requires matching service and billing months.")
    r,sources,version=rates_on(month,a["tariff"])
    return dict(service_start=month,service_end=last,billing_month=month,bill_date=last,
                elapsed_hours=float((stop-first)/pd.Timedelta(hours=1)),source_version=version),r,sources


def validate_account(a,index,equipment=None):
    if not isinstance(a,dict) or a.get("tariff") not in PLANS or a.get("supply")!="bundled" or a.get("export_mode")!="none":
        raise ValueError("Select Potomac Edison WV bundled R/G and zero export.")
    if any(a.get(k) is not True for k in CONFIRMATIONS):
        raise ValueError("Confirm Potomac Edison assignment, ordinary service, full charges and independent unincorporated tax location.")
    expected=dict(voltage="secondary",phase="single",voltage_v=240.,meter_count=1,opening_credit_usd=0.,
                  tax_jurisdiction="wv_unincorporated",rate_evidence_mode="verified")
    if any(a.get(k)!=v or isinstance(a.get(k),bool) for k,v in expected.items()) or a.get("provisional_assumptions_accepted",False) is not False:
        raise ValueError("Potomac Edison scope is verified ordinary single-phase secondary service without local electric tax.")
    for key in ("account_source","cycle_source"):_reference(a,key)
    cycle,_,_=cycle_review(a,index)
    if a["tariff"]=="G":
        cap=a.get("g_capacity_requirements_kw")
        if a.get("g_no_demand_meter_confirmed") is not True or type(cap) not in (int,float) or not 0<cap<10.:
            raise ValueError("Confirm Potomac Edison G non-demand metering and independent normal capacity requirements below 10 kW.")
        _reference(a,"history_source")
        _history(a.get("history"))
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Potomac Edison PV/storage requires a written special agreement retaining ordinary non-export billing.")
        _reference(a,"der_eligibility_source")
        date=a.get("der_activation_date")
        try:active=str(pd.Timestamp(date).date())==date and date<=cycle["service_start"]
        except (TypeError,ValueError):active=False
        if not active:raise ValueError("Potomac Edison approval must be active before service.")
        if equipment.get("battery") and (equipment.get("renewable_only_charging") is not True or equipment.get("no_battery_export") is not True):
            raise ValueError("Potomac Edison storage requires PV-only charging and zero export.")


def validate_native_load(a,load):
    if np.max(load)>MAX_KW[a["tariff"]]+1e-7 or a["tariff"]=="G" and .25*np.sum(load)>HISTORY_LIMIT_KWH+1e-7:
        raise ValueError("Potomac Edison native load exceeds its independent study envelope. Reduced imports cannot establish classification.")


def validate_state(a,index,state=None,equipment=None):
    if a["tariff"]=="R":
        if state not in (None,{}):raise ValueError("Potomac Edison R has no carried billing state.")
        return
    if state not in (None,{}) and (not isinstance(state,dict) or set(state)!={"history"}):
        raise ValueError("Potomac Edison G carried state contains only actual import history.")
    history=_history((state or {}).get("history",a["history"]))
    previous=pd.DatetimeIndex(index)[0].normalize()-pd.offsets.MonthBegin()
    if history[-1]["month"]!=str(previous.date())[:7]:
        raise ValueError("Potomac Edison G history must end immediately before this cycle without skipped months.")


def charge_lines(index,imports,exports,a,*,math,state=None):
    validate_state(a,index,state)
    cycle,r,sources=cycle_review(a,index)
    commercial=a["tariff"]=="G"
    energy=math.hours*math.sum(imports)
    if math.convex:
        math.constraints.extend([exports==0,imports<=MAX_KW[a["tariff"]]])
        if commercial:math.constraints.append(energy<=HISTORY_LIMIT_KWH)
    elif np.max(exports)>1e-5 or np.max(imports)>MAX_KW[a["tariff"]]+1e-7 or commercial and energy>HISTORY_LIMIT_KWH+1e-7:
        raise ValueError("Potomac Edison requires zero export and imports within the study envelope.")
    base_energy=math.tiered(energy,(400.,),r["energy"]) if commercial else energy*r["energy"][0]
    lines=dict(bundled_customer=r["customer"],bundled_base_energy=base_energy)
    metrics=dict(**cycle,raw_import_kwh=energy,rounded_cash_optimum_claimed=False)
    next_state={}
    if commercial:
        history=_history((state or {}).get("history",a["history"]))
        previous=max(h["import_kwh"] for h in history)
        capacity=math.maximum(energy,previous,exact=True)/120.
        minimum=2.41*capacity
        lines["capacity_minimum_adjustment"]=math.positive(minimum-r["customer"]-base_energy,exact=True)
        next_state=dict(history=(history+[dict(month=cycle["billing_month"][:7],
                                              import_kwh=energy if math.convex else float(energy))])[-12:])
        metrics.update(capacity_for_minimum_kw=capacity,prior_maximum_import_kwh=previous,
                       capacity_minimum_usd=minimum)
    # The notices combine ECC and ECC-2 for 2025. Current sheets itemize
    # them separately. No municipality tax is applicable in this initial scope.
    lines.update({name:energy*r[name] for name in ("normalization","ecc","ecc2","vegetation","effluent","renewable")})
    lines.update(state_sales_tax=0.,local_tax=0.)
    return dict(lines=lines,next_state=next_state,metrics=metrics,is_complete_bill=True,excluded_components=[],
                rate_sources=[*sources,TAX,DER,BOOK],rate_evidence_status="verified",assumption_model=None,rate_assumptions=[],
                warnings=["Bundled retail base rate includes supply and delivery, with no additional wholesale charge.",
                          "No local electric-tax jurisdiction is permitted by this initial account scope.",
                          "2025 ECC notice reports the combined environmental control charge. 2026 filed ECC and ECC-2 remain itemized."])
