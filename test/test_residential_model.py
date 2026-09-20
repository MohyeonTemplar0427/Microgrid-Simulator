"""Offline physical invariants and backend workflow tests. All inputs are fixtures."""
from dataclasses import replace
import json

import numpy as np
import pandas as pd
import pytest

from src.profiles.residential import (
    ResidentialError, Provenance, ResidentialProfile, EnergyBenchmark, ResidentialLoad,
    aggregate_population, calibrate, compare_profiles, read_resstock_csv,
    read_noaa_global_hourly, TemperatureWeather, WeatherResponseModel,
)
from src.profiles.residential.adapters import coarsen_profile
from src.profiles.residential.__main__ import run_study
from src.timeseries.interval_table import build_interval_index


PROVENANCE = Provenance("test-inland", "fixture-not-resstock", "fixture-2020", "test fixture", "America/Los_Angeles")


def population_fixture():
    index = pd.date_range("2020-01-01", periods=24*28, freq="h", tz="UTC")
    hour = index.tz_convert(PROVENANCE.timezone).hour.to_numpy()
    day = np.arange(len(index)) // 24
    temperature = 22 + 10 * np.sin(day * .7) + 2 * np.sin(hour * np.pi / 12)
    weather = TemperatureWeather(pd.DataFrame({"temperature_c": temperature}, index=index),
                                 60, PROVENANCE.region, PROVENANCE.weather_id, "fixture")
    frame = pd.DataFrame({"cooling": .15 * np.maximum(temperature-22, 0),
                          "heating": .2 * np.maximum(18-temperature, 0),
                          "appliances": .3 + .1*(hour >= 18)}, index=index)
    return ResidentialProfile(frame, 60, PROVENANCE), weather


RESPONSES = {"cooling": "cooling", "heating": "heating", "appliances": "schedule"}


def test_rounded_components_preserve_authoritative_energy(tmp_path):
    path = tmp_path / "rounded.csv"
    pd.DataFrame({"timestamp": ["2020-01-01T00:00Z", "2020-01-01T00:15Z"],
                  "a": [.25001, .25], "b": [.25, .25], "total": [.5, .6]}).to_csv(path, index=False)
    args = dict(provenance=PROVENANCE, end_use_columns={"a": "a", "b": "b"},
                timestep_minutes=15, unit="kWh", timestamp_convention="start", total_column="total")
    with pytest.raises(ResidentialError, match="exceed"):
        read_resstock_csv(path, **args)
    result = read_resstock_csv(path, **args, rounding_tolerance_kw=.00005)
    assert result.energy_kwh().sum() == pytest.approx(1.1)
    assert result.diagnostics["rounding_adjustment_kwh"] == pytest.approx(.00001)
    assert result.energy_kwh()["unallocated"] == pytest.approx(.1)
    assert (result.end_uses_kw >= 0).all().all()


@pytest.mark.parametrize("start,end", [("2020-01-01T00:00Z", "2020-01-01T03:00Z"),
                                      ("2019-12-31T23:00Z", "2020-01-01T02:00Z")])
def test_noaa_window_rejects_missing_boundary_hours(tmp_path, start, end):
    path = tmp_path / "weather.csv"
    pd.DataFrame({"STATION": ["001", "001"], "DATE": ["2020-01-01T00:00", "2020-01-01T01:00"],
                  "TMP": ["+0200,1", "+0300,1"]}).to_csv(path, index=False)
    with pytest.raises(ResidentialError, match="finite"):
        read_noaa_global_hourly(path, station="001", region="test", weather_id="2020", start=start, end=end)


def test_noaa_complete_window_excludes_bad_observations_outside(tmp_path):
    path = tmp_path / "weather.csv"
    pd.DataFrame({"STATION": ["001"]*3, "DATE": ["2020-01-01T00:00", "2020-01-01T01:00", "2020-01-01T02:00"],
                  "TMP": ["+9999,9", "+0200,1", "+0300,5"]}).to_csv(path, index=False)
    result = read_noaa_global_hourly(path, station="001", region="test", weather_id="2020",
                                   start="2020-01-01T01:00Z", end="2020-01-01T03:00Z")
    assert result.frame.temperature_c.tolist() == [20, 30]


