"""Existing durable worker adapter for bounded solar export studies."""
from pathlib import Path
import json
import pandas as pd
from ..billing import pge_export
from ..billing.export_settlement import CreditBalance,nonnegative
from ..dispatch.solar_export import compare, benefit_breakdown

TARIFF='pge_e_elec_residential_tier3_bundled_2026_06_01'


def validate(request):
    config=request['solar_export']
    if not isinstance(config,dict) or set(config)!={'account','opening_balance','export_limit_kw'}:raise ValueError('Supply export account, confirmed opening balances and export limit.')
    if request['schema_version'] not in (2,3) or request['site']['utility']!='pge' or request['tariff_id']!=TARIFF:raise ValueError('Export study currently requires PG&E bundled E-ELEC residential site inputs.')
    if request.get('site_profile',{}).get('subtype') not in ('house','apartment_unit'):raise ValueError('Export study requires an individually metered residence.')
    if request['timestep_minutes']!=15:raise ValueError('Solar export studies require 15-minute inputs.')
    if request['carbon_weight']!=0:raise ValueError('This export comparison optimizes current bill cash due, with optional battery wear; set carbon weight to zero.')
    nonnegative(config['export_limit_kw'],'Confirmed export limit')
    CreditBalance(**config['opening_balance'])
    start=pd.Timestamp(request['start_date'],tz=request['timezone']);end=pd.Timestamp(request['end_date'],tz=request['timezone'])+pd.DateOffset(days=1)
    index=pd.date_range(start,end,freq='15min',inclusive='left')
    pge_export.validate_account(config['account'],index)
    b=request['battery']
    if abs(b['energy_kWh']-b['capacity_kWh']*b['SOC_min'])>1e-8:raise ValueError('For this renewable-only comparison, set initial battery energy to capacity × minimum SOC.')


def execute(directory,request,frame,provenance):
    from .worker import write_json
    validate(request);directory=Path(directory)
    frame=frame.rename(columns={'load_kw':'native_load_kw','pv_kw':'pv_available_kw'}).copy()
    frame['timestamp']=pd.to_datetime(frame.timestamp,utc=True).dt.tz_convert('America/Los_Angeles')
    config=request['solar_export']
    results=compare(frame,config['account'],export_limit_kw=config['export_limit_kw'],battery=request['battery'],
                    wear_per_kwh=request['degradation_cost_per_kWh'],opening=CreditBalance(**config['opening_balance']),
                    include_degradation_in_optimization=request.get('include_degradation_in_optimization',False))
    tables=[]
    def save(key,label,data):
        payload=json.loads(data.to_json(orient='split',index=False,date_format='iso',double_precision=15))
        payload['labels']=[s.replace('_',' ') for s in payload['columns']]
        write_json(directory/(key+'.json'),payload);data.to_csv(directory/(key+'.csv'),index=False)
        tables.append(dict(id=key,label=label,row_count=len(data)))
    rows=[];credits=[]
    for name,result in results.items():
        bill=result['bill']
        rows.append(dict(scenario=name,amount_due=bill['amount_due'],credits_earned=sum(bill['credits_earned'].values()),
                         credits_used=sum(bill['credits_used'].values()),closing_credit_balance=sum(bill['closing_balance'].values()),
                         degradation_cost=result['degradation_cost'],operating_cost=result['operating_cost'],
                         bill_savings_vs_grid=results['grid_only']['bill']['amount_due']-bill['amount_due'],
                         savings_vs_grid=results['grid_only']['operating_cost']-result['operating_cost']))
        for group in ('import_charges','opening_balance','credits_earned','credits_used','closing_balance'):
            for component,value in bill[group].items():credits.append(dict(scenario=name,category=group,component=component,dollars=value))
        save('dispatch-'+name.replace('_','-'),name.replace('_',' ')+' · dispatch',result['dispatch'])
    save('comparison','Solar use, storage and surplus export comparison',pd.DataFrame(rows))
    # Default to comparison, preserving the existing result table convention.
    tables.insert(0,tables.pop())
    save('credits','Credit balances and eligible charges',pd.DataFrame(credits))
    flows,benefits,benefit_components=benefit_breakdown(results)
    save('solar-benefits','Solar bill savings · panel, inverter, export and battery',pd.DataFrame(benefits))
    save('solar-benefit-components','Solar savings · charge and credit components',pd.DataFrame(benefit_components))
    save('solar-energy-flows','Solar production, grid purchases and exports',pd.DataFrame(flows))
    write_json(directory/'solar_bills.json',{k:{x:y for x,y in v.items() if x!='dispatch'} for k,v in results.items()})
    write_json(directory/'result.json',dict(schema_version=request['schema_version'],tables=tables,request=request,
       engine=json.loads((directory/'engine.json').read_text()),input_provenance=provenance,
       warnings=list(provenance.get('warnings',[]))+results['grid_only']['bill']['warnings']+[
       results['grid_only']['optimization_scope'],'These five comparisons replace the generic strategy choices for this export study.',
       'Solar benefit rows are separate comparisons; do not add alternate battery/export paths together. Unspent credits are not current bill savings.',
       'This study credits only net surplus crossing the household meter. Exporting all solar output through a dedicated generation meter is a separate arrangement and is not modeled.',
       'Costs exclude equipment capital cost. Electrical network feasibility and inverter controls are not evaluated by this export dispatch path.']))
    write_json(directory/'progress.json',dict(message='Solar export comparison complete'))
