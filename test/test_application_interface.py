"""Tests for pure logic used by the guided application interface."""

from decimal import Decimal

import pytest

from src.simulation.application_interface import (
    MicrogridApplication,
    build_review_rows,
    build_results_export_table,
    calculate_progress_percentage,
    calculate_inclusive_day_count,
    format_runtime,
    parse_carbon_weights,
    selected_strategies,
)


class FakeBooleanVariable:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value

    def set(self, value: bool) -> None:
        self.value = value


class FakeValueVariable:
    def __init__(self, value) -> None:
        self.value = value

    def get(self):
        return self.value

    def set(self, value) -> None:
        self.value = value


class FakeConfigurableWidget:
    def __init__(self) -> None:
        self.configuration = {}

    def configure(self, **kwargs) -> None:
        self.configuration.update(kwargs)


class FakeProcess:
    def __init__(self, alive=True) -> None:
        self.alive = alive
        self.terminated = False
        self.joined = False
        self.closed = False

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.terminated = True
        self.alive = False

    def join(self, timeout=None):
        self.joined = True

    def close(self):
        self.closed = True


class FakeQueue:
    def __init__(self) -> None:
        self.closed = False
        self.joined = False

    def close(self):
        self.closed = True

    def join_thread(self):
        self.joined = True


class FakeWindow:
    def __init__(self) -> None:
        self.destroyed = False

    def destroy(self):
        self.destroyed = True


def test_selected_strategies_keeps_display_order():
    values = {
        "no_battery": FakeBooleanVariable(True),
        "rule_based": FakeBooleanVariable(False),
        "cost_optimal": FakeBooleanVariable(True),
        "carbon_optimal": FakeBooleanVariable(False),
        "combined_optimal": FakeBooleanVariable(True),
    }

    assert selected_strategies(values) == (
        "no_battery",
        "cost_optimal",
        "combined_optimal",
    )


def test_battery_controls_use_selected_battery_strategies():
    application = MicrogridApplication.__new__(MicrogridApplication)
    application.strategy_values = {
        "no_battery": FakeBooleanVariable(True),
        "cost_optimal": FakeBooleanVariable(True),
    }
    application.battery_entries = [FakeConfigurableWidget()]
    application.battery_status = FakeConfigurableWidget()

    application._update_battery_controls()

    assert application.battery_entries[0].configuration["state"] == "normal"
    assert application.battery_status.configuration["text"] == (
        "Battery parameters are active."
    )


def test_profile_controls_enable_synthetic_live_inputs():
    application = MicrogridApplication.__new__(MicrogridApplication)
    application.values = {
        "source_mode": FakeValueVariable("live_api"),
        "load_profile_mode": FakeValueVariable("synthetic"),
    }
    application.load_profile_combobox = FakeConfigurableWidget()
    application.load_archetype_combobox = FakeConfigurableWidget()
    application.load_variability_entry = FakeConfigurableWidget()
    application.load_power_label = FakeConfigurableWidget()
    application.load_power_entry = FakeConfigurableWidget()
    application.profile_explanation = FakeConfigurableWidget()

    application._update_profile_controls()

    assert application.load_profile_combobox.configuration["state"] == "readonly"
    assert application.load_archetype_combobox.configuration["state"] == "readonly"
    assert application.load_variability_entry.configuration["state"] == "normal"
    assert application.load_power_label.configuration["text"] == (
        "Synthetic profile peak load (kW)"
    )
    assert "generates one load value per interval" in (
        application.profile_explanation.configuration["text"]
    )


def test_ercot_region_removes_pge_tariff_and_tou_price_option():
    application = MicrogridApplication.__new__(MicrogridApplication)
    application.values = {
        "region_id": FakeValueVariable("ercot_houston_hub"),
        "price_mode": FakeValueVariable("time_of_use"),
        "tariff_id": FakeValueVariable(
            "pge_b10_secondary_bundled_2026_03_01"
        ),
    }
    application.price_mode_combobox = FakeConfigurableWidget()
    application.tariff_combobox = FakeConfigurableWidget()
    application._update_price_controls = lambda: None

    application._update_region_pricing_options()

    assert application.values["price_mode"].get() == "wholesale_market"
    assert application.values["tariff_id"].get() == ""
    assert application.tariff_combobox.configuration["values"] == ()
    assert "Time-of-Use(TOU) tariff" not in (
        application.price_mode_combobox.configuration["values"]
    )


