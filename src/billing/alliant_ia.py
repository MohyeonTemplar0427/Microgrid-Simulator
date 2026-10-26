"""Alliant / Interstate Power & Light ordinary Iowa retail billing.

Filed expressions supply both numerical billing and dispatch objectives.
Wholesale prices, account eligibility and physical circuits remain separate.
"""
from datetime import date, timedelta, timezone

import numpy as np
import pandas as pd

from .alliant_ia_rates import BASE, COVERAGE, PLANS, SOURCES, service_rates

UTILITY = "alliant_energy_iowa"
TIMEZONE = "America/Chicago"
STANDARD_TIME = timezone(timedelta(hours=-6), "CST")
DATED_RIDERS = ("energy_efficiency", "demand_response", "regional_transmission")


def _rider_segments(daily):
    result = {}
    for component in DATED_RIDERS:
        segments = []
        for day, values in sorted(daily.items()):
            factor = values[component]
            reference = values["rider_versions"][component]["reference"]
            if segments and (factor, reference) == (segments[-1]["factor_usd_per_kwh"], segments[-1]["reference"]):
                segments[-1]["end"] = day.isoformat()
                segments[-1]["calendar_days"] += 1
            else:
                segments.append(dict(start=day.isoformat(), end=day.isoformat(), calendar_days=1,
                                     factor_usd_per_kwh=factor, reference=reference))
        result[component] = segments
    return result


def periods(index, plan):
    idx = pd.DatetimeIndex(index)
    if plan not in PLANS or str(idx.tz) != TIMEZONE:
        raise ValueError("Choose an Alliant Iowa plan and America/Chicago timestamps.")
    # The rate sheets explicitly name CST. The public program page says CT;
    # this bounded interpretation is disclosed and requires meter confirmation.
    clock = idx.tz_convert(STANDARD_TIME)
    hour = clock.hour.to_numpy()+clock.minute.to_numpy()/60
    summer = np.asarray((idx.month >= 6) & (idx.month <= 8))
    independence = np.asarray((idx.month == 7) & (idx.day == 4))
    tou = plan in ("407", "427", "607")
    peak = np.asarray(tou & summer & (clock.dayofweek < 5) & ~independence & (hour >= 14) & (hour < 19))
    super_off = np.asarray((hour >= 0) & (hour < 8)) if plan == "427" else np.zeros(len(idx), dtype=bool)
    return dict(peak=peak, super_off=super_off, off=~(peak | super_off), summer=summer)


def interval_rates(index, plan, *, billing_month=None):
    """Per-cycle billing coefficients; callers must not blend utility cycles."""
    idx = pd.DatetimeIndex(index)
    p = periods(idx, plan)
    if not len(idx) or len(set(zip(idx.year, idx.month))) != 1:
        raise ValueError("Alliant Iowa interval billing coefficients need one calendar cycle; calculate annual studies through their separate monthly cycles.")
    daily = {d: service_rates(d, plan, billing_month=billing_month) for d in sorted(set(idx.date))}
    base = BASE[plan]
    energy = np.where(p["summer"], base[1], base[0])
    if plan in ("407", "427", "607"):
        energy = np.where(p["peak"], base[2], energy)
    if plan == "427":
        energy = np.where(p["super_off"], np.where(p["summer"], base[4], base[3]), energy)
    result = dict(energy=energy, **{k: np.asarray([daily[d][k] for d in idx.date])
        for k in ("energy_adjustment", "tax_benefit")})
    # Actual utility bills split a changed rider using whole-cycle kWh times
    # calendar-day fractions, not actual imports on either side of the change.
    # A constant weighted coefficient preserves that rule in the optimizer.
    for key in DATED_RIDERS:
        values = [day[key] for day in daily.values()]
        factor = values[0] if len(set(values)) == 1 else sum(values)/len(values)
        result[key] = np.full(len(idx), factor)
    return result


