"""Verified 2025 VA-1 / GS1 bundled charges with explicit historical tax gaps.

Numeric billing and optimization share this exact callback. Missing tax originals
are excluded by name, never replaced by a later tax or hidden in a complete bill.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import date
import numpy as np
import pandas as pd
from .dominion_va_historical_data import COMPONENT_VERSIONS, SOURCE_DOCUMENTS, BASE_SOURCES

START=date(2025,1,1)
END=date(2025,12,31)
PLANS=('VA-1','VA-GS1')
BASE_SOURCE='https://www.dominionenergy.com/-/media/content/renewable-energy-programs/pdfs/virginia/net-metering/'


def supports(account,index):
    idx=pd.DatetimeIndex(index)
    return bool(len(idx) and account.get('tariff') in PLANS and idx[0].date()>=START and idx[-1].date()<=END)


def component_vectors(index,customer):
    """Return actual interval rates and every dated source used in that cycle."""
    idx=pd.DatetimeIndex(index)
    if idx.tz is None or str(idx.tz)!='America/New_York':
        raise ValueError('Historical Dominion Virginia components require America/New_York interval starts.')
    if idx.empty or idx[0].date()<START or idx[-1].date()>END:
        raise ValueError('Historical Dominion Virginia component coverage is bounded to 2025.')
    position=1 if customer=='res' else 2 if customer=='gs1' else None
    if position is None:raise ValueError('Historical components require residential or GS1 service.')
    days=np.asarray([stamp.date().isoformat() for stamp in idx]);rates={};metadata={}
    for name,versions in COMPONENT_VERSIONS.items():
        vector=np.full(len(idx),np.nan);used=[]
        for i,row in enumerate(versions):
            start,res,gs1,doc_id,page=row
            end=versions[i+1][0] if i+1<len(versions) else '2026-01-01'
            mask=(days>=start)&(days<end)
            if not mask.any():continue
            vector[mask]=row[position]
            status='filed_rate'
            if name in ('B','BW','GV','US2','US3','US4','GT','U','C2A') and row[position]==0:
                status='filed_withdrawal'
            elif name in ('GEN','DIST','SMR') and row[position]==0:
                status='not_yet_effective'
            filed_start=versions[i+1][0] if status=='not_yet_effective' else start
            used.append({'effective_start':filed_start,'coverage_segment_start':start,'verified_segment_end':min((pd.Timestamp(end)-pd.Timedelta(days=1)).date(),END).isoformat(),
                'rate_usd_per_kwh':row[position],'status':status,'page':page,**SOURCE_DOCUMENTS[doc_id]})
        if not np.isfinite(vector).all():
            raise ValueError('Missing verified historical Dominion Virginia component '+name+'.')
        rates[name]=vector;metadata[name]=used
    return rates,metadata


def charge_lines(index,imports_kw,exports_kw,account,*,math,state=None):
    from . import dominion_va_general as current
    effective=deepcopy(account)
    if state and 'history' in state:effective['history']=deepcopy(state['history'])
    try:cfg=current.validate_account(effective,index)
    except ValueError as exc:
        if state and 'history' in state and any(word in str(exc) for word in ('eligibility','qualifying','high-load')):
            raise ValueError('Propagated demand history requires utility-confirmed tariff reclassification; automatic migration is unsupported. '+str(exc)) from exc
        raise
    idx=cfg['index'];dt=cfg['hours'];factor=cfg['factor'];tariff=account['tariff']
    if account.get('solar_mode','non_export')!='non_export':
        raise ValueError('2025 solar-export settlement needs its own applicable NEM terms and standby vintage; current 2026 NEM rules are not substituted.')
    if math.convex:math.constraints.append(exports_kw==0)
    else:
        imports_kw=np.asarray(imports_kw,float);exports_kw=np.asarray(exports_kw,float)
        if any(v.shape!=(len(idx),) or not np.isfinite(v).all() for v in (imports_kw,exports_kw)) or np.min(imports_kw)<-1e-7 or np.max(np.abs(exports_kw))>1e-7:
            raise ValueError('Historical non-export studies require finite nonnegative meter imports and zero exports; surplus PV must be curtailed.')
        imports_kw=np.maximum(imports_kw,0.)
    total=math.sum(imports_kw)*dt
    peak=math.demand(imports_kw,idx,30,exact=tariff=='VA-GS1')
    summer=6<=account['billing_month']<=9
    residential=tariff=='VA-1'
    rates,metadata=component_vectors(idx,'res' if residential else 'gs1')
    bound=(800. if residential else 1400.)*factor
    first=current._bounded_minimum(math,total,bound)
    dist=(.026656,.019708) if residential else (.019164,.018136)
    gen=((.028063,.042708) if summer else (.027031,.023430)) if residential else ((.025910,.034795) if summer else (.025910,.016732))
    lines={'customer':(7.58 if residential else 13.39 if account['phase']=='single' else 18.05)*factor,
        'distribution_energy':total*dist[1]+first*(dist[0]-dist[1]),
        'generation_energy':total*gen[1]+first*(gen[0]-gen[1]),
        'transmission_energy':total*(.00970 if residential else .00582)}
    for name,vector in rates.items():
        lines['deferred_fuel' if name=='deferred_fuel' else 'rider_'+name]=math.dot(imports_kw,vector)*dt
    prior=[dict(record) for record in (state or {}).get('history',account.get('history',[]))]
    next_state={}
    if not residential:
        floor=account['established_minimum_kw']
        if any(record['maximum_kw']>=500 for record in prior):floor=max(floor,max(record['maximum_kw'] for record in prior))
        if account['parallel_service']:
            contract=math.maximum([(state or {}).get('contract_demand_kw',account['contract_demand_kw']),floor,peak],exact=True)
            lines['parallel_contract_shortfall']=5.875*(contract-peak)*factor
            next_state['contract_demand_kw']=contract
        before_minimum=sum(value for name,value in lines.items() if name not in ('deferred_fuel','parallel_contract_shortfall'))
        supplement=math.positive(floor-peak,exact=True)*1.866*factor
        minimum=math.maximum(account['contract_minimum_charge']*factor,before_minimum+supplement)
        minimum=math.maximum(minimum,math.choose_leq(peak,50-1e-8,0.,3.88*peak*factor))
        lines['minimum_bill_adjustment']=math.positive(minimum-before_minimum)
        next_state['history']=(prior+[{'billing_month':account['billing_month'],'maximum_kw':peak,'on_peak_kw':peak}])[-11:]
    # The retained current tax sheet explicitly establishes these rates from
    # readings 2025-08-16 onward. Earlier tax tables have not been archived.
    # A complete cycle ending on/after that date necessarily reads afterward;
    # do not infer an earlier reading date from a nominal utility billing month.
    missing=['sales_use_tax_surcharge','local_utility_consumer_tax']
    if idx[-1].date()>=date(2025,8,16):
        lines['consumption_tax']=total*.000845+current._bounded_minimum(math,total,2500.)*.000510+current._bounded_minimum(math,total,50000.)*.000210
    else:missing.append('consumption_tax_before_2025_08_16')
    warnings=[
        'INCOMPLETE HISTORICAL BILL: verified 2025 bundled supply, delivery, riders and deferred fuel are calculated; missing historical tax components are excluded explicitly: '+', '.join(missing)+'.',
        'Dispatch minimizes the verified charges subtotal. Missing decision-dependent taxes mean a complete utility-bill optimum is not claimed.',
        'Capacity and transmission recovery are already included in bundled retail charges; no PJM wholesale price, capacity or transmission adder.',
        'Approved non-export parallel operation is required with PV/storage; surplus PV is curtailed. Historical NEM settlement is not substituted from 2026.'
    ]
    sources=sorted({source['source_url'] for entries in metadata.values() for source in entries})
    base_url=BASE_SOURCE+('schedule-1.pdf' if residential else 'schedule-gs1.pdf')
    sources.append(base_url)
    if 'consumption_tax' in lines:sources.append(current.FULL_SOURCE)
    return {'lines':lines,'metrics':{'import_kWh':total,'export_kWh':0.,'billed_energy_kwh':total,
        'peak_kw':peak,'on_peak_kw':peak,'distribution_demand_kw':0.,'billing_days':cfg['days'],
        'proration_factor':factor,'rate_version':'dominion_va_2025_dated_components','historical_tax_components_excluded':missing},
        'next_state':next_state,'warnings':warnings,'is_complete_bill':False,'excluded_components':missing,
        'sources':sources,'rate_components':{'base':{'tariff':tariff,**deepcopy(BASE_SOURCES[tariff])},**metadata}}
