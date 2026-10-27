"""Verified Rockland NJ ordinary SC1 non-TOD / metered SC2 non-demand BGS.

Only the October2026 component intersection and Bergen/Eastern PJM account
scope are enabled. Earlier source fragments are not executable prices.
"""
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd

from .rockland_nj_rates import COVERAGE, PLANS, SOURCES, rates_on

TIMEZONE = "America/New_York"


def account_fields(plan="SC1"):
    return [
        dict(name="eligibility_confirmed",type="boolean",label="Rockland NJ selected SC1 non-TOD or metered SC2 non-demand billing independently confirmed"),
        dict(name="ordinary_service_confirmed",type="boolean",label="Established ordinary continuous taxable service, one single-phase secondary meter; no initiation/termination or special provisions"),
        dict(name="full_monthly_charges_confirmed",type="boolean",label="Complete ordinary calendar meter cycle under Rockland's 26–34-day monthly rule"),
        dict(name="county",type="choice",choices=["Bergen"],label="Independently confirmed service county; initial scope Bergen only"),
        dict(name="service_division",type="choice",choices=["eastern"],label="Confirmed Eastern Division/PJM account; Central/Western regions not enabled"),
        dict(name="supply",type="choice",choices=["bgs_rscp"],label="Rockland default BGS Residential Small Commercial Pricing"),
        dict(name="bgs_rscp_confirmed",type="boolean",label="Confirmed BGS-RSCP enrollment; no competitive supplier or CIEP election/assignment"),
        dict(name="supply_eligibility_source",type="text",label="Utility BGS-RSCP and no-CIEP eligibility evidence; no JCP&L PLS rule assumed"),
        dict(name="no_ami_opt_out_fee_confirmed",type="boolean",label="Ordinary installed AMI/AMR service; no manual-reading opt-out/changeout fee"),
        dict(name="no_special_provisions_confirmed",type="boolean",label="No special heating, water heater, EV, facilities, unmetered or short-term contract provisions"),
        dict(name="cycle_source",type="text",label="Meter-cycle evidence or explicitly hypothetical complete calendar cycle"),
        dict(name="tax_source",type="text",label="Ordinary taxable NJ account; filed CBT/SUT already included"),
        dict(name="sc2_non_demand_confirmed",type="boolean",label="SC2: Company-assigned secondary metered non-demand billing, retained across all proposed operation"),
        dict(name="sc2_classification_source",type="text",label="SC2 retained non-demand billing evidence including proposed PV/storage; not absence of a demand-capable meter or an inferred kW threshold"),
        dict(name="der_ordinary_service_confirmed",type="boolean",label="Already-active approved ordinary Class I PV/storage NEM/parallel service; zero exports and bank"),
        dict(name="der_activation_date",type="date",label="Actual effective approved ordinary DER service date, not application date"),
        dict(name="der_eligibility_source",type="text",label="Executed utility agreement, active ordinary approval, required metering/sizing and permitted storage/grid charging"),
        dict(name="rate_evidence_mode",type="choice",choices=["verified"],label="Verified component intersection only; no historical price fallback"),
    ]


def defaults(plan="SC1"):
    if plan not in PLANS:
        raise ValueError("Select Rockland NJ SC1 non-TOD or metered SC2 non-demand BGS-RSCP.")
    return dict(tariff=plan,supply="bgs_rscp",export_mode="none",eligibility_confirmed=False,
        ordinary_service_confirmed=False,full_monthly_charges_confirmed=False,
        county="Bergen",service_division="eastern",bgs_rscp_confirmed=False,supply_eligibility_source="",
        no_ami_opt_out_fee_confirmed=False,no_special_provisions_confirmed=False,
        cycle_source="",tax_source="",billing_month="2026-10-01",bill_date="2026-10-31",cycle_kind="regular",
        voltage="secondary",phase="single",voltage_v=240.,power_factor=1.,meter_count=1,service_line_count=1,
        tax_exempt=False,opening_credit_usd=0.,demand_interval_minutes=15,
        metering="ordinary" if plan=="SC1" else "metered_non_demand_billed",
        sc2_non_demand_confirmed=False,sc2_classification_source="",
        der_ordinary_service_confirmed=False,der_activation_date="",der_eligibility_source="",
        rate_evidence_mode="verified",provisional_assumptions_accepted=False,hypothetical_account=False)


