"""Bounded SDG&E residential imports and separately confirmed CCA generation.

The same expressions price the reported bill and convex battery dispatch.
No solar settlement, inferred account vintage, tax jurisdiction, or historical
extrapolation. See docs/San_Diego.md for source evidence and study allocations.
"""
from dataclasses import dataclass
from datetime import date

import numpy as np

from .plans import RatePlan, RatePlanIdentity
from .san_diego_data import SDGE, SDCP, CEA

VERSION = 'san-diego-2026-10-11.1'
START, END = '2026-06-01', '2026-10-11'
SOURCE = 'https://www.sdge.com/total-electric-rates'
PROVIDERS = {
    'bundled': {'label':'SDG&E bundled generation', 'options':[]},
    'sdcp': {'label':'San Diego Community Power', 'options':['poweron','powerbase','power100'],
             'cohorts':[2021,2022], 'effective_start':'2026-05-01'},
    'cea': {'label':'Clean Energy Alliance', 'options':['cleanimpact','cleanimpactplus','greenimpact'],
            'effective_start':'2026-06-01'},
}


@dataclass(frozen=True)
class RateVersion:
    tariff_id: str
    effective_start: date
    effective_end: date
    data: dict

    def is_effective_on(self, service_date):
        return self.effective_start <= service_date <= self.effective_end


RATE_PLANS = {
    'sdge_' + s.lower(): RatePlan(RatePlanIdentity('sdge', s, 'account_selected', 'residential'),
        tuple(RateVersion(f'sdge-{s}-{v["start"]}', date.fromisoformat(v['start']),
                          date.fromisoformat(v['end']), v) for v in versions))
    for s, versions in SDGE.items()
}
PLANS = {
    key: dict(id=key, utility='sdge', schedule=plan.identity.schedule,
        label='SDG&E ' + plan.identity.schedule, customer_class='residential',
        effective_start=START, effective_end=END, tariff_data_version=VERSION,
        source=SOURCE, demand=False, input_groups=['sdge'],
        solar_programs=['none','approved_non_export'],
        generation_providers=list(PROVIDERS),
        coverage_windows=[dict(start=v.effective_start.isoformat(), end=v.effective_end.isoformat(),
                               version_id=v.tariff_id) for v in plan.versions],
        qualification_note='Confirmed ordinary non-CPP/non-RYU secondary account. Baseline quantity, CCA option/cohort and PCIA vintage require account confirmation. CCA City of San Diego fee ordering and nonzero local UUT are not yet supported.')
    for key, plan in RATE_PLANS.items()
}


def periods(index, schedule):
    from .socal import holidays
    hour = index.hour + index.minute / 60
    peak = (hour >= 16) & (hour < 21)
    if schedule == 'TOU-DR2':
        return np.where(peak, 'on', 'off')
    special = set().union(*(holidays(y) for y in set(index.year)))
    weekend = (index.dayofweek >= 5) | np.isin(index.date, list(special))
    super_off = (hour < 6) | ((hour >= 10) & (hour < 14)) | (weekend & (hour < 14))
    return np.where(peak, 'on', np.where(super_off, 'super', 'off'))


