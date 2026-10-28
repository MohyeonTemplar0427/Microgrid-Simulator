"""Penelec district ordinary RS / bounded GS-Small default PTC.

GS-S native/import envelopes preserve an inactive reclassification domain;
Company assignment remains independent of optimized purchases. January2025
commercial prior-refund sales-tax adjustment is explicitly unverified.
"""
from decimal import Decimal,ROUND_HALF_UP
import numpy as np
import pandas as pd

from .penelec_pa_rates import COVERAGE,PLANS,SOURCES,rates_on

TIMEZONE="America/New_York"
JANUARY_GS_EXCLUSION="january_2025_refund_prior_sales_tax_adjustment"


def history_through(day):
    return str((pd.Timestamp(day).replace(day=1)-pd.offsets.MonthBegin()).date())


def account_fields(plan="RS"):
    return [
        dict(name="eligibility_confirmed",type="boolean",label="FirstEnergy PA Penelec rate district and selected RS/GS-S class independently confirmed"),
        dict(name="ordinary_service_confirmed",type="boolean",label="Established ordinary continuous single-meter secondary service; "+("one residential dwelling, no multiunit/farm provisions; " if plan=="RS" else "actual metered nonresidential service; ")+"no special contract, early termination or extra fees"),
        dict(name="full_monthly_charges_confirmed",type="boolean",label="Complete ordinary calendar meter cycles and monthly charges independently confirmed"),
        dict(name="supply",type="choice",choices=["default_ptc"],label="Penelec default Price-to-Compare supply; no TOU, hourly, GSDS or alternative supplier"),
        dict(name="ptc_review_confirmed",type="boolean",label="Company-reviewed ordinary class/default PTC assignment; no wholesale PLC inference"),
        dict(name="supply_source",type="text",label="Default supply and classification evidence or explicit hypothetical account facts"),
        dict(name="tax_jurisdiction",type="choice",choices=["pa_state_only"],label="Ordinary PA state-only tax jurisdiction; no Philadelphia/Allegheny or special exemption"),
        dict(name="tax_source",type="text",label="RS solely residential exemption or GS-S ordinary business current-charge 6% sales-tax evidence"),
        dict(name="solely_residential_use_confirmed",type="boolean",label="RS: solely residential use; mixed business use is outside the exemption scope"),
        dict(name="rs_special_demand_inactive_confirmed",type="boolean",label="RS: Company confirms no current or inherited special-demand/excess-demand ratchet charge"),
        dict(name="rs_prior_11_peak_upper_bound_kw",type="number",label="RS independent preceding eleven 15-minute peak upper bound, at most 25 kW"),
        dict(name="rs_history_through_month",type="date",label="RS peak/ratchet history through immediately preceding month (first day)"),
        dict(name="rs_demand_source",type="text",label="RS utility peak/history and inactive excess-demand confirmation; no inference from PV-reduced demand"),
        dict(name="no_special_rates_confirmed",type="boolean",label="No CAP/PCAP, special heating, volunteer/fire, borderline, legacy or private-contract rates"),
        dict(name="cycle_source",type="text",label="Actual meter-cycle evidence or explicitly hypothetical complete calendar cycle"),
        dict(name="gs_small_confirmed",type="boolean",label="GS-S: utility-assigned existing non-demand class retained throughout proposed operation"),
        dict(name="gs_qualification_upper_bound_kwh",type="number",label="GS-S independent preceding twelve-month qualification-quantity upper bound, at most 1500 kWh"),
        dict(name="gs_history_through_month",type="date",label="GS-S initial qualification history through immediately preceding month (first day)"),
        dict(name="gs_qualification_source",type="text",label="Company classification/history and retained eligibility evidence; quantity predicate not inferred from PV-reduced net imports"),
        dict(name="gs_fixed_imputed_usage_excluded_confirmed",type="boolean",label="GS-S: ordinary actual metered usage; Company fixed/imputed-usage provision C excluded"),
        dict(name="gs_no_demand_meter_confirmed",type="boolean",label="GS-S: Company confirms ordinary service without a demand meter"),
        dict(name="january_refund_eligibility_confirmed",type="boolean",label="January 2025: established account independently entitled to the Penelec one-time prior-cost refund"),
        dict(name="refund_eligibility_source",type="text",label="January 2025 account entitlement/posting evidence or explicit hypothetical existing-account facts"),
        dict(name="refund_represented_before_study",type="boolean",label="January 2025 one-time refund already represented in imported model state"),
        dict(name="der_ordinary_service_confirmed",type="boolean",label="Already-active qualifying ordinary customer-generator/NEM approval, no Partial Services Rider; zero exports and bank"),
        dict(name="der_activation_date",type="date",label="Actual approved ordinary renewable service activation date before the cycle"),
        dict(name="der_eligibility_source",type="text",label="Executed qualifying renewable PV/storage approval, required metering and PV-only battery charging/no battery export"),
        dict(name="rate_evidence_mode",type="choice",choices=["verified"],label="Verified dated components only; January 2025 GS refund-tax gap remains a subtotal"),
    ]


