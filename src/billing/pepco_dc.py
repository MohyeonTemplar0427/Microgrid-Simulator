"""Pepco DC R and GS-ND Standard Offer Service, non-export only."""
import numpy as np
import pandas as pd

from .pepco_dc_rates import COVERAGE, DER_SOURCE, GAPS, PLANS, SOURCES, rates_for_month

UTILITY = "pepco_district_of_columbia"
TIMEZONE = "America/New_York"
STUDY_LIMIT_KW = 24.99999
GS_ENERGY_LIMIT_KWH = 5999.99999
CONFIRMATIONS = {
    "eligibility_confirmed": "Pepco DC confirms the selected R or secondary GS-ND tariff and SOS assignment",
    "ordinary_service_confirmed": "Ordinary one-meter single-phase service, no optional programs, special charges, RAD or senior/disabled credit",
    "full_monthly_charges_confirmed": "Complete matching calendar meter cycle and bill month with full monthly charges",
    "tax_status_confirmed": "Ordinary DC delivery tax and statutory riders apply without an exemption",
}


def account_fields(plan="R"):
    result = [dict(name=key, type="boolean", label=label, required=True)
              for key, label in CONFIRMATIONS.items()]
    result += [
        dict(name="account_source", type="text", required=True,
             label="Pepco assignment, SOS and ordinary account evidence or explicit hypothetical account"),
        dict(name="der_ordinary_service_confirmed", type="boolean",
             label="Written Pepco approval preserves ordinary billing for the exact non-export equipment"),
        dict(name="der_activation_date", type="date", label="Final parallel-operation approval active by"),
        dict(name="der_eligibility_source", type="text", label="Interconnection and special-agreement reference"),
    ]
    if plan == "GS-ND":
        result += [
            dict(name="gs_retained_classification_confirmed", type="boolean", required=True,
                 label="Pepco retains secondary GS-ND throughout the cycle with no pending reclassification"),
            dict(name="gs_no_demand_meter_confirmed", type="boolean", required=True,
                 label="Pepco confirms non-demand metering and no billed demand for this cycle"),
            dict(name="gs_prior_monthly_usage_kwh", type="number_array", required=True,
                 label="12 actual prior monthly kWh values, oldest first, each below 6,000"),
            dict(name="gs_usage_review_source", type="text", required=True,
                 label="Independent utility usage review and current-cycle non-demand metering evidence"),
            dict(name="gs_prior_monthly_demands_kw", type="number_array", required=True,
                 label="12 actual prior monthly maximum 30-minute demands, oldest first (all below 25 kW)"),
            dict(name="gs_history_source", type="text", required=True,
                 label="Independent demand history and retained Pepco GS-ND assignment"),
        ]
    return result


def defaults(plan="R"):
    if plan not in PLANS:
        raise ValueError("Select Pepco DC R or GS-ND SOS.")
    a = dict(tariff=plan, supply="sos", export_mode="none", voltage="secondary", phase="single",
             voltage_v=240., meter_count=1, opening_credit_usd=0., rate_evidence_mode="verified",
             billing_month="2026-10-01", bill_date="2026-10-31", cycle_kind="regular",
             cycle_source="", account_source="", der_ordinary_service_confirmed=False,
             der_activation_date="", der_eligibility_source="")
    a.update(dict.fromkeys(CONFIRMATIONS, False))
    if plan == "GS-ND":
        a.update(gs_retained_classification_confirmed=False, gs_no_demand_meter_confirmed=False,
                 gs_prior_monthly_usage_kwh=[], gs_usage_review_source="",
                 gs_prior_monthly_demands_kw=[], gs_history_source="")
    return a


