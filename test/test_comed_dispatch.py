"""Tariff-aware physical dispatch, independent meter peaks and signed prices."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pandas as pd
import pytest

from src.local_web.comed_simulation import defaults, prepare
from src.billing.comed_costs import compile_costs, calculate
from src.dispatch.comed import optimize
from src.billing.comed_commercial import ComEdCommercialAccount


def request(kind="residential", supply="BES", minutes=30):
    r=defaults(kind);r['timestep_minutes']=minutes
    r['account'].update(ordinary_import_only_confirmed=True,supply=supply)
    r['operating_contract'].update(interconnection_confirmed=True,standard_tariff_confirmed=True,
                                   grid_charging_confirmed=True,reference='Synthetic approved non-export test')
    if supply=='BESH':
        r['account'].update(capacity_obligation_kw=3.,capacity_source='Synthetic fixed account obligation')
        r['prices']={'mode':'constant_example','usd_per_mwh':50.,'csv':None,
                     'source':'Synthetic COMED residual hourly LMP','basis_confirmed':True}
    return r


def frame(r):
    g,load,a,p=prepare(r)
    h=g.index.hour;weekday=g.index.dayofweek<5
    power=np.where((h>=9)&(h<18)&weekday,36.,8.) if isinstance(a, ComEdCommercialAccount) else np.where((h>=17)&(h<22),2.,.6)
    pv=np.where((h>=10)&(h<15),20. if power.max()>5 else 3.,0.)
    return pd.DataFrame({'timestamp':g.index,'native_load_kw':power,'pv_available_kw':pv}),a,p


@pytest.mark.parametrize('kind',['residential','commercial'])
@pytest.mark.parametrize('supply',['BES','BESH'])
def test_authoritative_cost_expression_dispatch_and_fixed_capacity(kind,supply):
    r=request(kind,supply);f,a,p=frame(r)
    costs=compile_costs(pd.DatetimeIndex(f.timestamp),a,p)
    # Arbitrary loads exercise all signed rider rates, not just the optimizer's
    # optimum. The authoritative Decimal calculator remains the final bill.
    varied=np.linspace(1.,43.,len(f))
    bill=calculate(pd.Series(varied,index=costs.index),a,p)
    assert abs(bill['subtotal_usd']-costs.subtotal(varied))<=costs.rounding_bound_usd
    result=optimize(f,a,p,r['battery'])
    d=result['dispatch'];dt=costs.hours
    assert np.max(np.minimum(d.battery_charge_kw,d.battery_discharge_kw))<1e-6
    assert np.max(abs(d.grid_import_kw+d.pv_output_kw+d.battery_discharge_kw-f.native_load_kw-d.battery_charge_kw))<1e-5
    assert d.grid_export_kw.eq(0).all() and (d.pv_curtailed_kw>=0).all()
    assert np.max(abs(d.pv_output_kw+d.pv_curtailed_kw-f.pv_available_kw))<1e-6
    end=d.battery_soc_kWh.iloc[-1]+dt*(d.battery_charge_kw.iloc[-1]*.95-d.battery_discharge_kw.iloc[-1]/.95)
    assert end==pytest.approx(r['battery']['energy_kWh'],abs=1e-5)
    assert abs(result['rounding_difference_usd'])<=result['rounding_bound_usd']
    assert result['recalculated_objective_usd']==result['bill']['subtotal_usd']
    if supply=='BESH':
        original=calculate(pd.Series(f.native_load_kw.values,index=costs.index),a,p)
        assert next(x['amount_usd'] for x in result['bill']['lines'] if x['name']=='capacity')==next(x['amount_usd'] for x in original['lines'] if x['name']=='capacity')
    else:
        assert 'capacity' not in [x['name'] for x in result['bill']['lines']]


def test_mkd_averages_two_quarters_and_excludes_nerc_holiday_and_night():
    r=request('commercial',minutes=15);g,_,a,p=prepare(r);power=np.ones(len(g.index))
    for when,value in [('2026-09-01 09:00',80),('2026-09-01 09:15',0),('2026-09-07 10:00',200),
                       ('2026-09-07 10:15',200),('2026-09-02 22:00',160),('2026-09-02 22:15',160)]:
        power[g.index.get_loc(pd.Timestamp(when,tz='America/Chicago'))]=value
    result=calculate(pd.Series(power,index=g.index),a,p);costs=compile_costs(g.index,a,p)
    assert result['billed_mkd_kw']==40 and result['overall_30min_peak_kw']==200
    assert costs.billed_peak(power)==40
    assert abs(result['subtotal_usd']-costs.subtotal(power))<costs.rounding_bound_usd


def test_demand_shaving_does_not_reclassify_fixed_history():
    r=request('commercial');f,a,p=frame(r);f['pv_available_kw']=0.
    # One measured half-hour peak with ample opportunity to recharge.
    f['native_load_kw']=8.;f.loc[20,'native_load_kw']=40.
    prior=deepcopy(a)
    out=optimize(f,a,p,r['battery']);baseline=calculate(pd.Series(f.native_load_kw.values,index=pd.DatetimeIndex(f.timestamp)),a,p)
    assert out['bill']['billed_mkd_kw']<baseline['billed_mkd_kw']
    assert a==prior and a.previous_12_month_peak_kw==40.


def test_hourly_arbitrage_negative_prices_and_optional_wear():
    r=request('residential','BESH');f,a,p=frame(r);f['native_load_kw']=1.;f['pv_available_kw']=0.
    hours=p.values.index.tz_convert('America/Chicago').hour
    p=replace(p,values=pd.Series(np.where((hours>=17)&(hours<22),400.,np.where(hours==3,-300.,20.)),index=p.values.index))
    out=optimize(f,a,p,r['battery']);d=out['dispatch']
    assert d.loc[d.timestamp.dt.hour<5,'battery_charge_kw'].sum()>0
    assert d.loc[d.timestamp.dt.hour.between(17,21),'battery_discharge_kw'].sum()>0
    assert out['bill']['subtotal_usd']<calculate(pd.Series(1.,index=pd.DatetimeIndex(f.timestamp)),a,p)['subtotal_usd']
    worn=optimize(f,a,p,r['battery'],wear=10.,include_wear=True)
    assert worn['degradation_cost_usd']<1e-5
    assert worn['recalculated_objective_usd']==pytest.approx(worn['bill']['subtotal_usd']+worn['degradation_cost_usd'])


def test_negative_prices_cannot_dissipate_energy_with_zero_native_load():
    r=request('residential','BESH');f,a,p=frame(r);f['native_load_kw']=0.;f['pv_available_kw']=10.
    p=replace(p,values=pd.Series(-1000.,index=p.values.index))
    out=optimize(f,a,p,r['battery']);d=out['dispatch']
    assert d.grid_import_kw.max()<1e-6
    assert d.battery_charge_kw.max()<1e-6 and d.battery_discharge_kw.max()<1e-6
    assert d.pv_curtailed_kw.eq(10.).all()


def test_zero_storage_and_zero_pv_are_real_absent_equipment():
    r=request();r['battery']=None;r['solar']['dc_capacity_kw']=0;r['pv_capacity_kw']=0
    f,a,p=frame(r);f['pv_available_kw']=0.
    out=optimize(f,a,p,None)
    assert out['dispatch'].battery_soc_kWh.eq(0).all()
    assert out['dispatch'].battery_charge_kw.eq(0).all()
    assert out['dispatch'].grid_import_kw.to_numpy()==pytest.approx(f.native_load_kw.to_numpy())


@pytest.mark.parametrize('failure',['solver_error','user_limit'])
def test_failed_secondary_solve_keeps_proven_solution_even_if_variable_values_are_overwritten(monkeypatch,failure):
    import cvxpy as cp
    original=cp.Problem.solve;calls=0;saved={}
    r=request();f,a,p=frame(r)
    def solve(problem,*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==1:
            answer=original(problem,*args,**kwargs)
            saved['cost']=problem.value
            return answer
        for variable in problem.variables():
            variable.value=np.zeros(variable.shape)
        if failure=='solver_error':raise cp.error.SolverError('Synthetic secondary failure')
        problem._status='user_limit'
    monkeypatch.setattr(cp.Problem,'solve',solve)
    out=optimize(f,a,p,r['battery']);d=out['dispatch']
    assert calls==2 and out['cost_optimum_proven']
    assert out['throughput_tie_break_status']==failure and out['warnings']
    assert out['unrounded_subtotal_usd']==pytest.approx(saved['cost'],abs=1e-5)
    assert abs(out['rounding_difference_usd'])<=out['rounding_bound_usd']
    assert d.battery_soc_kWh.iloc[0]==pytest.approx(r['battery']['energy_kWh'])
    assert out['terminal_energy_kwh']==pytest.approx(r['battery']['energy_kWh'])
    assert np.max(np.minimum(d.battery_charge_kw,d.battery_discharge_kw))<1e-6
    assert np.max(abs(d.grid_import_kw+d.pv_output_kw+d.battery_discharge_kw-d.native_load_kw-d.battery_charge_kw))<1e-5


def test_unproven_primary_solve_still_rejects(monkeypatch):
    import cvxpy as cp
    def incomplete(problem,*args,**kwargs):problem._status='user_limit'
    monkeypatch.setattr(cp.Problem,'solve',incomplete)
    r=request();f,a,p=frame(r)
    with pytest.raises(ValueError,match='did not prove optimality'):
        optimize(f,a,p,r['battery'])


@pytest.mark.parametrize('variant',['primary_transformer','hv_low_history','hv_high_history'])
def test_transformer_and_hv_history_rates_are_compiled_from_authoritative_lines(variant):
    r=request('commercial','BESH')
    if variant=='primary_transformer':r['account']['service_voltage']='primary'
    else:r['account'].update(delivery_class='high_voltage',service_voltage='high_voltage',
        previous_12_month_peak_kw=12000.,previous_calendar_year_peak_kw=12000.,
        previous_year_months_ge_100kw=12,competitively_declared=True,
        previous_12_month_mkd_kw=9000. if variant=='hv_low_history' else 11000.)
    g,_,a,p=prepare(r);costs=compile_costs(g.index,a,p);power=np.linspace(3.,42.,len(g.index))
    bill=calculate(pd.Series(power,index=g.index),a,p)
    assert 'transformer_demand' in [line['name'] for line in bill['lines']]
    assert abs(costs.subtotal(power)-bill['subtotal_usd'])<=costs.rounding_bound_usd


@pytest.mark.parametrize('bad',['partial','old_date','hourly_commercial','missing_capacity','unapproved','wrong_supplier','meter_purchases','missing_interval','boolean_load'])
def test_scope_rejects_incomplete_or_unconfirmed_cases(bad):
    r=request('commercial','BESH')
    if bad=='partial':r['end_date']='2026-09-29'
    if bad=='old_date':r.update(start_date='2024-09-01',end_date='2024-09-30');r['account']['billing_month']='2024-09-01'
    if bad=='hourly_commercial':r['timestep_minutes']=60
    if bad=='missing_capacity':r['account']['capacity_obligation_kw']=None
    if bad=='unapproved':r['operating_contract']['interconnection_confirmed']=False
    if bad=='wrong_supplier':r['regional_account']['retail_supplier']='alternative'
    if bad in ('meter_purchases','missing_interval','boolean_load'):
        g,load,_,_=prepare(r)
        if bad=='boolean_load':load=np.ones(len(load),dtype=bool)
        r['load'].update(mode='csv',power_kw=None,archetype=None,native_basis_confirmed=bad!='meter_purchases',
            csv=pd.DataFrame({'timestamp':g.index[1:] if bad=='missing_interval' else g.index,
                              'native_load_kw':load[1:] if bad=='missing_interval' else load}).to_csv(index=False))
    with pytest.raises(ValueError):prepare(r)
