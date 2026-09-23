"""Pasadena legacy flat import schedules, June/July 2026 rate-card coverage.

Source: official June electric rate card, PMC 13.04 (Ord. 7466),
4.54.020(D), 4.56.040 and 13.04.230(G). No TOU/CPP or export inference.
"""
from datetime import date
import numpy as np

VERSION = 'pwp-2026-09-20.1'
SOURCE = 'https://pwp.cityofpasadena.net/wp-content/uploads/2026/07/Summary-Rates-2026_07_updated.pdf'
PLANS = {
    'pwp_'+s.lower()+'_flat': dict(
        id='pwp_'+s.lower()+'_flat', utility='pwp', schedule=s,
        label='Pasadena '+s+' · legacy flat energy',
        customer_class='commercial' if s=='S-1' else 'residential',
        effective_start='2026-06-01', effective_end='2026-07-31',
        tariff_data_version=VERSION, source=SOURCE, demand=False,
        input_groups=['pwp'], solar_programs=['none'],
        dispatch_kind='monotone_energy_only',
        qualification_note='Confirmed legacy flat enrollment; ordinary complete monthly/bimonthly cycle. No TOU/CPP, assistance, solar or standby. S-1 demand must remain below 30 kW.',
    ) for s in ('R-1','R-2','S-1')
}
# Independent rider records; do not carry these coefficients into later cards.
RIDERS = dict(start='2026-06-01', end='2026-07-31', version_id='PWP-June2026-riders',
              pca=.05165, transmission=.01609, public_benefit=.00685,
              utility_tax=.0767, slats=.0743,
              underground=(.0434,.0370,.0247,.0121))


def eligibility(key, account, start, end):
    from .socal import number
    p=PLANS[key]; a=account
    begin,finish=date.fromisoformat(start),date.fromisoformat(end)
    if begin>finish or start<p['effective_start'] or end>p['effective_end']:
        raise ValueError('Pasadena verified flat-plan coverage is June 1–July 31, 2026; no extrapolation.')
    if not isinstance(a,dict) or a.get('customer_class')!=p['customer_class']:
        raise ValueError('Customer type does not match Pasadena schedule.')
    for field in ('eligibility_confirmed','ordinary_account_confirmed','cycle_confirmed',
                  'tax_confirmed','pwp_flat_enrollment_confirmed'):
        if a.get(field) is not True: raise ValueError('Confirm '+field.replace('_',' ')+'.')
    if not isinstance(a.get('reference'),str) or not a['reference'].strip():
        raise ValueError('Supply Pasadena account qualification reference or explicit study assumption.')
    if a.get('generation_provider')!='pwp' or a.get('solar_program')!='none':
        raise ValueError('Pasadena requires bundled PWP imports; solar/export/CCA settlement is unsupported.')
    if a.get('voltage')!='secondary' or a.get('phase') not in ('single','three'):
        raise ValueError('Only ordinary Pasadena secondary service is supported.')
    if a.get('climate_credit_amount',0): raise ValueError('SCE climate credits do not apply to Pasadena.')
    if number(a.get('local_tax_percent'),'Pasadena utility tax')!=7.67:
        raise ValueError('This scope requires ordinary Pasadena 7.67% UUT jurisdiction; exempt/outside-city accounts are unsupported.')
    factor=number(a.get('billing_month_factor'),'Billed months')
    days=(finish-begin).days+1
    if factor not in (1,2) or not 25*factor<=days<=35*factor:
        raise ValueError('Pasadena requires a confirmed complete monthly or bimonthly bill; partial-service proration is unsupported.')
    if p['schedule']=='R-2' and a.get('pwp_r2_qualification_confirmed') is not True:
        raise ValueError('R-2 requires utility-confirmed multifamily qualification (at least four meters at the same location).')
    return p


def charge_lines(key,index,imports,a,*,convex=False,constraints=None):
    if convex:
        raise ValueError('Pasadena flat import plans use the exact monotone-energy dispatch proof, not a convex approximation of declining surtax.')
    s=PLANS[key]['schedule'];factor=a['billing_month_factor']
    total=float(np.sum(imports)*.25)
    if s=='S-1' and np.max(imports)>=30:
        raise ValueError('Pasadena S-1 scope requires demand below 30 kW; larger accounts require a demand schedule.')
    residential=s!='S-1'
    energy_rate=.10825 if residential else .14186
    distribution=(.03505*min(total,350*factor)+.14018*min(max(total-350*factor,0),400*factor)
                  +.25233*max(total-750*factor,0)) if residential else .06862*total
    lines=dict(customer_charge=(11 if residential else 14.70)*factor,
               grid_access_charge=(6.50 if residential else 17)*factor,
               distribution_charge=distribution,
               base_energy_charge=(energy_rate-RIDERS['pca'])*total,
               power_cost_adjustment=RIDERS['pca']*total,
               transmission_charge=RIDERS['transmission']*total)
    subtotal=sum(lines.values())
    # PMC 4.54.020(D) excludes energy and its periodic adjustment for the
    # first 1000 kWh/month, not customer/grid/distribution/transmission charges.
    lines['street_light_traffic_signal_tax']=RIDERS['slats']*(subtotal-energy_rate*min(total,1000*factor))
    lines['local_utility_tax']=RIDERS['utility_tax']*subtotal
    monthly=subtotal/factor
    blocks=(min(monthly,1000),min(max(monthly-1000,0),4000),
            min(max(monthly-5000,0),20000),max(monthly-25000,0))
    lines['underground_surtax']=factor*sum(q*r for q,r in zip(blocks,RIDERS['underground']))
    # PMC 13.04.230(G): PBC is outside every municipal tax/surcharge base.
    lines['public_benefits_charge']=total*RIDERS['public_benefit']
    lines['state_energy_surcharge']=total*.0003
    return lines


def bill_details(key,index,imports,a,lines):
    return dict(total=sum(lines.values()),line_items=lines,usage_kWh=float(np.sum(imports)*.25),
                peak_kw=float(np.max(imports)),amount_due=sum(lines.values()),credit_balance=0.,tariff=PLANS[key],
                rate_versions=[dict(version_id=VERSION,start=str(index[0].date()),end=str(index[-1].date()),source=SOURCE)],
                adjustment_versions=[RIDERS['version_id']],
                warnings=['Pasadena legacy flat enrollment must remain valid; interval-meter TOU/CPP transition is excluded.',
                          'Complete billing cycles only; partial-service proration, assistance and special account adjustments are not modeled.',
                          'No PV/export settlement or AC network feasibility. Flat import costs increase with total energy; cycling storage cannot lower the bill under equal starting/ending SOC.'])
