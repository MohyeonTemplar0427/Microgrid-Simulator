"""Appalachian Power West Virginia ordinary RS/SGS, non-export only."""
import numpy as np
import pandas as pd

from .appalachian_wv_rates import COVERAGE, DER, GAPS, SOURCES, TAX, rates_on

UTILITY = "appalachian_power_west_virginia"
TIMEZONE = "America/New_York"
PLANS = ("RS", "SGS")
MAX_KW = {"RS":25., "SGS":9.9}
CONFIRMATIONS = {
    "eligibility_confirmed":"Appalachian Power confirmed West Virginia RS 015 or SGS 231 service",
    "ordinary_service_confirmed":"Ordinary bundled single-phase meter, no special rates, assistance, credits or optional programs",
    "full_monthly_charges_confirmed":"Complete calendar reading cycle with matching bill month and full monthly charge",
    "no_local_tax_confirmed":"Outside municipal boundaries and all local electric-tax districts, confirmed independently",
}


def account_fields(plan_id="RS"):
    result = [dict(name=k,type="boolean",required=True,label=v) for k,v in CONFIRMATIONS.items()]
    result += [
        dict(name="account_source",type="text",required=True,label="Utility assignment, ordinary service and tax-location evidence"),
        dict(name="der_ordinary_service_confirmed",type="boolean",label="Written Company agreement preserves ordinary import billing for this exact non-export PV/storage installation"),
        dict(name="der_activation_date",type="date",label="Final interconnection approval active by"),
        dict(name="der_eligibility_source",type="text",label="Exact equipment and ordinary-rate continuation agreement reference"),
    ]
    if plan_id=="SGS":
        result += [
            dict(name="sgs_capacity_requirements_kw",type="number",required=True,label="Independent maximum electrical capacity requirement, below 10 kW"),
            dict(name="sgs_assignment_confirmed",type="boolean",required=True,label="Company retains SGS 231 and confirms no pending reclassification"),
            dict(name="sgs_capacity_source",type="text",required=True,label="Company capacity-requirement and SGS assignment evidence"),
        ]
    return result


def defaults(plan_id="RS"):
    if plan_id not in PLANS:
        raise ValueError("Select Appalachian Power WV RS or SGS.")
    a = dict(tariff=plan_id,supply="bundled",export_mode="none",voltage="secondary",phase="single",
             voltage_v=240.,meter_count=1,opening_credit_usd=0.,tax_jurisdiction="wv_unincorporated",
             rate_evidence_mode="verified",billing_month="2026-10-01",bill_date="2026-10-31",
             cycle_kind="regular",cycle_source="",account_source="",der_ordinary_service_confirmed=False,
             der_activation_date="",der_eligibility_source="")
    a.update(dict.fromkeys(CONFIRMATIONS,False))
    if plan_id=="SGS":
        a.update(sgs_capacity_requirements_kw=None,sgs_assignment_confirmed=False,sgs_capacity_source="")
    return a


def hypothetical_defaults(plan_id="RS", *, day=None):
    a=defaults(plan_id)
    month=pd.Timestamp(day or a["billing_month"]).replace(day=1)
    a.update(dict.fromkeys(CONFIRMATIONS,True))
    a.update(hypothetical_account=True,billing_month=str(month.date()),
             bill_date=str((month+pd.offsets.MonthEnd()).date()),
             cycle_source="Hypothetical complete calendar meter reading and matching bill month",
             account_source="Hypothetical ordinary APCo WV account in an unincorporated area with no local electric tax",
             der_ordinary_service_confirmed=True,der_activation_date="2024-12-31",
             der_eligibility_source="Hypothetical written APCo agreement approving exact non-export PV and PV-charged storage, ordinary rates without other charges")
    if plan_id=="SGS":
        a.update(sgs_capacity_requirements_kw=5.,sgs_assignment_confirmed=True,
                 sgs_capacity_source="Hypothetical Company-confirmed 5 kW normal capacity requirement and retained SGS 231")
    return a


def catalog():
    return [
        dict(id=p,label="Appalachian Power WV "+p+(" (015)" if p=="RS" else " (231)"),
             customer_class="residential" if p=="RS" else "commercial",status="supported",
             coverage=[dict(start=s,end=e) for s,e in COVERAGE],
             coverage_gaps=[dict(start=s,end=e,reason=r) for s,e,r in GAPS],
             supply_arrangements=["bundled"],voltage="secondary",interval_minutes=[15],
             equipment_modes=["grid_only","pv_only","pv_battery"],solar_modes=["non_export"],
             representative_peak_kw=3. if p=="RS" else 5.,account_fields=account_fields(p),sources=SOURCES,
             eligibility="Company-confirmed ordinary West Virginia RS 015 or SGS 231, one single-phase secondary meter, independently confirmed unincorporated tax location.",
             limitations=["Only listed complete calendar cycles. State-regulated electricity is sales-tax exempt. Municipal taxes and optional programs are outside scope.",
                          "SGS requires independent capacity requirements below 10 kW and retained assignment.",
                          "PV and PV-charged paired storage require an explicit written agreement preserving ordinary import billing."])
        for p in PLANS
    ]


def _reference(a,key):
    value=a.get(key)
    if not isinstance(value,str) or not 1<=len(value.strip())<=500:
        raise ValueError("Document Appalachian Power WV "+key+" without personal identifiers.")


