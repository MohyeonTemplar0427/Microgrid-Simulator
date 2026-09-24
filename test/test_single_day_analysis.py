"""Focused tests for single-day dispatch optimization."""

import pandas as pd
import pytest
import cvxpy as cp

from src.billing import (
    PGE_B19_SECONDARY_MANDATORY_BUNDLED,
    PGE_B20_SECONDARY_BUNDLED,
    PGE_B19_SECONDARY_OPTION_S_BUNDLED,
    PGE_B20_SECONDARY_OPTION_S_BUNDLED,
    calculate_meter_billing,
)
from src.dispatch.dispatch_scenarios import create_optimized_dispatch_scenarios
from src.dispatch.single_day_analysis import (
    _build_monthly_demand_charge_cost,
    run_cost_optimization,
)


BATTERY_PARAMETERS = {
    "capacity_kWh": 20.0,
    "initial_soc_kWh": 10.0,
    "min_soc_kWh": 2.0,
    "max_soc_kWh": 18.0,
    "max_charge_kw": 5.0,
    "max_discharge_kw": 5.0,
    "charge_efficiency": 0.95,
    "discharge_efficiency": 0.95,
}


def create_two_interval_price_spread() -> pd.DataFrame:
    """Create a small price-arbitrage case for optimizer tests."""

    return pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2026-08-25",
                periods=2,
                freq="15min",
                tz="America/Los_Angeles",
            ),
            "load_kw": [5.0, 5.0],
            "pv_kw": [0.0, 0.0],
            "price_per_kWh": [0.10, 0.20],
        }
    )


def test_cost_optimization_degradation_reduces_throughput():
    data = create_two_interval_price_spread()

    energy_cost_only = run_cost_optimization(
        data.copy(),
        BATTERY_PARAMETERS,
    )

    degradation_aware = run_cost_optimization(
        data.copy(),
        BATTERY_PARAMETERS,
        degradation_cost_per_kWh=0.10,
        include_degradation_in_optimization=True,
    )

    bill_only_with_reported_wear = run_cost_optimization(
        data.copy(),
        BATTERY_PARAMETERS,
        degradation_cost_per_kWh=0.10,
    )
    assert bill_only_with_reported_wear["grid_import_kw"].to_numpy() == pytest.approx(
        energy_cost_only["grid_import_kw"].to_numpy(), abs=1e-4
    )

    energy_cost_only_throughput_kWh = (
        energy_cost_only["battery_charge_kw"].sum()
        + energy_cost_only["battery_discharge_kw"].sum()
    ) * 0.25

    degradation_aware_throughput_kWh = (
        degradation_aware["battery_charge_kw"].sum()
        + degradation_aware["battery_discharge_kw"].sum()
    ) * 0.25

    assert degradation_aware_throughput_kWh < (
        energy_cost_only_throughput_kWh
    )


def test_cost_optimization_rejects_negative_degradation_cost():
    with pytest.raises(
        ValueError,
        match="Degradation cost must not be negative",
    ):
        run_cost_optimization(
            create_two_interval_price_spread(),
            BATTERY_PARAMETERS,
            degradation_cost_per_kWh=-0.01,
        )


def test_cost_optimization_includes_monthly_demand_charge():
    data = create_two_interval_price_spread()

    energy_only = run_cost_optimization(
        data.copy(),
        BATTERY_PARAMETERS,
    )
    demand_aware = run_cost_optimization(
        data.copy(),
        BATTERY_PARAMETERS,
        demand_charge_rate_per_kw=20.50,
    )

    assert energy_only["grid_import_kw"].max() > 5.0
    assert demand_aware["grid_import_kw"].max() == pytest.approx(
        5.0,
        abs=1e-4,
    )


@pytest.mark.parametrize("tariff", [
    PGE_B19_SECONDARY_MANDATORY_BUNDLED,
    PGE_B20_SECONDARY_BUNDLED,
])
def test_tariff_demand_objective_matches_bill_across_season_and_month(tariff):
    timestamps = pd.DatetimeIndex([
        pd.Timestamp("2026-09-30 15:00", tz="America/Los_Angeles"),
        pd.Timestamp("2026-09-30 17:00", tz="America/Los_Angeles"),
        pd.Timestamp("2026-10-01 03:00", tz="America/Los_Angeles"),
        pd.Timestamp("2026-10-01 17:00", tz="America/Los_Angeles"),
    ])
    imports = [120., 200., 220., 180.]
    data = pd.DataFrame({"timestamp": timestamps, "grid_import_kw": imports})
    objective = _build_monthly_demand_charge_cost(
        cp.Constant(imports), data, demand_charge_rate_per_kw=0.,
        previous_peak_kw=250., demand_tariff=tariff,
    )
    billed = calculate_meter_billing(
        data, tariff, meter_id="pcc", timestep_hours=.25,
        previous_peak_kw=250., expect_full_periods=False,
    )
    assert objective.value == pytest.approx(sum(month.demand_charge for month in billed))
    assert billed[0].demand_charge_by_component["part_peak_period_demand_summer"] > 0
    assert billed[1].demand_charge_by_component["peak_period_demand_winter"] > 0


