"""BGE Maryland ordinary R / G Type I SOS, complete calendar cycles only.

Filed monthly retail components feed both numerical bills and dispatch. Utility,
supplier, tax locality and PJM metadata remain independent account facts.
"""
import numpy as np
import pandas as pd

from .bge_md_rates import COVERAGE, PLANS, SOURCES, rates_on

UTILITY = "bge_maryland"
TIMEZONE = "America/New_York"
RELIEF_EXCLUSION = "account_specific_legislative_relief_refund"


def account_fields(plan="R"):
    return [dict(name=k, type="boolean", default=False, required=True, label=v)
        for k, v in (
            ("eligibility_confirmed", "BGE Maryland delivery, selected R/G schedule and BGE residential/Type I SOS independently confirmed"),
            ("ordinary_service_confirmed", "Ordinary single-meter secondary service; no competitive supplier, assistance, opt-out, special facilities, standby or discretionary adjustments"),
            ("full_monthly_charges_confirmed", "Complete hypothetical calendar cycle and matching billing month; no partial/shifted allocation"),
            ("local_charges_confirmed", "Ordinary account in unincorporated Anne Arundel County, outside Annapolis and Highland Beach; tax status independently confirmed"))] + [
        dict(name="cycle_source", type="text", required=True, label="Meter-cycle evidence or explicit hypothetical calendar-cycle assumption; omit personal information"),
        dict(name="tax_source", type="text", required=True, label="Tax locality and ordinary residential/business status evidence or explicit hypothetical assumption"),
        dict(name="type_i_confirmed", type="boolean", default=False, label="G: existing utility-assigned Type I SOS eligibility, including prior usage/demand, independently confirmed"),
        dict(name="usc_band", type="choice", choices=["residential", "175_to_1299"], label="Utility-assigned universal-service band; fixed across study scenarios"),
        dict(name="usc_source", type="text", label="G: utility-assigned annual delivery-charge bracket evidence or explicit hypothetical assumption"),
        dict(name="relief_policy", type="choice", choices=["exclude_account_specific_refunds"], label="Residential scope: recurring tariff subtotal excludes historical-account legislative relief refunds"),
        dict(name="der_ordinary_service_confirmed", type="boolean", default=False, label="PV/storage: approved ordinary parallel service without standby/special charges; non-export operation"),
        dict(name="der_eligibility_source", type="text", label="Approved interconnection/ordinary-service evidence or explicit hypothetical agreement"),
        dict(name="rate_evidence_mode", type="choice", choices=["verified"], default="verified", label="Verified BGE monthly components only; no provisional fallback"),
    ]


def defaults(plan="R"):
    if plan not in PLANS:
        raise ValueError("Select BGE R or G Type I Standard Offer Service.")
    return dict(tariff=plan, supply="sos", export_mode="none",
        eligibility_confirmed=False, ordinary_service_confirmed=False,
        full_monthly_charges_confirmed=False, local_charges_confirmed=False,
        tax_jurisdiction="anne_arundel_unincorporated", tax_exempt=False, tax_source="",
        cycle_source="", cycle_kind="regular", billing_month="2026-09-01", bill_date="2026-09-30",
        type_i_confirmed=False, usc_band="residential" if plan == "R" else "175_to_1299", usc_source="",
        relief_policy="exclude_account_specific_refunds",
        rate_evidence_mode="verified", provisional_assumptions_accepted=False,
        der_ordinary_service_confirmed=False, der_eligibility_source="",
        voltage="secondary", phase="single", voltage_v=240., power_factor=1.,
        meter_count=1, service_line_count=1, opening_credit_usd=0., demand_interval_minutes=30)


def hypothetical_defaults(plan="R", year=2025):
    a = defaults(plan)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True,
        full_monthly_charges_confirmed=True, local_charges_confirmed=True,
        type_i_confirmed=plan == "G", hypothetical_account=True,
        tax_source="Explicit hypothetical ordinary unincorporated Anne Arundel County account outside Annapolis/Highland Beach; ordinary residential exemption or commercial taxes, no special exemptions",
        usc_source="Explicit hypothetical utility-assigned annual delivery bracket $175–$1,299; assigned facts retained across all scenarios and billing years" if plan == "G" else "Residential universal-service charge",
        cycle_source="Explicit hypothetical complete calendar meter cycle and matching billing month; not an actual customer statement",
        der_ordinary_service_confirmed=True,
        der_eligibility_source="Explicit hypothetical BGE-approved ordinary renewable PV/storage service without standby/special charges; zero-export dispatch")
    return a