def hypothetical_defaults(plan="SC1",day="2026-10-01"):
    a=defaults(plan)
    start=pd.Timestamp(day).replace(day=1)
    a.update(billing_month=str(start.date()),bill_date=str((start+pd.offsets.MonthEnd()).date()))
    a.update(eligibility_confirmed=True,ordinary_service_confirmed=True,full_monthly_charges_confirmed=True,
        bgs_rscp_confirmed=True,no_ami_opt_out_fee_confirmed=True,no_special_provisions_confirmed=True,
        hypothetical_account=True,
        supply_eligibility_source="Explicit hypothetical utility-confirmed Bergen/Eastern ordinary BGS-RSCP, no CIEP eligibility/assignment/election; not inferred from modeled load or November PLS",
        cycle_source="Explicit hypothetical complete ordinary calendar cycle within the 26–34-day monthly rule; not an actual customer meter schedule",
        tax_source="Explicit hypothetical ordinary taxable NJ account, no exemption; filed CBT/SUT included once",
        der_ordinary_service_confirmed=True,der_activation_date="2026-09-01",
        der_eligibility_source="Explicit hypothetical already-active executed Rockland ordinary Class I PV/storage NEM agreement, approved sizing and installed metering, storage/grid charging permitted; no exports or bank")
    if plan=="SC2":
        a.update(sc2_non_demand_confirmed=True,
            sc2_classification_source="Explicit hypothetical Company-assigned metered secondary non-demand BILLING retained for all proposed grid/PV/storage scenarios; no inferred demand threshold, no metered-demand/standby branch")
    return a


def catalog():
    return [dict(id=p,label="Rockland NJ "+("SC1 non-TOD residential BGS-RSCP" if p=="SC1" else "SC2 metered secondary non-demand BGS-RSCP"),
        status="supported",customer_class="residential" if p=="SC1" else "commercial",voltage="secondary",
        coverage=[dict(start=s,end=e,is_complete_bill=True,scope="Conditional ordinary Bergen/Eastern component coverage; complete calendar cycles only") for s,e in COVERAGE],
        interval_minutes=[15],solar_modes=["non_export"],supply_arrangements=["bgs_rscp"],
        equipment_modes=["grid_only","pv_only","pv_battery"],representative_peak_kw=3.,
        account_fields=account_fields(p),sources=SOURCES,
        eligibility="Independently confirmed Bergen/Eastern ordinary taxable single-phase SC1 non-TOD or metered SC2 non-demand BGS-RSCP; approved active ordinary DER where present.",
        limitations=[
            "Only October2026 complete calendar cycles have a verified component intersection. No full2025 coverage or August/September2026 transmission backfill; current annual PTC is not proof of unchanged monthly surcharges.",
            "Normal monthly periods are26–34days. Partial/shifted cycles, mixed billing months and nonlinear July16,2026 distribution-credit allocation are unimplemented.",
            "Bergen/Eastern PJM scope only; other counties/control areas, competitive supply, CIEP, TOD, primary/three-phase, unmetered and special service reject.",
            "SC2 is independently assigned non-demand BILLING retained throughout proposed operation. No JCP&L10kW/prior11-month/NovemberPLS rule or physical no-demand-meter assumption is imported.",
            "Already-active ordinary ClassI PV/storage approval, zero exports/bank and permitted grid charging are required. Standby applies to demand-billed SC2/7; the retained non-demand account is outside that branch. No standalone storage or export settlement.",
            "CBT/SUT and BGS administration are embedded once. IIP is combined in base rates, TTAC expired June2021 and residential EGCC ended February2026; no duplicated or extended credits.",
            "Raw kWh/component half-up cents are modeling conventions, not exact printed-invoice rounding. Post-adjustment raw and component-cent totals must meet the ordinary monthly minimum; unsupported floor cases reject without forced imports.",
            "October actual full-month weather is unavailable at source review. Explicit clear-sky modeled acceptance is not historical weather/full-year evidence or a jointly optimized annual/rounded-cash/customer-savings claim."])
        for p in PLANS]


def _reference(a,key):
    if not isinstance(a.get(key),str) or not a[key].strip():
        raise ValueError("Document Rockland account fact: "+key)


