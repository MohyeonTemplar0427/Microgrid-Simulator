"""Toledo Edison ordinary RS / measured secondary GS SSO.

Only independently verified complete calendar component intersections execute.
The same charge expressions feed dispatch and numerical rebilling. PJM prices,
the FE-ATSI control area and regional-average carbon do not set retail charges.
"""
from copy import deepcopy

import numpy as np
import pandas as pd

from .toledo_oh_rates import COVERAGE, PLANS, rates_on

UTILITY = "firstenergy_ohio_toledo"
TIMEZONE = "America/New_York"
ROOT = "https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/Ohio/tariffs/"
SOURCES = [ROOT + name for name in ("TE-2026-Electric-Service.pdf",
    "2025-TE-Electric-Service-Tariff.pdf", "TE-2024-Electric-Service.pdf", "TE-2025-Electric-Service.pdf")]
SOURCES += ["https://www.firstenergycorp.com/customer_choice/ohio_/ohio_tariffs.html",
    "https://web.archive.org/web/20250612032413id_/" + ROOT + "TE-2025-Electric-Service.pdf",
    "https://web.archive.org/web/20250825001741id_/" + ROOT + "TE-2025-Electric-Service.pdf",
    "https://dam.assets.ohio.gov/image/upload/puco.ohio.gov/empliibrary/files/docketing/tariffs/Electric/The%20Toledo%20Edison%20Company%2C%20FIRSTENERGY/PUCO%208%20Schedule%20of%20Ratesfor%20Electric%20Service%20%281%29.pdf",
    "https://codes.ohio.gov/ohio-revised-code/section-5727.81",
    "https://codes.ohio.gov/ohio-revised-code/section-5751.03",
    "https://codes.ohio.gov/ohio-revised-code/section-5739.02",
    "https://codes.ohio.gov/ohio-administrative-code/rule-4901:1-10-28"]
GAPS = [dict(start="2025-02-01", end="2025-05-31", reason="Intermediate ESP-IV GEN18 and component chronology are unverified."),
    dict(start="2025-07-01", end="2025-08-31", reason="July LGR12 and August14 fixed-charge transition allocation are unverified."),
    dict(start="2025-12-01", end="2025-12-31", reason="December DCR revision is unverified; archived year-end and February2026 captures retain September DCR54."),
    dict(start="2026-01-01", end="2026-09-30", reason="Earlier quarterly riders, credits and complete dated intersections are unverified.")]


def account_fields(plan_id="RS"):
    fields = [
        {"name":"eligibility_confirmed", "type":"boolean", "label":"Confirmed Toledo Edison RS/GS secondary account", "default":False, "required":True},
        {"name":"ordinary_service_confirmed", "type":"boolean", "label":"One ordinary single-phase meter; no legacy heating/special credits, assistance, opt-out or additional facilities", "default":False, "required":True},
        {"name":"sso_enrollment_confirmed", "type":"boolean", "label":"Ordinary Standard Service Offer throughout the cycle; no shopping, aggregation or optional pricing", "default":False, "required":True},
        {"name":"supply_source", "type":"text", "label":"SSO enrollment evidence or explicit hypothetical assumption", "required":True},
        {"name":"no_local_tax_confirmed", "type":"boolean", "label":"Independently confirmed no additional municipal/franchise charge or special tax arrangement", "default":False, "required":True},
        {"name":"tax_source", "type":"text", "label":"Local-charge and ordinary state-kWh-tax evidence or hypothetical assumption", "required":True},
        {"name":"full_monthly_charges_confirmed", "type":"boolean", "label":"Complete calendar measurement cycle with full monthly charges", "default":False, "required":True},
        {"name":"cycle_source", "type":"text", "label":"Complete meter-cycle evidence or explicit hypothetical assumption", "required":True},
        {"name":"bill_date", "type":"date", "label":"Final-day bill-rendered date matching the service month", "required":True},
        {"name":"der_ordinary_service_confirmed", "type":"boolean", "label":"Already-approved exact PV/storage configuration qualifies for ordinary renewable service without Partial Service or extra recurring fees", "default":False},
        {"name":"der_activation_date", "type":"date", "label":"Final interconnection approval and required metering active by this date"},
        {"name":"der_eligibility_source", "type":"text", "label":"Ordinary renewable sizing, exact storage configuration and permission-to-operate evidence or hypothetical assumption"},
    ]
    if plan_id == "GS":
        fields += [
            {"name":"measured_demand_confirmed", "type":"boolean", "label":"Company measures GS demand on aligned 15-minute intervals; no estimated/unmetered demand", "default":False, "required":True},
            {"name":"contract_demand_confirmed", "type":"boolean", "label":"Contract demand is the actual Company-assigned obligation, independent of DER-reduced demand", "default":False, "required":True},
            {"name":"contract_demand_kw", "type":"number", "label":"Documented Company contract demand (kW)", "required":True},
            {"name":"contract_source", "type":"text", "label":"Contract-demand evidence or explicit hypothetical obligation", "required":True},
        ]
    return fields


