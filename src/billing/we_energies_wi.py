"""Wisconsin Electric ordinary residential and small commercial non-export billing.

One charge expression supplies both numerical bills and dispatch objectives.
Complete calendar cycles intentionally avoid unverified bill-date allocation.
"""
from copy import deepcopy
from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd

from ..tou_calendar import HolidayCalendar
from .we_energies_wi_rates import (COVERAGE, PLANS, SOURCES, PROVISIONAL_COVERAGE,
    PROVISIONAL_MODEL, PROVISIONAL_ASSUMPTIONS, service_rates)

UTILITY = "we_energies_wisconsin"
TIMEZONE = "America/Chicago"


@lru_cache(maxsize=32)
def holidays(year):
    may = date(year, 5, 31)
    sep = date(year, 9, 1)
    nov = date(year, 11, 1)
    actual = {date(year, 1, 1),
              may-timedelta(days=may.weekday()), date(year, 7, 4),
              sep+timedelta(days=(-sep.weekday()) % 7),
              nov+timedelta(days=(3-nov.weekday()) % 7+21), date(year, 12, 25)}
    # Tariff lists six legal holidays. Wisconsin995.20 observes Sunday on
    # Monday; a Saturday holiday stays Saturday, not the preceding Friday.
    return frozenset(actual | {d+timedelta(days=1) for d in actual if d.weekday() == 6})


CALENDAR = HolidayCalendar("Wisconsin Electric six legal holidays, Sunday Monday only", holidays, (SOURCES[3], SOURCES[6]))


def periods(index, plan, on_peak_start_hour=9):
    idx = pd.DatetimeIndex(index)
    if plan not in PLANS or str(idx.tz) != TIMEZONE:
        raise ValueError("Select Wisconsin Electric ordinary plan and America/Chicago timestamps.")
    if on_peak_start_hour not in (7, 8, 9, 10) or isinstance(on_peak_start_hour, bool):
        raise ValueError("Rg2 requires its confirmed7/8/9/10am twelve-hour peak window.")
    start = on_peak_start_hour if plan == "Rg2" else 9
    hour = idx.hour.to_numpy()+idx.minute.to_numpy()/60
    peak = ((idx.dayofweek < 5) & ~CALENDAR.mask(idx).to_numpy()
            & (hour >= start) & (hour < start+12)) if plan in ("Rg2", "Cg6") else np.zeros(len(idx), bool)
    return dict(peak=np.asarray(peak), off=~np.asarray(peak))


def interval_rates(index, plan, on_peak_start_hour=9, *, mode="verified"):
    idx = pd.DatetimeIndex(index)
    p = periods(idx, plan, on_peak_start_hour)
    rates = {d: service_rates(d, plan, mode=mode) for d in set(idx.date)}
    energy = np.asarray([rates[d]["energy"][0 if is_peak else 1] for d, is_peak in zip(idx.date, p["peak"])])
    return dict(energy=energy, **{k: np.asarray([rates[d][k] for d in idx.date])
        for k in ("fuel", "fuel_reconciliation", "environmental_control")})


def _evidence_mode(account):
    mode = account.get("rate_evidence_mode", "verified")
    accepted = account.get("provisional_assumptions_accepted", False)
    if (mode not in ("verified", "provisional_2025") or type(accepted) is not bool
            or mode == "provisional_2025" and accepted is not True):
        raise ValueError("Provisional Wisconsin Electric2025 ECC requires explicit mode selection and boolean acceptance of the documented assumptions.")
    return mode


def evidence(index, account):
    """Return assumptions actually used; accepting them cannot verify a rate."""
    mode = _evidence_mode(account)
    days = sorted(set(pd.DatetimeIndex(index).date))
    versions = [service_rates(day, account["tariff"], mode=mode) for day in days]
    used = deepcopy(PROVISIONAL_ASSUMPTIONS) if any(v["rate_evidence_status"] == "provisional" for v in versions) else []
    return dict(rate_evidence_status="provisional" if used else "verified",
        assumption_model=PROVISIONAL_MODEL if used else None, rate_assumptions=used,
        objective_scope="provisional_modeled_bill" if used else "complete_utility_bill")