def test_study_sampling_preserves_stock_and_is_independent_of_energy():
    from tools.run_fresno_residential_study import select_population, TOTAL
    stock = pd.DataFrame({"bldg_id": range(40), "weight": [3.]*40,
                          "in.geometry_building_type_recs": ["A"]*30+["B"]*10,
                          "in.hvac_cooling_type": ["Central AC"]*40, TOTAL: np.arange(40)*100})
    selected, strata = select_population(stock, size=10)
    altered, _ = select_population(stock.assign(**{TOTAL: 999}), size=10)
    assert selected.bldg_id.tolist() == altered.bldg_id.tolist()
    assert selected.study_weight.sum() == pytest.approx(stock.weight.sum())
    for entry in strata:
        assert selected.loc[selected.stratum == entry["stratum"], "study_weight"].sum() == pytest.approx(entry["represented_dwellings"])


def test_import_interval_end_energy_and_closure(tmp_path):
    path = tmp_path / "dwelling.csv"
    pd.DataFrame({"timestamp": ["2020-01-01 00:15", "2020-01-01 00:30"],
                  "ac": [.25, .5], "total": [.5, .75]}).to_csv(path, index=False)
    profile = read_resstock_csv(path, provenance=PROVENANCE, end_use_columns={"cooling": "ac"},
        timestep_minutes=15, unit="kWh", timestamp_convention="end", source_timezone="Etc/GMT+8", total_column="total")
    assert profile.end_uses_kw.index[0] == pd.Timestamp("2020-01-01 08:00Z")
    assert profile.energy_kwh().to_dict() == {"cooling": .75, "unallocated": .5}
    assert profile.native_load_kw.tolist() == [2, 3]
    assert len(profile.diagnostics["input_sha256"]) == 64


@pytest.mark.parametrize("problem", ["overlap", "negative_residual", "naive", "unit"])
def test_import_rejects_ambiguous_or_double_counted_inputs(tmp_path, problem):
    path = tmp_path / "input.csv"
    pd.DataFrame({"timestamp": ["2020-01-01 00:00", "2020-01-01 01:00"],
                  "ac": [1, 2], "total": [2, 3]}).to_csv(path, index=False)
    options = dict(provenance=PROVENANCE, end_use_columns={"cooling": "ac"},
                   timestep_minutes=60, unit="kW", timestamp_convention="start", source_timezone="UTC")
    if problem == "overlap":
        options["end_use_columns"] = {"cooling": "ac", "again": "ac"}
    elif problem == "negative_residual":
        options.update(end_use_columns={"cooling": "total"}, total_column="ac")
    elif problem == "naive":
        options["source_timezone"] = None
    else:
        options["unit"] = "W"
    with pytest.raises(ResidentialError):
        read_resstock_csv(path, **options)


def test_explicit_offsets_preserve_repeated_dst_hour(tmp_path):
    path = tmp_path / "input.csv"
    pd.DataFrame({"timestamp": ["2020-11-01T01:00:00-07:00", "2020-11-01T01:00:00-08:00"],
                  "base": [1, 2]}).to_csv(path, index=False)
    p = read_resstock_csv(path, provenance=PROVENANCE, end_use_columns={"base": "base"},
        timestep_minutes=60, unit="kW", timestamp_convention="start")
    assert p.energy_kwh()["base"] == 3
    assert not p.end_uses_kw.index.has_duplicates


def test_incomplete_coarse_interval_is_not_silently_averaged():
    index = pd.date_range("2020-01-01T00:15Z", periods=4, freq="15min")
    p = ResidentialProfile(pd.DataFrame({"base": 1}, index=index), 15, PROVENANCE)
    with pytest.raises(ResidentialError, match="complete"):
        coarsen_profile(p, 60)


@pytest.mark.parametrize("values", [[1, np.nan], [1, np.inf], [1, -1]])
def test_invalid_end_use_values(values):
    index = pd.date_range("2020-01-01", periods=2, freq="h", tz="UTC")
    with pytest.raises(ResidentialError):
        ResidentialProfile(pd.DataFrame({"cooling": values}, index=index), 60, PROVENANCE)


@pytest.mark.parametrize("problem", ["gap", "duplicate", "naive"])
def test_invalid_time_grids(problem):
    profile, _ = population_fixture()
    frame = profile.end_uses_kw
    if problem == "gap":
        frame = frame.drop(frame.index[4])
    elif problem == "duplicate":
        frame = pd.concat([frame.iloc[:1], frame])
    else:
        frame = frame.tz_localize(None)
    with pytest.raises(ResidentialError):
        replace(profile, end_uses_kw=frame)