def defaults(plan_id="RS"):
    if plan_id not in PLANS:
        raise ValueError("Select Toledo Edison RS or measured GS secondary SSO.")
    return dict(tariff=plan_id, supply="sso", export_mode="none", eligibility_confirmed=False,
        ordinary_service_confirmed=False, sso_enrollment_confirmed=False, supply_source="",
        no_local_tax_confirmed=False, tax_source="", full_monthly_charges_confirmed=False,
        cycle_source="", cycle_kind="regular", billing_month="2026-10-01", bill_date="2026-10-31",
        rate_evidence_mode="verified", provisional_assumptions_accepted=False,
        voltage="secondary", phase="single", voltage_v=240., power_factor=1., meter_count=1,
        opening_credit_usd=0., tax_jurisdiction="oh_state_only", self_assessor=False,
        demand_interval_minutes=15, measured_demand_confirmed=False, contract_demand_confirmed=False,
        contract_demand_kw=0., contract_source="", der_ordinary_service_confirmed=False,
        der_activation_date="", der_eligibility_source="")


def hypothetical_defaults(plan_id="RS", year=2026, *, day=None):
    a = defaults(plan_id)
    day = day or f"{year}-10-01"
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True, sso_enrollment_confirmed=True,
        supply_source="Explicit hypothetical Company-confirmed ordinary SSO account; no supplier change",
        no_local_tax_confirmed=True, tax_source="Explicit hypothetical ordinary non-self-assessor account without municipal/franchise charges",
        full_monthly_charges_confirmed=True, cycle_source="Explicit hypothetical complete calendar meter cycle; not a customer bill",
        billing_month=day, bill_date=str((pd.Timestamp(day)+pd.offsets.MonthEnd()).date()),
        der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
        der_eligibility_source="Hypothetical already-active qualifying solar and exact paired-storage approval, sizing, meter and final permission to operate; no Partial Service or recurring special charges",
        hypothetical_account=True)
    if plan_id == "GS":
        a.update(measured_demand_confirmed=True, contract_demand_confirmed=True, contract_demand_kw=12.,
            contract_source="Explicit hypothetical Company-assigned 12 kW contract, unchanged across scenarios; not inferred from optimized imports")
    return a


def catalog():
    return [dict(id=p, label="Toledo Edison " + ("Residential RS" if p=="RS" else "measured General Service–Secondary GS") + " (SSO)",
        status="supported", customer_class="residential" if p=="RS" else "commercial",
        coverage=[dict(start=s,end=e) for s,e in COVERAGE], coverage_gaps=deepcopy(GAPS), voltage="secondary",
        supply_arrangements=["sso"], solar_modes=["non_export"], equipment_modes=["grid_only","pv_only","pv_battery"],
        representative_peak_kw=3. if p=="RS" else 20., account_fields=account_fields(p), sources=SOURCES,
        eligibility="Company-confirmed ordinary SSO, one 120/240 V single-phase secondary meter, complete calendar cycle, no special or municipal charges. GS requires measured 15-minute demand and an independent contract obligation.",
        limitations=[
            "Complete verified intersections only: January, June and September–November2025; October2026. Full-year2025 and earlier2026 component gaps reject without provisional substitutions.",
            "No partial/shifted cycles or fixed-charge transition allocation, alternative suppliers, optional pricing, legacy heating/assistance credits, primary/three-phase service or special facilities.",
            "GS capacity is a flat amount for the first5kW, then a per-kW excess charge; billing demand=max(measured15-minute peak,5kW,documented contract). No invented historical ratchet. Study envelope<=100kW is narrower than the tariff.",
            "State-kWh tax includes the specified CAT gross-up; non30-day measurements use statutory daily bands. No generic sales tax, duplicate whole-bill CAT, or wholesale capacity/transmission adder.",
            "Already-active approved ordinary renewable PV and exact paired storage; PV-only charging, zero exports/bank. No standalone storage, NEM/export settlement, annual optimum or customer/site calibration claim."])
        for p in PLANS]


def _reference(a, key):
    if not isinstance(a.get(key),str) or not 1<=len(a[key].strip())<=500:
        raise ValueError("Document Toledo Edison " + key + " without personal identifiers.")


def _number(value, upper):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and np.isfinite(value) and 0.<=value<=upper


