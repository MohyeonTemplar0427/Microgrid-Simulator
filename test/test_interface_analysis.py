"""Tests for the interface-to-analysis adapter."""

from types import SimpleNamespace

import pandas as pd
import pytest

import src.simulation.interface_analysis as interface_analysis
from src.dispatch.battery import Battery
from src.simulation.interface_analysis import (
    _apply_tariff_billing,
    _build_live_price_source,
    build_analysis_details,
    build_results_table,
    build_equipment_pv_configuration,
    create_temporary_site_profile,
    create_site_profile,
    format_comparison_for_display,
    retail_tariff_ids_for_region,
    run_integrated_csv_analysis,
)
from src.signal_pipeline.horizon import build_horizon
from src.signal_pipeline.price_sources import WholesaleMarketPrice
from src.simulation.model_specifications import MicrogridSpecification


def _comparison() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "scenario": [
                "no_battery",
                "rule_based",
                "cost_optimal",
                "carbon_optimal",
                "combined_optimal",
            ],
            "energy_cost": [10.0, 9.0, 8.0, 8.5, 7.5],
            "degradation_cost": [0.0, 0.1, 0.2, 0.2, 0.3],
            "total_explicit_cost": [10.0, 9.1, 8.2, 8.7, 7.8],
            "emissions_kgCO2": [20.0, 19.0, 18.0, 17.0, 16.0],
            "equivalent_full_cycles": [0.0, 0.2, 0.3, 0.4, 0.5],
            "average_daily_efc": [0.0, 0.1, 0.15, 0.2, 0.25],
            "feasible_intervals": [96] * 5,
            "interval_count": [96] * 5,
        }
    )


def test_create_temporary_site_profile_allows_site_without_pv():
    horizon = build_horizon(
        "2026-08-25",
        1,
        "America/Los_Angeles",
        15,
    )

    profile = create_temporary_site_profile(
        horizon,
        load_kw=250.0,
        pv_capacity_kw=0.0,
    )

    assert profile["pv_kw"].eq(0.0).all()


def test_retail_tariffs_are_available_only_for_caiso_region():
    # Asserted as a set of required members rather than an exact ordered
    # tuple: adding a schedule is routine, so pinning the whole list only
    # produces churn. What must hold is that the PG&E families are all
    # offered and that regions without modelled retail tariffs offer none.
    offered = set(retail_tariff_ids_for_region("caiso_np15"))

    assert {
        "pge_b1_secondary_single_phase_bundled_2026_03_01",
        "pge_b6_secondary_single_phase_bundled_2026_03_01",
        "pge_b10_secondary_bundled_2026_03_01",
        "pge_b19_secondary_mandatory_bundled_2026_03_01",
        "pge_b20_secondary_bundled_2026_03_01",
    } <= offered

    assert retail_tariff_ids_for_region("ercot_houston_hub") == ()
    assert retail_tariff_ids_for_region("pjm_western_hub") == ()


def test_every_offered_tariff_is_registered_and_labelled():
    # A tariff offered for a region but missing from the registry or the
    # dropdown labels breaks the GUI at build time, so check both.
    import src.simulation.application_interface as application_interface
    from src.billing import get_tariff

    for region_id in ("caiso_np15", "ercot_houston_hub", "pjm_western_hub"):
        for tariff_id in retail_tariff_ids_for_region(region_id):
            assert get_tariff(tariff_id).tariff_id == tariff_id
            assert tariff_id in application_interface.TARIFF_LABELS


def test_b1_result_table_omits_demand_columns_and_explains_tou_windows():
    comparison = _comparison().iloc[:1].copy()
    comparison["tariff_has_demand_charge"] = False
    comparison["demand_charge"] = 0.0
    comparison["billed_peak_kw"] = 60.0
    comparison["peak_grid_import_kw"] = 60.0
    comparison["summer_peak_energy_kWh"] = 300.0
    comparison["summer_peak_energy_charge"] = 141.261

    headings, _rows = build_results_table(comparison)

    assert "Demand charge ($)" not in headings
    assert "Billed peak (kW)" not in headings
    assert "Peak import (kW)" in headings
    assert "Summer peak energy, 4–9 p.m. (kWh)" in headings
    assert "Summer peak charge, 4–9 p.m. ($)" in headings


