"""IPU adopted Resolution 2023-01, Attachment A domestic imports.

Current official rate book, pp. 4 (adoption/effective date), 11 (D).
Only D is enabled: posted general rules bear a draft legend, and commercial
season/contract terms are not sufficiently verified to implement A/B/C.
"""
from datetime import date
import numpy as np
VERSION='ipu-2026-09-20.1'
SOURCE='https://www.cityofindustry.org/DocumentCenter/View/226/IPU-Rate-Information-PDF'
PLANS={'ipu_d':dict(id='ipu_d',utility='ipu',schedule='D',label='Industry D · Domestic',customer_class='residential',
                   effective_start='2025-01-01',effective_end='2026-09-20',tariff_data_version=VERSION,source=SOURCE,
                   demand=False,input_groups=['ipu','municipal-storage'],solar_programs=['none'],dispatch_kind='monotone_energy_only',
                   qualification_note='Bill-confirmed IPU individual domestic meter and ordinary contract. City of Industry contains multiple utility territories. A/B/C commercial terms remain unsupported.')}


def eligibility(key,a,start,end):
    from .socal import number
    begin,finish=date.fromisoformat(start),date.fromisoformat(end)
    if begin>finish or start<'2025-01-01' or end>'2026-09-20':raise ValueError('IPU verified domestic billing coverage is January 2025–September 20, 2026.')
    if not isinstance(a,dict) or a.get('customer_class')!='residential':raise ValueError('IPU D requires residential service.')
    for f in ('eligibility_confirmed','ordinary_account_confirmed','cycle_confirmed','tax_confirmed','ipu_domestic_confirmed'):
        if a.get(f) is not True:raise ValueError('Confirm '+f.replace('_',' ')+'.')
    if not isinstance(a.get('reference'),str) or not a['reference'].strip():raise ValueError('Supply IPU account/contract confirmation or explicit hypothetical assumption.')
    if a.get('generation_provider')!='ipu' or a.get('solar_program')!='none':raise ValueError('IPU ordinary bundled D imports only; no solar/export settlement.')
    if a.get('voltage')!='secondary' or a.get('phase') not in ('single','three'):raise ValueError('Ordinary secondary metered domestic scope only.')
    if a.get('accommodation') not in ('single_family','multifamily'):raise ValueError('Confirm single-family or individually metered multifamily accommodation.')
    if number(a.get('local_tax_percent'),'IPU local UUT')!=0 or a.get('climate_credit_amount',0):raise ValueError('Industry ordinary domestic scope uses no local UUT and no SCE climate credit.')
    if number(a.get('billing_month_factor'),'Billed months')!=1 or not 27<=(finish-begin).days+1<=33:raise ValueError('IPU scope requires one complete 27–33-day cycle; opening/closing and irregular bills are excluded.')
    return PLANS[key]


def charge_lines(key,index,imports,a,*,convex=False,constraints=None):
    if convex:raise ValueError('IPU flat domestic billing uses exact monotone-energy dispatch.')
    total=float(np.sum(imports)*.25)
    return dict(customer_charge=(.033 if a['accommodation']=='single_family' else .025)*len(index.normalize().unique()),
                energy_charge=.10882*total,public_purpose_programs=.00328*total,state_energy_surcharge=.0003*total)


def bill_details(key,index,imports,a,lines):
    return dict(total=sum(lines.values()),line_items=lines,usage_kWh=float(np.sum(imports)*.25),peak_kw=float(np.max(imports)),
                amount_due=sum(lines.values()),credit_balance=0.,tariff=PLANS[key],
                rate_versions=[dict(version_id='IPUC-2023-01-effective-2023-02-01',start=str(index[0].date()),end=str(index[-1].date()),source=SOURCE)],
                adjustment_versions=[],warnings=['IPU service and ordinary contract terms require account confirmation; municipal location alone does not prove IPU service.',
                'Only individual domestic D imports are supported. No commercial, master-meter, irregular-cycle, solar or standby settlement.',
                'Flat import costs and equal initial/final battery SOC make idle storage optimal; no AC network feasibility assessment.'])
