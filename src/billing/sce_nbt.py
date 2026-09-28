"""Bounded SCE bundled residential Solar Billing Plan (NBT) cycles.

This adapter keeps SCE's delivery and generation credit banks separate and
does not project an annual true-up from one billing cycle. See
docs/Southern_California.md for the verified scope and source sheets.
"""
from datetime import date
import numpy as np

from .sce_nbt_2026_data import PRICES as PRICES_2026
from .sce_nbt_historical_data import PRICES_BY_VINTAGE_YEAR

PROGRAM = 'sce_nbt'
VINTAGES = (2023, 2024, 2025, 2026)
FIRST_DAY = date(2025, 1, 1)
LAST_DAY = date(2026, 9, 17)
# TOU-D-PRIME component sheet 90942-E applies January 1–May 31; 91201-E
# cancels it June 1 and 91355-E cancels that sheet June 25 without changing
# these components. The CTC is embedded in generation; NDC, PPPC and WFC
# are embedded in delivery. NBT sheet 3 makes them nonbypassable on imports.
DELIVERY_NBC_VERSIONS = (
    (date(2025, 1, 1), date(2025, 2, 28), -.00001 + .03577 + .00595, '89283-E'),
    (date(2025, 3, 1), date(2025, 5, 31), -.00001 + .03546 + .00595, '89533-E'),
    (date(2025, 6, 1), date(2025, 9, 30), -.00001 + .03395 + .00595, '89968-E'),
    (date(2025, 10, 1), date(2025, 11, 14), -.00001 + .03565 + .00595, '90412-E'),
    (date(2025, 11, 15), date(2025, 12, 31), -.00001 + .01060 + .00595, '90674-E'),
    (date(2026, 1, 1), date(2026, 5, 31), .00003 + .00527 + .00591, '90942-E'),
    (date(2026, 6, 1), date(2026, 6, 24), .00003 + .00171 + .00591, '91201-E'),
    (date(2026, 6, 25), LAST_DAY, .00003 + .00171 + .00591, '91355-E'),
)
GENERATION_NBC_PER_KWH = .00014
GENERATION_NBC_VERSIONS = ((date(2025, 1, 1), date(2025, 12, 31), -.00058),
                           (date(2026, 1, 1), LAST_DAY, GENERATION_NBC_PER_KWH))
ACC_PLUS_NON_EQUITY = {2023: .040, 2024: .032, 2025: .024, 2026: .016}


def delivery_nbc_rates(index):
    """Return the filed delivery NBC for each local service interval."""
    dates = index.date
    rates = np.empty(len(index), dtype=float)
    covered = np.zeros(len(index), dtype=bool)
    for start, end, rate, _sheet in DELIVERY_NBC_VERSIONS:
        mask = (dates >= start) & (dates <= end)
        rates[mask] = rate
        covered |= mask
    if not len(index) or not covered.all():
        raise ValueError('Delivery NBC intervals fall outside verified SCE NBT coverage.')
    return rates


def generation_nbc_rates(index):
    dates = index.date
    rates = np.empty(len(index), dtype=float)
    covered = np.zeros(len(index), dtype=bool)
    for start, end, rate in GENERATION_NBC_VERSIONS:
        mask = (dates >= start) & (dates <= end)
        rates[mask] = rate
        covered |= mask
    if not len(index) or not covered.all():
        raise ValueError('Generation CTC intervals fall outside verified SCE NBT coverage.')
    return rates


