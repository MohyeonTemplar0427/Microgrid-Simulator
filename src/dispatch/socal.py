"""PV self-consumption and storage with the authoritative SoCal bill objective."""
import numpy as np
import pandas as pd
import cvxpy as cp
from ..billing.socal import PLANS, bill, charge_lines, interval_index, number
from .battery import Battery


def optimize(key,inputs,account,start,end,battery,wear):
 idx=interval_index(inputs,start,end);n=len(idx)
 load=np.asarray(inputs.native_load_kw,dtype=float);pv=np.asarray(inputs.pv_available_kw,dtype=float)
 if not np.isfinite(load).all() or not np.isfinite(pv).all() or min(load.min(),pv.min())<0:raise ValueError('Invalid load/PV profile.')
 if PLANS.get(key,{}).get('solar_programs')==['none'] and np.any(pv>0):raise ValueError('This Billing Plan does not support PV/customer-generation settlement.')
 number(wear,'Degradation cost',0,10)
 baseline=inputs.copy();baseline['grid_import_kw']=load;baseline['grid_export_kw']=0.
 baseline_bill=bill(key,baseline,account,start,end)
 solar=inputs.copy();solar['grid_import_kw']=np.maximum(load-pv,0);solar['grid_export_kw']=0.
 solar_bill=bill(key,solar,account,start,end)
 if battery is None:return {'baseline_bill':baseline_bill,'solar_bill':solar_bill,'bill':solar_bill,'dispatch':solar,'degradation_cost':0.,'objective_gap':0.}
 b=Battery(**battery)
 charge=cp.Variable(n,nonneg=True);discharge=cp.Variable(n,nonneg=True);energy=cp.Variable(n+1)
 grid=cp.Variable(n,nonneg=True);output=cp.Variable(n,nonneg=True)
 constraints=[charge<=b.max_charge_kw,discharge<=b.max_discharge_kw,output<=pv,
  grid+output+discharge==load+charge,energy[0]==b.energy_kWh,energy[-1]==b.energy_kWh,
  energy>=b.capacity_kWh*b.SOC_min,energy<=b.capacity_kWh*b.SOC_max,
  energy[1:]==energy[:-1]+.25*(charge*b.charge_efficiency-discharge/b.discharge_efficiency)]
 # Stay within the deliberately bounded schedule scope during charging too.
 if key.startswith('ladwp_a-1'):constraints.append(grid<=29.999999)
 if key.startswith('sce_tou-gs-1'):constraints.append(grid<=20)
 if key=='sce_tou-gs-2-d':constraints.append(grid<=199.999999)
 if key=='sce_tou-gs-3-d':constraints.append(grid<=500)
 if key.startswith('gwp_l-2'):
  constraints.extend([grid<=19.999999,cp.sum(grid)*.25<=5000*len(idx.normalize().unique())/30-1e-5])
 lines=charge_lines(key,idx,grid,account,convex=True,constraints=constraints)
 degradation=wear*.25*cp.sum(charge+discharge)
 problem=cp.Problem(cp.Minimize(sum(lines.values())+degradation),constraints)
 if not problem.is_dcp():raise ValueError('Unsupported nonconvex billing objective.')
 problem.solve(solver='SCIPY' if problem.is_mixed_integer() else 'CLARABEL')
 if problem.status!='optimal':raise ValueError('Dispatch solver did not reach an optimal solution: '+str(problem.status))
 if np.max(np.minimum(charge.value,discharge.value))>1e-5:raise ValueError('Simultaneous charge/discharge: dispatch rejected.')
 out=inputs.copy();out['grid_import_kw']=np.maximum(grid.value,0);out['grid_export_kw']=0.
 out['pv_output_kw']=np.maximum(output.value,0);out['pv_curtailed_kw']=pv-out.pv_output_kw
 out['battery_charge_kw']=np.maximum(charge.value,0);out['battery_discharge_kw']=np.maximum(discharge.value,0);out['energy_kWh']=energy.value[:-1]
 authoritative=bill(key,out,account,start,end);degradation=float(degradation.value)
 gap=abs(authoritative['total']+degradation-problem.value)
 if gap>max(.02,abs(problem.value)*1e-6):raise ValueError('Bill and optimized objective do not reconcile.')
 return {'baseline_bill':baseline_bill,'solar_bill':solar_bill,'bill':authoritative,'dispatch':out,'degradation_cost':degradation,'objective_gap':gap}