def test_run_integrated_csv_analysis_filters_and_names_scenarios(
    monkeypatch,
    tmp_path,
):
    csv_path = tmp_path / "signals.csv"
    pd.DataFrame({"timestamp": ["2026-08-25"]}).to_csv(csv_path, index=False)

    calls = []
    progress_messages = []

    def fake_run(
        *args,
        carbon_weight,
        scenario_names,
        progress_callback,
        **kwargs,
    ):
        calls.append((carbon_weight, scenario_names))
        progress_callback("test backend phase")
        return SimpleNamespace(comparison=_comparison())

    monkeypatch.setattr(
        interface_analysis,
        "run_microgrid_timeseries_analysis",
        fake_run,
    )

    specification = MicrogridSpecification(
        battery=Battery(
            capacity_kWh=20,
            energy_kWh=10,
            max_charge_kw=5,
            max_discharge_kw=5,
        ),
        pv_capacity_kw=30,
        load_kw=25,
    )

    result = run_integrated_csv_analysis(
        specification,
        csv_path,
        start_date="2026-08-25",
        number_of_days=1,
        timestep_minutes=15,
        expected_timezone="America/Los_Angeles",
        selected_scenarios=("no_battery", "cost_optimal", "combined_optimal"),
        carbon_weights=(0.1, 0.2),
        degradation_cost_per_kWh=0.03,
        progress_callback=progress_messages.append,
    )

    assert calls == [
        (
            0.1,
            ("no_battery", "cost_optimal", "combined_optimal"),
        ),
        (0.2, ("combined_optimal",)),
    ]
    assert result.comparison["scenario"].tolist() == [
        "no_battery",
        "cost_optimal",
        "combined_optimal_0.10",
        "combined_optimal_0.20",
    ]
    by_scenario = result.comparison.set_index("scenario")
    assert by_scenario.loc[
        "no_battery", "carbon_adjusted_operating_cost"
    ] == pytest.approx(12.0)
    assert by_scenario.loc[
        "combined_optimal_0.20", "carbon_adjusted_operating_cost"
    ] == pytest.approx(11.0)
    assert any(
        "test backend phase" in message
        for message in progress_messages
    )


def test_format_comparison_for_display_includes_degradation_cost():
    formatted = format_comparison_for_display(_comparison())

    assert "degradation_cost" in formatted
    assert "combined_optimal" in formatted


def test_create_temporary_site_profile_uses_configured_ratings():
    horizon = build_horizon(
        "2026-08-25",
        1,
        "America/Los_Angeles",
        15,
    )

    profile = create_temporary_site_profile(
        horizon,
        load_kw=25,
        pv_capacity_kw=30,
    )

    assert len(profile) == 96
    assert profile["load_kw"].eq(25).all()
    assert profile["pv_kw"].min() == 0
    assert profile["pv_kw"].max() == 30


def test_create_site_profile_builds_synthetic_load_and_pv():
    horizon = build_horizon(
        "2026-08-25",
        2,
        "America/Los_Angeles",
        15,
    )

    profile = create_site_profile(
        horizon,
        load_kw=25,
        pv_capacity_kw=30,
        load_profile_mode="synthetic",
        load_archetype="office",
        load_variability_fraction=0.0,
    )

    assert len(profile) == 192
    assert profile["load_kw"].max() == pytest.approx(25.0)
    assert profile["load_kw"].nunique() > 1
    assert profile["pv_kw"].max() == pytest.approx(25.5)
    assert profile["pv_kw"].min() == 0


