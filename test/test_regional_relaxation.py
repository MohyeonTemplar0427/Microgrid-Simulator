"""Only physical schedules attaining a proven relaxation bound are executable."""
import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

import src.dispatch.regional as regional


def setup(monkeypatch, *, prices=None, n=16, exact_tariff=False):
    idx = pd.date_range("2025-07-01", periods=n, freq="15min", tz="America/New_York")
    prices = np.asarray(prices if prices is not None else [.1]*(n//2)+[.5]*(n-n//2))
    data = pd.DataFrame(dict(timestamp=idx, native_load_kw=np.full(n, 4.), pv_available_kw=np.zeros(n)))
    battery = dict(capacity_kWh=8., SOC_min=.1, SOC_max=.9, energy_kWh=4.,
        max_charge_kw=2., max_discharge_kw=2., charge_efficiency=.9, discharge_efficiency=.8)

    class Tariff:
        @staticmethod
        def validate_account(*args, **kwargs):
            return None

        @staticmethod
        def charge_lines(index, imports, exports, account, *, math, state=None):
            lines = {"energy": math.dot(imports, prices)*math.hours}
            if exact_tariff:
                lines["exact_regime"] = .03*math.positive(math.sum(imports)*math.hours-10, exact=True)
            return {"lines": lines}

    def numeric(utility, index, imports, exports, account, **kwargs):
        energy = float(np.sum(imports)*.25)
        return {"unrounded_total_usd": float(np.dot(prices, imports)*.25)+(.03*max(energy-10, 0) if exact_tariff else 0),
                "next_state": {}}

    monkeypatch.setattr(regional, "adapter", lambda _: Tariff)
    monkeypatch.setattr(regional, "calculate_cycle", numeric)
    return data, battery


def physical(result, battery):
    d = result["dispatch"]
    np.testing.assert_allclose(d.grid_import_kw+d.pv_output_kw+d.battery_discharge_kw,
        d.native_load_kw+d.battery_charge_kw+d.grid_export_kw, atol=1e-5)
    assert np.minimum(d.battery_charge_kw, d.battery_discharge_kw).max() <= 1e-5
    assert np.minimum(d.grid_import_kw, d.grid_export_kw).max() <= 1e-5
    end = d.energy_kWh+.25*(d.battery_charge_kw*battery["charge_efficiency"]-d.battery_discharge_kw/battery["discharge_efficiency"])
    np.testing.assert_allclose(d.energy_kWh.iloc[1:], end.iloc[:-1], atol=1e-5)
    assert end.iloc[-1] == pytest.approx(battery["energy_kWh"], abs=1e-5)
    assert result["cost_optimum_proven"] is True
    assert result["primary_optimality_gap_usd"] <= result["primary_proof_tolerance_usd"]
    assert result["recalculated_objective_usd"] == pytest.approx(result["objective_usd"], abs=1e-4)


def run(data, battery, **kwargs):
    return regional.optimize_cycle(data, "fixture", {}, battery, terminal_energy=battery["energy_kWh"],
                                   grid_charging=True, time_limit=10, **kwargs)


def test_positive_prices_accept_physical_relaxation_and_prove_minimum_cycling(monkeypatch):
    data, battery = setup(monkeypatch)
    result = run(data, battery)
    physical(result, battery)
    assert result["cost_proof_method"] == "physical_relaxation_bound"
    assert result["cycling_proof_method"] == "physical_relaxation_bound"
    assert result["minimum_cycling_proven"] is True
    assert result["cycling_optimality_gap_kwh"] <= result["cycling_proof_tolerance_kwh"]
    assert .25*result["dispatch"][["battery_charge_kw", "battery_discharge_kw"]].to_numpy().sum() == pytest.approx(result["cycling_lower_bound_kwh"], abs=1e-5)
    assert result["strict_fallback_used"] is False
    assert result["dispatch"].battery_charge_kw.sum() > 0


def test_tariff_integer_selectors_are_preserved_in_relaxed_battery_solve(monkeypatch):
    data, battery = setup(monkeypatch, exact_tariff=True)
    original = cp.Problem.solve
    calls = []
    def observed(problem, *args, **kwargs):
        calls.append(problem.is_mixed_integer())
        return original(problem, *args, **kwargs)
    monkeypatch.setattr(cp.Problem, "solve", observed)
    result = run(data, battery)
    physical(result, battery)
    assert result["cost_proof_method"] == "physical_relaxation_bound"
    assert calls and all(calls)  # Battery relaxation never relaxed the tariff.


def test_negative_price_artificial_loss_cycling_requires_strict_fallback(monkeypatch):
    data, battery = setup(monkeypatch, n=8, prices=[-1.]*8)
    result = run(data, battery)
    physical(result, battery)
    assert result["strict_fallback_used"] is True
    assert result["cost_proof_method"] == "strict_milp"
    assert result["relaxation_status"] == "rejected_nonphysical_or_unreconciled"
    assert result["objective_usd"] > result["relaxed_lower_bound_usd"]+1e-4


def test_unproven_relaxation_falls_back_and_reproduces_proven_primary_bill(monkeypatch):
    data, battery = setup(monkeypatch)
    reference = run(data, battery)
    original = cp.Problem.solve
    calls = []
    def skip_first(problem, *args, **kwargs):
        calls.append(problem.is_mixed_integer())
        if len(calls) == 1:
            problem._status = "optimal_inaccurate"
            return None
        return original(problem, *args, **kwargs)
    monkeypatch.setattr(cp.Problem, "solve", skip_first)
    result = run(data, battery)
    physical(result, battery)
    assert result["strict_fallback_used"] and result["cost_proof_method"] == "strict_milp"
    assert result["relaxation_status"] == "unproven_optimal_inaccurate"
    assert result["objective_usd"] == pytest.approx(reference["objective_usd"], abs=1e-5)
    assert calls[0] is False and calls[1] is True


def test_failed_secondary_keeps_physical_primary_without_minimum_claim(monkeypatch):
    data, battery = setup(monkeypatch)
    original = cp.Problem.solve
    calls = 0
    def skip_secondary(problem, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            problem._status = "user_limit"
            return None
        return original(problem, *args, **kwargs)
    monkeypatch.setattr(cp.Problem, "solve", skip_secondary)
    result = run(data, battery)
    physical(result, battery)
    assert result["cost_proof_method"] == "physical_relaxation_bound"
    assert result["minimum_cycling_proven"] is False
    assert result["cycling_proof_method"] == "not_proven"
    assert result["refinement_status"] == "retained_primary" and result["warnings"]


def test_no_unproven_relaxation_or_strict_primary_is_accepted(monkeypatch):
    data, battery = setup(monkeypatch)
    def unproven(problem, *args, **kwargs):
        problem._status = "optimal_inaccurate"
        return None
    monkeypatch.setattr(cp.Problem, "solve", unproven)
    with pytest.raises(ValueError, match="not proven"):
        run(data, battery)


def test_grid_import_export_direction_is_not_relaxed(monkeypatch):
    data, battery = setup(monkeypatch)
    original = cp.Problem.solve
    mixed = []
    def observe(problem, *args, **kwargs):
        mixed.append(problem.is_mixed_integer())
        return original(problem, *args, **kwargs)
    monkeypatch.setattr(cp.Problem, "solve", observe)
    result = run(data, battery, export_enabled=True)
    physical(result, battery)
    assert mixed and all(mixed)


@pytest.mark.parametrize("terminal", [float("nan"), float("inf"), -.1, 9., True])
def test_invalid_terminal_cannot_enter_lower_bound_calculation(monkeypatch, terminal):
    data, battery = setup(monkeypatch)
    with pytest.raises(ValueError, match="Terminal battery energy"):
        regional.optimize_cycle(data, "fixture", {}, battery, terminal_energy=terminal)