def hypothetical_defaults(plan="R", *, day=None):
    a = defaults(plan)
    month = pd.Timestamp(day or a["billing_month"]).replace(day=1)
    a.update(dict.fromkeys(CONFIRMATIONS, True))
    a.update(hypothetical_account=True, billing_month=str(month.date()),
             bill_date=str((month+pd.offsets.MonthEnd()).date()),
             cycle_source="Hypothetical calendar meter readings with matching bill month",
             account_source="Hypothetical ordinary Pepco DC single-meter SOS account without optional credits",
             der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
             der_eligibility_source="Hypothetical exact non-export PV and PV-only-charged storage agreement "
                                    "preserving ordinary import billing without other fees or export credits")
    if plan == "GS-ND":
        a.update(gs_retained_classification_confirmed=True, gs_no_demand_meter_confirmed=True,
                 gs_prior_monthly_usage_kwh=[1500.]*12,
                 gs_usage_review_source="Hypothetical actual prior twelve 1,500 kWh bills and Pepco-retained non-demand metering",
                 gs_prior_monthly_demands_kw=[10.]*12,
                 gs_history_source="Hypothetical independent twelve-month 10 kW demand history and retained GS-ND")
    return a


def catalog():
    return [dict(
        id=plan, label="Pepco DC "+("Residential R SOS" if plan == "R" else "General Service Non-Demand SOS"),
        status="supported", customer_class="residential" if plan == "R" else "commercial",
        coverage=[dict(start=s, end=e) for s,e in COVERAGE],
        coverage_gaps=[dict(start=s,end=e,reason=why) for s,e,why in GAPS],
        voltage="secondary", interval_minutes=[15], supply_arrangements=["sos"], solar_modes=["non_export"],
        equipment_modes=["grid_only","pv_only","pv_battery"], representative_peak_kw=3. if plan == "R" else 5.,
        account_fields=account_fields(plan), sources=SOURCES,
        eligibility="Confirmed ordinary single-phase Pepco DC SOS. GS-ND retains independent below-25 kW history and utility assignment.",
        limitations=[
            "Complete matching calendar cycles only, with verified monthly credit and rider intersections.",
            "Study power below 25 kW and GS-ND native/import cycle energy below 6,000 kWh. Independent prior energy review and non-demand metering are required.",
            "Approved non-export PV or PV-charged paired storage must preserve ordinary rates by written agreement.",
        ]) for plan in PLANS]


def _reference(a, name):
    value = a.get(name)
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 500:
        raise ValueError("Document Pepco DC "+name+" without personal identifiers.")


def cycle_review(a, index):
    idx = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if len(idx) < 2 or str(idx.tz) != TIMEZONE or idx.hasnans or not np.all(idx[1:]-idx[:-1] == step):
        raise ValueError("Pepco DC requires complete consecutive Eastern 15-minute intervals.")
    start, stop = idx[0], idx[-1]+step
    if (start != start.normalize() or start.day != 1 or stop != start+pd.offsets.MonthBegin()
            or a.get("cycle_kind") != "regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Pepco DC requires a complete calendar cycle and full monthly charges.")
    month, end = str(start.date()), str(idx[-1].date())
    if a.get("billing_month") != month or a.get("bill_date") != end:
        raise ValueError("Pepco DC requires matching service/bill months and final-day bill date.")
    r = rates_for_month(month[:7], a["tariff"])
    return dict(service_start=month, service_end=end, billing_month=month, bill_date=end,
                elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)),
                source_version=r["source_version"], source_grade=r["source_grade"]), r


