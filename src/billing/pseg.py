"""PSE&G New Jersey delivery and default supply, without wholesale substitution.

Rates include filed New Jersey sales/use tax. Rule 9.10 selects a filed
ratebook by the explicitly supplied bill date, not by individual service dates.
The same expressions serve numeric billing and bounded tariff optimization.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd

from .pseg_rates import DATA
TARIFF_URL = "https://nj.pseg.com/aboutpseg/regulatorypage/electrictariffs"
NET_METERING_URL = "https://nj.pseg.com/saveenergyandmoney/solarandrenewableenergy/netmetering"
TIMEZONE = "America/New_York"
RESIDENTIAL = {"RS", "RS_TOU_3P", "RHS", "RLM"}
LEGACY = {"RHS", "RLM", "HS"}
COMMERCIAL = {"GLP", "GLP_NIGHT", "LPL_S", "LPL_P", "HTS_SUB", "HTS_HV"}
PLANS = RESIDENTIAL | COMMERCIAL | {"HS"}
VOLTAGE = {"LPL_P": "primary", "HTS_SUB": "subtransmission", "HTS_HV": "high_voltage"}
LOSSES = {"secondary": .058327, "primary": .033153, "subtransmission": .020472, "high_voltage": .008605}
RESIDUAL_LOCATION = {"pnode_id":"116472957", "pnode_name":"PSEG_RESID_AGG", "zone":"",
    "source":"PSE&G official June 2023 CIEP methodology slideshow, PJM Data Miner screenshot; node 116472957 / RESIDUAL_METERED_EDC"}


def _date(value, name):
    try:
        if not isinstance(value, str):
            raise ValueError
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("PSE&G requires an explicit ISO calendar date for " + name) from exc


def _finite(value, name, minimum=0.):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value < minimum:
        raise ValueError("PSE&G " + name + " must be a finite number >= " + str(minimum))
    return float(value)


def version_on(bill_date):
    day = _date(bill_date, "bill_date") if not isinstance(bill_date, date) else bill_date
    if not date.fromisoformat(DATA["verified_start"]) <= day <= date.fromisoformat(DATA["verified_end"]):
        raise ValueError("PSE&G verified billing-date coverage is 2025-01-01 through 2026-10-15; no historical or future rate extrapolation.")
    book = next(b for b in reversed(DATA["ratebooks"]) if date.fromisoformat(b["effective_start"]) <= day)
    reconciliation = next(b for b in reversed(DATA["reconciliation"]) if date.fromisoformat(b["effective_start"]) <= day)
    return deepcopy(book), deepcopy(reconciliation)


def catalog():
    names = {"RS": "Residential Service", "RS_TOU_3P": "Residential three-period TOU",
             "RHS": "Residential Heating — existing accounts only", "RLM": "Residential Load Management — existing accounts only",
             "HS": "Building Heating — existing accounts only", "GLP": "General Lighting and Power",
             "GLP_NIGHT": "General Lighting and Power — Night Use", "LPL_S": "Large Power and Lighting — secondary",
             "LPL_P": "Large Power and Lighting — primary", "HTS_SUB": "High Tension — subtransmission",
             "HTS_HV": "High Tension — high voltage"}
    rows = []
    for plan in sorted(PLANS):
        supplies = ["bgs_rscp"] if plan in RESIDENTIAL | {"HS"} else (["bgs_ciep"] if plan in {"LPL_P", "HTS_SUB", "HTS_HV"} else ["bgs_rscp", "bgs_ciep"])
        rows.append({"plan_id": plan, "name": names[plan], "utility": "pseg_nj", "jurisdiction": "NJ",
                     "customer_class": "residential" if plan in RESIDENTIAL else "commercial",
                     "supply_arrangements": supplies, "voltage": VOLTAGE.get(plan, "secondary"),
                     "verified_start": "2025-12-08" if plan == "RS_TOU_3P" else DATA["verified_start"],
                     "verified_end": DATA["verified_end"], "billing_supported": True, "dispatch_supported": True,
                     "closed_to_new_accounts": plan in LEGACY,
                     "requires_verified_hourly_supply": supplies == ["bgs_ciep"],
                     "sources": [TARIFF_URL, NET_METERING_URL], "account_fields": account_fields(plan),
                     "representative_peak_kw": 4. if plan in RESIDENTIAL else 200. if plan=="LPL_S" else 800. if plan=="LPL_P" else 2000. if plan.startswith("HTS") else 20.,
                     "eligibility": ("Existing confirmed enrollment; closed to new accounts." if plan in LEGACY else
                          "GLP secondary: <=150 kW, utility capacity <=400 kW, and prior LPL transfer restrictions." if plan.startswith("GLP") else
                          "LPL secondary: utility-confirmed class and PLS-based default supply; monthly peak is not PLS." if plan == "LPL_S" else
                          "Utility-confirmed voltage class and default BGS enrollment.")})
    for plan, reason in {
        "WH": "Closed separately metered controlled-water-heating service; no separate appliance-meter topology in this workflow.",
        "WHS": "Separate controlled storage-water-heating meter and switching schedule required.",
        "HTS_TRANSMISSION": "Legacy high-voltage accounts converted to transmission require the account's approved metering/usage conversion.",
        "TPS": "A complete dated third-party supply contract is required; no assumed flat rate or LMP substitute.",
        "SPECIAL_PROVISIONS": "DC fast charging, area development, veterans, worship, traction, curtailable, duplicate facilities and negotiated agreements require their separate enrollment and charge models.",
    }.items():
        rows.append({"plan_id": plan, "name": plan, "utility": "pseg_nj", "jurisdiction": "NJ",
                     "billing_supported": False, "dispatch_supported": False, "unsupported_reason": reason,
                     "sources": [TARIFF_URL]})
    for row in rows:
        row.update(id=row["plan_id"], label=row["name"],
                   status="supported" if row["billing_supported"] else "unsupported",
                   reason=row.get("unsupported_reason", ""),
                   coverage=[{"start":row["verified_start"], "end":row["verified_end"]}] if row.get("verified_start") else [])
    return rows


def account_fields(plan_id="RS"):
    fields = [
        {"name": "eligibility_confirmed", "type": "boolean", "label": "Utility/account eligibility confirmed", "required": True, "default": False},
        {"name": "billing_month", "type": "date", "label": "Utility-designated billing month (first day)", "required": True},
        {"name": "bill_date", "type": "date", "label": "Bill date selecting filed rates (Rule 9.10)", "required": True},
        {"name": "cycle_kind", "type": "choice", "label": "Meter cycle", "choices": ["regular", "initial", "final"], "default": "regular", "required": True},
        {"name": "cycle_source", "type": "text", "label": "Meter cycle evidence or hypothetical assumption", "required": True},
        {"name": "power_factor", "type": "number", "label": "Account power factor", "default": .95, "required": True},
        {"name": "export_mode", "type": "choice", "label": "Export treatment", "choices": ["none", "net_metering"], "default": "none", "required": True},
        {"name": "single_meter", "type": "boolean", "label": "One utility billing meter", "default": True, "required": True},
        {"name": "no_special_provisions_confirmed", "type": "boolean", "label": "No special discounts, facilities contracts, annual seldom-use minimum or exemption", "default": False, "required": True},
        {"name": "parallel_operation_confirmed", "type": "boolean", "label": "Approved parallel PV/storage interconnection", "default": False, "required": False},
        {"name": "proration_denominator_days", "type": "number", "label": "Documented billing-month days for initial/final/outside25–36 day cycles", "required": False},
        {"name": "residential_tier_block_factor", "type": "number", "label": "Utility-confirmed multiplier for the residential600kWh block", "required": False},
        {"name": "residential_tier_block_confirmed", "type": "boolean", "label": "Utility confirmed the partial-cycle residential block allocation", "default": False, "required": False},
        {"name": "residential_tier_block_source", "type": "text", "label": "Utility evidence for the residential tier-block multiplier", "required": False},
        {"name": "net_metering_confirmed", "type": "boolean", "label": "Approved standard Class I renewable net-metering account", "default": False, "required": False},
        {"name": "net_metering_size_confirmed", "type": "boolean", "label": "Approved generation within annual electricity needs", "default": False, "required": False},
        {"name": "community_solar", "type": "boolean", "label": "Community solar enrollment (incompatible with net metering)", "default": False, "required": False},
        {"name": "anniversary_true_up", "type": "boolean", "label": "This cycle closes the account's annualized net-metering period", "default": False, "required": False},
        {"name": "opening_credit_kwh", "type": "object", "label": "Opening energy-credit banks by tariff TOU period", "default": {}, "required": False},
        {"name": "true_up_rate", "type": "object", "label": "Verified class/voltage/date-specific avoided-cost payout evidence", "required": False},
    ]
    if plan_id in LEGACY:
        fields.append({"name": "legacy_enrollment_confirmed", "type": "boolean", "label": "Already enrolled at this premise", "default": False, "required": True})
    if plan_id in COMMERCIAL:
        fields.extend([
            {"name": "generation_obligation_kw", "type": "number", "label": "Utility-assigned Generation Obligation (kW)", "required": True},
            {"name": "transmission_obligation_kw", "type": "number", "label": "Utility-assigned Transmission Obligation (kW)", "required": True},
            {"name": "obligation_source", "type": "text", "label": "Source of independently assigned obligations", "required": True},
            {"name": "obligation_effective_start", "type": "date", "label": "Obligation effective start", "required": True},
            {"name": "obligation_effective_end", "type": "date", "label": "Obligation effective end", "required": True},
            {"name": "history_peaks_kw", "type": "number_array", "label": "Eleven prior monthly meter peaks (oldest first)", "required": True},
            {"name": "self_generation_standby", "type": "boolean", "label": "Utility classified self-generation standby demand", "default": False, "required": True},
            {"name": "self_generation_classification_confirmed", "type": "boolean", "label": "PV/storage demand classification confirmed", "default": False, "required": True},
            {"name": "system_peak_hour", "type": "text", "label": "Sourced distribution-system monthly peak hour (offset timestamp; standby summer only)", "required": False},
            {"name": "system_peak_source", "type": "text", "label": "Utility evidence for the distribution-system monthly peak hour", "required": False},
            {"name": "demand_metering", "type": "choice", "label": "Utility demand measurement", "choices": ["measured", "estimated"], "default": "measured", "required": True},
            {"name": "market_data", "type": "object", "label": "CIEP official hourly PSEG_RESID_AGG CSV and metadata", "required": False},
        ])
    if plan_id.startswith("GLP") or plan_id == "LPL_S":
        fields.append({"name": "peak_load_share_kw", "type": "number", "label": "PJM Peak Load Share used for BGS eligibility (not monthly peak)", "required": True})
    if plan_id.startswith("GLP"):
        fields.extend([
            {"name": "installed_utility_capacity_kw", "type": "number", "label": "PSE&G installed electrical capacity (GLP maximum400kW)", "required": True},
            {"name": "previous_lpl_service", "type": "boolean", "label": "Previously served on LPL secondary", "default": False,"required": True},
            {"name": "lpl_history_peaks_kw", "type": "number_array", "label": "24 prior peaks if transferring from LPL", "required": False},
        ])
    return fields


def defaults(plan_id="RS"):
    plan_id = plan_id or "RS"
    if plan_id not in PLANS:
        raise ValueError("Unsupported PSE&G plan.")
    return {"tariff": plan_id, "supply": "bgs_ciep" if plan_id in {"LPL_P", "HTS_SUB", "HTS_HV"} else "bgs_rscp",
            "billing_month": "2025-07-01", "bill_date": "2025-07-31", "cycle_kind": "regular", "cycle_source": "",
            "eligibility_confirmed": False, "legacy_enrollment_confirmed": False, "power_factor": .95,
            "export_mode": "none", "net_metering_confirmed": False, "parallel_operation_confirmed": False,
            "no_special_provisions_confirmed": False, "tax_exempt": False,
            "demand_metering": "measured", "single_meter": True, "proration_denominator_days": None,
            "residential_tier_block_factor": None, "residential_tier_block_confirmed": False,
            "residential_tier_block_source": "",
            "generation_obligation_kw": None, "transmission_obligation_kw": None,
            "obligation_source": "", "obligation_effective_start": None, "obligation_effective_end": None,
            "peak_load_share_kw": None, "obligation_enrollment_confirmed": False,
            "history_peaks_kw": [], "self_generation_standby": False, "self_generation_classification_confirmed": False,
            "system_peak_hour": None, "system_peak_source":"", "anniversary_true_up": False, "opening_credit_kwh": {},
            "true_up_rate": None, "community_solar": False, "net_metering_size_confirmed": False,
            "dwelling_units": 1, "night_use_enrollment_confirmed": False, "market_data":None}


def hypothetical_defaults(plan_id="RS", year=2025):
    """Complete explicit study assumptions, never evidence of a real account.

    The caller must show the hypothetical designation and account facts. In
    particular these fixed capacity obligations are illustrative assignments,
    not estimates inferred from the site's monthly peaks.
    """
    a = defaults(plan_id)
    a.update(billing_month=f"{year}-07-01", bill_date=f"{year}-07-31",
             eligibility_confirmed=True, no_special_provisions_confirmed=True,
             cycle_source="Hypothetical complete calendar-month meter cycle; not a customer bill",
             legacy_enrollment_confirmed=plan_id in LEGACY,
             parallel_operation_confirmed=True, night_use_enrollment_confirmed=plan_id=="GLP_NIGHT",
             voltage_v={"LPL_P":13200,"HTS_SUB":26400,"HTS_HV":138000}.get(plan_id,240 if plan_id in RESIDENTIAL else 480),
             hypothetical_account=True)
    if plan_id in COMMERCIAL:
        a.update(generation_obligation_kw=15., transmission_obligation_kw=16.,
                 obligation_source="Explicit hypothetical utility-assigned obligations, held unchanged across scenarios",
                 obligation_effective_start=f"{year}-06-01",obligation_effective_end=f"{year+1}-05-31",
                 history_peaks_kw=[40.]*11,peak_load_share_kw=14.,
                 self_generation_classification_confirmed=True)
        if plan_id.startswith("GLP"):
            a.update(installed_utility_capacity_kw=100.,previous_lpl_service=False,lpl_history_peaks_kw=[])
    return a


def hypothetical_obligation_overrides(plan_id,billing_month):
    """Explicit study assignments for a named supply year, not observed PLCs.

    Annual orchestration records these per-cycle overrides rather than extending
    July's assignment backwards into January or past its stated expiry.
    """
    month=_date(billing_month,"billing_month")
    if plan_id not in COMMERCIAL:
        return {}
    year=month.year if month.month>=6 else month.year-1
    return {"generation_obligation_kw":15.,"transmission_obligation_kw":16.,
            "obligation_effective_start":f"{year}-06-01","obligation_effective_end":f"{year+1}-05-31",
            "obligation_source":"Explicit hypothetical utility assignments for supply year "+str(year)+"; not inferred from interval load"}


def objective_inputs(account,state=None,policy="exclude_opening_credits"):
    """Separate inherited cash credits from current operating incentives.

    Never erase physical demand history or fixed supply obligations. Numeric
    cash settlement must subsequently use the original account and state.
    """
    if policy not in {"exclude_opening_credits","explicit_cash_bill"}:
        raise ValueError("Select exclude_opening_credits or explicit_cash_bill.")
    a,s=deepcopy(account),deepcopy(state)
    if policy=="exclude_opening_credits":
        a["opening_credit_kwh"]={k:0. for k in a.get("opening_credit_kwh",{})}
        if s is not None:
            s["credit_kwh"]={k:0. for k in s.get("credit_kwh",{})}
    return a,s


def validate_state(account,index,state=None,equipment=None):
    """Validate evolving measured history separately from fixed enrollment.

    The supplied monthly classification stays a utility account fact. If the
    rolling history no longer proves the ordinary DER scope, require a dated
    reclassification and its actual system-peak inputs; never silently keep the
    original history or switch tariff treatment inside an optimized schedule.
    """
    if state is not None:
        if not isinstance(state,dict) or not isinstance(state.get("credit_kwh",{}),dict):
            raise ValueError("PSE&G carried state and energy-credit bank must be explicit objects.")
        credits=state.get("credit_kwh",{})
        for value in credits.values():
            _finite(value,"carried credit_kwh")
        if account.get("export_mode","none")=="none" and any(value>0 for value in credits.values()):
            raise ValueError("A positive carried net-metering credit bank cannot enter non-export mode; document the program transition and settlement instead of discarding credits.")
    if account.get("tariff") not in COMMERCIAL:
        return
    history=(state or {}).get("history_peaks_kw",account.get("history_peaks_kw"))
    if not isinstance(history,list) or len(history)!=11:
        raise ValueError("PSE&G evolving demand state requires eleven ordered prior monthly peaks.")
    for value in history:
        _finite(value,"evolving history_peaks_kw")
    if equipment and not account.get("self_generation_standby"):
        rating=sum(float(equipment.get(k,0) or 0) for k in ("pv_ac_kw","battery_kw"))
        if rating>0 and rating>=.5*max(history):
            raise ValueError("PSE&G evolving annual-peak history no longer proves the ordinary self-generation scope below50%. Supply a dated utility classification and sourced standby system-peak inputs; histories cannot be frozen.")


def validate_account(account, index, equipment=None):
    if not isinstance(account, dict) or account.get("tariff") not in PLANS:
        raise ValueError("Select a supported PSE&G New Jersey delivery tariff.")
    plan = account["tariff"]
    if account.get("eligibility_confirmed") is not True or account.get("single_meter") is not True:
        raise ValueError("Confirm PSE&G service, class eligibility and one utility billing meter; multi-meter demand sums cannot be inferred.")
    if account.get("no_special_provisions_confirmed") is not True or account.get("tax_exempt", False):
        raise ValueError("This model requires an ordinary taxable account without special provisions, negotiated facilities charges or discounts.")
    pf = _finite(account.get("power_factor"), "power_factor")
    if not .85 <= pf <= 1:
        raise ValueError("PSE&G requires power factor >=85%; corrective equipment/account treatment must be resolved first.")
    if plan in LEGACY and account.get("legacy_enrollment_confirmed") is not True:
        raise ValueError(plan + " is closed to new accounts; confirm existing eligible enrollment at this premise.")
    if plan == "GLP_NIGHT" and account.get("night_use_enrollment_confirmed") is not True:
        raise ValueError("GLP Night Use requires a utility time-of-day meter and confirmed two-year enrollment.")
    idx = pd.DatetimeIndex(index)
    if idx.tz is None or str(idx.tz) != TIMEZONE or len(idx) < 2 or not idx.is_unique or not idx.is_monotonic_increasing:
        raise ValueError("PSE&G needs ordered, unique America/New_York interval-start timestamps.")
    minutes = (idx[1]-idx[0]).total_seconds()/60
    if minutes not in (15, 30) or not (np.diff(idx.asi8) == pd.Timedelta(minutes=minutes).value).all():
        raise ValueError("PSE&G studies require complete 15- or 30-minute interval averages without missing physical intervals.")
    if plan in {"LPL_P", "HTS_SUB", "HTS_HV"} and minutes != 15:
        raise ValueError("PSE&G primary/HTS demand requires actual 15-minute records.")
    if idx[0] != idx[0].normalize() or idx[-1]+pd.Timedelta(minutes=minutes) != idx[-1].normalize()+pd.DateOffset(days=1):
        raise ValueError("Supply complete local service days for the meter cycle, including DST intervals.")
    days = len(idx.normalize().unique())
    if not 1 <= days <= 62:
        raise ValueError("PSE&G requires one explicit meter cycle of 1–62 complete service days.")
    billing_month = _date(account.get("billing_month"), "billing_month")
    bill_date = _date(account.get("bill_date"), "bill_date")
    if billing_month.day != 1 or bill_date < idx[-1].date() or (bill_date-idx[-1].date()).days > 35:
        raise ValueError("Supply a consistent utility billing month and a bill date on/after the final service day.")
    if abs((bill_date-billing_month).days) > 62:
        raise ValueError("Utility billing month and bill date are inconsistent.")
    version_on(bill_date)
    if plan == "RS_TOU_3P" and bill_date < date(2025, 12, 8):
        raise ValueError("PSE&G RS-TOU 3P did not take effect until December 8, 2025.")
    if not isinstance(account.get("cycle_source"), str) or not account["cycle_source"].strip():
        raise ValueError("Document the meter cycle or explicitly label a hypothetical cycle.")
    kind = account.get("cycle_kind")
    if kind not in {"regular", "initial", "final"}:
        raise ValueError("Declare regular, initial or final meter service.")
    if kind != "regular" or not 25 <= days <= 36:
        denominator = _finite(account.get("proration_denominator_days"), "proration_denominator_days", 1)
        if denominator not in (28, 29, 30, 31):
            raise ValueError("Document the billing-month day denominator for Rule 9.7 proration.")
    elif account.get("proration_denominator_days") is not None:
        raise ValueError("Ordinary 25–36 day bills do not use general daily charge proration.")
    monthly_factor = days/account["proration_denominator_days"] if kind != "regular" or not 25 <= days <= 36 else 1.
    block_factor = account.get("residential_tier_block_factor")
    if block_factor is not None:
        if plan not in {"RS", "RHS"}:
            raise ValueError("Only RS/RHS use the residential600kWh block; do not attach that factor to a TOU or commercial plan.")
        if (_finite(block_factor,"residential_tier_block_factor") <= 0
                or account.get("residential_tier_block_confirmed") is not True
                or not isinstance(account.get("residential_tier_block_source"),str)
                or not account["residential_tier_block_source"].strip()):
            raise ValueError("A residential tier-block multiplier requires positive utility-confirmed allocation and its source.")
    interpreted_block = plan in {"RS","RHS"} and monthly_factor != 1. and block_factor is None
    units = account.get("dwelling_units", 1)
    if type(units) is not int or units != 1:
        raise ValueError("This account path models one dwelling/unit; master-meter block multiplication needs a separate confirmed topology.")
    supply = account.get("supply")
    if supply not in {"bgs_rscp", "bgs_ciep"}:
        raise ValueError("Third-party supply requires a complete dated contract; no PSE&G BGS or convenient PJM price is substituted.")
    if plan in RESIDENTIAL and supply != "bgs_rscp":
        raise ValueError("Residential PSE&G default service is BGS-RSCP, not BGS-CIEP.")
    if plan == "HS" and supply != "bgs_rscp":
        raise ValueError("The closed HS heating path supports confirmed BGS-RSCP enrollment; hourly HS needs separately verified account-obligation treatment.")
    if plan in {"LPL_P", "HTS_SUB", "HTS_HV"} and supply != "bgs_ciep":
        raise ValueError("PSE&G primary and HTS default supply requires BGS-CIEP.")
    if plan in COMMERCIAL:
        for k in ("generation_obligation_kw", "transmission_obligation_kw"):
            _finite(account.get(k), k)
        if not str(account.get("obligation_source", "")).strip():
            raise ValueError("Document independent generation and transmission obligations; meter peaks are not substitutes.")
        lo,hi = (_date(account.get(k), k) for k in ("obligation_effective_start", "obligation_effective_end"))
        if not lo <= bill_date <= hi:
            raise ValueError("The utility-assigned obligation effective period does not cover this bill.")
        history = account.get("history_peaks_kw")
        if not isinstance(history, list) or len(history) != 11:
            raise ValueError("Supply eleven previous monthly meter peaks, oldest first, for demand history and DER classification.")
        for x in history:
            _finite(x, "history_peaks_kw")
        if account.get("self_generation_classification_confirmed") is not True:
            raise ValueError("Confirm the utility's ordinary versus self-generation standby demand classification.")
        if plan.startswith("GLP"):
            if _finite(account.get("installed_utility_capacity_kw"),"installed_utility_capacity_kw")>400:
                raise ValueError("GLP cannot serve utility-installed electrical capacity over400kW.")
            if account.get("previous_lpl_service") not in (True,False):
                raise ValueError("Declare previous LPL-secondary enrollment; it cannot be inferred from current load.")
            if account.get("previous_lpl_service"):
                old=account.get("lpl_history_peaks_kw")
                if not isinstance(old,list) or len(old)!=24:
                    raise ValueError("A transfer from LPL requires24prior consecutive monthly peaks.")
                if any(_finite(x,"lpl_history_peaks_kw")>100 for x in old):
                    raise ValueError("Prior LPL-secondary demand over100kW within24months prevents GLP transfer.")
        if account.get("self_generation_standby") and 6 <= billing_month.month <= 9:
            if not str(account.get("system_peak_source","")).strip():
                raise ValueError("Document the utility source of the distribution-system monthly peak hour.")
            h = account.get("system_peak_hour")
            try:
                h = pd.Timestamp(h)
                if h.tz is None or h.minute or h.second or h.tz_convert(TIMEZONE) < idx[0] or h.tz_convert(TIMEZONE)+pd.Timedelta(hours=1) > idx[-1]+pd.Timedelta(minutes=minutes):
                    raise ValueError
            except (TypeError, ValueError):
                raise ValueError("Self-generation summer demand requires the sourced PSE&G distribution-system monthly peak hour within this cycle.")
        if plan in {"GLP", "GLP_NIGHT", "LPL_S"}:
            pls = _finite(account.get("peak_load_share_kw"), "peak_load_share_kw")
            if plan == "LPL_S" and pls >= 500 and supply != "bgs_ciep":
                raise ValueError("LPL secondary with PLS >=500 kW requires BGS-CIEP; monthly maximum does not establish PLS.")
            if supply == "bgs_ciep" and pls < 500 and account.get("obligation_enrollment_confirmed") is not True:
                raise ValueError("Optional CIEP enrollment must have been elected by the filed January deadline for June service.")
        if account.get("demand_metering", "measured") not in {"measured", "estimated"}:
            raise ValueError("Declare the utility's measured or estimated demand enrollment.")
        if account.get("demand_metering") == "estimated" and (plan!="GLP" or account.get("self_generation_standby") or max(history) >= 10 or account.get("estimated_demand_enrollment_confirmed") is not True):
            raise ValueError("Estimated GLP demand needs utility enrollment, no prior >=10 kW measured peak and <=1,000 kWh historical bills.")
    equipment = equipment or {}
    if any(float(equipment.get(k, 0) or 0) > 0 for k in ("pv_ac_kw", "battery_kw", "pv_kw", "storage_kw")) and account.get("parallel_operation_confirmed") is not True:
        raise ValueError("Confirm utility-approved parallel PV/storage operation; non-export does not waive interconnection requirements.")
    if plan in COMMERCIAL and equipment:
        nameplate=sum(float(equipment.get(k,0) or 0) for k in ("pv_ac_kw","battery_kw"))
        if nameplate and not account.get("self_generation_standby") and nameplate >= .5*max(account["history_peaks_kw"]):
            raise ValueError("Configured combined PV/storage output reaches50%of the supplied annual demand reference. Confirm self-generation standby treatment and the actual annual peak; ordinary demand treatment cannot be assumed.")
    mode = account.get("export_mode", "none")
    if mode not in {"none", "net_metering"}:
        raise ValueError("PSE&G export requires standard approved net metering; no guessed export sale price.")
    if mode=="none" and (account.get("opening_credit_kwh") or account.get("anniversary_true_up")):
        raise ValueError("Opening credits and anniversary settlement require the approved net-metering account; they cannot be silently discarded by non-export mode.")
    if mode == "net_metering" and (account.get("net_metering_confirmed") is not True or account.get("net_metering_size_confirmed") is not True or account.get("community_solar") is not False):
        raise ValueError("Confirm approved Class I renewable net metering, annual-needs system sizing and no community-solar enrollment.")
    if mode == "net_metering" and supply == "bgs_ciep":
        raise ValueError("CIEP hourly net-metering cash/credit allocation requires an account-specific verified settlement model; ordinary CIEP non-export remains supported.")
    if supply=="bgs_ciep":
        _ciep_prices(idx,account,version_on(bill_date)[0]["rates"]["ciep"])
    return {"days": days, "minutes": minutes, "billing_month": billing_month, "bill_date": bill_date,
            "monthly_factor": monthly_factor,"tier_block_factor":monthly_factor if block_factor is None else block_factor,
            "tier_block_interpretation":interpreted_block}


def periods(index, plan):
    index = pd.DatetimeIndex(index)
    weekday = index.dayofweek < 5
    if plan == "RS_TOU_3P":
        # The tariff says PJM holidays, not merely NERC off-peak holidays.
        holidays = {2025: ["01-01", "01-20", "02-17", "05-26", "07-04", "09-01", "11-27", "11-28", "12-25"],
                    2026: ["01-01", "01-19", "02-16", "05-25", "07-04", "09-07", "11-26", "11-27", "12-25"]}
        if any(y not in holidays for y in index.year.unique()):
            raise ValueError("PSE&G RS-TOU holiday calendars are verified only for 2025 and 2026.")
        holiday = np.array([t.strftime("%m-%d") in holidays[t.year] for t in index])
        peak = weekday & ~holiday & (index.hour >= 16) & (index.hour < 21)
        off = index.hour < 6
        return {"on_peak": peak, "mid_peak": ~peak & ~off, "off_peak": off}
    if plan == "RLM":
        clock = index.tz_convert("Etc/GMT+5")  # filed EST, including summer.
        peak = (clock.dayofweek < 5) & (clock.hour >= 7) & (clock.hour < 21)
    elif plan == "GLP_NIGHT":
        peak = weekday & (index.hour >= 8) & (index.hour < 20)
    elif plan.startswith("LPL") or plan.startswith("HTS"):
        peak = weekday & (index.hour >= 8) & (index.hour < 22)
    else:
        return {"all": np.ones(len(index), dtype=bool)}
    return {"on_peak": np.asarray(peak), "off_peak": np.asarray(~peak)}


def import_ciep_prices(csv_text, metadata, index):
    """Reuse the revision/DST aware PJM adapter; raw licensed files stay private."""
    from ..signal_pipeline.providers.pjm import PJMProvider
    if not isinstance(metadata,dict) or metadata.get("market") != "REAL_TIME_HOURLY":
        raise ValueError("CIEP requires settlements-verified real-time hourly LMP, never day-ahead or preliminary five-minute prices.")
    hours = pd.DatetimeIndex(index).tz_convert("UTC").floor("h").unique()
    frame,provenance = PJMProvider.import_historical_file(csv_text,metadata,hours[0],hours[-1]+pd.Timedelta(hours=1),RESIDUAL_LOCATION)
    if "type" not in frame or not frame.type.eq("RESIDUAL_METERED_EDC").all():
        raise ValueError("Every CIEP row must identify PSEG_RESID_AGG as RESIDUAL_METERED_EDC; no hub or generic zone.")
    return frame.set_index("timestamp").total_lmp_rt,provenance


def _ciep_prices(index, account, rates):
    payload = account.get("market_data")
    if not isinstance(payload,dict) or set(payload) != {"csv_text","metadata"}:
        raise ValueError("BGS-CIEP needs market_data={csv_text,metadata}: an official PJM hourly PSEG_RESID_AGG file with current revisions. RSCP requires no wholesale data.")
    series,provenance = import_ciep_prices(payload["csv_text"],payload["metadata"],index)
    wanted = series.index
    voltage = VOLTAGE.get(account["tariff"], "secondary")
    factor = ((Decimal(1)-Decimal(str(rates["mean_marginal_loss_pct"]))/Decimal(100)) /
              (Decimal(1)-Decimal(str(LOSSES[voltage]))))
    # The official worked worksheet rounds each hourly unit-charge stage to
    # six decimals using Excel ROUND (half away from zero), including negative
    # LMPs. Binary/NumPy ties-to-even would silently erase a half-micro-dollar
    # price. Ancillary charges apply to total monthly kWh separately.
    def rounded(value):
        return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    expansion = rounded(factor)
    tax = Decimal("1.06625")
    hourly = [float(rounded(rounded(rounded(Decimal(str(value))/Decimal(1000))*expansion)*tax))
              for value in series.to_numpy()]
    ancillary = float(rounded(rounded(Decimal("0.006")*expansion)*tax))
    return pd.Series(hourly, index=wanted).reindex(pd.DatetimeIndex(index).tz_convert("UTC").floor("h")).to_numpy(), ancillary, float(factor), provenance


def charge_lines(index, imports_kw, exports_kw, account, *, math, state=None):
    facts = validate_account(account, index)
    validate_state(account,index,state)
    idx = pd.DatetimeIndex(index)
    plan = account["tariff"]
    baseplan = "GLP" if plan == "GLP_NIGHT" else plan
    riderplan = "RS" if plan == "RS_TOU_3P" else baseplan
    book, rec = version_on(facts["bill_date"])
    rates = book["rates"]
    delivery = rates["delivery"][baseplan if plan == "GLP_NIGHT" else plan]
    supply = account["supply"]
    season = int(6 <= facts["billing_month"].month <= 9)
    f = facts["monthly_factor"]
    hours = math.hours
    masks = periods(idx, plan)
    history = list((state or {}).get("history_peaks_kw", account.get("history_peaks_kw", [])))
    opening = deepcopy((state or {}).get("credit_kwh", account.get("opening_credit_kwh", {})))
    net_metering = account.get("export_mode") == "net_metering"
    imported = math.sum(imports_kw)*hours
    exported = math.sum(exports_kw)*hours
    if not math.convex:
        a,b = np.asarray(imports_kw, float),np.asarray(exports_kw, float)
        if a.shape != (len(idx),) or b.shape != (len(idx),) or not np.isfinite(a).all() or not np.isfinite(b).all() or np.any(a < -1e-6) or np.any(b < -1e-6):
            raise ValueError("PSE&G meter flows must be finite nonnegative interval-average kW on the exact grid.")
        if np.any(np.minimum(a,b) > 1e-5):
            raise ValueError("PSE&G meter imports and exports cannot be simultaneous.")
        if not net_metering and np.max(b) > 1e-6:
            raise ValueError("Non-export PSE&G studies must curtail surplus PV, not dispose of it as unpaid export.")
    elif not net_metering:
        math.constraints.append(exports_kw == 0)
    bank = {}; volume = {}
    if set(opening)-set(masks):
        raise ValueError("Opening net-metering credit banks must match this tariff's TOU periods.")
    for key, mask in masks.items():
        imp = math.sum(imports_kw[mask])*hours
        exp = math.sum(exports_kw[mask])*hours
        if net_metering:
            previous = opening.get(key, 0.)
            if not math.convex:
                _finite(previous, "opening_credit_kwh")
            volume[key] = math.positive(imp-exp-previous, exact=True)
            bank[key] = math.positive(previous+exp-imp, exact=True)
        else:
            volume[key] = imp
    total_billed = sum(volume.values())
    lines = {"customer": delivery["customer"]*f}
    if plan in {"RS", "RHS"}:
        energy = volume["all"]
        boundary = 600*facts["tier_block_factor"]
        first,excess=delivery["tier_first"][season],delivery["tier_excess"][season]
        # A filed block with identical rates is algebraically linear. Avoid
        # exact tier selectors that add no rate distinction to the model.
        lines["distribution_energy"] = energy*first if first==excess else math.tiered(energy,[boundary],[first,excess])
    elif plan in {"RS_TOU_3P", "RLM"}:
        lines["distribution_energy"] = sum(volume[k]*delivery[k][season] for k in masks)
    elif plan == "GLP_NIGHT":
        lines["distribution_energy"] = volume["on_peak"]*delivery["energy"][season]+volume["off_peak"]*delivery["energy"][0]
    else:
        lines["distribution_energy"] = total_billed*delivery["energy"][season]
    peak = 0.; annual = 0.; summer_peak = 0.
    if plan in COMMERCIAL:
        minutes = 30 if VOLTAGE.get(plan, "secondary") == "secondary" else 15
        if account.get("demand_metering") == "estimated":
            peak = imported/100
            if math.convex:
                math.constraints.append(imported <= 1000)
            elif imported > 1000+1e-6:
                raise ValueError("Utility estimated GLP enrollment cannot persist above 1,000 kWh; require measured demand.")
        else:
            peak = math.demand(imports_kw, idx, minutes)
        annual = math.maximum([peak]+history)
        standby = bool(account.get("self_generation_standby"))
        annual_basis = annual if standby or plan.startswith("HTS") else peak
        lines["distribution_annual_demand"] = annual_basis*delivery["annual_demand"]*f
        if season and delivery["summer_demand"]:
            if account.get("demand_metering")=="estimated":
                summer_mask=None
            elif standby:
                h = pd.Timestamp(account["system_peak_hour"]).tz_convert(TIMEZONE)
                summer_mask = (idx>=h)&(idx<h+pd.Timedelta(hours=1))
            elif plan in {"GLP", "GLP_NIGHT"}:
                summer_mask = masks.get("on_peak")
            else:
                summer_mask = masks["on_peak"]
            summer_peak = peak if account.get("demand_metering")=="estimated" else math.demand(imports_kw, idx, minutes, mask=summer_mask)
            lines["distribution_summer_demand"] = summer_peak*delivery["summer_demand"]*f
        if plan.startswith("GLP"):
            if math.convex:
                math.constraints.append(peak <= 150)
            elif peak > 150+1e-5:
                raise ValueError("GLP measured peak exceeds 150 kW; LPL eligibility must be established.")
    voltage = VOLTAGE.get(plan, "secondary")
    riders = rates["riders"]
    lines["societal_benefits"] = total_billed*riders["societal_benefits"][voltage]
    lines["nonutility_generation"] = total_billed*riders["nonutility_generation"]["residential" if plan in RESIDENTIAL else voltage]
    for name in ("zero_emission", "solar_pilot", "green_programs", "covid"):
        lines[name] = total_billed*riders[name]
    lines["tax_adjustment_credit"] = total_billed*riders["tax_adjustment"][riderplan]
    cip = riders["conservation"].get(riderplan, 0.)
    lines["conservation_incentive"] = (peak*f if plan in {"GLP", "GLP_NIGHT", "LPL_S"} else total_billed)*cip
    hourly_factor = None; market_provenance = None
    if supply == "bgs_rscp":
        s = rates["rscp"][baseplan if plan == "GLP_NIGHT" else plan]
        if plan in {"RS", "RHS"}:
            first,excess=s["tier_first"][season],s["tier_excess"][season]
            lines["supply_energy_capacity"] = (volume["all"]*first if first==excess else
                math.tiered(volume["all"],[600*facts["tier_block_factor"]],[first,excess]))
            lines["supply_transmission"] = total_billed*s["transmission"][season]
        elif plan in {"RS_TOU_3P", "RLM"}:
            lines["supply_energy_capacity"] = sum(volume[k]*s["energy"][k][season] for k in masks)
            lines["supply_transmission"] = sum(volume[k]*s["transmission"][k][season] for k in masks)
        elif plan == "GLP_NIGHT":
            lines["supply_energy"] = volume["on_peak"]*s["energy"][season]+volume["off_peak"]*s["night_energy"][season]
        elif plan == "LPL_S":
            lines["supply_energy"] = sum(volume[k]*s["energy"][k][season] for k in masks)
        else:
            lines["supply_energy"] = total_billed*s["energy"][season]
            if plan == "HS":
                lines["supply_transmission"] = total_billed*s["transmission"][season]
        if plan in {"GLP", "GLP_NIGHT", "LPL_S"}:
            lines["supply_capacity"] = account["generation_obligation_kw"]*s["capacity"]*f
            lines["supply_transmission"] = account["transmission_obligation_kw"]*s["transmission"]*f
    else:
        hourly, ancillary, hourly_factor, market_provenance = _ciep_prices(idx, account, rates["ciep"])
        lines["supply_hourly_energy"] = math.dot(imports_kw, hourly)*hours
        lines["supply_ancillary"] = imported*ancillary
        lines["supply_capacity"] = account["generation_obligation_kw"]*rates["ciep"]["capacity"]*f
        lines["supply_transmission"] = account["transmission_obligation_kw"]*rates["ciep"]["transmission"]*f
        lines["ciep_standby"] = imported*rates["ciep"]["standby"]
    lines["supply_reconciliation"] = total_billed*rec["rscp" if supply == "bgs_rscp" else "ciep"]
    # Only residential schedules prescribe a monthly service-charge floor.
    # Commercial GLP/LPL/HTS instead state a separately enrolled seldom-use
    # annual minimum, excluded by the explicit ordinary-account confirmation.
    before_minimum = sum(lines.values())
    lines["minimum_bill_adjustment"] = (math.positive(delivery["customer"]*f-before_minimum, exact=True)
                                         if plan in RESIDENTIAL else 0.)
    if plan in RESIDENTIAL:
        month = facts["billing_month"]
        lines["generation_capacity_deferral"] = (-30. if date(2025,7,1)<=month<=date(2025,8,1) else
                            10. if date(2025,9,1)<=month<=date(2026,2,1) else 0.)*f
    warnings = []
    if facts["tier_block_interpretation"]:
        warnings.append("Incomplete residential partial-cycle estimate: Rule9.7 verifies monthly-charge proration but does not explicitly specify600kWh tier-block allocation. The study provisionally scales that block by service days/billing-month days; supply a utility-confirmed residential_tier_block_factor and source for a complete bill.")
    if plan in LEGACY:
        warnings.append("Closed tariff; only confirmed existing enrollment is represented.")
    if net_metering and account.get("anniversary_true_up"):
        payout = account.get("true_up_rate")
        remaining = sum(bank.values())
        if payout is None and (math.convex or remaining <= 1e-7):
            if math.convex:
                math.constraints.append(remaining==0)
                warnings.append("Anniversary dispatch is constrained to zero remaining energy credits because no verified payout rate was supplied.")
            lines["net_metering_annual_payout"] = 0.
        else:
            required = {"usd_per_kwh", "source", "effective_start", "effective_end", "customer_class", "voltage"}
            if not isinstance(payout,dict) or not required <= payout.keys():
                raise ValueError("A remaining anniversary bank needs the verified PSE&G avoided-wholesale-cost payout for this customer class/voltage; PEP or retail rates are not substitutes.")
            r = _finite(payout["usd_per_kwh"],"true_up_rate")
            if not str(payout["source"]).strip() or not _date(payout["effective_start"],"payout start") <= facts["bill_date"] <= _date(payout["effective_end"],"payout end") or payout["customer_class"] != ("residential" if plan in RESIDENTIAL else "commercial") or payout["voltage"] != voltage:
                raise ValueError("True-up payout evidence must match this bill date, customer class and voltage.")
            lines["net_metering_annual_payout"] = -remaining*r
        bank = {k:0. for k in bank}
    metrics = {"import_kwh": imported,"export_kwh":exported,"billed_kwh":total_billed,
               "monthly_peak_kw":peak,"annual_peak_kw":annual,"summer_peak_kw":summer_peak,
               "billing_month":account["billing_month"],"bill_date":account["bill_date"],
               "rate_version":book["source"]["document_id"],"reconciliation_version":rec["effective_start"],
               "source":book["source"],"reconciliation_source":rec["source"],
               "sales_use_tax_included":True,"ciep_loss_expansion_factor":hourly_factor,
               "market_provenance":market_provenance,
               "billing_days":facts["days"],"monthly_charge_factor":f,
               "residential_tier_block_factor":facts["tier_block_factor"] if plan in {"RS","RHS"} else None,
               "residential_tier_block_interpretation":facts["tier_block_interpretation"]}
    return {"lines":lines,"metrics":metrics,"next_state":{"history_peaks_kw":(history+[peak])[-11:] if plan in COMMERCIAL else [],"credit_kwh":bank},
            "warnings":warnings,"is_complete_bill":not facts["tier_block_interpretation"]}


def bill(index, imports_kw, exports_kw, account, state=None):
    from .regional_math import BillingMath
    result = charge_lines(index,np.asarray(imports_kw,float),np.asarray(exports_kw,float),account,math=BillingMath(index),state=state)
    return {**result,"total_usd":float(sum(result["lines"].values()))}
