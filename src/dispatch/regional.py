"""Retail-cycle optimization using the authoritative regional charge expressions.

This is historical perfect foresight inside each billing cycle. Linked studies
are explicitly rolling-cycle decisions, not a jointly optimized annual bill.

A continuous battery-duty relaxation supplies an outer lower bound. Only an
independently physical, authoritatively rebilled schedule attaining that proven
bound is accepted. All tariff and grid-direction selectors remain integral;
nonphysical or unproven candidates fall back to the full battery-mode MILP.
"""
from copy import deepcopy
import time

import cvxpy as cp
import numpy as np
import pandas as pd

from ..billing.regional import adapter, calculate_cycle
from ..billing.regional_math import BillingMath
from .battery import Battery


def optimize_cycle(inputs,utility,account,battery=None,*,state=None,wear=0.,include_wear=False,
                   terminal_energy=None,export_enabled=False,grid_charging=False,time_limit=90,
                   credit_objective_policy="exclude_opening_credits",equipment=None):
    index=pd.DatetimeIndex(inputs.timestamp)
    load,pv=(np.asarray(inputs[k],dtype=float) for k in ("native_load_kw","pv_available_kw"))
    if any(v.shape!=(len(index),) or not np.isfinite(v).all() or (v<0).any() for v in (load,pv)):
        raise ValueError("Supply finite native demand and available AC PV for every interval.")
    if (isinstance(wear,bool) or not isinstance(wear,(int,float)) or not np.isfinite(wear) or wear<0
            or type(include_wear) is not bool or type(export_enabled) is not bool or type(grid_charging) is not bool):
        raise ValueError("Wear and operating choices must be finite and explicit.")
    if isinstance(time_limit,bool) or not isinstance(time_limit,(int,float)) or not np.isfinite(time_limit) or time_limit<=0:
        raise ValueError("Regional solver time limit must be finite and positive.")
    b=Battery(**battery) if battery is not None else None
    if terminal_energy is not None and (b is None or isinstance(terminal_energy,bool) or not isinstance(terminal_energy,(int,float))
            or not np.isfinite(terminal_energy) or not b.minimum_energy_kWh<=terminal_energy<=b.maximum_energy_kWh):
        raise ValueError("Terminal battery energy must be finite and within configured SOC bounds.")
    equipment=equipment or {"pv":bool(pv.max()>0),"battery":b is not None,
                            "pv_ac_kw":float(pv.max()),"battery_kw":b.max_discharge_kw if b else 0.}
    module=adapter(utility)
    module.validate_account(account,index,equipment=equipment)
    if hasattr(module,"validate_state"):
        module.validate_state(account,index,state=state,equipment=equipment)
    objective_account,objective_state=(module.objective_inputs(account,state,credit_objective_policy)
        if hasattr(module,"objective_inputs") else (deepcopy(account),deepcopy(state)))
    dt=BillingMath(index).hours;n=len(index)
    if b is None and not pv.any():
        dispatch=inputs.copy()
        for key,val in {"grid_import_kw":load,"grid_export_kw":np.zeros(n),"pv_output_kw":np.zeros(n),
                "pv_curtailed_kw":np.zeros(n),"battery_charge_kw":np.zeros(n),
                "battery_discharge_kw":np.zeros(n),"energy_kWh":np.zeros(n)}.items():
            dispatch[key]=val
        bill=calculate_cycle(utility,index,load,np.zeros(n),account,state=state,equipment=equipment)
        objective_bill=calculate_cycle(utility,index,load,np.zeros(n),objective_account,state=objective_state,equipment=equipment)
        return {"dispatch":dispatch,"bill":bill,"next_state":bill["next_state"],"wear_usd":0.,
            "optimization_bill":objective_bill,"credit_objective_policy":credit_objective_policy,
            "objective_usd":objective_bill["unrounded_total_usd"],"reconciliation_difference_usd":0.,
            "cost_optimum_proven":None,"refinement_status":"not_applicable","minimum_cycling_proven":None,
            "terminal_energy_kwh":None,"warnings":[],"strategy":"grid_only","solver":"not_required",
            "cost_proof_method":"direct_bill_no_dispatch","primary_lower_bound_usd":None,"primary_optimality_gap_usd":None,
            "primary_proof_tolerance_usd":None,"cycling_proof_method":"not_applicable","cycling_lower_bound_kwh":None,
            "cycling_optimality_gap_kwh":None,"cycling_proof_tolerance_kwh":None,
            "relaxation_status":"not_applicable","relaxed_lower_bound_usd":None,"strict_fallback_used":False}
    max_import=max(float(load.max())+(b.max_charge_kw if b else 0),1.)
    max_export=max(float(pv.max()),1.)
    constraints=[]
    math=BillingMath(index,convex=True,power_bound=max(max_import,max_export),constraints=constraints)
    lower_import=np.maximum(load-pv-(b.max_discharge_kw if b else 0.),0.)
    upper_import=load+(b.max_charge_kw if b else 0.)
    energy_upper=float(load.sum()*dt)
    if b:
        delta=(terminal_energy if terminal_energy is not None else b.maximum_energy_kWh)-b.energy_kWh
        charge_energy_upper=(n*dt+b.discharge_efficiency*delta/b.max_discharge_kw)/(1/b.max_charge_kw+b.charge_efficiency*b.discharge_efficiency/b.max_discharge_kw)
        energy_upper+=(1-b.charge_efficiency*b.discharge_efficiency)*charge_energy_upper+b.discharge_efficiency*delta
    imp=math.register_power(cp.Variable(n,nonneg=True),lower_import,upper_import,energy_upper=energy_upper+1e-7)
    exp=math.register(cp.Variable(n,nonneg=True),0,max_export)
    output=math.register(cp.Variable(n,nonneg=True),0,float(pv.max()))
    constraints.extend([imp>=lower_import,imp<=upper_import,exp<=max_export,output<=pv,
        dt*cp.sum(imp)<=energy_upper+1e-7])
    if export_enabled:
        direction=cp.Variable(n,boolean=True)
        constraints.extend([imp<=max_import*direction,exp<=max_export*(1-direction),exp<=output])
    else:
        constraints.append(exp==0)
    if b:
        charge=math.register(cp.Variable(n,nonneg=True),0,b.max_charge_kw)
        discharge=math.register(cp.Variable(n,nonneg=True),0,b.max_discharge_kw)
        energy=cp.Variable(n+1)
        # Only battery operating modes are relaxed. Tariff selectors and grid
        # import/export direction remain exact integers in both models.
        relaxed_mode=cp.Variable(n)
        strict_mode=cp.Variable(n,boolean=True)
        relaxed_modes=[relaxed_mode>=0,relaxed_mode<=1,charge<=b.max_charge_kw*relaxed_mode,
                       discharge<=b.max_discharge_kw*(1-relaxed_mode)]
        strict_modes=[charge<=b.max_charge_kw*strict_mode,discharge<=b.max_discharge_kw*(1-strict_mode)]
        constraints.extend([discharge<=load,energy[0]==b.energy_kWh,energy>=b.minimum_energy_kWh,
            energy<=b.maximum_energy_kWh,
            energy[1:]==energy[:-1]+dt*(charge*b.charge_efficiency-discharge/b.discharge_efficiency)])
        if export_enabled:
            constraints.append(discharge<=b.max_discharge_kw*direction)
        if terminal_energy is not None:
            constraints.append(energy[-1]==terminal_energy)
        if not grid_charging:
            # Separate flows establish PV-origin charging; a price signal alone
            # must never authorize grid energy to receive solar export credits.
            pv_load=cp.Variable(n,nonneg=True)
            constraints.extend([pv_load+charge+exp==output,pv_load+discharge+imp==load])
    else:
        charge=discharge=np.zeros(n);energy=None
    constraints.append(imp+output+discharge==load+charge+exp)
    charges=module.charge_lines(index,imp,exp,objective_account,math=math,state=objective_state)
    utility_cost=sum(charges["lines"].values())
    wear_expression=wear*dt*math.sum(charge+discharge)
    score=utility_cost+(wear_expression if include_wear else 0.)
    started=time.monotonic()
    proof_tolerance=lambda bound:max(.0001,abs(bound)*1e-7)
    throughput_tolerance=lambda bound:max(1e-5,abs(bound)*1e-8)

    def values():
        return [np.asarray(x.value if hasattr(x,"value") else x,dtype=float).copy() for x in (imp,exp,output,charge,discharge)] + [
            np.asarray(energy.value).copy() if energy is not None else np.zeros(n+1)]

    def validate_candidate(candidate,bound):
        """Independent physical feasibility and authoritative objective replay.

        No relaxed duty variable is evidence of executable battery operation.
        A physical candidate attaining an outer-relaxation lower bound proves
        the original optimum within the explicitly reported numerical tolerance.
        """
        g,x,p,c,d,e=(np.asarray(v,dtype=float).copy() for v in candidate)
        if (any(v.shape!=(n,) for v in (g,x,p,c,d)) or e.shape!=(n+1,)
                or not all(np.isfinite(v).all() for v in (g,x,p,c,d,e))
                or np.max(abs(g+p+d-load-c-x))>1e-5
                or min(np.min(v) for v in (g,x,p,c,d)) < -1e-5
                or np.max(p-pv)>1e-5 or np.max(np.minimum(g,x))>1e-5
                or np.max(np.minimum(c,d))>1e-5 or np.max(d-load)>1e-5
                or np.max(x-p)>1e-5 or np.max(np.minimum(x,d))>1e-5
                or not export_enabled and np.max(x)>1e-5):
            raise ValueError("Optimized schedule failed independent interval power, equipment or exclusivity checks.")
        g,x,c,d=(np.maximum(v,0.) for v in (g,x,c,d))
        p=np.clip(p,0.,pv)
        if np.max(abs(g+p+d-load-c-x))>1e-5:
            raise ValueError("Boundary-roundoff projection does not preserve interval power balance.")
        if b:
            if (np.max(abs(np.diff(e)-dt*(c*b.charge_efficiency-d/b.discharge_efficiency)))>1e-5
                    or abs(e[0]-b.energy_kWh)>1e-5 or e.min()<b.minimum_energy_kWh-1e-5
                    or e.max()>b.maximum_energy_kWh+1e-5
                    or c.max()>b.max_charge_kw+1e-5 or d.max()>b.max_discharge_kw+1e-5
                    or terminal_energy is not None and abs(e[-1]-terminal_energy)>1e-5
                    or not grid_charging and np.max(c+x-p)>1e-5):
                raise ValueError("Optimized schedule failed independent SOC, PV-origin charging or power-limit checks.")
        objective_bill=calculate_cycle(utility,index,g,x,objective_account,state=objective_state,equipment=equipment)
        wear_usd=float(wear*dt*np.sum(c+d))
        recalculated=objective_bill["unrounded_total_usd"]+(wear_usd if include_wear else 0)
        difference=abs(recalculated-bound)
        if not np.isfinite(recalculated) or difference>proof_tolerance(bound):
            raise ValueError(f"Authoritative regional bill does not reconcile with dispatch objective (${difference:.6f}).")
        return (g,x,p,c,d,e),objective_bill,wear_usd,recalculated,difference

    def solve(problem,limit):
        try:
            problem.solve(solver="SCIPY",scipy_options={"method":"highs","time_limit":limit,"mip_rel_gap":0.})
        except cp.error.SolverError:
            return False
        return problem.status=="optimal" and problem.value is not None and np.isfinite(problem.value)

    selected=None;accepted=None;optimum=None
    refinement="not_applicable";refinement_proven=None;warnings=[]
    proof_method="strict_milp";cycling_proof="not_applicable"
    relaxation_status="not_applicable";fallback=False;relaxed_lower_bound=None;cycling_bound=None
    if b:
        relaxed_constraints=constraints+relaxed_modes
        relaxed_problem=cp.Problem(cp.Minimize(score),relaxed_constraints)
        if solve(relaxed_problem,min(10.,time_limit)):
            relaxed_lower_bound=float(relaxed_problem.value)
            primary_candidate=values()
            refined=cp.Problem(cp.Minimize(dt*cp.sum(charge+discharge)),
                relaxed_constraints+[score<=relaxed_lower_bound+1e-6])
            refined_proven=solve(refined,min(10.,time_limit))
            candidates=[(values(),True,float(refined.value))] if refined_proven else []
            candidates.append((primary_candidate,False,None))
            relaxation_status="rejected_nonphysical_or_unreconciled"
            for candidate,minimum_proven,throughput_bound in candidates:
                try:
                    checked=validate_candidate(candidate,relaxed_lower_bound)
                except ValueError:
                    continue
                if minimum_proven and abs(dt*np.sum(checked[0][3]+checked[0][4])-throughput_bound)>throughput_tolerance(throughput_bound):
                    continue
                selected=candidate;accepted=checked;optimum=relaxed_lower_bound;cycling_bound=throughput_bound
                proof_method="physical_relaxation_bound";relaxation_status="accepted_physical"
                refinement="optimal" if minimum_proven else "retained_primary"
                refinement_proven=minimum_proven
                cycling_proof="physical_relaxation_bound" if minimum_proven else "not_proven"
                break
        else:
            relaxation_status="unproven_"+str(relaxed_problem.status)
    if selected is None:
        fallback=b is not None
        exact_constraints=constraints+(strict_modes if b else [])
        problem=cp.Problem(cp.Minimize(score),exact_constraints)
        if not solve(problem,time_limit):
            raise ValueError("Regional primary cost optimum was not proven: "+str(problem.status))
        optimum=float(problem.value);selected=values()
        accepted=validate_candidate(selected,optimum)
        if b:
            secondary=cp.Problem(cp.Minimize(dt*cp.sum(charge+discharge)),
                exact_constraints+[score<=optimum+1e-6])
            if solve(secondary,min(15.,time_limit)):
                candidate=values()
                try:
                    checked=validate_candidate(candidate,optimum)
                except ValueError:
                    checked=None
                if checked is not None and abs(dt*np.sum(checked[0][3]+checked[0][4])-float(secondary.value))<=throughput_tolerance(float(secondary.value)):
                    selected=candidate;accepted=checked;cycling_bound=float(secondary.value)
                    refinement="optimal";refinement_proven=True;cycling_proof="strict_milp"
            if refinement_proven is not True:
                refinement="retained_primary";refinement_proven=False;cycling_proof="not_proven"
    if b and refinement_proven is not True:
        warnings.append("Primary cycle cost optimum proven; minimum cycling was not proven. The saved primary schedule is retained.")
    (g,x,p,c,d,e),objective_bill,wear_usd,recalculated,difference=accepted
    bill=calculate_cycle(utility,index,g,x,account,state=state,equipment=equipment)
    dispatch=inputs.copy()
    for key,val in (("grid_import_kw",g),("grid_export_kw",x),("pv_output_kw",p),
            ("pv_curtailed_kw",pv-p),("battery_charge_kw",c),("battery_discharge_kw",d),("energy_kWh",e[:-1])):
        dispatch[key]=np.maximum(val,0)
    return {"dispatch":dispatch,"bill":bill,"next_state":bill["next_state"],"wear_usd":wear_usd,
        "optimization_bill":objective_bill,"credit_objective_policy":credit_objective_policy,
        "objective_usd":optimum,"recalculated_objective_usd":recalculated,
        "reconciliation_difference_usd":difference,"cost_optimum_proven":True,
        "refinement_status":refinement,"minimum_cycling_proven":refinement_proven,
        "terminal_energy_kwh":float(e[-1]) if b else None,"warnings":warnings,
        "strategy":"historical_perfect_foresight_per_cycle","solver":"SciPy HiGHS MILP/LP",
        "cost_proof_method":proof_method,"primary_lower_bound_usd":optimum,
        "primary_optimality_gap_usd":max(0.,recalculated-optimum),"primary_proof_tolerance_usd":proof_tolerance(optimum),
        "cycling_proof_method":cycling_proof,"cycling_lower_bound_kwh":cycling_bound,
        "cycling_optimality_gap_kwh":max(0.,dt*float(np.sum(c+d))-cycling_bound) if cycling_bound is not None else None,
        "cycling_proof_tolerance_kwh":throughput_tolerance(cycling_bound) if cycling_bound is not None else None,
        "relaxation_status":relaxation_status,
        "relaxed_lower_bound_usd":relaxed_lower_bound,"strict_fallback_used":fallback,
        "elapsed_seconds":time.monotonic()-started}
