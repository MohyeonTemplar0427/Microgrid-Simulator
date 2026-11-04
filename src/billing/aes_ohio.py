"""AES Ohio ordinary D17/D19 G10 Standard Offer, with bounded dated evidence.

The utility owns its calendar, history, low-load and tax expressions. Existing
regional billing/dispatch supply arithmetic and authoritative numeric replay.
PJM metadata, wholesale prices and optional carbon do not set retail charges.
"""
from copy import deepcopy

import numpy as np
import pandas as pd

from .aes_ohio_rates import COVERAGE, GAPS, SOURCES, rates_on

UTILITY = "aes_ohio"
TIMEZONE = "America/New_York"
PLANS = ("D17", "D19")
SEASONAL_MONTHS = (1, 2, 6, 7, 8, 12)
# A study exclusion, not an AES tariff prohibition. Official spreadsheets use
# intermediate cents absent from the filed raw expressions. Near the selector
# boundary the separate distribution allocation can change percentage riders.
LLF_BOUNDARY_USD = .02


def account_fields(plan_id="D17"):
    fields = [
        dict(name="eligibility_confirmed", type="boolean", required=True, default=False,
             label="AES Ohio ordinary D17 residential or metered D19 secondary account confirmed"),
        dict(name="ordinary_service_confirmed", type="boolean", required=True, default=False,
             label="One ordinary single-phase meter; no auxiliary/standby, special facilities, assistance, adjustments or special contract"),
        dict(name="sso_enrollment_confirmed", type="boolean", required=True, default=False,
             label="G10 Standard Offer throughout service; no shopping, aggregation or optional pricing"),
        dict(name="supply_source", type="text", required=True, label="SSO enrollment evidence or explicit hypothetical account"),
        dict(name="no_local_tax_confirmed", type="boolean", required=True, default=False,
             label="Ordinary D33 tax, no municipal/franchise adder, self-assessment or special exemption"),
        dict(name="tax_source", type="text", required=True, label="Tax/local-charge evidence or explicit hypothetical assumption"),
        dict(name="full_monthly_charges_confirmed", type="boolean", required=True, default=False,
             label="Complete matching calendar service/bill cycle; full monthly charges"),
        dict(name="cycle_source", type="text", required=True, label="Meter-cycle evidence or explicit hypothetical calendar"),
        dict(name="bill_date", type="date", required=True, label="Final-day bill-rendered date matching service month"),
        dict(name="d43_refund_resolved_confirmed", type="boolean", default=False,
             label="September2026 onward: Company D43 one-time refund already received before this study"),
        dict(name="d43_refund_received_date", type="date", label="Actual prior D43 credit date (August2026 or later, before first study cycle)"),
        dict(name="d43_refund_received_usd", type="number", label="Prior one-time D43 credit amount in USD"),
        dict(name="d43_refund_source", type="text", label="Prior D43 receipt evidence or explicit hypothetical receipt"),
        dict(name="der_ordinary_service_confirmed", type="boolean", default=False,
             label="Exact installed PV/storage approved for ordinary service, with no D10 auxiliary/standby capacity charges"),
        dict(name="der_activation_date", type="date", label="Final approval/PTO and required metering active by this date"),
        dict(name="der_eligibility_source", type="text", label="Exact PV/storage approval, ordinary-rate continuation and PTO evidence or hypothetical assumption"),
    ]
    if plan_id == "D19":
        fields += [
            dict(name="no_demand_elections_confirmed", type="boolean", required=True, default=False,
                 label="No off-peak election now/prior eleven months, NSPL option, legacy TCRR opt-out, 85% connected-load or agreement minimum"),
            dict(name="history_confirmed", type="boolean", required=True, default=False,
                 label="Eleven actual all-hours 30-minute monthly maxima independently confirmed; no ratchet-inflated peaks"),
            dict(name="history_source", type="text", required=True, label="Company demand-history evidence or explicit hypothetical history"),
            dict(name="history", type="object", required=True,
                 label="Eleven consecutive prior months, oldest first: month YYYY-MM-01 and actual maximum_kw"),
        ]
    return fields


