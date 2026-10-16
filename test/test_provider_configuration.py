"""Source routing is identical across workflows, without live services."""
from dataclasses import replace
import socket

import pandas as pd
import pytest

from src.dispatch.config import ExperimentConfig
from src.signal_pipeline import gridstatus_data
from src.signal_pipeline.horizon import build_horizon
from src.signal_pipeline.market_data_integration import resolve_region_config as experiment_region
from src.signal_pipeline.price_sources import FixedRetailPrice
from src.signal_pipeline.providers import GridStatusIOProvider, PJMProvider
from src.signal_pipeline.providers.base import (
    EmptyResponseError, MissingCredentialsError, MissingIntervalError,
    RangeLimitError, SignalProviderError, TimezoneNormalizationError,
)
from src.signal_pipeline.region_config import get_region_config, supported_regions
from src.signal_pipeline.signal_loader import _build_cache_key, load_signal_data
from src.signal_pipeline.source_config import (
    SourceConfigurationError, resolve_live_api_config, resolve_region_config,
    resolve_signal_config,
)


HOSTED = "pjm_western_hub_gridstatus"
EASTERN = "America/New_York"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("Configuration tests must not read credentials or contact services.")
    monkeypatch.setattr(socket.socket, "connect", unexpected)
    monkeypatch.setattr(socket, "create_connection", unexpected)
    monkeypatch.setattr("dotenv.main.DotEnv.dict", unexpected)
    monkeypatch.setenv("GRIDSTATUS_API_KEY", "test-hosted-key")
    monkeypatch.setenv("PJM_API_KEY", "test-direct-key")


def site(horizon):
    return pd.DataFrame({"timestamp": horizon.index, "load_kw": 10., "pv_kw": 2.})


@pytest.fixture
def hosted_client(monkeypatch):
    calls = []

    def client(adapter):
        class FakeClient:
            def get_dataset(self, dataset, **kwargs):
                calls.append((dataset, kwargs))
                timestamps = pd.date_range(pd.Timestamp(kwargs["start"]).tz_convert("UTC"),
                    pd.Timestamp(kwargs["end"]).tz_convert("UTC"),
                    freq=f"{adapter.native_interval_minutes}min", inclusive="left")
                return pd.DataFrame({adapter.timestamp_column: timestamps,
                    adapter.price_column: 100. if dataset == "alternate-test-dataset" else 50.})
        return FakeClient()

    monkeypatch.setattr(GridStatusIOProvider, "_build_client", client)
    return calls


@pytest.mark.parametrize("region", supported_regions())
def test_guided_and_experiment_configs_use_identical_region_resolution(region):
    legacy = experiment_region(ExperimentConfig("2025-08-01", 1, region=region))
    guided = resolve_live_api_config(region)
    for field in ("market_provider", "market_location", "carbon_provider", "carbon_zone", "timezone", "provider_options"):
        assert getattr(legacy, field) == getattr(guided, field)


def test_explicit_options_and_location_survive_both_workflows_without_aliasing():
    options = {"dataset": "alternate-test-dataset", "location_column": "node",
        "price_column": "price", "timestamp_column": "start"}
    legacy = ExperimentConfig("2025-08-01", 1, region=HOSTED, market_location="TEST NODE",
        electricity_maps_zone="TEST-CARBON-ZONE", provider_options=options)
    guided = resolve_live_api_config(HOSTED, market_location="TEST NODE",
        carbon_zone="TEST-CARBON-ZONE", provider_options=options)
    options["dataset"] = "changed-after-resolution"
    assert legacy.provider_options == guided.provider_options
    assert experiment_region(legacy).provider_options == guided.provider_options
    assert guided.provider_options["dataset"] == "alternate-test-dataset"
    assert guided.market_location == legacy.market_location == "TEST NODE"
    assert guided.carbon_zone == legacy.electricity_maps_zone == "TEST-CARBON-ZONE"
    legacy.provider_options["dataset"] = "changed-legacy"
    assert guided.provider_options["dataset"] == "alternate-test-dataset"
    preset = get_region_config(HOSTED)
    preset.provider_options["dataset"] = "changed-copy"
    assert get_region_config(HOSTED).provider_options["dataset"] == "pjm_lmp_real_time_5_min"


