"""Verified, bounded Atlantic City Electric NJ RS/MGS-Secondary BGS-RSCP.

Exactly 30 local service days within one calendar month, season and verified
component regime. Meter quantity rounding is distinct from monetary rounding:
MGS dispatch uses the existing objective-input hook for a raw-quantity proxy;
its final numeric bill applies the filed quantity rules, rejecting half ties.
"""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd

from .atlantic_city_electric_rates import PLANS, REGIMES, SOURCES, rates_on

TIMEZONE = "America/New_York"
COVERAGE = (("2025-02-01", "2025-08-31"), ("2025-10-01", "2025-11-30"),
            ("2026-09-01", "2026-10-31"))
RAW_OBJECTIVE = "pre_measurement_rounding_charge_proxy"


class _RawQuantityObjective(dict):
    """Internal-only account type; JSON requests cannot request a rounding bypass."""


def account_fields(plan="RS"):
    return [
        dict(name="eligibility_confirmed", type="boolean", label="ACE New Jersey and this filed schedule independently confirmed"),
        dict(name="ordinary_service_confirmed", type="boolean", label="Ordinary continuous service, one single-phase secondary meter; no special contract or discounts"),
        dict(name="full_monthly_charges_confirmed", type="boolean", label="Exactly 30 service days within one month and unchanged rate regime; full monthly charges"),
        dict(name="no_special_provisions_confirmed", type="boolean", label="No special heating, worship/veteran, EV, computed-load, exemption or facilities provisions"),
        dict(name="supply", type="choice", choices=["bgs_rscp"], label="ACE default Basic Generation Service - Residential Small Commercial Pricing"),
        dict(name="cycle_source", type="text", label="Meter-cycle evidence or explicit hypothetical 30-day assumption"),
        dict(name="tax_source", type="text", label="Ordinary New Jersey taxable account evidence; published CBT/SUT retained once"),
        dict(name="bgs_rscp_confirmed", type="boolean", label="Assigned BGS-RSCP; no alternative supplier or CIEP election"),
        dict(name="peak_load_share_kw", type="number", label="MGS utility-assigned generation-capacity PLS below 500 kW; independent of modeled monthly peak"),
        dict(name="peak_load_share_as_of", type="date", label="MGS November 1 PLS assignment for the procurement year"),
        dict(name="pls_source", type="text", label="MGS utility PLS/enrollment evidence or explicit hypothetical assignment"),
        dict(name="demand_method", type="choice", choices=["not_applicable", "measured"], label="MGS measured 15-minute demand; no unmetered or fixed-load estimate"),
        dict(name="quantity_objective_confirmed", type="boolean", label="MGS cost study uses quantities before rounding; final bill rounds quantities, without a rounded-invoice optimum claim"),
        dict(name="der_ordinary_service_confirmed", type="boolean", label="Written approved ordinary non-export PV/storage service with no standby or special charges"),
        dict(name="der_eligibility_source", type="text", label="Written parallel-service approval and ordinary charge classification; no export settlement"),
        dict(name="rate_evidence_mode", type="choice", choices=["verified"], label="Verified intersections only; no missing-rate fallback"),
    ]


def pls_as_of(day):
    current = pd.Timestamp(day)
    supply_year = current.year if current.month >= 6 else current.year-1
    return f"{supply_year-1}-11-01"


def defaults(plan="RS"):
    if plan not in PLANS:
        raise ValueError("Select ACE NJ RS or MGS-Secondary BGS-RSCP.")
    res = plan == "RS"
    return dict(tariff=plan, supply="bgs_rscp", export_mode="none", eligibility_confirmed=False,
        ordinary_service_confirmed=False, full_monthly_charges_confirmed=False,
        no_special_provisions_confirmed=False, bgs_rscp_confirmed=False,
        billing_month="2026-09-01", bill_date="2026-09-30", cycle_kind="regular", cycle_source="",
        tax_exempt=False, tax_source="", voltage="secondary", phase="single", voltage_v=240.,
        power_factor=1., meter_count=1, service_line_count=1, opening_credit_usd=0.,
        demand_interval_minutes=15, demand_method="not_applicable" if res else "measured",
        peak_load_share_kw=None if res else 10., peak_load_share_as_of="" if res else "2025-11-01",
        pls_source="", quantity_objective_confirmed=False,
        der_ordinary_service_confirmed=False, der_eligibility_source="",
        rate_evidence_mode="verified", provisional_assumptions_accepted=False,
        hypothetical_account=False)