def cycle_review(a,index):
    idx=pd.DatetimeIndex(index);step=pd.Timedelta(minutes=15)
    if len(idx)<2 or str(idx.tz)!=TIMEZONE or not np.all(idx[1:]-idx[:-1]==step):
        raise ValueError("Rockland requires consecutive America/New_York15-minute intervals; missing, duplicate, naive or hourly data reject.")
    start=idx[0];stop=idx[-1]+step
    if (start!=start.normalize() or start.day!=1 or stop!=start+pd.offsets.MonthBegin()
        or not 26<=(stop.date()-start.date()).days<=34 or a.get("cycle_kind")!="regular"
        or a.get("full_monthly_charges_confirmed") is not True
        or a.get("billing_month")!=str(start.date()) or a.get("bill_date")!=str(idx[-1].date())):
        raise ValueError("Rockland requires a matching complete ordinary calendar cycle and final-day bill date; irregular proration/billing-month shifts reject.")
    rates_on(str(start.date()),a["tariff"]);rates_on(str(idx[-1].date()),a["tariff"])
    return dict(service_start=str(start.date()),service_end=str(idx[-1].date()),billing_month=a["billing_month"],bill_date=a["bill_date"],
        cycle_days=(stop.date()-start.date()).days,elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)),
        monthly_charge_factor=1.,partial_period_proration_applied=False,
        reconciliation_clock="All usage billed in the month indicated; calendar service/bill month explicitly matched",
        rate_allocation="One verified component regime; full monthly charges and 600kWh SC1 block retained")


def validate_account(a,index,equipment=None):
    if not isinstance(a,dict) or a.get("tariff") not in PLANS or a.get("supply")!="bgs_rscp" or a.get("export_mode")!="none":
        raise ValueError("Select Rockland NJ SC1 non-TOD or SC2 non-demand BGS-RSCP with zero export.")
    if set(a)-set(defaults(a["tariff"])) or a.get("rate_evidence_mode")!="verified" or a.get("provisional_assumptions_accepted") is not False:
        raise ValueError("Rockland has no unsupported-field, provisional-price or missing-component fallback.")
    for key in ("eligibility_confirmed","ordinary_service_confirmed","full_monthly_charges_confirmed","bgs_rscp_confirmed","no_ami_opt_out_fee_confirmed","no_special_provisions_confirmed"):
        if a.get(key) is not True:raise ValueError("Confirm Rockland ordinary account eligibility, monthly cycle, BGS and no opt-out/special fees independently.")
    for key in ("supply_eligibility_source","cycle_source","tax_source"):_reference(a,key)
    if (a.get("county"),a.get("service_division"))!=("Bergen","eastern"):
        raise ValueError("Rockland initial scope is independently confirmed Bergen/Eastern/PJM only; other control areas are not inferred.")
    expected=dict(voltage="secondary",phase="single",voltage_v=240.,power_factor=1.,meter_count=1,service_line_count=1,tax_exempt=False,opening_credit_usd=0.,demand_interval_minutes=15)
    if any(a.get(k)!=v or type(a.get(k)) is bool and type(v) is not bool
           or type(v) is bool and a.get(k) is not v for k,v in expected.items()):
        raise ValueError("Rockland scope is one ordinary taxable120/240V single-phase meter/service, unity billing PF,15-minute intervals and no bank.")
    cycle_review(a,index)
    if a["tariff"]=="SC2":
        if a.get("metering")!="metered_non_demand_billed" or a.get("sc2_non_demand_confirmed") is not True:
            raise ValueError("SC2 needs utility-assigned metered secondary non-demand BILLING retained across all operation, not an inferred threshold or missing demand-capable meter.")
        _reference(a,"sc2_classification_source")
    elif a.get("metering")!="ordinary" or a.get("sc2_non_demand_confirmed") is not False or a.get("sc2_classification_source")!="":
        raise ValueError("SC1 non-TOD has no SC2 demand-billing assignment.")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Rockland DER requires already-active approved ordinary PV/storage NEM service; no standalone storage.")
        _reference(a,"der_eligibility_source")
        try:
            active=pd.Timestamp(a["der_activation_date"]);valid=str(active.date())==a["der_activation_date"] and active.date()<=pd.DatetimeIndex(index)[0].date()
        except (TypeError,ValueError,KeyError):valid=False
        if not valid:raise ValueError("Rockland executed ordinary DER approval and required metering must already be active before the cycle; no application-date or borrowed20-day rule.")
        if max(equipment.get("pv_dc_kw",0.),equipment.get("pv_ac_kw",0.))+equipment.get("battery_kw",0.)>25.+1e-8:
            raise ValueError("Rockland study output capacity is at most25kW combined PV/storage; this is not an interconnection exemption.")