def account_fields(plan="400"):
    fields = [dict(name=k, type="boolean", default=False, required=True, label=label) for k, label in (
        ("eligibility_confirmed", "Iowa Interstate Power & Light/Alliant territory and selected tariff independently confirmed"),
        ("ordinary_service_confirmed", "Ordinary bundled account: one meter/service line, no special facilities, exemptions, discretionary bill credits or Second Nature subscription"),
        ("full_monthly_charges_confirmed", "Complete calendar meter cycle, designated billing month and full charges confirmed; no shifted/partial-cycle approximation"),
        ("local_charges_confirmed", "Explicit local tax jurisdiction confirmed; no franchise, government-relocation or other supplemental charges"))]
    fields += [dict(name="rate_evidence_mode", type="choice", choices=["verified"], default="verified",
                   label="Verified filed components only; no Alliant provisional model is available"),
        dict(name="provisional_assumptions_accepted", type="boolean", default=False,
             label="Alliant has no provisional-rate model; this permission must remain false"),
        dict(name="tax_jurisdiction", type="text", choices=["unincorporated_linn_county"],
                    label="Verified tax jurisdiction; independent of utility map and weather coordinates"),
        dict(name="tax_source", type="text", required=True, label="Tax/local-charge evidence or explicit hypothetical ordinary account; omit personal information"),
        dict(name="cycle_source", type="text", required=True, label="Meter-cycle evidence or explicit hypothetical calendar-cycle assumption"),
        dict(name="dg_enrollment_confirmed", type="boolean", default=False,
             label="PV/storage: approved IO-eligible non-export installation, applicable110%-annual-use sizing confirmed, ordinary inflow tariff retained, no standby/net-metering or extra charges"),
        dict(name="dg_source", type="text", label="Approved non-export ordinary billing/interconnection reference or explicit hypothetical agreement")]
    if plan in ("407", "427", "607"):
        fields += [dict(name="tou_enrollment_confirmed", type="boolean", default=False, required=True,
                        label="TOD meter, enrollment and minimum one-year term confirmed"),
            dict(name="tou_clock_confirmed", type="boolean", default=False, required=True,
                 label="Account meter follows the filed fixed-CST windows; utility confirmation required because the public guide says CT")]
    if plan in ("600", "607"):
        fields.append(dict(name="small_general_confirmed", type="boolean", default=False, required=True,
            label="Utility-approved600/607 classification and prior12-month monthly usage history confirmed; each modeled cycle stays below20,000kWh"))
    return fields


def defaults(plan="400"):
    if plan not in PLANS:
        raise ValueError("Choose Alliant Iowa400/407/427/600/607.")
    return dict(tariff=plan, supply="bundled", export_mode="none", eligibility_confirmed=False,
        ordinary_service_confirmed=False, full_monthly_charges_confirmed=False, local_charges_confirmed=False,
        tax_jurisdiction="unincorporated_linn_county", tax_source="", cycle_source="",
        rate_evidence_mode="verified", provisional_assumptions_accepted=False,
        tou_enrollment_confirmed=False, tou_clock_confirmed=False, small_general_confirmed=False,
        dg_enrollment_confirmed=False, dg_source="", opening_credit_usd=0.,
        billing_month="2026-07-01", bill_date="2026-07-31", cycle_kind="regular",
        voltage="secondary", phase="single", voltage_v=240., power_factor=1., meter_count=1, service_line_count=1)


def hypothetical_defaults(plan="400"):
    a = defaults(plan)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True,
        full_monthly_charges_confirmed=True, local_charges_confirmed=True,
        tou_enrollment_confirmed=True, tou_clock_confirmed=True, small_general_confirmed=True,
        tax_source="Explicit hypothetical ordinary unincorporated Linn County account: residential state exemption,1%local-option; commercial6%state+1%local-option; no franchise/extra fees",
        cycle_source="Explicit hypothetical complete calendar meter readings; not actual customer billing data",
        dg_enrollment_confirmed=True,
        dg_source="Explicit hypothetical utility-approved IO-eligible non-export PV/storage;110%annual-use sizing satisfied; ordinary inflow tariff retained without extra agreement charges")
    return a