def defaults(plan_id="D17"):
    if plan_id not in PLANS:
        raise ValueError("Choose AES Ohio D17 Residential or metered D19 Secondary SSO.")
    return dict(tariff=plan_id, supply="sso", export_mode="none", eligibility_confirmed=False,
        ordinary_service_confirmed=False, sso_enrollment_confirmed=False, supply_source="",
        no_local_tax_confirmed=False, tax_source="", full_monthly_charges_confirmed=False,
        cycle_source="", cycle_kind="regular", billing_month="2026-11-01", bill_date="2026-11-30",
        rate_evidence_mode="verified", provisional_assumptions_accepted=False,
        voltage="secondary", phase="single", voltage_v=240., meter_count=1,
        opening_credit_usd=0., tax_jurisdiction="oh_state_only", self_assessor=False,
        offpeak_election=False, nspl_opt_in=False, tcrr_opt_out=False,
        connected_load_alternative=False, agreement_minimum_kw=0.,
        demand_interval_minutes=30, no_demand_elections_confirmed=False,
        history_confirmed=False, history_source="", history=[],
        d43_refund_resolved_confirmed=False, d43_refund_received_date="", d43_refund_received_usd=0., d43_refund_source="",
        der_ordinary_service_confirmed=False, der_activation_date="", der_eligibility_source="")


def hypothetical_defaults(plan_id="D17", *, day="2026-11-01"):
    a = defaults(plan_id)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True, sso_enrollment_confirmed=True,
        supply_source="Explicit hypothetical Company-confirmed ordinary G10 SSO account, no supplier change",
        no_local_tax_confirmed=True, tax_source="Explicit hypothetical ordinary D33 non-self-assessor account without municipal/franchise charges",
        full_monthly_charges_confirmed=True, cycle_source="Explicit hypothetical full calendar meter cycle, not a customer bill",
        billing_month=day, bill_date=str((pd.Timestamp(day)+pd.offsets.MonthEnd()).date()),
        der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
        der_eligibility_source="Hypothetical Company approval of exact PV and paired storage, required metering and final PTO already active; ordinary underlying service retained, no D10 auxiliary/standby or recurring special charges",
        hypothetical_account=True)
    if day >= "2026-09-01":
        a.update(d43_refund_resolved_confirmed=True, d43_refund_received_date="2026-08-31",
            d43_refund_received_usd=14.39 if plan_id == "D17" else 49.27,
            d43_refund_source="Explicit hypothetical Company D43 credit received once in August2026, before this study; not an actual customer receipt")
    if plan_id == "D19":
        a.update(no_demand_elections_confirmed=True, history_confirmed=True,
            history_source="Explicit hypothetical eleven actual all-hours 30-minute monthly maxima of40kW; no off-peak election/NSPL/special facilities/minimum agreement, not measured customer records",
            history=[dict(month=str(m.date()), maximum_kw=40.)
                     for m in pd.date_range(end=pd.Timestamp(day)-pd.offsets.MonthBegin(), periods=11, freq="MS")])
    return a


