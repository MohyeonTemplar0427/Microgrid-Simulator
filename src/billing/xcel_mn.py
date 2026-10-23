"""Minnesota ordinary residential and small commercial non-export billing.

One charge expression supplies both numerical bills and dispatch objectives.
Complete calendar cycles intentionally avoid unverified bill-date allocation.
"""
from datetime import date, timedelta
from functools import lru_cache

from dateutil.easter import easter
import numpy as np
import pandas as pd

from ..tou_calendar import HolidayCalendar
from .xcel_mn_rates import BASE, COVERAGE, PLANS, SOURCES, service_rates

UTILITY = "xcel_energy_minnesota"
TIMEZONE = "America/Chicago"


@lru_cache(maxsize=32)
def holidays(year):
    may = date(year, 5, 31)
    sep = date(year, 9, 1)
    nov = date(year, 11, 1)
    actual = {date(year, 1, 1), easter(year)-timedelta(days=2),
              may-timedelta(days=may.weekday()), date(year, 7, 4),
              sep+timedelta(days=(-sep.weekday()) % 7),
              nov+timedelta(days=(3-nov.weekday()) % 7+21), date(year, 12, 25)}
    return frozenset(actual | {d+timedelta(days=-1 if d.weekday() == 5 else 1)
                              for d in actual if d.weekday() >= 5})


CALENDAR = HolidayCalendar("NSP Minnesota ordinary TOD seven holidays, Saturday Friday / Sunday Monday", holidays, (SOURCES[0], SOURCES[4]))


def periods(index, plan):
    idx = pd.DatetimeIndex(index)
    if plan not in PLANS or str(idx.tz) != TIMEZONE:
        raise ValueError("Select Minnesota ordinary plan and America/Chicago timestamps.")
    hour = idx.hour.to_numpy()+idx.minute.to_numpy()/60
    peak = ((idx.dayofweek < 5) & ~CALENDAR.mask(idx).to_numpy()
            & (hour >= 9) & (hour < 21)) if plan in ("A02", "A12") else np.zeros(len(idx), bool)
    return dict(peak=np.asarray(peak), off=~np.asarray(peak), summer=np.asarray((idx.month >= 6) & (idx.month <= 9)))


def interval_rates(index, plan):
    idx = pd.DatetimeIndex(index)
    p = periods(idx, plan)
    rates = {d: service_rates(d, plan) for d in set(idx.date)}
    energy = np.where(p["summer"], BASE[plan][0], BASE[plan][1])
    if plan in ("A02", "A12"):
        energy = np.where(p["peak"], energy, BASE[plan][2])
    return dict(energy=energy, **{k: np.asarray([rates[d][k] for d in idx.date])
        for k in ("fuel", "cip", "rdf", "tcr", "sales_true_up", "mercury", "environmental", "state_energy_policy")})


def account_fields(plan="A01"):
    fields = [dict(name=k, type="boolean", default=False, required=True, label=label) for k, label in (
        ("eligibility_confirmed", "Minnesota NSP/Xcel territory and ordinary selected tariff independently confirmed"),
        ("ordinary_service_confirmed", "Ordinary AC bundled account: no electric space heating, assistance discounts, credits, special facilities, contracts or rider exemptions"),
        ("full_monthly_charges_confirmed", "Complete calendar meter cycle with full monthly charges; no partial or shifted cycle"),
        ("local_charges_confirmed", "Unincorporated Sherburne County: ordinary taxable electric service, no city/franchise or special charges"))]
    fields += [dict(name="tax_jurisdiction", type="text", choices=["sherburne_county_unincorporated"], label="Explicit tax jurisdiction; independent of utility/location map"),
        dict(name="tax_source", type="text", required=True, label="Jurisdiction and non-exempt status evidence, or explicit hypothetical account"),
        dict(name="cycle_source", type="text", required=True, label="Complete meter-cycle evidence or explicit hypothetical calendar-cycle assumption"),
        dict(name="dg_enrollment_confirmed", type="boolean", default=False, label="PV/storage: approved non-export interconnection with ordinary tariff retained; no NEM/standby or supplemental agreement"),
        dict(name="dg_source", type="text", label="Non-export approval reference or explicit hypothetical assumption; omit personal information")]
    if plan in ("A02", "A12"):
        fields.append(dict(name="tou_enrollment_confirmed", type="boolean", required=True,
            label="Ordinary Time of Day metering/enrollment and minimum term confirmed; not Flex Pricing or three-period pilot"))
    if plan in ("A10", "A12"):
        fields.append(dict(name="small_general_confirmed", type="boolean", required=True,
            label="Current utility-approved Small General classification and required metering/history confirmed; study imports stay below25kW"))
    return fields


