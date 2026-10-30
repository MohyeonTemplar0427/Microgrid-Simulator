"""Duquesne RS and bounded, Company-retained non-demand GS default service.

Matching complete calendar cycles only. GS classification and the inactive
minimum-charge domain are independently constrained; PV cannot erase history.
"""
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd

from .duquesne_pa_rates import COVERAGE, PLANS, SOURCES, rates_on

TIMEZONE = "America/New_York"


def history_through(day):
    return str((pd.Timestamp(day).replace(day=1)-pd.offsets.MonthBegin()).date())


def account_fields(plan="RS"):
    fields = [
        ("eligibility_confirmed", "Duquesne Light Pennsylvania territory and actual RS/GS Company assignment independently confirmed"),
        ("ordinary_service_confirmed", "Ordinary established single-meter 120/240V single-phase service; no special contract, assistance, extra facilities or optional programs"),
        ("full_monthly_charges_confirmed", "Complete calendar meter cycles, billed on final service date; no partial/shifted-cycle approximation"),
        ("fixed_default_supply_confirmed", "Company-confirmed Rider8 fixed default supply and AppendixA transmission; no TOU, hourly, shopping or medium-class supply"),
        ("local_charges_confirmed", "Ordinary Pennsylvania state-only jurisdiction outside Allegheny/Philadelphia; no extra local tax or exemption"),
        ("solely_residential_use_confirmed", "RS: solely residential use; same-meter business/mixed-use tax treatment is excluded"),
        ("gs_small_confirmed", "GS: Company-retained established non-demand class throughout proposed operation; annual assignment/history independently reviewed"),
        ("gs_no_demand_minimum_confirmed", "GS: continuous non-demand service, no prior GM/priced demand, contract minimum or carried eleven-month demand-minimum obligation"),
        ("der_ordinary_service_confirmed", "PV/storage: already-active qualifying Rider21 ordinary renewable approval and required metering; non-export study"),
    ]
    return [dict(name=k,type="boolean",default=False,label=v) for k,v in fields] + [
        dict(name="supply",type="choice",choices=["default_ptc"],label="Fixed default service: Rider8 DSS plus AppendixA transmission, each once"),
        dict(name="tax_jurisdiction",type="choice",choices=["pa_state_only"],label="State-only ordinary tax jurisdiction; no Allegheny/Philadelphia or special exemption"),
        *[dict(name=k,type="text",label=v) for k,v in (
            ("supply_source","Company supply/classification evidence including relevant October/January review; no inference from a wholesale node"),
            ("tax_source","Solely residential exemption or ordinary commercial 6% state sales-tax jurisdiction evidence"),
            ("cycle_source","Meter-cycle evidence or explicit hypothetical full calendar cycle"),
            ("gs_qualification_source","Company GS assignment, preceding twelve-month usage/peak bounds and no historical demand-minimum evidence"),
            ("der_eligibility_source","Active qualifying renewable PV/storage approval, metering and ordinary tariff treatment; no export settlement inferred"))],
        dict(name="gs_qualification_upper_bound_kwh",type="number",label="GS independent preceding twelve monthly native/qualification quantities upper bound, at most1000kWh"),
        dict(name="gs_prior_peak_upper_bound_kw",type="number",label="GS independent preceding twelve monthly known/billing-demand upper bound, at most5kW"),
        dict(name="gs_history_through_month",type="date",label="GS qualification history through immediately preceding month (first day)"),
        dict(name="der_activation_date",type="date",label="Approved ordinary renewable service/metering active on or before service start"),
        dict(name="rate_evidence_mode",type="choice",choices=["verified"],label="Verified dated components only; no provisional price or unsupported minimum fallback"),
    ]


