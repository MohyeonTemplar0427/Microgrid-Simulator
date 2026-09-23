"""BWP ordinary non-demand imports, adopted FY2026–27 fee schedule.

Separate energy, ECAC, in-lieu transfer and UUT. The official sample bill
confirms both 7% amounts use the pre-tax service subtotal (no tax-on-tax).
"""
from datetime import date, timedelta
import numpy as np
import pandas as pd

VERSION='bwp-2026-09-20.1'
SOURCE='https://www.burbankwaterandpower.com/documents/d/guest/burbank_adopted_fee_schedule'
START='2026-07-01';END='2026-09-20'
PLANS={
    key:dict(id=key,utility='bwp',schedule=s,label='Burbank '+label,
             customer_class=customer,effective_start=START,effective_end=END,
             tariff_data_version=VERSION,source=SOURCE,demand=False,
             input_groups=['bwp','municipal-storage'],solar_programs=['none'],
             qualification_note='Ordinary complete monthly cycle, published $0.034/kWh ECAC confirmed for the cycle. No assistance, green premium, meter opt-out, demand-metered or standby service.')
    for key,s,label,customer in [('bwp_basic','Basic','Residential Basic','residential'),
                               ('bwp_ev','EV','Residential EV TOU','residential'),
                               ('bwp_c','C','C · Small General Service','commercial')]
}


def holidays(year):
    result={date(year,1,1),date(year,3,31),date(year,6,19),date(year,7,4),date(year,11,11),date(year,12,25)}
    for month,ordinal,weekday in [(1,3,0),(2,3,0),(5,-1,0),(9,1,0),(11,4,3)]:
        choices=[v.date() for v in pd.date_range(f'{year}-{month:02}-01',periods=31) if v.month==month and v.weekday()==weekday]
        result.add(choices[ordinal-1] if ordinal>0 else choices[-1])
    result.add(next(v for v in result if v.month==11 and v.weekday()==3)+timedelta(days=1))
    return result|{v+timedelta(days=1) for v in result if v.weekday()==6}


def periods(index):
    special=set().union(*(holidays(y) for y in set(index.year)))
    weekday=(index.dayofweek<5)&~np.isin(index.date,list(special))
    hour=index.hour+index.minute/60
    summer=np.isin(index.month,[6,7,8,9,10])
    return np.where(weekday&summer&(hour>=16)&(hour<19),'on',np.where(weekday&(hour>=8)&(hour<23),'mid','off'))


def eligibility(key,a,start,end):
    from .socal import number
    p=PLANS[key];begin,finish=date.fromisoformat(start),date.fromisoformat(end)
    if begin>finish or start<START or end>END:raise ValueError('Burbank verified coverage is July 1–September 20, 2026; older ECAC/rule history is not extrapolated.')
    if not isinstance(a,dict) or a.get('customer_class')!=p['customer_class']:raise ValueError('Customer type does not match Burbank schedule.')
    for f in ('eligibility_confirmed','ordinary_account_confirmed','cycle_confirmed','tax_confirmed','bwp_ecac_confirmed'):
        if a.get(f) is not True:raise ValueError('Confirm '+f.replace('_',' ')+'.')
    if not isinstance(a.get('reference'),str) or not a['reference'].strip():raise ValueError('Supply BWP qualification reference or explicit study assumption.')
    if a.get('generation_provider')!='bwp' or a.get('solar_program')!='none':raise ValueError('BWP ordinary bundled import scope excludes PV/export settlement.')
    if a.get('voltage')!='secondary' or a.get('phase') not in ('single','three'):raise ValueError('Ordinary secondary metered service only.')
    if number(a.get('local_tax_percent'),'BWP UUT')!=7 or a.get('climate_credit_amount',0):raise ValueError('Ordinary 7% Burbank UUT required; SCE credits and tax-exempt accounts are excluded.')
    if number(a.get('billing_month_factor'),'Billed months')!=1 or not 25<=(finish-begin).days+1<=35:raise ValueError('BWP requires one complete monthly billing cycle; partial-service proration is unsupported.')
    if p['customer_class']=='residential' and a.get('bwp_service_size') not in ('small','medium','large'):raise ValueError('Confirm BWP small, medium or large service size from the account; it is not inferred from building size.')
    if key=='bwp_ev' and a.get('bwp_ev_confirmed') is not True:raise ValueError('EV TOU requires utility-confirmed EV enrollment.')
    if key=='bwp_c' and a.get('bwp_c_confirmed') is not True:raise ValueError('Confirm C non-demand service assignment; kW alone does not establish the kVA classification.')
    return p


def charge_lines(key,index,imports,a,*,convex=False,constraints=None):
    import cvxpy as cp
    total=.25*(cp.sum(imports) if convex else np.sum(imports))
    lines={}
    if key=='bwp_basic':
        pos=cp.pos if convex else lambda v:max(v,0)
        lines['energy_charge']=.1460*total+(.2442-.1460)*pos(total-300)
    else:
        rates=(.3562,.2277,.1215) if key=='bwp_ev' else (.4018,.2623,.1403)
        band=periods(index)
        prices=np.select([band=='on',band=='mid'],rates[:2],default=rates[2])
        lines['energy_charge']=.25*(cp.sum(cp.multiply(prices,imports)) if convex else np.dot(prices,imports))
    if key=='bwp_c':
        lines['customer_charge']=28. if a['phase']=='single' else 34.
        # An assigned C account must not be silently promoted by battery charging.
        if convex:constraints.append(imports<=19.999999)
        elif np.max(imports)>=20:raise ValueError('BWP C scope requires import below 20 kW and separately confirmed non-demand kVA classification.')
    else:
        lines['customer_charge']=19.5
        lines['service_size_charge']={'small':2.18,'medium':4.45,'large':13.37}[a['bwp_service_size']]
    lines['energy_cost_adjustment']=.0340*total
    base=sum(lines.values())
    lines['in_lieu_transfer']=.07*base
    lines['local_utility_tax']=.07*base
    lines['state_energy_surcharge']=.0003*total
    return lines


def bill_details(key,index,imports,a,lines):
    return dict(total=sum(lines.values()),line_items=lines,usage_kWh=float(np.sum(imports)*.25),peak_kw=float(np.max(imports)),
                amount_due=sum(lines.values()),credit_balance=0.,tariff=PLANS[key],
                rate_versions=[dict(version_id='BWP-base-2026-01-01-rules-FY2027',start=str(index[0].date()),end=str(index[-1].date()),source=SOURCE)],
                adjustment_versions=['BWP-ECAC-0.034-verified-2026-09-20'],
                warnings=['Published ECAC must match the confirmed cycle; no monthly adjustment history is inferred.',
                          'Ordinary complete monthly imports only; no demand-metered, assistance, green premium, meter opt-out or standby billing.',
                          'In-lieu transfer and UUT each use service charges before taxes. Export settlement and AC network feasibility are not modeled.'])
