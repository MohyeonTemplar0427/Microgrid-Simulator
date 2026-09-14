"""Tests for the weather-derived PV model (Phase 1).

Everything here is offline and deterministic. Irradiance comes from pvlib's
clear-sky model rather than a provider, so no test touches the network or
needs a secret.
"""

import numpy as np
import pandas as pd
import pytest
from pvlib.location import Location

from src.profiles import (
    DEFAULT_DC_AC_RATIO,
    DIAGNOSTIC_COLUMNS,
    POWER_STAGE_COLUMNS,
    PV_MODEL_VERSION,
    PVSourceError,
    WeatherDerivedPV,
    WeatherDerivedPVConfiguration,
    WeatherError,
    prepare_weather_frame,
)
from src.profiles.pv_model import interval_midpoints
from src.profiles.weather import (
    DHI_W_PER_M2,
    DNI_W_PER_M2,
    GHI_W_PER_M2,
    TEMPERATURE_C,
    WIND_SPEED_M_PER_S,
)
from src.timeseries import build_interval_index
from src.timeseries.schema import MissingDataPolicy

PACIFIC = "America/Los_Angeles"
LATITUDE = 37.77
LONGITUDE = -122.42


def make_index(start="2026-06-21", end="2026-06-21", timezone=PACIFIC):
    return build_interval_index(start, end, timezone)


def clear_sky_weather(
    interval_index,
    *,
    temperature_c: float = 20.0,
    wind_speed_m_per_s: float = 2.0,
) -> pd.DataFrame:
    """Physically consistent GHI/DNI/DHI for the horizon, from pvlib."""

    location = Location(LATITUDE, LONGITUDE, tz=interval_index.timezone)
    sky = location.get_clearsky(interval_index.index, model="ineichen")

    return pd.DataFrame(
        {
            "timestamp": interval_index.index,
            GHI_W_PER_M2: sky["ghi"].to_numpy(),
            DNI_W_PER_M2: sky["dni"].to_numpy(),
            DHI_W_PER_M2: sky["dhi"].to_numpy(),
            TEMPERATURE_C: temperature_c,
            WIND_SPEED_M_PER_S: wind_speed_m_per_s,
        }
    )


def make_configuration(**overrides) -> WeatherDerivedPVConfiguration:
    settings = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "rated_pv_capacity_kw": 100.0,
    }
    settings.update(overrides)
    return WeatherDerivedPVConfiguration(**settings)


def build(configuration, interval_index, weather=None, **kwargs):
    source = WeatherDerivedPV(
        configuration=configuration,
        weather_data=weather if weather is not None
        else clear_sky_weather(interval_index),
        **kwargs,
    )
    return source.build_pv_available_kw(interval_index)


## Configuration ----------------------------------------------------------


def test_inverter_capacity_defaults_to_the_dc_ac_ratio():
    configuration = make_configuration(rated_pv_capacity_kw=120.0)

    assert configuration.resolved_inverter_ac_capacity_kw == pytest.approx(
        120.0 / DEFAULT_DC_AC_RATIO
    )
    assert configuration.resolved_dc_ac_ratio == pytest.approx(
        DEFAULT_DC_AC_RATIO
    )


def test_explicit_inverter_capacity_wins_over_the_default_ratio():
    configuration = make_configuration(
        rated_pv_capacity_kw=100.0,
        inverter_ac_capacity_kw=60.0,
    )

    assert configuration.resolved_inverter_ac_capacity_kw == pytest.approx(60.0)
    assert configuration.resolved_dc_ac_ratio == pytest.approx(100.0 / 60.0)


def test_supplying_both_inverter_capacity_and_ratio_is_rejected():
    # They describe the same quantity. Accepting both would mean silently
    # preferring one, which is the kind of hidden precedence that produces
    # numbers nobody can explain later.
    with pytest.raises(PVSourceError) as error:
        make_configuration(inverter_ac_capacity_kw=80.0, dc_ac_ratio=1.25)

    assert "not both" in str(error.value)


