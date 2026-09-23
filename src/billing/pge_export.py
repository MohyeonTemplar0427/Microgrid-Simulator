"""PG&E bundled residential NBT monthly operational settlement.

Bounded first adapter, NOT annual true-up or complete NEM/NBT support.
Filed NBT SC2(c-f); E-ELEC June 2026; official hourly UTC export CSVs.
Unimplemented annual/NSC and other-provider paths must remain explicit errors.
"""
from datetime import date
import numpy as np
import pandas as pd
from .export_settlement import CreditBalance, monthly_credit_ledger
from .pge_export_data import RATES, SOURCE_SHA256

VERSION='pge-nbt-monthly-2026-09-21.1'
SOURCES=('https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_NBT.pdf',
         'https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-ELEC.pdf',
         'https://www.pge.com/assets/pge/docs/vanities/PGE-Solar-Billing-Plan-Export-Rates.zip')


def export_rates(index, vintage):
    if type(vintage) is not int or vintage not in RATES:raise ValueError('Supported confirmed NBT application vintages: 2023–2026.')
    index=pd.DatetimeIndex(index)
    if index.tz is None:raise ValueError('Export timestamps require a timezone.')
    hours=((index.tz_convert('UTC').asi8-pd.Timestamp('2026-01-01T08:00Z').value)//3_600_000_000_000).astype(int)
    if len(hours)==0 or hours.min()<0 or hours.max()>=len(RATES[vintage]):raise ValueError('Verified export data covers local calendar year 2026 only.')
    values=np.asarray(RATES[vintage],dtype=float)[hours]/100000
    return values[:,0],values[:,1]


def validate_account(account,index):
    index=pd.DatetimeIndex(index)
    if index.tz is None or str(index.tz)!='America/Los_Angeles':raise ValueError('Use America/Los_Angeles timestamps.')
    if len(index)<2 or not np.all(np.diff(index.asi8)==900_000_000_000):raise ValueError('Complete ordered 15-minute inputs required.')
    if index[0].minute%15 or index[0].second or index[0].microsecond:raise ValueError('Align inputs to quarter hours.')
    if index[0].date()<date(2026,6,1) or index[-1].date()>date(2026,9,21):raise ValueError('Verified E-ELEC/component coverage: June 1–September 21, 2026.')
    if index[0].normalize()!=index[0] or index[-1]+pd.Timedelta(minutes=15)!=(index[-1].normalize()+pd.DateOffset(days=1)):
        raise ValueError('Use whole local service days.')
    required={'utility':'pge','generation_provider':'pge','customer_class':'residential','billing_plan':'E-ELEC','program':'NBT','income_tier':3}
    for key,value in required.items():
        if account.get(key)!=value:raise ValueError(f'Current adapter requires {key}={value}.')
    for field in ('enrollment_confirmed','ordinary_account_confirmed','cycle_confirmed','no_local_tax_confirmed','no_other_adjustments_confirmed'):
        if account.get(field) is not True:raise ValueError('Confirm '+field.replace('_',' ')+'.')
    if not isinstance(account.get('reference'),str) or not account['reference'].strip():raise ValueError('Supply a non-sensitive account confirmation reference.')
    vintage=account.get('application_year')
    if type(vintage) is not int or vintage not in RATES:raise ValueError('Confirm application year 2023–2026.')
    pto=date.fromisoformat(account['pto_date'])
    if pto.year<vintage or pto>index[0].date():raise ValueError('PTO must follow application year and precede the study.')
    lock_in_end=(pd.Timestamp(pto)+pd.DateOffset(years=9)).date()
    if index[-1].date()>=lock_in_end:raise ValueError('Nine-year lock-in has ended; floating rates are not implemented.')
    if account.get('bonus_eligible_confirmed') is not True:raise ValueError('Current adapter requires confirmed ordinary residential ACC Plus eligibility; transitions/mandated solar are not modeled.')
    cycle_start=date.fromisoformat(account['cycle_start']);cycle_end=date.fromisoformat(account['cycle_end'])
    if cycle_start!=index[0].date() or cycle_end!=index[-1].date() or not 25<=(cycle_end-cycle_start).days+1<=35:
        raise ValueError('Supply one complete confirmed 25–35-day billing cycle matching the data.')
    true_up=date.fromisoformat(account['next_true_up_date'])
    if true_up<=cycle_end:raise ValueError('Annual true-up/NSC is not implemented by the monthly adapter; choose a cycle before true-up.')
    if true_up>(pd.Timestamp(cycle_end)+pd.DateOffset(years=1)).date():raise ValueError('Next annual true-up cannot be more than one year after this cycle.')
    if account.get('storage') not in ('none','renewable_only'):raise ValueError('Only confirmed renewable-only paired storage is supported; grid-charged export is excluded.')
    return index


def prices(account,index):
    index=validate_account(account,index)
    # Reuse the existing authoritative E-ELEC total import schedule.
    from .pge_residential import PGE_E_ELEC_RESIDENTIAL_TIER3_BUNDLED as tariff
    total=np.asarray(tariff.energy_rates(index),dtype=float)
    h=index.hour+index.minute/60
    summer=(index.month>=6)&(index.month<=9)
    peak=(h>=16)&(h<21);part=((h>=15)&(h<16))|(h>=21)
    generation=np.where(summer,np.where(peak,.26299,np.where(part,.16388,.11878)),np.where(peak,.10086,np.where(part,.08089,.06754)))
    nbc=.00614-.00002+.00027+.00591
    eg,ed=export_rates(index,account['application_year'])
    return dict(generation=generation,delivery=total-generation-nbc,protected=np.full(len(index),nbc+.0003),
                export_generation=eg,export_delivery=ed,export_bonus=np.full(len(index),{2023:.022,2024:.0176,2025:.0132,2026:.0088}[account['application_year']]),
                fixed=tariff.daily_customer_charge*len(index.normalize().unique()))


def charge_expressions(imports,exports,rates,*,convex=False):
    if convex:
        import cvxpy as cp
        dot=lambda x,y:cp.sum(cp.multiply(x,y))*.25
    else:dot=lambda x,y:float(np.dot(x,y)*.25)
    charges={key:dot(imports,rates[key]) for key in ('generation','delivery','protected')}
    charges['protected']+=rates['fixed']
    earned={key:dot(exports,rates['export_'+key]) for key in ('generation','delivery','bonus')}
    return charges,earned


def bill(frame,account,opening=CreditBalance()):
    index=pd.DatetimeIndex(frame.timestamp)
    rates=prices(account,index)
    imp=np.asarray(frame.grid_import_kw,float);exp=np.asarray(frame.grid_export_kw,float)
    if not np.isfinite(imp).all() or not np.isfinite(exp).all() or min(imp.min(),exp.min())<-1e-7:raise ValueError('Invalid import/export power.')
    if np.max(np.minimum(imp,exp))>1e-6:raise ValueError('Simultaneous import/export is not supported.')
    charges,earned=charge_expressions(np.maximum(imp,0),np.maximum(exp,0),rates)
    result=monthly_credit_ledger(charges,earned,opening)
    return dict(result,import_kwh=float(imp.sum()*.25),export_kwh=float(exp.sum()*.25),version=VERSION,
                export_data_sha256=SOURCE_SHA256[account['application_year']],sources=SOURCES,
                warnings=['Monthly operational settlement only; annual true-up, retrospective credit offsets, NSC and termination are not implemented.',
                          'Unused credit is carried as restricted credit, not cash. Local taxes, climate credits and other account adjustments are excluded by explicit confirmation.'])
