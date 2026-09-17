"""Account-aware municipal storage optimization with exact bill reconciliation.

Enumerates monthly tier regimes (including decreasing C-1 tiers). The only
nonlinear energy term, proportional TOU allocation above a tier, has a filed
rounding residual bounded below one cent per cycle; report its certified gap.
"""
import cvxpy as cp
import numpy as np
import pandas as pd

from ..billing.municipal import RATES, bill_cycle, charge_lines, finite, svp_peak_mask
from .battery import Battery


def optimize_storage(tariff_id, load, *, cycle_start, cycle_end, account, battery,
                     degradation_cost_per_kWh=0.03):
    """Return baseline, feasible cyclic dispatch, exact bills and objective bound.

    No exports, PV, changed PF activation state or invented demand history.
    Each physical vector constraint covers the entire horizon.
    """
    if not isinstance(battery,Battery):
        battery=Battery(**battery)
    degradation=finite(degradation_cost_per_kWh,'Degradation')
    # This enforces tariff, coverage, account facts and interval validity first.
    baseline=bill_cycle(tariff_id,load,cycle_start=cycle_start,cycle_end=cycle_end,account=account)
    rate=RATES[tariff_id]
    stamps=pd.DatetimeIndex(pd.to_datetime(load.timestamp,utc=True)).tz_convert('America/Los_Angeles')
    native=load.grid_import_kw.to_numpy(dtype=float)
    n=len(native)
    mask=svp_peak_mask(stamps) if rate.utility=='svp' else np.ones(n,dtype=bool)
    prior=max(account.get('previous_11_month_peaks_kw',{}).values(),default=0)
    pf_active=False
    if rate.schedule=='CB-3':
        threshold=.1*prior
        lower=float(np.maximum(native[mask]-battery.max_discharge_kw,0).max(initial=0))
        upper=float((native[mask]+battery.max_charge_kw).max(initial=0))
        if lower>=threshold:
            pf_active=True
        elif upper>=threshold:
            raise ValueError('CB-3 storage could cross the historical low-load PF exemption boundary. Optimization of this discontinuous case is not supported; use bill replay.')
    tier=rate.tier_kwh
    if rate.utility=='amp' and rate.schedule=='D-1':
        summer=5<=stamps[0].month<=10
        tier=(211 if summer else 253) if account['heating_source']=='gas_or_other' else (258 if summer else 473)
    regimes=['flat'] if tier is None else ['lower','upper']
    candidates=[]
    lower_bounds=[]
    for regime in regimes:
        charge=cp.Variable(n,nonneg=True)
        discharge=cp.Variable(n,nonneg=True)
        energy=cp.Variable(n+1)
        grid=cp.Variable(n,nonneg=True)
        constraints=[charge<=battery.max_charge_kw,discharge<=battery.max_discharge_kw,
            energy[0]==battery.energy_kWh,energy[-1]==battery.energy_kWh,
            energy>=battery.minimum_energy_kWh,energy<=battery.maximum_energy_kWh,
            energy[1:]==energy[:-1]+.25*(battery.charge_efficiency*charge-discharge/battery.discharge_efficiency),
            grid==native+charge-discharge]
        q=.25*cp.sum(grid)
        p=.25*cp.sum(grid[svp_peak_mask(stamps)])
        tou=account.get('time_of_use',False)
        if regime=='lower':
            constraints.append(q<=tier)
        elif regime=='upper':
            constraints.append(q>=tier)
        idx=1 if regime=='upper' else 0
        residual_bound=0.0
        if tou:
            energy_cost=rate.tou_offpeak[idx]*q+(rate.tou_peak[idx]-rate.tou_offpeak[idx])*p
            if regime=='upper':
                # E = linear part + tier * delta * peak_kWh / total_kWh.
                # 0 <= ratio <= 1 yields a rigorous lower-bound objective.
                delta=(rate.tou_peak[0]-rate.tou_offpeak[0])-(rate.tou_peak[1]-rate.tou_offpeak[1])
                energy_cost+=tier*(rate.tou_offpeak[0]-rate.tou_offpeak[1])+min(0,tier*delta)
                residual_bound=abs(tier*delta)
        else:
            energy_cost=rate.energy[idx]*q
            if regime=='upper':
                energy_cost+=tier*(rate.energy[0]-rate.energy[1])
        billed=cp.Variable(nonneg=True)
        if rate.demand:
            peak=cp.Variable(nonneg=True)
            constraints += [peak>=grid[mask]]
            constraints += [billed>=peak,billed>=(peak+prior)/2] if rate.utility=='svp' else [billed==peak]
        else:
            constraints.append(billed==0)
        lines=charge_lines(rate,energy_cost,billed,q,account,cb3_pf_active=pf_active,maximum=cp.maximum)
        objective=sum(lines.values())+degradation*.25*cp.sum(charge+discharge)
        problem=cp.Problem(cp.Minimize(objective),constraints)
        problem.solve(solver='SCIPY',scipy_options={'method':'highs'})
        if problem.status=='infeasible':
            continue
        if problem.status!='optimal':
            raise ValueError(f'Municipal optimization did not converge: {problem.status}.')
        c=np.maximum(np.asarray(charge.value),0)
        d=np.maximum(np.asarray(discharge.value),0)
        if np.max(np.minimum(c,d))>1e-6:
            # A lower bound on tier usage can make dissipative cycling useful
            # in an otherwise dominated regime. Enforce physical exclusivity
            # only when the continuous relaxation actually needs it.
            charging=cp.Variable(n,boolean=True)
            constraints += [charge<=battery.max_charge_kw*charging,
                            discharge<=battery.max_discharge_kw*(1-charging)]
            problem=cp.Problem(cp.Minimize(objective),constraints)
            problem.solve(solver='SCIPY',scipy_options={'method':'highs','time_limit':60,'mip_rel_gap':1e-9})
            if problem.status=='infeasible':
                continue
            if problem.status!='optimal':
                raise ValueError('Physical charge/discharge optimization did not converge within its limit.')
            c=np.maximum(np.asarray(charge.value),0)
            d=np.maximum(np.asarray(discharge.value),0)
            if np.max(np.minimum(c,d))>1e-6:
                raise ValueError('Optimizer returned simultaneous charge/discharge; no schedule accepted.')
        lower_bounds.append(float(problem.value))
        actual=native+c-d
        actual[np.abs(actual)<1e-8]=0
        state=np.r_[battery.energy_kWh,battery.energy_kWh+np.cumsum(.25*(battery.charge_efficiency*c-d/battery.discharge_efficiency))]
        if (actual.min()<-1e-7 or state.min()<battery.minimum_energy_kWh-1e-6 or state.max()>battery.maximum_energy_kWh+1e-6 or abs(state[-1]-state[0])>1e-6):
            raise ValueError('Optimized schedule failed physical balance or terminal-SOC validation.')
        dispatch=pd.DataFrame({'timestamp':stamps,'native_load_kw':native,'grid_import_kw':actual,
            'charge_kw':c,'discharge_kw':d,'energy_start_kwh':state[:-1],'energy_end_kwh':state[1:]})
        bill=bill_cycle(tariff_id,dispatch,cycle_start=cycle_start,cycle_end=cycle_end,account=account)
        wear=degradation*.25*float((c+d).sum())
        # The bill remains authoritative: objective approximation cannot leak
        # into exports or itemized utility charges.
        objective_actual=bill['total']+wear
        scale=1.0285 if rate.utility=='svp' else 1.075
        if objective_actual-float(problem.value)>residual_bound*scale+1e-4:
            raise ValueError('Dispatch objective and authoritative bill do not reconcile.')
        candidates.append(dict(dispatch=dispatch,bill=bill,degradation_cost=wear,
                               total_explicit_cost=objective_actual,regime=regime))
    if not candidates:
        raise ValueError('No feasible battery dispatch for the complete billing cycle.')
    best=min(candidates,key=lambda x:x['total_explicit_cost'])
    # Baseline is a feasible zero-throughput candidate; never offer worse costs.
    if baseline['total']<best['total_explicit_cost']:
        best=dict(dispatch=pd.DataFrame({'timestamp':stamps,'native_load_kw':native,'grid_import_kw':native,
            'charge_kw':0.,'discharge_kw':0.,'energy_start_kwh':battery.energy_kWh,'energy_end_kwh':battery.energy_kWh}),
            bill=baseline,degradation_cost=0.,total_explicit_cost=baseline['total'],regime='no_cycling')
    gap=max(0,best['total_explicit_cost']-min(lower_bounds))
    return {**best,'baseline_bill':baseline,'objective_lower_bound':min(lower_bounds),
            'optimality_gap_bound_dollars':gap,'solver':'scipy-highs',
            'warnings':['Storage finishes at its starting energy; grid export and onsite generation are disabled.',
                        'Existing account power-factor state and rate assignment remain fixed; no future enrollment changes are inferred.']+
                       ([f'Proportional TOU tier optimization is certified within ${gap:.6f} of the model optimum; reported bills use the exact filed rates.'] if gap>1e-5 else [])}
