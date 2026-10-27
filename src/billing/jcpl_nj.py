"""JCP&L NJ RS and utility-assigned nondemand GS secondary BGS-RSCP.

Complete calendar cycles retain monthly blocks/fixed charges. PartII3.07
prices verified linear changes on actual interval service energy. Eligibility,
November PLS and approved ordinary DER/standby classification are account facts.
"""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd

from .jcpl_nj_rates import COVERAGE, PLANS, SOURCES, rates_on

TIMEZONE = "America/New_York"


def account_fields(plan="RS"):
    return [
        dict(name="eligibility_confirmed", type="boolean", label="JCP&L New Jersey and selected RS/GS class independently confirmed"),
        dict(name="ordinary_service_confirmed", type="boolean", label="Ordinary taxable continuous service, one secondary single-phase meter; no special contract/discount"),
        dict(name="full_monthly_charges_confirmed", type="boolean", label="Complete ordinary calendar meter cycle within the 26–35-day monthly rule"),
        dict(name="no_special_provisions_confirmed", type="boolean", label="No special heating, water heater, worship/veteran, EV, computed load or facilities provisions"),
        dict(name="supply", type="choice", choices=["bgs_rscp"], label="JCP&L default BGS Residential Small Commercial Pricing"),
        dict(name="bgs_rscp_confirmed", type="boolean", label="Utility-assigned BGS-RSCP; no alternative supplier or CIEP election"),
        dict(name="cycle_source", type="text", label="Meter-cycle evidence or explicit hypothetical calendar-cycle assumption"),
        dict(name="tax_source", type="text", label="Ordinary NJ taxable-account evidence; filed CBT/SUT already included"),
        dict(name="demand_method", type="choice", choices=["not_applicable", "utility_no_meter"], label="GS: Company elected no demand meter after determining demand does not exceed 10 kW"),
        dict(name="gs_no_demand_meter_confirmed", type="boolean", label="GS: existing utility-assigned no-demand-meter branch retained for all proposed scenarios"),
        dict(name="gs_minimum_domain_confirmed", type="boolean", label="GS: independently documented prior eleven actual peaks and Contract Demand are at most 10 kW"),
        dict(name="contract_demand_kw", type="number", label="GS utility Contract Demand, independently confirmed at most 10 kW"),
        dict(name="prior_11_actual_peak_upper_bound_kw", type="number", label="GS conservative upper bound for the preceding eleven actual created peaks, at most 10 kW"),
        dict(name="prior_history_through_month", type="date", label="GS historical bound through the month immediately before this study (first day)"),
        dict(name="gs_classification_source", type="text", label="GS utility no-meter, contract and historical-peak evidence; never derived from simulated imports"),
        dict(name="peak_load_share_kw", type="number", label="GS independently assigned generation-capacity PLS below 500 kW"),
        dict(name="peak_load_share_as_of", type="date", label="GS November 1 PLS assignment for the applicable procurement year"),
        dict(name="pls_source", type="text", label="GS utility PLS/enrollment evidence or explicitly dated hypothetical assignment"),
        dict(name="der_ordinary_service_confirmed", type="boolean", label="Already-active approved ordinary Class I PV/storage NEM/parallel service, zero exports and no bank"),
        dict(name="der_activation_date", type="date", label="Effective ordinary DER service date after utility approval, meter installation and required initiation period"),
        dict(name="der_eligibility_source", type="text", label="Written active ordinary service approval, including storage/grid charging and annual-needs eligibility"),
        dict(name="gs_standby_not_applicable_confirmed", type="boolean", label="GS DER: utility confirms ordinary no-STB treatment and retained no-meter classification across proposed operation"),
        dict(name="gs_standby_source", type="text", label="GS utility ordinary NEM/no-STB confirmation; equipment size is not an exemption"),
        dict(name="rate_evidence_mode", type="choice", choices=["verified"], label="Verified dated components only; no missing-price fallback"),
    ]


def pls_as_of(day):
    current = pd.Timestamp(day)
    year = current.year if current.month >= 6 else current.year-1
    return f"{year-1}-11-01"


def history_through(day):
    return str((pd.Timestamp(day).replace(day=1)-pd.offsets.MonthBegin()).date())


