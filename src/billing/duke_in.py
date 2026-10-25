"""Ordinary Duke Indiana single-phase RS/CS non-export retail bills.

The same expression owns numerical billing and the bounded exact dispatch
objective, including decreasing energy blocks and all mandatory reset riders.
"""
from copy import deepcopy
from datetime import date, timedelta, timezone
from functools import lru_cache

import numpy as np
import pandas as pd

from ..tou_calendar import HolidayCalendar
from .duke_in_rates import (ASSUMPTIONS, BASE, COVERAGE, PLANS, RIDERS, SOURCES,
                            evidence as _rate_evidence, provisional_coverage, service_rates)

UTILITY = "duke_energy_indiana"
TIMEZONE = "America/Indiana/Indianapolis"


@lru_cache(maxsize=32)
def holidays(year):
    may = date(year, 5, 31)
    sep = date(year, 9, 1)
    nov = date(year, 11, 1)
    actual = {date(year, 1, 1), may-timedelta(days=may.weekday()), date(year, 7, 4),
              sep+timedelta(days=(-sep.weekday()) % 7),
              nov+timedelta(days=(3-nov.weekday()) % 7+21), date(year, 12, 25)}
    return frozenset(actual | {d+timedelta(days=-1 if d.weekday() == 5 else 1)
                              for d in actual if d.weekday() >= 5})


CALENDAR = HolidayCalendar("Duke Indiana six holidays, Saturday Friday / Sunday Monday", holidays, (SOURCES[0],))


def periods(index, plan):
    idx = pd.DatetimeIndex(index)
    if plan not in PLANS or str(idx.tz) != TIMEZONE:
        raise ValueError("Duke Indiana requires its own plan and America/Indiana/Indianapolis timestamps.")
    # Filed periods follow Eastern STANDARD time, appearing an hour later on
    # daylight clocks. Offset conversion retains both repeated DST records.
    standard = idx.tz_convert(timezone(timedelta(hours=-5)))
    hour = standard.hour.to_numpy()+standard.minute.to_numpy()/60
    winter = np.asarray([not bool(t.dst()) for t in idx.to_pydatetime()])
    holiday = CALENDAR.mask(idx).to_numpy()  # Holiday is the local civil date.
    tou = plan.endswith("-TOU")
    peak = (((hour >= 17) & (hour < 21)) | (winter & (hour >= 6) & (hour < 8))) & ~holiday if tou else np.zeros(len(idx), bool)
    discount = (hour >= 0) & (hour < 4) & ~holiday if tou else np.zeros(len(idx), bool)
    return dict(peak=np.asarray(peak), discount=np.asarray(discount), off=~(peak | discount))


def interval_rates(index, plan, *, billing_month=None, mode="verified"):
    idx = pd.DatetimeIndex(index)
    p = periods(idx, plan)
    dated = {d: service_rates(d, plan, billing_month=billing_month, mode=mode) for d in set(idx.date)}
    result = {name: np.asarray([dated[d][name] for d in idx.date]) for name in RIDERS}
    if plan.endswith("-TOU"):
        energy = BASE[plan]["energy"]
        result["energy"] = np.where(p["peak"], energy[0], np.where(p["discount"], energy[2], energy[1]))
    # Standard rates are cumulative monthly blocks, never flat interval prices.
    return result


def account_fields(plan="RS"):
    result = [dict(name=name, type="boolean", default=False, required=True, label=label) for name, label in (
        ("eligibility_confirmed", "Duke Indiana territory, ordinary selected tariff and maximum load at most75kW independently confirmed"),
        ("ordinary_service_confirmed", "Ordinary metered bundled single-phase service: no special contracts, assistance, high-efficiency option, energy-efficiency opt-out, excess facilities or AMI opt-out fees"),
        ("full_monthly_charges_confirmed", "Complete regular26–34day meter cycle with full monthly charges and explicit billing month; no partial or rate-crossing allocation"),
        ("local_charges_confirmed", "Ordinary Indiana7% taxable account with no additional local charge or exemption"))]
    result += [dict(name="rate_evidence_mode", type="choice", choices=["verified", "provisional_2025"], default="verified",
                   label="Rate evidence: verified March2025 or explicitly provisional2025 study assumptions"),
        dict(name="provisional_assumptions_accepted", type="boolean", default=False,
             label="I accept the documented Duke2025 rate proxies and billing-clock assumptions; historical bills and savings may be inaccurate"),
        dict(name="tax_jurisdiction", type="text", choices=["indiana_ordinary_taxable"], label="Separately confirmed ordinary Indiana taxable account"),
        dict(name="tax_source", type="text", required=True, label="Tax/local-charge evidence or explicitly hypothetical account; omit personal identifiers"),
        dict(name="cycle_source", type="text", required=True, label="Complete meter-cycle evidence or explicit hypothetical calendar assumption"),
        dict(name="dg_enrollment_confirmed", type="boolean", default=False, label="PV/storage: approved Tariff51Option2 non-export interconnection under Tariff80; ordinary rate retained"),
        dict(name="dg_source", type="text", label="Option2 non-export/interconnection approval or explicitly hypothetical assumption")]
    if plan.endswith("-TOU"):
        result += [dict(name="tou_enrollment_confirmed", type="boolean", required=True,
            label="TOU enrollment, smart meter, average prior12-month Billing Maximum Load at least1kW and <=75kW maximum confirmed")]
    return result