def account_fields(plan="Rg1"):
    fields = [dict(name=k, type="boolean", default=False, required=True, label=label) for k, label in (
        ("eligibility_confirmed", "Wisconsin Electric/We Energies Wisconsin territory and ordinary selected tariff independently confirmed"),
        ("ordinary_service_confirmed", "Ordinary AC bundled account: one meter and service line, no assistance discounts, credits, special facilities, contracts or rider exemptions"),
        ("full_monthly_charges_confirmed", "Complete calendar meter cycle with full monthly charges; no partial or shifted cycle"),
        ("local_charges_confirmed", "Unincorporated Waukesha County: ordinary taxable electric service, no city/franchise or special charges"))]
    fields += [dict(name="rate_evidence_mode", type="choice", choices=["verified", "provisional_2025"], default="verified",
            label="Rate evidence: verified dates only or explicitly provisional2025 ECC", required=True),
        dict(name="provisional_assumptions_accepted", type="boolean", default=False,
            label="I accept carrying June2025 ECC through July–December2025; actual rates remain unverified and bills/savings are provisional estimates"),
        dict(name="tax_jurisdiction", type="text", choices=["waukesha_county_unincorporated"], label="Explicit tax jurisdiction; independent of utility/location map"),
        dict(name="tax_source", type="text", required=True, label="Jurisdiction and non-exempt status evidence, or explicit hypothetical account"),
        dict(name="cycle_source", type="text", required=True, label="Complete meter-cycle evidence or explicit hypothetical calendar-cycle assumption"),
        dict(name="dg_enrollment_confirmed", type="boolean", default=False, label="PV/storage: approved CGS-NP non-purchase enrollment/interconnection, ordinary retail tariff retained, no export or supplemental fees"),
        dict(name="dg_source", type="text", label="Non-export approval reference or explicit hypothetical assumption; omit personal information")]
    if plan in ("Rg1", "Rg2"):
        fields.append(dict(name="principal_residence_confirmed", type="boolean", required=True,
            label="Permanent principal residence: November–April billing-date tax exemption applies; not a second home or transient rental"))
    if plan in ("Rg2", "Cg6"):
        fields.append(dict(name="tou_enrollment_confirmed", type="boolean", required=True,
            label="Ordinary TOU enrollment, metering and12-month term confirmed; Rg2 selected window remains fixed"))
    if plan == "Rg2":
        fields.append(dict(name="on_peak_start_hour", type="number", required=True, default=9,
            label="Confirmed Rg2 peak window start7,8,9 or10am; lasts12hours, held12months"))
    if plan in ("Cg1", "Cg6"):
        fields.append(dict(name="small_general_confirmed", type="boolean", required=True,
            label="Current utility-approved Cg1/Cg6 non-demand classification and prior12-month history confirmed; every study cycle stays below329kWh/day"))
    return fields


def defaults(plan="Rg1"):
    if plan not in PLANS:
        raise ValueError("Select Wisconsin Electric ordinary Rg1/Rg2/Cg1/Cg6.")
    res = plan in ("Rg1", "Rg2")
    return dict(tariff=plan, supply="bundled", export_mode="none", eligibility_confirmed=False,
        ordinary_service_confirmed=False, full_monthly_charges_confirmed=False, local_charges_confirmed=False,
        tax_jurisdiction="waukesha_county_unincorporated", tax_source="", cycle_source="",
        rate_evidence_mode="verified", provisional_assumptions_accepted=False,
        tou_enrollment_confirmed=False, small_general_confirmed=False, principal_residence_confirmed=False,
        dg_enrollment_confirmed=False, dg_source="",
        opening_credit_usd=0., billing_month="2026-07-01", bill_date="2026-07-31", cycle_kind="regular",
        voltage="secondary", phase="single" if res else "three", voltage_v=240. if res else 480., power_factor=1., meter_count=1, service_line_count=1, on_peak_start_hour=9)