def validate_account(key, account, start, end):
    if key != 'sce_tou-d-prime' or account.get('customer_class') != 'residential':
        raise ValueError('SCE NBT currently requires bundled residential TOU-D-PRIME.')
    if account.get('generation_provider') != 'sce' or account.get('actual_generation_provider') != 'bundled':
        raise ValueError('SCE bundled NBT cannot substitute for a CCA generation account.')
    begin, finish = date.fromisoformat(start), date.fromisoformat(end)
    if begin < FIRST_DAY or finish > LAST_DAY:
        raise ValueError(f'SCE NBT cycle coverage is {FIRST_DAY} through {LAST_DAY}.')
    try:
        vintage = int(account['nbt_vintage'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Select a verified SCE NBT23–NBT26 vintage.') from exc
    if vintage not in VINTAGES or (vintage == 2026 and begin.year != 2026):
        raise ValueError('Select the actual NBT23–NBT26 vintage applicable to this cycle.')
    try:
        request = date.fromisoformat(account['nbt_interconnection_request_date'])
        pto = date.fromisoformat(account['nbt_pto_date'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Supply the confirmed NBT interconnection-request and permission-to-operate dates.') from exc
    if not (request.year == pto.year == vintage and date(2023, 4, 15) <= request <= pto <= begin):
        raise ValueError('NBT vintage must match the confirmed application and PTO year, before the study cycle.')
    first_cycle = account.get('nbt_first_cycle_confirmed') is True
    if not first_cycle:
        if account.get('nbt_opening_balances_confirmed') is not True:
            raise ValueError('Confirm the opening delivery, generation and ACC Plus balances from this account.')
        for field in ('nbt_opening_delivery_eec', 'nbt_opening_generation_eec', 'nbt_opening_acc_plus'):
            value = account.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value < 0:
                raise ValueError('Opening NBT credit balances must be finite nonnegative dollar amounts.')
        try:
            relevant_end = date.fromisoformat(account['nbt_relevant_period_end'])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('Supply the confirmed annual NBT relevant-period end date.') from exc
        if not finish < relevant_end <= date(begin.year + 1, begin.month, begin.day):
            raise ValueError('This bounded NBT cycle must end before the annual true-up date.')
    elif any(account.get(field, 0) not in (0, 0.) for field in
             ('nbt_opening_delivery_eec', 'nbt_opening_generation_eec', 'nbt_opening_acc_plus')):
        raise ValueError('A first NBT cycle must have zero opening credit balances.')
    if account.get('nbt_bonus_status') != 'eligible_non_equity' or account.get('nbt_bonus_confirmed') is not True:
        raise ValueError('This bounded SCE NBT path requires confirmed vintage-specific non-equity ACC Plus eligibility.')
    if account.get('interconnection_confirmed') is not True:
        raise ValueError('Confirm SCE NBT interconnection and bidirectional 15-minute metering.')


def export_prices(index, vintage=2026):
    """Return delivery and SCE generation $/kWh for each Pacific-local interval."""
    from .socal import holidays
    if str(index.tz) != 'America/Los_Angeles':
        raise ValueError('SCE NBT prices require America/Los_Angeles timestamps.')
    if not len(index) or index.min().date() < FIRST_DAY or index.max().date() > LAST_DAY:
        raise ValueError('Export intervals fall outside verified SCE NBT coverage.')
    if vintage not in VINTAGES or (vintage == 2026 and index.min().year != 2026):
        raise ValueError('No verified NBT vintage prices for this service year.')
    special = set().union(*(holidays(year) for year in set(index.year)))
    weekend_or_holiday = (index.dayofweek >= 5) | np.isin(index.date, list(special))
    row = np.array([(PRICES_2026 if vintage == 2026 else PRICES_BY_VINTAGE_YEAR[vintage, y])[m - 1][h]
                    for y, m, h in zip(index.year, index.month, index.hour)], dtype=float)
    cols = np.where(weekend_or_holiday, 1, 0)
    return row[np.arange(len(index)), cols], row[np.arange(len(index)), cols + 2]


def settlement(import_lines, imports, exports, index, account=None, *, convex=False):
    """SCE cycle amount due and separate earned/applied EEC components.

    The shared import-charge expression already includes confirmed local-tax
    study assumptions. Export credits are applied after that calculation and
    cannot offset its tax or state surcharge. ACC Plus offsets the remaining
    tariff charges, including the base service charge and NBCs.
    """
    import cvxpy as cp
    account = account or {'nbt_vintage': '2026', 'nbt_first_cycle_confirmed': True}
    vintage = int(account['nbt_vintage'])
    opening_delivery = 0. if account.get('nbt_first_cycle_confirmed') else account['nbt_opening_delivery_eec']
    opening_generation = 0. if account.get('nbt_first_cycle_confirmed') else account['nbt_opening_generation_eec']
    opening_bonus = 0. if account.get('nbt_first_cycle_confirmed') else account['nbt_opening_acc_plus']
    sum_ = cp.sum if convex else np.sum
    maximum = cp.maximum if convex else np.maximum
    total_import = sum_(imports) * .25
    delivery_price, generation_price = export_prices(index, vintage)
    earned_delivery = sum_(cp.multiply(exports, delivery_price) if convex else exports * delivery_price) * .25
    earned_generation = sum_(cp.multiply(exports, generation_price) if convex else exports * generation_price) * .25
    bonus = sum_(exports) * (.25 * ACC_PLUS_NON_EQUITY[vintage])
    nbc_rates = delivery_nbc_rates(index)
    nbc_delivery = sum_(cp.multiply(imports, nbc_rates) if convex else imports * nbc_rates) * .25
    ctc_rates = generation_nbc_rates(index)
    nbc_generation = sum_(cp.multiply(imports, ctc_rates) if convex else imports * ctc_rates) * .25
    eligible_delivery = import_lines['energy_charge'] - nbc_delivery
    eligible_generation = import_lines['generation_charge'] - nbc_generation
    protected = nbc_delivery + nbc_generation + import_lines['fixed_recovery_charge'] + import_lines['fixed_charge']
    after_eec = maximum(eligible_delivery - earned_delivery - opening_delivery, 0) + maximum(eligible_generation - earned_generation - opening_generation, 0) + protected
    tariff_due = maximum(after_eec - bonus - opening_bonus, 0)
    due = tariff_due + import_lines['local_utility_tax'] + import_lines['state_energy_surcharge'] + import_lines['climate_credit']
    if convex:
        return due
    earned_delivery, earned_generation, bonus = map(float, (earned_delivery, earned_generation, bonus))
    used_delivery = min(float(eligible_delivery), earned_delivery + opening_delivery)
    used_generation = min(float(eligible_generation), earned_generation + opening_generation)
    used_bonus = min(float(after_eec), bonus + opening_bonus)
    return float(due), {
        'opening_delivery_eec': float(opening_delivery),
        'earned_delivery_eec': earned_delivery,
        'applied_delivery_eec': used_delivery,
        'closing_delivery_eec': earned_delivery + opening_delivery - used_delivery,
        'opening_generation_eec': float(opening_generation),
        'earned_generation_eec': earned_generation,
        'applied_generation_eec': used_generation,
        'closing_generation_eec': earned_generation + opening_generation - used_generation,
        'opening_acc_plus': float(opening_bonus),
        'earned_acc_plus': bonus,
        'applied_acc_plus': used_bonus,
        'closing_acc_plus': bonus + opening_bonus - used_bonus,
        'nonbypassable_delivery_charge': float(nbc_delivery),
        'nonbypassable_generation_charge': float(nbc_generation),
        'nonbypassable_import_charge': float(nbc_delivery + nbc_generation),
    }


def bill(key, index, imports, exports, account, plan):
    from .socal import charge_lines, version_details, RESIDENTIAL_PLANS
    if not np.isfinite(exports).all() or (exports < 0).any():
        raise ValueError('SCE NBT exports must be nonnegative finite kW.')
    if np.max(np.minimum(imports, exports)) > 1e-7:
        raise ValueError('SCE NBT cannot import and export simultaneously at the same meter.')
    lines = {k: float(v) for k, v in charge_lines(key, index, imports, account).items()}
    total, ledger = settlement(lines, imports, exports, index, account)
    lines.update({'delivery_eec_applied': -ledger['applied_delivery_eec'],
                  'generation_eec_applied': -ledger['applied_generation_eec'],
                  'acc_plus_applied': -ledger['applied_acc_plus']})
    if abs(sum(lines.values()) - total) > 1e-7:
        raise ValueError('SCE NBT line items do not reconcile to the amount due.')
    details = version_details(RESIDENTIAL_PLANS[key], key, index, account)
    return {'total': total, 'line_items': lines, 'usage_kWh': float(np.sum(imports) * .25),
            'export_kWh': float(np.sum(exports) * .25), 'peak_kw': float(np.max(imports)),
            'amount_due': max(0., total), 'credit_balance': max(0., -total),
            'credit_ledger': ledger, 'rate_versions': details, 'tariff': plan,
            'adjustment_versions': [d['version_id'] for d in details],
            'warnings': ['SCE NBT one confirmed billing cycle only: account opening EEC and ACC Plus balances are inputs; annual true-up and NSC are not projected.',
                         'Dispatch minimizes this cycle’s amount due; it does not assign future value to unused export-credit balances, so it is not a full-year optimum.',
                         'SCE bundled delivery and generation credits have separate banks. Ordinary EEC cannot offset NBCs, base services, fixed recovery, taxes or state surcharge.',
                         'Paired storage, if modeled, charges only from surplus PV and does not export battery energy or model SCE paired-storage export caps.',
                         'Local utility tax uses the existing confirmed/assumed study rate on import charges before export credits; jurisdiction-specific solar tax treatment is not modeled.',
                         'PV production and operating savings exclude capital costs, incentives and AC network feasibility.']}