def defaults(plan="RS"):
    if plan not in PLANS:raise ValueError("Select Penelec RS or GS-Small default PTC.")
    res=plan=="RS"
    return dict(tariff=plan,supply="default_ptc",export_mode="none",eligibility_confirmed=False,
        ordinary_service_confirmed=False,full_monthly_charges_confirmed=False,ptc_review_confirmed=False,supply_source="",
        tax_jurisdiction="pa_state_only",tax_source="",tax_exempt=False,solely_residential_use_confirmed=False,
        rs_special_demand_inactive_confirmed=False,rs_prior_11_peak_upper_bound_kw=25. if res else None,rs_history_through_month="2026-05-01" if res else "",rs_demand_source="",
        no_special_rates_confirmed=False,cycle_source="",billing_month="2026-06-01",bill_date="2026-06-30",cycle_kind="regular",
        voltage="secondary",phase="single",voltage_v=240.,power_factor=1.,meter_count=1,service_line_count=1,
        opening_credit_usd=0.,demand_interval_minutes=15,metering="ordinary_residential" if res else "non_demand_billed",
        gs_small_confirmed=False,gs_qualification_upper_bound_kwh=None if res else 1500.,gs_history_through_month="" if res else "2026-05-01",gs_qualification_source="",
        gs_fixed_imputed_usage_excluded_confirmed=False,gs_no_demand_meter_confirmed=False,january_refund_eligibility_confirmed=False,refund_eligibility_source="",
        refund_represented_before_study=False,der_ordinary_service_confirmed=False,der_activation_date="",der_eligibility_source="",
        rate_evidence_mode="verified",provisional_assumptions_accepted=False,hypothetical_account=False)


def hypothetical_defaults(plan="RS",day="2026-06-01"):
    a=defaults(plan);start=pd.Timestamp(day).replace(day=1)
    a.update(eligibility_confirmed=True,ordinary_service_confirmed=True,full_monthly_charges_confirmed=True,
        ptc_review_confirmed=True,no_special_rates_confirmed=True,hypothetical_account=True,
        solely_residential_use_confirmed=plan=="RS",billing_month=str(start.date()),bill_date=str((start+pd.offsets.MonthEnd()).date()),
        supply_source="Explicit hypothetical Company-confirmed Penelec ordinary default PTC, no alternative supplier/TOU/HP/GSDS or special rates; no wholesale PLC inference",
        cycle_source="Explicit hypothetical complete ordinary calendar meter cycles, not actual customer reading dates",
        tax_source="Explicit hypothetical solely residential statutory exemption" if plan=="RS" else "Explicit hypothetical ordinary PA state-only business current charges taxed6%, no exemption; January2025 prior-refund tax adjustment remains excluded",
        der_ordinary_service_confirmed=True,der_activation_date="2024-12-01",
        der_eligibility_source="Explicit hypothetical already-active qualifying renewable customer-generator ordinary NEM/PV-storage approval and metering, exempt from Partial Services Rider, PV-only charging/no battery export and zero export/bank")
    a.update(january_refund_eligibility_confirmed=str(start.date())=="2025-01-01",refund_eligibility_source="Explicit hypothetical established eligible Penelec account entitled to the January2025 prior-cost refund" if str(start.date())=="2025-01-01" else "")
    if plan=="GS-S":a.update(gs_small_confirmed=True,gs_fixed_imputed_usage_excluded_confirmed=True,gs_no_demand_meter_confirmed=True,gs_history_through_month=history_through(day),
        gs_qualification_source="Explicit hypothetical Company-retained existing Penelec GS-S assignment without demand meter across proposed operation; actual meter readings, no fixed/imputed-usage provision C or early contract termination; independent preceding12qualification quantities at most1500kWh, no requalification from optimized net imports")
    else:a.update(rs_special_demand_inactive_confirmed=True,rs_history_through_month=history_through(day),
        rs_demand_source="Explicit hypothetical Company-confirmed prior eleven actual15-minute peaks at most25kW, no inherited excess-demand ratchet; proposed native/import peaks remain in the inactive envelope, not derived eligibility from PV")
    return a


