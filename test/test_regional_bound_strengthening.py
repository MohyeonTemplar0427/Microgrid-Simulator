"""Independent linear bounds and exact conditional-selection regressions."""
import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing.regional_math import BillingMath


def grid():
    return pd.date_range('2026-06-01',periods=4,freq='15min',tz='America/New_York')


def optimum(expression,constraints,maximize=False):
    p=cp.Problem(cp.Maximize(expression) if maximize else cp.Minimize(expression),constraints)
    p.solve(solver='SCIPY',scipy_options={'method':'highs','mip_rel_gap':0.})
    assert p.status=='optimal'
    return p.value


@pytest.mark.parametrize('coefficient',[.25,-.4,0.])
def test_constant_rate_preserves_proven_aggregate_energy_cap(coefficient):
    m=BillingMath(grid(),convex=True,power_bound=10.)
    low=np.array([1.,2.,0.,1.]);high=np.array([8.,5.,4.,9.])
    power=m.register_power(cp.Variable(4),low,high,energy_upper=3.)
    amount=m.dot(power,np.full(4,coefficient))
    expected=sorted((4.*coefficient,12.*coefficient))
    assert m.bounds(amount)==pytest.approx(expected)
    # The independent physical LP omits the calculator's registered bounds.
    constraints=[power>=low,power<=high,.25*cp.sum(power)<=3.]
    assert optimum(amount,constraints)>=expected[0]-1e-8
    assert optimum(amount,constraints,True)<=expected[1]+1e-8


def test_signed_varying_rates_keep_interval_specific_bounds():
    m=BillingMath(grid(),convex=True,power_bound=10.)
    low=np.array([1.,2.,0.,1.]);high=np.array([8.,5.,4.,9.])
    power=m.register_power(cp.Variable(4),low,high)
    amount=m.dot(power,np.array([2.,-.5,0.,3.]))
    lo,hi=m.bounds(amount)
    assert (lo,hi)==pytest.approx((2.5,42.))
    constraints=[power>=low,power<=high]
    assert optimum(amount,constraints)==pytest.approx(lo)
    assert optimum(amount,constraints,True)==pytest.approx(hi)


def test_unregistered_constant_dot_keeps_safe_original_behavior():
    m=BillingMath(grid(),convex=True,power_bound=10.)
    amount=m.dot(cp.Constant([1.,2.,3.,4.]),np.array([1.,-1.,0.,.5]))
    assert amount.value==pytest.approx(1.)


@pytest.mark.parametrize('volume,expected',[(5.,15.),(10.,30.),(15.,37.5)])
def test_same_predicate_reuses_one_selector_at_and_around_continuous_boundary(volume,expected):
    m=BillingMath(grid(),convex=True,power_bound=30.)
    x=m.register(cp.Variable(),0.,30.);peak=m.register(cp.Variable(),1.,10.)
    first=m.choose_leq(x,2*peak,x,.5*x+peak)
    second=m.choose_leq(x,1.*(2.*peak),2*x,x+2*peak)
    problem=cp.Problem(cp.Minimize(first+second),m.constraints+[x==volume,peak==5.])
    assert sum(v.size for v in problem.variables() if v.attributes['boolean'])==1
    problem.solve(solver='SCIPY',scipy_options={'method':'highs'})
    assert problem.status=='optimal'
    assert problem.value==pytest.approx(expected)


def test_different_slices_or_thresholds_never_share_a_selector():
    m=BillingMath(grid(),convex=True,power_bound=30.)
    values=m.register(cp.Variable(2),0.,30.)
    first,second=values[0],values[1]
    a=m.choose_leq(first,10.,first,5.+.5*first)
    b=m.choose_leq(second,10.,second,5.+.5*second)
    c=m.choose_leq(second,20.,second,10.+.5*second)
    p=cp.Problem(cp.Minimize(a+b+c),m.constraints+[values==[5.,15.]])
    assert sum(v.size for v in p.variables() if v.attributes['boolean'])==3
    p.solve(solver='SCIPY',scipy_options={'method':'highs'})
    assert p.status=='optimal'
    assert p.value==pytest.approx(32.5)


def test_distinct_parameters_with_equal_values_are_not_constant_identities():
    m=BillingMath(grid(),convex=True,power_bound=30.)
    x=m.register(cp.Variable(),0.,30.)
    first,second=cp.Parameter(value=10.),cp.Parameter(value=10.)
    a=m.choose_leq(x,first,x,5.+.5*x)
    b=m.choose_leq(x,second,x,5.+.5*x)
    p=cp.Problem(cp.Minimize(a+b),m.constraints+[x==5.])
    assert sum(v.size for v in p.variables() if v.attributes['boolean'])==2
    p.solve(solver='SCIPY',scipy_options={'method':'highs'})
    assert p.status=='optimal'
    assert p.value==pytest.approx(10.)


@pytest.mark.parametrize('volume,branches,expected',[
    (5.,'negative_true',-10.),(15.,'negative_true',20.),
    (5.,'negative_false',25.),(15.,'negative_false',-30.),
])
@pytest.mark.parametrize('maximize',[False,True])
def test_asymmetric_bounds_preserve_exact_selected_value_with_disjoint_cost_ranges(volume,branches,expected,maximize):
    m=BillingMath(grid(),convex=True,power_bound=30.)
    x=m.register(cp.Variable(),0.,30.)
    true,false=(-2*x,5+x) if branches=='negative_true' else (x+20,-2*x)
    amount=m.choose_leq(x,10.,true,false)
    assert optimum(amount,m.constraints+[x==volume],maximize)==pytest.approx(expected)