def test_configuration_rejects_contradictory_and_impossible_values():
    with pytest.raises(PVSourceError):
        make_configuration(latitude=95.0)

    with pytest.raises(PVSourceError):
        make_configuration(azimuth_degrees=400.0)

    with pytest.raises(PVSourceError):
        make_configuration(tilt_degrees=120.0)

    with pytest.raises(PVSourceError):
        make_configuration(dc_ac_ratio=0.0)

    with pytest.raises(PVSourceError):
        make_configuration(inverter_ac_capacity_kw=-1.0)

    with pytest.raises(PVSourceError):
        make_configuration(ground_albedo=1.5)

    with pytest.raises(PVSourceError):
        make_configuration(system_losses_fraction=1.0)


def test_a_positive_temperature_coefficient_is_rejected():
    # Module output falls as the cell warms; a positive coefficient is a sign
    # error that would make hot afternoons look better than they are.
    with pytest.raises(PVSourceError) as error:
        make_configuration(power_temperature_coefficient_per_c=0.004)

    assert "must not be positive" in str(error.value)


def test_configuration_records_the_model_version():
    assert make_configuration().model_version == PV_MODEL_VERSION


## Weather validation -----------------------------------------------------


def test_weather_must_be_timezone_aware():
    index = make_index()
    weather = clear_sky_weather(index)
    weather["timestamp"] = weather["timestamp"].dt.tz_localize(None)

    with pytest.raises(WeatherError) as error:
        prepare_weather_frame(weather)

    assert "timezone-naive" in str(error.value)


def test_weather_rejects_duplicate_timestamps():
    index = make_index()
    weather = clear_sky_weather(index)
    weather = pd.concat([weather, weather.iloc[[0]]], ignore_index=True)

    with pytest.raises(WeatherError) as error:
        prepare_weather_frame(weather)

    assert "duplicate" in str(error.value)


def test_weather_rejects_negative_irradiance():
    index = make_index()
    weather = clear_sky_weather(index)
    weather.loc[40, GHI_W_PER_M2] = -5.0

    with pytest.raises(WeatherError) as error:
        prepare_weather_frame(weather)

    assert "negative irradiance" in str(error.value)


def test_weather_catches_an_energy_accumulation_supplied_as_irradiance():
    index = make_index()
    weather = clear_sky_weather(index)
    weather[GHI_W_PER_M2] = weather[GHI_W_PER_M2] * 3600.0  # J/m^2, not W/m^2

    with pytest.raises(WeatherError) as error:
        prepare_weather_frame(weather)

    assert "plausibility ceiling" in str(error.value)


def test_weather_catches_irradiance_supplied_in_kw_per_m2():
    index = make_index()
    weather = clear_sky_weather(index)
    for column in (GHI_W_PER_M2, DNI_W_PER_M2, DHI_W_PER_M2):
        weather[column] = weather[column] / 1000.0

    with pytest.raises(WeatherError) as error:
        prepare_weather_frame(weather)

    assert "kW/m^2" in str(error.value)


def test_weather_catches_kelvin_and_fahrenheit_temperatures():
    index = make_index()

    kelvin = clear_sky_weather(index)
    kelvin[TEMPERATURE_C] = kelvin[TEMPERATURE_C] + 273.15
    with pytest.raises(WeatherError) as error:
        prepare_weather_frame(kelvin)
    assert "kelvin or Fahrenheit" in str(error.value)

    fahrenheit = clear_sky_weather(index, temperature_c=95.0)
    with pytest.raises(WeatherError):
        prepare_weather_frame(fahrenheit)


def test_an_all_dark_horizon_is_accepted_deliberately():
    # Zero irradiance is legitimate; only a *small nonzero* peak suggests
    # the wrong unit.
    index = make_index()
    weather = clear_sky_weather(index)
    for column in (GHI_W_PER_M2, DNI_W_PER_M2, DHI_W_PER_M2):
        weather[column] = 0.0

    prepared = prepare_weather_frame(weather)

    assert float(prepared[GHI_W_PER_M2].max()) == 0.0


def test_missing_weather_intervals_are_rejected_by_default():
    index = make_index()
    weather = clear_sky_weather(index).drop(index=[10, 11, 12])

    with pytest.raises(Exception) as error:
        build(make_configuration(), index, weather=weather)

    assert "missing" in str(error.value).lower()


