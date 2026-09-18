"""Schema 4: durable municipal import-only storage studies."""
from copy import deepcopy
from datetime import date, timedelta
import json
import io

import numpy as np
import pandas as pd

from ..billing.municipal import bill_cycle, finite
from ..dispatch.battery import Battery
from ..dispatch.municipal import optimize_storage
from .municipal_service import validate_arrangement

FIELDS={'schema_version','name','resolution_id','resolution','mode','arrangement','account',
        'start_date','end_date','timezone','timestep_minutes','battery','load','degradation_cost_per_kWh'}


def cycle(request):
    start=pd.Timestamp(request['start_date'],tz='America/Los_Angeles')
    end=pd.Timestamp(request['end_date'],tz='America/Los_Angeles')+pd.DateOffset(days=1)
    return start,end


def load_frame(request):
    start,end=cycle(request)
    stamps=pd.date_range(start,end,freq='15min',inclusive='left')
    spec=request['load']
    if spec['mode'] in ('intervals','csv'):
        data=pd.read_csv(io.StringIO(spec['csv'])) if spec['mode']=='csv' else pd.DataFrame(spec['intervals'])
        if len(data)>3300:
            raise ValueError('Supply at most 3300 load intervals for one cycle.')
        if set(data.columns)!={'timestamp','grid_import_kw'}:
            raise ValueError('Import-only load data requires exactly timestamp and grid_import_kw; PV/export columns are not accepted.')
        return data
    base=finite(spec['base_kw'],'Base load')
    power=np.full(len(stamps),base,dtype=float)
    if spec['mode']=='daily_peak':
        peak=finite(spec['peak_kw'],'Peak load',base)
        begin=finite(spec['peak_start_hour'],'Peak start hour',0,23)
        finish=finite(spec['peak_end_hour'],'Peak end hour',1,24)
        if begin>=finish or begin%1 or finish%1:
            raise ValueError('Use whole-hour daily peaks with start before end.')
        power[(stamps.hour>=begin)&(stamps.hour<finish)]=peak
    return pd.DataFrame({'timestamp':stamps,'grid_import_kw':power})


def validate_study(request):
    if not isinstance(request,dict) or set(request) - {"site_profile", "grid_only", "carbon"} != FIELDS or request.get('schema_version')!=4:
        raise ValueError('Supply exactly the schema 4 municipal study fields.')
    if not isinstance(request['name'],str) or not 1<=len(request['name'].strip())<=120:
        raise ValueError('Study name must contain 1–120 characters.')
    from .site_profile import validate_profile_request
    validate_profile_request(request)
    from .carbon import validate as validate_carbon
    validate_carbon(request)
    rid=request['resolution_id']
    if not isinstance(rid,str) or len(rid)!=32 or any(c not in '0123456789abcdef' for c in rid):
        raise ValueError('A saved utility resolution ID is required.')
    if request['mode'] not in ('actual_service','alternative_location'):
        raise ValueError('Choose actual service or alternative location.')
    if not isinstance(request['resolution'],dict):
        raise ValueError('Saved location evidence is required.')
    validate_arrangement(request['arrangement'],request['resolution'],comparison=request['mode']=='alternative_location')
    if request['arrangement']['delivery_utility'] not in ('amp','svp'):
        raise ValueError('Use the existing workflow for PG&E and CCA studies.')
    if request['timezone']!='America/Los_Angeles' or type(request['timestep_minutes']) is not int or request['timestep_minutes']!=15:
        raise ValueError('Municipal studies require America/Los_Angeles and 15-minute intervals.')
    start,end=date.fromisoformat(request['start_date']),date.fromisoformat(request['end_date'])
    if not 0<=(end-start).days<=32:
        raise ValueError('Run one complete supported billing cycle (at most 33 days).')
    grid_only = request.get('grid_only', False)
    if type(grid_only) is not bool:
        raise ValueError('grid_only must be boolean.')
    if grid_only and (request['battery'] is not None or request['degradation_cost_per_kWh'] != 0):
        raise ValueError('Grid-only studies must have no battery and zero degradation cost.')
    if not grid_only and (not isinstance(request['battery'],dict) or set(request['battery'])!={'capacity_kWh','energy_kWh','max_charge_kw','max_discharge_kw','SOC_min','SOC_max','charge_efficiency','discharge_efficiency'}):
        raise ValueError('Supply all eight battery settings.')
    if not grid_only:
        Battery(**request['battery'])
    finite(request['degradation_cost_per_kWh'],'Degradation cost')
    load=request['load']
    shapes={'constant':{'mode','base_kw'},'daily_peak':{'mode','base_kw','peak_kw','peak_start_hour','peak_end_hour'},'intervals':{'mode','intervals'},'csv':{'mode','csv'}}
    if not isinstance(load,dict) or load.get('mode') not in shapes or set(load)!=shapes[load['mode']]:
        raise ValueError('Choose constant, daily_peak, CSV, or explicit interval load with its required fields.')
    if load['mode']=='intervals' and (not isinstance(load['intervals'],list) or len(load['intervals'])>3300):
        raise ValueError('Supply at most 3300 load intervals for one cycle.')
    if load['mode']=='csv' and (not isinstance(load['csv'],str) or len(load['csv'])>1000000):
        raise ValueError('Load CSV must be text under 1 MB.')
    begin,finish=cycle(request)
    bill_cycle(request['arrangement']['tariff_id'],load_frame(request),cycle_start=begin,cycle_end=finish,account=request['account'])
    return request


