"""Pepco Maryland R / GS Type I SOS recurring verified-charge subtotals.

Filed monthly retail components feed both numerical bills and dispatch. Utility,
supplier, tax locality and PJM metadata remain independent account facts.
"""
import numpy as np
import pandas as pd

from .pepco_md_rates import COVERAGE, PLANS, SOURCES, rates_on

UTILITY = "pepco_maryland"
TIMEZONE = "America/New_York"
RELIEF_EXCLUSION = "account_specific_legislative_relief_refund"
SALES_TAX_EXCLUSION = "maryland_state_sales_tax"
RRC_EXCLUSION = "residential_rggi_rate_credit"


def excluded_components(plan):
    return [RELIEF_EXCLUSION, RRC_EXCLUSION] if plan == "R" else [SALES_TAX_EXCLUSION]


def account_fields(plan="R"):
    return [dict(name=k, type="boolean", default=False, required=True, label=v)
        for k, v in (
            ("eligibility_confirmed", "Pepco Maryland delivery, selected R/GS schedule and Pepco Maryland residential/Type I SOS independently confirmed"),
            ("ordinary_service_confirmed", "Ordinary single-meter secondary service; no competitive supplier, assistance, opt-out, special facilities, standby or discretionary adjustments"),
            ("full_monthly_charges_confirmed", "Complete hypothetical calendar cycle and matching billing month; no partial/shifted allocation"),
            ("local_charges_confirmed", "Ordinary account in unincorporated Montgomery County; tax status independently confirmed"))] + [
        dict(name="cycle_source", type="text", required=True, label="Meter-cycle evidence or explicit hypothetical calendar-cycle assumption; omit personal information"),
        dict(name="tax_source", type="text", required=True, label="Tax locality and ordinary residential/business status evidence or explicit hypothetical assumption"),
        dict(name="type_i_confirmed", type="boolean", default=False, label="GS: existing utility-assigned Type I SOS eligibility, including prior usage/demand, independently confirmed"),
        dict(name="usc_band", type="choice", choices=["residential", "175_to_1299"], label="Utility-assigned universal-service band; fixed across study scenarios"),
        dict(name="usc_assignment_2025_source", type="text", label="GS: assigned USC band throughout2025, before/after the first-quarter update; evidence or explicit hypothetical assumption"),
        dict(name="usc_assignment_2026_source", type="text", label="GS: assigned USC band throughout2026, before/after the first-quarter update; evidence or explicit hypothetical assumption"),
        dict(name="subtotal_scope_confirmed", type="boolean", default=False, required=True, label="Recurring verified-charge subtotal only: R excludes RGGI/legislative credits; GS excludes unresolved state sales-tax calculation"),
        dict(name="relief_policy", type="choice", choices=["exclude_account_specific_refunds"], label="Residential scope: recurring tariff subtotal excludes historical-account legislative relief refunds"),
        dict(name="der_ordinary_service_confirmed", type="boolean", default=False, label="PV/storage: approved ordinary parallel service without standby/special charges; non-export operation"),
        dict(name="der_eligibility_source", type="text", label="Approved interconnection/ordinary-service evidence or explicit hypothetical agreement"),
        dict(name="rate_evidence_mode", type="choice", choices=["verified"], default="verified", label="Verified Pepco Maryland monthly components only; no provisional fallback"),
    ]


def defaults(plan="R"):
    if plan not in PLANS:
        raise ValueError("Select Pepco Maryland R or GS Type I Standard Offer Service.")
    return dict(tariff=plan, supply="sos", export_mode="none",
        eligibility_confirmed=False, ordinary_service_confirmed=False,
        full_monthly_charges_confirmed=False, local_charges_confirmed=False,
        tax_jurisdiction="montgomery_unincorporated", tax_exempt=False, tax_source="",
        cycle_source="", cycle_kind="regular", billing_month="2026-09-01", bill_date="2026-09-30",
        type_i_confirmed=False, usc_band="residential" if plan == "R" else "175_to_1299", usc_assignment_2025_source="", usc_assignment_2026_source="",
        relief_policy="exclude_account_specific_refunds",
        subtotal_scope_confirmed=False,
        rate_evidence_mode="verified", provisional_assumptions_accepted=False,
        der_ordinary_service_confirmed=False, der_eligibility_source="",
        voltage="secondary", phase="single", voltage_v=240., power_factor=1.,
        meter_count=1, service_line_count=1, opening_credit_usd=0., demand_interval_minutes=30)


