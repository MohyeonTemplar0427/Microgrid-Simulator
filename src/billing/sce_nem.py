"""Bounded bundled SCE legacy NEM 1.0 / NEM-ST 2.0 monthly-cycle estimate.

The two legacy schedules use retail TOU netting, unlike NBT hourly avoided-cost
export prices. NEM-ST protects interval import NBCs; NEM 1.0 does not impose
that successor-tariff rule. Annual true-up and paired storage are excluded.
"""
from datetime import date
import numpy as np

from .sce_nbt import delivery_nbc_rates, generation_nbc_rates

FIRST_DAY = date(2025, 1, 1)
LAST_DAY = date(2026, 9, 17)


def validate_account(key, account, start, end):
    if key != 'sce_tou-d-prime' or account.get('customer_class') != 'residential':
        raise ValueError('Bounded SCE legacy NEM requires residential TOU-D-PRIME.')
    if account.get('generation_provider') != 'sce' or account.get('actual_generation_provider') != 'bundled':
        raise ValueError('SCE bundled NEM cannot substitute for CCA generation settlement.')
    begin, finish = date.fromisoformat(start), date.fromisoformat(end)
    if begin < FIRST_DAY or finish > LAST_DAY:
        raise ValueError(f'SCE legacy NEM cycle coverage is {FIRST_DAY} through {LAST_DAY}.')
    version = account.get('sce_nem_version')
    if version not in ('nem1', 'nem2'):
        raise ValueError('Confirm whether the account is on legacy NEM 1.0 or NEM-ST 2.0.')
    try:
        request = date.fromisoformat(account['sce_nem_request_date'])
        pto = date.fromisoformat(account['sce_nem_pto_date'])
        relevant_end = date.fromisoformat(account['sce_nem_relevant_period_end'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Supply confirmed NEM request, PTO and next annual true-up dates.') from exc
    cutoff = date(2017, 6, 30) if version == 'nem1' else date(2023, 4, 14)
    if not (request <= cutoff and request <= pto <= begin):
        raise ValueError('The confirmed NEM request must meet its legacy deadline and precede PTO and the study cycle.')
    if version == 'nem1' and pto > date(2017, 6, 30):
        raise ValueError('NEM 1.0 PTO must precede its July 2017 closure.')
    if version == 'nem2' and pto < date(2017, 7, 1):
        raise ValueError('NEM-ST 2.0 PTO must be July 1, 2017 or later.')
    if finish >= date(pto.year + 20, pto.month, pto.day):
        raise ValueError('The 20-year legacy eligibility period must still cover this cycle.')
    if not finish < relevant_end <= date(begin.year + 1, begin.month, begin.day):
        raise ValueError('The bounded NEM study must finish before the confirmed annual true-up.')
    if account.get('sce_nem_legacy_confirmed') is not True or account.get('interconnection_confirmed') is not True:
        raise ValueError('Confirm legacy NEM enrollment and bidirectional metering with SCE.')
    if account.get('sce_nem_billing_option') != 'monthly':
        raise ValueError('Only the monthly billing option is implemented for SCE legacy NEM.')
    value = account.get('sce_nem_opening_energy_credit')
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not np.isfinite(value) or value < 0 or account.get('sce_nem_credit_confirmed') is not True):
        raise ValueError('Confirm a finite nonnegative opening NEM energy-credit balance.')


def _cycle_prices(key, index, account):
    from .socal import RESIDENTIAL_PLANS, periods
    from .sce_residential import ROW_NAMES
    plan = RESIDENTIAL_PLANS[key]
    segments = plan.segments_for(index)
    if len(segments) != 1 or len(set(np.isin(index.month, [6, 7, 8, 9]))) != 1:
        raise ValueError('SCE legacy NEM currently needs one filed rate version and one season per cycle.')
    version = segments[0][0]
    data = version.data
    prefix = 'summer_' if index[0].month in (6, 7, 8, 9) else 'winter_'
    labels = [prefix + ('super_off' if p == 'super' else p) for p in periods(index, 'sce', 'TOU-D-PRIME')]
    if not set(labels) <= set(ROW_NAMES):
        raise ValueError('Unverified SCE TOU period in legacy NEM cycle.')
    rows = np.asarray([data['energy_rows'][label] for label in labels], dtype=float)
    fixed = len(index.normalize().unique()) * (
        data.get('base_services_charge_per_day', 0.) or
        data.get('basic_charge_per_day', 0.) or
        data.get('basic_charge_multifamily_per_day' if account.get('accommodation') == 'multifamily'
                 else 'basic_charge_single_family_per_day', 0.))
    minimum = len(index.normalize().unique()) * data['minimum_charge_per_day']
    return rows[:, 0] + rows[:, 1] + data['fixed_recovery_per_kwh'], fixed, minimum, version


def settlement(key, index, imports, exports, account, *, convex=False):
    """Amount due and bounded carryover, using one cycle's retail TOU netting."""
    import cvxpy as cp
    price, fixed, minimum, _version = _cycle_prices(key, index, account)
    version = account['sce_nem_version']
    nbc = delivery_nbc_rates(index) + generation_nbc_rates(index) if version == 'nem2' else np.zeros(len(index))
    energy_rate = price - nbc
    sum_ = cp.sum if convex else np.sum
    maximum = cp.maximum if convex else np.maximum
    net_energy = sum_(cp.multiply(imports - exports, energy_rate) if convex else
                      (imports - exports) * energy_rate) * .25
    protected_nbc = sum_(cp.multiply(imports, nbc) if convex else imports * nbc) * .25
    # The pre-BSC residential minimum includes interval NBCs; do not add both
    # the entire minimum and NBCs. After BSC, the filed minimum is zero.
    protected_fixed = maximum(fixed, minimum - protected_nbc)
    opening = account['sce_nem_opening_energy_credit']
    energy_due = maximum(net_energy - opening, 0)
    taxable = energy_due + protected_nbc + protected_fixed
    local_tax = taxable * account['local_tax_percent'] / 100
    surcharge = sum_(imports) * (.25 * .0003)
    due = taxable + local_tax + surcharge - account.get('climate_credit_amount', 0.)
    if convex:
        return due
    net_energy, protected_nbc, energy_due = map(float, (net_energy, protected_nbc, energy_due))
    used = min(opening, max(net_energy, 0.))
    earned = max(-net_energy, 0.)
    ledger = {'opening_energy_credit': float(opening), 'earned_energy_credit': earned,
              'applied_energy_credit': float(used), 'closing_energy_credit': float(opening + earned - used),
              'protected_import_nbc': protected_nbc}
    lines = {'net_energy_charge_before_opening_credit': max(net_energy, 0.),
             'opening_energy_credit_applied': -float(used), 'protected_import_nbc': protected_nbc,
             'fixed_or_minimum_charge': protected_fixed, 'local_utility_tax': float(local_tax),
             'state_energy_surcharge': float(surcharge),
             'climate_credit': -account.get('climate_credit_amount', 0.)}
    return float(due), ledger, lines


def bill(key, index, imports, exports, account, plan):
    from .socal import RESIDENTIAL_PLANS, version_details
    if not np.isfinite(exports).all() or (exports < 0).any():
        raise ValueError('SCE NEM exports must be nonnegative finite kW.')
    if np.max(np.minimum(imports, exports)) > 1e-7:
        raise ValueError('SCE NEM cannot import and export simultaneously at one meter.')
    total, ledger, lines = settlement(key, index, imports, exports, account)
    if abs(sum(lines.values()) - total) > 1e-7:
        raise ValueError('SCE NEM lines do not reconcile to amount due.')
    details = version_details(RESIDENTIAL_PLANS[key], key, index, account)
    return {'total': total, 'amount_due': max(0., total), 'credit_balance': max(0., -total),
            'line_items': lines, 'usage_kWh': float(np.sum(imports) * .25),
            'export_kWh': float(np.sum(exports) * .25), 'peak_kw': float(np.max(imports)),
            'credit_ledger': ledger, 'rate_versions': details, 'tariff': plan,
            'adjustment_versions': [d['version_id'] for d in details],
            'warnings': ['SCE legacy NEM is one confirmed monthly billing cycle only; annual true-up and net-surplus compensation are not projected.',
                         'NEM 1.0 credits retail TOU net energy; NEM-ST 2.0 protects NBCs on interval imports. They do not use NBT hourly export prices.',
                         'Dispatch and bill do not assign future value to closing NEM credits; this is not a full-year optimum.',
                         'Local utility tax and state surcharge use study conventions; reconcile jurisdiction-specific treatment against an actual bill.',
                         'Paired storage, CCA generation, aggregation and meter-transfer arrangements are unsupported.']}
