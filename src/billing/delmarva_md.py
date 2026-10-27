"""Delmarva Maryland R / bounded estimated-demand SGS-S Type I SOS.

Verified recurring-charge subtotals, with explicit omitted credits/state tax.
Utility, supplier, locality and PJM metadata are independently confirmed facts.
"""
import numpy as np
import pandas as pd

from .delmarva_md_rates import COVERAGE, PLANS, SOURCES, rates_on

UTILITY = "delmarva_maryland"
TIMEZONE = "America/New_York"
RELIEF_EXCLUSION = "account_specific_legislative_relief_refund"
SALES_TAX_EXCLUSION = "maryland_state_sales_tax"
RRC_EXCLUSION = "residential_rggi_rate_credit"


def excluded_components(plan):
    return [RELIEF_EXCLUSION, RRC_EXCLUSION] if plan == "R" else [SALES_TAX_EXCLUSION]


def account_fields(plan="R"):
    return [dict(name=k, type="boolean", default=False, required=True, label=v)
        for k, v in (
            ("eligibility_confirmed", "Delmarva Maryland delivery, selected R/SGS-S schedule and residential/Type I SOS independently confirmed"),
            ("ordinary_service_confirmed", "Ordinary single-meter secondary service; no competitive supplier, assistance, opt-out, off-peak contract, standby or special charges"),
            ("full_monthly_charges_confirmed", "Complete hypothetical calendar meter cycle and matching billing month; no partial/shifted allocation"),
            ("local_charges_confirmed", "Ordinary unincorporated Wicomico County account; tax locality and absence of additional local energy charges independently confirmed"))] + [
        dict(name="cycle_source", type="text", required=True, label="Meter-cycle evidence or explicit hypothetical calendar-cycle assumption; omit personal information"),
        dict(name="tax_source", type="text", required=True, label="Tax locality and ordinary residential/business status evidence or explicit hypothetical assumption"),
        dict(name="type_i_confirmed", type="boolean", default=False, label="SGS-S: existing utility-assigned Type I SOS membership, including prior usage/demand, independently confirmed"),
        dict(name="demand_method", type="choice", choices=["not_applicable", "utility_estimate"], label="SGS-S scope: utility-assigned estimated demand under Schedule E.3 only"),
        dict(name="estimated_demand_source", type="text", label="SGS-S: utility approval retaining E.3 estimated demand across grid/PV/storage scenarios, or explicit hypothetical agreement"),
        dict(name="usc_band", type="choice", choices=["residential", "175_to_1299"], label="Utility-assigned universal-service band; retained across scenarios"),
        dict(name="usc_assignment_2025_source", type="text", label="SGS-S: assigned USC band throughout 2025, before/after the first-quarter update; evidence or explicit hypothetical assumption"),
        dict(name="usc_assignment_2026_source", type="text", label="SGS-S: assigned USC band throughout 2026, before/after the first-quarter update; evidence or explicit hypothetical assumption"),
        dict(name="subtotal_scope_confirmed", type="boolean", default=False, required=True, label="Verified-charge subtotal only: R excludes RGGI/legislative credits; SGS-S excludes unresolved state sales-tax calculation"),
        dict(name="relief_policy", type="choice", choices=["exclude_account_specific_refunds"], label="Residential scope excludes unverified historical-account relief refunds"),
        dict(name="der_ordinary_service_confirmed", type="boolean", default=False, label="PV/storage: approved ordinary parallel service without standby/special charges; zero exports"),
        dict(name="der_eligibility_source", type="text", label="Approved interconnection/ordinary-service evidence or explicit hypothetical agreement"),
        dict(name="rate_evidence_mode", type="choice", choices=["verified"], default="verified", label="Verified Delmarva Maryland monthly components only; no fallback"),
    ]