def hypothetical_defaults(plan="R", year=2025):
    a = defaults(plan)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True,
        full_monthly_charges_confirmed=True, local_charges_confirmed=True,
        type_i_confirmed=plan == "GS", hypothetical_account=True, subtotal_scope_confirmed=True,
        tax_source="Explicit hypothetical ordinary unincorporated Montgomery County account; ordinary residential exemption or commercial taxes, no special exemptions",
        usc_assignment_2025_source="Explicit hypothetical utility-assigned $175–$1299 annual-delivery bracket throughout2025, before and after the first-quarter update" if plan == "GS" else "Residential universal-service charge",
        usc_assignment_2026_source="Explicit hypothetical utility-assigned $175–$1299 annual-delivery bracket throughout2026, before and after the first-quarter update" if plan == "GS" else "Residential universal-service charge",
        cycle_source="Explicit hypothetical complete calendar meter cycle and matching billing month; not an actual customer statement",
        der_ordinary_service_confirmed=True,
        der_eligibility_source="Explicit hypothetical Pepco Maryland-approved ordinary renewable PV/storage service without standby/special charges; zero-export dispatch")
    return a


def catalog():
    return [dict(id=p, label="Pepco Maryland " + ("Residential R SOS" if p == "R" else "Small General Service GS · Type I SOS"),
        status="supported", customer_class="residential" if p == "R" else "commercial",
        coverage=[dict(start=s, end=e, is_complete_bill=False,
            scope="Recurring verified-charge subtotal; RGGI and legislative credits excluded" if p == "R" else "Recurring verified-charge subtotal; state sales-tax calculation excluded",
            excluded_components=excluded_components(p)) for s, e in COVERAGE], voltage="secondary",
        interval_minutes=[15], solar_modes=["non_export"], supply_arrangements=["sos"],
        equipment_modes=["grid_only", "pv_only", "pv_battery"], representative_peak_kw=3.,
        account_fields=account_fields(p), sources=SOURCES,
        eligibility="Independently confirmed ordinary Pepco Maryland R residential or secondary GS Type I SOS, one meter, complete calendar cycles and unincorporated Montgomery County tax scope.",
        limitations=[
            "Complete consecutive 15-minute calendar cycles with the same designated billing month only; partial/shifted cycles and unverified dates reject.",
            "GS requires existing utility-assigned Type I eligibility. Studies retain 30-minute import demand below25kW and monthly imports at most6000kWh November–May or7500kWh June–October; this conservative domain does not infer historical classification.",
            "GS universal-service band $175–$1299 annual utility delivery charges is an explicit assigned account fact retained across scenarios; the optimizer does not recompute it from modeled annual bills.",
            "Both plans report verified-charge subtotals. R excludes unverified RGGI/legislative fixed credits; GS excludes unresolved state sales-tax base/bracket calculation. No complete amount due or complete-bill optimum is claimed.",
            "R study imports are bounded to7500kWh per month; the MES1000-dollar monthly cap is inactive. This is a study-domain restriction, not a residential tariff eligibility threshold.",
            "Generation/admin, transmission and PCA are separate. Pepco transmission excludes separately calculated2.0408%GRT; no extra PJM LMP/PLC/NSPL charge. County MCS is not the underlying county tax rate.",
            "Distribution uses billing months June–October for summer, November–May for winter. Same-clock base/RDM are reported net; separate August2026 transition proration is not claimed.",
            "PV/storage requires approved ordinary service and zero exports; no NEM bank, export credit, standalone storage or standby settlement.",
            "Other localities, Type II/hourly SOS, R-TM/other time-of-use schedules, competitive supply, assistance, opt-out and special charges remain unsupported."])
        for p in PLANS]