def defaults(plan="RS"):
    if plan not in PLANS:
        raise ValueError("Choose Duke Indiana RS, RS-TOU, CS or CS-TOU.")
    return dict(tariff=plan, supply="bundled", export_mode="none", eligibility_confirmed=False,
        rate_evidence_mode="verified", provisional_assumptions_accepted=False,
        ordinary_service_confirmed=False, full_monthly_charges_confirmed=False, local_charges_confirmed=False,
        tax_jurisdiction="indiana_ordinary_taxable", tax_source="", cycle_source="", tou_enrollment_confirmed=False,
        dg_enrollment_confirmed=False, dg_source="", opening_credit_usd=0., billing_month="2025-03-01", bill_date="2025-03-31",
        cycle_kind="regular", voltage="secondary", phase="single", voltage_v=240., power_factor=1.)


def hypothetical_defaults(plan="RS"):
    a = defaults(plan)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True, full_monthly_charges_confirmed=True,
        local_charges_confirmed=True, tou_enrollment_confirmed=True, dg_enrollment_confirmed=True, hypothetical_account=True,
        tax_source="Explicit hypothetical ordinary Indiana7% taxable account; no additional local charge or exemption",
        cycle_source="Explicit hypothetical complete March2025 calendar meter cycle, not a customer statement",
        dg_source="Hypothetical utility-approved Tariff51Option2 non-export PV/storage and Tariff80 interconnection, ordinary retail backup/supplemental terms retained")
    return a


def catalog():
    labels = {"RS": "Residential", "RS-TOU": "Residential Time-of-Use", "CS": "Commercial", "CS-TOU": "Commercial Time-of-Use"}
    return [dict(id=p, label="Duke Indiana "+labels[p], status="supported", customer_class="residential" if p.startswith("RS") else "commercial",
        coverage=[dict(start=s, end=e) for s, e in COVERAGE], voltage="secondary", solar_modes=["non_export"], supply_arrangements=["bundled"],
        provisional_coverage=provisional_coverage(p), provisional_assumptions=deepcopy(ASSUMPTIONS),
        equipment_modes=["grid_only", "pv_only", "pv_battery"], representative_peak_kw=3. if p.startswith("RS") else 10.,
        account_fields=account_fields(p), sources=SOURCES,
        eligibility="Independently confirmed ordinary Duke Indiana bundled single-phase120/240V service, maximum load75kW or less. TOU needs smart metering and average prior12-month Billing Maximum Load at least1kW.",
        limitations=["Verified March2025 service and billing designation only. Explicit provisional_2025 mode plus acceptance enables standardRS/CS calendar2025 study proxies, TOU only fromFebruary27; inspect each result's component assumptions. No2026 extrapolation.",
            "Standard RS/CS use decreasing monthly kWh blocks. TOU follows the individual filed6.5/7.5 sheets; conflicting proposal-summary/generic business-calendar guidance requires utility confirmation before actual-account use.",
            "No measured demand charge or separate MISO LMP/capacity/transmission-tag charge: ordinary bundled supply and applicable filed riders only.",
            "Ordinary Indiana7% sales tax with independently confirmed local-charge/non-exempt status. Special contracts, AMI opt-out, EE opt-out, assistance and excess facilities unsupported.",
            "DER: Tariff51Option2 reduction-in-usage, no export credit, approved Tariff80 interconnection; model conservatively bounds aggregate PV nameplate plus battery discharge to40kW.",
            "Complete confirmed regular26–34day cycles only. No EDG, legacy NEM, exports, standalone storage, QF purchase agreement, partial/base-crossing cycles, three-phase/120-208V service or data-center tariff eligibility inference."])
        for p in PLANS]


