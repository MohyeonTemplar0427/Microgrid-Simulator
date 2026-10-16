"""Reduced mode formulation agrees with a fully exclusive MILP oracle."""
import numpy as np
import pandas as pd
import pytest
from dataclasses import replace
from test_comed_dispatch import request, frame
from src.dispatch import comed
from src.billing.comed_cycles import parse_cycles, FIXED, DEMAND


@pytest.mark.parametrize("kind", ["residential","commercial"])
@pytest.mark.parametrize("price_case", ["positive","mixed","zero"])
@pytest.mark.parametrize("include_wear", [False,True])
def test_reduced_modes_match_all_binary_objective_and_physics(monkeypatch,kind,price_case,include_wear):
    r=request(kind,"BESH");inputs,account,prices=frame(r)
    inputs=inputs.iloc[:96].copy()
    prices=replace(prices,values=prices.values.iloc[:48].copy())
    cycles=parse_cycles([dict(start_date="2026-09-01",end_date="2026-09-02",billing_month="2026-09-01",
        kind="short_service",source="Synthetic short-service oracle fixture; every charge factor explicitly one",
        charge_factors={k:1. for k in FIXED | DEMAND | {"capacity"}})])
    hours=prices.values.index.hour
    if price_case=="mixed":prices.values[:]=np.where(hours<5,-150.,200.)
    if price_case=="zero":
        # Cancel the *total* energy marginal price, including signed riders.
        costs=comed.compile_costs(pd.DatetimeIndex(inputs.timestamp),account,prices,cycles)
        multiplier=comed.calculate(pd.Series(0.,index=costs.index),account,prices,cycles)["cycles"][0]["source"]["hourly_energy_multiplier"]
        prices.values[:]-=costs.blocks[0][1].marginal_per_kwh[0]*1000/multiplier
    reduced=comed.optimize(inputs,account,prices,r["battery"],wear=.03,include_wear=include_wear,billing_cycles=cycles)
    monkeypatch.setattr(comed,"_exclusive_intervals",lambda costs,n:np.ones(n,dtype=bool))
    oracle=comed.optimize(inputs,account,prices,r["battery"],wear=.03,include_wear=include_wear,billing_cycles=cycles)
    assert reduced["objective_usd"]==pytest.approx(oracle["objective_usd"],abs=1e-4)
    assert reduced["throughput_refinement"]["minimum_throughput_proven"]
    assert oracle["throughput_refinement"]["minimum_throughput_proven"]
    assert reduced["throughput_refinement"]["selected_throughput_kwh"]==pytest.approx(
        oracle["throughput_refinement"]["selected_throughput_kwh"],abs=1e-4)
    assert abs(reduced["bill"]["subtotal_usd"]-oracle["bill"]["subtotal_usd"]) <= reduced["rounding_bound_usd"]+oracle["rounding_bound_usd"]
    d=reduced["dispatch"];dt=.5;b=r["battery"]
    assert np.max(np.minimum(d.battery_charge_kw,d.battery_discharge_kw))<1e-6
    assert np.max(abs(d.grid_import_kw+d.pv_output_kw+d.battery_discharge_kw-d.native_load_kw-d.battery_charge_kw))<1e-5
    assert d.grid_import_kw.min()>=0 and d.pv_output_kw.min()>=0 and d.pv_curtailed_kw.min()>=0
    e=np.r_[d.battery_soc_kWh,reduced["terminal_energy_kwh"]]
    assert np.max(abs(np.diff(e)-dt*(d.battery_charge_kw*b["charge_efficiency"]-d.battery_discharge_kw/b["discharge_efficiency"])))<1e-5


def test_removing_positive_price_cycle_preserves_soc_and_reduces_supply():
    from src.dispatch.battery import Battery
    b=Battery(**request()["battery"])
    c=np.array([2.,2.,2.]);d=np.array([1.,1.,1.]);g=np.array([4.,0.,4.]);p=np.array([1.,3.,1.])
    original_energy=c*b.charge_efficiency-d/b.discharge_efficiency
    a,z,imports,solar=comed._remove_dominated_cycles(c,d,g,p,b,np.array([False,False,True]))
    assert np.allclose(a*b.charge_efficiency-z/b.discharge_efficiency,original_energy)
    assert np.allclose(imports+solar+z-a,g+p+d-c)
    assert imports[0]<g[0] and solar[1]<p[1] # PV absorbs the reduction when import is zero
    assert min(a[0],z[0])<1e-12 and min(a[1],z[1])<1e-12
    assert a[2]==c[2] and z[2]==d[2] # Never remove a negative-price pair by this argument