@pytest.mark.parametrize("explicit", [None, "TH_SP15_GEN-APND"])
def test_legacy_caiso_alias_remains_compatible(explicit):
    config = ExperimentConfig("2025-08-01", 1, caiso_node="legacy-node", market_location=explicit)
    assert config.caiso_node == config.market_location == (explicit or "legacy-node")
    assert experiment_region(config).market_location == config.market_location


@pytest.mark.parametrize("date,count", [("2025-03-09", 92), ("2025-11-02", 100), ("2025-08-01", 96)])
def test_both_retrieval_paths_use_hosted_dataset_location_units_and_dst(hosted_client, date, count):
    horizon = build_horizon(date, 1, EASTERN)
    options = {"location_column": "node", "price_column": "price", "timestamp_column": "start"}
    legacy = experiment_region(ExperimentConfig(date, 1, region=HOSTED,
        market_location="TEST NODE", provider_options=options))
    prices = gridstatus_data.fetch_region_prices(legacy, date, 1)
    guided = resolve_live_api_config(HOSTED, market_location="TEST NODE", provider_options=options)
    data = load_signal_data(guided, horizon, site_profile=site(horizon), carbon_fallback_gCO2_per_kWh=300.)
    pd.testing.assert_frame_equal(prices, data[["timestamp", "price_per_kWh"]])
    assert len(prices) == count
    assert prices.price_per_kWh.to_numpy() == pytest.approx(.05)
    assert prices.timestamp.is_unique
    assert len(hosted_client) == 2
    for dataset, query in hosted_client:
        assert dataset == "pjm_lmp_real_time_5_min"
        assert query["filter_column"] == "node" and query["filter_value"] == "TEST NODE"
        assert query["tz"] == EASTERN
        assert pd.Timestamp(query["start"]) == horizon.start
        assert pd.Timestamp(query["end"]) == horizon.end


def test_cache_separates_datasets_and_ignores_old_optionless_hosted_cache(tmp_path, hosted_client):
    horizon = build_horizon("2025-08-01", 1, EASTERN)
    old_key = _build_cache_key("wholesale_price", horizon, provider="gridstatus_io",
        location="WESTERN HUB", provider_options=None)
    pd.DataFrame({"timestamp": horizon.index, "price_per_kWh": 999.}).to_csv(tmp_path/f"{old_key}.csv", index=False)
    first = resolve_live_api_config(HOSTED)
    second = resolve_live_api_config(HOSTED, provider_options={"dataset": "alternate-test-dataset"})
    def load(config):
        return load_signal_data(config, horizon, site_profile=site(horizon),
            carbon_fallback_gCO2_per_kWh=300., cache_directory=tmp_path)
    assert load(first).price_per_kWh.to_numpy() == pytest.approx(.05)
    assert load(second).price_per_kWh.to_numpy() == pytest.approx(.10)
    assert load(first).price_per_kWh.to_numpy() == pytest.approx(.05)
    assert [call[0] for call in hosted_client] == ["pjm_lmp_real_time_5_min", "alternate-test-dataset"]


@pytest.mark.parametrize("region,target", [(HOSTED, "pjm"), ("pjm_western_hub", "gridstatus_io")])
def test_switching_provider_requires_explicit_location(region, target):
    with pytest.raises(SourceConfigurationError, match="explicit market location"):
        resolve_live_api_config(region, market_provider=target)


def test_provider_switch_discards_incompatible_options_and_never_infers_hosted_dataset():
    direct = resolve_live_api_config(HOSTED, market_provider="pjm", market_location="999")
    assert direct.market_provider == "pjm" and direct.market_location == "999"
    assert direct.provider_options is None
    with pytest.raises(SourceConfigurationError, match="requires explicit configuration"):
        resolve_live_api_config("pjm_western_hub", market_provider="gridstatus_io", market_location="TEST NODE")
    hosted = resolve_live_api_config("pjm_western_hub", market_provider="gridstatus_io", market_location="TEST NODE",
        provider_options={"dataset": "alternate-test-dataset", "timezone": EASTERN, "native_interval_minutes": 5})
    assert hosted.market_location == "TEST NODE" and hosted.provider_options["dataset"] == "alternate-test-dataset"