def cycle_review(a,index):
    idx=pd.DatetimeIndex(index)
    step=pd.Timedelta(minutes=15)
    if len(idx)<2 or str(idx.tz)!=TIMEZONE or idx.hasnans or not np.all(idx[1:]-idx[:-1]==step):
        raise ValueError("Appalachian Power WV requires complete consecutive Eastern 15-minute data.")
    first,last=idx[0],idx[-1]+step
    if (first!=first.normalize() or first.day!=1 or last!=first+pd.offsets.MonthBegin()
            or a.get("cycle_kind")!="regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Appalachian Power WV requires a complete calendar meter cycle and full monthly charges.")
    month,bill_date=str(first.date()),str(idx[-1].date())
    if a.get("billing_month")!=month or a.get("bill_date")!=bill_date:
        raise ValueError("Appalachian Power WV requires matching service and bill calendar months.")
    r,source,version,grade=rates_on(month,a["tariff"])
    return dict(service_start=month,service_end=bill_date,billing_month=month,bill_date=bill_date,
                elapsed_hours=float((last-first)/pd.Timedelta(hours=1)),source_version=version,source_grade=grade),r,source


def validate_account(a,index,equipment=None):
    if (not isinstance(a,dict) or a.get("tariff") not in PLANS
            or a.get("supply")!="bundled" or a.get("export_mode")!="none"):
        raise ValueError("Select Appalachian Power WV bundled RS/SGS and zero export.")
    if any(a.get(k) is not True for k in CONFIRMATIONS):
        raise ValueError("Confirm APCo WV assignment, ordinary service, full charges and no local electric tax.")
    expected=dict(voltage="secondary",phase="single",voltage_v=240.,meter_count=1,opening_credit_usd=0.,
                  tax_jurisdiction="wv_unincorporated",rate_evidence_mode="verified")
    if any(a.get(k)!=v or isinstance(a.get(k),bool) for k,v in expected.items()) or a.get("provisional_assumptions_accepted",False) is not False:
        raise ValueError("APCo WV supports verified ordinary single-phase secondary service in confirmed unincorporated locations.")
    for k in ("account_source","cycle_source"):_reference(a,k)
    cycle,_,_=cycle_review(a,index)
    if a["tariff"]=="SGS":
        capacity=a.get("sgs_capacity_requirements_kw")
        if a.get("sgs_assignment_confirmed") is not True or type(capacity) not in (int,float) or not 0<capacity<10.:
            raise ValueError("SGS requires independent Company-confirmed capacity requirements below 10 kW.")
        _reference(a,"sgs_capacity_source")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("PV/storage requires a written APCo WV ordinary-service non-export agreement.")
        _reference(a,"der_eligibility_source")
        date=a.get("der_activation_date")
        try:active=str(pd.Timestamp(date).date())==date and date<=cycle["service_start"]
        except (ValueError,TypeError):active=False
        if not active:
            raise ValueError("APCo WV approval must be active before the service cycle.")
        if equipment.get("battery") and (equipment.get("renewable_only_charging") is not True or equipment.get("no_battery_export") is not True):
            raise ValueError("APCo WV storage requires PV-only charging and zero export.")


def validate_native_load(a,load):
    if np.max(load)>MAX_KW[a["tariff"]]+1e-7:
        raise ValueError("APCo WV native load exceeds the declared study envelope. Modeled imports cannot determine SGS assignment.")


def validate_state(a,index,state=None,equipment=None):
    if state not in (None,{}):
        raise ValueError("APCo WV non-export service has no credit or demand state.")


def charge_lines(index,imports,exports,a,*,math,state=None):
    validate_state(a,index,state)
    cycle,r,source=cycle_review(a,index)
    cap=MAX_KW[a["tariff"]]
    if math.convex:math.constraints.extend([exports==0,imports<=cap])
    elif np.max(exports)>1e-5 or np.max(imports)>cap+1e-7:
        raise ValueError("APCo WV requires zero export and imports within the study limit.")
    energy=math.hours*math.sum(imports)
    if a["tariff"]=="RS":
        winter=int(cycle["billing_month"][5:7]) in (1,2,12)
        price=math.tiered(energy,(500.,1350.) if winter else (500.,),r["energy"] if winter else r["energy"][:2])
    else:price=energy*r["energy"][0]
    lines=dict(bundled_customer=r["customer"],bundled_base_energy=price,enec_including_crrc=energy*r["enec"],
               energy_efficiency=energy*r["energy_efficiency"],environmental_compliance=energy*r["environmental"],
               renewable_generation=energy*r["renewable_generation"],broadband=0.,business_ready_sites=0.,
               state_sales_tax=0.,local_tax=0.)
    return dict(lines=lines,next_state={},is_complete_bill=True,excluded_components=[],
                rate_sources=[source,TAX,DER],rate_evidence_status="verified",assumption_model=None,rate_assumptions=[],
                metrics={**cycle,"raw_import_kwh":energy,"billing_demand_applied":False,
                         "crrc_embedded_in_enec":True,"rounded_cash_optimum_claimed":False},
                warnings=["Filed ENEC includes CRRC. Base rates bundle supply and delivery.",
                          "Scope requires independent confirmation of no municipal or district electric tax.",
                          "Unrounded tariff arithmetic and component-rounded cents are retained."])
