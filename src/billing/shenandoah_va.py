"""Researched, unavailable Shenandoah Valley Virginia A/B retail service.

No base/PCA subtotal is a complete bill. Neither account confirmations nor
hypothetical approvals can resolve the missing dated surcharge/tax evidence.
"""

import numpy as np
import pandas as pd

from .shenandoah_va_rates import BLOCKED_REASON, GAPS, PLANS, SOURCES, rates_for_month

UTILITY = "shenandoah_valley_electric_cooperative"
TIMEZONE = "America/New_York"
CONFIRMATIONS = {
    "eligibility_confirmed": "SVEC independently confirms ordinary residential A or retained general-service B classification",
    "ordinary_service_confirmed": "One ordinary single-phase 120/240 V secondary meter without special facilities, fees, optional programs, discounts or credits",
    "cooperative_supply_confirmed": "SVEC is the ordinary retail energy provider throughout the cycle; ODEC wholesale recovery is separate from PJM data",
    "full_monthly_charges_confirmed": "Complete actual monthly meter cycle with independently verified billing month, bill date and full monthly charges",
    "locality_confirmed": "Service is in unincorporated Rockingham County and subject to the independently documented utility tax",
    "taxable_service_confirmed": "Ordinary taxable service; all state/local/SCC levies, applicable federal-power reduction and sales/use surcharge are independently resolved",
    "meter_precision_confirmed": "Actual kWh metering and bill precision confirmed; no unmodeled rounding to 10 kWh",
    "motor_limit_confirmed": "No individual single-phase motor reaches 10 hp and no unapproved unusual equipment is present",
}


def account_fields(plan_id="A-15"):
    if plan_id not in PLANS:
        raise ValueError("Select Shenandoah Valley A-15 or B-16.")
    fields = [dict(name=key, type="boolean", required=True, label=label)
              for key, label in CONFIRMATIONS.items()]
    fields += [
        dict(name="account_source", type="text", required=True,
             label="Independent SVEC plan, supply and ordinary-account evidence"),
        dict(name="cycle_source", type="text", required=True,
             label="Actual service cycle, billing month, bill date and rate applicability evidence"),
        dict(name="tax_source", type="text", required=True,
             label="Complete state/county/SCC and STS applicability evidence"),
        dict(name="der_ordinary_service_confirmed", type="boolean",
             label="Written SVEC approval preserves ordinary import billing for this exact non-export installation"),
        dict(name="der_activation_date", type="date", label="Final interconnection and metering active by"),
        dict(name="der_eligibility_source", type="text",
             label="Exact PV or PV-charged paired storage approval, ordinary import terms and all additional charges"),
    ]
    if plan_id == "B-16":
        fields += [
            dict(name="b_retained_assignment_confirmed", type="boolean", required=True,
                 label="SVEC independently retains ordinary B, without LP/LPD transfer or special contractual terms"),
            dict(name="b_demand_minimum_source", type="text", required=True,
                 label="Independent preceding-calendar-year demands, requested capacity and contract minimum review"),
            dict(name="b_rkva_source", type="text", required=True,
                 label="Independent utility RKVA metering/billing applicability and actual reactive-demand evidence"),
        ]
    return fields


def defaults(plan_id="A-15"):
    if plan_id not in PLANS:
        raise ValueError("Select Shenandoah Valley A-15 or B-16.")
    account = dict(tariff=plan_id, supply="bundled", export_mode="none", voltage="secondary",
                   phase="single", voltage_v=240., meter_count=1, opening_credit_usd=0.,
                   rate_evidence_mode="verified", locality="rockingham_unincorporated",
                   billing_month="2026-11-01", bill_date="2026-11-30", cycle_kind="regular",
                   account_source="", cycle_source="", tax_source="",
                   der_ordinary_service_confirmed=False, der_activation_date="", der_eligibility_source="")
    account.update(dict.fromkeys(CONFIRMATIONS, False))
    if plan_id == "B-16":
        account.update(b_retained_assignment_confirmed=False, b_demand_minimum_source="", b_rkva_source="")
    return account


def hypothetical_defaults(plan_id="A-15", *, day=None):
    """Hypothetical labels leave rates and exact-installation approval absent."""
    account = defaults(plan_id)
    month = pd.Timestamp(day or account["billing_month"]).replace(day=1)
    account.update(hypothetical_account=True, billing_month=str(month.date()),
                   bill_date=str((month+pd.offsets.MonthEnd()).date()),
                   account_source="Hypothetical SVEC account; executable tariff coverage remains unavailable",
                   cycle_source="Hypothetical complete calendar cycle; billing remains unavailable")
    return account


def catalog():
    return [dict(
        id=plan, label=f"Shenandoah Valley {plan} {label}", status="unsupported",
        billing_supported=False, dispatch_supported=False,
        customer_class="residential" if plan == "A-15" else "commercial", coverage=[],
        coverage_gaps=[dict(start=start, end=end, reason=reason) for start, end, reason in GAPS],
        base_effective_start="2026-05-01", voltage="secondary", interval_minutes=[15],
        supply_arrangements=["bundled"], equipment_modes=[], solar_modes=[],
        representative_peak_kw=3. if plan == "A-15" else 5.,
        account_fields=account_fields(plan), sources=list(SOURCES), reason=BLOCKED_REASON,
        eligibility="Ordinary single-phase secondary SVEC retail supply. A covers permanent single-family residences/farms. B requires independent classification, demand/minimum and RKVA review.",
        limitations=[
            BLOCKED_REASON,
            "Published PCA factors are source observations, without executable complete-bill coverage. A tariff suffix or current web link does not resolve STS-12 successor applicability.",
            "B uses actual fifteen-minute demand, reactive demand where billed, preceding-calendar-year/requested-capacity minimum and any contract minimum; modeled imports cannot establish those facts.",
            "Exact-installation written ordinary-import approval, PV-only storage charging and zero export would be required for future DER support; no equipment mode is enabled.",
        ],
    ) for plan, label in PLANS.items()]


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans
            or not np.all(index[1:]-index[:-1] == step)):
        raise ValueError("Shenandoah Valley requires complete consecutive 15-minute Eastern-time intervals.")
    start, stop = index[0], index[-1]+step
    if (start != start.normalize() or start.day != 1 or stop != start+pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular"
            or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Shenandoah Valley requires a complete calendar cycle and full monthly charges.")
    if account.get("billing_month") != str(start.date()) or account.get("bill_date") != str(index[-1].date()):
        raise ValueError("Shenandoah Valley requires matching calendar service/billing months and a final-day bill date.")
    return rates_for_month(str(start.date()), account.get("tariff"))


def validate_account(account, index, equipment=None):
    if (not isinstance(account, dict) or account.get("tariff") not in PLANS
            or account.get("supply") != "bundled" or account.get("export_mode") != "none"):
        raise ValueError("Shenandoah Valley initial scope is ordinary A-15/B-16 bundled service with zero export.")
    raise ValueError(BLOCKED_REASON)


def validate_native_load(account, load):
    raise ValueError(BLOCKED_REASON)


def validate_state(account, index, state=None, equipment=None):
    raise ValueError(BLOCKED_REASON)


def charge_lines(index, imports, exports, account, *, math, state=None):
    raise ValueError(BLOCKED_REASON)