@pytest.mark.parametrize("options", [[], {"datset": "typo"}, {"api_key": "must-not-appear"},
    {"dataset": " "}, {"dataset": None}, {"native_interval_minutes": 0},
    {"native_interval_minutes": 2.5}, {"native_interval_minutes": True}])
def test_invalid_or_secret_options_fail_without_printing_values(options):
    with pytest.raises(SourceConfigurationError) as error:
        resolve_live_api_config(HOSTED, provider_options=options)
    assert "must-not-appear" not in str(error.value)


def test_invalid_provider_timezone_retains_typed_error():
    with pytest.raises(TimezoneNormalizationError):
        resolve_live_api_config(HOSTED, provider_options={"timezone": "Not/A_Zone"})


def test_invalid_region_object_fails_before_retrieval():
    with pytest.raises(SourceConfigurationError, match="dictionary"):
        resolve_region_config(replace(get_region_config(HOSTED), provider_options=["dataset"]))
    with pytest.raises(SourceConfigurationError, match="Market location"):
        resolve_region_config(replace(get_region_config(HOSTED), market_location=None))


@pytest.mark.parametrize("region,selected,other", [
    (HOSTED, GridStatusIOProvider, PJMProvider), ("pjm_western_hub", PJMProvider, GridStatusIOProvider)])
@pytest.mark.parametrize("error_type", [MissingCredentialsError, RangeLimitError,
    MissingIntervalError, EmptyResponseError, SignalProviderError])
def test_provider_errors_propagate_unchanged_without_substitution(monkeypatch, region, selected, other, error_type):
    error = error_type("Selected provider failed")
    calls = []
    def fail(*args):
        calls.append("selected")
        raise error
    def forbidden(*args):
        raise AssertionError("Do not substitute another provider")
    monkeypatch.setattr(selected, "fetch_energy_prices", fail)
    monkeypatch.setattr(other, "fetch_energy_prices", forbidden)
    horizon = build_horizon("2025-08-01", 1, EASTERN)
    with pytest.raises(error_type) as guided:
        load_signal_data(resolve_live_api_config(region), horizon, site_profile=site(horizon))
    assert guided.value is error
    with pytest.raises(error_type) as legacy:
        gridstatus_data.fetch_region_prices(region, "2025-08-01", 1)
    assert legacy.value is error and calls == ["selected", "selected"]


def test_missing_hosted_credential_does_not_use_available_direct_pjm_key(monkeypatch):
    monkeypatch.delenv("GRIDSTATUS_API_KEY")
    with pytest.raises(MissingCredentialsError, match="GRIDSTATUS_API_KEY"):
        gridstatus_data.fetch_region_prices(HOSTED, "2025-08-01", 1)


def test_csv_and_retail_sources_do_not_construct_market_providers(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No market provider is needed")
    monkeypatch.setattr(gridstatus_data, "get_provider", forbidden)
    horizon = build_horizon("2025-08-01", 1, EASTERN)
    frame = site(horizon).assign(net_load_kw=8., price_per_kWh=.12, **{"gCO2/kWh": 300.})
    csv = resolve_signal_config("integrated_csv", timezone=EASTERN)
    assert csv.provider_options is None
    pd.testing.assert_frame_equal(load_signal_data(csv, horizon, integrated_data=frame), frame)
    with pytest.raises(SourceConfigurationError, match="does not use market"):
        resolve_signal_config("integrated_csv", timezone=EASTERN, provider_options={"dataset": "unneeded"})
    retail = load_signal_data(resolve_live_api_config(HOSTED), horizon,
        site_profile=site(horizon), price_source=FixedRetailPrice(.12), carbon_fallback_gCO2_per_kWh=300.)
    assert retail.price_per_kWh.eq(.12).all()