def test_create_site_profile_scales_capacity_factor_csv_by_rated_capacity(
    tmp_path,
):
    horizon = build_horizon(
        "2026-08-25",
        1,
        "America/Los_Angeles",
        15,
    )
    csv_path = tmp_path / "pv_capacity_factor.csv"
    pd.DataFrame(
        {
            "timestamp": horizon.index,
            "capacity_factor": [index / 95 for index in range(96)],
        }
    ).to_csv(csv_path, index=False)

    profile = create_site_profile(
        horizon,
        load_kw=25,
        pv_capacity_kw=30,
        load_profile_mode="constant",
        load_archetype="office",
        load_variability_fraction=0.0,
        pv_profile_mode="capacity_factor_csv",
        pv_capacity_factor_csv_path=csv_path,
    )

    assert profile["pv_kw"].iloc[0] == 0
    assert profile["pv_kw"].iloc[-1] == pytest.approx(30)
    assert profile.attrs["pv_provenance"]["rated_dc_capacity_kw"] == 30


def test_pge_tariff_builds_summer_tou_prices():
    horizon = build_horizon(
        "2026-08-25",
        1,
        "America/Los_Angeles",
        15,
    )

    source = _build_live_price_source(
        "time_of_use",
        horizon,
        fixed_retail_price=None,
        price_csv_path=None,
        tariff_id="pge_b10_secondary_bundled_2026_03_01",
    )
    prices = source.build_prices(horizon)

    assert prices.loc[
        prices["timestamp"].dt.hour == 16,
        "price_per_kWh",
    ].eq(0.33947).all()
    assert prices.loc[
        prices["timestamp"].dt.hour == 10,
        "price_per_kWh",
    ].eq(0.24522).all()


def test_tariff_billing_adds_customer_and_demand_charges():
    timestamps = pd.date_range(
        "2026-08-25",
        periods=4,
        freq="15min",
        tz="America/Los_Angeles",
    )
    dispatch = pd.DataFrame(
        {
            "timestamp": timestamps,
            "grid_import_kw": [250.0] * 4,
            "grid_export_kw": [0.0] * 4,
        }
    )
    comparison = pd.DataFrame(
        {
            "scenario": ["no_battery"],
            "carbon_weight": [0.2],
            "degradation_cost": [0.0],
            "total_explicit_cost": [0.0],
        }
    )
    run = SimpleNamespace(
        dispatch_scenarios={"no_battery": dispatch}
    )

    billed, warnings = _apply_tariff_billing(
        comparison,
        {0.2: run},
        first_weight=0.2,
        tariff_id="pge_b10_secondary_bundled_2026_03_01",
        meter_topology_mode="single_pcc",
        submeter_count=1,
        previous_peak_kw=None,
        timestep_hours=0.25,
    )

    assert billed.loc[0, "customer_charge"] == pytest.approx(11.36882)
    assert billed.loc[0, "demand_charge"] == pytest.approx(5125.0)
    assert billed.loc[0, "billed_peak_kw"] == pytest.approx(250.0)
    assert any("PARTIAL BILLING PERIOD" in warning for warning in warnings)


def test_b1_billing_has_no_demand_charge_and_flags_threshold_month():
    timestamps = pd.date_range(
        "2026-06-01",
        periods=4,
        freq="15min",
        tz="America/Los_Angeles",
    )
    dispatch = pd.DataFrame(
        {
            "timestamp": timestamps,
            "grid_import_kw": [80.0] * 4,
            "grid_export_kw": [0.0] * 4,
        }
    )
    comparison = pd.DataFrame(
        {
            "scenario": ["no_battery"],
            "carbon_weight": [0.2],
            "degradation_cost": [0.0],
            "total_explicit_cost": [0.0],
        }
    )
    run = SimpleNamespace(dispatch_scenarios={"no_battery": dispatch})

    billed, warnings = _apply_tariff_billing(
        comparison,
        {0.2: run},
        first_weight=0.2,
        tariff_id="pge_b1_secondary_polyphase_bundled_2026_03_01",
        meter_topology_mode="single_pcc",
        submeter_count=1,
        previous_peak_kw=None,
        timestep_hours=0.25,
    )

    assert billed.loc[0, "demand_charge"] == pytest.approx(0.0)
    assert not bool(billed.loc[0, "tariff_has_demand_charge"])
    assert billed.loc[0, "summer_off_peak_energy_kWh"] == pytest.approx(80.0)
    assert any("Demand charges are omitted" in note for note in warnings)
    assert any(
        "Fewer than three consecutive" in warning
        for warning in warnings
    )


