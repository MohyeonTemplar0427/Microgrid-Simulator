"""Tests for pure logic used by the guided application interface."""

from decimal import Decimal

import pytest

import json

from src.simulation.application_interface import (
    MicrogridApplication,
    STRATEGY_LABELS,
    build_review_rows,
    build_results_export_table,
    calculate_progress_percentage,
    filter_cec_equipment_names,
    format_cec_equipment_name,
    calculate_inclusive_day_count,
    describe_equipment_ratings,
    describe_pv_selection,
    format_runtime,
    migrate_legacy_pv_profile_mode,
    parse_carbon_weights,
    resolve_pv_profile_mode,
    selected_strategies,
)
from src.simulation.geocoding import GeocodedLocation, GeocodingError
from src.simulation.interface_analysis import build_equipment_pv_configuration


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
        self.visible = True

    def configure(self, **kwargs) -> None:
        self.configuration.update(kwargs)

    def grid(self) -> None:
        self.visible = True

    def grid_remove(self) -> None:
        self.visible = False


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
        "pv_profile_method": FakeValueVariable("weather"),
        "weather_source": FakeValueVariable("csv"),
        "pv_system_model": FakeValueVariable("generic"),
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



def test_pge_tariff_reenables_after_region_round_trip():
    application = MicrogridApplication.__new__(MicrogridApplication)
    application.values = {
        "source_mode": FakeValueVariable("live_api"),
        "region_id": FakeValueVariable("ercot_houston_hub"),
        "price_mode": FakeValueVariable("time_of_use"),
        "tariff_id": FakeValueVariable(
            "pge_b10_secondary_bundled_2026_03_01"
        ),
        "meter_topology_mode": FakeValueVariable("single_pcc"),
    }
    application.price_mode_combobox = FakeConfigurableWidget()
    application.tariff_combobox = FakeConfigurableWidget()
    application.fixed_price_entry = FakeConfigurableWidget()
    application.price_csv_entry = FakeConfigurableWidget()
    application.price_csv_button = FakeConfigurableWidget()
    application.meter_topology_combobox = FakeConfigurableWidget()
    application.submeter_count_entry = FakeConfigurableWidget()
    application.previous_peak_entry = FakeConfigurableWidget()
    application.tariff_explanation = FakeConfigurableWidget()

    application._update_region_pricing_options()

    assert application.values["price_mode"].get() == "wholesale_market"
    assert application.tariff_combobox.configuration["state"] == "disabled"

    application.values["region_id"].set("caiso_np15")
    application._update_region_pricing_options()

    assert application.values["price_mode"].get() == "time_of_use"
    assert application.values["tariff_id"].get() == (
        "pge_b10_secondary_bundled_2026_03_01"
    )
    assert application.tariff_combobox.configuration["state"] == "readonly"
    assert application.meter_topology_combobox.configuration["state"] == "readonly"