def defaults(plan="R"):
    if plan not in PLANS:
        raise ValueError("Select Delmarva Maryland R or SGS-S Type I SOS.")
    return dict(tariff=plan, supply="sos", export_mode="none", eligibility_confirmed=False,
        ordinary_service_confirmed=False, full_monthly_charges_confirmed=False, local_charges_confirmed=False,
        tax_jurisdiction="wicomico_unincorporated", tax_exempt=False, tax_source="", cycle_source="",
        cycle_kind="regular", billing_month="2026-09-01", bill_date="2026-09-30",
        type_i_confirmed=False, demand_method="not_applicable" if plan == "R" else "utility_estimate", estimated_demand_source="",
        usc_band="residential" if plan == "R" else "175_to_1299",
        usc_assignment_2025_source="", usc_assignment_2026_source="",
        relief_policy="exclude_account_specific_refunds", subtotal_scope_confirmed=False,
        rate_evidence_mode="verified", provisional_assumptions_accepted=False,
        der_ordinary_service_confirmed=False, der_eligibility_source="", voltage="secondary", phase="single",
        voltage_v=240., power_factor=1., meter_count=1, service_line_count=1,
        opening_credit_usd=0., demand_interval_minutes=15)


def hypothetical_defaults(plan="R", year=2025):
    a = defaults(plan)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True,
        full_monthly_charges_confirmed=True, local_charges_confirmed=True,
        type_i_confirmed=plan == "SGS-S", hypothetical_account=True, subtotal_scope_confirmed=True,
        tax_source="Explicit hypothetical ordinary unincorporated Wicomico County account; residential exemption or commercial status, no special exemptions or additional local energy levy",
        estimated_demand_source="Explicit hypothetical utility approval of Schedule SGS-S E.3 estimation retained across grid-only, PV and PV/storage studies; not inferred from load" if plan == "SGS-S" else "Not applicable to R",
        usc_assignment_2025_source="Explicit hypothetical utility-assigned $175–$1299 annual-delivery USC band throughout 2025, before and after its first-quarter update" if plan == "SGS-S" else "Residential USC",
        usc_assignment_2026_source="Explicit hypothetical utility-assigned $175–$1299 annual-delivery USC band throughout 2026, before and after its first-quarter update" if plan == "SGS-S" else "Residential USC",
        cycle_source="Explicit hypothetical complete calendar meter cycle and matching billing month; not an actual customer statement",
        der_ordinary_service_confirmed=True,
        der_eligibility_source="Explicit hypothetical Delmarva Maryland approval of ordinary PV/storage service, no standby/special charges and zero-export operation")
    return a


def catalog():
    return [dict(id=p, label="Delmarva Maryland " + ("Residential R SOS" if p == "R" else "SGS-S Type I SOS · utility-estimated demand"),
        status="supported", customer_class="residential" if p == "R" else "commercial",
        coverage=[dict(start=s, end=e, is_complete_bill=False, scope="Verified recurring-charge subtotal; plan-specific credits or state sales-tax calculation excluded", excluded_components=excluded_components(p)) for s, e in COVERAGE],
        voltage="secondary", interval_minutes=[15], solar_modes=["non_export"], supply_arrangements=["sos"],
        equipment_modes=["grid_only", "pv_only", "pv_battery"], representative_peak_kw=3.,
        account_fields=account_fields(p), sources=SOURCES,
        eligibility="Independently confirmed Delmarva Maryland R or secondary SGS-S Type I SOS with utility-assigned E.3 estimated demand; unincorporated Wicomico County, one ordinary meter and complete calendar cycles.",
        limitations=[
            "Only recovered complete calendar service/billing months; source gaps and unverified mid-month allocation reject, with no current-rate substitution.",
            "SGS-S estimation must be utility-assigned and retained across scenarios, not selected by the optimizer. Actual 15-minute import peaks stay below20kW and monthly imports at most3500kWh. Billed demand equals kWh/175, so distribution demand is charged and transmission demand remains within the first20kW free block.",
            "Metered/assessed demand, nearest-whole-kW rounding, off-peak contracts, usage above3500kWh and other supply types are not supported. Existing Type I classification and year-specific USC assignment remain independent historical account facts.",
            "R excludes unverified RGGI/legislative fixed credits; SGS-S excludes unresolved state sales-tax base/bracket calculation. Exclusions are not zero/exemptions. No complete amount due or complete-bill optimum is claimed.",
            "R study imports are bounded to7500kWh per month to keep the MES cap inactive; this is a study restriction, not tariff eligibility.",
            "Filed Delmarva GRT treatment is retained without extra Pepco/BGE gross-up. Wholesale LMP/PLC/NSPL are not added to SOS retail charges.",
            "PV/storage requires independently approved ordinary service. Combined PV/storage nameplate is limited to25kW by this implementation; no exports, NEM bank, standby or community-solar settlement.",
            "Maryland retail jurisdiction is separate from Delaware/Virginia and the DPL transmission zone. Coordinates establish neither territory nor tax status."])
        for p in PLANS]


