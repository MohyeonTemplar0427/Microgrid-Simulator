"""Researched, disabled REC Virginia A-1/B-1 bundled catalog.

No current or historical subtotal is exposed as a complete bill. Account
confirmations, hypothetical defaults and non-export settings cannot bypass
the missing complete tax/component intersections.
"""
import numpy as np
import pandas as pd

from .rappahannock_va_rates import BLOCKED_REASON, GAPS, PLANS, SOURCES, rates_for_month

UTILITY = "rappahannock_electric_cooperative"
TIMEZONE = "America/New_York"
CONFIRMATIONS = {
    "eligibility_confirmed": "REC independently confirms the selected Virginia A-1/B-1 bundled classification",
    "ordinary_service_confirmed": "Ordinary single-meter secondary service without optional programs or special facilities",
    "full_monthly_charges_confirmed": "Complete calendar service and billing month with full monthly charges",
}


def account_fields(plan="A-1"):
    if plan not in PLANS:
        raise ValueError("Select REC A-1 or B-1.")
    return [dict(name=key, type="boolean", required=True, label=label)
            for key, label in CONFIRMATIONS.items()] + [
        dict(name="account_source", type="text", required=True,
             label="Independent utility classification and tax evidence"),
        dict(name="cycle_source", type="text", required=True,
             label="Meter-cycle and bill-date evidence"),
        dict(name="der_ordinary_service_confirmed", type="boolean",
             label="Written REC approval preserves ordinary import charges for this exact non-export installation"),
        dict(name="der_activation_date", type="date", label="Final interconnection approval active by"),
        dict(name="der_eligibility_source", type="text", label="Exact PV/storage approval and billing reference"),
    ]


def defaults(plan="A-1"):
    if plan not in PLANS:
        raise ValueError("Select REC A-1 or B-1.")
    account = dict(tariff=plan, supply="bundled", export_mode="none", voltage="secondary", phase="single",
                   voltage_v=240., meter_count=1, opening_credit_usd=0., rate_evidence_mode="verified",
                   billing_month="2026-10-01", bill_date="2026-10-31", cycle_kind="regular",
                   account_source="", cycle_source="", der_ordinary_service_confirmed=False,
                   der_activation_date="", der_eligibility_source="")
    account.update(dict.fromkeys(CONFIRMATIONS, False))
    return account


def hypothetical_defaults(plan="A-1", *, day=None):
    """A hypothetical account remains blocked; no assumed rates or approvals."""
    account = defaults(plan)
    month = pd.Timestamp(day or account["billing_month"]).replace(day=1)
    account.update(hypothetical_account=True, billing_month=str(month.date()),
                   bill_date=str((month+pd.offsets.MonthEnd()).date()),
                   account_source="Hypothetical REC account; executable tariff coverage remains unavailable",
                   cycle_source="Hypothetical complete calendar cycle; billing remains blocked")
    return account


def catalog():
    return [dict(
        id=plan, label=f"REC {plan} {'Residential' if plan == 'A-1' else 'Small General Service'} bundled",
        status="unsupported", billing_supported=False, dispatch_supported=False,
        customer_class="residential" if plan == "A-1" else "commercial",
        coverage=[], coverage_gaps=[dict(start=start, end=end, reason=reason) for start, end, reason in GAPS],
        base_effective_start="2024-10-01", voltage="secondary", interval_minutes=[15],
        supply_arrangements=["bundled"], equipment_modes=[], solar_modes=[],
        representative_peak_kw=3. if plan == "A-1" else 5., account_fields=account_fields(plan), sources=SOURCES,
        eligibility="A-1 covers ordinary residences; B-1 requires independent REC classification "
                    "and maximum required demand at most25kW. Required transformer capacity affects its delivery minimum. No complete billing dates are verified.",
        reason=BLOCKED_REASON, limitations=[BLOCKED_REASON,
            "Filed base/PCA/DR rates cannot replace the missing cooperative-period tax adjustment or prove complete bills.",
            "Non-export operation does not itself establish approval or ordinary import-billing eligibility.",
            "Utility, bundled supply, Virginia taxes and PJM/wholesale metadata remain separate."],
    ) for plan in PLANS]


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans
            or not np.all(index[1:]-index[:-1] == step)):
        raise ValueError("REC requires complete consecutive 15-minute Eastern-time intervals.")
    start, stop = index[0], index[-1]+step
    if (start != start.normalize() or start.day != 1 or stop != start+pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular"
            or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("REC requires a complete calendar cycle and full monthly charges.")
    if account.get("billing_month") != str(start.date()) or account.get("bill_date") != str(index[-1].date()):
        raise ValueError("REC requires matching service and billing months with a final-day bill date.")
    return rates_for_month(str(start.date())[:7], account.get("tariff"))


def validate_account(account, index, equipment=None):
    if (not isinstance(account, dict) or account.get("tariff") not in PLANS
            or account.get("supply") != "bundled" or account.get("export_mode") != "none"):
        raise ValueError("REC initial scope is A-1/B-1 bundled with no export settlement.")
    # Even a fully confirmed/hypothetical account cannot manufacture rates.
    raise ValueError(BLOCKED_REASON)


def validate_native_load(account, load):
    raise ValueError(BLOCKED_REASON)


def validate_state(account, index, state=None, equipment=None):
    raise ValueError(BLOCKED_REASON)


def charge_lines(index, imports, exports, account, *, math, state=None):
    raise ValueError(BLOCKED_REASON)
