"""Monthly PV/export/storage comparison using an authoritative credit ledger.

Currently PG&E bundled NBT adapter only. Do not silently reuse it for another
utility or legacy NEM. Mixed-integer modes prevent artificial import/export
arbitrage when hourly export compensation exceeds the import price.
"""
import numpy as np
import pandas as pd
import cvxpy as cp
from .battery import Battery
from ..billing import pge_export
from ..billing.export_settlement import CreditBalance, monthly_credit_objective, nonnegative


def compare(frame,account,*,export_limit_kw,battery=None,wear_per_kwh=0.,opening=CreditBalance()):
    nonnegative(export_limit_kw,'Export limit');nonnegative(wear_per_kwh,'Battery wear')
    index=pd.DatetimeIndex(frame.timestamp);rates=pge_export.prices(account,index)
    load=np.asarray(frame.native_load_kw,float);pv=np.asarray(frame.pv_available_kw,float);n=len(load)
    if not np.isfinite(load).all() or not np.isfinite(pv).all() or min(load.min(),pv.min())<0:raise ValueError('Finite nonnegative load and PV required.')
    results={}
    def record(name,imports,exports,charge,discharge,output,energy,objective=None):
        values=[imports,exports,charge,discharge,output,energy]
        if any(not np.isfinite(v).all() for v in values):raise ValueError('Invalid solver output.')
        if np.max(np.abs(imports+output+discharge-load-charge-exports))>1e-5:raise ValueError('Power balance does not reconcile.')
        if np.max(np.minimum(charge,discharge))>1e-6:raise ValueError('Simultaneous charge/discharge.')
        out=frame.copy()
        available=zeros if name=='grid_only' else pv
        out['pv_available_kw']=available
        out['grid_import_kw']=np.maximum(imports,0);out['grid_export_kw']=np.maximum(exports,0)
        out['pv_output_kw']=np.maximum(output,0);out['pv_curtailed_kw']=np.maximum(available-output,0)
        out['battery_charge_kw']=np.maximum(charge,0);out['battery_discharge_kw']=np.maximum(discharge,0);out['energy_kWh']=energy
        bill=pge_export.bill(out,account,opening)
        wear=float(.25*np.sum(charge+discharge)*wear_per_kwh)
        cost=bill['amount_due']+wear
        gap=None if objective is None else abs(cost-objective)
        if gap is not None and gap>.02:raise ValueError('Export ledger/dispatch objective does not reconcile.')
        results[name]=dict(bill=bill,dispatch=out,degradation_cost=wear,operating_cost=cost,objective_gap=gap,
            optimization_scope='One billing cycle cash due plus throughput wear; unused closing credits have no assumed cash value. Not annual optimality or lifecycle payback.')
    zeros=np.zeros(n)
    record('grid_only',load,zeros,zeros,zeros,zeros,zeros)
    direct=np.minimum(load,pv);surplus=np.minimum(np.maximum(pv-load,0),export_limit_kw)
    record('pv_self_consumption',load-direct,zeros,zeros,zeros,direct,zeros)
    record('pv_with_export',load-direct,surplus,zeros,zeros,direct+surplus,zeros)
    if battery is None:return results
    if account['storage']!='renewable_only':raise ValueError('Confirm renewable-only paired storage before optimizing.')
    b=Battery(**battery)
    if abs(b.energy_kWh-b.minimum_energy_kWh)>1e-8:raise ValueError('Start/end battery at minimum SOC so no unverified initial energy can earn export credits.')
    for name,limit in [('storage_self_consumption',0.),('storage_with_export',export_limit_kw)]:
        charge=cp.Variable(n,nonneg=True);discharge=cp.Variable(n,nonneg=True)
        imp=cp.Variable(n,nonneg=True);exp=cp.Variable(n,nonneg=True);output=cp.Variable(n,nonneg=True);energy=cp.Variable(n+1)
        charging=cp.Variable(n,boolean=True);importing=cp.Variable(n,boolean=True)
        constraints=[charge<=b.max_charge_kw*charging,discharge<=b.max_discharge_kw*(1-charging),
          imp<=cp.multiply(load+b.max_charge_kw,importing),exp<=limit*(1-importing),
          output<=pv,charge<=output,imp+output+discharge==load+charge+exp,
          energy[0]==b.energy_kWh,energy[-1]==b.energy_kWh,
          energy>=b.minimum_energy_kWh,energy<=b.maximum_energy_kWh,
          energy[1:]==energy[:-1]+.25*(b.charge_efficiency*charge-discharge/b.discharge_efficiency)]
        charges,earned=pge_export.charge_expressions(imp,exp,rates,convex=True)
        objective=monthly_credit_objective(charges,earned,opening,constraints)+wear_per_kwh*.25*cp.sum(charge+discharge)
        problem=cp.Problem(cp.Minimize(objective),constraints)
        problem.solve(solver='SCIPY',scipy_options={'mip_rel_gap':1e-8})
        if problem.status!='optimal':raise ValueError('Export dispatch did not reach optimality: '+str(problem.status))
        if np.max(np.abs(np.diff(energy.value)-.25*(b.charge_efficiency*charge.value-discharge.value/b.discharge_efficiency)))>1e-5:
            raise ValueError('Battery energy does not reconcile.')
        record(name,imp.value,exp.value,charge.value,discharge.value,output.value,energy.value[:-1],problem.value)
    return results


