"""SCE residential dated plans and shared numerical/convex cycle charges.

Daily fixed charges follow Rule 9 A.3; baseline quantities follow Preliminary H.
Rate/season subperiod baseline allocation is an explicit study approximation,
not an assertion of SCE's account-specific meter-read allocation algorithm.
"""
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
import numpy as np
from .plans import RatePlan, RatePlanIdentity
from .sce_residential_data import HISTORICAL_RATES
from .sce_residential_2026_data import RATES_2026

BASELINES = {'5':(17,16.8,18.4,27),'6':(11.4,8.7,11,12.6),'8':(12.8,9.9,10.3,12.3),
 '9':(16.9,12.5,12,13.9),'10':(19.3,15.9,12.1,16.4),'13':(22.2,24.2,12.2,23),
 '14':(19.2,18.5,11.9,21.1),'15':(45,24,9.7,17.4),'16':(14.7,13.5,12.4,23.2)}
ROW_NAMES = ('summer_on','summer_mid','summer_off','winter_mid','winter_off','winter_super_off')

@dataclass(frozen=True)
class ResidentialRateVersion:
    tariff_id: str
    effective_start: date
    effective_end: date
    data: object

    def is_effective_on(self, service_date):
        return self.effective_start <= service_date <= self.effective_end


def build_plans():
    records = [dict(r) for r in (*HISTORICAL_RATES, *RATES_2026)]
    plans = {}
    for key in dict.fromkeys(r['plan_id'] for r in records):
        versions=[]
        for record in records:
            if record['plan_id'] != key: continue
            data={**record,'energy_rows':MappingProxyType({k:tuple(v) for k,v in record['energy_rows'].items()})}
            versions.append(ResidentialRateVersion(key+'_'+record['effective_start'],date.fromisoformat(record['effective_start']),
                date.fromisoformat(record['effective_end']),MappingProxyType(data)))
        plans[key]=RatePlan(RatePlanIdentity('sce',key.removeprefix('sce_').upper(),'bundled','residential'),tuple(versions))
    return plans


def segments(plan,index):
    """Separate dated prices and seasonal allowances; retain actual local days."""
    for version,dates in plan.segments_for(index):
        version_mask=np.isin(index.date,dates)
        for summer in dict.fromkeys(np.isin(index[version_mask].month,[6,7,8,9])):
            mask=version_mask & (np.isin(index.month,[6,7,8,9]) == summer)
            if np.any(mask): yield version,mask,summer


def allowance(account,days,summer,key):
    electric=account['baseline_type']=='all_electric'
    daily=BASELINES[account['baseline_region']][(0 if summer else 2)+electric]
    if account.get('heat_pump_water') and key in ('sce_tou-d-4-9','sce_tou-d-5-8'):
        daily += 1.9 if summer else (3. if electric else 2.6)
    return days*daily


def charges(plan,key,index,imports,account,period_labels,convex=False):
    import cvxpy as cp
    sum_=cp.sum if convex else np.sum
    maximum=cp.maximum if convex else np.maximum
    lines={k:0. for k in ('energy_charge','generation_charge','baseline_credit','fixed_charge',
                          'minimum_adjustment','fixed_recovery_charge')}
    for version,mask,summer in segments(plan,index):
        r=version.data;power=imports[mask];energy=sum_(power)*.25
        days=len(index[mask].normalize().unique())
        allocation=allowance(account,days,summer,key) if key!='sce_tou-d-prime' else 0.
        credit=0.
        if key=='sce_d':
            prefix='summer_' if summer else 'winter_'
            lower=r['energy_rows'][prefix+'baseline'];upper=r['energy_rows'][prefix+'above_baseline']
            delivery=lower[0]*energy+(upper[0]-lower[0])*maximum(energy-allocation,0)
            generation=lower[1]*energy+(upper[1]-lower[1])*maximum(energy-allocation,0)
        else:
            labels=[('summer_' if summer else 'winter_')+('super_off' if p=='super' else p) for p in period_labels[mask]]
            prices=np.array([r['energy_rows'][label] for label in labels])
            delivery=sum_(cp.multiply(power,prices[:,0]) if convex else power*prices[:,0])*.25
            generation=sum_(cp.multiply(power,prices[:,1]) if convex else power*prices[:,1])*.25
            rate=r['baseline_credit_per_kwh']
            credit=rate*(maximum(energy-allocation,0)-energy) if rate else 0.
        basic=r.get('basic_charge_per_day',r.get('basic_charge_multifamily_per_day' if account.get('accommodation')=='multifamily' else 'basic_charge_single_family_per_day',0.))
        fixed=days*(r.get('base_services_charge_per_day',0.)+basic)
        floor=days*r['minimum_charge_per_day']
        # D's filed minimum comparison excludes WFC; TOU-D's does not.
        wfc=energy*.00595 if key=='sce_d' and floor else 0.
        if convex and floor:
            # max(convex delivery + basic - WFC, minimum) + WFC is DCP.
            delivery=maximum(delivery+credit+fixed-wfc,floor)+wfc-fixed
            credit=0.
        elif floor:
            lines['minimum_adjustment']+=max(0.,floor-float(delivery+credit+fixed-wfc))
        lines['energy_charge']+=delivery
        lines['generation_charge']+=generation
        lines['baseline_credit']+=credit
        lines['fixed_charge']+=fixed
        lines['fixed_recovery_charge']+=r['fixed_recovery_per_kwh']*energy
    return lines


def version_details(plan,key,index,account):
    result=[]
    for version,mask,summer in segments(plan,index):
        dates=index[mask].normalize().unique();r=version.data
        result.append(dict(version_id=version.tariff_id,start_date=dates[0].date().isoformat(),
            end_date=dates[-1].date().isoformat(),service_days=len(dates),season='summer' if summer else 'winter',
            baseline_kwh=allowance(account,len(dates),summer,key) if key!='sce_tou-d-prime' else 0.,
            sheet=r['sheet'],source=r['source_url']))
    return result
