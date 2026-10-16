"""Independent finite-bound checks, with no utility rates or external data.

The physical proof model below intentionally omits the optimizer's strengthening
cuts, then maximizes their violation. It therefore detects an over-tight cut
rather than merely replaying a schedule already constrained by that cut.
"""
import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

import src.dispatch.regional as regional
from src.billing.regional_math import BillingMath


def index(n=16):
    return pd.date_range("2025-07-01", periods=n, freq="15min", tz="America/New_York")


def solve(objective, constraints):
    problem = cp.Problem(objective, constraints)
    problem.solve(solver="SCIPY", scipy_options={"method": "highs", "mip_rel_gap": 0.})
    assert problem.status == "optimal"
    return problem.value


def test_constant_expressions_need_no_variable_identity():
    m = BillingMath(index(4), convex=True, power_bound=10)
    values = cp.Constant([0., 1., 2., 3.])
    assert m.sum(values).value == pytest.approx(6.)
    assert m.maximum(values, exact=True) == 3.
    assert m.demand(values, index(4), 30, exact=True) == 2.5


def test_per_entry_maximum_pruning_preserves_exact_negative_objective():
    m = BillingMath(index(4), convex=True, power_bound=10)
    values = m.register_power(cp.Variable(4), [1., 5., 0., 2.], [2., 8., 4., 3.])
    peak = m.maximum(values, exact=True)
    assert m.bounds(peak) == (5., 8.)
    actual = [1.5, 7., 3., 2.5]
    result = solve(cp.Minimize(-peak), m.constraints+[values == actual])
    assert result == pytest.approx(-max(actual))


def test_demand_preserves_averaged_per_entry_bounds_and_energy_bound():
    m = BillingMath(index(4), convex=True, power_bound=12)
    values = m.register_power(cp.Variable(4), [1., 7., 2., 10.], [2., 8., 4., 12.], energy_upper=6.)
    peak = m.demand(values, index(4), 30, exact=True)
    assert m.bounds(peak) == (6., 8.)  # Means, not extrema of the native quarters.
    assert m.bounds(m.sum(values)) == (20., 24.)
    actual = [1., 8., 3., 10.]
    result = solve(cp.Minimize(-peak), m.constraints+[values == actual])
    assert result == pytest.approx(-6.5)


@pytest.mark.parametrize("powers,efficiencies,terminal", [
    ((3., 3.), (.95, .95), 4.),
    ((1., 4.), (.8, .9), 3.),
    ((4., 1.), (.9, .8), 6.),
    ((2., 5.), (1., 1.), None),
    ((5., 2.), (.7, .85), None),
])
def test_optimizer_bound_cuts_admit_every_independently_feasible_schedule(monkeypatch, powers, efficiencies, terminal):
    """Compare the actual registered cut against an uncut physical MILP."""
    dt = .25
    n = 16
    load = np.array([1., 3., 2., 4.]*4)
    pv = np.array([0., 4., 6., 0.]*4)
    pc, pd_ = powers
    ec, ed = efficiencies
    battery = dict(capacity_kWh=10., SOC_min=.1, SOC_max=.9, energy_kWh=4.,
                   max_charge_kw=pc, max_discharge_kw=pd_, charge_efficiency=ec,
                   discharge_efficiency=ed)
    recorded = {}
    original = regional.BillingMath

    class RecordingMath(original):
        def register_power(self, x, lower, upper, *, energy_upper=None):
            recorded.update(lower=np.array(lower), upper=np.array(upper), energy=energy_upper)
            return super().register_power(x, lower, upper, energy_upper=energy_upper)

    class FixtureTariff:
        @staticmethod
        def validate_account(*args, **kwargs):
            return None

        @staticmethod
        def charge_lines(index, imports, exports, account, *, math, state=None):
            return {"lines": {"energy": math.sum(imports)*math.hours}}

    def fixture_bill(utility, index, imports, exports, account, **kwargs):
        return {"unrounded_total_usd": float(np.sum(imports)*dt), "next_state": {}}

    monkeypatch.setattr(regional, "BillingMath", RecordingMath)
    monkeypatch.setattr(regional, "adapter", lambda _: FixtureTariff)
    monkeypatch.setattr(regional, "calculate_cycle", fixture_bill)
    inputs = pd.DataFrame(dict(timestamp=index(n), native_load_kw=load, pv_available_kw=pv))
    regional.optimize_cycle(inputs, "fixture", {}, battery, terminal_energy=terminal,
                            export_enabled=True, grid_charging=True, time_limit=10)

    # Independent model: deliberately no registered import or total-energy cuts.
    imp, exp, output, charge, discharge = [cp.Variable(n, nonneg=True) for _ in range(5)]
    energy = cp.Variable(n+1)
    charging, importing = cp.Variable(n, boolean=True), cp.Variable(n, boolean=True)
    constraints = [output <= pv, exp <= output, imp <= (load.max()+pc)*importing,
        exp <= pv.max()*(1-importing), charge <= pc*charging,
        discharge <= pd_*(1-charging), discharge <= load,
        discharge <= pd_*importing, energy[0] == 4., energy >= 1., energy <= 9.,
        energy[1:] == energy[:-1]+dt*(ec*charge-discharge/ed),
        imp+output+discharge == load+charge+exp]
    if terminal is not None:
        constraints.append(energy[-1] == terminal)
    assert solve(cp.Maximize(dt*cp.sum(imp)-recorded["energy"]), constraints) <= 1e-6
    # Maximize each possible interval-cut violation in one exact MILP.
    # Separate solves avoid relaxing a maximum into an epigraph.
    for i in range(n):
        assert solve(cp.Maximize(imp[i]-recorded["upper"][i]), constraints) <= 1e-6
        assert solve(cp.Maximize(recorded["lower"][i]-imp[i]), constraints) <= 1e-6
