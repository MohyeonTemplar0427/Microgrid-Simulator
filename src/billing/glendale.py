"""GWP ordinary import billing. Source ledger: docs/LA_County_Utilities.md.

Numerical bills and dispatch use the same expressions. Base-rate and rider
windows are independent; neither is extended beyond verified coverage.
"""
from datetime import date

import numpy as np
import pandas as pd

VERSION = 'gwp-2026-09-19.1'
SOURCE = 'https://glendaleca.primegov.com/Portal/Meeting?meetingTemplateId=39969'
# Ordinance 6042, Exhibit A. Tuples: customer/day, high energy, low energy,
# high demand/kW/day, low demand/kW/day. TOU tuples are base, peak.
BASE_VERSIONS = (
    ('2025-01-01', '2025-10-31', 'GWP-6025-phase2', {
        'L-1-A': (.75, (.2883, .3549, .4238), (.2401, .2973, .3688), 0, 0),
        'L-1-B': (.75, (.2141, .6423), (.1785, .5353), 0, 0),
        'L-2-A': (1., (.2993,), (.2593,), 0, 0),
        'L-2-B': (1., (.1899, .5695), (.1460, .4380), 0, 0),
        'LD-2-A': (1.5, (.1583,), (.1514,), 1.08, .75),
    }),
    ('2025-11-01', '2026-09-19', 'GWP-6042-phase3', {
        'L-1-A': (.75, (.3071, .3806, .4547), (.2575, .3189, .3935), 0, 0),
        'L-1-B': (.75, (.2280, .6839), (.1901, .5700), 0, 0),
        'L-2-A': (1.15, (.3118,), (.2701,), 0, 0),
        'L-2-B': (1.15, (.1996, .5985), (.1535, .4604), 0, 0),
        'LD-2-A': (1.6, (.1645,), (.1573,), 1.10, .77),
    }),
)
ADJUSTMENT_VERSIONS = (
    ('2025-01-01', '2026-09-19', 'GWP-zero-ECAC-RAC-RDC-and-24-163',
     {'ECAC': 0., 'RAC': 0., 'RDC': 0., 'public_benefits_fraction': .0285}),
)
PLANS = {
    'gwp_' + schedule.lower(): dict(
        id='gwp_' + schedule.lower(), utility='gwp', schedule=schedule,
        label='Glendale ' + schedule, customer_class='residential' if schedule.startswith('L-1') else 'commercial',
        effective_start='2025-01-01', effective_end='2026-09-19',
        tariff_data_version=VERSION, source=SOURCE, demand=schedule.startswith('LD'),
        input_groups=['gwp'] + (['gwp-demand'] if schedule.startswith('LD') else []),
        qualification_note='Utility-assigned ordinary import schedule; individually metered residential only. Solar/standby and assistance unsupported. Confirm complete cycle and tax jurisdiction.',
        coverage_windows=[dict(start=s, end=e, version_id=v) for s, e, v, _ in BASE_VERSIONS],
        solar_programs=['none'],
    ) for schedule in BASE_VERSIONS[0][3]
}


def require_coverage(versions, start, end):
    remaining = pd.date_range(start, end, freq='D')
    for begin, finish, _, _ in versions:
        remaining = remaining[(remaining < begin) | (remaining > finish)]
    if len(remaining):
        raise ValueError(f'GWP verified coverage unavailable on {remaining[0].date()}; no rate extrapolation.')


def eligibility(key, account, start, end):
    from .socal import number
    p = PLANS[key]
    begin, finish = date.fromisoformat(start), date.fromisoformat(end)
    if not 0 <= (finish - begin).days <= 69:
        raise ValueError('GWP requires one confirmed monthly/bimonthly cycle of at most 70 days.')
    require_coverage(BASE_VERSIONS, start, end)
    require_coverage(ADJUSTMENT_VERSIONS, start, end)
    a = account
    if not isinstance(a, dict) or a.get('customer_class') != p['customer_class']:
        raise ValueError('Customer type does not match GWP schedule.')
    for field in ('eligibility_confirmed', 'cycle_confirmed', 'ordinary_account_confirmed', 'tax_confirmed'):
        if a.get(field) is not True:
            raise ValueError('Confirm ' + field.replace('_', ' ') + ' for GWP.')
    if not isinstance(a.get('reference'), str) or not a['reference'].strip():
        raise ValueError('Supply GWP bill/utility qualification reference or hypothetical assumption.')
    if a.get('generation_provider') != 'gwp':
        raise ValueError('GWP plans require GWP bundled generation; CCA pairing is unsupported.')
    if a.get('solar_program') != 'none':
        raise ValueError('GWP customer-generation and standby schedules require separate settlement; solar is unsupported.')
    if a.get('voltage') != 'secondary' or a.get('phase') not in ('single', 'three'):
        raise ValueError('GWP implementation covers ordinary secondary service only.')
    if a.get('climate_credit_amount', 0):
        raise ValueError('SCE climate credits cannot be applied to GWP.')
    if a.get('gwp_individual_meter_confirmed') is not True and p['customer_class'] == 'residential':
        raise ValueError('Confirm individually metered GWP residence; master meters are unsupported.')
    if a.get('gwp_allocation_confirmed') is not True:
        raise ValueError('Confirm GWP daily tier allocation across season/rate changes is a study approximation.')
    tax = number(a.get('local_tax_percent'), 'GWP local tax', 0, 7)
    if tax not in (0., 7.):
        raise ValueError('GWP supports confirmed Glendale 7% tax or confirmed exempt/outside-city 0% only.')
    if p['demand']:
        number(a.get('gwp_historical_peak_floor_kw'), 'GWP historical billed-demand floor')
        if a.get('gwp_demand_history_confirmed') is not True:
            raise ValueError('Confirm the applicable trailing-12-month demand floor and ordinary 15-minute demand measurement.')
        if (finish-begin).days > 39:
            raise ValueError('GWP demand studies require one monthly cycle, at most 40 days; split longer periods.')
    return p