def catalog():
    labels = {"400": "Residential seasonal", "407": "Residential two-part Time of Day",
              "427": "Residential three-part Time of Day", "600": "General Service seasonal",
              "607": "General Service two-part Time of Day"}
    return [dict(id=p, label="Alliant Iowa "+labels[p], status="supported",
        customer_class="residential" if p in ("400", "407", "427") else "commercial",
        coverage=[dict(start=s, end=e) for s, e in COVERAGE], voltage="secondary",
        interval_minutes=[15],
        solar_modes=["non_export"], supply_arrangements=["bundled"],
        equipment_modes=["grid_only", "pv_only", "pv_battery"], representative_peak_kw=3.,
        account_fields=account_fields(p), sources=SOURCES,
        eligibility="Confirmed ordinary Iowa IPL bundled account, one meter/service line, secondary120/240V single-phase, complete calendar cycles and explicit unincorporated Linn County tax facts. Coordinates do not establish eligibility.",
        limitations=["Verified complete calendar cycles January–December2025 and June–October2026 only; consecutive15-minute meter intervals required, including for IO inflow treatment. No historical/provisional price fallback; January–May2026 remains unsupported and November/December2026 EAC is not published.",
            "Summer is June–August. Filed TOD2–7pm CST summer weekdays excluding actual Independence Day;427 adds midnight–8am CST daily super-off-peak. FixedCST clock interpretation requires account confirmation; public guide saysCT. No other holiday/observed-day substitution.",
            "Ordinary600/607 classification is a utility account fact with monthly usage history. This bounded study keeps every complete cycle below20,000kWh; this is not a20,000annual-kWh cutoff or automatic enrollment decision.",
            "No demand charges under these selected plans. Optional demand507/707, large general, electric vehicle pilots, three-phase extras, exemptions and special contracts are not implemented.",
            "EAC composite is applied once, including its included AEP/fuel/RCE components. Separate TBR credit applies January–September2025. June2025 EECR/DRCR changes use whole-cycle kWh times calendar-day fractions, not actual interval purchases on each side. No wholesale MISO LMP, capacity/PLC or transmission-tag amount is added to ordinary retail charges.",
            "Only approved ordinary non-export PV/storage; exports/NEM/inflow-outflow settlement, standalone storage and additional standby agreements remain unsupported."])
        for p in PLANS]


def cycle_review(a, index):
    if a.get("rate_evidence_mode", "verified") != "verified" or a.get("provisional_assumptions_accepted", False) is not False:
        raise ValueError("Alliant Iowa has no provisional-rate mode; other utilities' acceptance cannot authorize missing prices.")
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2 or str(idx.tz) != TIMEZONE:
        raise ValueError("Alliant Iowa requires America/Chicago interval timestamps.")
    step = idx[1]-idx[0]
    if step != pd.Timedelta(minutes=15) or not np.all(idx[1:]-idx[:-1] == step):
        raise ValueError("Alliant Iowa requires consecutive15-minute meter intervals; gaps, duplicates and30-minute averages are rejected rather than aggregated across IO netting periods.")
    stop = idx[-1]+step
    if (idx[0] != idx[0].normalize() or idx[0].day != 1 or stop != idx[0]+pd.offsets.MonthBegin()
            or a.get("cycle_kind") != "regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Alliant Iowa first scope requires complete calendar meter cycles; no inferred partial/crossing allocation.")
    if a.get("billing_month") != str(idx[0].date()) or a.get("bill_date") != str(idx[-1].date()):
        raise ValueError("Alliant Iowa designated billing month must align with service and the bill date must be its final service day.")
    for day in (idx[0].date(), idx[-1].date()):
        service_rates(day, a["tariff"], billing_month=a["billing_month"])
    return dict(cycle_days=(stop.date()-idx[0].date()).days,
        elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)), monthly_charge_factor=1.,
        service_start=str(idx[0].date()), service_end=str(idx[-1].date()), billing_month=a["billing_month"],
        bill_date=a["bill_date"], partial_period_proration_applied=False)


def evidence(index, account):
    cycle_review(account, index)
    return dict(rate_evidence_status="verified", assumption_model=None, rate_assumptions=[],
                objective_scope="complete_utility_bill")