def catalog():
    rows=[]
    for plan in PLANS:
        coverage=[dict(start=s,end=e,is_complete_bill=True) for s,e in COVERAGE]
        if plan=="GS-S":coverage=[dict(start="2025-01-01",end="2025-01-31",is_complete_bill=False,excluded_components=[JANUARY_GS_EXCLUSION],scope="Verified current charges and known refund; prior-refund sales-tax adjustment unverified"),dict(start="2025-02-01",end="2026-06-30",is_complete_bill=True),dict(start="2026-10-01",end="2026-10-31",is_complete_bill=True)]
        rows.append(dict(id=plan,label="Penelec PA "+("RS residential default PTC" if plan=="RS" else "GS-Small non-demand default PTC"),status="supported",customer_class="residential" if plan=="RS" else "commercial",voltage="secondary",
            coverage=coverage,interval_minutes=[15],solar_modes=["non_export"],supply_arrangements=["default_ptc"],equipment_modes=["grid_only","pv_only","pv_battery"],representative_peak_kw=3.,account_fields=account_fields(plan),sources=SOURCES,
            eligibility="Confirmed Penelec solely residential RS or ordinary taxable/state-only Company-retained existing GS-Small; complete calendar cycles and approved active qualifying renewable service where present.",
            limitations=[
                "Verified2025,January–June2026 andOctober2026 only; July–September2026 DSIC is missing and rejects. Complete calendar cycles only; no irregular proration or cross-month allocation.",
                "January2025 GS-S is a verified-charge subtotal: known current-tax6% plus known3.42refund once, excluding unverified prior-refund sales-tax adjustment. No complete January commercial invoice or full-year complete commercial amount-due claim.",
                "GS-S Company assignment/history remains independent. The initial declared domain requires preceding12qualification/native/currentimport quantities at most1500kWh; this is a conservative inactive-reclassification envelope, not the tariff's automatic monthly eligibility rule or a net-vs-native interpretation.",
                "RS requires independent prior11peak bounds at most25kW and inactive excess-demand/ratchet confirmation; native and actual15-minute imports are bounded at25kW. No history is erased by PV.",
                "LEDC is mandatory on every class billing unit, not conditional on customer lighting conversion; Apr2025/Apr2026 dated versions apply once in DSIC/STAS/current-tax bases. JanMar2025 non-applicability is an explicitly disclosed first-April-window interpretation, not a filed zero-priced row.",
                "Positive3.04%TCJAJuly–December2025, district-specific STAS/DSIC/DSS/USC/EEC/SMT and mandatoryJanuaryrefund retained. PTC GRT/admin embedded; no extraLMP/PLC charge. JanMaySPVcredit applies to RS/GS-S even with PV; no large-class waiver copied.",
                "Current tariff raw/component-cent subtotal must meet the customer amount as a narrower inactive-minimum domain. Unknown floor cases reject without forced imports; refund is never clipped or included in STAS basis.",
                "Already-active qualifying renewable NEM/ordinary PV-storage approval and no Partial Services Rider; PV-only charging, no exports/bank, no standalone battery or unsupported export settlement. Study capacity bound is not approval.",
                "No exact printed/rounded-cash invoice, joint annual optimum, actual customer savings or surveyed-site electrical/interconnection approval claim."]))
    return rows


def _reference(a,key):
    if not isinstance(a.get(key),str) or not a[key].strip():raise ValueError("Document Penelec account fact: "+key)


def _bound(v):
    return not isinstance(v,bool) and isinstance(v,(int,float)) and np.isfinite(v) and 0.<=v<=1500.


def cycle_review(a,index):
    idx=pd.DatetimeIndex(index);step=pd.Timedelta(minutes=15)
    if len(idx)<2 or str(idx.tz)!=TIMEZONE or not np.all(idx[1:]-idx[:-1]==step):raise ValueError("Penelec needs consecutive America/New_York15-minute intervals; missing/duplicate/naive/hourly data reject.")
    start=idx[0];stop=idx[-1]+step
    if start!=start.normalize() or start.day!=1 or stop!=start+pd.offsets.MonthBegin() or a.get("cycle_kind")!="regular" or a.get("full_monthly_charges_confirmed") is not True or a.get("billing_month")!=str(start.date()) or a.get("bill_date")!=str(idx[-1].date()):
        raise ValueError("Penelec initial scope requires matching complete ordinary calendar cycles and final-day bill dates; partial/shifted proration rejects.")
    rates_on(str(start.date()),a["tariff"]);rates_on(str(idx[-1].date()),a["tariff"])
    return dict(service_start=str(start.date()),service_end=str(idx[-1].date()),billing_month=a["billing_month"],bill_date=a["bill_date"],cycle_days=(stop.date()-start.date()).days,elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)),monthly_charge_factor=1.,partial_period_proration_applied=False)