def test_gui_preferences_round_trip_latest_valid_selections(tmp_path):
    preferences_path = tmp_path / "gui_preferences.json"
    writer = MicrogridApplication.__new__(MicrogridApplication)
    writer.preferences_path = preferences_path
    writer.values = {
        "region_id": FakeValueVariable("ercot_houston_hub"),
        "price_mode": FakeValueVariable("wholesale_market"),
        "start_date": FakeValueVariable("2026-09-01"),
        "pv_capacity": FakeValueVariable("0"),
        "include_degradation_in_optimization": FakeValueVariable("true"),
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
        "include_degradation_in_optimization": FakeValueVariable("false"),
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
    assert reader.values["include_degradation_in_optimization"].get() == "true"
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


def test_build_review_rows_describes_capacity_factor_csv():
    rows = build_review_rows(
        source_mode="live_api",
        region_id="caiso_np15",
        start_date="2026-08-25",
        end_date_inclusive="2026-08-25",
        timestep_minutes="15",
        price_mode="wholesale_market",
        strategies=("cost_optimal",),
        carbon_weights=("0.20",),
        degradation_cost="0.03",
        battery_active=True,
        battery_capacity="20",
        battery_initial_energy="10",
        battery_max_charge="5",
        battery_max_discharge="5",
        pv_capacity="30",
        load_power="25",
        load_profile_mode="constant",
        load_archetype="office",
        load_variability="0",
        tariff_id="",
        meter_topology_mode="single_pcc",
        submeter_count="1",
        previous_peak_kw="",
        pv_profile_method="capacity_factor_csv",
        pv_capacity_factor_csv_path="/profiles/site-pv.csv",
    )

    assert (
        "Profiles",
        "PV profile method",
        "Capacity-factor CSV; site-pv.csv; rated 30 kW",
    ) in rows
    # A capacity-factor profile uses no weather and no site, and the review
    # says so rather than leaving a stale row from another mode.
    assert ("Profiles", "PV weather source", "Not used") in rows
    assert ("Profiles", "PV system model", "Not used") in rows
    assert ("Profiles", "PV site location", "Not used") in rows


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


def test_pv_diagnostic_chart_uses_phase2_power_stage_contract():
    import pandas as pd
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from src.profiles import EQUIPMENT_POWER_STAGE_COLUMNS
    from src.simulation.results_visualization import (
        available_pv_power_stages,
        draw_pv_power_stages,
    )

    diagnostics = pd.DataFrame({
        "timestamp": pd.date_range("2026-06-01", periods=3, freq="15min"),
        **{
            column: [0.0, float(index + 1), 0.0]
            for index, column in enumerate(EQUIPMENT_POWER_STAGE_COLUMNS)
            if column != "timestamp"
        },
    })
    expected = tuple(
        column for column in EQUIPMENT_POWER_STAGE_COLUMNS
        if column != "timestamp"
    )

    assert available_pv_power_stages(diagnostics) == expected

    figure = Figure(figsize=(8, 4), layout="constrained")
    canvas = FigureCanvasAgg(figure)
    draw_pv_power_stages(figure, diagnostics)
    canvas.draw()

    assert len(figure.axes[0].lines) == len(expected)
    assert figure.axes[0].get_ylabel() == "Power (kW)"


class FakeFrame:
    """A section frame that records whether it is currently packed."""

    def __init__(self) -> None:
        self.packed = False

    def pack(self, **_kwargs) -> None:
        self.packed = True

    def pack_forget(self) -> None:
        self.packed = False


PV_SECTION_ROW_COUNTS = {
    "profile": 4,
    "weather": 8,
    "model": 12,
    "location": 6,
}


def build_pv_application(**selections):
    """A MicrogridApplication with fake widgets for every Step 2 control.

    Row numbers mirror the real layout, so a test can assert that the field on
    a given row came back after a selection changed -- which is the behaviour
    the grid_remove/grid_slaves bug used to break.
    """

    values = {
        "source_mode": FakeValueVariable("live_api"),
        "pv_profile_method": FakeValueVariable("weather"),
        "weather_source": FakeValueVariable("csv"),
        "pv_system_model": FakeValueVariable("generic"),
        "pv_latitude": FakeValueVariable("37.77"),
        "pv_longitude": FakeValueVariable("-122.42"),
        "location_query": FakeValueVariable("San Francisco, CA"),
        "load_profile_mode": FakeValueVariable("constant"),
    }
    for name, value in selections.items():
        values[name] = FakeValueVariable(value)

    application = MicrogridApplication.__new__(MicrogridApplication)
    application.values = values
    application.show_coordinates = FakeBooleanVariable(False)

    application.pv_section_frames = {
        name: FakeFrame() for name in PV_SECTION_ROW_COUNTS
    }
    application.pv_section_rows = {
        section: {
            row: (FakeConfigurableWidget(),) for row in range(count)
        }
        for section, count in PV_SECTION_ROW_COUNTS.items()
    }

    application.pv_profile_method_combobox = FakeConfigurableWidget()
    application.weather_source_combobox = FakeConfigurableWidget()
    application.pv_system_model_combobox = FakeConfigurableWidget()
    application.pv_capacity_entry = FakeConfigurableWidget()
    application.pv_capacity_factor_csv_widgets = (
        FakeConfigurableWidget(), FakeConfigurableWidget()
    )
    application.weather_csv_widgets = (
        FakeConfigurableWidget(), FakeConfigurableWidget()
    )
    application.nsrdb_year_entry = FakeConfigurableWidget()
    application.nsrdb_time_step_combobox = FakeConfigurableWidget()
    application.fetch_weather_button = FakeConfigurableWidget()
    application.pv_orientation_entries = [
        FakeConfigurableWidget(), FakeConfigurableWidget()
    ]
    application.pv_generic_only_entries = [
        FakeConfigurableWidget(), FakeConfigurableWidget()
    ]
    application.pv_generic_entries = [
        *application.pv_generic_only_entries,
        *application.pv_orientation_entries,
    ]
    application.pv_module_combobox = FakeConfigurableWidget()
    application.pv_inverter_combobox = FakeConfigurableWidget()
    application.pv_module_search_button = FakeConfigurableWidget()
    application.pv_inverter_search_button = FakeConfigurableWidget()
    application.pv_equipment_entries = [
        FakeConfigurableWidget() for _ in range(4)
    ]
    application.pv_equipment_summary = FakeConfigurableWidget()
    application.location_query_entry = FakeConfigurableWidget()
    application.location_search_button = FakeConfigurableWidget()
    application.show_coordinates_checkbutton = FakeConfigurableWidget()
    application.location_result_label = FakeConfigurableWidget()
    application.pv_coordinate_entries = [
        FakeConfigurableWidget(), FakeConfigurableWidget()
    ]
    application._cec_options_loaded = True
    application._update_equipment_summary = lambda *_args: None

    return application


def visible_rows(application, section):
    return {
        row
        for row, widgets in application.pv_section_rows[section].items()
        if widgets[0].visible
    }


def packed_sections(application):
    return {
        name
        for name, frame in application.pv_section_frames.items()
        if frame.packed
    }


## CEC equipment search ---------------------------------------------------


def test_cec_search_matches_multiple_readable_terms_and_reports_total():
    names = (
        "Canadian_Solar_Inc__CS6X_300M",
        "Canadian_Solar_Inc__CS6K_285M",
        "SMA_America__STP_50_US_41__480V_",
    )

    matches, total = filter_cec_equipment_names(
        names,
        "canadian 300m",
        limit=10,
    )

    assert matches == ("Canadian_Solar_Inc__CS6X_300M",)
    assert total == 1
    assert format_cec_equipment_name(matches[0]) == (
        "Canadian Solar Inc — CS6X 300M"
    )


def test_cec_search_bounds_large_result_sets_without_losing_total():
    names = tuple(f"Example_Module_{index}" for index in range(20))

    matches, total = filter_cec_equipment_names(names, "example", limit=5)

    assert matches == names[:5]
    assert total == 20


## Step 2 progressive disclosure ------------------------------------------


def test_capacity_factor_method_shows_only_its_own_fields():
    application = build_pv_application(pv_profile_method="capacity_factor_csv")

    application._update_pv_controls()

    # Weather source, system model and site location answer questions a
    # capacity-factor CSV does not raise, so they are not on screen at all.
    assert packed_sections(application) == {"profile"}
    assert visible_rows(application, "profile") == {0, 1, 2, 3}
    assert (
        application.pv_capacity_factor_csv_widgets[0].configuration["state"]
        == "normal"
    )
    assert application.pv_capacity_entry.configuration["state"] == "normal"
    assert application.weather_csv_widgets[0].configuration["state"] == "disabled"


def test_weather_method_reveals_the_other_three_sections():
    application = build_pv_application(pv_profile_method="weather")

    application._update_pv_controls()

    assert packed_sections(application) == {
        "profile", "weather", "model", "location"
    }
    # The capacity-factor CSV rows are gone; only the method selector remains
    # in the profile section.
    assert visible_rows(application, "profile") == {0}


def test_switching_between_profile_methods_repeatedly_restores_controls():
    # The grid_remove/grid_slaves bug made a hidden widget unreachable, so a
    # field could disappear permanently after two switches. Three round trips
    # would have caught it.
    application = build_pv_application(pv_profile_method="capacity_factor_csv")

    for _ in range(3):
        application.values["pv_profile_method"].set("capacity_factor_csv")
        application._update_pv_controls()
        assert visible_rows(application, "profile") == {0, 1, 2, 3}
        assert packed_sections(application) == {"profile"}

        application.values["pv_profile_method"].set("weather")
        application._update_pv_controls()
        assert visible_rows(application, "profile") == {0}
        assert len(packed_sections(application)) == 4
        assert visible_rows(application, "weather") == {0, 1, 2}


def test_switching_between_generic_and_equipment_restores_fields():
    application = build_pv_application()

    for _ in range(3):
        application.values["pv_system_model"].set("generic")
        application._update_pv_controls()
        assert visible_rows(application, "model") == {0, 1, 2, 3, 4}
        assert (
            application.pv_generic_only_entries[0].configuration["state"]
            == "normal"
        )
        assert application.pv_module_combobox.configuration["state"] == "disabled"

        application.values["pv_system_model"].set("cec_equipment")
        application._update_pv_controls()
        # Rows 2 and 3 are tilt and azimuth: both models transpose irradiance
        # onto the array plane, so both must show the orientation they use.
        assert visible_rows(application, "model") == {
            0, 2, 3, 5, 6, 7, 8, 9, 10, 11
        }
        assert (
            application.pv_generic_only_entries[0].configuration["state"]
            == "disabled"
        )
        assert application.pv_module_combobox.configuration["state"] == "readonly"
        assert application.pv_module_search_button.configuration["state"] == "normal"
        assert application.pv_inverter_search_button.configuration["state"] == "normal"
        assert application.pv_equipment_entries[0].configuration["state"] == "normal"


def test_orientation_is_editable_under_both_system_models():
    # The equipment model reads tilt and azimuth exactly as the generic one
    # does. Leaving them hidden let a stored orientation move the answer by
    # nearly twenty percent with nothing on screen to explain it.
    application = build_pv_application()

    for system_model in ("generic", "cec_equipment"):
        application.values["pv_system_model"].set(system_model)
        application._update_pv_controls()

        assert {2, 3} <= visible_rows(application, "model"), system_model

        for entry in application.pv_orientation_entries:
            assert entry.configuration["state"] == "normal", system_model


def test_orientation_is_disabled_when_no_weather_model_is_selected():
    application = build_pv_application(pv_profile_method="capacity_factor_csv")

    application._update_pv_controls()

    for entry in application.pv_orientation_entries:
        assert entry.configuration["state"] == "disabled"


def test_switching_between_weather_csv_and_api_restores_fields():
    application = build_pv_application()

    for _ in range(3):
        application.values["weather_source"].set("csv")
        application._update_pv_controls()
        assert visible_rows(application, "weather") == {0, 1, 2}
        assert application.weather_csv_widgets[0].configuration["state"] == "normal"
        assert application.fetch_weather_button.configuration["state"] == "disabled"

        application.values["weather_source"].set("nsrdb")
        application._update_pv_controls()
        assert visible_rows(application, "weather") == {0, 3, 4, 5, 6, 7}
        assert application.weather_csv_widgets[0].configuration["state"] == "disabled"
        assert application.fetch_weather_button.configuration["state"] == "normal"
        assert application.nsrdb_year_entry.configuration["state"] == "normal"


def test_coordinates_stay_folded_away_until_advanced_is_opened():
    application = build_pv_application()

    application._update_pv_controls()
    assert visible_rows(application, "location") == {0, 1, 2, 5}

    application.show_coordinates.set(True)
    application._update_pv_controls()
    assert visible_rows(application, "location") == {0, 1, 2, 3, 4, 5}

    application.show_coordinates.set(False)
    application._update_pv_controls()
    assert visible_rows(application, "location") == {0, 1, 2, 5}


def test_integrated_csv_mode_disables_every_new_pv_control():
    # load_kw and pv_kw come from the integrated file, so Step 2's profile
    # controls describe nothing and must not look editable.
    application = build_pv_application(source_mode="integrated_csv")

    application._update_pv_controls()

    assert packed_sections(application) == {"profile"}
    assert (
        application.pv_profile_method_combobox.configuration["state"] == "disabled"
    )
    assert application.weather_source_combobox.configuration["state"] == "disabled"
    assert application.pv_system_model_combobox.configuration["state"] == "disabled"
    assert application.fetch_weather_button.configuration["state"] == "disabled"
    assert application.location_search_button.configuration["state"] == "disabled"
    assert application.pv_coordinate_entries[0].configuration["state"] == "disabled"


## Site location search ---------------------------------------------------


def test_location_search_populates_latitude_and_longitude():
    application = build_pv_application()
    application.location_search = _StubLocationSearch(
        GeocodedLocation(
            query="Oakland, CA",
            display_name="Oakland, Alameda County, California",
            latitude=37.8044,
            longitude=-122.2712,
            provider="stub",
        )
    )
    application.values["location_query"].set("Oakland, CA")

    application._search_site_location()

    assert float(application.values["pv_latitude"].get()) == pytest.approx(37.8044)
    assert float(application.values["pv_longitude"].get()) == pytest.approx(
        -122.2712
    )
    assert "Oakland" in application.location_result_label.configuration["text"]


def test_a_geocoding_failure_leaves_the_previous_coordinates_intact():
    # The coordinates are what the model actually uses. A provider being
    # unreachable is no reason to lose ones that were already correct.
    application = build_pv_application()
    application.location_search = _StubLocationSearch(
        error=GeocodingError("The location service could not be reached.")
    )
    application.values["pv_latitude"].set("37.77")
    application.values["pv_longitude"].set("-122.42")

    application._search_site_location()

    assert application.values["pv_latitude"].get() == "37.77"
    assert application.values["pv_longitude"].get() == "-122.42"
    assert "failed" in application.location_result_label.configuration["text"]


class _StubLocationSearch:
    def __init__(self, location=None, error=None) -> None:
        self.location = location
        self.error = error

    def search(self, query):
        if self.error is not None:
            raise self.error
        return self.location


## Selection mapping ------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "model", "expected"),
    [
        ("capacity_factor_csv", "generic", "capacity_factor_csv"),
        ("capacity_factor_csv", "cec_equipment", "capacity_factor_csv"),
        ("weather", "generic", "weather_generic"),
        ("weather", "cec_equipment", "weather_equipment"),
    ],
)
def test_the_three_selections_resolve_to_one_backend_mode(method, model, expected):
    assert resolve_pv_profile_mode(method, model) == expected