def test_gui_preferences_round_trip_latest_valid_selections(tmp_path):
    preferences_path = tmp_path / "gui_preferences.json"
    writer = MicrogridApplication.__new__(MicrogridApplication)
    writer.preferences_path = preferences_path
    writer.values = {
        "region_id": FakeValueVariable("ercot_houston_hub"),
        "price_mode": FakeValueVariable("wholesale_market"),
        "start_date": FakeValueVariable("2026-09-01"),
        "pv_capacity": FakeValueVariable("0"),
    }
    writer.strategy_values = {
        "no_battery": FakeBooleanVariable(True),
        "cost_optimal": FakeBooleanVariable(True),
    }

    assert writer._save_preferences()

    reader = MicrogridApplication.__new__(MicrogridApplication)
    reader.preferences_path = preferences_path
    reader.values = {
        "region_id": FakeValueVariable("caiso_np15"),
        "price_mode": FakeValueVariable("time_of_use"),
        "start_date": FakeValueVariable("2026-08-25"),
        "pv_capacity": FakeValueVariable("150"),
    }
    reader.strategy_values = {
        "no_battery": FakeBooleanVariable(False),
        "cost_optimal": FakeBooleanVariable(False),
    }

    reader._load_preferences()

    assert reader.values["region_id"].get() == "ercot_houston_hub"
    assert reader.values["price_mode"].get() == "wholesale_market"
    assert reader.values["start_date"].get() == "2026-09-01"
    assert reader.values["pv_capacity"].get() == "0"
    assert reader.strategy_values["no_battery"].get() is True
    assert reader.strategy_values["cost_optimal"].get() is True


def test_build_review_rows_uses_readable_sections_and_units():
    rows = build_review_rows(
        source_mode="live_api",
        region_id="caiso_np15",
        start_date="2026-08-25",
        end_date_inclusive="2026-08-26",
        timestep_minutes="15",
        price_mode="wholesale_market",
        strategies=("no_battery", "cost_optimal"),
        carbon_weights=("0.20",),
        degradation_cost="0.03",
        battery_active=True,
        battery_capacity="20",
        battery_initial_energy="10",
        battery_max_charge="5",
        battery_max_discharge="5",
        pv_capacity="30",
        load_power="25",
        load_profile_mode="synthetic",
        load_archetype="office",
        load_variability="0.05",
        tariff_id="pge_b10_secondary_bundled_2026_03_01",
        meter_topology_mode="single_pcc",
        submeter_count="30",
        previous_peak_kw="",
    )

    assert rows[0] == ("Analysis", "Data source", "Live API data")
    assert (
        "Analysis",
        "Region",
        "Northern California — CAISO NP15",
    ) in rows
    assert (
        "Strategies",
        "Selected scenarios",
        "No-battery baseline, Cost optimization",
    ) in rows
    assert ("Analysis", "End date (inclusive)", "2026-08-26") in rows
    assert ("Analysis", "Time interval", "15 minutes") in rows
    assert ("Microgrid", "Battery capacity", "20 kWh") in rows
    assert (
        "Profiles",
        "Load details",
        "Office, peak 25 kW, variability 0.05",
    ) in rows


def test_calculate_inclusive_day_count_includes_end_date():
    assert calculate_inclusive_day_count("2026-08-25", "2026-08-31") == 7


def test_calculate_inclusive_day_count_rejects_reversed_range():
    with pytest.raises(ValueError, match="must not precede"):
        calculate_inclusive_day_count("2026-08-31", "2026-08-25")


@pytest.mark.parametrize(
    ("elapsed_seconds", "expected"),
    [
        (12.34, "12.3 seconds"),
        (75.25, "1 min 15.2 sec"),
        (3675.25, "1 hr 1 min 15.2 sec"),
    ],
)
def test_format_runtime_uses_readable_units(elapsed_seconds, expected):
    assert format_runtime(elapsed_seconds) == expected


def test_progress_percentage_advances_left_to_right():
    progress = [
        calculate_progress_percentage(step, 4)
        for step in range(5)
    ]

    assert progress == [5.0, 27.5, 50.0, 72.5, 95.0]
    assert progress == sorted(progress)


def test_close_application_releases_process_and_queue():
    application = MicrogridApplication.__new__(MicrogridApplication)
    application.is_closing = False
    application.analysis_process = FakeProcess(alive=True)
    application.analysis_messages = FakeQueue()
    application.window = FakeWindow()

    process = application.analysis_process
    messages = application.analysis_messages
    window = application.window

    application._close_application()

    assert process.terminated
    assert process.joined
    assert process.closed
    assert messages.closed
    assert messages.joined
    assert window.destroyed


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("single", [Decimal("0.20")]),
        ("list", [Decimal("0.00"), Decimal("0.10"), Decimal("0.20")]),
        (
            "range",
            [Decimal("0.00"), Decimal("0.10"), Decimal("0.20")],
        ),
    ],
)
def test_parse_carbon_weights(mode, expected):
    assert parse_carbon_weights(
        mode,
        single="0.20",
        explicit_list="0.00, 0.10, 0.20",
        range_start="0.00",
        range_end="0.20",
        range_interval="0.10",
    ) == expected