def validate_account(a,index,equipment=None):
    if not isinstance(a,dict) or a.get("tariff") not in PLANS or a.get("supply")!="default_ptc" or a.get("export_mode")!="none":raise ValueError("Select Penelec RS/GS-S ordinary default PTC with zero export.")
    if set(a)-set(defaults(a["tariff"])) or a.get("rate_evidence_mode")!="verified" or a.get("provisional_assumptions_accepted") is not False:raise ValueError("Penelec has no unknown-field/provisional/missing-price fallback.")
    for k in ("eligibility_confirmed","ordinary_service_confirmed","full_monthly_charges_confirmed","ptc_review_confirmed","no_special_rates_confirmed"):
        if a.get(k) is not True:raise ValueError("Confirm Penelec district, ordinary calendar service and default PTC independently.")
    for k in ("supply_source","tax_source","cycle_source"):_reference(a,k)
    expected=dict(tax_jurisdiction="pa_state_only",tax_exempt=False,voltage="secondary",phase="single",voltage_v=240.,power_factor=1.,meter_count=1,service_line_count=1,opening_credit_usd=0.,demand_interval_minutes=15)
    if any(a.get(k)!=v or type(a.get(k)) is bool and type(v) is not bool or type(v) is bool and a.get(k) is not v for k,v in expected.items()):raise ValueError("Penelec scope is ordinary PA state-only tax, one120/240V single-phase secondary service, unity billing PF and no bank.")
    if type(a.get("refund_represented_before_study")) is not bool:raise ValueError("Penelec refund model-state flag must be boolean.")
    cycle_review(a,index)
    if type(a.get("january_refund_eligibility_confirmed")) is not bool:raise ValueError("Penelec refund entitlement assertion must be boolean.")
    if a["bill_date"][:7]=="2025-01":
        if a.get("january_refund_eligibility_confirmed") is not True:raise ValueError("Confirm independent Penelec January2025 refund entitlement; it is not inferred from a simulation.")
        _reference(a,"refund_eligibility_source")
    if a["tariff"]=="RS":
        if a.get("gs_fixed_imputed_usage_excluded_confirmed") is not False or a.get("gs_no_demand_meter_confirmed") is not False:raise ValueError("Penelec RS has no GS fixed-usage/demand-meter assertions.")
        if a.get("solely_residential_use_confirmed") is not True or a.get("metering")!="ordinary_residential" or a.get("gs_small_confirmed") is not False or a.get("gs_qualification_upper_bound_kwh") is not None or a.get("gs_history_through_month")!="" or a.get("gs_qualification_source")!="":raise ValueError("Penelec RS tax scope requires solely residential use and no GS qualification assertions.")
        value=a.get("rs_prior_11_peak_upper_bound_kw")
        if a.get("rs_special_demand_inactive_confirmed") is not True or isinstance(value,bool) or not isinstance(value,(int,float)) or not np.isfinite(value) or not 0.<=value<=25.:raise ValueError("Penelec RS needs independent prior11peak bound at most25kW and inactive excess-demand/ratchet confirmation.")
        _reference(a,"rs_demand_source")
    else:
        if a.get("solely_residential_use_confirmed") is not False or a.get("metering")!="non_demand_billed" or a.get("gs_small_confirmed") is not True or not _bound(a.get("gs_qualification_upper_bound_kwh")):raise ValueError("GS-S requires independent retained non-demand Company classification and preceding12qualification upper bound at most1500kWh; not inferred from optimized load.")
        _reference(a,"gs_qualification_source")
        if a.get("rs_special_demand_inactive_confirmed") is not False or a.get("rs_prior_11_peak_upper_bound_kw") is not None or a.get("rs_history_through_month")!="" or a.get("rs_demand_source")!="":raise ValueError("GS-S has no RS special-demand assertions.")
    if a["tariff"]=="GS-S" and (a.get("gs_fixed_imputed_usage_excluded_confirmed") is not True or a.get("gs_no_demand_meter_confirmed") is not True):raise ValueError("Penelec GS-S requires actual metered usage and Company-confirmed absence of a demand meter; fixed/imputed usage rejects.")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True:raise ValueError("Penelec needs already-active qualifying ordinary renewable PV/storage NEM approval with no Partial Services Rider; no standalone storage.")
        _reference(a,"der_eligibility_source")
        try:
            active=pd.Timestamp(a["der_activation_date"]);valid=str(active.date())==a["der_activation_date"] and active.date()<=pd.DatetimeIndex(index)[0].date()
        except (ValueError,TypeError,KeyError):valid=False
        if not valid:raise ValueError("Penelec ordinary DER approval/metering must already be active before the cycle.")
        if equipment.get("battery") and (not equipment.get("renewable_only_charging") or not equipment.get("no_battery_export")):raise ValueError("Penelec initial storage scope is PV-only charging and no battery export.")
        if max(equipment.get("pv_dc_kw",0.),equipment.get("pv_ac_kw",0.))+equipment.get("battery_kw",0.)>25.+1e-8:raise ValueError("Penelec combined study output is at most25kW; this is not an eligibility/Partial Services exemption.")