def test_population_weights_and_zero_weights():
    p, _ = population_fixture()
    q = replace(p, end_uses_kw=p.end_uses_kw*2)
    result = aggregate_population([p, q], [3, 1], households=100)
    np.testing.assert_allclose(result.native_load_kw, p.native_load_kw*125)
    assert result.households == 100
    with pytest.raises(ResidentialError):
        aggregate_population([p], [0])


@pytest.mark.parametrize("change", [{"region": "elsewhere"}, {"weather_id": "2024"}, {"weather_kind": "typical"}])
def test_population_rejects_mismatched_weather_and_geography(change):
    p, _ = population_fixture()
    q = replace(p, provenance=replace(p.provenance, **change))
    with pytest.raises(ResidentialError):
        aggregate_population([p, q], [1, 1])


def test_calibration_preserves_other_components_and_shape():
    p, _ = population_fixture()
    target = EnergyBenchmark(PROVENANCE.region, p.end_uses_kw.index[0].isoformat(), p.end.isoformat(),
                             "cooling", float(p.energy_kwh().cooling*2), "fixture benchmark")
    result = calibrate(p, [target])
    np.testing.assert_allclose(result.end_uses_kw.cooling, p.end_uses_kw.cooling*2)
    pd.testing.assert_series_equal(result.end_uses_kw.appliances, p.end_uses_kw.appliances)
    assert "calibration" not in p.diagnostics
    for invalid in [replace(target, end="2020-12-31T00:00Z"), replace(target, basis="grid_sales"),
                    replace(target, kwh_per_household=float("nan")), replace(target, region="wrong")]:
        with pytest.raises(ResidentialError):
            calibrate(p, [invalid])


def test_cannot_calibrate_missing_equipment_into_existence():
    p, _ = population_fixture()
    p.end_uses_kw["cooling"] = 0
    target = EnergyBenchmark(PROVENANCE.region, p.end_uses_kw.index[0].isoformat(), p.end.isoformat(),
                             "cooling", 100, "fixture")
    with pytest.raises(ResidentialError, match="absent"):
        calibrate(p, [target])


def test_surrogate_recovers_known_response_and_held_out_energy():
    p, w = population_fixture()
    split = 24*14
    training = replace(p, end_uses_kw=p.end_uses_kw.iloc[:split])
    train_weather = replace(w, frame=w.frame.iloc[:split])
    model = WeatherResponseModel.fit(training, train_weather, response_by_end_use=RESPONSES)
    assert model.coefficients["cooling"]["slope_kw_per_c"] == pytest.approx(.15, abs=1e-7)
    assert model.coefficients["heating"]["slope_kw_per_c"] == pytest.approx(.2, abs=1e-7)
    result = model.predict(replace(w, frame=w.frame.iloc[split:]), allow_extrapolation=True)
    metrics = compare_profiles(result, p.native_load_kw.iloc[split:])
    assert metrics["rmse_kw"] < 1e-7
    assert abs(metrics["energy_bias_kwh"]) < 1e-6


def test_hot_weather_changes_cooling_not_appliance_stock():
    p, w = population_fixture()
    model = WeatherResponseModel.fit(p, w, response_by_end_use=RESPONSES)
    baseline = model.predict(w)
    hot = replace(w, frame=w.frame + 8, weather_id="hot scenario")
    with pytest.raises(ResidentialError, match="outside training"):
        model.predict(hot)
    result = model.predict(hot, allow_extrapolation=True)
    assert result.energy_kwh().cooling > baseline.energy_kwh().cooling
    assert result.energy_kwh().heating < baseline.energy_kwh().heating
    np.testing.assert_allclose(result.end_uses_kw.appliances, baseline.end_uses_kw.appliances)
    assert result.diagnostics["extrapolated_intervals"] > 0
    assert result.provenance.weather_id == "hot scenario"