def catalog():
    return [dict(id=p, label="AES Ohio " + ("Residential D17" if p == "D17" else "Secondary D19 · single phase") + " (G10 SSO)",
        status="supported", customer_class="residential" if p == "D17" else "commercial",
        coverage=[dict(start=s, end=e) for s, e in COVERAGE], coverage_gaps=deepcopy(GAPS),
        voltage="secondary", supply_arrangements=["sso"], solar_modes=["non_export"],
        equipment_modes=["grid_only", "pv_only", "pv_battery"], representative_peak_kw=3. if p == "D17" else 20.,
        account_fields=account_fields(p), sources=SOURCES,
        eligibility="Company-confirmed ordinary single-phase secondary G10 SSO, one meter, complete calendar cycles and independently confirmed taxes/PTO. D19 requires actual eleven-month history without optional demand elections.",
        limitations=[
            "Only verified dated component intersections execute; November2025 mixed-cycle allocation, other source gaps and August2026 one-time refund state reject. No provisional-rate substitution.",
            "D19 highest30-minute actual peak and75% seasonal actual prior11-month ratchet; no invented first5 exemption, minimum kW or contract demand. Study peak<=100kW is narrower than the tariff.",
            "D19/T08 low-load alternative uses unrounded filed expressions and percentage riders on selected distribution. A$0.02 comparator boundary band with differing distribution allocations is outside this study scope; exact invoice/rounded-cash optimization is not claimed.",
            "D33 statutory measurement-day kWh tiers, no imported affiliate CAT gross-up; utility-calculator tax convention differs for non30-day cycles.",
            "Exact approved ordinary PV/paired storage, already active PTO, PV-only charging and zero exports/bank. Charging restriction is model scope, not asserted universal AES tariff law. No standalone storage, export settlement, measured-customer/site or annual-optimum claim."])
        for p in PLANS]


def _reference(a, key):
    if not isinstance(a.get(key), str) or not 1 <= len(a[key].strip()) <= 500:
        raise ValueError("Document AES Ohio " + key + " without personal identifiers.")


def _number(value, upper):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and np.isfinite(value) and 0. <= value <= upper


def _history(value):
    if not isinstance(value, list) or len(value) != 11:
        raise ValueError("AES D19 requires eleven consecutive actual demand-history months, never inferred missing zeros.")
    rows = []
    for row in value:
        if not isinstance(row, dict) or set(row) != {"month", "maximum_kw"} or not _number(row["maximum_kw"], 100.):
            raise ValueError("AES D19 history needs month and finite actual30-minute maximum_kw within the100kW study envelope.")
        try:
            month = pd.Timestamp(row["month"])
            valid = month.tz is None and month.day == 1 and str(month.date()) == row["month"]
        except (ValueError, TypeError):
            valid = False
        if not valid or rows and month != pd.Timestamp(rows[-1]["month"])+pd.offsets.MonthBegin():
            raise ValueError("AES demand history must have exact consecutive first-of-month dates, oldest first.")
        rows.append(dict(row))
    return rows


def cycle_review(a, index):
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2 or str(idx.tz) != TIMEZONE or not np.all(idx[1:]-idx[:-1] == pd.Timedelta(minutes=15)):
        raise ValueError("AES Ohio requires complete consecutive Eastern-time15-minute data; missing/duplicate/hourly substitutes reject.")
    stop = idx[-1]+pd.Timedelta(minutes=15)
    if idx[0] != idx[0].normalize() or idx[0].day != 1 or stop != idx[0]+pd.offsets.MonthBegin() or a.get("cycle_kind") != "regular" or a.get("full_monthly_charges_confirmed") is not True:
        raise ValueError("AES Ohio initial scope requires complete calendar cycles; partial/shifted and mixed-rate allocations are unsupported.")
    if a.get("billing_month") != str(idx[0].date()) or a.get("bill_date") != str(idx[-1].date()):
        raise ValueError("AES billing month and final-day bill date must match service.")
    if a.get("rate_evidence_mode", "verified") != "verified" or a.get("provisional_assumptions_accepted", False) is not False:
        raise ValueError("AES Ohio has no provisional or inferred-rate mode.")
    first = rates_on(idx[0].date(), a["tariff"], bill_date=a["bill_date"])
    if first != rates_on(idx[-1].date(), a["tariff"], bill_date=a["bill_date"]):
        raise ValueError("AES component transition within service lacks a verified allocation.")
    days = (stop.date()-idx[0].date()).days
    return dict(service_start=str(idx[0].date()), service_end=str(idx[-1].date()),
        billing_month=a["billing_month"], bill_date=a["bill_date"], cycle_days=days,
        elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)), monthly_charge_factor=1.,
        partial_period_proration_applied=False,
        excise_tax_thresholds_kwh=[2000., 15000.] if days == 30 else [67.*days, 500.*days])