def cycle_review(a, index):
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2 or str(idx.tz) != TIMEZONE:
        raise ValueError("Delmarva Maryland requires America/New_York timestamps and complete15-minute intervals.")
    step = pd.Timedelta(minutes=15)
    if not np.all(idx[1:]-idx[:-1] == step):
        raise ValueError("Delmarva Maryland requires consecutive15-minute intervals; missing/duplicate/hourly data reject.")
    stop = idx[-1]+step
    if (idx[0] != idx[0].normalize() or idx[0].day != 1 or stop != idx[0]+pd.offsets.MonthBegin()
            or a.get("cycle_kind") != "regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Delmarva Maryland requires complete calendar meter cycles; partial/shifted allocation is unverified.")
    if a.get("billing_month") != str(idx[0].date()) or a.get("bill_date") != str(idx[-1].date()):
        raise ValueError("Delmarva Maryland requires matching calendar service/billing month and bill date on its final service date.")
    rates_on(a["billing_month"], a["tariff"])
    return dict(service_start=str(idx[0].date()), service_end=str(idx[-1].date()),
        cycle_days=(stop.date()-idx[0].date()).days, elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)),
        billing_month=a["billing_month"], bill_date=a["bill_date"], monthly_charge_factor=1., partial_period_proration_applied=False)


def evidence(index, account):
    cycle_review(account, index)
    return dict(rate_evidence_status="verified", assumption_model=None, rate_assumptions=[], objective_scope="verified_charges_subtotal")


def _reference(a, key):
    if not isinstance(a.get(key), str) or not 1 <= len(a[key].strip()) <= 500:
        raise ValueError("Document Delmarva cycle, tax, USC, estimation and interconnection evidence without personal identifiers.")


def validate_account(a, index, equipment=None):
    if (not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "sos" or a.get("export_mode") != "none"):
        raise ValueError("Select ordinary Delmarva Maryland R/SGS-S residential/Type I SOS and zero export.")
    if a.get("rate_evidence_mode", "verified") != "verified" or a.get("provisional_assumptions_accepted", False) is not False:
        raise ValueError("Delmarva Maryland has no provisional-rate mode or missing-price fallback.")
    if a.get("relief_policy") != "exclude_account_specific_refunds" or a.get("subtotal_scope_confirmed") is not True:
        raise ValueError("Confirm the Delmarva verified-charge subtotal and its excluded credits or state sales-tax calculation.")
    if any(a.get(k) is not True for k in ("eligibility_confirmed", "ordinary_service_confirmed", "local_charges_confirmed")):
        raise ValueError("Confirm Delmarva Maryland service, schedule, SOS, ordinary use and tax locality independently of location.")
    for key in ("cycle_source", "tax_source"):
        _reference(a, key)
    if (a.get("tax_jurisdiction") != "wicomico_unincorporated" or a.get("tax_exempt") is not False
            or (a.get("voltage"), a.get("phase"), a.get("voltage_v"), a.get("power_factor")) != ("secondary", "single", 240., 1.)
            or a.get("meter_count") != 1 or a.get("service_line_count") != 1
            or a.get("opening_credit_usd") != 0. or a.get("demand_interval_minutes") != 15):
        raise ValueError("Delmarva first scope requires ordinary unincorporated Wicomico taxes, one120/240V single-phase meter/service, unity PF,15-minute grid and no opening credits.")
    if a["tariff"] == "SGS-S":
        if a.get("type_i_confirmed") is not True or a.get("usc_band") != "175_to_1299" or a.get("demand_method") != "utility_estimate":
            raise ValueError("Confirm existing SGS-S Type I SOS, assigned USC band $175–$1299 and utility-assigned E.3 estimated demand.")
        _reference(a, "usc_assignment_"+str(pd.DatetimeIndex(index)[0].year)+"_source")
        _reference(a, "estimated_demand_source")
    elif a.get("usc_band") != "residential" or a.get("type_i_confirmed") is not False or a.get("demand_method") != "not_applicable":
        raise ValueError("Delmarva R requires residential SOS, residential USC and no commercial demand method.")
    cycle_review(a, index)
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Delmarva PV/storage requires approved ordinary renewable service; standalone storage is outside scope.")
        _reference(a, "der_eligibility_source")
        if max(equipment.get("pv_dc_kw", 0.), equipment.get("pv_ac_kw", 0.))+equipment.get("battery_kw", 0.) > 25.+1e-8:
            raise ValueError("Delmarva implementation limits combined PV/storage nameplate to25kW; size does not establish approved interconnection.")


