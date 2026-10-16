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
    if request['carbon_weight']!=0:raise ValueError('This export comparison optimizes cycle cost before inherited credits, with optional battery wear; set carbon weight to zero.')
    nonnegative(config['export_limit_kw'],'Confirmed export limit')
    CreditBalance(**config['opening_balance'])
    start=pd.Timestamp(request['start_date'],tz=request['timezone']);end=pd.Timestamp(request['end_date'],tz=request['timezone'])+pd.DateOffset(days=1)
    index=pd.date_range(start,end,freq='15min',inclusive='left')
    pge_export.validate_account(config['account'],index)
    b=request['battery']
    if abs(b['energy_kWh']-b['capacity_kWh']*b['SOC_min'])>1e-8:raise ValueError('For this renewable-only comparison, set initial battery energy to capacity × minimum SOC.')


def execute(directory,request,frame,provenance,*,pv_replay=None,residential_service=None):
    from .worker import write_json, summarize_ac_validation
    # Contract validation also runs in the API process; load mutable OpenDSS
    # state only when executing the isolated simulation worker.
    from ..opendss.solar_export_replay import replay_export_scenario
    from ..opendss.residential_service import ResidentialService
    from ..opendss.qsts_analysis import create_qsts_scenario_comparison
    validate(request);directory=Path(directory)
    service=ResidentialService() if residential_service is None else residential_service
    if not isinstance(service, ResidentialService):
        raise ValueError('Export replay requires a validated ResidentialService configuration.')
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
    rows=[];credits=[];replays={}
    for name,result in results.items():
        write_json(directory/'progress.json',dict(message='Validating electrical feasibility: '+name.replace('_',' ')))
        replays[name]=replay_export_scenario(name,result['dispatch'],battery=request['battery'],
                                           pv_capacity_kw=request['pv_capacity_kw'],pv_replay=pv_replay,
                                           residential_service=service)
        bill=result['bill']
        rows.append(dict(scenario=name,amount_due=bill['amount_due'],credits_earned=sum(bill['credits_earned'].values()),
                         credits_used=sum(bill['credits_used'].values()),closing_credit_balance=sum(bill['closing_balance'].values()),
                         degradation_cost=result['degradation_cost'],operating_cost=result['operating_cost'],
                         bill_savings_vs_grid=results['grid_only']['bill']['amount_due']-bill['amount_due'],
                         savings_vs_grid=results['grid_only']['operating_cost']-result['operating_cost']))
        for group in ('import_charges','opening_balance','credits_earned','credits_used','closing_balance'):
            for component,value in bill[group].items():credits.append(dict(scenario=name,category=group,component=component,dollars=value))
        save('dispatch-'+name.replace('_','-'),name.replace('_',' ')+' · dispatch',result['dispatch'])
        save('ac-'+name.replace('_','-'),name.replace('_',' ')+' · electrical validation',replays[name])
    # The shared QSTS summary expects its legacy signed scheduled-grid column.
    electrical=create_qsts_scenario_comparison({name:ac.assign(scheduled_grid_import_kw=ac.scheduled_grid_net_import_kw)
                                               for name,ac in replays.items()}).rename(columns={
        'grid_import_energy_kWh':'replay_pcc_grid_import_energy_kWh',
        'grid_export_energy_kWh':'replay_pcc_grid_export_energy_kWh',
        'peak_grid_import_kw':'scheduled_peak_grid_net_import_kw',
        'minimum_grid_power_kw':'scheduled_minimum_grid_net_import_kw'})
    electrical['failed_intervals']=electrical.interval_count-electrical.feasible_intervals
    electrical['all_intervals_feasible']=electrical.failed_intervals.eq(0)
    electrical['electrical_measurements_complete']=electrical.converged_intervals.eq(electrical.interval_count)
    electrical['network_loss_energy_kWh']=[replays[name].network_real_loss_kw.sum(min_count=1)*.25 for name in electrical.scenario]
    for column in ('service_l1_current_a','service_l2_current_a','service_neutral_current_a',
                   'neutral_voltage_v','transformer_primary_loading_percent',
                   'transformer_l1_loading_percent','transformer_l2_loading_percent'):
        electrical['maximum_'+column]=[replays[name][column].max() for name in electrical.scenario]
    # If all solves fail, a loss total of zero would be misleading.
    energy_columns=[c for c in electrical if c.endswith('energy_kWh')]
    electrical.loc[electrical.converged_intervals.eq(0),energy_columns]=float('nan')
    validation=summarize_ac_validation(replays)
    statistics=json.loads(electrical.to_json(orient='records',double_precision=15))
    for item,stats in zip(validation['scenarios'],statistics):
        item.update(stats,interval_table='ac-'+item['scenario'].replace('_','-'))
    validation.update(status='completed',method='OpenDSS quasi-static power flow',version=2,timestep_minutes=15,
                      soc_convention='start_of_interval',billing_basis='original scheduled meter flows',
                      network=service.description,network_configuration=service.metadata(),
                      inverter_model='Constant P/Q AC generators; Q=0 by default; storage external dispatch; no inverter dynamics')
    save('comparison','Solar use, storage and surplus export comparison',pd.DataFrame(rows).merge(electrical,on='scenario',validate='one_to_one'))
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
       ac_validation=validation,
       warnings=list(provenance.get('warnings',[]))+results['grid_only']['bill']['warnings']+[
       results['grid_only']['optimization_scope'],'These five comparisons replace the generic strategy choices for this export study.',
       'Solar benefit rows are separate comparisons; do not add alternate battery/export paths together. Unspent credits are not current bill savings.',
       'This study credits only net surplus crossing the household meter. Exporting all solar output through a dedicated generation meter is a separate arrangement and is not modeled.',
       'Costs exclude equipment capital cost. OpenDSS validates every 15-minute schedule after optimization; electrical constraints do not change dispatch or billing.',
       'Electrical validation: '+service.description+'. This is an assumed single-home circuit, not verified customer wiring or a shared neighborhood transformer.',
       f'Assumed service: {service.service_length_km*1000:g} m, {service.conductor_r_ohm_per_km:g} ohm/km resistance and {service.conductor_x_ohm_per_km:g} ohm/km reactance per conductor, explicit neutral grounded at the transformer, no earth-return path. Native load: {service.l1_load_fraction:.0%} L1–N, {service.l2_load_fraction:.0%} L2–N and {1-service.l1_load_fraction-service.l2_load_fraction:.0%} at 240 V; PV and battery are connected at 240 V. No appliance or leg allocation is inferred from the load data.',
       f'Transformer limits check primary kVA and each half-secondary against {service.transformer_kva/2:g} kVA; service limits check both hot conductors and neutral against {service.service_amps:g} A. Voltage checks use both line-to-neutral voltages and line-to-line voltage. No breaker coordination, service-panel busbar or time-dependent thermal validation.',
       'PV replays actual scheduled AC output, including curtailment. Inverters use constant P/Q equivalents (Q=0 by default); aggregate ratings assume kVA=kW. Load defaults to 0.95 lagging power factor. No Volt-Var, Volt-Watt or transient analysis.',
       'Replay PCC import/export and network losses are diagnostic only. Bills and export-credit ledgers use the original scheduled meter flows.',
       'A completed calculation may be electrically infeasible. Inspect the comparison and downloadable electrical-validation interval tables; nonconverged measurements are excluded from electrical energy totals.']+
       [f"Electrical validation failed for {s['scenario']}: {s['failed_intervals']} of {s['checked_intervals']} intervals. Costs describe the scheduled flows, not an electrically feasible installation."
        for s in validation['scenarios'] if s['failed_intervals']]))
    write_json(directory/'progress.json',dict(message='Solar export comparison complete'))