def test_an_unsupported_selection_is_rejected_by_name():
    with pytest.raises(ValueError) as error:
        resolve_pv_profile_mode("weather", "measured_inverter")

    assert "measured_inverter" in str(error.value)


@pytest.mark.parametrize(
    ("legacy", "expected"),
    [
        ("capacity_factor_csv", ("capacity_factor_csv", "csv", "generic")),
        ("weather_generic", ("weather", "csv", "generic")),
        ("weather_equipment", ("weather", "csv", "cec_equipment")),
        # No synthetic control survives the redesign, so the stored value
        # falls back to the remaining non-weather method.
        ("synthetic", ("capacity_factor_csv", "csv", "generic")),
    ],
)
def test_legacy_saved_modes_map_onto_the_new_selections(legacy, expected):
    assert migrate_legacy_pv_profile_mode(legacy) == expected


def test_an_unrecognised_saved_mode_leaves_the_defaults_alone():
    assert migrate_legacy_pv_profile_mode("measured_inverter") is None


def test_legacy_preferences_restore_the_three_controls(tmp_path):
    preferences = tmp_path / "gui_preferences.json"
    preferences.write_text(
        json.dumps(
            {
                "version": 2,
                "values": {
                    "pv_profile_mode": "weather_equipment",
                    "pv_capacity": "45",
                },
                "strategies": {"cost_optimal": True},
            }
        )
    )

    application = MicrogridApplication.__new__(MicrogridApplication)
    application.values = {
        "pv_profile_method": FakeValueVariable("capacity_factor_csv"),
        "weather_source": FakeValueVariable("csv"),
        "pv_system_model": FakeValueVariable("generic"),
        "pv_capacity": FakeValueVariable("20"),
    }
    application.strategy_values = {
        "no_battery": FakeBooleanVariable(False),
        "cost_optimal": FakeBooleanVariable(False),
    }
    application.preferences_path = preferences

    application._load_preferences()

    assert application.values["pv_profile_method"].get() == "weather"
    assert application.values["pv_system_model"].get() == "cec_equipment"
    assert application.values["weather_source"].get() == "csv"
    # Everything else in the old file still restores.
    assert application.values["pv_capacity"].get() == "45"