def peak_mask(index):
    """GMC 13.44.015 explicitly references holidays in 3.08.010(A)."""
    holidays = set()
    for year in set(index.year):
        holidays.update(date(year, m, d) for m, d in ((1, 1), (7, 4), (11, 11), (12, 25)))
        for month, weekday, nth in ((1, 0, 3), (2, 0, 3), (5, 0, -1), (9, 0, 1), (11, 3, 4), (11, 4, 4)):
            ds = [d.date() for d in pd.date_range(f'{year}-{month:02}-01', periods=31)
                  if d.month == month and d.weekday() == weekday]
            # Thanksgiving Friday is the day AFTER fourth Thursday, not always fourth Friday.
            if month == 11 and weekday == 4:
                continue
            chosen = ds[nth-1] if nth > 0 else ds[-1]
            holidays.add(chosen)
            if month == 11:
                holidays.add((pd.Timestamp(chosen)+pd.DateOffset(days=1)).date())
    high = np.isin(index.month, (7, 8, 9, 10))
    hour = index.hour + index.minute / 60
    return (index.dayofweek < 5) & ~np.isin(index.date, list(holidays)) & (hour >= np.where(high, 14, 12)) & (hour < np.where(high, 20, 21))


def charge_lines(key, index, imports, account, *, convex=False, constraints=None):
    import cvxpy as cp
    s = PLANS[key]['schedule']
    sum_ = cp.sum if convex else np.sum
    maximum = cp.maximum if convex else np.maximum
    total = sum_(imports) * .25
    high = np.isin(index.month, (7, 8, 9, 10))
    peak = peak_mask(index)
    lines = dict(energy_charge=0., fixed_charge=0., facilities_demand=0.)
    dates = index.strftime('%Y-%m-%d')
    for begin, finish, _, data in BASE_VERSIONS:
        version = (dates >= begin) & (dates <= finish)
        customer, high_rates, low_rates, high_demand, low_demand = data[s]
        for hot, rates, demand in ((True, high_rates, high_demand), (False, low_rates, low_demand)):
            mask = version & (high == hot)
            if not mask.any():
                continue
            days = len(index[mask].normalize().unique())
            energy = sum_(imports[mask]) * .25
            lines['fixed_charge'] += days * customer
            if s == 'L-1-A':
                cap = 10 * days
                lines['energy_charge'] += rates[0]*energy + (rates[1]-rates[0])*maximum(energy-cap, 0) + (rates[2]-rates[1])*maximum(energy-2*cap, 0)
            elif s.endswith('-B'):
                lines['energy_charge'] += rates[0]*energy + (rates[1]-rates[0])*sum_(imports[mask & peak])*.25
            else:
                lines['energy_charge'] += rates[0]*energy
            if demand:
                measured = cp.max(imports) if convex else float(np.max(imports))
                lines['facilities_demand'] += days*demand*maximum(measured, account['gwp_historical_peak_floor_kw'])
    for begin, finish, _, rates in ADJUSTMENT_VERSIONS:
        mask = (dates >= begin) & (dates <= finish)
        for name in ('ECAC', 'RAC', 'RDC'):
            lines[name] = lines.get(name, 0.) + sum_(imports[mask])*.25*rates[name]
    # Percentage riders apply to service charges, not just interval energy.
    # A future mid-cycle percentage change needs a verified allocation rule.
    fractions = {r['public_benefits_fraction'] for begin, finish, _, r in ADJUSTMENT_VERSIONS
                 if ((dates >= begin) & (dates <= finish)).any()}
    if len(fractions) != 1:
        raise ValueError('GWP public-benefit percentage transition requires a verified charge-allocation rule.')
    lines['public_benefits_charge'] = sum(lines.values())*next(iter(fractions))
    lines['local_utility_tax'] = sum(lines.values())*account['local_tax_percent']/100
    lines['state_energy_surcharge'] = total*.0003
    return lines


def version_details(index):
    dates = index.strftime('%Y-%m-%d')
    return [dict(version_id=v, start=max(begin, dates.min()), end=min(end, dates.max()), source=SOURCE)
            for begin, end, v, _ in BASE_VERSIONS if ((dates >= begin) & (dates <= end)).any()]