def hypothetical_defaults(plan="RS", day="2026-09-01"):
    a = defaults(plan)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True,
        full_monthly_charges_confirmed=True, no_special_provisions_confirmed=True,
        bgs_rscp_confirmed=True, hypothetical_account=True, quantity_objective_confirmed=plan != "RS",
        cycle_source="Explicit hypothetical ordinary 30-day cycle; no partial/monthly allocation or actual customer statement",
        tax_source="Explicit hypothetical ordinary New Jersey taxable account; published CBT/SUT already included, no exemption",
        pls_source="Explicit hypothetical utility-assigned November PLS of 10 kW and BGS-RSCP enrollment; not inferred from simulated demand" if plan != "RS" else "Not applicable to residential RS",
        der_ordinary_service_confirmed=True,
        der_eligibility_source="Explicit hypothetical written ACE ordinary Class I PV/storage parallel-service approval, zero exports and no opening bank, standby or special charges")
    if plan != "RS":
        a["peak_load_share_as_of"] = pls_as_of(day)
    return a


def catalog():
    return [dict(id=p, label="Atlantic City Electric NJ " + ("RS residential BGS-RSCP" if p == "RS" else "MGS-Secondary BGS-RSCP"),
        status="supported", customer_class="residential" if p == "RS" else "commercial", voltage="secondary",
        coverage=[dict(start=s, end=e, is_complete_bill=True,
                       scope="Ordinary component coverage; exactly 30-day single-regime cycles") for s,e in COVERAGE],
        interval_minutes=[15], solar_modes=["non_export"], supply_arrangements=["bgs_rscp"],
        equipment_modes=["grid_only", "pv_only", "pv_battery"], representative_peak_kw=3. if p == "RS" else 8.,
        account_fields=account_fields(p), sources=SOURCES,
        eligibility="Explicit ordinary utility-assigned RS or measured MGS-Secondary BGS-RSCP, one 120/240 V single-phase meter, unity billing PF and exactly 30 local service days inside one calendar month, season and verified rate regime.",
        limitations=[
            "February-August and October-November2025; September-October2026 component intersections only. Exactly30-day cycles; February's short month, non30-day, crossed-month/season/regime cycles and full years reject. January/September/December2025 and January-August2026 are not filled with current rates.",
            "MGS uses utility-assigned annual November PLS below500kW, separate from actual15-minute peaks; no CIEP, unmetered demand, fixed-load computation, ratchets or special-service provisions.",
            "MGS final bill rounds energy to0.01kWh and demand to0.1kW. Exact half ties reject because the tie convention is unverified. Its cost and cycling proofs concern quantities before rounding, never a minimum rounded invoice.",
            "RS retains raw energy; the MGS quantity rule is not borrowed. Component half-up monetary cents are a study convention, not a calibrated printed-invoice rule.",
            "Published CBT/SUT, supply administration and capacity are included once; no extra tax percentage, wholesale energy, PLC or NSPL charge.",
            "RS applies mandatory -$30 July/August2025 and +$10 September2025-February2026 within verified windows. Negative post-credit balances reject; refund/carry settlement is not inferred.",
            "Approved ordinary non-export PV/storage only, combined capacity at most25kW. Historical NEM does not enable export credits. MGS2025 DER rejects because historical standby generation-availability rules are not modeled; no standalone storage."])
        for p in PLANS]


def cycle_review(a, index):
    idx = pd.DatetimeIndex(index); step = pd.Timedelta(minutes=15)
    if (len(idx) < 2 or str(idx.tz) != TIMEZONE
            or not np.all(idx[1:]-idx[:-1] == step)):
        raise ValueError("ACE needs consecutive America/New_York15-minute intervals; missing/duplicate/hourly data reject.")
    stop = idx[-1]+step; start = idx[0]
    if (start != start.normalize() or stop != stop.normalize()
            or (stop.date()-start.date()).days != 30
            or start.strftime("%Y-%m") != idx[-1].strftime("%Y-%m")
            or a.get("cycle_kind") != "regular" or a.get("full_monthly_charges_confirmed") is not True
            or a.get("billing_month") != start.strftime("%Y-%m-01")
            or a.get("bill_date") != str(idx[-1].date())):
        raise ValueError("ACE scope requires exactly30 complete local days within one calendar month, a matching billing-month designation and final-day bill date; other proration is unverified.")
    r = rates_on(start.date(), a["tariff"])
    if rates_on(idx[-1].date(), a["tariff"])["version_id"] != r["version_id"]:
        raise ValueError("ACE cycle crosses a filed component regime; transition allocation is unverified.")
    return dict(service_start=str(start.date()), service_end=str(idx[-1].date()),
        billing_month=a["billing_month"], bill_date=a["bill_date"], cycle_days=30,
        elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)), monthly_charge_factor=1.,
        partial_period_proration_applied=False, rate_version=r["version_id"])


