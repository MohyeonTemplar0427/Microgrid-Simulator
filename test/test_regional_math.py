"""Exact operation tests: no utility rates or external requests."""
import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing.regional_math import BillingMath


def grid(start="2025-01-01", periods=4):
    return pd.date_range(start, periods=periods, freq="15min", tz="America/New_York")


def solve(expression, math, constraints=()):
    problem = cp.Problem(cp.Minimize(expression), math.constraints+list(constraints))
    problem.solve(solver="SCIPY", scipy_options={"method":"highs"})
    assert problem.status == "optimal"
    return problem.value


def test_exact_peak_cannot_inflate_when_its_coefficient_is_negative():
    m = BillingMath(grid(), convex=True, power_bound=10)
    power = m.register(cp.Variable(4), 0, 10)
    peak = m.demand(power, grid(), 30, exact=True)
    assert solve(-peak, m, [power == [2, 4, 6, 2]]) == pytest.approx(-4)
    assert BillingMath(grid()).demand(np.array([2, 4, 6, 2]), grid(), 30) == 4


@pytest.mark.parametrize("volume,expected", [(0,0),(5,5),(10,10),(15,12.5),(25,16.25)])
def test_declining_tiers_are_filled_in_order(volume, expected):
    m = BillingMath(grid(), convex=True, power_bound=40)
    x = m.register(cp.Variable(), 0, 40)
    expression = m.tiered(x, [10,20], [1,.5,.25])
    assert solve(expression,m,[x == volume]) == pytest.approx(expected)
    assert BillingMath(grid()).tiered(volume,[10,20],[1,.5,.25]) == expected


def test_symbolic_tier_width_and_minimum_bill():
    m = BillingMath(grid(),convex=True,power_bound=30)
    volume = m.register(cp.Variable(),0,30)
    width = m.register(cp.Variable(),5,15)
    amount = m.tiered(volume,[width],[2,1])
    floor = m.maximum(amount,12)
    assert solve(floor,m,[volume==10,width==7]) == pytest.approx(17)


@pytest.mark.parametrize("volume,expected",[(5,5),(15,12.5)])
def test_regime_selection_with_continuous_boundary(volume,expected):
    m = BillingMath(grid(),convex=True,power_bound=30)
    x = m.register(cp.Variable(),0,30)
    amount = m.choose_leq(x,10,x,5+.5*x)
    assert solve(amount,m,[x==volume]) == pytest.approx(expected)


def test_demand_dst_and_alignment_are_physical_instants():
    index = pd.date_range("2025-11-02", "2025-11-03",freq="15min",tz="America/New_York",inclusive="left")
    assert len(index)==100
    m=BillingMath(index)
    assert m.demand(np.ones(100),index,30)==1
    with pytest.raises(ValueError,match="aligned"):
        m.demand(np.ones(99),index[:-1],30)
    with pytest.raises(ValueError,match="align"):
        BillingMath(grid("2025-01-01 00:15")).demand(np.ones(4),grid("2025-01-01 00:15"),30)


def test_missing_bound_rejects_instead_of_inventing_big_m():
    m=BillingMath(grid(),convex=True,power_bound=10)
    with pytest.raises(ValueError,match="bound"):
        m.positive(cp.Variable(),exact=True)


def test_nested_positive_peak_inside_exact_minimum_is_not_relaxed():
    m=BillingMath(grid(),convex=True,power_bound=10)
    x=m.register(cp.Variable(4),0,10)
    demand=m.demand(x,grid(),30)
    floor=m.maximum(demand,3)
    amount=m.minimum(2*floor,7)
    assert solve(-amount,m,[x==[2,4,6,2]])==pytest.approx(-7)