def validate_account(a, index, equipment=None):
    if not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "bundled" or a.get("export_mode") != "none":
        raise ValueError("Alliant Iowa needs a supported ordinary bundled tariff with zero export.")
    if a.get("rate_evidence_mode", "verified") != "verified" or a.get("provisional_assumptions_accepted", False) is not False:
        raise ValueError("Alliant Iowa has no provisional-rate mode; other utilities' acceptance cannot authorize missing prices.")
    if any(a.get(k) is not True for k in ("eligibility_confirmed", "ordinary_service_confirmed", "local_charges_confirmed")) or a.get("tax_jurisdiction") != "unincorporated_linn_county":
        raise ValueError("Confirm Alliant Iowa ordinary eligibility and the explicit unincorporated Linn County tax jurisdiction.")
    for key in ("tax_source", "cycle_source"):
        if not isinstance(a.get(key), str) or not 1 <= len(a[key].strip()) <= 500:
            raise ValueError("Document Alliant Iowa tax/local charges and complete meter-cycle assumptions.")
    if ((a.get("voltage"), a.get("phase"), a.get("voltage_v"), a.get("power_factor")) != ("secondary", "single", 240., 1.)
            or a.get("opening_credit_usd") != 0. or a.get("meter_count") != 1 or a.get("service_line_count") != 1):
        raise ValueError("Alliant Iowa first scope is ordinary120/240V single-phase, unity billing PF, one meter/service line, no opening credits or special facilities.")
    if a["tariff"] in ("407", "427", "607") and (a.get("tou_enrollment_confirmed") is not True or a.get("tou_clock_confirmed") is not True):
        raise ValueError("Confirm Alliant TOD enrollment, minimum one-year term and the actual account's filed-CST meter clock.")
    if a["tariff"] in ("600", "607") and a.get("small_general_confirmed") is not True:
        raise ValueError("Confirm600/607 classification and monthly usage history independently of the synthetic load.")
    cycle_review(a, index)
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if (not equipment.get("pv") or a.get("dg_enrollment_confirmed") is not True
                or not isinstance(a.get("dg_source"), str) or not 1 <= len(a["dg_source"].strip()) <= 500):
            raise ValueError("Alliant Iowa requires approved ordinary non-export PV/storage; standalone storage and assumed export/standby eligibility are unsupported.")
        if max(equipment.get("pv_dc_kw", 0.), equipment.get("pv_ac_kw", 0.))+equipment.get("battery_kw", 0.) > 20.+1e-8:
            raise ValueError("Alliant Iowa first DER scope conservatively limits aggregate PV nameplate plus battery discharge to20kW; this is a study bound, not proof of an interconnection category.")