def cycle_review(a, index):
    idx = pd.DatetimeIndex(index)
    if len(idx)<2 or str(idx.tz)!=TIMEZONE or not np.all(idx[1:]-idx[:-1]==pd.Timedelta(minutes=15)):
        raise ValueError("Toledo Edison requires complete consecutive Eastern-time15-minute intervals; missing/duplicate/hourly substitutes reject.")
    stop = idx[-1]+pd.Timedelta(minutes=15)
    if idx[0]!=idx[0].normalize() or idx[0].day!=1 or stop!=idx[0]+pd.offsets.MonthBegin() or a.get("cycle_kind")!="regular" or a.get("full_monthly_charges_confirmed") is not True:
        raise ValueError("Toledo Edison initial scope requires a complete calendar measurement cycle; no partial/shifted fixed-charge allocation.")
    if a.get("billing_month")!=str(idx[0].date()) or a.get("bill_date")!=str(idx[-1].date()):
        raise ValueError("Toledo Edison billing month and final-day bill date must match service.")
    if a.get("rate_evidence_mode","verified")!="verified" or a.get("provisional_assumptions_accepted",False) is not False:
        raise ValueError("Toledo Edison has no provisional-rate or inferred allocation mode.")
    r = rates_on(idx[0].date(),a["tariff"],bill_date=a["bill_date"])
    if r!=rates_on(idx[-1].date(),a["tariff"],bill_date=a["bill_date"]):
        raise ValueError("A component transition inside the calendar cycle lacks verified allocation.")
    days = (stop.date()-idx[0].date()).days
    return dict(service_start=str(idx[0].date()),service_end=str(idx[-1].date()),billing_month=a["billing_month"],
        bill_date=a["bill_date"],cycle_days=days,elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)),
        monthly_charge_factor=1.,partial_period_proration_applied=False,
        state_tax_thresholds_kwh=[2000.,15000.] if days==30 else [67.*days,500.*days])


def validate_account(a, index, equipment=None):
    if not isinstance(a,dict) or a.get("tariff") not in PLANS or a.get("supply")!="sso" or a.get("export_mode")!="none":
        raise ValueError("Select Toledo Edison ordinary RS/GS SSO and zero export; other suppliers/settlement are unsupported.")
    for key in ("eligibility_confirmed","ordinary_service_confirmed","sso_enrollment_confirmed","no_local_tax_confirmed","full_monthly_charges_confirmed"):
        if a.get(key) is not True:
            raise ValueError("Confirm Company eligibility, ordinary SSO, absent special/local charges and full calendar measurement cycles independently.")
    for key in ("supply_source","tax_source","cycle_source"):
        _reference(a,key)
    expected=dict(voltage="secondary",phase="single",voltage_v=240.,power_factor=1.,meter_count=1,
        opening_credit_usd=0.,tax_jurisdiction="oh_state_only",self_assessor=False,demand_interval_minutes=15)
    if any(a.get(k)!=v or isinstance(a.get(k),bool) and not isinstance(v,bool) or isinstance(v,bool) and a.get(k) is not v for k,v in expected.items()):
        raise ValueError("Toledo Edison scope is one120/240V single-phase secondary meter, unity billing PF, ordinary state-kWh tax, no local tax/self-assessment and no bank.")
    cycle_review(a,index)
    if a["tariff"]=="GS":
        if a.get("measured_demand_confirmed") is not True or a.get("contract_demand_confirmed") is not True or not _number(a.get("contract_demand_kw"),100.):
            raise ValueError("GS requires confirmed15-minute measured demand and documented Company contract demand within the100kW study envelope.")
        _reference(a,"contract_source")
    elif a.get("measured_demand_confirmed") is not False or a.get("contract_demand_confirmed") is not False or a.get("contract_demand_kw")!=0. or isinstance(a.get("contract_demand_kw"),bool) or a.get("contract_source")!="":
        raise ValueError("Ordinary solely residential RS has no modeled commercial contract or mixed-use account.")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Already-active Company-approved ordinary qualifying renewable PV is required; standalone storage is unsupported.")
        _reference(a,"der_eligibility_source")
        try:
            activation=pd.Timestamp(a["der_activation_date"])
            valid=str(activation.date())==a["der_activation_date"] and activation.date()<=pd.DatetimeIndex(index)[0].date()
        except (ValueError,TypeError,KeyError):
            valid=False
        if not valid:
            raise ValueError("Company final interconnection approval and required metering must already be active before service.")
        if equipment.get("battery") and (not equipment.get("renewable_only_charging") or not equipment.get("no_battery_export")):
            raise ValueError("Initial paired-storage scope requires PV-only charging and zero battery exports.")
        if max(equipment.get("pv_dc_kw",0.),equipment.get("pv_ac_kw",0.))+equipment.get("battery_kw",0.)>25.+1e-8:
            raise ValueError("Combined study output is bounded at25kW; this does not establish Company sizing/interconnection eligibility.")