def catalog():
    return [dict(id=p, label="BGE " + ("Residential R SOS" if p == "R" else "Small General Service G · Type I SOS"),
        status="supported", customer_class="residential" if p == "R" else "commercial",
        coverage=[dict(start=s, end=e, is_complete_bill=p == "G",
            scope="Recurring tariff charges; residential historical-account relief refunds excluded" if p == "R" else "Ordinary utility bill within selected account/tax scope",
            excluded_components=[RELIEF_EXCLUSION] if p == "R" else []) for s, e in COVERAGE], voltage="secondary",
        interval_minutes=[15], solar_modes=["non_export"], supply_arrangements=["sos"],
        equipment_modes=["grid_only", "pv_only", "pv_battery"], representative_peak_kw=3.,
        account_fields=account_fields(p), sources=SOURCES,
        eligibility="Independently confirmed ordinary BGE Maryland R residential or secondary G Type I SOS, one meter, complete calendar cycles and unincorporated Anne Arundel County tax scope.",
        limitations=[
            "Complete consecutive 15-minute calendar cycles with the same designated billing month only; partial/shifted cycles and unverified dates reject.",
            "G requires existing utility-assigned Type I eligibility. Studies retain 30-minute import demand below25kW and monthly imports at most6000kWh October–May or7500kWh June–September; this conservative domain does not infer historical classification.",
            "G universal-service band $175–$1299 annual utility delivery charges is an explicit assigned account fact retained across scenarios; the optimizer does not recompute it from modeled annual bills.",
            "R reports a recurring tariff subtotal excluding historical-account legislative relief refunds. Refund eligibility, amount and posting month are unverified; a complete residential amount due is not claimed.",
            "SOS includes capacity, losses, ancillary service, administration and applicable embedded taxes. Retail transmission and monthly energy-cost adjustment are charged once; no wholesale LMP/PLC/NSPL adder.",
            "PV/storage requires approved ordinary service and zero exports; no NEM bank, export credit, standalone storage or standby settlement.",
            "Other localities, Type II/hourly SOS, GS time-of-use, competitive supply, assistance, opt-out and special charges remain unsupported."])
        for p in PLANS]


def cycle_review(a, index):
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2 or str(idx.tz) != TIMEZONE:
        raise ValueError("BGE requires America/New_York timestamps and complete15-minute intervals.")
    step = pd.Timedelta(minutes=15)
    if not np.all(idx[1:]-idx[:-1] == step):
        raise ValueError("BGE requires consecutive15-minute intervals; missing/duplicate/hourly data reject.")
    stop = idx[-1]+step
    if (idx[0] != idx[0].normalize() or idx[0].day != 1 or stop != idx[0]+pd.offsets.MonthBegin()
            or a.get("cycle_kind") != "regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("BGE first scope requires a complete calendar meter cycle; partial/shifted allocation is unverified.")
    if a.get("billing_month") != str(idx[0].date()):
        raise ValueError("BGE designated billing month must match the complete calendar service month.")
    # This bounded interface avoids assuming how bill-month factors allocate to
    # service dates in a shifted cycle. The bill date remains a separate fact.
    if a.get("bill_date") != str(idx[-1].date()):
        raise ValueError("BGE first scope requires a bill date on the final calendar service date.")
    rates_on(a["billing_month"], a["tariff"])
    return dict(service_start=str(idx[0].date()), service_end=str(idx[-1].date()),
        cycle_days=(stop.date()-idx[0].date()).days,
        elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)),
        billing_month=a["billing_month"], bill_date=a["bill_date"],
        monthly_charge_factor=1., partial_period_proration_applied=False)


def evidence(index, account):
    cycle_review(account, index)
    return dict(rate_evidence_status="verified", assumption_model=None,
        rate_assumptions=[], objective_scope="verified_charges_subtotal" if account["tariff"] == "R" else "complete_utility_bill")


def _reference(a, key):
    if not isinstance(a.get(key), str) or not 1 <= len(a[key].strip()) <= 500:
        raise ValueError("Document BGE cycle, tax, classification and interconnection assumptions without personal identifiers.")


def validate_account(a, index, equipment=None):
    if (not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "sos"
            or a.get("export_mode") != "none"):
        raise ValueError("Select ordinary BGE R/G residential/Type I SOS and zero export.")
    if a.get("rate_evidence_mode", "verified") != "verified" or a.get("provisional_assumptions_accepted", False) is not False:
        raise ValueError("BGE has no provisional-rate mode or missing-price fallback.")
    if a.get("relief_policy") != "exclude_account_specific_refunds":
        raise ValueError("BGE recurring tariff scope explicitly excludes account-specific legislative relief; no historical refund amount or posting cycle is inferred.")
    if any(a.get(k) is not True for k in ("eligibility_confirmed", "ordinary_service_confirmed", "local_charges_confirmed")):
        raise ValueError("Confirm BGE delivery/schedule/SOS eligibility, ordinary service and tax jurisdiction independently of location.")
    for key in ("cycle_source", "tax_source"):
        _reference(a, key)
    if (a.get("tax_jurisdiction") != "anne_arundel_unincorporated" or a.get("tax_exempt") is not False
            or (a.get("voltage"), a.get("phase"), a.get("voltage_v"), a.get("power_factor")) != ("secondary", "single", 240., 1.)
            or a.get("meter_count") != 1 or a.get("service_line_count") != 1
            or a.get("opening_credit_usd") != 0. or a.get("demand_interval_minutes") != 30):
        raise ValueError("BGE first scope requires ordinary unincorporated Anne Arundel taxes, one120/240V single-phase meter/service, unity PF,30-minute eligibility demand and no opening credits.")
    if a["tariff"] == "G":
        if a.get("type_i_confirmed") is not True or a.get("usc_band") != "175_to_1299":
            raise ValueError("Confirm existing BGE G Type I SOS classification and the utility-assigned universal-service annual delivery band $175–$1299.")
        _reference(a, "usc_source")
    elif a.get("usc_band") != "residential" or a.get("type_i_confirmed") is not False:
        raise ValueError("BGE R requires residential SOS and the residential universal-service charge.")
    cycle_review(a, index)
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("BGE PV/storage requires approved ordinary renewable service; standalone storage is outside this scope.")
        _reference(a, "der_eligibility_source")
        if max(equipment.get("pv_dc_kw", 0.), equipment.get("pv_ac_kw", 0.))+equipment.get("battery_kw", 0.) > 25.+1e-8:
            raise ValueError("BGE bounded ordinary renewable study limits combined PV/battery nameplate to25kW; this does not establish interconnection eligibility.")


