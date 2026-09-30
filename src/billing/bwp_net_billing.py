"""Bounded BWP residential EV TOU net-billing cycle and credit ledger.

The published solar sample bill places export credit against usage and ECAC,
then taxes the nonnegative remaining usage plus the protected service charges.
There is no annual cash-out estimate in this single-cycle model.
"""

import cvxpy as cp
import numpy as np

from . import burbank
from .bwp_solar_rates import (SOURCE, RULES_SOURCE, earned_export_credit,
                              export_prices, validate_net_billing_account)

SAMPLE_SOURCE = 'https://www.burbankwaterandpower.com/solar-net-bill-breakdown'


def validate_account(account, start, end):
    if account.get('solar_program') != 'bwp_net_billing':
        raise ValueError('Select BWP net billing explicitly.')
    validate_net_billing_account(account, service_date=start)
    if account.get('bwp_first_cycle_confirmed') is True:
        if account.get('bwp_opening_credit', 0) not in (None, 0):
            raise ValueError('A confirmed first BWP solar cycle has no opening credit.')
    else:
        from .socal import number
        number(account.get('bwp_opening_credit'), 'Confirmed BWP opening solar credit')
        if account.get('bwp_opening_balance_confirmed') is not True:
            raise ValueError('Confirm the BWP opening solar credit balance or select first cycle.')
    if end > burbank.END or start < burbank.START:
        raise ValueError('BWP net billing is verified July 1–September 20, 2026 only.')


def opening_credit(account):
    return 0. if account.get('bwp_first_cycle_confirmed') is True else float(account['bwp_opening_credit'])


def settlement(import_lines, imports, exports, index, account, *, convex=False):
    """Return payable expression and, for numeric use, reconciled bill lines/ledger."""
    prices = export_prices(index)
    if convex:
        earned = .25 * cp.sum(cp.multiply(prices, exports))
        imported_kwh = .25 * cp.sum(imports)
    else:
        metered = earned_export_credit(index, exports)
        earned = metered['earned_credit']
        imported_kwh = float(np.sum(imports) * .25)
    usage = import_lines['energy_charge'] + import_lines['energy_cost_adjustment']
    fixed = import_lines['customer_charge'] + import_lines['service_size_charge']
    available = opening_credit(account) + earned
    remaining = cp.pos(usage - available) if convex else max(0., usage - available)
    due = 1.14 * (remaining + fixed) + .0003 * imported_kwh
    if convex:
        return due
    applied = min(usage, available)
    lines = {
        'energy_charge': float(import_lines['energy_charge']),
        'energy_cost_adjustment': float(import_lines['energy_cost_adjustment']),
        'solar_credit_applied': -float(applied),
        'customer_charge': float(import_lines['customer_charge']),
        'service_size_charge': float(import_lines['service_size_charge']),
        'in_lieu_transfer': .07 * (remaining + fixed),
        'local_utility_tax': .07 * (remaining + fixed),
        'state_energy_surcharge': .0003 * imported_kwh,
    }
    ledger = dict(opening_credit=opening_credit(account), earned_export_credit=float(earned),
                  applied_to_usage=float(applied), closing_credit=float(available - applied),
                  exported_kwh=float(np.sum(exports) * .25))
    if abs(sum(lines.values()) - due) > 1e-7:
        raise ValueError('BWP solar line items do not reconcile to the bill.')
    return float(due), lines, ledger


def bill(key, index, imports, exports, account, plan):
    power = np.asarray(exports, dtype=float)
    if power.shape != imports.shape or not np.isfinite(power).all() or (power < 0).any():
        raise ValueError('BWP export channel must contain finite, nonnegative interval kW.')
    lines = burbank.charge_lines(key, index, imports, account)
    total, items, ledger = settlement(lines, imports, power, index, account)
    return dict(total=total, amount_due=total, line_items=items,
                usage_kWh=float(np.sum(imports) * .25), peak_kw=float(np.max(imports)),
                credit_balance=ledger['closing_credit'], credit_ledger=ledger,
                tariff=plan,
                rate_versions=[dict(version_id='BWP-EV-TOU-FY2027',start=str(index[0].date()),
                                    end=str(index[-1].date()),source=SOURCE)],
                adjustment_versions=['BWP-ECAC-0.034-verified-2026-09-20'],
                warnings=['BWP EV TOU solar net billing: metered export ACOE offsets import energy and ECAC; customer and service-size charges remain payable.',
                          'In-lieu transfer and UUT each apply to the post-credit usage subtotal plus service charges; imported kWh incur the state surcharge.',
                          'Unused solar dollars carry forward. Annual cash-out, special riders and future cycles are not projected.',
                          'Account eligibility and meter configuration must be confirmed; weather and AC network feasibility are separate assumptions.'],
                sources=[SOURCE, RULES_SOURCE, SAMPLE_SOURCE])