def defaults(plan="A01"):
    if plan not in PLANS:
        raise ValueError("Select Minnesota ordinary A01/A02/A10/A12.")
    res = plan in ("A01", "A02")
    return dict(tariff=plan, supply="bundled", export_mode="none", eligibility_confirmed=False,
        ordinary_service_confirmed=False, full_monthly_charges_confirmed=False, local_charges_confirmed=False,
        tax_jurisdiction="sherburne_county_unincorporated", tax_source="", cycle_source="",
        tou_enrollment_confirmed=False, small_general_confirmed=False, dg_enrollment_confirmed=False, dg_source="",
        opening_credit_usd=0., billing_month="2026-07-01", bill_date="2026-07-31", cycle_kind="regular",
        voltage="secondary", phase="single" if res else "three", voltage_v=240. if res else 480., power_factor=1.)


def hypothetical_defaults(plan="A01"):
    a = defaults(plan)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True, full_monthly_charges_confirmed=True,
        local_charges_confirmed=True, tou_enrollment_confirmed=True, small_general_confirmed=True, hypothetical_account=True,
        tax_source="Explicit hypothetical unincorporated Sherburne County ordinary taxable account: state6.875% plus county transit0.5%; no extra fees/exemptions",
        cycle_source="Explicit hypothetical complete calendar meter cycle; not a customer statement",
        dg_enrollment_confirmed=True, dg_source="Hypothetical utility-approved non-export PV/storage with ordinary tariff retained, no NEM/standby/supplemental agreement")
    return a


def catalog():
    labels = {"A01": "Residential standard overhead", "A02": "Residential ordinary Time of Day overhead",
              "A10": "Small General metered AC", "A12": "Small General ordinary Time of Day metered"}
    return [dict(id=p, label="Xcel Minnesota "+labels[p], status="supported",
        customer_class="residential" if p in ("A01", "A02") else "commercial",
        coverage=[dict(start=s, end=e) for s, e in COVERAGE], voltage="secondary",
        solar_modes=["non_export"], supply_arrangements=["bundled"], equipment_modes=["grid_only", "pv_only", "pv_battery"],
        representative_peak_kw=3. if p in ("A01", "A02") else 10., account_fields=account_fields(p), sources=SOURCES,
        eligibility="Explicit Minnesota NSP account; ordinary non-space-heating AC service; full calendar cycles and unincorporated Sherburne County ordinary tax status. Confirm enrollment independently of coordinates.",
        limitations=["Verified complete-rate coverage January2025–September2026, including full-year2025. Complete calendar cycles only; no October partial cycle.",
            "Ordinary TOD9am–9pm weekdays, seven holidays with Friday/Monday observance; no three-period pilot/Flex Pricing, EV or electric space-heating rates.",
            "Small General has no demand charge. Imports must stay below25kW for every study scenario; current classification and prior history still need utility confirmation.",
            "Sales tax7.375% for confirmed unincorporated Sherburne ordinary taxable service only. Other localities, franchise fees, assistance/tax exemptions unsupported.",
            "Non-export, approved ordinary service only; first DER scope limits aggregate PV nameplate plus battery discharge to40kW as a conservative model bound, not a statutory eligibility rule.",
            "No demand-billed A14/A15, exports/NEM settlement, standalone storage, partial/crossing meter cycles, underground service or special contracts. No MISO LMP/PLC adder or CAISO carbon substitution."])
        for p in PLANS]


def cycle_review(a, index):
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2 or str(idx.tz) != TIMEZONE:
        raise ValueError("Minnesota requires America/Chicago local intervals.")
    step = idx[1]-idx[0]
    if step not in (pd.Timedelta(minutes=15), pd.Timedelta(minutes=30)) or not np.all(idx[1:]-idx[:-1] == step):
        raise ValueError("Minnesota requires consecutive15/30-minute intervals; missing/duplicate data rejected.")
    stop = idx[-1]+step
    if (idx[0] != idx[0].normalize() or idx[0].day != 1 or stop != idx[0]+pd.offsets.MonthBegin()
            or a.get("cycle_kind") != "regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Minnesota first scope needs a complete calendar meter cycle; no inferred partial/crossing-cycle proration.")
    if a.get("billing_month") != str(idx[0].date()) or a.get("bill_date") != str(idx[-1].date()):
        raise ValueError("Minnesota calendar billing month must match service and bill date must be the final service day.")
    service_rates(idx[0].date(), a["tariff"])
    service_rates(idx[-1].date(), a["tariff"])
    return dict(cycle_days=(stop.date()-idx[0].date()).days,
        elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)), monthly_charge_factor=1.,
        service_start=str(idx[0].date()), service_end=str(idx[-1].date()),
        billing_month=a["billing_month"], bill_date=a["bill_date"], partial_period_proration_applied=False)