def validate_account(a, index, equipment=None):
    if (not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "sos"
            or a.get("export_mode") != "none"):
        raise ValueError("Select Pepco DC R or GS-ND SOS and non-export operation.")
    if any(a.get(key) is not True for key in CONFIRMATIONS):
        raise ValueError("Confirm Pepco DC ordinary assignment, full charges and tax status.")
    for key in ("account_source", "cycle_source"):
        _reference(a, key)
    expected = dict(voltage="secondary",phase="single",voltage_v=240.,meter_count=1,
                    opening_credit_usd=0.,rate_evidence_mode="verified")
    if (any(a.get(k) != v or isinstance(a.get(k),bool) for k,v in expected.items())
            or a.get("provisional_assumptions_accepted",False) is not False):
        raise ValueError("Pepco DC initial scope requires ordinary 120/240 V secondary service and verified rates.")
    cycle,_ = cycle_review(a,index)
    if a["tariff"] == "GS-ND":
        history = a.get("gs_prior_monthly_demands_kw")
        if (a.get("gs_retained_classification_confirmed") is not True
                or not isinstance(history,list) or len(history) != 12
                or any(type(v) not in (int,float) or not 0 <= v < 25. for v in history)):
            raise ValueError("GS-ND requires independent twelve-month below-25 kW demand history and retained assignment.")
        _reference(a,"gs_history_source")
        usage = a.get("gs_prior_monthly_usage_kwh")
        if (a.get("gs_no_demand_meter_confirmed") is not True
                or not isinstance(usage,list) or len(usage) != 12
                or any(type(v) not in (int,float) or not 0 <= v < 6000. for v in usage)):
            raise ValueError("GS-ND requires confirmed non-demand metering and independent twelve-month usage below 6,000 kWh in every month.")
        _reference(a,"gs_usage_review_source")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Confirm written Pepco approval preserving ordinary non-export PV billing.")
        _reference(a,"der_eligibility_source")
        activation = a.get("der_activation_date")
        try:
            active = str(pd.Timestamp(activation).date()) == activation and activation <= cycle["service_start"]
        except (TypeError,ValueError):
            active = False
        if not active:
            raise ValueError("Pepco DC final interconnection approval must precede the cycle.")
        if equipment.get("battery") and (equipment.get("renewable_only_charging") is not True
                                        or equipment.get("no_battery_export") is not True):
            raise ValueError("Pepco DC storage requires PV-only charging and zero export.")


def validate_native_load(a, load):
    if (np.max(load) >= 25.
            or a["tariff"] == "GS-ND" and .25*np.sum(load) >= 6000.):
        raise ValueError("Pepco DC native load exceeds the study envelope of below 25 kW and GS-ND energy below 6,000 kWh.")


def validate_state(a, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("Pepco DC non-export scope has no modeled credit or demand state.")


def charge_lines(index, imports, exports, a, *, math, state=None):
    validate_state(a,index,state)
    cycle,r = cycle_review(a,index)
    if math.convex:
        math.constraints.extend([exports == 0, imports <= STUDY_LIMIT_KW])
    elif np.max(exports) > 1e-5 or np.max(imports) >= 25.:
        raise ValueError("Pepco DC requires zero export and imports below 25 kW.")
    energy = math.hours*math.sum(imports)
    residential = a["tariff"] == "R"
    if not residential:
        if math.convex:
            math.constraints.append(energy <= GS_ENERGY_LIMIT_KWH)
        elif energy >= 6000.:
            raise ValueError("Pepco DC GS-ND study imports must stay below 6,000 kWh per cycle.")
    above30 = math.positive(energy-30., exact=True) if residential else energy
    lines = dict(
        distribution_customer=r["customer"],
        distribution_energy=math.tiered(energy,(400.,),r["distribution"]) if residential else energy*r["distribution"][0],
        generation_minimum_including_admin=r["generation_minimum"],
        generation_energy=above30*r["generation"],
        supply_administration=above30*r["administration"],
        transmission_minimum=r["transmission_minimum"],
        transmission_energy=above30*r["transmission"],
        excess_deferred_income_tax_credit=math.tiered(energy,(400.,),r["edit"]) if residential else energy*r["edit"][0],
    )
    lines.update({name:energy*rate for name,rate in r["per_kwh"].items()})
    return dict(lines=lines,next_state={},is_complete_bill=True,excluded_components=[],
                rate_sources=[*r["sources"],DER_SOURCE],rate_evidence_status="verified",
                assumption_model=None,rate_assumptions=[],metrics={**cycle,"raw_import_kwh":energy,
                    "billed_demand":False,"generation_included_kwh":30. if residential else 0.,
                    "rounded_cash_optimum_claimed":False},
                warnings=[
                    "Ordinary Pepco DC SOS with separately itemized delivery, generation, transmission and statutory riders.",
                    "Generation minimum contains the first 30 kWh and their administration. Invoice-specific rounding may differ.",
                    "BSA Adjustment II uses the official continuing rate table; the 2026 BSA report defers Adjustment I recovery.",
                    "PV/storage requires approved non-export ordinary billing. No credit bank or export settlement is modeled.",
                ])