def hypothetical_defaults(plan="Rg1"):
    a = defaults(plan)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True, full_monthly_charges_confirmed=True,
        local_charges_confirmed=True, tou_enrollment_confirmed=True, small_general_confirmed=True,
        principal_residence_confirmed=True, hypothetical_account=True,
        tax_source="Explicit hypothetical unincorporated Waukesha County ordinary account:5%state; permanent principal residenceNovember–April bills exempt; no additional exemptions/fees",
        cycle_source="Explicit hypothetical complete calendar meter cycle; not a customer statement",
        dg_enrollment_confirmed=True, dg_source="Hypothetical utility-approved CGS-NP non-purchase PV/storage, ordinary retail tariff retained, no export or additional fees")
    return a


def catalog():
    labels = {"Rg1": "Residential standard", "Rg2": "Residential Time of Use",
              "Cg1": "Small commercial General Secondary", "Cg6": "Small commercial General Secondary Time of Use"}
    return [dict(id=p, label="We Energies Wisconsin "+labels[p], status="supported",
        customer_class="residential" if p in ("Rg1", "Rg2") else "commercial",
        coverage=[dict(start=s, end=e) for s, e in COVERAGE], voltage="secondary",
        provisional_coverage=[dict(start=s, end=e) for s, e in PROVISIONAL_COVERAGE],
        provisional_assumptions=deepcopy(PROVISIONAL_ASSUMPTIONS),
        solar_modes=["non_export"], supply_arrangements=["bundled"], equipment_modes=["grid_only", "pv_only", "pv_battery"],
        representative_peak_kw=3. if p in ("Rg1", "Rg2") else 10., account_fields=account_fields(p), sources=SOURCES,
        eligibility="Explicit Wisconsin Electric Wisconsin account, ordinary domestic/small commercial secondary service, one meter/service line, complete calendar cycles and unincorporated Waukesha County tax status. Confirm eligibility independently of coordinates.",
        limitations=["Verified complete-rate coverage January–June2025 and January–September2026. July–December2025 ECC needs explicit provisional_2025 mode and assumption acceptance; full-year2025 is a provisional study, not a verified tariff reconstruction. Complete calendar cycles only.",
            "Rg2 customer-selected12h window beginning7/8/9/10am; Cg6 fixed9am–9pm weekdays. Six legal holidays; Sunday Monday observance, no Saturday Friday substitution.",
            "Small General has no demand charge. Imports must stay below329kWh/day for every study scenario; current classification and prior history still need utility confirmation.",
            "Unincorporated Waukesha5% tax; residential November–April billing-date exemption. State assistance fee is lower of3%electric subtotal or$3.15res/$10.66commercial, not taxable.",
            "Non-export, approved ordinary service only; first DER scope limits aggregate PV nameplate plus battery discharge to40kW as a conservative model bound, not a statutory eligibility rule.",
            "No Cg2 or larger demand plans, special80%off-peak eligibility exception, exports/NEM settlement, standalone storage, partial/crossing cycles or special contracts. No MISO LMP/PLC adder or CAISO carbon substitution."])
        for p in PLANS]


def cycle_review(a, index):
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2 or str(idx.tz) != TIMEZONE:
        raise ValueError("Wisconsin Electric requires America/Chicago local intervals.")
    step = idx[1]-idx[0]
    if step not in (pd.Timedelta(minutes=15), pd.Timedelta(minutes=30)) or not np.all(idx[1:]-idx[:-1] == step):
        raise ValueError("Wisconsin Electric requires consecutive15/30-minute intervals; missing/duplicate data rejected.")
    stop = idx[-1]+step
    if (idx[0] != idx[0].normalize() or idx[0].day != 1 or stop != idx[0]+pd.offsets.MonthBegin()
            or a.get("cycle_kind") != "regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Wisconsin Electric first scope needs a complete calendar meter cycle; no inferred partial/crossing-cycle proration.")
    if a.get("billing_month") != str(idx[0].date()) or a.get("bill_date") != str(idx[-1].date()):
        raise ValueError("Wisconsin Electric calendar billing month must match service and bill date must be the final service day.")
    mode = _evidence_mode(a)
    service_rates(idx[0].date(), a["tariff"], mode=mode)
    service_rates(idx[-1].date(), a["tariff"], mode=mode)
    return dict(cycle_days=(stop.date()-idx[0].date()).days,
        elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)), monthly_charge_factor=1.,
        service_start=str(idx[0].date()), service_end=str(idx[-1].date()),
        billing_month=a["billing_month"], bill_date=a["bill_date"], partial_period_proration_applied=False)