def defaults(plan="RS"):
    if plan not in PLANS:raise ValueError("Select Duquesne RS or non-demand GS fixed default service.")
    return dict(tariff=plan,supply="default_ptc",export_mode="none",eligibility_confirmed=False,
        ordinary_service_confirmed=False,full_monthly_charges_confirmed=False,fixed_default_supply_confirmed=False,
        local_charges_confirmed=False,solely_residential_use_confirmed=False,gs_small_confirmed=False,
        gs_no_demand_minimum_confirmed=False,supply_source="",tax_jurisdiction="pa_state_only",tax_exempt=False,
        tax_source="",cycle_source="",billing_month="2026-06-01",bill_date="2026-06-30",cycle_kind="regular",
        voltage="secondary",phase="single",voltage_v=240.,power_factor=1.,meter_count=1,service_line_count=1,
        opening_credit_usd=0.,demand_interval_minutes=15,
        gs_qualification_upper_bound_kwh=None if plan=="RS" else 1000.,
        gs_prior_peak_upper_bound_kw=None if plan=="RS" else 5.,
        gs_history_through_month="" if plan=="RS" else "2026-05-01",gs_qualification_source="",
        der_ordinary_service_confirmed=False,der_activation_date="",der_eligibility_source="",
        rate_evidence_mode="verified",provisional_assumptions_accepted=False,hypothetical_account=False)


def hypothetical_defaults(plan="RS",day="2026-06-01"):
    a=defaults(plan);start=pd.Timestamp(day).replace(day=1)
    for k in ("eligibility_confirmed","ordinary_service_confirmed","full_monthly_charges_confirmed",
              "fixed_default_supply_confirmed","local_charges_confirmed","der_ordinary_service_confirmed","hypothetical_account"):
        a[k]=True
    a.update(billing_month=str(start.date()),bill_date=str((start+pd.offsets.MonthEnd()).date()),
        solely_residential_use_confirmed=plan=="RS",
        supply_source="Explicit hypothetical Company-confirmed ordinary Duquesne fixed default service including all relevant annual small-CI classification reviews; no TOU, shopping or hourly service",
        cycle_source="Explicit hypothetical complete calendar service cycle, bill rendered on final service date; not an actual customer meter schedule",
        tax_source="Explicit hypothetical solely residential Pennsylvania exemption" if plan=="RS" else "Explicit hypothetical ordinary taxable business in Center Township, Beaver County; state-only6%, no special exemption/local surcharge",
        der_activation_date="2024-12-01",der_eligibility_source="Explicit hypothetical already-active qualifying Rider21 renewable PV/storage approval and metering under ordinary RS/GS; PV-only storage charging, no exports or bank")
    if plan=="GS":a.update(gs_small_confirmed=True,gs_no_demand_minimum_confirmed=True,
        gs_history_through_month=history_through(day),gs_qualification_source="Explicit hypothetical Company-retained established non-demand GS throughout preceding history/proposed operation; every preceding12native/qualification month<=1000kWh and known/billing peak<=5kW; no priorGM, priced demand, contract minimum or carried demand-minimum obligation")
    return a


def catalog():
    return [dict(id=p,label="Duquesne PA "+("RS residential" if p=="RS" else "GS small non-demand")+" fixed default supply",
        status="supported",customer_class="residential" if p=="RS" else "commercial",voltage="secondary",
        coverage=[dict(start=s,end=e) for s,e in COVERAGE],interval_minutes=[15],solar_modes=["non_export"],
        supply_arrangements=["default_ptc"],equipment_modes=["grid_only","pv_only","pv_battery"],
        representative_peak_kw=3. if p=="RS" else 2.5,account_fields=account_fields(p),sources=SOURCES,
        eligibility="Company-confirmed ordinary solely residential RS or established non-demand GS, fixed default supply, state-only taxes, complete matching calendar cycles and active ordinary renewable approval where present.",
        limitations=[
            "Verified complete calendar cycles only; no shifted/partial-cycle allocation, alternative suppliers, TOU/hourly supply, primary/three-phase service or special contracts.",
            "GS Company twelve-month assignment and supply-review histories are independent. Initial conservative preceding/current native/import month bounds<=1000kWh and15-minute peak<=5kW keep reclassification inactive; these are not eligibility inferred from optimized imports.",
            "GS low-import minimum-charge treatment remains unverified. Cases outside the declared inactive-minimum domain reject after rebilling; no forced purchases, invented demand rate or minimum charge is applied.",
            "DSS and AppendixA transmission use exact filed prices, not rounded website PTC; both already include GRT. No wholesale LMP/PLC/NSPL or duplicate administration/transmission adder.",
            "DSIC uses the bill-rendered date and excludes STAS and retail supply/transmission; TSC is excluded from STAS and the minimum. Ordinary sales-tax6% applies to taxable GS; solely residential RS is exempt. Allegheny/Philadelphia and special exemptions unsupported.",
            "Active approved ordinary renewable service only; PV-only storage charging, zero exports/bank. No standalone battery, export credit, NEM true-up or surveyed-site engineering claim."])
        for p in PLANS]