def validate_state(a,index,state=None,equipment=None):
    if state not in (None,{}):raise ValueError("Rockland ordinary non-demand scope has no modeled carried credit/demand state.")


def charge_lines(index,imports,exports,a,*,math,state=None):
    cycle=cycle_review(a,index);validate_state(a,index,state=state);r=rates_on(cycle["service_start"],a["tariff"])
    if math.convex:math.constraints.append(exports==0)
    elif np.max(exports)>1e-5:raise ValueError("Rockland export/NEM settlement is unimplemented; exports must be zero.")
    energy=math.hours*math.sum(imports)
    def block(pair):return energy*pair[0] if pair[0]==pair[1] else math.tiered(energy,[600.],pair)
    lines=dict(distribution_customer=r["customer"],distribution_energy=block(r["distribution_energy"]),
        distribution_adjustment=block(r["distribution_adjustment"]),bgs_generation_energy=block(r["generation_energy"]))
    lines.update({key:energy*rate for key,rate in r["linear_rates"].items()})
    lines.update(temporary_tax_act_credit=0.,infrastructure_investment_increment=0.,residential_generation_capacity_deferral=0.)
    if a["tariff"]=="SC2":lines.update(distribution_demand=0.,transmission_demand=0.,bgs_generation_demand=0.,ciep_standby_fee=0.)
    if not math.convex:
        raw=sum(lines.values());rounded=sum(Decimal(str(v)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) for v in lines.values())
        if raw<r["minimum"]-1e-7 or rounded<Decimal(str(r["minimum"])):
            raise ValueError("Rockland post-adjustment monthly minimum ordering is unverified in this domain; reject raw/rounded floor cases without forcing imports.")
    return dict(lines=lines,metrics={**cycle,"raw_import_kwh":energy,"actual_15_minute_peak_kw":math.demand(imports,index,minutes=15),
        "quantity_basis":"raw_import_energy_no_unsourced_quantity_rounding","objective_scope":"unrounded_ordinary_component_charges",
        "whole_cycle_block_kwh":600. if a["tariff"]=="SC1" else None,"monthly_minimum_usd":r["minimum"],
        "minimum_inactive_domain_verified":True,"additional_tax_percentage_applied":False,"rounded_cash_optimum_claimed":False,
        "transmission_surcharge_basis":"Filed bundled RMR/EL05-121/TEC once; no separate TEC addition",
        "account_branch":"Bergen/Eastern SC1 non-TOD" if a["tariff"]=="SC1" else "Bergen/Eastern metered secondary non-demand BILLING; no numeric threshold inferred",
        "component_versions":r["component_versions"],"tax_treatment":"Applicable CBT/SUT included once in filed prices"},
        next_state={},is_complete_bill=True,excluded_components=[],rate_evidence_status="verified",assumption_model=None,rate_assumptions=[],rate_sources=SOURCES,
        warnings=[
            "Rockland October2026 ordinary Bergen/Eastern component intersection only; earlier dates, other divisions and missing historical prices reject.",
            "Utility/supplier/tax county, PJM RECO metadata, actual active DER and retained non-demand billing are independent account facts. No wholesale price node or JCP&L demand/PLS rule is inferred.",
            "SC2 is metered non-demand BILLING, not lack of a demand-capable meter. Ordinary non-demand accounts are outside the demand-billed SC2/7 standby branch; assignment must remain valid for proposed PV/storage operation.",
            "Raw kWh, component half-up cents and unrounded cost proofs are study conventions. Unsupported monthly-floor cases reject without forced purchases; no exact printed/rounded-cash or jointly optimized annual minimum is claimed.",
            "TTAC ended June2021, EGCC ended February2026, and IIP is combined in base prices. Inclusive taxes/admin and bundled transmission surcharges are counted once.",
            "Non-export active approved ordinary ClassI PV/storage only; no standalone battery, opening bank, export credit/banking/cashout, CIEP, TOD, special service or inferred county/control area."])