## Step 3 review ----------------------------------------------------------


def _weather_review_rows(**overrides):
    settings = {
        "source_mode": "live_api",
        "region_id": "caiso_np15",
        "start_date": "2026-08-25",
        "end_date_inclusive": "2026-08-25",
        "timestep_minutes": "15",
        "price_mode": "wholesale_market",
        "strategies": ("cost_optimal",),
        "carbon_weights": ("0.20",),
        "degradation_cost": "0.03",
        "battery_active": True,
        "battery_capacity": "20",
        "battery_initial_energy": "10",
        "battery_max_charge": "5",
        "battery_max_discharge": "5",
        "pv_capacity": "30",
        "load_power": "25",
        "load_profile_mode": "constant",
        "load_archetype": "office",
        "load_variability": "0",
        "tariff_id": "",
        "meter_topology_mode": "single_pcc",
        "submeter_count": "1",
        "previous_peak_kw": "",
        "pv_profile_method": "weather",
        "weather_source": "csv",
        "pv_system_model": "generic",
        "weather_csv_path": "/weather/sf_2023.csv",
        "location_query": "San Francisco, CA",
        "pv_latitude": "37.77",
        "pv_longitude": "-122.42",
        "pv_tilt_degrees": "20",
        "pv_azimuth_degrees": "180",
    }
    settings.update(overrides)
    return build_review_rows(**settings)