def test_build_results_table_uses_readable_headings():
    comparison = _comparison().copy()
    comparison["pcc_grid_import_energy_kWh"] = 100.12345
    comparison["peak_grid_import_kw"] = 30.12345
    comparison["billed_peak_kw"] = 31.0
    comparison["minimum_voltage_pu"] = 0.998123
    comparison["maximum_line_loading_percent"] = 4.8
    comparison["maximum_transformer_loading_percent"] = 4.2
    comparison["demand_charge"] = 20.0
    comparison["customer_charge"] = 5.0
    comparison["export_credit"] = 0.0

    headings, rows = build_results_table(comparison)

    assert headings[0] == "Scenario"
    assert headings[1:9] == (
        "Total cost ($)",
        "Energy cost ($)",
        "Demand charge ($)",
        "Peak import (kW)",
        "Billed peak (kW)",
        "Customer charge ($)",
        "Export credit ($)",
        "Degradation ($)",
    )
    assert "Utility bill ($)" not in headings
    assert "Degradation ($)" in headings
    assert "Avg daily EFC" in headings
    assert "Feasible intervals" not in headings
    assert rows[0][0] == "no_battery"
    assert rows[0][1] == "10.00"


def test_build_analysis_details_describes_live_study_horizon():
    details = dict(
        build_analysis_details(
            source_mode="live_api",
            region_id="caiso_np15",
            market_location="TH_NP15_GEN-APND",
            csv_path="",
            start_date="2026-08-25",
            end_date_inclusive="2026-08-26",
            timestep_minutes=15,
        )
    )

    assert details["Data source"] == "Live APIs"
    assert "Northern California" in details["Location"]
    assert "TH_NP15_GEN-APND" in details["Location"]
    assert details["Time range"] == (
        "2026-08-25 → 2026-08-26 (both dates included)"
    )
    assert details["Time interval"] == "15 minutes"


@pytest.mark.parametrize(
    ("region_id", "expected_timezone"),
    [
        ("ercot_houston_hub", "America/Chicago"),
        ("pjm_western_hub", "America/New_York"),
    ],
)
def test_live_regional_analysis_reaches_opendss_results(
    monkeypatch,
    tmp_path,
    region_id,
    expected_timezone,
):
    def fake_prices(self, horizon):
        return pd.DataFrame(
            {
                "timestamp": horizon.index,
                "price_per_kWh": 0.10,
            }
        )

    def fake_carbon(
        api_key,
        zone,
        start_date,
        number_of_days,
        timezone,
    ):
        horizon = build_horizon(
            start_date,
            number_of_days,
            timezone,
            15,
        )
        return pd.DataFrame(
            {
                "timestamp": horizon.index,
                "gCO2/kWh": 300.0,
            }
        )

    monkeypatch.setattr(
        WholesaleMarketPrice,
        "build_prices",
        fake_prices,
    )
    monkeypatch.setattr(
        "src.signal_pipeline.signal_loader."
        "emd.get_multi_day_carbon_data",
        fake_carbon,
    )
    monkeypatch.setattr(
        interface_analysis,
        "DEFAULT_SIGNAL_CACHE_DIRECTORY",
        tmp_path,
    )

    specification = MicrogridSpecification(
        battery=Battery(
            capacity_kWh=20,
            energy_kWh=10,
            max_charge_kw=5,
            max_discharge_kw=5,
        ),
        pv_capacity_kw=30,
        load_kw=25,
    )
    result = interface_analysis.run_live_api_analysis(
        specification,
        start_date="2026-08-25",
        number_of_days=1,
        timestep_minutes=15,
        region_id=region_id,
        market_provider=None,
        market_location=None,
        carbon_provider=None,
        carbon_zone=None,
        timezone=None,
        price_mode="wholesale_market",
        fixed_retail_price=None,
        price_csv_path=None,
        selected_scenarios=("no_battery", "cost_optimal"),
        carbon_weights=(0.20,),
        degradation_cost_per_kWh=0.03,
    )

    assert result.comparison["scenario"].tolist() == [
        "no_battery",
        "cost_optimal",
    ]
    assert all(
        frame["converged"].all()
        for frame in result.runs_by_carbon_weight[
            0.20
        ].powerflow_scenarios.values()
    )
    assert all(
        str(frame["timestamp"].dt.tz) == expected_timezone
        for frame in result.runs_by_carbon_weight[
            0.20
        ].dispatch_scenarios.values()
    )