def test_missing_weather_intervals_are_counted_when_a_policy_is_given():
    index = make_index()
    weather = clear_sky_weather(index).drop(index=[10, 11, 12])

    source = WeatherDerivedPV(
        configuration=make_configuration(),
        weather_data=weather,
        missing_data_policy=MissingDataPolicy.INTERPOLATE,
    )
    values = source.build_pv_available_kw(index)

    assert len(values) == index.interval_count
    assert source.filled_interval_count == 3


## Model behaviour --------------------------------------------------------


def test_output_is_one_nonnegative_value_per_interval():
    index = make_index()
    values = build(make_configuration(), index)

    assert values.name == "pv_available_kw"
    assert len(values) == index.interval_count
    assert bool((values >= 0).all())


def test_night_produces_no_power():
    index = make_index()
    values = build(make_configuration(), index).to_numpy()
    hours = index.index.hour.to_numpy()

    assert values[hours == 0].max() == pytest.approx(0.0)
    assert values[hours == 23].max() == pytest.approx(0.0)
    assert values[(hours >= 11) & (hours <= 13)].max() > 0.0


def test_summer_produces_more_energy_than_winter():
    # The whole point of a weather-derived model: the previous synthetic
    # curve produced identical output on both solstices.
    summer = make_index("2026-06-21", "2026-06-21")
    winter = make_index("2026-12-21", "2026-12-21")

    summer_kWh = build(make_configuration(), summer).sum() * summer.timestep_hours
    winter_kWh = build(make_configuration(), winter).sum() * winter.timestep_hours

    assert winter_kWh < summer_kWh
    # A defensible mid-latitude ratio, not a knife-edge assertion.
    assert 0.2 < winter_kWh / summer_kWh < 0.8


def test_a_south_facing_array_beats_north_in_the_northern_hemisphere():
    index = make_index()

    south = build(make_configuration(azimuth_degrees=180.0), index).sum()
    north = build(make_configuration(azimuth_degrees=0.0), index).sum()

    assert south > north


def test_hotter_air_reduces_output_through_the_temperature_coefficient():
    index = make_index()
    configuration = make_configuration()

    cool = build(
        configuration, index, weather=clear_sky_weather(index, temperature_c=10.0)
    ).sum()
    hot = build(
        configuration, index, weather=clear_sky_weather(index, temperature_c=40.0)
    ).sum()

    assert hot < cool


def test_output_is_clipped_at_the_inverter_ac_rating():
    index = make_index()
    configuration = make_configuration(
        rated_pv_capacity_kw=100.0,
        inverter_ac_capacity_kw=30.0,
    )

    values = build(configuration, index)

    assert values.max() == pytest.approx(30.0)
    assert bool((values <= 30.0 + 1e-9).all())
    # A 100 kW array behind a 30 kW inverter must actually be clipping.
    assert int((values >= 29.999).sum()) > 0


def test_system_losses_scale_output_and_are_applied_once():
    index = make_index()
    # Use a large inverter so clipping cannot mask the loss scaling.
    lossless = build(
        make_configuration(
            system_losses_fraction=0.0, inverter_ac_capacity_kw=200.0
        ),
        index,
    )
    lossy = build(
        make_configuration(
            system_losses_fraction=0.20, inverter_ac_capacity_kw=200.0
        ),
        index,
    )

    daylight = lossless > 0
    ratio = (lossy[daylight] / lossless[daylight]).to_numpy()

    # Applied once and only to DC, so the AC ratio is close to (1 - f). It is
    # not exactly (1 - f) because the inverter's efficiency curve is not flat.
    assert np.all(ratio < 1.0)
    assert 0.78 < float(np.median(ratio)) < 0.82


def test_a_zero_capacity_array_produces_no_power():
    index = make_index()
    values = build(make_configuration(rated_pv_capacity_kw=0.0), index)

    assert float(values.abs().max()) == pytest.approx(0.0)


## Interval and timezone handling -----------------------------------------


def test_solar_position_uses_interval_midpoints():
    index = make_index()
    midpoints = interval_midpoints(index)

    assert len(midpoints) == index.interval_count
    assert midpoints[0] - index.index[0] == pd.Timedelta(
        minutes=index.timestep_minutes / 2
    )


def test_daylight_saving_days_keep_their_real_interval_counts():
    # 92 and 100, never days * 96.
    spring = make_index("2026-03-08", "2026-03-08")
    autumn = make_index("2026-11-01", "2026-11-01")

    assert spring.interval_count == 92
    assert autumn.interval_count == 100

    assert len(build(make_configuration(), spring)) == 92
    assert len(build(make_configuration(), autumn)) == 100