def test_review_names_all_three_selections_and_the_site():
    rows = _weather_review_rows()

    assert (
        "Profiles", "PV profile method", "Calculate from weather"
    ) in rows
    assert (
        "Profiles",
        "PV weather source",
        "Upload weather CSV; sf_2023.csv",
    ) in rows
    assert (
        "Profiles",
        "PV system model",
        "Generic array; rated 30 kW; tilt 20 deg, azimuth 180 deg",
    ) in rows
    assert (
        "Profiles",
        "PV site location",
        "37.77, -122.42 (searched: San Francisco, CA)",
    ) in rows


def test_review_names_the_api_weather_source_and_the_equipment():
    rows = _weather_review_rows(
        weather_source="nsrdb",
        pv_system_model="cec_equipment",
        weather_csv_path="/cache/nsrdb_2023.csv",
        pv_module_name="Canadian_Solar_Inc__CS6X_300M",
        pv_inverter_name="SMA_America__STP_50_US_41__480V_",
        pv_equipment_rating="58.51 kW DC, 50.01 kW AC (DC/AC 1.17)",
    )

    assert (
        "Profiles",
        "PV weather source",
        "Retrieve weather from API (NSRDB); nsrdb_2023.csv",
    ) in rows
    assert (
        "Profiles",
        "PV system model",
        "Named CEC equipment; module Canadian_Solar_Inc__CS6X_300M; "
        "inverter SMA_America__STP_50_US_41__480V_; "
        "tilt 20 deg, azimuth 180 deg",
    ) in rows
    assert (
        "Microgrid",
        "PV capacity",
        "58.51 kW DC, 50.01 kW AC (DC/AC 1.17)",
    ) in rows


def test_integrated_csv_review_does_not_claim_a_pv_model():
    rows = _weather_review_rows(source_mode="integrated_csv")

    assert ("Profiles", "PV profile method", "Integrated CSV pv_kw") in rows
    assert (
        "Profiles", "PV weather source", "Included in integrated CSV"
    ) in rows
    assert ("Profiles", "PV site location", "Not used") in rows


def test_the_selection_description_reads_as_one_line():
    assert describe_pv_selection(
        pv_profile_method="weather",
        weather_source="nsrdb",
        pv_system_model="cec_equipment",
    ) == (
        "Calculate from weather — Retrieve weather from API (NSRDB) — "
        "Named CEC equipment"
    )
    assert describe_pv_selection(
        pv_profile_method="capacity_factor_csv",
        weather_source="csv",
        pv_system_model="generic",
    ) == "Capacity-factor CSV"


def test_the_equipment_summary_reports_the_derived_module_count():
    configuration = build_equipment_pv_configuration(
        latitude=37.77,
        longitude=-122.42,
        tilt_degrees=20.0,
        azimuth_degrees=180.0,
        module_name="Canadian_Solar_Inc__CS6X_300M",
        inverter_name="SMA_America__STP_50_US_41__480V_",
        modules_per_string=15,
        strings=13,
        inverter_count=2,
        mppt_input_count=2,
    )

    summary = describe_equipment_ratings(configuration)

    assert "390 modules" in summary
    assert "kW DC" in summary and "kW AC" in summary
    assert "DC/AC" in summary
    assert "grid-following" in summary


## Result export metadata -------------------------------------------------


def _export_application(**overrides):
    """A MicrogridApplication carrying only what export metadata reads."""

    values = {
        "source_mode": "live_api",
        "signal_csv_path": "",
        "region_id": "caiso_np15",
        "market_provider": "caiso",
        "market_location": "TH_NP15_GEN-APND",
        "carbon_provider": "electricity_maps",
        "carbon_zone": "US-CAL-CISO",
        "timezone": "America/Los_Angeles",
        "start_date": "2026-06-21",
        "end_date_inclusive": "2026-06-21",
        "timestep_minutes": "15",
        "price_mode": "wholesale_market",
        "tariff_id": "",
        "meter_topology_mode": "single_pcc",
        "submeter_count": "1",
        "previous_peak_kw": "",
        "carbon_weight_mode": "single",
        "carbon_weight_single": "0.20",
        "carbon_weight_list": "0.00, 0.10",
        "carbon_weight_start": "0.00",
        "carbon_weight_end": "0.50",
        "carbon_weight_interval": "0.10",
        "degradation_cost": "0.03",
        "battery_capacity": "20",
        "battery_initial_energy": "10",
        "battery_max_charge": "5",
        "battery_max_discharge": "5",
        "pv_capacity": "30",
        "pv_profile_method": "weather",
        "weather_source": "nsrdb",
        "pv_system_model": "generic",
        "pv_capacity_factor_csv_path": "",
        "weather_csv_path": "/cache/weather/nsrdb_2023.csv",
        "nsrdb_year": "2023",
        "nsrdb_time_step_minutes": "60",
        "location_query": "San Francisco, CA",
        "pv_latitude": "37.770000",
        "pv_longitude": "-122.420000",
        "pv_tilt_degrees": "20",
        "pv_azimuth_degrees": "180",
        "pv_dc_ac_ratio": "1.2",
        "pv_module_name": "Canadian_Solar_Inc__CS6X_300M",
        "pv_inverter_name": "SMA_America__STP_50_US_41__480V_",
        "pv_modules_per_string": "15",
        "pv_strings": "13",
        "pv_inverter_count": "1",
        "pv_mppt_input_count": "2",
        "load_profile_mode": "constant",
        "load_power": "25",
        "load_archetype": "office",
        "load_variability": "0",
    }
    values.update(overrides)

    application = MicrogridApplication.__new__(MicrogridApplication)
    application.values = {
        name: FakeValueVariable(value) for name, value in values.items()
    }
    application.strategy_values = {
        name: FakeBooleanVariable(name in {"no_battery", "cost_optimal"})
        for name in STRATEGY_LABELS
    }
    return application