def cycle_review(a, index):
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2 or str(idx.tz) != TIMEZONE:
        raise ValueError("Duke Indiana requires America/Indiana/Indianapolis intervals.")
    mode = a.get("rate_evidence_mode", "verified")
    if (mode not in ("verified", "provisional_2025")
            or type(a.get("provisional_assumptions_accepted", False)) is not bool
            or mode == "provisional_2025" and a.get("provisional_assumptions_accepted") is not True):
        raise ValueError("Provisional Duke Indiana2025 rates require explicit mode selection and boolean acceptance of the documented assumptions.")
    step = idx[1]-idx[0]
    if step not in (pd.Timedelta(minutes=15), pd.Timedelta(minutes=30)) or not np.all(idx[1:]-idx[:-1] == step):
        raise ValueError("Duke Indiana requires consecutive15/30-minute intervals; missing/duplicate data rejected.")
    stop = idx[-1]+step
    days = (stop.date()-idx[0].date()).days
    if (idx[0] != idx[0].normalize() or stop != stop.normalize() or not 26 <= days <= 34
            or a.get("cycle_kind") != "regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Duke Indiana requires a complete documented regular26–34day meter cycle; no inferred partial or rate-crossing proration.")
    # The first historical scope keeps the bill-render month explicit and the
    # bill date on its final service day. It does not infer a utility reading
    # schedule from civil-month boundaries or silently move a rider clock.
    expected_month = idx[-1].date().replace(day=1).isoformat()
    if a.get("billing_month") != expected_month or a.get("bill_date") != str(idx[-1].date()):
        raise ValueError("Duke Indiana designated billing month must match the confirmed final-day bill date.")
    if idx[0].date() < date(2025, 2, 27) <= idx[-1].date():
        raise ValueError("Duke Indiana cycle crosses the February27 base/rider reset; exact rate-change allocation is not yet verified.")
    first = service_rates(idx[0].date(), a["tariff"], billing_month=a["billing_month"], mode=mode)
    last = service_rates(idx[-1].date(), a["tariff"], billing_month=a["billing_month"], mode=mode)
    if first["base_version"] != last["base_version"]:
        raise ValueError("Duke Indiana cycle crosses base versions; exact rate-change allocation is not yet verified.")
    return dict(cycle_days=days,
        elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)), monthly_charge_factor=1.,
        service_start=str(idx[0].date()), service_end=str(idx[-1].date()), billing_month=a["billing_month"], bill_date=a["bill_date"], partial_period_proration_applied=False)


def evidence(index, account):
    cycle_review(account, index)
    return _rate_evidence(pd.DatetimeIndex(index), account)


def validate_account(a, index, equipment=None):
    if not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "bundled" or a.get("export_mode") != "none":
        raise ValueError("Duke Indiana requires an ordinary supported bundled plan with zero export.")
    if any(a.get(k) is not True for k in ("eligibility_confirmed", "ordinary_service_confirmed", "local_charges_confirmed")) or a.get("tax_jurisdiction") != "indiana_ordinary_taxable":
        raise ValueError("Confirm Duke Indiana ordinary eligibility, tax and local-charge status.")
    for key in ("tax_source", "cycle_source"):
        if not isinstance(a.get(key), str) or not 1 <= len(a[key].strip()) <= 500:
            raise ValueError("Document Duke Indiana tax/local-charge and complete meter-cycle assumptions.")
    if (a.get("voltage"), a.get("phase"), a.get("voltage_v"), a.get("power_factor")) != ("secondary", "single", 240., 1.) or a.get("opening_credit_usd") != 0.:
        raise ValueError("Duke Indiana first scope requires single-phase120/240V, unity-PF representative service without opening credits.")
    if a["tariff"].endswith("-TOU") and a.get("tou_enrollment_confirmed") is not True:
        raise ValueError("Confirm Duke Indiana TOU smart meter, prior12-month average maximum>=1kW and enrollment.")
    cycle_review(a, index)
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("dg_enrollment_confirmed") is not True or not isinstance(a.get("dg_source"), str) or not 1 <= len(a["dg_source"].strip()) <= 500:
            raise ValueError("Duke Indiana requires confirmed Tariff51Option2 non-export PV/storage and Tariff80 interconnection; standalone storage/QF/export programs unsupported.")
        if max(equipment.get("pv_dc_kw", 0.), equipment.get("pv_ac_kw", 0.))+equipment.get("battery_kw", 0.) > 40.+1e-8:
            raise ValueError("Duke Indiana first DER scope conservatively limits aggregate PV nameplate plus storage discharge to40kW.")