@pytest.mark.parametrize(
    ("mode", "overrides"),
    [
        ("single", {"single": "-0.1"}),
        ("list", {"explicit_list": "0.1, 0.1"}),
        ("range", {"range_interval": "0"}),
        ("range", {"range_end": "0.25"}),
    ],
)
def test_parse_carbon_weights_rejects_invalid_values(mode, overrides):
    arguments = {
        "single": "0.20",
        "explicit_list": "0.00, 0.10, 0.20",
        "range_start": "0.00",
        "range_end": "0.20",
        "range_interval": "0.10",
    }
    arguments.update(overrides)

    with pytest.raises(ValueError):
        parse_carbon_weights(mode, **arguments)


def test_results_export_contains_results_parameters_and_warnings():
    import pandas as pd

    comparison = pd.DataFrame(
        {
            "scenario": ["cost_optimal"],
            "total_explicit_cost": [14233.230196],
            "energy_cost": [9392.384272],
            "demand_charge": [4761.264184],
            "customer_charge": [79.58174],
            "export_credit": [0.0],
            "degradation_cost": [0.0],
            "internal_debug_value": [123],
        }
    )

    exported = build_results_export_table(
        comparison,
        {
            "input_start_date": "2026-08-25",
            "input_load_power_or_peak_kw": 250.0,
        },
        warnings=("Partial billing period",),
    )

    assert exported.loc[0, "total_explicit_cost"] == pytest.approx(
        14233.230196
    )
    assert exported.loc[0, "input_start_date"] == "2026-08-25"
    assert exported.loc[0, "input_load_power_or_peak_kw"] == 250.0
    assert exported.loc[0, "analysis_warnings"] == "Partial billing period"
    assert "internal_debug_value" not in exported.columns


def test_b1_results_export_omits_non_applicable_demand_columns():
    import pandas as pd

    comparison = pd.DataFrame(
        {
            "scenario": ["no_battery"],
            "total_explicit_cost": [100.0],
            "energy_cost": [98.0],
            "demand_charge": [0.0],
            "billed_peak_kw": [60.0],
            "peak_grid_import_kw": [60.0],
            "customer_charge": [2.0],
            "tariff_has_demand_charge": [False],
        }
    )

    exported = build_results_export_table(comparison, {})

    assert "demand_charge" not in exported.columns
    assert "billed_peak_kw" not in exported.columns
    assert "peak_grid_import_kw" in exported.columns


def test_comparison_chart_preserves_sweep_rows_negative_and_missing_values(tmp_path):
    import pandas as pd
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from src.simulation.results_visualization import draw_comparison

    comparison = pd.DataFrame({
        "scenario": ["no_battery", "combined_optimal_0.10", "combined_optimal_0.20"],
        "total_explicit_cost": [100.0, -20.0, float("nan")],
    })
    original = comparison.copy(deep=True)
    figure = Figure(figsize=(9, 4), layout="constrained")
    canvas = FigureCanvasAgg(figure)
    draw_comparison(figure, comparison, "Total operating cost ($)")
    canvas.draw()
    axis = figure.axes[0]
    assert [bar.get_width() for bar in axis.patches] == [100.0, -20.0]
    assert [label.get_text() for label in axis.get_yticklabels()] == comparison.scenario.tolist()
    assert "Unavailable" in [text.get_text() for text in axis.texts]
    pd.testing.assert_frame_equal(comparison, original)
    draw_comparison(figure, comparison.iloc[:1], "Total operating cost ($)")
    canvas.draw()
    assert len(figure.axes) == 1
    assert len(figure.axes[0].patches) == 1


def test_comparison_metrics_exclude_absent_and_nonfinite_data():
    import pandas as pd
    from src.simulation.results_visualization import available_comparison_metrics

    assert available_comparison_metrics(pd.DataFrame()) == ()
    assert available_comparison_metrics(pd.DataFrame({
        "total_explicit_cost": [0.0],
        "emissions_kgCO2": [float("nan")],
        "peak_grid_import_kw": [float("inf")],
    })) == ("Total operating cost ($)",)