def test_peak_output_follows_the_local_clock_across_a_dst_transition():
    # Solar noon does not move, but the local clock does, so the peak shifts
    # by an hour in local time on the spring-forward day.
    before = make_index("2026-03-07", "2026-03-07")
    after = make_index("2026-03-09", "2026-03-09")

    def peak_hour(interval_index):
        values = build(make_configuration(), interval_index).to_numpy()
        return interval_index.index[int(np.argmax(values))].hour

    assert peak_hour(before) == 12
    assert peak_hour(after) == 13


def test_weather_may_cover_a_longer_horizon_than_the_analysis():
    wide = make_index("2026-06-20", "2026-06-22")
    narrow = make_index("2026-06-21", "2026-06-21")

    values = build(make_configuration(), narrow, weather=clear_sky_weather(wide))

    assert len(values) == narrow.interval_count


def test_weather_in_another_timezone_is_converted_not_rejected():
    index = make_index()
    weather = clear_sky_weather(index)
    weather["timestamp"] = weather["timestamp"].dt.tz_convert("UTC")

    values = build(make_configuration(), index, weather=weather)

    assert len(values) == index.interval_count
    assert values.sum() > 0.0


## Provenance -------------------------------------------------------------


def test_describe_reports_the_resolved_inverter_and_model_version():
    text = WeatherDerivedPV(
        configuration=make_configuration(),
        weather_data=clear_sky_weather(make_index()),
    ).describe()

    assert "kW DC" in text
    assert "kW AC" in text
    assert PV_MODEL_VERSION in text


## Power-stage diagnostics -------------------------------------------------


def build_detailed(configuration, interval_index, weather=None, **kwargs):
    source = WeatherDerivedPV(
        configuration=configuration,
        weather_data=weather if weather is not None
        else clear_sky_weather(interval_index),
        **kwargs,
    )
    return source.build_detailed(interval_index)


def clipping_configuration(**overrides):
    """A 100 kW array behind a 30 kW inverter, so clipping is guaranteed."""

    settings = {"rated_pv_capacity_kw": 100.0, "inverter_ac_capacity_kw": 30.0}
    settings.update(overrides)
    return make_configuration(**settings)


def test_diagnostics_carry_exactly_the_required_columns():
    result = build_detailed(make_configuration(), make_index())

    for column in POWER_STAGE_COLUMNS:
        assert column in result.diagnostics.columns

    assert tuple(result.diagnostics.columns) == DIAGNOSTIC_COLUMNS


def test_diagnostics_preserve_the_weather_diagnostics():
    result = build_detailed(make_configuration(), make_index())

    for column in (
        "solar_zenith_degrees",
        "solar_azimuth_degrees",
        "plane_of_array_irradiance_w_per_m2",
        "estimated_cell_temperature_c",
    ):
        assert column in result.diagnostics.columns


def test_diagnostic_timestamps_match_the_interval_index_exactly():
    index = make_index("2026-06-20", "2026-06-22")
    result = build_detailed(make_configuration(), index)

    timestamps = pd.DatetimeIndex(result.diagnostics["timestamp"])

    assert len(result.diagnostics) == index.interval_count
    assert timestamps.equals(index.index)
    assert str(timestamps.tz) == str(index.index.tz)


def test_diagnostics_keep_real_interval_counts_on_dst_days():
    for day, expected in (("2026-03-08", 92), ("2026-11-01", 100)):
        index = make_index(day, day)
        result = build_detailed(make_configuration(), index)

        assert index.interval_count == expected
        assert len(result.diagnostics) == expected
        assert pd.DatetimeIndex(
            result.diagnostics["timestamp"]
        ).equals(index.index)


def test_available_series_matches_the_diagnostic_column():
    result = build_detailed(clipping_configuration(), make_index())

    assert np.allclose(
        result.pv_available_kw.to_numpy(),
        result.diagnostics["pv_available_kw"].to_numpy(),
    )