def validate_account(a, index, equipment=None):
    if not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "sso" or a.get("export_mode") != "none":
        raise ValueError("Select AES D17/D19 ordinary G10 SSO, zero export and no credit bank.")
    for key in ("eligibility_confirmed", "ordinary_service_confirmed", "sso_enrollment_confirmed", "no_local_tax_confirmed", "full_monthly_charges_confirmed"):
        if a.get(key) is not True:
            raise ValueError("Confirm ordinary AES eligibility, G10 SSO, absent special/local charges and full calendar cycle independently.")
    for key in ("supply_source", "tax_source", "cycle_source"):
        _reference(a, key)
    expected = dict(voltage="secondary", phase="single", voltage_v=240., meter_count=1,
        opening_credit_usd=0., tax_jurisdiction="oh_state_only", self_assessor=False, demand_interval_minutes=30,
        offpeak_election=False, nspl_opt_in=False, tcrr_opt_out=False,
        connected_load_alternative=False, agreement_minimum_kw=0.)
    if any(a.get(k) != v or isinstance(a.get(k), bool) and not isinstance(v, bool) or isinstance(v, bool) and a.get(k) is not v for k, v in expected.items()):
        raise ValueError("AES scope requires one120/240V single-phase secondary meter, ordinary D33 tax, no local tax/self-assessment/bank and30-minute demand.")
    cycle_review(a, index)
    if a["billing_month"] >= "2026-09-01":
        if a.get("d43_refund_resolved_confirmed") is not True or not _number(a.get("d43_refund_received_usd"), 100.) or a["d43_refund_received_usd"] != (14.39 if a["tariff"] == "D17" else 49.27):
            raise ValueError("September2026 onward requires the exact one-time D43 refund already received; no credit or ending date is inferred.")
        _reference(a, "d43_refund_source")
        try:
            receipt = pd.Timestamp(a["d43_refund_received_date"])
            valid = receipt.tz is None and str(receipt.date()) == a["d43_refund_received_date"] and "2026-08-01" <= a["d43_refund_received_date"] < a["billing_month"]
        except (ValueError, TypeError, KeyError):
            valid = False
        if not valid:
            raise ValueError("D43 one-time receipt must be independently documented after its effective date and before this cycle.")
    elif a.get("d43_refund_resolved_confirmed") is not False or a.get("d43_refund_received_date") != "" or a.get("d43_refund_received_usd") != 0. or isinstance(a.get("d43_refund_received_usd"), bool) or a.get("d43_refund_source") != "":
        raise ValueError("Before August2026, D43 had not become effective; no future refund receipt is allowed.")
    if a["tariff"] == "D19":
        if a.get("no_demand_elections_confirmed") is not True or a.get("history_confirmed") is not True:
            raise ValueError("Confirm AES D19 actual history, no off-peak/NSPL election, connected-load rule or agreement minimum.")
        _reference(a, "history_source")
        history = _history(a.get("history"))
        if history[-1]["month"] >= a["billing_month"]:
            raise ValueError("AES demand history must precede service, without future demand determinants.")
    elif a.get("history") != [] or a.get("history_confirmed") is not False or a.get("no_demand_elections_confirmed") is not False or a.get("history_source") != "":
        raise ValueError("AES D17 residential service has no modeled commercial demand history or election.")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Already-approved exact AES ordinary-service PV and paired storage are required; standalone storage is unsupported.")
        _reference(a, "der_eligibility_source")
        try:
            activation = pd.Timestamp(a["der_activation_date"])
            valid = activation.tz is None and str(activation.date()) == a["der_activation_date"] and activation.date() <= pd.DatetimeIndex(index)[0].date()
        except (ValueError, TypeError, KeyError):
            valid = False
        if not valid:
            raise ValueError("AES exact-configuration approval, PTO and required metering must be active before service.")
        if equipment.get("battery") and (not equipment.get("renewable_only_charging") or not equipment.get("no_battery_export")):
            raise ValueError("AES initial model restricts paired storage to PV-only charging and zero exports.")
        if max(equipment.get("pv_dc_kw", 0.), equipment.get("pv_ac_kw", 0.))+equipment.get("battery_kw", 0.) > 25.+1e-8:
            raise ValueError("Combined AES study output is bounded at25kW; Company interconnection eligibility is separately confirmed.")