def _reference(a, key):
    if not isinstance(a.get(key), str) or not 1 <= len(a[key].strip()) <= 500:
        raise ValueError("Document ACE cycle, taxable-account, PLS and written operating approvals without personal identifiers.")


def validate_account(a, index, equipment=None):
    if not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "bgs_rscp" or a.get("export_mode") != "none":
        raise ValueError("Select ACE NJ RS/MGS-Secondary BGS-RSCP and zero export.")
    # A JSON caller cannot forge the internal objective-account type.
    if set(a)-set(defaults(a["tariff"])):
        raise ValueError("ACE account contains unsupported fields; quantity rounding cannot be disabled by a request.")
    if a.get("rate_evidence_mode") != "verified" or a.get("provisional_assumptions_accepted") is not False:
        raise ValueError("ACE has no provisional or missing-price fallback.")
    for key in ("eligibility_confirmed", "ordinary_service_confirmed", "full_monthly_charges_confirmed", "no_special_provisions_confirmed", "bgs_rscp_confirmed"):
        if a.get(key) is not True:
            raise ValueError("Confirm ACE NJ tariff, ordinary service, 30-day billing scope and BGS-RSCP independently.")
    for key in ("tax_source", "cycle_source"):
        _reference(a, key)
    if (a.get("tax_exempt") is not False
            or (a.get("voltage"), a.get("phase"), a.get("voltage_v"), a.get("power_factor")) != ("secondary", "single", 240., 1.)
            or a.get("meter_count") != 1 or a.get("service_line_count") != 1
            or a.get("opening_credit_usd") != 0. or a.get("demand_interval_minutes") != 15):
        raise ValueError("ACE first scope needs one ordinary taxable120/240V single-phase meter, unity billing PF,15-minute demand and no credit bank.")
    if any(type(a.get(k)) not in (int, float) or not np.isfinite(a[k])
           for k in ("voltage_v", "power_factor", "meter_count", "service_line_count", "opening_credit_usd", "demand_interval_minutes")):
        raise ValueError("ACE electrical/account quantities must be finite numbers, not boolean values.")
    cycle = cycle_review(a, index)
    if a["tariff"] == "MGS-SECONDARY":
        pls = a.get("peak_load_share_kw")
        if (type(pls) not in (int, float) or not np.isfinite(pls) or not 0 <= pls < 500
                or a.get("peak_load_share_as_of") != pls_as_of(cycle["service_start"])
                or a.get("demand_method") != "measured" or a.get("quantity_objective_confirmed") is not True):
            raise ValueError("MGS requires measured demand, correct independent November PLS below500kW, retained BGS-RSCP and acknowledgment of the pre-rounding objective.")
        _reference(a, "pls_source")
    elif (a.get("demand_method") != "not_applicable" or a.get("peak_load_share_kw") is not None
            or a.get("peak_load_share_as_of") != "" or a.get("quantity_objective_confirmed") is not False):
        raise ValueError("RS has no commercial PLS/demand method or MGS quantity objective.")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("ACE PV/storage requires written ordinary parallel/NEM-account approval, zero exports and no standalone storage.")
        _reference(a, "der_eligibility_source")
        if a["tariff"] == "MGS-SECONDARY" and cycle["service_start"] < "2025-12-01":
            raise ValueError("MGS2025 PV/storage standby generation-availability/history rules are unmodeled; historical G studies are grid-only.")
        if max(equipment.get("pv_dc_kw", 0.), equipment.get("pv_ac_kw", 0.))+equipment.get("battery_kw", 0.) > 25.+1e-8:
            raise ValueError("ACE study limits combined PV/storage to25kW; this is not proof of interconnection eligibility.")