def validate_state(a,index,state=None,equipment=None):
    prior=history_through(pd.DatetimeIndex(index)[0]);gs=a["tariff"]=="GS-S"
    if state in (None,{}):
        if a.get("gs_history_through_month" if gs else "rs_history_through_month")!=prior:raise ValueError("Penelec initial independent qualification/demand history must end immediately before the study.")
        return
    keys={"january_refund_applied","through_month"}|({"gs_qualification_upper_bound_kwh"} if gs else {"rs_peak_upper_bound_kw"})
    if not isinstance(state,dict) or set(state)!=keys or type(state["january_refund_applied"]) is not bool or state["through_month"]!=prior or gs and not _bound(state["gs_qualification_upper_bound_kwh"]):raise ValueError("Penelec carried state needs adjacent months, a boolean refund flag and unchanged conservative GS qualification domain; no reset/gaps.")
    if not gs:
        value=state["rs_peak_upper_bound_kw"]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not np.isfinite(value) or not 0.<=value<=25.:raise ValueError("Penelec RS carried peak envelope must retain inactive excess-demand history at most25kW.")


def charge_lines(index,imports,exports,a,*,math,state=None):
    cycle=cycle_review(a,index);validate_state(a,index,state=state);r=rates_on(cycle["service_start"],a["tariff"]);res=a["tariff"]=="RS"
    if math.convex:math.constraints.append(exports==0)
    elif np.max(exports)>1e-5:raise ValueError("Penelec export credit/banking settlement is unimplemented; exports must be zero.")
    energy=math.hours*math.sum(imports)
    peak=math.demand(imports,index,minutes=15)
    if res:
        if math.convex:math.constraints.append(peak<=25.)
        elif peak>25.+1e-7:raise ValueError("Penelec RS actual15-minute imports exceed the inactive special-demand25kW envelope.")
    else:
        if math.convex:math.constraints.append(energy<=1500.)
        elif energy>1500.+1e-7:raise ValueError("Penelec GS-S initial inactive-reclassification envelope bounds imported cycle energy at1500kWh; this is not automatic tariff eligibility.")
    lines=dict(distribution_customer=r["customer"],distribution_energy=energy*r["distribution_kwh"])
    if res:lines["distribution_special_demand"]=0.
    base=sum(lines.values());lines.update(supply=energy*r["ptc_kwh"],default_service_support=energy*r["dss_kwh"],energy_efficiency=energy*r["eec_kwh"],universal_service=energy*r["usc_kwh"],smart_meter=r["smart_meter"],led_conversion=energy*r["ledc_kwh"],solar_photovoltaic_requirement=energy*r["spvrc_kwh"],tcja=base*r["tcja_fraction"])
    dsic_basis=sum(v for k,v in lines.items() if k!="supply");lines["distribution_dsic"]=dsic_basis*r["dsic_fraction"]
    stas_basis=sum(lines.values());lines["state_tax_adjustment"]=stas_basis*r["stas_fraction"]
    current=sum(lines.values())
    if not math.convex:
        cents=sum(Decimal(str(v)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) for v in lines.values())
        if current<r["customer"]-1e-7 or cents<Decimal(str(r["customer"])):raise ValueError("Penelec current-charge minimum ordering is outside the declared inactive domain; reject raw/component-cent floor cases without forced purchases.")
    represented=(state or {}).get("january_refund_applied",a["refund_represented_before_study"]);refund=r["january_refund"] if not represented else 0.
    lines.update(sales_tax=0. if res else current*.06,january_refund=refund)
    excluded=[JANUARY_GS_EXCLUSION] if not res and a["bill_date"][:7]=="2025-01" else []
    next_state=dict(january_refund_applied=bool(represented or refund!=0.),through_month=a["billing_month"])
    if not res:next_state["gs_qualification_upper_bound_kwh"]=1500. # Conservative native/import envelope, never PV-reduced actual qualification history.
    else:next_state["rs_peak_upper_bound_kw"]=25.
    return dict(lines=lines,metrics={**cycle,"raw_import_kwh":energy,"quantity_basis":"raw_import_energy_no_unsourced_quantity_rounding",
        "objective_scope":"unrounded_verified_component_charges","rounded_cash_optimum_claimed":False,"current_tariff_before_sales_tax_usd":current,
        "ledc_usd_kwh":r["ledc_kwh"],"ledc_applicability_status":r["source_versions"]["LEDC"].get("status","FILED_EFFECTIVE_PRICE"),"ledc_start_window_interpretation":r["source_versions"]["LEDC"].get("interpretation"),
        "gs_fixed_imputed_usage_excluded_verified":True if not res else None,"january_refund_entitlement_confirmed":a["january_refund_eligibility_confirmed"] if a["bill_date"][:7]=="2025-01" else None,
        "tcja_basis_usd":base,"tcja_fraction":r["tcja_fraction"],"dsic_basis_usd":dsic_basis,"dsic_fraction":r["dsic_fraction"],"stas_basis_usd":stas_basis,"stas_fraction":r["stas_fraction"],
        "tax_treatment":"RS solely residential statutory exemption" if res else "6% on known current tariff charges; prior-refund tax adjustment excluded inJanuary2025",
        "january_refund_applied_this_cycle":bool(refund!=0.),"january_refund_sales_tax_status":"unverified_excluded" if excluded else "not_applicable",
        "current_charge_minimum_domain_verified":True,"minimum_domain_customer_usd":r["customer"],"additional_grt_percentage_applied":False,
        "actual_15_minute_peak_kw":peak,"rs_special_demand_inactive_verified":True if res else None,
        "gs_reclassification_treatment":"not_applicable" if res else "Company-retained class; independent prior12 and separate native/import<=1500conservative envelope, not inferred eligibility",
        "gs_qualification_envelope_kwh":None if res else 1500.,"source_versions":r["source_versions"]},next_state=next_state,is_complete_bill=not excluded,excluded_components=excluded,
        rate_evidence_status="verified",assumption_model=None,rate_assumptions=[],rate_sources=SOURCES,warnings=[
            "Penelec district only; rates/eligibility are independent of neighboring FEPA districts, coordinates, supplier, tax jurisdiction, PENELEC market-zone and FE-PN emergency-region labels.",
            "Verified2025,January–June2026 andOctober2026 calendar cycles only. July–September2026 DSIC gap and unsupported periods reject without current-price substitution.",
            "January2025 GS-S is a verified-current-charge/known-refund subtotal; the unknown prior-refund sales-tax adjustment is excluded, not assigned zero. Other supported ordinary months have complete modeled components.",
            "GS-S Company-retained qualification/history is independent. Native and imported energy are bounded at1500kWh in the initial inactive-reclassification domain; this does not interpret the tariff quantity predicate or prove eligibility from optimized purchases.",
            "Mandatory LEDC applies to ordinary class billing units regardless of individual conversion. JanMar2025 no-charge status is a disclosed first-April-rate-window interpretation; no explicit JanMar zero-priced row was found.",
            "Penelec TCJA signs, STAS/DSIC tax bases, source replacement dates, signed riders and SPV credits are retained. GRT/admin/transmission are embedded in supply; no separate wholesale LMP/PLC charge is added.",
            "Januaryrefund is represented once after current tariff/STAS and is never clipped. Current minimum-domain failures reject without forced purchases; no exact printed/rounded-cash minimum is claimed.",
            "Already-active qualifying ordinary renewable NEM/PV-storage approval, PV-only charging, no Partial Services Rider, zero exports and opening bank. No standalone storage or unverified export/credit settlement.",
            "Historical perfect foresight is per cycle; carried refund/SOC/qualification state and representative OpenDSS replay do not establish a joint annual optimum, actual customer savings or site-specific interconnection/engineering approval."])