def test_b6_is_offered_and_labelled_in_the_gui():
    import src.simulation.application_interface as application_interface

    single = "pge_b6_secondary_single_phase_bundled_2026_03_01"
    poly = "pge_b6_secondary_polyphase_bundled_2026_03_01"

    assert single in application_interface.TARIFF_LABELS
    assert poly in application_interface.TARIFF_LABELS
    assert "B-6" in application_interface.TARIFF_LABELS[single]
    # Every offered tariff needs a label or the dropdown build raises.
    for tariff_id in retail_tariff_ids_for_region("caiso_np15"):
        assert tariff_id in application_interface.TARIFF_LABELS


def test_integrated_csv_analysis_bills_against_the_selected_tariff(tmp_path):
    csv_path = _write_small_signal_csv(tmp_path)

    unbilled = run_integrated_csv_analysis(
        _small_specification(),
        csv_path,
        start_date="2026-08-01",
        number_of_days=1,
        timestep_minutes=15,
        expected_timezone="America/Los_Angeles",
        selected_scenarios=("no_battery",),
        carbon_weights=(0.20,),
        degradation_cost_per_kWh=0.03,
    )

    billed = run_integrated_csv_analysis(
        _small_specification(),
        csv_path,
        start_date="2026-08-01",
        number_of_days=1,
        timestep_minutes=15,
        expected_timezone="America/Los_Angeles",
        selected_scenarios=("no_battery",),
        carbon_weights=(0.20,),
        degradation_cost_per_kWh=0.03,
        tariff_id="pge_b6_secondary_single_phase_bundled_2026_03_01",
    )

    # Without a tariff the CSV path produces no utility bill at all.
    assert "total_utility_charge" not in unbilled.comparison.columns
    assert "total_utility_charge" in billed.comparison.columns

    # B-6 carries no demand charge, and one day of customer charge.
    assert billed.comparison["demand_charge"].eq(0.0).all()
    assert billed.comparison["customer_charge"].iloc[0] == pytest.approx(
        0.32854
    )


def test_integrated_csv_billing_flags_the_two_price_bases(tmp_path):
    csv_path = _write_small_signal_csv(tmp_path)

    result = run_integrated_csv_analysis(
        _small_specification(),
        csv_path,
        start_date="2026-08-01",
        number_of_days=1,
        timestep_minutes=15,
        expected_timezone="America/Los_Angeles",
        selected_scenarios=("no_battery",),
        carbon_weights=(0.20,),
        degradation_cost_per_kWh=0.03,
        tariff_id="pge_b6_secondary_single_phase_bundled_2026_03_01",
    )

    assert any("price bases" in w or "own prices" in w for w in result.warnings)


def test_b6_warns_when_the_simulated_peak_exceeds_its_eligibility_ceiling(
    tmp_path,
):
    # 300 kW of load is far above the 75 kW ceiling B-6 is available at.
    csv_path = _write_small_signal_csv(tmp_path, load_kw=300.0)

    result = run_integrated_csv_analysis(
        MicrogridSpecification(
            battery=Battery(
                capacity_kWh=60.0,
                energy_kWh=30.0,
                max_charge_kw=20.0,
                max_discharge_kw=20.0,
            ),
            pv_capacity_kw=25.0,
            load_kw=300.0,
        ),
        csv_path,
        start_date="2026-08-01",
        number_of_days=1,
        timestep_minutes=15,
        expected_timezone="America/Los_Angeles",
        selected_scenarios=("no_battery",),
        carbon_weights=(0.20,),
        degradation_cost_per_kWh=0.03,
        tariff_id="pge_b6_secondary_single_phase_bundled_2026_03_01",
    )

    assert any("75 kW ceiling" in warning for warning in result.warnings)

    # B-10's ceiling is 499 kW, so the same peak raises no eligibility warning.
    b10_result = run_integrated_csv_analysis(
        MicrogridSpecification(
            battery=Battery(
                capacity_kWh=60.0,
                energy_kWh=30.0,
                max_charge_kw=20.0,
                max_discharge_kw=20.0,
            ),
            pv_capacity_kw=25.0,
            load_kw=300.0,
        ),
        csv_path,
        start_date="2026-08-01",
        number_of_days=1,
        timestep_minutes=15,
        expected_timezone="America/Los_Angeles",
        selected_scenarios=("no_battery",),
        carbon_weights=(0.20,),
        degradation_cost_per_kWh=0.03,
        tariff_id="pge_b10_secondary_bundled_2026_03_01",
    )

    assert not any("ceiling" in warning for warning in b10_result.warnings)


