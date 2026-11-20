"""Catalog-only Choptank Maryland SOS schedules, pending complete bill evidence."""

import pandas as pd

from .choptank_md_rates import (
    BLOCKED_REASON, C, ELIGIBILITY, GAPS, PLANS, R, S, SOURCES, check_plan, rates_for_month,
)

UTILITY = "choptank_electric_cooperative"
TIMEZONE = "America/New_York"


def account_fields(plan=R):
    check_plan(plan)
    return [
        dict(name="account_source", type="text", label="Choptank schedule, service capacity in kVA and retail SOS evidence"),
        dict(name="cycle_source", type="text", label="Meter interval, bill date and applicable tax and credit records"),
        dict(name="full_monthly_charges_confirmed", type="boolean", label="Actual complete monthly cycle with full monthly charges"),
        dict(name="der_ordinary_service_confirmed", type="boolean",
             label="Final Choptank operating approval and ordinary import terms for the exact non-export installation"),
    ]


def defaults(plan=R):
    check_plan(plan)
    return dict(tariff=plan, supply="sos", export_mode="none", voltage="secondary",
                phase="three" if plan == S else "single", meter_count=1,
                opening_credit_usd=0., rate_evidence_mode="verified", cycle_kind="regular",
                billing_month="2026-10-01", bill_date="2026-10-31", account_source="", cycle_source="",
                full_monthly_charges_confirmed=False, der_ordinary_service_confirmed=False)


def hypothetical_defaults(plan=R, *, day=None):
    account = defaults(plan)
    month = pd.Timestamp(day or account["billing_month"]).replace(day=1)
    account.update(hypothetical_account=True, billing_month=str(month.date()),
                   bill_date=str((month + pd.offsets.MonthEnd()).date()))
    return account


def catalog():
    return [
        dict(id=plan, label=f"Choptank {label} SOS", status="unsupported",
             billing_supported=False, dispatch_supported=False,
             customer_class="residential" if plan == R else "commercial",
             eligibility=ELIGIBILITY[plan], voltage="secondary", interval_minutes=[15],
             base_effective_start="2023-12-01", supply_arrangements=["sos"],
             equipment_modes=[], solar_modes=[], coverage=[],
             coverage_gaps=[dict(start=start, end=end, reason=why) for start, end, why in GAPS],
             representative_peak_kw={R: 3., C: 5., S: 20.}[plan],
             account_fields=account_fields(plan), sources=list(SOURCES), reason=BLOCKED_REASON,
             limitations=[
                 BLOCKED_REASON,
                 "May 2025 and May 2026 capital-credit retirements depend on historical account membership and purchases.",
                 "Sections 114 and 920 require final approval for the exact interconnected equipment. "
                 "PJM or Old Dominion wholesale settlement does not price Choptank retail SOS.",
             ])
        for plan, label in PLANS.items()
    ]


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    if len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans:
        raise ValueError("Choptank requires consecutive 15-minute Eastern-time intervals.")
    step = pd.Timedelta(minutes=15)
    if not ((index[1:] - index[:-1]) == step).all():
        raise ValueError("Choptank requires consecutive 15-minute Eastern-time intervals.")
    start = index[0]
    if (start.day != 1 or start != start.normalize()
            or index[-1] + step != start + pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular"
            or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Choptank requires a complete calendar cycle with full monthly charges.")
    if account.get("billing_month") != str(start.date()) or account.get("bill_date") != str(index[-1].date()):
        raise ValueError("Choptank requires matching service and billing dates for this calendar-cycle scope.")
    return rates_for_month(str(start.date()), account.get("tariff"))


def validate_account(account, index, equipment=None):
    if (not isinstance(account, dict) or account.get("tariff") not in PLANS
            or account.get("supply") != "sos" or account.get("export_mode") != "none"):
        raise ValueError("Choptank's researched scope requires ordinary R/C/S, cooperative SOS and zero export.")
    raise ValueError(BLOCKED_REASON)


def validate_native_load(account, load):
    raise ValueError(BLOCKED_REASON)


def validate_state(account, index, state=None, equipment=None):
    raise ValueError(BLOCKED_REASON)


def charge_lines(index, imports, exports, account, *, math, state=None):
    raise ValueError(BLOCKED_REASON)