def _reference(a,key):
    if not isinstance(a.get(key),str) or not 1<=len(a[key].strip())<=500:raise ValueError("Document Duquesne "+key+" without personal identifiers.")


def _bound(value,maximum):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and np.isfinite(value) and 0.<=value<=maximum


def cycle_review(a,index):
    idx=pd.DatetimeIndex(index)
    if len(idx)<2 or str(idx.tz)!=TIMEZONE or not np.all(idx[1:]-idx[:-1]==pd.Timedelta(minutes=15)):
        raise ValueError("Duquesne requires complete consecutive America/New_York15-minute intervals; no missing, duplicate or hourly substitutes.")
    stop=idx[-1]+pd.Timedelta(minutes=15)
    if idx[0]!=idx[0].normalize() or idx[0].day!=1 or stop!=idx[0]+pd.offsets.MonthBegin() or a.get("cycle_kind")!="regular" or a.get("full_monthly_charges_confirmed") is not True:
        raise ValueError("Duquesne initial scope requires a complete calendar meter cycle; partial/shifted proration is unverified.")
    if a.get("billing_month")!=str(idx[0].date()) or a.get("bill_date")!=str(idx[-1].date()):
        raise ValueError("Duquesne calendar billing month and explicit final-day bill-rendered date must match service.")
    if a.get("rate_evidence_mode","verified")!="verified" or a.get("provisional_assumptions_accepted",False) is not False:
        raise ValueError("Duquesne has no provisional-rate or minimum-charge assumption mode.")
    first=rates_on(idx[0].date(),a["tariff"],bill_date=a["bill_date"])
    if first!=rates_on(idx[-1].date(),a["tariff"],bill_date=a["bill_date"]):
        raise ValueError("Duquesne component versions cross inside the cycle; allocation is unverified.")
    return dict(service_start=str(idx[0].date()),service_end=str(idx[-1].date()),billing_month=a["billing_month"],
        bill_date=a["bill_date"],cycle_days=(stop.date()-idx[0].date()).days,elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)),
        monthly_charge_factor=1.,partial_period_proration_applied=False)


def evidence(index,account):
    cycle_review(account,index)
    return dict(rate_evidence_status="verified",assumption_model=None,rate_assumptions=[],objective_scope="complete_utility_bill")