def validate_state(a, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("Delmarva ordinary non-export billing has no modeled opening credit or demand-history state.")


def charge_lines(index, imports, exports, a, *, math, state=None):
    validate_state(a, index, state=state)
    idx = pd.DatetimeIndex(index); cycle = cycle_review(a, idx)
    if math.convex:
        math.constraints.append(exports == 0)
    elif np.max(exports) > 1e-5:
        raise ValueError("Delmarva export settlement is unimplemented; exports must be zero.")
    r = rates_on(a["billing_month"], a["tariff"]); energy = math.hours*math.sum(imports)
    metrics = {**cycle, "rates":r, "measured_demand_charge":False, "intraday_time_of_use_pricing":False}
    if a["tariff"] == "R":
        if math.convex: math.constraints.append(energy <= 7500.)
        elif energy > 7500.+1e-7: raise ValueError("Delmarva R study requires monthly imports at most7500kWh; no larger-account MES-cap treatment is inferred.")
    else:
        peak = math.demand(imports, idx, minutes=15)
        if math.convex: math.constraints.extend([peak <= 19.99999, energy <= 3500.])
        elif peak >= 20. or energy > 3500.+1e-7: raise ValueError("Delmarva estimated-demand SGS-S study requires15-minute import peak below20kW and monthly imports at most3500kWh.")
        metrics.update(actual_15_minute_peak_kw=peak, estimated_billing_demand_kw=energy/175.,
            demand_method=a["demand_method"], estimated_demand_source=a["estimated_demand_source"],
            transmission_demand_kw=0., metered_demand_rounding_applied=False,
            usc_source=a["usc_assignment_"+str(idx[0].year)+"_source"])
    lines={"distribution_customer":r["customer"]}
    lines.update({name:energy*value for name,value in r["energy"].items()});lines.update(r["monthly"])
    if a["tariff"] == "SGS-S":
        lines["distribution_estimated_demand"] = (energy/175.)*r["distribution_demand_rate"]
        lines["transmission_demand"] = 0.
    metrics.update(capacity_transmission_treatment="SOS generation/admin/PCA and filed transmission charged once; GRT embedded in applicable rates. No extra wholesale LMP/PLC/NSPL or Pepco-style gross-up.",
        component_application_clocks="Recovered matching complete calendar service/billing months only; intramonth allocation unverified",
        tax_jurisdiction=a["tax_jurisdiction"], usc_band=a["usc_band"], additional_gross_receipts_tax_applied=False,
        state_sales_tax_status="residential_filed_schedule_exempt" if a["tariff"] == "R" else "excluded_unresolved_compound_base_and_statutory_brackets",
        relief_policy=a["relief_policy"], rate_effective_basis="Verified monthly intersections; no shifted/partial/crossing allocations")
    return dict(lines=lines, metrics=metrics, next_state={}, is_complete_bill=False,
        excluded_components=excluded_components(a["tariff"]), rate_evidence_status="verified", assumption_model=None,
        rate_assumptions=[], rate_sources=SOURCES,
        warnings=["Delmarva Maryland hypothetical ordinary non-export account; schedule, SOS, USC, demand method, locality and interconnection require independent confirmation.",
            "Complete matching calendar service/billing months only; no missing-rate substitution, export credits or special settlement.",
            "Delmarva verified-charge subtotal excludes R residential RGGI/legislative credits or SGS-S state sales-tax calculation. Excluded amounts are not zero or exemptions; no complete bill or complete-bill optimum is claimed.",
            "SGS-S E.3 estimated demand must remain utility-approved across study scenarios; metered/assessed/off-peak accounts are outside scope.",
            "Historical perfect foresight per cycle; representative OpenDSS replay does not validate a surveyed customer installation."])