@pytest.mark.parametrize("tariff", [
    PGE_B19_SECONDARY_OPTION_S_BUNDLED,
    PGE_B20_SECONDARY_OPTION_S_BUNDLED,
])
def test_option_s_objective_matches_bills_across_days_and_season_boundary(tariff):
    timestamps = pd.DatetimeIndex([
        pd.Timestamp(f"2026-{month_day} {hour}:00", tz="America/Los_Angeles")
        for month_day, hour in (
            ("09-29", 10), ("09-29", 14), ("09-29", 17),
            ("09-30", 17), ("09-30", 21),
            ("10-01", 10), ("10-01", 17), ("10-02", 17),
        )
    ])
    imports = [300., 100., 200., 120., 180., 250., 170., 90.]
    data = pd.DataFrame({"timestamp": timestamps, "grid_import_kw": imports})
    objective = _build_monthly_demand_charge_cost(
        cp.Constant(imports), data, demand_charge_rate_per_kw=0.,
        previous_peak_kw=350., demand_tariff=tariff,
    )
    billed = calculate_meter_billing(
        data, tariff, meter_id="pcc", timestep_hours=.25,
        previous_peak_kw=350., expect_full_periods=False,
    )
    assert objective.value == pytest.approx(sum(month.demand_charge for month in billed))
    assert billed[0].demand_charge_by_component["maximum_demand_all_hours"] == pytest.approx(
        350 * next(c.rate_per_kW for c in tariff.demand_charges if c.name == "maximum_demand_all_hours")
    )
    assert billed[0].demand_charge_by_component["maximum_demand_excluding_09_to_14"] == pytest.approx(
        200 * next(c.rate_per_kW for c in tariff.demand_charges if c.name == "maximum_demand_excluding_09_to_14")
    )
    assert billed[1].demand_charge_by_component["peak_period_demand_winter_daily"] > 0


def test_option_s_cost_dispatch_reduces_billed_daily_peaks():
    tariff = PGE_B19_SECONDARY_OPTION_S_BUNDLED
    timestamps = pd.DatetimeIndex([
        pd.Timestamp(f"2026-07-{day:02d} {hour:02d}:00", tz="America/Los_Angeles")
        for day in (10, 11) for hour in (12, 17, 23)
    ])
    loads = [100., 100., 0.] * 2
    data = pd.DataFrame({
        "timestamp": timestamps, "load_kw": loads, "pv_kw": [0.] * 6,
        "net_load_kw": loads,
        "price_per_kWh": tariff.energy_rates(timestamps).to_numpy(),
        "gCO2/kWh": [0.] * 6,
    })
    battery = dict(
        initial_soc_kWh=1.25, min_soc_kWh=0., max_soc_kWh=1.25,
        max_charge_kw=5., max_discharge_kw=5.,
        charge_efficiency=1., discharge_efficiency=1.,
    )
    optimized = run_cost_optimization(
        data.copy(), battery, demand_tariff=tariff,
    )
    baseline = pd.DataFrame({"timestamp": timestamps, "grid_import_kw": loads})
    (baseline_bill,) = calculate_meter_billing(
        baseline, tariff, meter_id="pcc", timestep_hours=.25,
        expect_full_periods=False,
    )
    (optimized_bill,) = calculate_meter_billing(
        optimized, tariff, meter_id="pcc", timestep_hours=.25,
        expect_full_periods=False,
    )
    assert optimized.loc[[1, 4], "battery_discharge_kw"].min() > 4.9
    assert optimized_bill.demand_charge < baseline_bill.demand_charge
    assert optimized_bill.total_utility_charge < baseline_bill.total_utility_charge


def test_b19_peak_demand_changes_battery_dispatch_and_reduces_actual_bill():
    tariff = PGE_B19_SECONDARY_MANDATORY_BUNDLED
    timestamps = pd.DatetimeIndex([
        pd.Timestamp(f"2026-07-15 {hour}:00", tz="America/Los_Angeles")
        for hour in (12, 17, 23)
    ])
    data = pd.DataFrame({
        "timestamp": timestamps,
        "load_kw": [100., 90., 1.],
        "pv_kw": [0., 0., 0.],
        "net_load_kw": [100., 90., 1.],
        "price_per_kWh": [.01, .01, .01],
        "gCO2/kWh": [0., 0., 0.],
    })
    battery = dict(initial_soc_kWh=1.25, min_soc_kWh=0., max_soc_kWh=1.25,
                   max_charge_kw=5., max_discharge_kw=5.,
                   charge_efficiency=.95, discharge_efficiency=.95)
    flat = run_cost_optimization(
        data.copy(), battery, degradation_cost_per_kWh=.01,
        demand_charge_rate_per_kw=tariff.demand_charges[0].rate_per_kW,
    )
    scenarios = create_optimized_dispatch_scenarios(
        data, battery, carbon_weight=0., degradation_cost_per_kWh=.01,
        demand_tariff=tariff, scenario_names=("cost_optimal", "combined_optimal"),
    )
    scoped = scenarios["cost_optimal"]
    combined = scenarios["combined_optimal"]
    flat_bill, = calculate_meter_billing(flat, tariff, meter_id="pcc", timestep_hours=.25)
    scoped_bill, = calculate_meter_billing(scoped, tariff, meter_id="pcc", timestep_hours=.25)
    assert flat.loc[0, "battery_discharge_kw"] > 4.7
    assert scoped.loc[1, "battery_discharge_kw"] > 4.5
    assert scoped_bill.demand_charge < flat_bill.demand_charge - 100
    assert combined.loc[1, "battery_discharge_kw"] == pytest.approx(
        scoped.loc[1, "battery_discharge_kw"], abs=1e-3,
    )
