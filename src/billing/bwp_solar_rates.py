"""Filed Burbank solar net-billing export values.

The 2026 adopted fee schedule, Article X section 11(C), publishes these ACOE
values. Rules and Regulations 3.25(a) assigns this program to qualifying new
solar installations. Billing and eligibility are enforced by the separate
BWP net-billing adapter; annual payout remains outside its bounded scope.
"""
from datetime import date

import numpy as np
import pandas as pd

from .burbank import periods


SOURCE = 'https://www.burbankwaterandpower.com/documents/d/guest/burbank_adopted_fee_schedule'
RULES_SOURCE = 'https://www.burbankwaterandpower.com/documents/d/guest/12-4-2025-2025-rules-and-regulations'
EFFECTIVE_START = date(2026, 1, 1)
RATE_VERIFIED_FROM = date(2026, 7, 1)
VERIFIED_THROUGH = date(2026, 9, 20)
SUMMER = {'on': .1186, 'mid': .0825, 'off': .0702}


def validate_net_billing_account(account, *, service_date):
    """Require a confirmed Section 3.25(a) trigger and interconnection.

    A pre-2026 permitted installation may move to net billing following an
    upgrade or transfer. An address alone never establishes the program.
    """
    if not isinstance(account, dict) or account.get('solar_program') != 'bwp_net_billing':
        raise ValueError('Confirm BWP solar net-billing enrollment.')
    try:
        service_day = date.fromisoformat(service_date)
    except (TypeError, ValueError):
        raise ValueError('BWP service_date must be an ISO calendar date.') from None
    if account.get('interconnection_confirmed') is not True:
        raise ValueError('Confirm the BWP solar interconnection agreement and permits.')
    capacity = account.get('solar_capacity_kw')
    if isinstance(capacity, bool) or not isinstance(capacity, (int, float)) or not np.isfinite(capacity) or not 0 < capacity <= 5000:
        raise ValueError('BWP solar net billing requires generation above zero and at most 5 MW.')
    triggers = []
    for field in ('permit_issue_date', 'upgrade_date', 'account_transfer_date'):
        value = account.get(field)
        if value is not None:
            try:
                parsed = date.fromisoformat(value)
            except (TypeError, ValueError):
                raise ValueError(f'BWP {field} must be an ISO calendar date.') from None
            if field != 'account_transfer_date' or account.get('transfer_to_new_customer_confirmed') is True:
                triggers.append(parsed)
    if not any(EFFECTIVE_START <= trigger <= service_day for trigger in triggers):
        raise ValueError('BWP net billing requires a permit, upgrade or account transfer on or after January 1, 2026 and no later than the service date.')
    return True


def export_prices(index):
    """Return verified $/kWh ACOE for Pacific-time 15-minute meter intervals."""
    index = pd.DatetimeIndex(index)
    if index.empty or index.tz is None:
        raise ValueError('BWP export timestamps must be timezone-aware and nonempty.')
    index = index.tz_convert('America/Los_Angeles')
    if (not index.is_monotonic_increasing or not index.is_unique or
            (len(index) > 1 and not (np.diff(index.asi8) == 15 * 60 * 10**9).all())):
        raise ValueError('BWP export values require unique ordered 15-minute intervals.')
    if index[0].date() < RATE_VERIFIED_FROM or index[-1].date() > VERIFIED_THROUGH:
        raise ValueError('BWP export prices are verified only July 1–September 20, 2026.')
    band = periods(index)
    return np.select([band == 'on', band == 'mid'],
                     [SUMMER['on'], SUMMER['mid']], default=SUMMER['off'])


def earned_export_credit(index, exported_kw):
    """Price metered exports only; do not treat earned dollars as cash paid."""
    prices = export_prices(index)
    power = np.asarray(exported_kw, dtype=float)
    if power.shape != prices.shape or not np.isfinite(power).all() or (power < 0).any():
        raise ValueError('BWP exported kW must be finite, nonnegative and interval-aligned.')
    return dict(export_kwh=float(power.sum() * .25),
                earned_credit=float(np.dot(power, prices) * .25),
                rate_source=SOURCE, rules_source=RULES_SOURCE)