def defaults(plan="RS"):
    if plan not in PLANS:
        raise ValueError("Select JCP&L NJ RS or nondemand GS secondary BGS-RSCP.")
    res = plan == "RS"
    return dict(tariff=plan, supply="bgs_rscp", export_mode="none", eligibility_confirmed=False,
        ordinary_service_confirmed=False, full_monthly_charges_confirmed=False,
        no_special_provisions_confirmed=False, bgs_rscp_confirmed=False,
        billing_month="2026-09-01", bill_date="2026-09-30", cycle_kind="regular", cycle_source="",
        tax_source="", tax_exempt=False, voltage="secondary", phase="single", voltage_v=240.,
        power_factor=1., meter_count=1, service_line_count=1, opening_credit_usd=0.,
        demand_interval_minutes=15, demand_method="not_applicable" if res else "utility_no_meter",
        gs_no_demand_meter_confirmed=False, gs_minimum_domain_confirmed=False,
        contract_demand_kw=0. if res else 5., prior_11_actual_peak_upper_bound_kw=0. if res else 10.,
        prior_history_through_month="" if res else "2026-08-01", gs_classification_source="",
        peak_load_share_kw=None if res else 10., peak_load_share_as_of="" if res else "2025-11-01", pls_source="",
        der_ordinary_service_confirmed=False, der_activation_date="", der_eligibility_source="",
        gs_standby_not_applicable_confirmed=False, gs_standby_source="",
        rate_evidence_mode="verified", provisional_assumptions_accepted=False, hypothetical_account=False)


def hypothetical_defaults(plan="RS", day="2026-09-01"):
    a = defaults(plan); res = plan == "RS"
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True,
        full_monthly_charges_confirmed=True, no_special_provisions_confirmed=True,
        bgs_rscp_confirmed=True, hypothetical_account=True,
        cycle_source="Explicit hypothetical complete calendar meter cycle under JCP&L's 26–35-day ordinary monthly rule; not an actual customer statement",
        tax_source="Explicit hypothetical ordinary New Jersey taxable account, no exemption; filed CBT/SUT included once",
        der_ordinary_service_confirmed=True, der_activation_date="2024-12-01",
        der_eligibility_source="Explicit hypothetical already-active written JCP&L ordinary Class I PV/storage NEM approval, installed required meters/initiation period complete, sizing within annual needs and grid charging approved; zero exports/bank")
    if not res:
        a.update(gs_no_demand_meter_confirmed=True, gs_minimum_domain_confirmed=True,
            prior_history_through_month=history_through(day), peak_load_share_as_of=pls_as_of(day),
            gs_classification_source="Explicit hypothetical Company-assigned no-demand-meter branch retained across all scenarios; prior eleven actual created peaks at most10kW, Contract Demand5kW, independently confirmed",
            pls_source="Explicit hypothetical utility-assigned November PLS10kW for the named procurement year and retained BGS-RSCP; not inferred from monthly demand",
            gs_standby_not_applicable_confirmed=True,
            gs_standby_source="Explicit hypothetical written JCP&L confirmation of active ordinary NEM/no-STB treatment and retained no-meter classification throughout all proposed PV/storage scenarios; no categorical size exemption")
    return a


def catalog():
    return [dict(id=p, label="JCP&L NJ "+("RS residential BGS-RSCP" if p == "RS" else "GS secondary BGS-RSCP · utility-assigned no demand meter"),
        status="supported", customer_class="residential" if p == "RS" else "commercial", voltage="secondary",
        coverage=[dict(start=s, end=e, is_complete_bill=True,
            scope="Conditional ordinary component coverage; complete calendar cycles, service-dated linear changes") for s,e in COVERAGE],
        interval_minutes=[15], solar_modes=["non_export"], supply_arrangements=["bgs_rscp"],
        equipment_modes=["grid_only", "pv_only", "pv_battery"], representative_peak_kw=3. if p == "RS" else 5.,
        account_fields=account_fields(p), sources=SOURCES,
        eligibility="Confirmed ordinary taxable single-phase120/240V RS or utility-assigned GS no-demand-meter secondary BGS-RSCP, explicit calendar meter cycles and independently approved active DER account where present.",
        limitations=[
            "January2025–October2026 verified components only. Complete ordinary calendar cycles retain full monthly charges/600 or1000kWh blocks; partial/shifted cycles and unsupported nonlinear/fixed crossings reject.",
            "Verified linear per-kWh changes use actual interval imported energy under PartII3.07, including September15,2025 TEC and July15,2026 transmission/TEC. No uniform-days energy allocation or bill-date substitution.",
            "GS requires existing Company no-demand-meter assignment, Contract Demand and preceding eleven actual created peaks at most10kW, and actual current15-minute imports at most10kW. Conservative history bounds carry; metered/standby/general demand formulas are unimplemented.",
            "November PLS below500kW and BGS-RSCP enrollment are separate utility facts; monthly demand never establishes them. No CIEP, alternative supplier, heating/water-heater or special provisions.",
            "Raw kWh are retained; no ACE measurement rounding is borrowed. Component half-up cents and unrounded charge proofs are study conventions, not exact printed-invoice or rounded-cash optimum claims.",
            "RS includes mandatory -$30 July/August2025 and +$10 September2025–February2026. Negative raw or component-rounded post-relief balances reject; no refund/carry or forced purchases.",
            "DER requires already-active approved ordinary Class I NEM/PV/storage service, zero exports/bank and no special recurring fees. GS additionally needs utility-confirmed ordinary no-STB treatment and retained no-meter classification; no size exemption is inferred. No standalone storage, community solar or export settlement.",
            "Utility, NJ tax/supplier status, written interconnection, PJM market label JCPL and emergency-region FE-JC are independent. No wholesale price node or PLC/NSPL charge is inferred."])
        for p in PLANS]