def validate_account(a, index, equipment=None):
    if not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "bundled" or a.get("export_mode") != "none":
        raise ValueError("Minnesota requires supported bundled ordinary A01/A02/A10/A12 and zero export.")
    if any(a.get(k) is not True for k in ("eligibility_confirmed", "ordinary_service_confirmed", "local_charges_confirmed")) or a.get("tax_jurisdiction") != "sherburne_county_unincorporated":
        raise ValueError("Confirm Minnesota ordinary service eligibility and unincorporated Sherburne taxable jurisdiction.")
    for key in ("tax_source", "cycle_source"):
        if not isinstance(a.get(key), str) or not 1 <= len(a[key].strip()) <= 500:
            raise ValueError("Document Minnesota jurisdiction and complete calendar meter cycle.")
    res = a["tariff"] in ("A01", "A02")
    allowed = (("single", 240.),) if res else (("single", 240.), ("three", 480.))
    if a.get("voltage") != "secondary" or a.get("power_factor") != 1. or (a.get("phase"), a.get("voltage_v")) not in allowed or a.get("opening_credit_usd") != 0.:
        raise ValueError("Ordinary Minnesota secondary240V split phase or commercial480V three phase only; no credit/PF/voltage adjustment.")
    if a["tariff"] in ("A02", "A12") and a.get("tou_enrollment_confirmed") is not True:
        raise ValueError("Confirm ordinary TOD meter/enrollment and minimum term; pilot rules cannot substitute.")
    if not res and a.get("small_general_confirmed") is not True:
        raise ValueError("Confirm current Small General classification and required demand meter/history.")
    cycle_review(a, index)
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("dg_enrollment_confirmed") is not True or not isinstance(a.get("dg_source"), str) or not 1 <= len(a["dg_source"].strip()) <= 500:
            raise ValueError("Minnesota requires approved ordinary-service non-export PV/storage; standalone storage and assumed NEM/standby eligibility unsupported.")
        if max(equipment.get("pv_dc_kw", 0.), equipment.get("pv_ac_kw", 0.))+equipment.get("battery_kw", 0.) > 40.+1e-8:
            raise ValueError("Minnesota first DER scope conservatively limits aggregate PV nameplate plus storage discharge to40kW; larger agreements unsupported.")


def validate_state(a, index, *, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("Minnesota non-export non-demand plans have no carried credit or ratchet state.")


def charge_lines(index, imports, exports, a, *, math, state=None):
    validate_state(a, index, state=state)
    idx = pd.DatetimeIndex(index)
    res = a["tariff"] in ("A01", "A02")
    if math.convex:
        math.constraints.append(exports == 0)
        if not res:
            # Conservative guard: no case is allowed to trigger next-month
            # automatic General classification, which this adapter cannot bill.
            math.constraints.append(imports <= 24.999)
    elif np.max(exports) > 1e-5 or not res and np.max(imports) > 24.999+1e-7:
        raise ValueError("Minnesota ordinary non-export Small General study imports must stay below25kW; no automatic reclassification modeled.")
    r = service_rates(idx[0].date(), a["tariff"])
    rates = interval_rates(idx, a["tariff"])
    energy = math.hours*math.dot(imports, rates["energy"])
    base = r["customer"]+energy
    lines = dict(customer=r["customer"], energy=energy,
        interim_rate_surcharge=base*r["interim"], renewable_energy_standard=base*r["res_factor"], affordability=r["affordability"])
    for key in ("fuel", "cip", "rdf", "tcr", "sales_true_up", "mercury", "environmental", "state_energy_policy"):
        lines[key] = math.hours*math.dot(imports, rates[key])
    tax_base = sum(lines.values())
    lines["minnesota_sales_tax"] = tax_base*.07375
    return dict(lines=lines, metrics={**cycle_review(a, idx), "measured_demand_charge":False,
        "intraday_time_of_use_pricing":a["tariff"] in ("A02", "A12"), "fuel_category":"residential" if res else "commercial_non_demand",
        "base_version":r["base_version"], "fuel_version":r["fuel_version"], "rider_version":r["rider_version"], "rider_versions":r["rider_versions"],
        "sales_true_up_rate_usd_per_kwh":r["sales_true_up"],
        "tax_jurisdiction":a["tax_jurisdiction"], "sales_tax_rate":.07375, "sales_tax_base_usd":tax_base,
        "rate_effective_basis":"Complete calendar cycles; same-month FCC. No guessed crossing-cycle/bill-render allocation.",
        "capacity_transmission_treatment":"Bundled supply plus filed TCR; no additional MISO LMP, capacity/PLC or transmission tag charge"},
        next_state={}, is_complete_bill=True, rate_evidence_status="verified", assumption_model=None,
        rate_assumptions=[], rate_sources=SOURCES,
        warnings=["Hypothetical/non-export ordinary account; utility tariff enrollment, interconnection and tax status are independent account facts.",
                  "Verified January2025–September2026 complete calendar cycles only; no partial/crossing-cycle proration or extrapolation.",
                  "Dispatch is rolling-cycle historical perfect foresight; electrical replay is representative, not a site-specific engineering approval."])