def test_clipping_identity_holds():
    configuration = clipping_configuration()
    result = build_detailed(configuration, make_index())
    diagnostics = result.diagnostics

    rating = configuration.resolved_inverter_ac_capacity_kw
    expected = np.maximum(
        diagnostics["pv_ac_before_clipping_kw"].to_numpy() - rating, 0.0
    )

    assert np.allclose(
        diagnostics["pv_inverter_clipping_kw"].to_numpy(), expected, atol=1e-12
    )


def test_available_identity_holds_both_ways():
    configuration = clipping_configuration()
    result = build_detailed(configuration, make_index())
    diagnostics = result.diagnostics

    rating = configuration.resolved_inverter_ac_capacity_kw
    before = diagnostics["pv_ac_before_clipping_kw"].to_numpy()
    clipping = diagnostics["pv_inverter_clipping_kw"].to_numpy()
    available = diagnostics["pv_available_kw"].to_numpy()

    assert np.allclose(available, before - clipping, atol=1e-12)
    assert np.allclose(available, np.minimum(before, rating), atol=1e-12)


def test_every_power_stage_is_nonnegative():
    for configuration in (make_configuration(), clipping_configuration()):
        diagnostics = build_detailed(configuration, make_index()).diagnostics

        for column in POWER_STAGE_COLUMNS:
            if column == "timestamp":
                continue
            assert bool(
                (diagnostics[column] >= 0).all()
            ), f"{column} went negative"


def test_stages_are_monotonically_nonincreasing_through_the_chain():
    # Each stage can only take power away, never add it.
    diagnostics = build_detailed(
        clipping_configuration(), make_index()
    ).diagnostics

    assert bool(
        (
            diagnostics["pv_dc_after_system_losses_kw"]
            <= diagnostics["pv_module_dc_power_kw"] + 1e-12
        ).all()
    )
    assert bool(
        (
            diagnostics["pv_available_kw"]
            <= diagnostics["pv_ac_before_clipping_kw"] + 1e-12
        ).all()
    )


def test_all_stages_are_zero_at_night():
    index = make_index()
    diagnostics = build_detailed(make_configuration(), index).diagnostics
    hours = index.index.hour.to_numpy()
    night = (hours <= 3) | (hours >= 22)

    for column in POWER_STAGE_COLUMNS:
        if column == "timestamp":
            continue
        assert float(
            diagnostics.loc[night, column].abs().max()
        ) == pytest.approx(0.0)


def test_clipping_occurs_only_above_the_inverter_rating():
    configuration = clipping_configuration()
    diagnostics = build_detailed(configuration, make_index()).diagnostics

    rating = configuration.resolved_inverter_ac_capacity_kw
    before = diagnostics["pv_ac_before_clipping_kw"].to_numpy()
    clipping = diagnostics["pv_inverter_clipping_kw"].to_numpy()

    # Below the rating there is no clipping at all.
    assert float(clipping[before <= rating].max()) == pytest.approx(0.0)
    # Above it, there is.
    assert float(clipping[before > rating].min()) > 0.0


def test_an_oversized_inverter_never_clips():
    configuration = make_configuration(
        rated_pv_capacity_kw=100.0, inverter_ac_capacity_kw=500.0
    )
    diagnostics = build_detailed(configuration, make_index()).diagnostics

    assert float(
        diagnostics["pv_inverter_clipping_kw"].max()
    ) == pytest.approx(0.0)
    assert np.allclose(
        diagnostics["pv_available_kw"].to_numpy(),
        diagnostics["pv_ac_before_clipping_kw"].to_numpy(),
    )


def test_clipped_result_reproduces_pvlib_exactly():
    # The "before clipping" stage needs pvlib's efficiency curve reimplemented
    # without its clip. This asserts the two cannot drift apart: clipping our
    # unclipped result must reproduce pvlib's own output bit for bit.
    from pvlib import inverter as pvlib_inverter

    from src.profiles.pv_model import ac_before_clipping_kw

    efficiency = 0.96
    rating = 30.0
    dc = pd.Series(np.linspace(0.0, 80.0, 2000))

    ours = ac_before_clipping_kw(
        dc,
        inverter_ac_capacity_kw=rating,
        nominal_inverter_efficiency=efficiency,
    ).to_numpy()
    theirs = np.asarray(
        pvlib_inverter.pvwatts(
            dc.to_numpy(), pdc0=rating / efficiency, eta_inv_nom=efficiency
        )
    )

    assert np.allclose(np.minimum(ours, rating), theirs, atol=1e-12)