def _reference(a, key):
    if not isinstance(a.get(key), str) or not 1 <= len(a[key].strip()) <= 500:
        raise ValueError("Document JCP&L cycle, tax, PLS, no-meter/history and operating approvals without personal identifiers.")


def _number(value, low, high):
    return type(value) in (int, float) and np.isfinite(value) and low <= value <= high


def cycle_rates(index, plan):
    idx = pd.DatetimeIndex(index); dates = np.array([str(v) for v in idx.date])
    unique = list(dict.fromkeys(dates)); records = {d:rates_on(d, plan) for d in unique}
    first = records[unique[0]]
    def nonlinear(r):
        return (r["customer"], r["distribution_energy"], r["generation_energy"],
                r["block_kwh"], r["season"], r["residential_generation_capacity_deferral"])
    if any(nonlinear(r) != nonlinear(first) for r in records.values()):
        raise ValueError("JCP&L nonlinear/fixed component crossing is unverified; only source-backed linear service changes may split a cycle.")
    keys = set(first["linear_rates"])
    if any(set(r["linear_rates"]) != keys for r in records.values()):
        raise ValueError("JCP&L dated linear-component inventory changed without an explicit model.")
    prices = {k:np.array([records[d]["linear_rates"][k] for d in dates]) for k in keys}
    segments = []; last = None
    for day in unique:
        r = records[day]
        identity = tuple((k,v["effective"]) for k,v in r["component_versions"].items())
        if identity == last:
            segments[-1]["end_date"] = day
        else:
            segments.append(dict(start_date=day, end_date=day, rates=r)); last=identity
    return first, prices, segments


def cycle_review(a, index):
    idx = pd.DatetimeIndex(index); step = pd.Timedelta(minutes=15)
    if len(idx) < 2 or str(idx.tz) != TIMEZONE or not np.all(idx[1:]-idx[:-1] == step):
        raise ValueError("JCP&L needs consecutive America/New_York15-minute intervals; missing/duplicate/hourly data reject.")
    stop = idx[-1]+step; start = idx[0]
    if (start != start.normalize() or start.day != 1 or stop != start+pd.offsets.MonthBegin()
            or not 26 <= (stop.date()-start.date()).days <= 35
            or a.get("cycle_kind") != "regular" or a.get("full_monthly_charges_confirmed") is not True
            or a.get("billing_month") != str(start.date()) or a.get("bill_date") != str(idx[-1].date())):
        raise ValueError("JCP&L scope requires a complete matching ordinary calendar cycle and final-day bill date; partial/shifted proration is unsupported.")
    cycle_rates(idx, a["tariff"])
    return dict(service_start=str(start.date()), service_end=str(idx[-1].date()), billing_month=a["billing_month"],
        bill_date=a["bill_date"], cycle_days=(stop.date()-start.date()).days,
        elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)), monthly_charge_factor=1.,
        partial_period_proration_applied=False, linear_allocation_basis="PartII3.07 actual interval service energy, no days averaging")