def validate_state(a, index, state=None, equipment=None):
    if a["tariff"] == "D17":
        if state not in (None, {}):
            raise ValueError("AES D17 has no carried demand or export-credit ledger.")
        return
    if state is not None and (not isinstance(state, dict) or set(state) != {"history", "next_billing_month"} or state["next_billing_month"] != a["billing_month"]):
        raise ValueError("AES D19 carried state must continue adjacent cycles without reset, replay or skipped history.")
    history = _history(a["history"] if state is None else state["history"])
    previous = str((pd.Timestamp(a["billing_month"])-pd.offsets.MonthBegin()).date())
    if history[-1]["month"] != previous:
        raise ValueError("AES D19 actual history must end immediately before the current cycle.")


def evidence(index, account):
    cycle_review(account, index)
    return dict(rate_evidence_status="verified", assumption_model=None, rate_assumptions=[], objective_scope="complete_utility_bill")


def charge_lines(index, imports, exports, a, *, math, state=None):
    validate_state(a, index, state)
    cycle = cycle_review(a, index)
    r = rates_on(cycle["service_start"], a["tariff"], bill_date=a["bill_date"])
    res = a["tariff"] == "D17"
    energy = math.hours*math.sum(imports)
    if math.convex:
        math.constraints.extend([exports == 0, energy <= 833000., imports <= (25. if res else 100.)])
    elif np.max(exports) > 1e-5 or energy > 833000.+1e-7 or np.max(imports) > (25. if res else 100.)+1e-7:
        raise ValueError("AES initial model requires zero exports and D17 25kW/D19 100kW,<=833000kWh study bounds.")
    peak = math.demand(imports, index, minutes=30)
    history = [] if res else deepcopy(a["history"] if state is None else state["history"])
    ratchet = 0. if res else .75*max((row["maximum_kw"] for row in history if pd.Timestamp(row["month"]).month in SEASONAL_MONTHS), default=0.)
    demand = 0. if res else math.maximum(peak, ratchet)
    customer = r["customer"]
    normal_distribution = energy*r["distribution_energy"] if res else demand*r["distribution_demand"]
    normal_transmission_energy = energy*r["transmission_energy"]
    normal_transmission_demand = 0. if res else demand*r["transmission_demand"]
    llf_selected = False
    comparator = None
    if res:
        distribution_energy, distribution_demand = normal_distribution, 0.
        transmission_energy, transmission_demand = normal_transmission_energy, 0.
    else:
        normal = normal_distribution+normal_transmission_energy+normal_transmission_demand
        capped = energy*r["low_load_combined"]
        comparator = normal-capped
        if not math.convex:
            if abs(comparator) <= LLF_BOUNDARY_USD and abs(normal_distribution-energy*r["low_load_distribution"]) > 1e-7:
                raise ValueError("AES low-load comparator is inside the unsupported$0.02 boundary band with differing distribution allocations; no invoice-rounding branch is invented.")
            llf_selected = bool(normal > capped)
        # Both halves use one shared bounded selector. The symbolic graph is an
        # outer model at ties; authoritative numeric replay rejects the bounded
        # ambiguous domain before any dispatch/proof can be accepted.
        distribution_energy = math.choose_leq(normal, capped, 0., energy*r["low_load_distribution"])
        distribution_demand = math.choose_leq(normal, capped, normal_distribution, 0.)
        transmission_energy = math.choose_leq(normal, capped, normal_transmission_energy, energy*r["low_load_transmission"])
        transmission_demand = math.choose_leq(normal, capped, normal_transmission_demand, 0.)
    base = customer+distribution_energy+distribution_demand
    lines = dict(distribution_customer=customer, distribution_energy=distribution_energy,
        distribution_demand=distribution_demand, transmission_energy=transmission_energy,
        transmission_demand=transmission_demand, supply_energy=energy*r["supply_energy"],
        infrastructure_investment=base*r["infrastructure_percent"]/100.,
        distribution_investment=base*r["distribution_investment_percent"]/100.,
        storm_recovery=r["storm_fixed"],
        regulatory_compliance=base*r["regulatory_percent"]/100.+r["regulatory_fixed"],
        proactive_reliability=r["proactive_fixed"], pipp=energy*r["pipp_energy"],
        solar_generation=r["solar_fixed"]+energy*r["solar_energy"],
        legacy_generation=r["legacy_fixed"]+energy*r["legacy_energy"],
        economic_development=energy*r["economic_energy"], customer_programs=energy*r["customer_programs_energy"],
        energy_efficiency=energy*r["efficiency_energy"], tax_savings=base*r["tax_savings_percent"]/100.,
        customer_refund=0.,
        excise_tax=math.tiered(energy, cycle["excise_tax_thresholds_kwh"], [.00465, .00419, .00363]),
        sales_tax=0., minimum_adjustment=math.positive(customer-base))
    next_state = {} if res else dict(history=(history+[dict(month=a["billing_month"], maximum_kw=peak)])[-11:],
                                    next_billing_month=str((pd.Timestamp(a["billing_month"])+pd.offsets.MonthBegin()).date()))
    return dict(lines=lines, metrics={**cycle, "rates":r, "raw_import_kwh":energy,
        "actual_30_minute_peak_kw":peak, "billing_demand_kw":demand, "ratchet_floor_kw":ratchet,
        "demand_history_used":history, "demand_history_ratchet_applied":not res,
        "low_load_factor_applied":llf_selected if not math.convex else "symbolic_shared_comparator",
        "low_load_comparator_usd":comparator, "low_load_boundary_exclusion_usd":LLF_BOUNDARY_USD,
        "base_distribution_usd":base, "monthly_minimum_usd":customer,
        "quantity_basis":"raw_interval_energy_no_unsourced_meter_rounding", "rounded_cash_optimum_claimed":False,
        "state_tax_cat_gross_up_applied":False, "additional_tax_percentage_applied":False,
        "d43_refund_status":"confirmed_received_once_before_cycle" if a["billing_month"] >= "2026-09-01" else "not_yet_effective",
        "d43_refund_received_date":a["d43_refund_received_date"], "d43_refund_received_usd":a["d43_refund_received_usd"],
        "source_versions":r["source_versions"], "supply_source_grade":r["supply_source_grade"]},
        next_state=next_state, is_complete_bill=True, excluded_components=[], rate_evidence_status="verified",
        assumption_model=None, rate_assumptions=[], rate_sources=SOURCES,
        warnings=["AES ordinary single-phase D17/D19 G10 SSO, complete supported calendar cycles; provider, supplier, jurisdiction, PJM/DAY and pricing/carbon signals remain separate.",
            "D19 uses actual30-minute demand and75% qualifying seasonal peaks from preceding11months; no off-peak/NSPL election, first5 exemption, invented minimum kW or agreement minimum. History evolves independently by scenario.",
            "D19/T08 low-load and percentage bases use unrounded filed arithmetic; comparator boundary band rejects. Official calculator interim rounding and non30-day tax conventions differ; no exact printed-invoice or rounded-cash optimum claim.",
            "D33 incorporates statutory local-calendar measurement-day tiers without an affiliate CAT gross-up. One-time August2026 refund state and other tariff gaps are blocked.",
            "Company-approved exact ordinary PV/paired storage and active PTO are independent account facts. PV-only charging/non-export/25kW combined output are conservative study restrictions; no standalone storage or export/NEM settlement."]+
            (["This cycle's G10 pricing is verified by preserved dated official calculators and cached adopted text; its originalPDF gap remains visible in supply_source_grade."] if r["supply_source_grade"] != "official_adopted_tariff_original" else []))