def test_system_losses_apply_to_dc_only_and_not_to_the_inverter_stage():
    # pv_dc_after_system_losses_kw must be exactly (1 - f) x module DC. If the
    # inverter efficiency leaked into the loss fraction, this ratio would not
    # be the configured one.
    fraction = 0.20
    configuration = make_configuration(
        system_losses_fraction=fraction, inverter_ac_capacity_kw=500.0
    )
    diagnostics = build_detailed(configuration, make_index()).diagnostics

    module = diagnostics["pv_module_dc_power_kw"].to_numpy()
    after = diagnostics["pv_dc_after_system_losses_kw"].to_numpy()
    daylight = module > 0

    assert np.allclose(
        after[daylight], module[daylight] * (1.0 - fraction), atol=1e-12
    )


def test_inverter_efficiency_is_applied_once_not_twice():
    # AC before clipping divided by DC after losses is the inverter's own
    # part-load efficiency, which near rated load sits close to the nominal
    # value. If efficiency were also inside the system losses, this ratio
    # would fall well below it.
    efficiency = 0.96
    configuration = make_configuration(
        nominal_inverter_efficiency=efficiency,
        system_losses_fraction=0.0,
        inverter_ac_capacity_kw=500.0,
    )
    diagnostics = build_detailed(configuration, make_index()).diagnostics

    dc = diagnostics["pv_dc_after_system_losses_kw"].to_numpy()
    ac = diagnostics["pv_ac_before_clipping_kw"].to_numpy()
    strong = dc > 0.5 * dc.max()

    ratio = ac[strong] / dc[strong]

    assert np.all(ratio < 1.0)
    assert float(np.median(ratio)) > efficiency - 0.02


def test_build_pv_available_kw_still_returns_only_the_series():
    # The existing PVProfileSource contract is unchanged.
    index = make_index()
    source = WeatherDerivedPV(
        configuration=make_configuration(),
        weather_data=clear_sky_weather(index),
    )
    values = source.build_pv_available_kw(index)

    assert isinstance(values, pd.Series)
    assert values.name == "pv_available_kw"
    assert len(values) == index.interval_count


def test_the_simple_path_still_records_the_detailed_result():
    index = make_index()
    source = WeatherDerivedPV(
        configuration=clipping_configuration(),
        weather_data=clear_sky_weather(index),
    )

    assert source.last_result is None

    values = source.build_pv_available_kw(index)

    assert source.last_result is not None
    assert np.allclose(
        source.last_result.pv_available_kw.to_numpy(), values.to_numpy()
    )
    assert tuple(source.last_result.diagnostics.columns) == DIAGNOSTIC_COLUMNS


def test_the_supplied_weather_frame_is_never_modified():
    index = make_index()
    weather = clear_sky_weather(index)
    before = weather.copy(deep=True)

    build_detailed(clipping_configuration(), index, weather=weather)

    pd.testing.assert_frame_equal(weather, before)


def test_provenance_records_how_the_profile_was_made():
    configuration = clipping_configuration()
    result = build_detailed(configuration, make_index())

    assert result.provenance["model_version"] == PV_MODEL_VERSION
    assert result.provenance["inverter_model"] == "pvwatts"
    assert result.provenance["inverter_ac_capacity_kw"] == pytest.approx(30.0)
    assert result.provenance["timezone"] == PACIFIC
    assert result.provenance["interval_count"] == 96


def test_heavy_clipping_is_reported_as_a_warning():
    result = build_detailed(clipping_configuration(), make_index())

    assert any("clipping" in warning for warning in result.warnings)


def test_a_well_matched_inverter_raises_no_clipping_warning():
    result = build_detailed(
        make_configuration(
            rated_pv_capacity_kw=100.0, inverter_ac_capacity_kw=500.0
        ),
        make_index(),
    )

    assert not any("clipping" in warning for warning in result.warnings)


def test_filled_weather_intervals_are_reported_as_a_warning():
    index = make_index()
    weather = clear_sky_weather(index).drop(index=[40, 41])

    result = build_detailed(
        make_configuration(),
        index,
        weather=weather,
        missing_data_policy=MissingDataPolicy.INTERPOLATE,
    )

    assert any("filled" in warning for warning in result.warnings)