def test_export_metadata_records_all_three_selections_and_the_site():
    application = _export_application()

    parameters = application._current_export_parameters()

    assert parameters["input_pv_profile_method"] == "weather"
    assert parameters["input_weather_source"] == "nsrdb"
    assert parameters["input_pv_system_model"] == "generic"
    assert parameters["input_pv_location_query"] == "San Francisco, CA"
    assert parameters["input_pv_latitude"] == "37.770000"
    assert parameters["input_nsrdb_year"] == "2023"
    assert parameters["input_nsrdb_time_step_minutes"] == "60"
    # The derived backend mode is still exported, so an older reader of the
    # results CSV keeps working.
    assert parameters["input_pv_profile_mode"] == "weather_generic"


def test_export_metadata_omits_weather_fields_for_a_capacity_factor_run():
    application = _export_application(
        pv_profile_method="capacity_factor_csv",
        pv_capacity_factor_csv_path="/profiles/site-pv.csv",
    )

    parameters = application._current_export_parameters()

    assert parameters["input_pv_profile_mode"] == "capacity_factor_csv"
    assert parameters["input_pv_capacity_factor_csv_path"] == (
        "/profiles/site-pv.csv"
    )
    # Nothing about weather, location or NSRDB applied to this run, so nothing
    # about them is asserted in the export.
    for name in (
        "input_weather_source",
        "input_pv_system_model",
        "input_pv_location_query",
        "input_pv_latitude",
        "input_pv_longitude",
        "input_weather_csv_path",
        "input_nsrdb_year",
    ):
        assert parameters[name] == "", name


def test_export_metadata_records_the_equipment_plant():
    application = _export_application(pv_system_model="cec_equipment")

    parameters = application._current_export_parameters()

    assert parameters["input_pv_profile_mode"] == "weather_equipment"
    assert parameters["input_pv_system_model"] == "cec_equipment"
    assert parameters["input_pv_module_name"] == "Canadian_Solar_Inc__CS6X_300M"
    assert parameters["input_pv_modules_per_string"] == 15
    assert parameters["input_pv_control_mode"] == "grid_following"
    assert parameters["input_pv_capacity_kw"] == pytest.approx(58.5, rel=0.02)


def test_integrated_csv_export_claims_no_pv_model():
    application = _export_application(source_mode="integrated_csv")

    parameters = application._current_export_parameters()

    assert parameters["input_pv_profile_mode"] == "integrated_csv"
    assert parameters["input_pv_profile_method"] == "integrated_csv"
    assert parameters["input_weather_source"] == ""
    assert parameters["input_pv_latitude"] == ""


## Real-widget smoke test -------------------------------------------------
#
# The fake-widget tests above are fast and precise about which row is visible,
# but they supply every attribute themselves -- so they cannot notice that the
# real page builder forgot to create one. This test builds the actual window.


@pytest.fixture
def tk_application():
    tkinter = pytest.importorskip("tkinter")

    from src.simulation.application_interface import (
        create_guided_application_window,
    )

    try:
        window = create_guided_application_window()
    except tkinter.TclError as error:  # no display available
        pytest.skip(f"Tk is unavailable here: {error}")

    window.update_idletasks()
    try:
        yield window.microgrid_application, window
    finally:
        window.destroy()


def _real_packed_sections(application):
    return {
        name
        for name, frame in application.pv_section_frames.items()
        if frame.winfo_manager()
    }


def _real_visible_rows(application, section):
    return {
        row
        for row, widgets in application.pv_section_rows[section].items()
        if widgets and widgets[0].winfo_manager()
    }


def test_the_built_page_survives_every_selection_combination(tk_application):
    # Selecting named CEC equipment used to raise AttributeError because the
    # flag guarding the one-off database load was initialised in the layout
    # block rather than with the rest of the application's state.
    application, window = tk_application

    combinations = (
        ("capacity_factor_csv", "csv", "generic"),
        ("weather", "csv", "generic"),
        ("weather", "nsrdb", "generic"),
        ("weather", "nsrdb", "cec_equipment"),
        ("weather", "csv", "cec_equipment"),
        ("capacity_factor_csv", "csv", "generic"),
    )

    for method, weather_source, system_model in combinations:
        application.values["pv_profile_method"].set(method)
        application.values["weather_source"].set(weather_source)
        application.values["pv_system_model"].set(system_model)
        application._update_pv_controls()
        window.update_idletasks()

        if method == "capacity_factor_csv":
            assert _real_packed_sections(application) == {"profile"}
            assert _real_visible_rows(application, "profile") == {0, 1, 2, 3}
        else:
            assert _real_packed_sections(application) == {
                "profile", "weather", "model", "location"
            }
            assert _real_visible_rows(application, "weather") == (
                {0, 1, 2} if weather_source == "csv" else {0, 3, 4, 5, 6, 7}
            )
            assert _real_visible_rows(application, "model") == (
                {0, 1, 2, 3, 4}
                if system_model == "generic"
                else {0, 2, 3, 5, 6, 7, 8, 9, 10, 11}
            )


