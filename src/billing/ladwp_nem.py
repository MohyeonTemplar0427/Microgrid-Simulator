"""LADWP R-1A NEM for a net-import billing cycle.

The filed NEM rider nets energy over the billing period. Its public text does
not specify which R-1A tier prices a net-export cycle, so this adapter rejects
that case instead of inventing an export-credit rate.
"""
import numpy as np

from .socal import number


def validate_account(key, account):
    if key != 'ladwp_r-1a' or account.get('customer_class') != 'residential':
        raise ValueError('LADWP NEM currently supports residential R-1A net-import cycles only.')
    if account.get('interconnection_confirmed') is not True:
        raise ValueError('Confirm LADWP NEM interconnection and bidirectional metering.')
    if account.get('nem_credit_confirmed') is not True:
        raise ValueError('Confirm the opening NEM credit balance from the account, or explicitly assume zero.')
    number(account.get('nem_opening_credit'), 'Opening LADWP NEM credit balance', 0, 1e6)


def bill(key, index, imports, exports, account, plan):
    from .socal import charge_lines

    exports = np.asarray(exports, dtype=float)
    if exports.shape != imports.shape or not np.isfinite(exports).all() or np.any(exports < 0):
        raise ValueError('LADWP NEM exports must be finite nonnegative 15-minute kW.')
    if np.max(np.minimum(imports, exports)) > 1e-7:
        raise ValueError('LADWP NEM cannot import and export simultaneously at one meter.')
    imported = float(np.sum(imports) * .25)
    exported = float(np.sum(exports) * .25)
    net = imported - exported
    if net < -1e-7:
        raise ValueError('LADWP NEM net-export cycles need a verified R-1A excess-credit tier; this study cannot price them.')
    net = max(0., net)
    # R-1A allocates non-TOU consumption by service days at a rate boundary.
    # Uniform synthetic power preserves exactly the cycle's net kWh for the
    # existing tier/minimum/quarterly-adjustment calculation.
    net_power = np.full(len(index), net / (len(index) * .25))
    lines = {name: float(value) for name, value in charge_lines(key, index, net_power, account).items()}
    factor = account.get('billing_month_factor', len(index.normalize().unique()) / 30)
    protected_minimum = 10 * factor
    adjustment_names = ('ECA', 'VEA', 'CRPSEA', 'VRPSEA', 'ESA', 'RCA', 'IRCA')
    eligible = max(0., lines['energy_charge'] + lines['minimum_adjustment'] - protected_minimum)
    eligible += sum(lines.get(name, 0.) for name in adjustment_names)
    opening = float(account['nem_opening_credit'])
    used = min(opening, eligible)
    lines['nem_opening_credit_applied'] = -used
    total = sum(lines.values())
    return {'total': total, 'line_items': lines, 'usage_kWh': net,
            'import_kWh': imported, 'export_kWh': exported, 'peak_kw': float(imports.max()),
            'amount_due': max(0., total), 'credit_balance': opening - used,
            'credit_ledger': {'opening_credit': opening, 'earned_credit': 0.,
                              'applied_credit': used, 'closing_credit': opening - used,
                              'protected_minimum': protected_minimum},
            'tariff': plan,
            'adjustment_versions': sorted({f'{day.year}-Q{(day.month-1)//3+1}' for day in index}),
            'rate_versions': [],
            'warnings': [
                'LADWP NEM R-1A: imports and exports are netted over this billing cycle; net-export cycles and R-1B TOU settlement are not priced.',
                'Opening credit is account-confirmed or explicitly assumed; credits cannot pay minimum charges or taxes.',
                'Monthly quantities use the confirmed billing-month factor; local tax follows the existing study assumption on charges before credit application.',
                'Only this meter and billing cycle are modeled; account termination and special riders are excluded.',
            ]}
