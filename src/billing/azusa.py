"""Azusa ordinary D/G-1 imports; 2025/2026 independently dated filed-book coverage.

Rates: official January 1, 2025 Rules and Regulations, schedules D, G,
PCA and PBC. Complete monthly cycles only (Rule 8).
"""
from datetime import date
import numpy as np

VERSION='alw-2026-09-20.1'
SOURCE='https://azusaca.gov/DocumentCenter/View/48871/Rules-and-Regulations-01-1-2025'
SOURCES = {2025: SOURCE, 2026: 'https://www.azusaca.gov/DocumentCenter/View/49491/Rules-and-Regulations-01-1-2026',
           '2026H2': 'https://www.azusaca.gov/DocumentCenter/View/50568/Rules-and-Regulations-6-1-2026'}
BASE_VERSION=dict(start='2025-01-01',end='2026-09-20',version_id='ALW-UB-01-2018-verified-2026-09-20')
PCA_VERSIONS=[dict(start='2025-01-01',end='2025-06-30',rate=.06137,version_id='ALW-PCA-2025H1',source=SOURCE),
              dict(start='2026-01-01',end='2026-06-30',rate=.05000,version_id='ALW-PCA-2026H1',source=SOURCES[2026]),
              dict(start='2026-07-01',end='2026-12-31',rate=.05000,version_id='ALW-PCA-2026H2',source=SOURCES['2026H2'])]
PBC_VERSIONS=[dict(start='2024-07-01',end='2025-06-30',rate=.00591,version_id='ALW-PBC-FY2025',source=SOURCE),
              dict(start='2025-07-01',end='2026-06-30',rate=.00528,version_id='ALW-PBC-FY2026',source=SOURCES[2026]),
              dict(start='2026-07-01',end='2027-06-30',rate=.00536,version_id='ALW-PBC-FY2027',source=SOURCES['2026H2'])]


def riders(start,end):
    selected=[]
    for versions in (PCA_VERSIONS,PBC_VERSIONS):
        matches=[v for v in versions if v['start']<=start<=end<=v['end']]
        if len(matches)!=1:raise ValueError('Azusa rider coverage missing or cycle crosses a rider change; use complete cycles within a verified rider window. July–December 2025 PCA is not loaded.')
        selected.append(matches[0])
    return selected

PLANS={
    'alw_'+s.lower():dict(id='alw_'+s.lower(),utility='alw',schedule=s,label='Azusa '+s,
        customer_class='residential' if s=='D' else 'commercial',
        effective_start='2025-01-01',effective_end='2026-09-20',tariff_data_version=VERSION,
        coverage_windows=[dict(start='2025-01-01',end='2025-06-30',version_id='ALW-2025H1'),dict(start='2026-01-01',end='2026-06-30',version_id='ALW-2026H1'),dict(start='2026-07-01',end='2026-09-20',version_id='ALW-2026H2')],
        source=SOURCE,demand=False,input_groups=['alw'],solar_programs=['none'],
        dispatch_kind='monotone_energy_only',
        qualification_note='Verified windows: Jan–Jun 2025 and Jan–Sep 20, 2026; cycles crossing rider changes are unsupported. Ordinary D or non-demand-metered G-1, complete monthly cycle only. WH/SH, RL, AMI opt-out, G-2/GL/TOU and special riders excluded.')
    for s in ('D','G-1')
}


def eligibility(key,a,start,end):
    from .socal import number
    p=PLANS[key];begin,finish=date.fromisoformat(start),date.fromisoformat(end)
    riders(start,end)
    for v in (BASE_VERSION,):
        if begin>finish or start<v['start'] or end>v['end']:
            raise ValueError('Azusa verified coverage ends September 20, 2026; missing rider dates cannot be extrapolated.')
    if not isinstance(a,dict) or a.get('customer_class')!=p['customer_class']:
        raise ValueError('Customer type does not match Azusa schedule.')
    for field in ('eligibility_confirmed','ordinary_account_confirmed','cycle_confirmed','tax_confirmed','alw_ordinary_meter_confirmed'):
        if a.get(field) is not True:raise ValueError('Confirm '+field.replace('_',' ')+'.')
    if not isinstance(a.get('reference'),str) or not a['reference'].strip():raise ValueError('Supply Azusa qualification reference or explicit study assumption.')
    if a.get('generation_provider')!='alw' or a.get('solar_program')!='none':raise ValueError('Azusa ordinary import plans require bundled generation and no PV/export settlement.')
    if a.get('voltage')!='secondary' or a.get('phase') not in ('single','three'):raise ValueError('Azusa ordinary secondary service only.')
    if a.get('climate_credit_amount',0):raise ValueError('SCE climate credits do not apply to Azusa.')
    tax=number(a.get('local_tax_percent'),'Azusa tax')
    if tax not in (0.,4. if p['customer_class']=='residential' else 8.):raise ValueError('Confirm Azusa residential 4%, commercial 8%, or documented 0% utility-user tax.')
    if number(a.get('billing_month_factor'),'Billed months')!=1 or not 25<=(finish-begin).days+1<=35:
        raise ValueError('Azusa requires a complete 25–35-day monthly cycle; partial-service proration is not implemented.')
    return p


def charge_lines(key,index,imports,a,*,convex=False,constraints=None):
    if convex:raise ValueError('Azusa D/G-1 use exact monotone-energy dispatch; do not convexify declining G-1 tiers.')
    pca,pbc=riders(str(index[0].date()),str(index[-1].date()))
    total=float(np.sum(imports)*.25)
    if PLANS[key]['schedule']=='D':
        energy=.1091*min(total,250)+.1487*max(total-250,0)
        fixed=0.;minimum=max(5.80-energy,0.)
    else:
        if np.max(imports)>20:raise ValueError('Azusa G-1 study exceeds 20 kW; confirm demand-meter assignment and use G-2 when applicable.')
        energy=.1650*min(total,500)+.1430*max(total-500,0)
        fixed=10.;minimum=0.
    lines=dict(energy_charge=energy,customer_charge=fixed,minimum_charge_adjustment=minimum,
               power_cost_adjustment=total*pca['rate'],public_benefits_charge=total*pbc['rate'])
    lines['local_utility_tax']=sum(lines.values())*a['local_tax_percent']/100
    lines['state_energy_surcharge']=total*.0003
    return lines


def bill_details(key,index,imports,a,lines):
    return dict(total=sum(lines.values()),line_items=lines,usage_kWh=float(np.sum(imports)*.25),
                peak_kw=float(np.max(imports)),amount_due=sum(lines.values()),credit_balance=0.,tariff=PLANS[key],
                rate_versions=[dict(version_id=BASE_VERSION['version_id'],start=str(index[0].date()),end=str(index[-1].date()),source=SOURCE)],
                adjustment_versions=[v['version_id'] for v in riders(str(index[0].date()),str(index[-1].date()))],
                warnings=['Azusa ordinary monthly D/G-1 import scope excludes assistance, heating allowances, AMI opt-out, standby and demand-metered service.',
                          'Partial-service proration and export settlement are not modeled. Tax jurisdiction is account-confirmed.',
                          'Flat import costs increase with energy; equal starting/ending SOC makes idle storage optimal. No AC network feasibility assessment.'])