def test_the_built_page_keeps_the_pv_sections_above_the_load_section(
    tk_application,
):
    # pack() appends, so re-showing a hidden section would drop it below Load
    # unless every section is re-packed in order. Comparing y positions is the
    # only way to see that from outside.
    application, window = tk_application

    application.values["pv_profile_method"].set("capacity_factor_csv")
    application._update_pv_controls()
    window.update_idletasks()

    application.values["pv_profile_method"].set("weather")
    application._update_pv_controls()
    window.update_idletasks()

    tops = [
        application.pv_section_frames[name].winfo_y()
        for name in ("profile", "location", "weather", "model")
    ]

    assert tops == sorted(tops), tops


def test_the_built_page_derives_equipment_ratings_from_the_form(tk_application):
    application, window = tk_application

    application.values["pv_profile_method"].set("weather")
    application.values["pv_system_model"].set("cec_equipment")
    application._update_pv_controls()
    window.update_idletasks()

    summary = application.pv_equipment_summary.cget("text")

    assert "modules" in summary
    assert "kW DC" in summary
    assert "grid-following" in summary


def test_every_input_the_equipment_model_reads_is_visible_and_editable(
    tk_application,
):
    """No hidden input may change an equipment-model result.

    The redesign briefly hid array tilt and azimuth under the named-equipment
    selection while the model went on reading their stored values -- a stored
    orientation moved a clear-day yield by roughly eighteen percent with
    nothing on screen to explain it. This walks the arguments
    ``build_equipment_pv_configuration`` actually takes and insists each one
    is reachable, so adding an argument without a control fails here.
    """

    import inspect

    from src.simulation.interface_analysis import (
        build_equipment_pv_configuration,
    )

    application, window = tk_application

    application.values["pv_profile_method"].set("weather")
    application.values["pv_system_model"].set("cec_equipment")
    application.show_coordinates.set(True)
    application._update_pv_controls()
    window.update_idletasks()

    # Model argument -> the GUI variable that supplies it.
    supplied_by = {
        "latitude": "pv_latitude",
        "longitude": "pv_longitude",
        "tilt_degrees": "pv_tilt_degrees",
        "azimuth_degrees": "pv_azimuth_degrees",
        "module_name": "pv_module_name",
        "inverter_name": "pv_inverter_name",
        "modules_per_string": "pv_modules_per_string",
        "strings": "pv_strings",
        "inverter_count": "pv_inverter_count",
        "mppt_input_count": "pv_mppt_input_count",
    }

    arguments = set(
        inspect.signature(build_equipment_pv_configuration).parameters
    )
    assert arguments == set(supplied_by), (
        "build_equipment_pv_configuration gained or lost an argument; map it "
        "to the control that supplies it."
    )

    # Every widget bound to one of those variables must be shown and enabled.
    def bound_widgets(variable_name):
        target = str(application.values[variable_name])
        found = []
        for section in application.pv_section_frames.values():
            for child in section.winfo_children():
                if str(child.cget("textvariable") or "") == target:
                    found.append(child)
        return found

    for argument, variable_name in sorted(supplied_by.items()):
        widgets = bound_widgets(variable_name)
        assert widgets, f"{argument} has no control bound to {variable_name}"

        visible = [
            widget
            for widget in widgets
            if widget.winfo_manager()
            and str(widget.cget("state")) != "disabled"
        ]
        assert visible, (
            f"{argument} is read by the equipment model but no control for "
            f"{variable_name} is visible and editable."
        )


## NSRDB year follows the horizon ------------------------------------------


def _weather_application(
    start="2026-05-31",
    end="2026-06-02",
    year="2026",
    timezone="America/Los_Angeles",
):
    application = MicrogridApplication.__new__(MicrogridApplication)
    application.values = {
        "start_date": FakeValueVariable(start),
        "end_date_inclusive": FakeValueVariable(end),
        "timezone": FakeValueVariable(timezone),
        "timestep_minutes": FakeValueVariable("15"),
        "nsrdb_year": FakeValueVariable(year),
    }
    application.nsrdb_year_notice = FakeConfigurableWidget()
    application._nsrdb_year_auto_value = year
    return application


def test_a_year_matching_the_horizon_shows_no_notice():
    application = _weather_application(year="2026")

    application._refresh_nsrdb_year_notice()

    assert application.nsrdb_year_notice.configuration["text"] == ""


def test_a_mismatched_year_is_explained_before_any_fetch():
    application = _weather_application(year="2025")

    application._refresh_nsrdb_year_notice()

    text = application.nsrdb_year_notice.configuration["text"]
    assert "2025" in text and "2026" in text
    assert "proxy" in text


def test_the_year_follows_the_start_date_while_untouched():
    application = _weather_application(start="2026-05-31", year="2026")

    application.values["start_date"].set("2024-03-01")
    application._on_horizon_changed()

    assert application.values["nsrdb_year"].get() == "2024"


def test_an_edited_year_is_not_overwritten_by_the_start_date():
    # A deliberate proxy year must survive a change to the horizon; this is
    # the only way to study a period NSRDB has no weather for.
    application = _weather_application(start="2026-05-31", year="2026")
    application.values["nsrdb_year"].set("2023")   # the person edits it

    application.values["start_date"].set("2024-03-01")
    application._on_horizon_changed()

    assert application.values["nsrdb_year"].get() == "2023"


def test_a_half_typed_date_produces_no_notice_rather_than_an_error():
    application = _weather_application(start="2026-0")

    application._refresh_nsrdb_year_notice()

    assert application.nsrdb_year_notice.configuration["text"] == ""