def benefit_breakdown(results):
    """Explain solar operating savings without treating unused credits as cash.

    Each bridge is a separate counterfactual. The two export bridges and two
    storage bridges are alternative paths, so their rows must not be summed.
    """
    scenarios=('grid_only','pv_self_consumption','pv_with_export',
               'storage_self_consumption','storage_with_export')
    if not all(name in results for name in scenarios[:3]):
        raise ValueError('Grid, behind-meter solar and solar-export results are required.')
    def energy(result,column):
        return float(result['dispatch'][column].sum()*.25)
    flows=[]
    for name in scenarios:
        if name not in results:continue
        result=results[name]
        flows.append(dict(scenario=name,
                          load_kwh=energy(result,'native_load_kw'),
                          solar_ac_available_kwh=energy(result,'pv_available_kw'),
                          solar_ac_generated_kwh=energy(result,'pv_output_kw'),
                          solar_ac_curtailed_kwh=energy(result,'pv_curtailed_kw'),
                          grid_import_kwh=energy(result,'grid_import_kw'),
                          grid_export_kwh=energy(result,'grid_export_kw'),
                          battery_charge_kwh=energy(result,'battery_charge_kw'),
                          battery_discharge_kwh=energy(result,'battery_discharge_kw')))
    pairs=[('Solar panel + inverter, on-site use only','grid_only','pv_self_consumption'),
           ('Allow surplus export without battery','pv_self_consumption','pv_with_export')]
    if all(name in results for name in scenarios[3:]):
        pairs += [('Add battery without export','pv_self_consumption','storage_self_consumption'),
                  ('Add battery with surplus export','pv_with_export','storage_with_export'),
                  ('Allow surplus export with battery','storage_self_consumption','storage_with_export')]
    bridges=[];components=[]
    for label,before,after in pairs:
        old,new=results[before],results[after]
        old_bill,new_bill=old['bill'],new['bill']
        avoided={key:old_bill['import_charges'][key]-new_bill['import_charges'][key]
                 for key in ('generation','delivery','protected')}
        used={key:new_bill['credits_used'][key]-old_bill['credits_used'][key]
              for key in ('generation','delivery','bonus')}
        earned={key:new_bill['credits_earned'][key]-old_bill['credits_earned'][key]
                for key in ('generation','delivery','bonus')}
        bill_savings=old_bill['amount_due']-new_bill['amount_due']
        if abs(sum(avoided.values())+sum(used.values())-bill_savings)>1e-6:
            raise ValueError('Solar benefit components do not reconcile with the bill.')
        wear_change=new['degradation_cost']-old['degradation_cost']
        operating_savings=old['operating_cost']-new['operating_cost']
        if abs(bill_savings-wear_change-operating_savings)>1e-6:
            raise ValueError('Solar operating savings do not reconcile.')
        closing_change=sum(new_bill['closing_balance'].values())-sum(old_bill['closing_balance'].values())
        bridges.append(dict(comparison=label,from_scenario=before,to_scenario=after,
                            grid_import_reduction_kwh=energy(old,'grid_import_kw')-energy(new,'grid_import_kw'),
                            grid_export_change_kwh=energy(new,'grid_export_kw')-energy(old,'grid_export_kw'),
                            avoided_import_charges=sum(avoided.values()),
                            change_in_credits_used=sum(used.values()),
                            current_bill_savings=bill_savings,
                            battery_wear_change=wear_change,
                            operating_savings=operating_savings,
                            change_in_export_credits_earned=sum(earned.values()),
                            unspent_credit_change=closing_change))
        for group,amounts in (('avoided_import_charge',avoided),('change_in_credit_used',used),
                              ('change_in_export_credit_earned',earned)):
            for component,value in amounts.items():
                components.append(dict(comparison=label,category=group,component=component,dollars=value))
    return flows,bridges,components