def eligibility(key, a, start, end):
    from .socal import number
    begin, finish = date.fromisoformat(start), date.fromisoformat(end)
    if begin > finish:
        raise ValueError('Start date must precede end date.')
    RATE_PLANS[key].require_coverage(begin, finish)
    if (finish - begin).days + 1 > 40:
        raise ValueError('SDG&E studies cover one confirmed billing cycle, at most 40 days.')
    if not isinstance(a, dict) or a.get('customer_class') != 'residential':
        raise ValueError('SDG&E currently supports residential accounts only.')
    for field in ('eligibility_confirmed','ordinary_account_confirmed','cycle_confirmed',
                  'tax_confirmed','sdge_jurisdiction_confirmed','sdge_non_event_confirmed'):
        if a.get(field) is not True:
            raise ValueError('Confirm ' + field.replace('_',' ') + '.')
    if not isinstance(a.get('reference'), str) or not a['reference'].strip():
        raise ValueError('Supply bill/utility confirmation or explicit hypothetical assumptions.')
    if a.get('generation_provider') != 'sdge':
        raise ValueError('SDG&E delivery is required; confirm generation separately.')
    if any(a.get(x) for x in ('care','fera','medical_baseline','cpp','reduce_your_use','direct_access','master_meter')):
        raise ValueError('SDG&E assistance, event, direct-access and master-meter riders are outside verified scope.')
    provider = a.get('actual_generation_provider')
    if provider not in PROVIDERS:
        raise ValueError('Confirm SDG&E bundled, SDCP, or CEA generation; no fallback is applied.')
    if a.get('voltage') != 'secondary' or a.get('phase') not in ('single','three'):
        raise ValueError('Ordinary individually metered secondary service only.')
    if a.get('solar_program') not in ('none','approved_non_export'):
        raise ValueError('SDG&E/CCA solar export settlement is not implemented.')
    if a['solar_program'] == 'approved_non_export' and a.get('interconnection_confirmed') is not True:
        raise ValueError('Confirm approved non-export interconnection and standby exemption.')
    if type(a.get('sdge_city_san_diego')) is not bool:
        raise ValueError('Confirm whether this account lies inside City of San Diego limits.')
    if provider != 'bundled' and a['sdge_city_san_diego']:
        raise ValueError('CCA City of San Diego franchise-fee ordering is not yet reconciled; this account is outside verified scope.')
    if number(a.get('local_tax_percent'),'Confirmed local utility tax',0,20) != 0:
        raise ValueError('SDG&E currently requires confirmed zero local UUT; other jurisdictions need verified tax bases.')
    credit = number(a.get('climate_credit_amount',0),'Bill-confirmed climate credit',0,1000)
    if credit and a.get('climate_credit_confirmed') is not True:
        raise ValueError('A climate credit requires explicit confirmation from this billing statement.')
    if PLANS[key]['schedule'] != 'EV-TOU-5':
        number(a.get('sdge_baseline_kwh'),'Confirmed cycle baseline allowance in kWh',0,100000)
        if a.get('sdge_baseline_confirmed') is not True:
            raise ValueError('Confirm baseline allowance for these exact cycle dates; location alone is insufficient.')
        if a.get('sdge_allocation_confirmed') is not True:
            raise ValueError('Acknowledge baseline day allocation across rate changes as a study approximation.')
    elif a.get('sdge_ev_confirmed') is not True:
        raise ValueError('EV-TOU-5 requires confirmed eligible EV enrollment in this import-only scope.')
    if provider != 'bundled':
        vintage = a.get('sdge_pcia_vintage')
        if type(vintage) is not int or not 2009 <= vintage <= 2026 or a.get('sdge_pcia_confirmed') is not True:
            raise ValueError('Confirm the account PCIA vintage; do not infer it from location or study year.')
        if a.get('sdge_generation_option') not in PROVIDERS[provider]['options']:
            raise ValueError('Confirm the selected CCA generation service option.')
        if a.get('sdge_generation_confirmed') is not True:
            raise ValueError('Confirm the CCA option and, for SDCP, published rate cohort from the account.')
        if provider == 'sdcp' and (type(a.get('sdge_sdcp_cohort')) is not int or a['sdge_sdcp_cohort'] not in SDCP):
            raise ValueError('Confirm SDCP 2021 or 2022 rate cohort separately from the PCIA vintage.')
    return PLANS[key]