def validate_state(a, index, *, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("Alliant Iowa ordinary non-export plans have no modeled opening credit/demand state.")


def charge_lines(index, imports, exports, a, *, math, state=None):
    validate_state(a, index, state=state)
    idx = pd.DatetimeIndex(index)
    cycle = cycle_review(a, idx)
    residential = a["tariff"] in ("400", "407", "427")
    if math.convex:
        math.constraints.append(exports == 0)
        if not residential:
            math.constraints.append(math.hours*math.sum(imports) <= 19999.999)
    elif np.max(exports) > 1e-5 or not residential and math.hours*np.sum(imports) > 19999.999+1e-7:
        raise ValueError("Alliant ordinary non-export600/607 cases must keep cycle purchases below20,000kWh; no automatic reclassification is modeled.")
    r = service_rates(idx[0].date(), a["tariff"], billing_month=a["billing_month"])
    rates = interval_rates(idx, a["tariff"], billing_month=a["billing_month"])
    daily = {day: service_rates(day, a["tariff"], billing_month=a["billing_month"]) for day in sorted(set(idx.date))}
    rider_segments = _rider_segments(daily)
    lines = dict(customer=r["customer_daily"]*cycle["cycle_days"], energy=math.hours*math.dot(imports, rates["energy"]))
    for key in ("energy_adjustment", "energy_efficiency", "demand_response", "regional_transmission"):
        lines[key] = math.hours*math.dot(imports, rates[key])
    # The 2025 EAC's TBR column is dashed; the standalone credit is additional.
    # Leave the existing post-expiry itemized schema unchanged.
    if np.any(rates["tax_benefit"]):
        lines["tax_benefit"] = math.hours*math.dot(imports, rates["tax_benefit"])
    tax_base = sum(lines.values())
    lines["iowa_state_sales_tax"] = tax_base*(0. if residential else .06)
    lines["local_option_sales_tax"] = tax_base*.01
    tou = a["tariff"] in ("407", "427", "607")
    return dict(lines=lines, metrics={**cycle, "measured_demand_charge":False,
        "intraday_time_of_use_pricing":tou, "base_version":r["base_version"], "eac_version":r["eac_version"],
        "rider_version":r["rider_version"], "rider_versions":r["rider_versions"],
        "rider_versions_basis":"First-service-date source snapshots; rider_allocation_segments records every version used in a crossing month",
        "rider_allocation_segments":rider_segments,
        "rider_allocation_basis":"Whole-cycle imported kWh times calendar-day-weighted dated EECR/DRCR/RTS factors; not interval-specific consumption allocation",
        "billed_rider_factors_usd_per_kwh":{k:float(rates[k][0]) for k in DATED_RIDERS},
        "calendar_evidence_status":"filed_CST_interpretation_utility_confirmation_required" if tou else "not_time_of_use",
        "calendar_confirmation_required":tou, "clock_basis":"fixedCST (UTC-06:00)" if tou else None,
        "holiday_basis":"Actual Independence Day only; no observed substitute;427 daily super-off-peak retained" if tou else None,
        "tax_jurisdiction":a["tax_jurisdiction"], "state_sales_tax_rate":0. if residential else .06,
        "local_option_sales_tax_rate":.01, "sales_tax_base_usd":tax_base,
        "eac_includes_rce":r["eac_includes_rce"], "included_rce_usd_per_kwh":r["rce_included_usd_per_kwh"],
        "tax_benefit_usd_per_kwh":r["tax_benefit"],
        "component_application_clocks":{
            "energy_adjustment":"Utility-designated billing month, aligned to the complete calendar study cycle",
            "rate_case_expense":"Included in EAC for bills rendered September2025 onward; not charged again",
            "tax_benefit":"Service-date credit expires October1,2025; January–September2025 calendar cycles receive it, October onward do not",
            "dated_riders":"EECR/DRCR/RTS effective-day segments weight whole-cycle imported kWh by calendar days"},
        "eac_treatment":"Published monthly composite once; included AEP/fuel/RCE not separately added; standalone TBR credit applied only during its verified application window",
        "dg_enrollment_confirmed":a.get("dg_enrollment_confirmed") is True,
        "generation_program":("Confirmed IO-eligible DG; ordinary inflow tariff applies, outflow constrained to zero and no export settlement modeled"
            if a.get("dg_enrollment_confirmed") is True else "Ordinary absent-DER service; no IO/DG enrollment asserted"),
        "capacity_transmission_treatment":"Ordinary bundled retail rates plus filed RTS once; no additional MISO LMP, capacity/PLC or transmission-tag charge",
        "rate_effective_basis":"Dated service/base and billing-month riders aligned to complete calendar cycles; no guessed crossing allocation"},
        next_state={}, is_complete_bill=True, rate_evidence_status="verified", assumption_model=None,
        rate_assumptions=[], rate_sources=SOURCES,
        warnings=(["TOD clock requires utility confirmation: this model follows the filed fixed-CST windows; the public Time of Day guide uses the broader termCT."] if tou else [])+[
            "Ordinary hypothetical non-export account; distribution service, tariff enrollment, tax jurisdiction and interconnection are independent account facts.",
            "Verified historical component reconstruction; no unsupported-date/provisional fallback. Early2025 DRCR is corroborated by official plan guides, actual utility bills and the filed successor; the original sixth-sheet start is not asserted.",
            "Dispatch is rolling-cycle historical perfect foresight; representative electrical replay is not site-specific engineering approval."])
