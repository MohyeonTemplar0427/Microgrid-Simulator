"""Cost priority and honest cycling proof status, with deterministic prices."""
from dataclasses import replace

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.dispatch import comed
from src.dispatch.battery import Battery
from src.billing.comed_cycles import parse_cycles, FIXED, DEMAND
from test_comed_dispatch import request, frame


def short_case():
    r=request("commercial","BESH")
    inputs,account,prices=frame(r)
    inputs=inputs.iloc[:96].copy()
    prices=replace(prices,values=prices.values.iloc[:48].copy())
    hours=prices.values.index.tz_convert("America/Chicago").hour
    prices.values[:]=np.where(hours<5,-150.,np.where(hours<18,200.,50.))
    cycles=parse_cycles([dict(start_date="2026-09-01",end_date="2026-09-02",billing_month="2026-09-01",
        kind="short_service",source="Synthetic declared two-day test; explicit charge factors",
        charge_factors={key:1. for key in FIXED|DEMAND|{"capacity"}})])
    return r,inputs,account,prices,cycles


@pytest.mark.parametrize("include_wear",[False,True])
def test_fixed_mode_incumbent_survives_failed_global_search(monkeypatch,include_wear):
    r,inputs,a,p,cycles=short_case()
    original=cp.Problem.solve
    captured={};calls=0
    def solve(problem,*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==3:
            for var in problem.variables():var.value=np.zeros(var.shape)
            raise cp.error.SolverError("Synthetic interrupted global refinement")
        result=original(problem,*args,**kwargs)
        if calls==1:captured["cost"]=problem.value
        if calls==2:
            assert not problem.is_mixed_integer()
            captured["local_throughput"]=problem.value
        return result
    monkeypatch.setattr(cp.Problem,"solve",solve)
    result=comed.optimize(inputs,a,p,r["battery"],wear=.03,include_wear=include_wear,billing_cycles=cycles)
    info=result["throughput_refinement"]
    assert calls==3
    assert result["cost_optimum_proven"] and not info["minimum_throughput_proven"]
    assert info["fixed_mode_status"]=="optimal" and info["global_status"]=="solver_error"
    assert info["selected_solution"]=="primary_modes_refined"
    assert info["selected_throughput_kwh"]==pytest.approx(captured["local_throughput"],abs=1e-5)
    assert info["selected_throughput_kwh"]<=info["primary_throughput_kwh"]+1e-6
    assert result["objective_usd"]<=captured["cost"]+1.1e-6
    d=result["dispatch"];b=r["battery"]
    assert np.minimum(d.battery_charge_kw,d.battery_discharge_kw).max()<1e-6
    energy=np.r_[d.battery_soc_kWh,result["terminal_energy_kwh"]]
    assert np.diff(energy)==pytest.approx(.5*(d.battery_charge_kw*b["charge_efficiency"]-
                                           d.battery_discharge_kw/b["discharge_efficiency"]),abs=1e-5)
    assert info["optimality_gap_kwh"] is None  # No invented bound after solver error.


@pytest.mark.parametrize("corrupt",["soc","cost","simultaneous","pv","power_limit","missing"])
def test_refinement_validator_rejects_corrupt_solver_incumbents(corrupt):
    r,inputs,a,p,cycles=short_case()
    result=comed.optimize(inputs,a,p,r["battery"],billing_cycles=cycles)
    d=result["dispatch"];costs=comed.compile_costs(pd.DatetimeIndex(d.timestamp),a,p,cycles)
    values=[d[k].to_numpy().copy() for k in ("battery_charge_kw","battery_discharge_kw","grid_import_kw","pv_output_kw")]
    values.append(np.r_[d.battery_soc_kWh,result["terminal_energy_kwh"]])
    if corrupt=="soc":values[4][1]+=1
    if corrupt=="cost":
        # Preserve power balance, battery operation and SOC; only cost worsens.
        marginal=costs.blocks[0][1].marginal_per_kwh
        i=np.flatnonzero((values[3]>.5)&(marginal>0))[0]
        values[2][i]+=.5;values[3][i]-=.5
    if corrupt=="simultaneous":
        # Preserve both power balance and SOC while violating negative-price modes.
        ratio=r["battery"]["charge_efficiency"]*r["battery"]["discharge_efficiency"]
        values[0][0]+=1;values[1][0]+=ratio;values[2][0]+=1-ratio
    if corrupt=="pv":values[3][0]=1000.
    if corrupt=="power_limit":values[0][0]=1000.
    if corrupt=="missing":values[0]=None
    assert comed._validated_refinement(values,load=inputs.native_load_kw.to_numpy(),pv=inputs.pv_available_kw.to_numpy(),
        battery=Battery(**r["battery"]),costs=costs,mask=comed._exclusive_intervals(costs,len(inputs)),
        optimum=result["solver_optimum_usd"],wear=0.,include_wear=False,
        maximum_throughput=result["throughput_refinement"]["selected_throughput_kwh"]) is None


def test_no_battery_does_not_claim_minimum_battery_cycling():
    r,inputs,a,p,cycles=short_case()
    result=comed.optimize(inputs,a,p,billing_cycles=cycles)
    assert result["throughput_refinement"]["status"]=="not_applicable"
    assert result["throughput_refinement"]["minimum_throughput_proven"] is None
    assert result["throughput_refinement"]["selected_throughput_kwh"]==0


def test_negligible_secondary_roundoff_keeps_better_incumbent_and_valid_proof(monkeypatch):
    variables=tuple(cp.Variable(1) for _ in range(4))+(cp.Variable(2),)
    selected=(np.array([1.]),np.array([0.]),np.array([1.]),np.array([0.]),np.array([0.,0.]))
    throughput=cp.sum(variables[0]+variables[1])
    def solve(problem,*args,**kwargs):
        for var,value in zip(variables,selected):var.value=value.copy()
        variables[0].value=np.array([1.+1.05e-6])
        problem._status="optimal"
        problem._value=float(throughput.value)
    monkeypatch.setattr(cp.Problem,"solve",solve)
    result,info=comed._refine_throughput(variables=variables,constraints=[],modes=None,
        primary_modes=None,throughput=throughput,selected=selected,
        validate=lambda arrays:tuple(v.copy() for v in arrays),time_limit=60,hours=1.)
    assert result[0][0]==1.  # Keep the slightly better feasible incumbent.
    assert info["minimum_throughput_proven"] and info["global_status"]=="optimal"
    assert info["optimality_gap_kwh"]==0.
    assert abs(info["global_lower_bound_kwh"]-1.)<=info["proof_tolerance_kwh"]
