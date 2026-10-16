"""Effective-dated 2026 component selection, shared by billing and optimization.

Demand-rate changes retain the measured whole-cycle demand and require explicit
account confirmation of calendar-day rate allocation. Energy uses actual dated
interval purchases. No current rate is extended into a missing predecessor.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import date
import numpy as np
import pandas as pd
from .dominion_va_2026_data import PREDECESSORS, SOURCE_DOCUMENTS, T1_JULY_REVISION

START=date(2026,1,1)
END=date(2026,10,15)
FULL_SOURCE='https://www.dominionenergy.com/-/media/content/rates-and-tariffs/pdfs/virginia/shared/entire-filed-tariff.pdf'
FULL_HASH='b6a2fa0612183c27d839df336a9d555085757f2bbb0d698a2f21c902af0098dd'
BASE_PAGES={'VA-1':[4,5,6],'VA-1G':[10,11,12,13],'VA-1S':[24,25,26,27],
    'VA-1T':[32,33,34],'VA-GS1':[60,61,62,63,64],'VA-GS2':[82,83,84,85,86,87],
    'VA-GS2T':[94,95,96,97],'VA-GS3':list(range(114,123)),
    'VA-GS4-primary':list(range(146,155)),'VA-GS4-transmission':list(range(146,155)),
    'VA-5C':[170,171],'VA-5P':[174,175,176],
    **{f'VA-10-{level}':list(range(4,12)) for level in ('secondary','primary','transmission')}}


def versions(current):
    result={}
    for name,component in current.items():
        source={'source_url':FULL_SOURCE,'pdf_sha256':FULL_HASH,'retrieved_on':'2026-10-15','page':component['page']}
        rows=[]
        if name in PREDECESSORS:
            start,doc,page,values=PREDECESSORS[name]
            rows.append({'effective_start':start,'values':deepcopy(values),'page':page,**SOURCE_DOCUMENTS[doc]})
        if name=='CERC':
            # The Jan1 filing was suspended Dec16,25 and never implemented.
            rows.append({'effective_start':'2026-01-01','values':{'all':0.},'status':'not_yet_effective',
                'filed_action_effective_start':'2026-03-01','page':5,'supporting_pages':[2,5],**SOURCE_DOCUMENTS[386988]})
        if name=='deferred_fuel':
            rows.append({'effective_start':'2026-02-01','values':{'all':.002900},'page':30,**SOURCE_DOCUMENTS[385769]})
        if name=='T1':
            rows.append({**deepcopy(T1_JULY_REVISION),'values':deepcopy(PREDECESSORS['T1'][3])})
        rows.append({'effective_start':component['effective_start'],'values':{k:deepcopy(v) for k,v in component.items() if k not in ('page','effective_start','effective_end')},**source})
        result[name]=sorted(rows,key=lambda row:row['effective_start'])
    start,doc,page,values=PREDECESSORS['RBB']
    result['RBB']=[{'effective_start':start,'values':deepcopy(values),'page':page,**SOURCE_DOCUMENTS[doc]},
        {'effective_start':'2026-06-01','values':{'all':0.},'status':'filed_withdrawal','page':19,**SOURCE_DOCUMENTS[389025]}]
    return result


class Components:
    def __init__(self,index,current):
        self.index=pd.DatetimeIndex(index)
        if self.index.empty or self.index.tz is None or str(self.index.tz)!='America/New_York' or self.index[0].date()<START or self.index[-1].date()>END:
            raise ValueError('2026 Dominion components require covered America/New_York interval starts.')
        self.days=np.asarray([stamp.date().isoformat() for stamp in self.index])
        self.records={};self.metadata={}
        for name,rows in versions(current).items():
            used=[];records=[];coverage=np.zeros(len(self.index),bool)
            for i,row in enumerate(rows):
                end=rows[i+1]['effective_start'] if i+1<len(rows) else '2026-10-16'
                selector=(self.days>=row['effective_start'])&(self.days<end)
                if not selector.any():continue
                records.append((selector,row['values']));coverage|=selector
                used.append({**{k:v for k,v in row.items() if k!='values'},'rates':deepcopy(row['values']),
                    'coverage_segment_start':str(self.days[selector][0]),'coverage_segment_end':str(self.days[selector][-1])})
            if not coverage.all():raise ValueError('Missing verified 2026 Dominion component '+name+'.')
            self.records[name]=records;self.metadata[name]=used
        self._cache={}

    def rate(self,name,key,position=None):
        cache_key=(name,key,position)
        if cache_key not in self._cache:
            result=np.empty(len(self.index))
            for selector,values in self.records[name]:
                actual=key if key in values else 'gs4' if key in ('gs4p','gs4t') and 'gs4' in values else 'all'
                if actual not in values:raise ValueError(f'Missing verified {name} rate for {key}.')
                value=values[actual]
                if position is not None and isinstance(value,(tuple,list)):value=value[position]
                if isinstance(value,(tuple,list)):raise ValueError(f'{name}/{key} needs an explicit energy/demand selector.')
                result[selector]=float(value)
            self._cache[cache_key]=result
        return self._cache[cache_key]

    def demand_rate(self,name,key,position=None):
        rates=self.rate(name,key,position)
        # Calendar-day, not elapsed-hour, weighting preserves the filed 30-day
        # convention through DST. This path requires explicit account evidence.
        unique,first=np.unique(self.days,return_index=True)
        return float(np.mean(rates[first]))

    def varying(self,name,key,position=None):
        rates=self.rate(name,key,position)
        return bool(np.max(rates)-np.min(rates)>1e-14)


def group_for(tariff,customer_class):
    if customer_class=='residential':return 'res'
    if tariff=='VA-GS1':return 'gs1'
    if tariff in ('VA-GS2','VA-GS2T'):return 'gs2'
    if tariff=='VA-GS3':return 'gs3'
    if tariff=='VA-GS4-primary':return 'gs4p'
    if tariff=='VA-GS4-transmission':return 'gs4t'
    if tariff.startswith('VA-10-'):return {'secondary':'10s','primary':'10p','transmission':'10t'}[tariff[6:]]
    return 'church'


def validate_allocation(account,components):
    tariff=account['tariff'];group=group_for(tariff,account['customer_class'])
    demand=[]
    for name in components.records:
        key=None;position=None
        if group=='gs2':
            if name in ('DIST','RBB','T1'):key='gs2t' if tariff=='VA-GS2T' else 'gs2_demand'
            elif name in ('CE','CERC','E','GEN','OSW','SMR','SNA'):key='gs2';position=1
        elif group in ('gs3','gs4p','gs4t') and name in ('DIST','RBB','T1','CE','CERC','E','GEN','OSW','SMR','SNA'):key=group
        elif group in ('10s','10p','10t') and name in ('DIST','RBB','T1'):key=group
        if key and components.varying(name,key,position):demand.append(name)
    if demand and (account.get('demand_rate_change_allocation')!='calendar_day_prorated_cycle_peak' or not isinstance(account.get('demand_rate_change_source'),str) or not account['demand_rate_change_source'].strip()):
        raise ValueError('A meter cycle crosses demand-rider rate changes ('+', '.join(demand)+'). Confirm calendar-day prorated rates applied to whole-cycle measured demand with demand_rate_change_allocation and a supporting demand_rate_change_source; no segment-peak or proration rule is inferred.')
    if account.get('solar_mode')=='net_metering':
        changed=[name for name in components.records if components.varying(name,group)]
        if changed:raise ValueError('A NEM meter cycle crosses dated rates ('+', '.join(changed)+'); allocation of monthly netted kWh and opening credits across rate versions is not verified. Use a supported complete cycle without a rate transition.')


def base_metadata(tariff,index):
    idx=pd.DatetimeIndex(index)
    july=tariff in ('VA-1','VA-1G','VA-1S') and idx[-1].date()>=date(2026,7,1)
    return {'tariff':tariff,'effective_start':'2026-01-01','pages':BASE_PAGES[tariff],
        **SOURCE_DOCUMENTS[385824 if tariff.startswith('VA-10-') else 385680],
        'ordinary_charge_coefficients_unchanged_by_july_reissue':tariff in ('VA-1','VA-1G','VA-1S'),
        'july_residential_standby_revision_applies':july,
        'july_revision_source':FULL_SOURCE if july else None}