def _small_specification() -> MicrogridSpecification:
    return MicrogridSpecification(
        battery=Battery(
            capacity_kWh=60.0,
            energy_kWh=30.0,
            max_charge_kw=20.0,
            max_discharge_kw=20.0,
        ),
        pv_capacity_kw=25.0,
        load_kw=55.0,
    )


def _write_small_signal_csv(tmp_path, load_kw: float = 40.0) -> str:
    timestamps = pd.date_range(
        "2026-08-01 00:00",
        periods=96,
        freq="15min",
        tz="America/Los_Angeles",
    )

    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "load_kw": load_kw,
            "pv_kw": 0.0,
            "price_per_kWh": 0.30,
            "gCO2/kWh": 300.0,
            "net_load_kw": load_kw,
        }
    )

    path = tmp_path / "signal.csv"
    frame.to_csv(path, index=False)
    return str(path)


def test_b20_warns_when_the_simulated_peak_is_below_its_eligibility_floor(
    tmp_path,
):
    # B-20 is only available once demand exceeds 999 kW; 40 kW is far below.
    csv_path = _write_small_signal_csv(tmp_path, load_kw=40.0)

    result = run_integrated_csv_analysis(
        _small_specification(),
        csv_path,
        start_date="2026-08-01",
        number_of_days=1,
        timestep_minutes=15,
        expected_timezone="America/Los_Angeles",
        selected_scenarios=("no_battery",),
        carbon_weights=(0.20,),
        degradation_cost_per_kWh=0.03,
        tariff_id="pge_b20_secondary_bundled_2026_03_01",
    )

    assert any("1,000 kW minimum" in warning for warning in result.warnings)


def test_b20_raises_no_eligibility_warning_for_a_large_enough_site(tmp_path):
    csv_path = _write_small_signal_csv(tmp_path, load_kw=1500.0)

    result = run_integrated_csv_analysis(
        MicrogridSpecification(
            battery=Battery(
                capacity_kWh=60.0,
                energy_kWh=30.0,
                max_charge_kw=20.0,
                max_discharge_kw=20.0,
            ),
            pv_capacity_kw=25.0,
            load_kw=1500.0,
        ),
        csv_path,
        start_date="2026-08-01",
        number_of_days=1,
        timestep_minutes=15,
        expected_timezone="America/Los_Angeles",
        selected_scenarios=("no_battery",),
        carbon_weights=(0.20,),
        degradation_cost_per_kWh=0.03,
        tariff_id="pge_b20_secondary_bundled_2026_03_01",
    )

    assert not any("minimum" in warning for warning in result.warnings)


def test_equipment_configuration_derives_gui_plant_ratings():
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

    assert configuration.rated_dc_capacity_kw == pytest.approx(117.0, rel=0.01)
    assert configuration.inverter_ac_capacity_kw == pytest.approx(100.0, rel=0.01)
    assert configuration.dc_ac_ratio == pytest.approx(1.17, rel=0.02)