def cycle_review(a, index):
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2 or str(idx.tz) != TIMEZONE:
        raise ValueError("Pepco Maryland requires America/New_York timestamps and complete15-minute intervals.")
    step = pd.Timedelta(minutes=15)
    if not np.all(idx[1:]-idx[:-1] == step):
        raise ValueError("Pepco Maryland requires consecutive15-minute intervals; missing/duplicate/hourly data reject.")
    stop = idx[-1]+step
    if (idx[0] != idx[0].normalize() or idx[0].day != 1 or stop != idx[0]+pd.offsets.MonthBegin()
            or a.get("cycle_kind") != "regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Pepco Maryland first scope requires a complete calendar meter cycle; partial/shifted allocation is unverified.")
    if a.get("billing_month") != str(idx[0].date()):
        raise ValueError("Pepco Maryland designated billing month must match the complete calendar service month.")
    # This bounded interface avoids assuming how bill-month factors allocate to
    # service dates in a shifted cycle. The bill date remains a separate fact.
    if a.get("bill_date") != str(idx[-1].date()):
        raise ValueError("Pepco Maryland first scope requires a bill date on the final calendar service date.")
    rates_on(a["billing_month"], a["tariff"])
    return dict(service_start=str(idx[0].date()), service_end=str(idx[-1].date()),
        cycle_days=(stop.date()-idx[0].date()).days,
        elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)),
        billing_month=a["billing_month"], bill_date=a["bill_date"],
        monthly_charge_factor=1., partial_period_proration_applied=False)


def evidence(index, account):
    cycle_review(account, index)
    return dict(rate_evidence_status="verified", assumption_model=None,
        rate_assumptions=[], objective_scope="verified_charges_subtotal")


def _reference(a, key):
    if not isinstance(a.get(key), str) or not 1 <= len(a[key].strip()) <= 500:
        raise ValueError("Document Pepco Maryland cycle, tax, classification and interconnection assumptions without personal identifiers.")


def validate_account(a, index, equipment=None):
    if (not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "sos"
            or a.get("export_mode") != "none"):
        raise ValueError("Select ordinary Pepco Maryland R/GS residential/Type I SOS and zero export.")
    if a.get("rate_evidence_mode", "verified") != "verified" or a.get("provisional_assumptions_accepted", False) is not False:
        raise ValueError("Pepco Maryland has no provisional-rate mode or missing-price fallback.")
    if a.get("relief_policy") != "exclude_account_specific_refunds":
        raise ValueError("Pepco Maryland recurring tariff scope explicitly excludes account-specific legislative relief; no historical refund amount or posting cycle is inferred.")
    if a.get("subtotal_scope_confirmed") is not True:
        raise ValueError("Confirm Pepco's verified-charge subtotal scope and the selected plan's excluded credits or state sales-tax calculation.")
    if any(a.get(k) is not True for k in ("eligibility_confirmed", "ordinary_service_confirmed", "local_charges_confirmed")):
        raise ValueError("Confirm Pepco Maryland delivery/schedule/SOS eligibility, ordinary service and tax jurisdiction independently of location.")
    for key in ("cycle_source", "tax_source"):
        _reference(a, key)
    if (a.get("tax_jurisdiction") != "montgomery_unincorporated" or a.get("tax_exempt") is not False
            or (a.get("voltage"), a.get("phase"), a.get("voltage_v"), a.get("power_factor")) != ("secondary", "single", 240., 1.)
            or a.get("meter_count") != 1 or a.get("service_line_count") != 1
            or a.get("opening_credit_usd") != 0. or a.get("demand_interval_minutes") != 30):
        raise ValueError("Pepco Maryland first scope requires ordinary unincorporated Montgomery County taxes, one120/240V single-phase meter/service, unity PF,30-minute eligibility demand and no opening credits.")
    if a["tariff"] == "GS":
        if a.get("type_i_confirmed") is not True or a.get("usc_band") != "175_to_1299":
            raise ValueError("Confirm existing Pepco Maryland GS Type I SOS classification and the utility-assigned universal-service annual delivery band $175–$1299.")
        year = str(pd.DatetimeIndex(index)[0].year)
        _reference(a, "usc_assignment_"+year+"_source")
    elif a.get("usc_band") != "residential" or a.get("type_i_confirmed") is not False:
        raise ValueError("Pepco Maryland R requires residential SOS and the residential universal-service charge.")
    cycle_review(a, index)
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Pepco Maryland PV/storage requires approved ordinary renewable service; standalone storage is outside this scope.")
        _reference(a, "der_eligibility_source")
        if max(equipment.get("pv_dc_kw", 0.), equipment.get("pv_ac_kw", 0.))+equipment.get("battery_kw", 0.) > 25.+1e-8:
            raise ValueError("Pepco Maryland bounded ordinary renewable study limits combined PV/battery nameplate to25kW; this does not establish interconnection eligibility.")