def validate_account(a,index,equipment=None):
    if not isinstance(a,dict) or a.get("tariff") not in PLANS or a.get("supply")!="default_ptc" or a.get("export_mode")!="none":
        raise ValueError("Select ordinary Duquesne RS/GS fixed default supply and no export.")
    for k in ("eligibility_confirmed","ordinary_service_confirmed","full_monthly_charges_confirmed","fixed_default_supply_confirmed","local_charges_confirmed"):
        if a.get(k) is not True:raise ValueError("Confirm Duquesne ordinary service, Company class/default supply, tax and full cycles independently.")
    for k in ("supply_source","tax_source","cycle_source"):_reference(a,k)
    expected=dict(tax_jurisdiction="pa_state_only",tax_exempt=False,voltage="secondary",phase="single",voltage_v=240.,power_factor=1.,meter_count=1,service_line_count=1,opening_credit_usd=0.,demand_interval_minutes=15)
    if any(a.get(k)!=v or type(a.get(k)) is bool and type(v) is not bool or type(v) is bool and a.get(k) is not v for k,v in expected.items()):
        raise ValueError("Duquesne initial scope is one120/240V single-phase secondary meter, ordinary state-only taxes, unity billing PF and no bank.")
    cycle_review(a,index)
    if a["tariff"]=="RS":
        if a.get("solely_residential_use_confirmed") is not True or a.get("gs_small_confirmed") is not False or a.get("gs_no_demand_minimum_confirmed") is not False or a.get("gs_qualification_upper_bound_kwh") is not None or a.get("gs_prior_peak_upper_bound_kw") is not None or a.get("gs_history_through_month")!="" or a.get("gs_qualification_source")!="":
            raise ValueError("Duquesne RS scope is solely residential, without commercial history or mixed-use tax assumptions.")
    else:
        if a.get("solely_residential_use_confirmed") is not False or a.get("gs_small_confirmed") is not True or a.get("gs_no_demand_minimum_confirmed") is not True or not _bound(a.get("gs_qualification_upper_bound_kwh"),1000.) or not _bound(a.get("gs_prior_peak_upper_bound_kw"),5.):
            raise ValueError("Duquesne GS needs Company-retained non-demand assignment, independent prior12month<=1000kWh/5kW bounds and no inherited demand minimum.")
        _reference(a,"gs_qualification_source")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True:raise ValueError("Duquesne requires already-active qualifying ordinary renewable service; standalone storage is outside this scope.")
        _reference(a,"der_eligibility_source")
        try:valid=str(pd.Timestamp(a["der_activation_date"]).date())==a["der_activation_date"] and pd.Timestamp(a["der_activation_date"]).date()<=pd.DatetimeIndex(index)[0].date()
        except (ValueError,TypeError,KeyError):valid=False
        if not valid:raise ValueError("Duquesne renewable approval and required metering must already be active before service.")
        if equipment.get("battery") and (not equipment.get("renewable_only_charging") or not equipment.get("no_battery_export")):
            raise ValueError("Duquesne initial storage scope requires PV-only charging and no battery export.")
        if max(equipment.get("pv_dc_kw",0.),equipment.get("pv_ac_kw",0.))+equipment.get("battery_kw",0.)>25.+1e-8:
            raise ValueError("Duquesne combined study output is bounded at25kW; this does not establish renewable/interconnection eligibility.")


def validate_state(a,index,state=None,equipment=None):
    if a["tariff"]=="RS":
        if state not in (None,{}):raise ValueError("Duquesne RS has no modeled opening credit or demand state.")
        return
    prior=history_through(pd.DatetimeIndex(index)[0])
    if state in (None,{}):
        if a.get("gs_history_through_month")!=prior:raise ValueError("Duquesne initial GS history must end immediately before the study.")
    elif not isinstance(state,dict) or set(state)!={"through_month","gs_qualification_upper_bound_kwh","gs_peak_upper_bound_kw"} or state["through_month"]!=prior or not _bound(state["gs_qualification_upper_bound_kwh"],1000.) or not _bound(state["gs_peak_upper_bound_kw"],5.):
        raise ValueError("Duquesne GS carried history must have adjacent months and retained native/qualification bounds; no reset or gap.")