def _write_clear_sky_weather_csv(path, horizon):
    """A physically consistent weather CSV for the horizon, from pvlib.

    Offline: irradiance comes from the clear-sky model, not a provider.
    """

    from pvlib.location import Location

    location = Location(37.77, -122.42, tz=horizon.timezone)
    sky = location.get_clearsky(pd.DatetimeIndex(horizon.index), model="ineichen")

    pd.DataFrame(
        {
            "timestamp": horizon.index,
            "ghi_w_per_m2": sky["ghi"].to_numpy(),
            "dni_w_per_m2": sky["dni"].to_numpy(),
            "dhi_w_per_m2": sky["dhi"].to_numpy(),
            "temperature_c": 20.0,
            "wind_speed_m_per_s": 2.0,
        }
    ).to_csv(path, index=False)

    return path


def test_generic_selection_routes_to_the_phase_one_weather_model(tmp_path):
    # The GUI asks three questions; this pins that the generic answer still
    # reaches the PVWatts-style model and not the equipment one.
    from src.simulation.application_interface import resolve_pv_profile_mode

    horizon = build_horizon("2026-06-21", 1, "America/Los_Angeles", 15)
    weather_path = _write_clear_sky_weather_csv(
        tmp_path / "weather.csv", horizon
    )

    profile = create_site_profile(
        horizon,
        load_kw=25,
        pv_capacity_kw=30,
        load_profile_mode="constant",
        load_archetype="office",
        load_variability_fraction=0.0,
        pv_profile_mode=resolve_pv_profile_mode("weather", "generic"),
        weather_csv_path=weather_path,
        pv_latitude=37.77,
        pv_longitude=-122.42,
        pv_tilt_degrees=20.0,
        pv_azimuth_degrees=180.0,
        pv_dc_ac_ratio=1.2,
    )

    provenance = profile.attrs["pv_provenance"]

    assert provenance["model_version"].startswith("phase1-")
    assert provenance["inverter_model"] == "pvwatts"
    assert profile["pv_kw"].max() > 0
    assert (profile["pv_kw"] >= 0).all()


def test_equipment_selection_routes_to_the_phase_two_weather_model(tmp_path):
    from src.simulation.application_interface import resolve_pv_profile_mode

    horizon = build_horizon("2026-06-21", 1, "America/Los_Angeles", 15)
    weather_path = _write_clear_sky_weather_csv(
        tmp_path / "weather.csv", horizon
    )

    profile = create_site_profile(
        horizon,
        load_kw=25,
        pv_capacity_kw=0.0,
        load_profile_mode="constant",
        load_archetype="office",
        load_variability_fraction=0.0,
        pv_profile_mode=resolve_pv_profile_mode("weather", "cec_equipment"),
        weather_csv_path=weather_path,
        pv_latitude=37.77,
        pv_longitude=-122.42,
        pv_tilt_degrees=20.0,
        pv_azimuth_degrees=180.0,
        pv_module_name="Canadian_Solar_Inc__CS6X_300M",
        pv_inverter_name="SMA_America__STP_50_US_41__480V_",
        pv_modules_per_string=15,
        pv_strings=13,
        pv_inverter_count=1,
        pv_mppt_input_count=2,
    )

    provenance = profile.attrs["pv_provenance"]

    assert provenance["model_version"].startswith("phase2-")
    assert provenance["inverter_model"] == "sandia"
    assert provenance["control_mode"] == "grid_following"
    assert profile["pv_kw"].max() > 0
    config = profile.attrs["pv_replay"]
    assert config.rated_ac_kw == pytest.approx(provenance["inverter_ac_capacity_kw"])
    assert config.available_power_kw.sum(axis=1).to_numpy() == pytest.approx(profile.pv_kw)
    assert profile.load_kw.to_numpy() == pytest.approx(
        25 + profile.attrs["pv_diagnostics"]["pv_inverter_night_tare_kw"].to_numpy()
    )
    from src.opendss.opendss_analysis import replay_dispatch_timeseries
    from src.dispatch.battery import Battery
    replay_input = profile.copy()
    replay_input["battery_net_injection_kw"] = 0.
    replay_input["battery_soc_kWh"] = 10.
    replay_input["grid_net_import_kw"] = profile.load_kw - profile.pv_kw
    result = replay_dispatch_timeseries(
        replay_input,
        battery=Battery(capacity_kWh=20., SOC_min=0.1, SOC_max=0.9,
                        energy_kWh=10., max_charge_kw=5., max_discharge_kw=5.),
        pv_capacity_kw=provenance["rated_dc_capacity_kw"], pv_replay=config,
    )
    assert result.pv_actual_kw.to_numpy() == pytest.approx(profile.pv_kw, abs=0.01)
    assert not result.setpoint_mismatch.any()