def validate_account(a, index, equipment=None):
    if not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "bgs_rscp" or a.get("export_mode") != "none":
        raise ValueError("Select JCP&L NJ RS/GS secondary BGS-RSCP and zero export.")
    if set(a)-set(defaults(a["tariff"])):
        raise ValueError("JCP&L account has unsupported fields; no silent alternate billing method.")
    if a.get("rate_evidence_mode") != "verified" or a.get("provisional_assumptions_accepted") is not False:
        raise ValueError("JCP&L has no provisional or missing-price fallback.")
    for k in ("eligibility_confirmed", "ordinary_service_confirmed", "full_monthly_charges_confirmed", "no_special_provisions_confirmed", "bgs_rscp_confirmed"):
        if a.get(k) is not True:
            raise ValueError("Confirm JCP&L class, ordinary calendar service and BGS-RSCP independently.")
    for k in ("cycle_source", "tax_source"):
        _reference(a,k)
    if (a.get("tax_exempt") is not False
            or (a.get("voltage"),a.get("phase"),a.get("voltage_v"),a.get("power_factor")) != ("secondary","single",240.,1.)
            or a.get("meter_count") != 1 or a.get("service_line_count") != 1
            or a.get("opening_credit_usd") != 0. or a.get("demand_interval_minutes") != 15
            or any(not _number(a.get(k),0.,1e6) for k in ("voltage_v","power_factor","meter_count","service_line_count","opening_credit_usd","demand_interval_minutes"))):
        raise ValueError("JCP&L first scope is one taxable120/240V single-phase meter/service, unity billing PF,15-minute intervals and no opening bank.")
    cycle = cycle_review(a,index)
    if a["tariff"] == "GS":
        if (a.get("demand_method") != "utility_no_meter" or a.get("gs_no_demand_meter_confirmed") is not True
                or a.get("gs_minimum_domain_confirmed") is not True
                or not _number(a.get("contract_demand_kw"),0.,10.)
                or not _number(a.get("prior_11_actual_peak_upper_bound_kw"),0.,10.)
                or not _number(a.get("peak_load_share_kw"),0.,500.) or a["peak_load_share_kw"] >= 500.
                or a.get("peak_load_share_as_of") != pls_as_of(cycle["service_start"])):
            raise ValueError("GS needs Company-assigned no demand meter, prior actual peaks/Contract Demand at most10kW and independent correct November PLS below500kW; no classification from optimized demand.")
        for k in ("gs_classification_source", "pls_source"):
            _reference(a,k)
    elif (a.get("demand_method") != "not_applicable" or a.get("gs_no_demand_meter_confirmed") is not False
            or a.get("gs_minimum_domain_confirmed") is not False or a.get("contract_demand_kw") != 0.
            or a.get("prior_11_actual_peak_upper_bound_kw") != 0. or a.get("prior_history_through_month") != ""
            or a.get("peak_load_share_kw") is not None or a.get("peak_load_share_as_of") != ""):
        raise ValueError("RS has no GS demand/history or PLS assignment.")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("JCP&L DER needs already-active approved ordinary PV/storage NEM service; no standalone storage or export settlement.")
        _reference(a,"der_eligibility_source")
        try:
            activation = pd.Timestamp(a["der_activation_date"])
            valid = str(activation.date()) == a["der_activation_date"] and activation.date() <= pd.DatetimeIndex(index)[0].date()
        except (TypeError,ValueError,KeyError):
            valid = False
        if not valid:
            raise ValueError("JCP&L DER must already be active before the cycle after installed metering, approval and required initiation period; application alone is insufficient.")
        if a["tariff"] == "GS":
            if a.get("gs_standby_not_applicable_confirmed") is not True:
                raise ValueError("GS DER needs utility-confirmed ordinary NEM/no-STB treatment and retained no-meter classification; no size-based standby exemption is inferred.")
            _reference(a,"gs_standby_source")
        if max(equipment.get("pv_dc_kw",0.),equipment.get("pv_ac_kw",0.))+equipment.get("battery_kw",0.) > 25.+1e-8:
            raise ValueError("JCP&L study capacity is at most25kW combined PV/storage; this is not a standby exemption or interconnection approval.")


def validate_state(a, index, state=None, equipment=None):
    if a["tariff"] == "RS":
        if state not in (None,{}):
            raise ValueError("JCP&L RS has no modeled carried credit/demand state.")
        return
    prior = history_through(pd.DatetimeIndex(index)[0])
    if state in (None,{}):
        if a.get("prior_history_through_month") != prior:
            raise ValueError("GS independent prior eleven actual-peak bound must end immediately before the initial study cycle.")
    elif (not isinstance(state,dict) or set(state) != {"gs_history_peak_upper_bound_kw","through_month"}
            or state["through_month"] != prior or not _number(state["gs_history_peak_upper_bound_kw"],0.,10.)):
        raise ValueError("GS carried conservative history bound must be at most10kW and from the immediately preceding cycle; no missing months or reset.")