def execute_study(directory,request):
    from .worker import write_json
    from pathlib import Path
    directory=Path(directory)
    validate_study(request)
    start,end=cycle(request)
    inputs=load_frame(request)
    carbon_provenance = None
    if 'carbon' in request:
        from .carbon import values as carbon_values
        carbon, carbon_provenance = carbon_values(request, directory, pd.to_datetime(inputs.timestamp, utc=True))
    inputs.to_csv(directory/'normalized.csv',index=False)
    if request.get('grid_only'):
        from .grid_only import save_results
        bill = bill_cycle(request['arrangement']['tariff_id'], inputs, cycle_start=start, cycle_end=end, account=request['account'])
        row = dict(scenario='no_battery', total_explicit_cost=bill['total'], total_utility_charge=bill['total'],
                   degradation_cost=0, peak_grid_import_kw=float(inputs.grid_import_kw.max()), interval_count=len(inputs))
        if carbon_provenance:
            row['emissions_kgCO2'] = float((inputs.grid_import_kw.to_numpy() * carbon).sum() * .25 / 1000)
            inputs['gCO2/kWh'] = carbon
        row.update(energy_cost=bill['line_items']['energy_charge'], demand_charge=bill['line_items']['demand_charge'], customer_charge=bill['line_items']['customer_charge'])
        warnings = ['Grid-only study: no PV, battery, weather or dispatch optimization.',
                    'No AC power-flow replay is performed; electrical network feasibility is not evaluated.']
        if carbon_provenance:
            warnings.append(carbon_provenance['warning'])
        if request['mode']=='alternative_location':
            warnings.append('HYPOTHETICAL ALTERNATIVE LOCATION: account eligibility is assumed for this scenario.')
        save_results(directory, request, [('comparison','Grid-only operating cost',pd.DataFrame([row])),
            ('costs','Itemized utility bill',pd.DataFrame([dict(component=k,amount=v) for k,v in bill['line_items'].items()])),
            ('inputs','Grid-only load and imports',inputs)], warnings, bills={'no_battery':bill}, input_provenance={'carbon':carbon_provenance})
        return

    write_json(directory/'progress.json',{'message':'Optimizing storage against municipal tiers, demand history, taxes and adjustments'})
    result=optimize_storage(request['arrangement']['tariff_id'],inputs,cycle_start=start,cycle_end=end,
        account=request['account'],battery=request['battery'],degradation_cost_per_kWh=request['degradation_cost_per_kWh'])
    tables=[]
    def save(key,label,frame):
        payload=json.loads(frame.to_json(orient='split',index=False,date_format='iso',double_precision=15))
        payload['labels']=[c.replace('_',' ') for c in payload['columns']]
        write_json(directory/(key+'.json'),payload)
        frame.to_csv(directory/(key+'.csv'),index=False)
        tables.append({'id':key,'label':label,'row_count':len(frame)})
    bills={'no_battery':result['baseline_bill'],'cost_optimal':result['bill']}
    comparison=[]; costs=[]; details=[]
    for scenario,bill in bills.items():
        wear=result['degradation_cost'] if scenario=='cost_optimal' else 0
        comparison.append(dict(scenario=scenario,total_explicit_cost=bill['total']+wear,
            energy_cost=bill['line_items']['energy_charge'],demand_charge=bill['line_items']['demand_charge'],
            customer_charge=bill['line_items']['customer_charge'],total_utility_charge=bill['total'],
            degradation_cost=wear,peak_grid_import_kw=float((result['dispatch'] if scenario=='cost_optimal' else inputs).grid_import_kw.max()),
            billed_peak_kw=bill['billing_demand_kw'],interval_count=len(inputs),
            optimality_gap_bound_dollars=result['optimality_gap_bound_dollars'] if scenario=='cost_optimal' else None))
        if carbon_provenance:
            dispatch = result['dispatch'] if scenario=='cost_optimal' else inputs
            comparison[-1]['emissions_kgCO2'] = float((dispatch.grid_import_kw.to_numpy() * carbon).sum() * .25 / 1000)
        costs.extend(dict(scenario=scenario,component=k,amount=v) for k,v in bill['line_items'].items())
        details.extend(dict(scenario=scenario,**row) for row in bill['energy_detail'])
    save('comparison','Municipal strategy comparison',pd.DataFrame(comparison))
    save('costs','Itemized utility bills',pd.DataFrame(costs))
    save('energy','Energy tiers and TOU charges',pd.DataFrame(details))
    inputs['timestamp']=pd.to_datetime(inputs.timestamp,utc=True)
    if carbon_provenance:
        inputs['gCO2/kWh'] = carbon
    save('inputs','Native load inputs',inputs)
    save('dispatch-cost_optimal','Optimized battery dispatch',result['dispatch'])
    warnings=result['warnings']+[
        'Import-only load and storage study. Solar generation, export settlement and standby service are not modeled.',
        'No AC power-flow replay is performed for this municipal billing study; electrical network feasibility is not established.',
        'Existing assignment is confirmed or explicitly assumed for this scenario; no automatic utility rate transfer.']
    if request['mode']=='alternative_location':
        warnings.insert(0,'HYPOTHETICAL ALTERNATIVE LOCATION: this utility is not claimed to serve the original site.')
    if carbon_provenance:
        warnings.append(carbon_provenance['warning'])
    write_json(directory/'result.json',dict(schema_version=4,tables=tables,warnings=warnings,
        request=request,engine=json.loads((directory/'engine.json').read_text()),bills=bills,
        optimization={k:result[k] for k in ('solver','objective_lower_bound','optimality_gap_bound_dollars','regime')},
        tariff=result['bill']['tariff'],input_provenance={'resolution':request['resolution'],'account':request['account'],'carbon':carbon_provenance}))
    write_json(directory/'progress.json',{'message':'Municipal bills reconciled and dispatch saved'})