def validate_state(a, index, state=None, equipment=None):
    if state not in (None,{}):
        raise ValueError("Toledo Edison ordinary scope has no export credit bank or trailing demand ratchet; contract obligations stay in the account.")


def evidence(index, account):
    cycle_review(account,index)
    return dict(rate_evidence_status="verified",assumption_model=None,rate_assumptions=[],objective_scope="complete_utility_bill")


def charge_lines(index, imports, exports, a, *, math, state=None):
    validate_state(a,index,state)
    cycle=cycle_review(a,index);r=rates_on(cycle["service_start"],a["tariff"],bill_date=a["bill_date"])
    res=a["tariff"]=="RS";energy=math.hours*math.sum(imports)
    if math.convex:
        math.constraints.extend([exports==0,energy<=833000.,imports<=(25. if res else 100.)])
    elif np.max(exports)>1e-5 or energy>833000.+1e-7 or np.max(imports)>(25. if res else 100.)+1e-7:
        raise ValueError("Toledo Edison requires zero exports and the declared ordinary RS25kW/GS100kW,<=833000kWh study envelope.")
    peak=math.demand(imports,index,minutes=15)
    demand=0. if res else math.maximum([peak,5.,a["contract_demand_kw"]])
    lines=dict(distribution_customer=r["customer"],distribution_energy=r["distribution_kwh"]*energy,
        distribution_demand=0. if res else r["first_5_kw"]+r["excess_kw"]*(demand-5.))
    base=sum(lines.values())
    lines.update(supply_energy=energy*r["supply_energy"],supply_capacity=energy*r["supply_capacity"],
        non_market_transmission=r["nmb"]*(energy if res else demand),
        delivery_capital=r["dcr"]*(base if r["dcr_basis"]=="base_distribution" else energy if res else demand),
        delivery_capital_credit=r["dcr_credit_fixed"]+r["dcr_credit_kw"]*demand+r["dcr_credit_kwh"]*energy,
        alternative_energy=energy*r["aer"],delta_revenue=energy*r["drr"],distribution_uncollectible=energy*r["dun"],
        generation_reconciliation=energy*r["gcr"],pipp_uncollectible=energy*r["pur"],nondistribution_uncollectible=energy*r["ndu"],
        economic_development=energy*r["edr"],automaker_recovery=energy*r["automaker"],tax_savings=energy*r["tsa"],
        demand_side_efficiency=energy*r["dse"],phase_in_recovery=energy*r["pir"],residential_heating_recovery=energy*r["rer"],
        customer_credit_recovery=energy*r["ccr"],consumer_rate_credit=r["crc"]*(1. if res else energy),
        legacy_generation=r["lgr"]*(1. if res else energy),solar_generation_fund=r["sgf"]*(1. if res else energy),
        vegetation_management=r["vmc"]*(energy if res else demand),advanced_meter=r["ami"],
        universal_service=energy*r["usf_first_833000_kwh"])
    lines["state_kwh_tax"]=math.tiered(energy,cycle["state_tax_thresholds_kwh"],[.00465,.00419,.00363])/(1.-.0026)
    lines["sales_tax"]=0.
    return dict(lines=lines,metrics={**cycle,"rates":r,"raw_import_kwh":energy,"actual_15_minute_peak_kw":peak,
        "billing_demand_kw":demand,"contract_demand_kw":a["contract_demand_kw"],"base_distribution_usd":base,
        "demand_history_ratchet_applied":False,"state_tax_cat_rate":.0026,"additional_tax_percentage_applied":False,
        "quantity_basis":"raw_interval_energy_no_unsourced_meter_rounding","rounded_cash_optimum_claimed":False,
        "capacity_transmission_treatment":"GEN energy/capacity per kWh; NMB separately once; no LMP/PLC/NSPL or whole-bill CAT adder",
        "source_versions":r["source_versions"]},next_state={},is_complete_bill=True,excluded_components=[],
        rate_evidence_status="verified",assumption_model=None,rate_assumptions=[],rate_sources=SOURCES,
        warnings=["Toledo Edison ordinary RS/GS SSO only, complete matching calendar cycles and independently confirmed utility, supplier and local-charge eligibility.",
            "GS measured15-minute demand retains the documented Company contract and5kW floor; the first5kW capacity amount is flat. Native/import envelopes are conservative study scope, not the whole tariff.",
            "State-kWh tax uses the statutory non30-day local-calendar-day bands and its specified CAT gross-up. Other filed rates include applicable taxes; wired electricity has no additional sales-tax percentage.",
            "Already-active ordinary approved PV/paired storage, PV-only charging and zero exports/bank. No unsupported historical rate substitution, NEM settlement, rounded-cash or annual joint optimum, measured-customer or surveyed-site claim."])