def validate_account(a, index, equipment=None):
    if not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "bundled" or a.get("export_mode") != "none":
        raise ValueError("Wisconsin Electric requires supported bundled ordinary Rg1/Rg2/Cg1/Cg6 and zero export.")
    if any(a.get(k) is not True for k in ("eligibility_confirmed", "ordinary_service_confirmed", "local_charges_confirmed")) or a.get("tax_jurisdiction") != "waukesha_county_unincorporated":
        raise ValueError("Confirm Wisconsin Electric ordinary service eligibility and unincorporated Waukesha taxable jurisdiction.")
    for key in ("tax_source", "cycle_source"):
        if not isinstance(a.get(key), str) or not 1 <= len(a[key].strip()) <= 500:
            raise ValueError("Document Wisconsin Electric jurisdiction and complete calendar meter cycle.")
    res = a["tariff"] in ("Rg1", "Rg2")
    if res and a.get("principal_residence_confirmed") is not True:
        raise ValueError("Confirm permanent principal residence for the supported residential November–April billing-date tax exemption.")
    allowed = (("single", 240.),) if res else (("single", 240.), ("three", 480.))
    if (a.get("voltage") != "secondary" or a.get("power_factor") != 1. or (a.get("phase"), a.get("voltage_v")) not in allowed
            or a.get("opening_credit_usd") != 0. or a.get("meter_count") != 1 or a.get("service_line_count") != 1):
        raise ValueError("Ordinary Wisconsin Electric secondary240V split phase or commercial480V three phase only; no credit/PF/voltage adjustment.")
    if a["tariff"] in ("Rg2", "Cg6") and a.get("tou_enrollment_confirmed") is not True:
        raise ValueError("Confirm ordinary TOU meter/enrollment and minimum term; pilot rules cannot substitute.")
    if a.get("on_peak_start_hour") not in (7, 8, 9, 10) or isinstance(a.get("on_peak_start_hour"), bool):
        raise ValueError("Confirm Rg2 twelve-hour peak window starting7/8/9/10am.")
    if a["tariff"] == "Cg6" and a.get("on_peak_start_hour") != 9:
        raise ValueError("Cg6 has a fixed9am–9pm peak window.")
    # A flat Rg1/Cg1 comparison inherits account facts from its TOU case.
    # Retain the chosen window for audit, but do not apply it to flat pricing.
    if not res and a.get("small_general_confirmed") is not True:
        raise ValueError("Confirm current Cg1/Cg6 non-demand classification and prior12-month energy history.")
    cycle_review(a, index)
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("dg_enrollment_confirmed") is not True or not isinstance(a.get("dg_source"), str) or not 1 <= len(a["dg_source"].strip()) <= 500:
            raise ValueError("Wisconsin Electric requires approved CGS-NP non-export PV/storage; standalone storage and assumed NEM/standby eligibility unsupported.")
        if max(equipment.get("pv_dc_kw", 0.), equipment.get("pv_ac_kw", 0.))+equipment.get("battery_kw", 0.) > 40.+1e-8:
            raise ValueError("Wisconsin Electric first DER scope conservatively limits aggregate PV nameplate plus storage discharge to40kW; larger agreements unsupported.")