def validate_state(a, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("BGE ordinary non-export billing has no modeled opening credit or demand-history state.")


def charge_lines(index, imports, exports, a, *, math, state=None):
    validate_state(a, index, state=state)
    idx = pd.DatetimeIndex(index)
    cycle = cycle_review(a, idx)
    if math.convex:
        math.constraints.append(exports == 0)
    elif np.max(exports) > 1e-5:
        raise ValueError("BGE export settlement is not implemented; exports must be zero.")
    r = rates_on(a["billing_month"], a["tariff"])
    energy = math.hours*math.sum(imports)
    metrics = {**cycle, "rates":r, "measured_demand_charge":False, "intraday_time_of_use_pricing":False}
    if a["tariff"] == "G":
        peak = math.demand(imports, idx, minutes=30)
        energy_limit = 7500. if 6 <= idx[0].month <= 9 else 6000.
        if math.convex:
            math.constraints.extend([peak <= 24.99999, energy <= energy_limit])
        elif peak >= 25. or energy > energy_limit+1e-7:
            raise ValueError("BGE G bounded Type I study requires30-minute import demand below25kW and monthly imports within6000/7500kWh; prior classification remains independently confirmed.")
        metrics.update(measured_demand_kw=peak, type_i_monthly_energy_limit_kwh=energy_limit,
            type_i_classification_basis="Existing utility-assigned membership plus conservative study import limits; no automatic reassignment or inferred PJM tag",
            usc_band=a["usc_band"], usc_source=a["usc_source"])
    return _bill(r, energy, a, metrics, math)


def _bill(r, energy, a, metrics, math):
    """Separately stated county tax and EES are outside state taxable price."""
    # No market prices enter an ordinary default retail bill.
    lines = {"distribution_customer":r["customer"]}
    lines.update({name:energy*value for name, value in r["energy"].items()})
    lines.update(r["monthly"])
    # County excise and EES are explicitly excluded by COMAR03.06.01.10C.
    taxable = sum(lines.values())
    lines["environmental_surcharge"] = math.minimum(energy*r["environmental_rate"], r["environmental_monthly_cap"])
    lines["county_energy_tax"] = energy*r["county_tax_rate"]
    lines["sales_tax"] = taxable*r["sales_tax_rate"]
    complete = a["tariff"] == "G"
    metrics.update(capacity_transmission_treatment="SOS includes capacity/losses/ancillary/administration/embedded taxes. Filed retail transmission and Rider8 charged once; no wholesale LMP/PLC/NSPL charge.",
        component_application_clocks="Base service year and designated monthly riders; only matching complete calendar service/billing months executable",
        tax_jurisdiction=a["tax_jurisdiction"], usc_band=a["usc_band"],
        sales_tax_base_usd=taxable, sales_tax_rate=r["sales_tax_rate"],
        sales_tax_excludes=["environmental_surcharge", "county_energy_tax"],
        relief_policy=a["relief_policy"],
        rate_effective_basis="Verified monthly tariff intersections; no shifted-cycle or partial-period allocation")
    return dict(lines=lines, metrics=metrics, next_state={}, is_complete_bill=complete,
        excluded_components=[] if complete else [RELIEF_EXCLUSION],
        rate_evidence_status="verified", assumption_model=None, rate_assumptions=[], rate_sources=SOURCES,
        warnings=["BGE hypothetical ordinary non-export account; tariff, SOS type, assigned universal-service band, tax locality and interconnection require independent confirmation.",
            "Complete matching calendar service/billing months only; no unverified allocation, export credits or special-service settlement.",
            "Residential recurring tariff subtotal excludes account-specific legislative relief refunds, whose historical eligibility, amount and posting cycle are not inferred. It is not the complete amount due." if not complete else "Commercial taxes follow filed rates and Maryland taxable-price rules; no actual customer statement was recovered for tax-base calibration.",
            "Historical perfect foresight within each cycle; representative OpenDSS replay does not validate a surveyed customer installation."])
