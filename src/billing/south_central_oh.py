"""Researched, unavailable South Central Power Ohio R/SGS bundled service.

No base subtotal or sample-only factor is exposed as an executable bill.
Written non-export approval and independent account confirmations cannot
replace missing complete dated tariff intersections.
"""

import numpy as np
import pandas as pd

from .south_central_oh_rates import BLOCKED_REASON, GAPS, PLANS, SOURCES, rates_for_month

UTILITY = "south_central_power_ohio"
TIMEZONE = "America/New_York"
CONFIRMATIONS = {
    "eligibility_confirmed": "South Central Power independently confirms ordinary R or retained SGS membership and classification",
    "ordinary_service_confirmed": "One ordinary single-phase 120/240 V secondary meter without shared dwellings, special installations or special facilities",
    "cooperative_supply_confirmed": "Ordinary bundled South Central Power service throughout the cycle, with Buckeye Power wholesale costs passed through under Rider B",
    "full_monthly_charges_confirmed": "Actual complete monthly meter cycle and bill dates, without estimated or bimonthly reads",
    "tax_scope_confirmed": "Independent ordinary Ohio kWh-tax and all Rider A/locality impositions are documented",
    "transformer_capacity_confirmed": "Cooperative-installed or allocated transformer kVA and the applicable minimum are independently documented",
    "no_optional_charges_confirmed": "No optional programs, community solar, round-up donation, discounts, credits, fees or other special charges",
}


def account_fields(plan_id="R"):
    if plan_id not in PLANS:
        raise ValueError("Select South Central Power R or SGS.")
    fields = [dict(name=key, type="boolean", required=True, label=label)
              for key, label in CONFIRMATIONS.items()]
    fields += [
        dict(name="account_source", type="text", required=True,
             label="Independent cooperative plan assignment, ordinary service and supply evidence"),
        dict(name="cycle_source", type="text", required=True,
             label="Actual service cycle, bill date and monthly factor applicability evidence"),
        dict(name="tax_source", type="text", required=True,
             label="Ordinary state tax and all applicable locality/Rider A evidence"),
        dict(name="transformer_kva", type="number", required=True,
             label="Cooperative installed or allocated transformer capacity in kVA"),
        dict(name="transformer_source", type="text", required=True,
             label="Independent transformer allocation and minimum-charge evidence"),
        dict(name="der_ordinary_service_confirmed", type="boolean",
             label="Written South Central Power approval preserves ordinary import billing for this exact non-export installation"),
        dict(name="der_activation_date", type="date", label="Final interconnection and metering active by"),
        dict(name="der_eligibility_source", type="text",
             label="Exact non-export PV or PV-charged paired storage approval, ordinary tariff continuation and all additional charges"),
    ]
    if plan_id == "SGS":
        fields += [
            dict(name="sgs_retained_assignment_confirmed", type="boolean", required=True,
                 label="Cooperative retains ordinary SGS classification below 50 kW; no pending reassignment or special minimum"),
            dict(name="sgs_classification_source", type="text", required=True,
                 label="Independent historical demand, retained SGS assignment and contract/minimum evidence"),
        ]
    return fields


def defaults(plan_id="R"):
    if plan_id not in PLANS:
        raise ValueError("Select South Central Power R or SGS.")
    account = dict(tariff=plan_id, supply="bundled", export_mode="none", voltage="secondary",
                   phase="single", voltage_v=240., meter_count=1, opening_credit_usd=0.,
                   rate_evidence_mode="verified", billing_month="2026-06-01", bill_date="2026-06-30",
                   cycle_kind="regular", account_source="", cycle_source="", tax_source="",
                   transformer_kva=None, transformer_source="", der_ordinary_service_confirmed=False,
                   der_activation_date="", der_eligibility_source="")
    account.update(dict.fromkeys(CONFIRMATIONS, False))
    if plan_id == "SGS":
        account.update(sgs_retained_assignment_confirmed=False, sgs_classification_source="")
    return account


def hypothetical_defaults(plan_id="R", *, day=None):
    """Hypothetical account labels never approve DER or supply missing rates."""
    account = defaults(plan_id)
    month = pd.Timestamp(day or account["billing_month"]).replace(day=1)
    account.update(hypothetical_account=True, billing_month=str(month.date()),
                   bill_date=str((month+pd.offsets.MonthEnd()).date()),
                   account_source="Hypothetical South Central Power account; complete tariff coverage remains unavailable",
                   cycle_source="Hypothetical complete calendar cycle; billing remains unavailable")
    return account


def catalog():
    return [dict(
        id=plan, label=f"South Central Power {plan} {label}", status="unsupported",
        billing_supported=False, dispatch_supported=False,
        customer_class="residential" if plan == "R" else "commercial", coverage=[],
        coverage_gaps=[dict(start=start, end=end, reason=reason) for start, end, reason in GAPS],
        base_effective_start="2026-04-01", voltage="secondary", interval_minutes=[15],
        supply_arrangements=["bundled"], equipment_modes=[], solar_modes=[],
        representative_peak_kw=3. if plan == "R" else 5.,
        account_fields=account_fields(plan), sources=list(SOURCES), reason=BLOCKED_REASON,
        eligibility="R is individual single-family, home or farm single-phase service. SGS is independently assigned non-residential service with billing capacity below 50 kW; the cooperative retains reclassification authority.",
        limitations=[
            BLOCKED_REASON,
            "Transformer-based minimums require installed or allocated kVA, independently of modeled imports. SGS unusual installations and extensions can have contract minimums or facility charges.",
            "Bundled cooperative supply and Buckeye Power cost recovery are separate from PJM metadata and wholesale prices; an IOU SSO tariff is not substituted.",
            "Non-export PV requires final written approval for this exact installation and unchanged ordinary import billing. Paired storage requires PV-only charging and zero export; neither is enabled while the rate stack is unavailable.",
        ],
    ) for plan, label in PLANS.items()]


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans
            or not np.all(index[1:]-index[:-1] == step)):
        raise ValueError("South Central Power requires complete consecutive 15-minute Eastern-time intervals.")
    start, stop = index[0], index[-1]+step
    if (start != start.normalize() or start.day != 1 or stop != start+pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular"
            or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("South Central Power requires a complete calendar cycle and full monthly charges.")
    if account.get("billing_month") != str(start.date()) or account.get("bill_date") != str(index[-1].date()):
        raise ValueError("South Central Power calendar studies require matching service/billing months and final-day bill dates; actual shifted billing applicability remains unverified.")
    return rates_for_month(str(start.date()), account.get("tariff"))


def validate_account(account, index, equipment=None):
    if (not isinstance(account, dict) or account.get("tariff") not in PLANS
            or account.get("supply") != "bundled" or account.get("export_mode") != "none"):
        raise ValueError("South Central Power initial scope is ordinary R/SGS bundled service with zero export.")
    raise ValueError(BLOCKED_REASON)


def validate_native_load(account, load):
    raise ValueError(BLOCKED_REASON)


def validate_state(account, index, state=None, equipment=None):
    raise ValueError(BLOCKED_REASON)


def charge_lines(index, imports, exports, account, *, math, state=None):
    raise ValueError(BLOCKED_REASON)