def validate_state(a, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("Pepco Maryland ordinary non-export billing has no modeled opening credit or demand-history state.")


def charge_lines(index, imports, exports, a, *, math, state=None):
    validate_state(a, index, state=state)
    idx = pd.DatetimeIndex(index)
    cycle = cycle_review(a, idx)
    if math.convex:
        math.constraints.append(exports == 0)
    elif np.max(exports) > 1e-5:
        raise ValueError("Pepco Maryland export settlement is not implemented; exports must be zero.")
    r = rates_on(a["billing_month"], a["tariff"])
    energy = math.hours*math.sum(imports)
    metrics = {**cycle, "rates":r, "measured_demand_charge":False, "intraday_time_of_use_pricing":False}
    if a["tariff"] == "R":
        if math.convex:
            math.constraints.append(energy <= 7500.)
        elif energy > 7500.+1e-7:
            raise ValueError("Pepco R first study domain requires monthly imports at most7500kWh; no larger-account MES-cap interpretation is inferred.")
    if a["tariff"] == "GS":
        peak = math.demand(imports, idx, minutes=30)
        energy_limit = 7500. if 6 <= idx[0].month <= 10 else 6000.
        if math.convex:
            math.constraints.extend([peak <= 24.99999, energy <= energy_limit])
        elif peak >= 25. or energy > energy_limit+1e-7:
            raise ValueError("Pepco Maryland GS bounded Type I study requires30-minute import demand below25kW and monthly imports within6000/7500kWh; prior classification remains independently confirmed.")
        metrics.update(measured_demand_kw=peak, type_i_monthly_energy_limit_kwh=energy_limit,
            type_i_classification_basis="Existing utility-assigned membership plus conservative study import limits; no automatic reassignment or inferred PJM tag",
            usc_band=a["usc_band"], usc_source=a["usc_assignment_"+str(idx[0].year)+"_source"])
    return _bill(r, energy, a, metrics, math)


def _bill(r, energy, a, metrics, math):
    """Same numeric/convex component bases; unresolved state tax stays excluded."""
    lines = {"distribution_customer_net_rdm":r["customer_net_rdm"]}
    lines.update({name:energy*value for name, value in r["energy"].items()})
    lines.update(r["monthly"])
    delivery_base = lines["distribution_customer_net_rdm"]+lines["universal_service"]+sum(lines[k] for k in r["grt_delivery_components"])
    lines["distribution_gross_receipts_tax"] = delivery_base*r["gross_receipts_rate"]
    lines["transmission_gross_receipts_tax"] = lines["transmission_service"]*r["gross_receipts_rate"]
    metrics.update(capacity_transmission_treatment="SOS includes capacity/losses/ancillary service. Filed energy/admin, PCA, transmission and separately calculated transmission GRT charged once; no PJM LMP/PLC/NSPL charge.",
        component_application_clocks="Verified service-date components and designated billing-month factors; matching complete calendar cycles only",
        tax_jurisdiction=a["tax_jurisdiction"], usc_band=a["usc_band"],
        gross_receipts_rate=r["gross_receipts_rate"], grt_delivery_base_usd=delivery_base,
        grt_delivery_components=r["grt_delivery_components"],
        grt_excludes=["administrative_delivery_credit", "montgomery_county_surcharge", "generation_energy", "supply_administration", "procurement_cost_adjustment"],
        state_sales_tax_status="residential_filed_schedule_exempt" if a["tariff"] == "R" else "excluded_unresolved_compound_base_and_statutory_brackets",
        distribution_netting=r["distribution_netting"],
        relief_policy=a["relief_policy"],
        rate_effective_basis="Verified monthly tariff intersections; no shifted-cycle or partial-period allocation")
    return dict(lines=lines, metrics=metrics, next_state={}, is_complete_bill=False,
        excluded_components=excluded_components(a["tariff"]),
        rate_evidence_status="verified", assumption_model=None, rate_assumptions=[], rate_sources=SOURCES,
        warnings=["Pepco Maryland hypothetical ordinary non-export account; tariff, SOS type, assigned universal-service band, tax locality and interconnection require independent confirmation.",
            "Complete matching calendar service/billing months only; no unverified allocation, export credits or special-service settlement.",
            "Pepco verified-charge subtotal excludes residential RGGI/legislative credits or GS state sales-tax calculation. Excluded amounts are not zero or exemptions; no complete bill or complete-bill optimum is claimed.",
            "Base/RDM distribution is reported net. Identical dated August2026 increases/offsets cancel; individual temporary component allocation is not independently benchmarked.",
            "Historical perfect foresight within each cycle; representative OpenDSS replay does not validate a surveyed customer installation."])