def test_a_non_numeric_year_produces_no_notice():
    application = _weather_application(year="")

    application._refresh_nsrdb_year_notice()

    assert application.nsrdb_year_notice.configuration["text"] == ""


def test_a_horizon_crossing_new_year_says_one_fetch_is_not_enough():
    application = _weather_application(
        start="2025-12-30", end="2026-01-02", year="2025"
    )

    application._refresh_nsrdb_year_notice()

    text = application.nsrdb_year_notice.configuration["text"]
    assert "2025 and 2026" in text
    assert "separately" in text


def test_cleanpowersf_gui_preserves_account_choice_and_shows_scope():
    from src.billing.cleanpowersf import build_b1
    tariff = build_b1(phase="polyphase", product="supergreen", vintage=2019)
    application = MicrogridApplication.__new__(MicrogridApplication)
    application.values = {key: FakeValueVariable(value) for key, value in {
        "source_mode": "live_api", "region_id": "caiso_np15",
        "price_mode": "time_of_use", "tariff_id": tariff.tariff_id,
        "meter_topology_mode": "single_pcc"}.items()}
    for key in ("price_mode_combobox", "tariff_combobox", "fixed_price_entry",
                "price_csv_entry", "price_csv_button", "meter_topology_combobox",
                "submeter_count_entry", "previous_peak_entry", "tariff_explanation"):
        setattr(application, key, FakeConfigurableWidget())
    application._update_region_pricing_options()
    assert application.values["tariff_id"].get() == tariff.tariff_id
    assert tariff.name in application.tariff_combobox.configuration["values"]
    assert application.tariff_combobox.configuration["state"] == "readonly"
    assert application.previous_peak_entry.configuration["state"] == "disabled"
    assert "PCIA vintage 2019" in application.tariff_explanation.configuration["text"]
    assert "non-exempt" in application.tariff_explanation.configuration["text"]


def test_hetch_hetchy_gui_shows_c1_account_scope():
    from src.billing.hetch_hetchy import build_c1
    tariff = build_c1(premium=True)
    application = MicrogridApplication.__new__(MicrogridApplication)
    application.values = {key: FakeValueVariable(value) for key, value in {
        "source_mode": "live_api", "region_id": "caiso_np15",
        "price_mode": "time_of_use", "tariff_id": tariff.tariff_id,
        "meter_topology_mode": "single_pcc"}.items()}
    for key in ("price_mode_combobox", "tariff_combobox", "fixed_price_entry",
                "price_csv_entry", "price_csv_button", "meter_topology_combobox",
                "submeter_count_entry", "previous_peak_entry", "tariff_explanation"):
        setattr(application, key, FakeConfigurableWidget())
    application._update_region_pricing_options()
    assert application.values["tariff_id"].get() == tariff.tariff_id
    assert tariff.name in application.tariff_combobox.configuration["values"]
    assert application.previous_peak_entry.configuration["state"] == "disabled"
    assert "Hetch Hetchy retail C-1" in application.tariff_explanation.configuration["text"]
    assert "Premium requires confirmed enrollment" in application.tariff_explanation.configuration["text"]


def test_hetch_hetchy_gui_shows_c2_demand_controls():
    from src.billing.hetch_hetchy import build_c2
    tariff = build_c2(voltage="primary", premium=True)
    application = MicrogridApplication.__new__(MicrogridApplication)
    application.values = {key: FakeValueVariable(value) for key, value in {
        "source_mode": "live_api", "region_id": "caiso_np15",
        "price_mode": "time_of_use", "tariff_id": tariff.tariff_id,
        "meter_topology_mode": "single_pcc"}.items()}
    for key in ("price_mode_combobox", "tariff_combobox", "fixed_price_entry",
                "price_csv_entry", "price_csv_button", "meter_topology_combobox",
                "submeter_count_entry", "previous_peak_entry", "tariff_explanation"):
        setattr(application, key, FakeConfigurableWidget())
    application._update_region_pricing_options()
    assert application.values["tariff_id"].get() == tariff.tariff_id
    assert tariff.name in application.tariff_combobox.configuration["values"]
    assert application.previous_peak_entry.configuration["state"] == "normal"
    assert "Hetch Hetchy retail C-2P" in application.tariff_explanation.configuration["text"]
    assert "Premium requires enrollment" in application.tariff_explanation.configuration["text"]


@pytest.mark.parametrize("provider,product", [("peninsula", "eco100"), ("svce", "greenprime"), ("sjce", "totalgreen")])
def test_bay_area_cca_gui_shows_provider_account_scope(provider, product):
    from src.billing.bay_area_cca import build_b1
    tariff = build_b1(provider=provider, product=product, phase="polyphase", vintage=2018)
    application = MicrogridApplication.__new__(MicrogridApplication)
    application.values = {key: FakeValueVariable(value) for key, value in {
        "source_mode": "live_api", "region_id": "caiso_np15",
        "price_mode": "time_of_use", "tariff_id": tariff.tariff_id,
        "meter_topology_mode": "single_pcc"}.items()}
    for key in ("price_mode_combobox", "tariff_combobox", "fixed_price_entry",
                "price_csv_entry", "price_csv_button", "meter_topology_combobox",
                "submeter_count_entry", "previous_peak_entry", "tariff_explanation"):
        setattr(application, key, FakeConfigurableWidget())
    application._update_region_pricing_options()
    assert application.values["tariff_id"].get() == tariff.tariff_id
    assert tariff.name in application.tariff_combobox.configuration["values"]
    assert application.previous_peak_entry.configuration["state"] == "disabled"
    assert tariff.notes == application.tariff_explanation.configuration["text"]