def charge_lines(index, imports, exports, a, *, math, state=None):
    cycle = cycle_review(a,index); validate_state(a,index,state=state)
    if math.convex:
        math.constraints.append(exports == 0)
    elif np.max(exports) > 1e-5:
        raise ValueError("JCP&L export/NEM credit settlement is not implemented; exports must be zero.")
    r, prices, segments = cycle_rates(index,a["tariff"]); energy = math.hours*math.sum(imports)
    def block(rates):
        return energy*rates[0] if rates[0] == rates[1] else math.tiered(energy,[r["block_kwh"]],rates)
    lines = {"distribution_customer":r["customer"], "distribution_energy":block(r["distribution_energy"]),
             "bgs_generation_energy":block(r["generation_energy"])}
    lines.update({name:energy*float(values[0]) if np.all(values == values[0])
                  else math.hours*math.dot(imports,values) for name,values in prices.items()})
    peak = math.demand(imports,index,minutes=15); res = a["tariff"] == "RS"
    next_state = {}; opening = None
    if res:
        lines["residential_generation_capacity_deferral"] = r["residential_generation_capacity_deferral"]
        if not math.convex:
            rounded = sum(Decimal(str(v)).quantize(Decimal(".01"),rounding=ROUND_HALF_UP) for v in lines.values())
            if sum(lines.values()) < -1e-7 or rounded < 0:
                raise ValueError("JCP&L negative post-relief balance settlement is unverified; no refund/carry or forced extra purchases.")
    else:
        if math.convex:
            math.constraints.append(peak <= 10.)
        elif peak > 10.+1e-7:
            raise ValueError("GS ordinary no-demand-meter domain requires actual15-minute imports at most10kW; metered/general demand service is unimplemented.")
        opening = max(a["prior_11_actual_peak_upper_bound_kw"],(state or {}).get("gs_history_peak_upper_bound_kw",0.),a["contract_demand_kw"])
        closing = math.maximum(peak,opening)
        next_state = dict(gs_history_peak_upper_bound_kw=closing if math.convex else float(closing),through_month=a["billing_month"])
        lines.update(distribution_demand=0., minimum_demand=0., reactive_demand=0.)
    return dict(lines=lines, metrics={**cycle, "raw_import_kwh":energy,"actual_15_minute_peak_kw":peak,
            "quantity_basis":"raw_import_energy_no_unsourced_quantity_rounding",
            "applied_rate_segments":segments,"dated_linear_component_count":len(prices),
            "whole_cycle_block_kwh":r["block_kwh"],"unchanged_monthly_blocks_verified":True,
            "gs_no_meter_billing_treatment":"not_applicable" if res else "Company considers billing demand below10kW; all excess10 demand/minimum charges inactive",
            "opening_conservative_peak_bound_kw":opening,"contract_demand_kw":a["contract_demand_kw"],
            "gs_minimum_inactive_verified":None if res else True,
            "gs_standby_treatment":"RS outside STB classes" if res else "Conditional ordinary utility-confirmed account only; no categorical exemption or STB formula modeled",
            "tax_treatment":r["tax_basis"],"additional_tax_percentage_applied":False,
            "objective_scope":"unrounded_ordinary_component_charges","rounded_cash_optimum_claimed":False,
            "rate_allocation":"Actual interval energy at each filed service-effective linear rate; no whole-month end rate or days-weighted energy"},
        next_state=next_state,is_complete_bill=True,excluded_components=[],rate_evidence_status="verified",
        assumption_model=None,rate_assumptions=[],rate_sources=SOURCES,
        warnings=[
            "JCP&L NJ ordinary account facts are explicit: utility, BGS-RSCP, tax status, PLS, no-meter/history and written DER classification are independent of coordinates or modeled load.",
            "Complete calendar cycles January2025–October2026 only. Verified linear changes use actual interval service energy under PartII3.07; monthly blocks stay whole. Other allocation/partial/shifted cycles reject.",
            "GS below10kW billing requires Company no-meter assignment, independent Contract Demand/prior actual peaks at most10kW and current actual imports at most10kW. Conservative bounds retain history; no metered demand/ratchet/standby formula or utility eligibility from optimization.",
            "PV/storage requires already-active written ordinary NEM approval, correct installed meter/initiation, zero exports/bank and confirmed storage/grid charging. GS additionally requires explicit ordinary no-STB treatment and retained no-meter classification; capacity is not an exemption.",
            "Published CBT/SUT and BGS capacity/ancillary/related costs are included once. No wholesale LMP, extra tax/admin or PLC/NSPL charge is added; all dated TEC owner blocks are counted once.",
            "Mandatory RS relief/recovery is retained; negative raw or component-rounded balances reject without forcing extra purchases. Regulatory EGCC recovery is not an individual credit bank.",
            "Raw kWh and component half-up cents are retained. Per-cycle historical perfect foresight proves unrounded modeled charges, not an exact printed/rounded invoice, joint annual optimum, customer savings or surveyed-site electrical feasibility."])