def validate_state(a, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("ACE non-export scope has no carried credit, demand ratchet or settlement state.")


def objective_inputs(account, state=None, policy="exclude_opening_credits"):
    if policy != "exclude_opening_credits":
        raise ValueError("ACE uses the disclosed unrounded-charge operating objective; no exact rounded cash-bill objective.")
    copied = deepcopy(account)
    return (_RawQuantityObjective(copied) if account["tariff"] == "MGS-SECONDARY" else copied), deepcopy(state)


def _nearest_unambiguous(value, quantum):
    scaled = float(value)/quantum
    if abs(scaled-np.floor(scaled)-.5) <= 1e-7:
        raise ValueError("ACE exact quantity-rounding half ties are unsupported; no unsourced tie convention is selected.")
    return float(np.floor(scaled+.5)*quantum)


def charge_lines(index, imports, exports, a, *, math, state=None):
    validate_state(a, index, state=state); cycle = cycle_review(a, index)
    if math.convex:
        math.constraints.append(exports == 0)
    elif np.max(exports) > 1e-5:
        raise ValueError("ACE export/NEM credit settlement is not implemented; exports must be zero.")
    r = rates_on(cycle["service_start"], a["tariff"]); res = a["tariff"] == "RS"
    raw_energy = math.hours*math.sum(imports)
    raw_peak = 0. if res else math.demand(imports, index, minutes=15)
    proxy = isinstance(a, _RawQuantityObjective) or math.convex
    energy = raw_energy if res or proxy else _nearest_unambiguous(raw_energy, .01)
    peak = raw_peak if res or proxy else _nearest_unambiguous(raw_peak, .1)
    if not res:
        if math.convex:
            math.constraints.append(raw_peak <= 100.)
        elif raw_peak > 100.+1e-7:
            raise ValueError("ACE first MGS study is bounded to100kW actual import peak; larger/reactive-service cases are unverified.")
    lines = {"distribution_customer": r["customer"],
             **{key: energy*rate for key,rate in r["energy_rates"].items()}}
    if res:
        def block(rates):
            return energy*rates[0] if rates[0] == rates[1] else math.tiered(energy, [r["energy_block_kwh"]], rates)
        lines.update(distribution_energy=block(r["distribution_energy"]),
                     generation_energy=block(r["generation_energy"]),
                     transmission_energy=energy*r["transmission_energy"],
                     residential_capacity_deferral=r["residential_capacity_deferral"])
        if not math.convex:
            monetary_total = sum(Decimal(str(v)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
                                 for v in lines.values())
            if sum(lines.values()) < -1e-7 or monetary_total < 0:
                raise ValueError("ACE negative post-relief balance settlement is unverified; no refund/carry or forced extra purchases are modeled.")
    else:
        lines.update(distribution_energy=energy*r["distribution_energy"],
                     generation_energy=energy*r["generation_energy"],
                     distribution_demand=peak*r["distribution_demand"],
                     transmission_demand=math.positive(peak-3.)*r["transmission_demand"],
                     infrastructure_demand=peak*r["infrastructure_demand"],
                     reactive_demand=0., minimum_bill_adjustment=0.)
    error_bound = (0. if res else .005*(sum(abs(v) for v in r["energy_rates"].values())+abs(r["distribution_energy"])+abs(r["generation_energy"]))
                   +.05*(r["distribution_demand"]+r["transmission_demand"]+r["infrastructure_demand"])+1e-8)
    metrics = {**cycle, "rates": r, "raw_import_kwh": raw_energy, "raw_peak_kw": raw_peak,
        "billed_import_kwh": energy, "billed_peak_kw": peak,
        "quantity_basis": "raw_rs_energy" if res else "raw_objective_proxy" if proxy else "filed_nearest_quantities_no_half_ties",
        "optimization_objective_scope": "unrounded_rs_component_charges" if res else RAW_OBJECTIVE,
        "quantity_rounding_charge_error_bound_usd": error_bound,
        "minimum_basis": "No additional RS minimum invented" if res else "Applicable single-phase customer plus adjustments; nonnegative distribution energy/demand make ordinary minimum inactive",
        "tax_treatment": r["taxes"], "additional_tax_percentage_applied": False,
        "supply_treatment": "BGS-RSCP includes generation capacity, ancillary/admin and SUT once; separate filed transmission and TEC retained, no wholesale price or obligation substitute",
        "standby_scope": "RS outside listed STB classes" if res else "Grid-only beforeDec2025; approved at-most25kW PV/storage after adoptedDec2025 rule",
        "rounded_cash_optimum_claimed": False}
    return dict(lines=lines, metrics=metrics, next_state={}, is_complete_bill=True, excluded_components=[],
        rate_evidence_status="verified", assumption_model=None, rate_assumptions=[], rate_sources=SOURCES,
        warnings=[
            "ACE NJ ordinary hypothetical account: territory, BGS-RSCP, PLS, tax status and written interconnection approval are independent facts.",
            "Exactly30 local days within one calendar month, season and verified regime only; proration, full-year coverage and export settlement are unsupported.",
            "MGS cost and minimum-cycling proofs concern quantities before measurement rounding; final bill rounds kWh/demand. No minimum rounded-invoice claim; exact half ties reject.",
            "RS retains raw energy, applies dated mandatory relief/recovery and rejects negative post-credit balances. No inferred refund or credit carry.",
            "Published CBT/SUT and supply administration are included once. Component half-up monetary cents are a study convention, not calibrated invoice arithmetic.",
            "MGS2025 DER/standby history is unsupported. Historical per-cycle perfect foresight and representative OpenDSS are not customer savings or surveyed-site validation."])