def charge_lines(index,imports,exports,a,*,math,state=None):
    validate_state(a,index,state);cycle=cycle_review(a,index);r=rates_on(cycle["service_start"],a["tariff"],bill_date=a["bill_date"]);res=a["tariff"]=="RS"
    if math.convex:math.constraints.append(exports==0)
    elif np.max(exports)>1e-5:raise ValueError("Duquesne export settlement is not implemented; exports must be zero.")
    energy=math.hours*math.sum(imports);peak=math.demand(imports,index,minutes=15)
    if not res:
        if math.convex:math.constraints.extend([energy<=1000.,peak<=5.])
        elif energy>1000.+1e-7 or peak>5.+1e-7:raise ValueError("Duquesne GS initial inactive-reclassification domain bounds imported cycle energy<=1000kWh and15-minute peak<=5kW.")
    lines=dict(distribution_customer=r["customer"],distribution_energy=energy*r["distribution_kwh"],
        retail_market_enhancement=r["rmes"],universal_service=energy*r["usc_kwh"],energy_efficiency=energy*r["eec_kwh"],smart_meter=r["smart_meter"])
    distribution=sum(lines.values());lines["distribution_dsic"]=distribution*r["dsic_fraction"]
    stas1_basis=distribution+lines["distribution_dsic"];lines["distribution_state_tax_adjustment"]=stas1_basis*r["stas_distribution_fraction"]
    lines["default_service_supply"]=energy*r["dss_kwh"]
    stas2_basis=sum(lines.values());lines["all_service_state_tax_adjustment"]=stas2_basis*r["stas_all_fraction"]
    lines["retail_transmission"]=energy*r["tsc_kwh"] # AppendixA excludes TSC from STAS/minimum.
    if not res and not math.convex:
        # A postsolve domain rejection, never a forced-purchase constraint or
        # invented GS demand/minimum bill. Both readings of the filed paragraph
        # are inactive inside the separately documented conservative envelope.
        before=r["customer"]+energy*r["distribution_kwh"]
        after=stas1_basis+lines["distribution_state_tax_adjustment"]
        before_dsic_cents=sum(Decimal(str(lines[k])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) for k in ("distribution_customer","distribution_energy","retail_market_enhancement","universal_service","energy_efficiency","smart_meter"))
        cents=sum(Decimal(str(v)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) for k,v in lines.items() if k not in ("default_service_supply","all_service_state_tax_adjustment","retail_transmission"))
        if min(before,distribution,after)<2*r["customer"]-1e-7 or min(before_dsic_cents,cents)<Decimal(str(2*r["customer"])):
            raise ValueError("Duquesne GS low-import minimum-charge treatment is unverified outside the declared inactive domain; no forced purchases or invented minimum.")
    subtotal=sum(lines.values());lines["sales_tax"]=0. if res else subtotal*.06
    next_state={} if res else dict(through_month=a["billing_month"],gs_qualification_upper_bound_kwh=1000.,gs_peak_upper_bound_kw=5.)
    return dict(lines=lines,metrics={**cycle,"raw_import_kwh":energy,"actual_15_minute_peak_kw":peak,"rates":r,
        "dsic_basis_usd":distribution,"stas_distribution_basis_usd":stas1_basis,"stas_all_basis_usd":stas2_basis,
        "sales_tax_rate":0. if res else .06,"tax_jurisdiction":a["tax_jurisdiction"],
        "quantity_basis":"raw_interval_energy_no_unsourced_meter_rounding","rounded_cash_optimum_claimed":False,
        "additional_grt_percentage_applied":False,"minimum_charge_domain":"ordinary_RS" if res else "restricted_inactive_GS_ambiguity_bound_no_minimum_added",
        "gs_classification_basis":"Company assignment and independent preceding history; bounded native/import envelope, not inferred from PV" if not res else None,
        "capacity_transmission_treatment":"Fixed DSS includes capacity/admin/PJM/losses/GRT; AppendixA TSC separately once, includes GRT and is excluded from STAS/minimum; no wholesale adder",
        "source_versions":r["source_versions"]},next_state=next_state,is_complete_bill=True,excluded_components=[],
        rate_evidence_status="verified",assumption_model=None,rate_assumptions=[],rate_sources=SOURCES,
        warnings=["Duquesne ordinary RS/GS default service, matching full calendar cycles and state-only jurisdiction; service and tax eligibility are not inferred from coordinates.",
            "GS is restricted to Company-retained non-demand service with independently confirmed history and no inherited priced demand/contract minimum. Low-import minimum cases reject; no demand rate or minimum amount is invented or forced into dispatch.",
            "Exact filed DSS and TSC are charged separately; website class-average PTC rounding is not the billing rate. GRT/capacity/admin are included once; no PJM wholesale price/tag adder.",
            "PV/storage requires already-active ordinary qualifying renewable approval; PV-only charging, no exports or credit bank. No actual customer invoice, rounded-cash optimum, annual joint optimum or site-specific electrical claim."])