def charge_lines(key, index, imports, a, *, convex=False, constraints=None):
    import cvxpy as cp
    RATE_PLANS[key].require_coverage(index[0].date(), index[-1].date())
    schedule = PLANS[key]['schedule']
    provider = a['actual_generation_provider']
    total = .25 * (cp.sum(imports) if convex else np.sum(imports))
    def cost(mask, prices):
        return .25 * (cp.sum(cp.multiply(imports[mask], prices)) if convex else np.sum(imports[mask] * prices))
    band = periods(index, schedule)
    season = np.where(np.isin(index.month, [6,7,8,9,10]), 'summer_', 'winter_')
    slots = np.char.add(season, band)
    lines = {k:0. for k in ('energy_charge','wildfire_fund_charge','generation_charge',
              'generation_premium','generation_relief_credit','baseline_credit','fixed_charge','pcia','mcam')}
    imputed_generation = 0.
    days = len(index.normalize().unique())
    for version in RATE_PLANS[key].versions:
        mask = (index.date >= version.effective_start) & (index.date <= version.effective_end)
        if not mask.any():
            continue
        v = version.data
        rates = np.array([v['rates'][x] for x in slots[mask]])
        lines['energy_charge'] += cost(mask, rates[:,0])
        lines['wildfire_fund_charge'] += cost(mask, rates[:,1])
        imputed_generation += cost(mask, rates[:,2])
        subdays = len(index[mask].normalize().unique())
        lines['fixed_charge'] += subdays * v['daily_fixed']
        kwh = .25 * (cp.sum(imports[mask]) if convex else np.sum(imports[mask]))
        if schedule != 'EV-TOU-5':
            cap = 1.3 * a['sdge_baseline_kwh'] * subdays / days
            # -credit * min(kWh, allowance) is convex, with no binary variables.
            pos = cp.pos if convex else lambda x: max(x, 0.)
            lines['baseline_credit'] += v['baseline_credit'] * (pos(kwh-cap)-kwh)
        if provider != 'bundled':
            lines['pcia'] += kwh * v['pcia'][a['sdge_pcia_vintage']]
    if provider == 'bundled':
        lines['generation_charge'] = imputed_generation
    else:
        option = a['sdge_generation_option']
        if provider == 'sdcp':
            table = SDCP[a['sdge_sdcp_cohort']]['rates'][schedule]
            column = 1 if option == 'powerbase' else 0
            prices = np.array([table[x][column] for x in slots])
            lines['generation_premium'] = total * (.01 if option == 'power100' else 0.)
        else:
            prices = np.array([CEA['rates'][schedule][x] for x in slots])
            lines['generation_premium'] = total * {'cleanimpact':0.,'cleanimpactplus':.001,'greenimpact':.0075}[option]
            lines['generation_relief_credit'] = -total * (.03871 if option == 'cleanimpact' else 0.)
            lines['mcam'] = total * .00006
        lines['generation_charge'] = cost(np.ones(len(index), dtype=bool), prices)
    # The ordinary 1.1% SDG&E franchise fee is embedded in UDC/EECC.
    # CCA FFE uses imputed SDG&E generation, not the customer's CCA price.
    lines['franchise_fee_equivalent'] = .011 * (lines['wildfire_fund_charge'] + (imputed_generation if provider != 'bundled' else 0.))
    city_base = lines['energy_charge'] + lines['baseline_credit'] + lines['fixed_charge'] + lines['wildfire_fund_charge'] + lines['generation_charge']
    lines['city_franchise_differential'] = .0578 * city_base if a['sdge_city_san_diego'] else 0.
    lines['state_regulatory_fee'] = .001 * total
    # Collected once, on the generation provider's portion of the combined bill.
    lines['state_energy_surcharge'] = .0003 * total
    lines['climate_credit'] = -a.get('climate_credit_amount',0.)
    return lines


def bill_details(key, index, imports, a, lines):
    provider = a['actual_generation_provider']
    details = []
    for v in RATE_PLANS[key].versions:
        mask = (index.date >= v.effective_start) & (index.date <= v.effective_end)
        if mask.any():
            details.append(dict(version_id=v.tariff_id, component='SDG&E delivery/bundled generation/PCIA',
                effective_start=v.effective_start.isoformat(),effective_end=v.effective_end.isoformat(),
                service_start=index[mask][0].date().isoformat(),service_end=index[mask][-1].date().isoformat(),
                **v.data['source']))
    if provider != 'bundled':
        source = SDCP[a['sdge_sdcp_cohort']]['source'] if provider == 'sdcp' else CEA['source']
        details.append(dict(version_id=f'{provider}-{PROVIDERS[provider]["effective_start"]}',
            component='CCA generation',effective_start=PROVIDERS[provider]['effective_start'],effective_end=END,
            service_start=index[0].date().isoformat(),service_end=index[-1].date().isoformat(),**source))
    amount = float(sum(lines.values()))
    warnings = ['One confirmed billing cycle; ordinary secondary import service only. Solar export, event tariffs, assistance discounts and nonzero local UUT are not priced.',
                'Location suggests providers; actual delivery, generation, baseline and PCIA vintage require account confirmation.',
                'No hourly load shape or tariff-switch eligibility is inferred from a monthly bill. No AC network feasibility or capital cost is modeled.',
                'Climate credit is applied once only when explicitly confirmed on this bill; other account adjustments are excluded.']
    if PLANS[key]['schedule'] != 'EV-TOU-5':
        warnings.append('The supplied baseline quantity belongs to these exact cycle dates. Across dated rates it is allocated by service days; this is an acknowledged study approximation.')
    return dict(total=amount,line_items=lines,usage_kWh=float(imports.sum()*.25),peak_kw=float(imports.max()),
        amount_due=max(0.,amount),credit_balance=max(0.,-amount),tariff=PLANS[key],
        rate_versions=details,adjustment_versions=[v['version_id'] for v in details],warnings=warnings)