def test_weather_fit_rejects_wrong_year_or_unidentifiable_temperature():
    p, w = population_fixture()
    with pytest.raises(ResidentialError, match="match"):
        WeatherResponseModel.fit(p, replace(w, weather_id="wrong"), response_by_end_use=RESPONSES)
    with pytest.raises(ResidentialError, match="unidentifiable"):
        WeatherResponseModel.fit(p, replace(w, frame=w.frame*0+25), response_by_end_use=RESPONSES)
    with pytest.raises(ResidentialError, match="Classify"):
        WeatherResponseModel.fit(p, w, response_by_end_use={"cooling": "cooling"})


def test_noaa_decodes_quality_station_and_rejects_missing_hour(tmp_path):
    path = tmp_path / "noaa.csv"
    raw = pd.DataFrame({"STATION": ["001", "001", "001", "002"],
        "DATE": ["2020-01-01T00:00:00", "2020-01-01T00:30:00", "2020-01-01T01:00:00", "2020-01-01T00:00:00"],
        "TMP": ["+0200,1", "+0300,5", "+0100,1", "+0500,1"]})
    raw.to_csv(path, index=False)
    weather = read_noaa_global_hourly(path, station="001", region="test", weather_id="2020")
    assert weather.frame.temperature_c.tolist() == [25, 10]
    raw.loc[2, "TMP"] = "+9999,9"
    raw.to_csv(path, index=False)
    with pytest.raises(ResidentialError, match="finite"):
        read_noaa_global_hourly(path, station="001", region="test", weather_id="2020")


@pytest.mark.parametrize("day,expected", [("2020-03-08", 23), ("2020-11-01", 25)])
def test_dst_energy_and_existing_load_adapter(day, expected):
    grid = build_interval_index(day, day, PROVENANCE.timezone, 15)
    p = ResidentialProfile(pd.DataFrame({"base": np.ones(grid.interval_count)}, index=grid.index), 15, PROVENANCE)
    hourly = coarsen_profile(p, 60)
    assert len(hourly.end_uses_kw) == expected
    assert hourly.energy_kwh()["base"] == p.energy_kwh()["base"] == expected
    result = ResidentialLoad(p).build_load_kw(grid)
    assert len(result) == grid.interval_count
    assert result.name == "native_load_kw"
    with pytest.raises(ResidentialError, match="resolution"):
        ResidentialLoad(hourly).build_load_kw(grid)


@pytest.mark.parametrize("mode", ["published", "weather_response"])
def test_cli_workflows_export_provenance_without_touching_browser(tmp_path, mode):
    from dataclasses import asdict
    p, w = population_fixture()
    p.frame().to_csv(tmp_path / "dwelling.csv", index=False)
    pd.DataFrame({"STATION": "001", "DATE": w.frame.index.strftime("%Y-%m-%dT%H:%M:%S"),
                  "TMP": [f"{int(round(t*10)):+05d},1" for t in w.frame.temperature_c]}).to_csv(tmp_path / "weather.csv", index=False)
    config = dict(schema_version=1, mode=mode, provenance=asdict(PROVENANCE), households=10,
        profiles=[dict(path="dwelling.csv", weight=1, timestep_minutes=60, unit="kW", timestamp_convention="start",
                       end_use_columns={c: c for c in p.end_uses_kw})])
    if mode == "weather_response":
        spec = dict(path="weather.csv", station="001", weather_id=PROVENANCE.weather_id)
        config.update(training_weather=spec, prediction_weather=spec, response_by_end_use=RESPONSES)
    (tmp_path / "study.json").write_text(json.dumps(config))
    run_study(tmp_path / "study.json", tmp_path / "output")
    manifest = json.loads((tmp_path / "output/manifest.json").read_text())
    data = pd.read_csv(tmp_path / "output/residential_load.csv")
    assert manifest["households"] == 10
    assert manifest["is_synthetic"] is True
    assert manifest["basis"] == "gross_electricity"
    assert data.native_load_kw.sum() == pytest.approx(p.native_load_kw.sum()*10, rel=.01)
    assert manifest["provenance"]["region"] == PROVENANCE.region


def test_cli_rejects_weather_settings_in_published_mode_before_writing(tmp_path):
    config = dict(schema_version=1, mode="published", allow_extrapolation=True)
    (tmp_path / "study.json").write_text(json.dumps(config))
    with pytest.raises(ResidentialError, match="Published mode"):
        run_study(tmp_path / "study.json", tmp_path / "output")
    assert not (tmp_path / "output").exists()