def validate_state(a, index, *, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("Wisconsin Electric non-export non-demand plans have no carried credit or ratchet state.")


def charge_lines(index, imports, exports, a, *, math, state=None):
    validate_state(a, index, state=state)
    idx = pd.DatetimeIndex(index)
    res = a["tariff"] in ("Rg1", "Rg2")
    cycle = cycle_review(a, idx)
    if math.convex:
        math.constraints.append(exports == 0)
        if not res:
            # Conservative guard: no case is allowed to trigger next-month
            # automatic General classification, which this adapter cannot bill.
            math.constraints.append(math.hours*math.sum(imports) <= 328.999*cycle["cycle_days"])
    elif np.max(exports) > 1e-5 or not res and math.hours*np.sum(imports) > 328.999*cycle["cycle_days"]+1e-7:
        raise ValueError("Wisconsin Electric ordinary non-export Small General study imports must stay below329kWh/day; no automatic reclassification modeled.")
    mode = _evidence_mode(a)
    evidence_result = evidence(idx, a)
    r = service_rates(idx[0].date(), a["tariff"], mode=mode)
    rates = interval_rates(idx, a["tariff"], a["on_peak_start_hour"], mode=mode)
    energy = math.hours*math.dot(imports, rates["energy"])
    lines = dict(customer=r["customer_daily"]*cycle["cycle_days"], energy=energy)
    for key in ("fuel", "fuel_reconciliation", "environmental_control"):
        lines[key] = math.hours*math.dot(imports, rates[key])
    tax_base = sum(lines.values())
    # Non-taxable state fee: exact minimum is shared by bills and MILP.
    lines["state_low_income_assistance"] = math.minimum(.03*tax_base, r["assistance_cap"])
    tax_rate = 0. if res and date.fromisoformat(a["bill_date"]).month in (11, 12, 1, 2, 3, 4) else .05
    lines["wisconsin_sales_tax"] = tax_base*tax_rate
    return dict(lines=lines, metrics={**cycle, "measured_demand_charge":False,
        "intraday_time_of_use_pricing":a["tariff"] in ("Rg2", "Cg6"), "fuel_category":"residential" if res else "commercial_non_demand",
        "base_version":r["base_version"], "fuel_version":r["fuel_version"], "rider_version":r["rider_version"], "rider_versions":r["rider_versions"],
        "on_peak_start_hour":a["on_peak_start_hour"] if a["tariff"] in ("Rg2", "Cg6") else None,
        "environmental_control_usd_per_kwh":r["environmental_control"], "fuel_reconciliation_usd_per_kwh":r["fuel_reconciliation"],
        "rate_evidence_mode":mode, "environmental_control_evidence_status":evidence_result["rate_evidence_status"],
        "provisional_ecc_applied":evidence_result["rate_evidence_status"] == "provisional",
        "billing_rule_evidence_status":"verified", "verified_base_energy_and_fuel":True,
        "assistance_fee_cap_usd":r["assistance_cap"], "assistance_fee_taxable":False,
        "tax_jurisdiction":a["tax_jurisdiction"], "sales_tax_rate":tax_rate, "sales_tax_base_usd":tax_base,
        "rate_effective_basis":"Service-date base/fuel/ECC; bill-date residential tax exemption; complete calendar cycles only.",
        "capacity_transmission_treatment":"Bundled ordinary retail service; no additional MISO LMP, capacity/PLC or ATC transmission tag charge",
        "energy_efficiency_act141_treatment":"Included in base prices; informational sheet20.1 not added again",
        "generation_program":"CGS-NP non-purchase when approved PV/storage present; imports retain ordinary rates, no export credits"},
        next_state={}, is_complete_bill=True, **evidence_result, rate_sources=SOURCES,
        warnings=["Hypothetical/non-export ordinary account; utility tariff enrollment, interconnection and tax status are independent account facts.",
                  "Verified January–June2025 and January–September2026; July–December2025 is opt-in provisional ECC only. No partial/crossing-cycle proration or other date extrapolation.",
                  "Dispatch is rolling-cycle historical perfect foresight; electrical replay is representative, not a site-specific engineering approval."] +
            (["Provisional historical estimate: "+PROVISIONAL_MODEL+" uses WE25-ECC-JUNE-CARRY-FORWARD. Solver reconciliation, optimality and OpenDSS do not verify the assumed historical ECC or the resulting savings."]+
             [v["explanation"] for v in evidence_result["rate_assumptions"]] if evidence_result["rate_assumptions"] else []))