def validate_state(a, index, *, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("Duke Indiana ordinary non-export plans have no carried credit or demand ratchet state.")


def charge_lines(index, imports, exports, a, *, math, state=None):
    validate_state(a, index, state=state)
    idx = pd.DatetimeIndex(index)
    if math.convex:
        math.constraints += [exports == 0, imports <= 75.]
    elif np.max(exports) > 1e-5 or np.max(imports) > 75.+1e-7:
        raise ValueError("Duke Indiana ordinary scope requires zero export and maximum import75kW or less.")
    mode = a.get("rate_evidence_mode", "verified")
    proof = evidence(idx, a)
    rates = service_rates(idx[0].date(), a["tariff"], billing_month=a["billing_month"], mode=mode)
    volume = math.hours*math.sum(imports)
    dated = interval_rates(idx, a["tariff"], billing_month=a["billing_month"], mode=mode)
    energy = (math.hours*math.dot(imports, dated["energy"]) if a["tariff"].endswith("-TOU")
              else math.tiered(volume, rates["bounds"], rates["energy"]))
    lines = dict(customer=rates["customer"], energy=energy)
    for component in RIDERS:
        lines[component] = math.hours*math.dot(imports, dated[component])
    tax_base = sum(lines.values())
    lines["indiana_sales_tax"] = tax_base*.07
    tou = a["tariff"].endswith("-TOU")
    calendar_warning = (
        "TOU calendar evidence discrepancy: this estimate and its optimum follow the individual filed Tariff6.5/7.5 sheets "
        "(Eastern-standard clock, weekend peaks, holidays entirely off-peak). The order's proposal summary and generic "
        "business guidance describe different weekday/holiday treatment and may concern other TOU schedules. "
        "The applicable calendar for an actual enrolled RS/CS account requires utility confirmation; arithmetic reconciliation does not resolve that source discrepancy."
    )
    return dict(lines=lines, metrics={**cycle_review(a, idx), "measured_demand_charge": False,
        "intraday_time_of_use_pricing": a["tariff"].endswith("-TOU"), "base_version": rates["base_version"], "rider_version": rates["rider_version"],
        "calendar_evidence_status": "filed_sheet_interpretation_utility_confirmation_required" if tou else "not_time_of_use",
        "calendar_confirmation_required": tou,
        "calendar_evidence_note": calendar_warning if tou else None,
        "calendar_source_references": [SOURCES[0], SOURCES[1], SOURCES[7], SOURCES[8]] if tou else [],
        "tax_jurisdiction": a["tax_jurisdiction"], "sales_tax_rate": .07, "sales_tax_base_usd": tax_base,
        "rate_effective_basis": ("Provisional2025 composite: inspect component and billing-clock assumptions; complete regular cycle, no base-crossing allocation" if proof["rate_evidence_status"] == "provisional" else
                                 "February27,2025 reset with explicit March2025 service/billing clocks; complete regular26–34day cycle at full schedule under GTC12.4, no inferred rate-crossing allocation"),
        "capacity_transmission_treatment": "Bundled ordinary supply plus filed RTO/TDSIC and other riders; no additional MISO LMP, PLC/capacity or transmission-tag charge"},
        next_state={}, is_complete_bill=True, **proof, rate_sources=SOURCES,
        warnings=([calendar_warning] if tou else [])+([
            "Provisional historical estimate using "+", ".join(v["id"] for v in proof["rate_assumptions"])+
            ". Pre-reset proxies may misstate base/rider reallocation; later missing factors are held study values. Solver optimality, arithmetic reconciliation and OpenDSS cannot validate these historical assumptions; inspect their dates, values and sources."
            ] if proof["rate_evidence_status"] == "provisional" else ["Verified March2025 service/billing designation only; no extrapolation to other2025/2026 dates."])+[
            "Hypothetical non-export ordinary account; territory, tariff enrollment, local tax and interconnection remain separate verified account facts.",
            "Dispatch is rolling-cycle historical perfect foresight; representative electrical replay is not site-specific engineering approval."])