def test_the_weather_source_does_not_change_the_pv_model(tmp_path):
    # Upload and API retrieval both end at a weather CSV on disk, so the
    # system model is free to vary independently of where weather came from.
    from src.simulation.application_interface import resolve_pv_profile_mode

    horizon = build_horizon("2026-06-21", 1, "America/Los_Angeles", 15)
    uploaded = _write_clear_sky_weather_csv(tmp_path / "uploaded.csv", horizon)
    retrieved = _write_clear_sky_weather_csv(tmp_path / "retrieved.csv", horizon)

    profiles = [
        create_site_profile(
            horizon,
            load_kw=25,
            pv_capacity_kw=30,
            load_profile_mode="constant",
            load_archetype="office",
            load_variability_fraction=0.0,
            pv_profile_mode=resolve_pv_profile_mode("weather", "generic"),
            weather_csv_path=path,
            pv_latitude=37.77,
            pv_longitude=-122.42,
        )
        for path in (uploaded, retrieved)
    ]

    pd.testing.assert_series_equal(
        profiles[0]["pv_kw"], profiles[1]["pv_kw"]
    )


@pytest.mark.parametrize("mode", ["weather_generic", "weather_equipment"])
def test_gui_weather_selection_reaches_qsts_ac_ratings(tmp_path, monkeypatch, mode):
    horizon = build_horizon("2026-06-21", 1, "America/Los_Angeles", 15)
    weather = _write_clear_sky_weather_csv(tmp_path / "weather.csv", horizon)
    def offline_signals(config, horizon, *, site_profile, **kwargs):
        frame = site_profile.copy()
        frame["price_per_kWh"] = 0.2
        frame["gCO2/kWh"] = 300.
        return frame
    monkeypatch.setattr(interface_analysis, "load_signal_data", offline_signals)
    result = interface_analysis.run_live_api_analysis(
        MicrogridSpecification(
            battery=Battery(capacity_kWh=20, energy_kWh=10,
                            max_charge_kw=5, max_discharge_kw=5),
            pv_capacity_kw=30, load_kw=25,
        ),
        start_date="2026-06-21", number_of_days=1, timestep_minutes=15,
        region_id="caiso_np15", market_provider=None, market_location=None,
        carbon_provider=None, carbon_zone=None, timezone=None,
        price_mode="fixed_retail", fixed_retail_price=0.2, price_csv_path=None,
        selected_scenarios=("no_battery", "cost_optimal"), carbon_weights=(0.2,),
        degradation_cost_per_kWh=0.03,
        pv_profile_mode=mode, weather_csv_path=weather,
        pv_latitude=37.77, pv_longitude=-122.42, pv_dc_ac_ratio=1.2,
        pv_module_name="Canadian_Solar_Inc__CS6X_300M",
        pv_inverter_name="SMA_America__STP_50_US_41__480V_",
        pv_modules_per_string=15, pv_strings=13, pv_inverter_count=2,
        pv_mppt_input_count=2,
    )
    for replay in result.runs_by_carbon_weight[0.2].powerflow_scenarios.values():
        assert replay.pv_actual_kw.to_numpy() == pytest.approx(replay.pv_kw, abs=0.01)
        assert not replay.setpoint_mismatch.any()
        rating_columns = [c for c in replay if c.startswith("pv_") and c.endswith("_rated_ac_kw")]
        assert len(rating_columns) == (2 if mode == "weather_equipment" else 1)
        assert replay[rating_columns].iloc[0].sum() == pytest.approx(
            result.pv_provenance["inverter_ac_capacity_kw"]
        )
    assert any("representative balanced 480 V" in w for w in result.warnings)
