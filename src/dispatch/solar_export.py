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
        out=frame.copy();out['grid_import_kw']=np.maximum(imports,0);out['grid_export_kw']=np.maximum(exports,0)
        out['pv_output_kw']=np.maximum(output,0);out['pv_curtailed_kw']=np.maximum(pv-output,0)
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
