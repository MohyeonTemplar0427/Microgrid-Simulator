"""Offline PJM carbon provenance, complete interval coverage and accounting."""
from copy import deepcopy
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from src.local_web.regional_study import defaults, calendar_cycles, prepare, execute


ZONE = "US-MIDA-PJM"
SPEC = {"source": "electricity_maps", "region": ZONE}


def carbon_request(day="2025-07-01", end=None, minutes=15):
    r = defaults("dominion_energy_north_carolina", "residential")
    r.update(start_date=day, end_date=end or day, timestep_minutes=minutes, carbon=deepcopy(SPEC))
    r["billing_cycles"] = calendar_cycles(r["start_date"], r["end_date"])
    r["operating_contract"].update(interconnection_confirmed=True,
        grid_charging_confirmed=True, reference="Explicit hypothetical approved non-export account")
    return r


def native_index(r):
    start = pd.Timestamp(r["start_date"], tz=r["timezone"])
    stop = pd.Timestamp(r["end_date"], tz=r["timezone"]) + pd.DateOffset(days=1)
    return pd.date_range(start, stop, freq="15min", inclusive="left").tz_convert("UTC")


def payload(start, end):
    index = pd.date_range(start, end, freq="15min", inclusive="left")
    # A reproducible varying signal makes time/energy weighting errors visible.
    return {"zone": ZONE, "temporalGranularity": "15_minutes", "data": [
        {"datetime": t.isoformat(), "carbonIntensity": 120. + t.hour * 13. + t.minute / 4.,
         "zone": ZONE, "emissionFactorType": "lifecycle", "flowTraced": True,
         "isEstimated": i % 7 == 0, "estimationMethod": "TEST_ESTIMATE" if i % 7 == 0 else None,
         "createdAt": "2026-10-01T00:00:00Z", "updatedAt": "2026-10-02T00:00:00Z"}
        for i, t in enumerate(index)]}


def mock_provider(monkeypatch, transform=None):
    import src.signal_pipeline.electricity_maps_data as provider
    calls = []
    monkeypatch.setenv("ELECTRICITY_MAPS_API_KEY", "offline-test-only")

    def fetch(key, zone, start, end, **kwargs):
        assert key == "offline-test-only" and zone == ZONE
        assert kwargs == {"flow_traced": True, "emission_factor_type": "lifecycle"}
        calls.append((start, end))
        result = payload(start, end)
        return transform(result) if transform else result

    monkeypatch.setattr(provider, "get_carbon_intensity_range", fetch)
    return calls


@pytest.mark.parametrize("day,count", [("2025-03-09", 92), ("2025-11-02", 100), ("2026-03-08", 92)])
@pytest.mark.parametrize("minutes", [15, 30])
def test_dst_coverage_aggregation_and_preserved_estimation_metadata(tmp_path, monkeypatch, day, count, minutes):
    from src.local_web.regional_carbon import values
    calls = mock_provider(monkeypatch)
    r = carbon_request(day, minutes=minutes)
    index = native_index(r)
    result, meta = values(r, tmp_path, index[::minutes // 15])
    source = payload(index[0], index[-1] + pd.Timedelta(minutes=15))["data"]
    expected = np.array([row["carbonIntensity"] for row in source]).reshape(-1, minutes // 15).mean(axis=1)
    assert len(result) == count // (minutes // 15)
    assert result == pytest.approx(expected)
    assert len(calls) == 1
    assert meta["status"] == "verified" and meta["zone"] == ZONE
    assert meta["factor_type"] == "lifecycle" and meta["flow_traced"] is True
    assert meta["units"] == "gCO2e/kWh"
    assert meta["provider_interval_minutes"] == 15 and meta["study_interval_minutes"] == minutes
    assert meta["coverage"]["interval_count"] == count
    assert meta["coverage"]["estimated_interval_count"] == sum(row["isEstimated"] for row in source)
    assert pd.Timestamp(meta["coverage"]["start_utc"]) == index[0]
    assert pd.Timestamp(meta["coverage"]["end_exclusive_utc"]) == index[-1] + pd.Timedelta(minutes=15)
    assert meta["sha256"] == hashlib.sha256((tmp_path / "carbon-source.csv").read_bytes()).hexdigest()
    csv = pd.read_csv(tmp_path / "carbon-source.csv")
    assert {"isEstimated", "estimationMethod", "createdAt", "updatedAt", "flowTraced", "emissionFactorType", "zone"} <= set(csv)
    assert list((tmp_path / "carbon-source").glob("*.json"))


def test_chunk_boundaries_follow_local_calendar_across_dst(tmp_path, monkeypatch):
    from src.local_web.regional_carbon import values
    calls = mock_provider(monkeypatch)
    r = carbon_request("2025-03-08", "2025-03-10", 30)
    index = native_index(r)
    result, _ = values(r, tmp_path, index[::2])
    assert len(result) == 142
    assert len(calls) == 2
    assert pd.Timestamp(calls[0][0]) == pd.Timestamp("2025-03-08T05:00:00Z")
    assert pd.Timestamp(calls[0][1]) == pd.Timestamp("2025-03-10T04:00:00Z")
    assert pd.Timestamp(calls[1][0]) == pd.Timestamp(calls[0][1])
    assert pd.Timestamp(calls[1][1]) == pd.Timestamp("2025-03-11T04:00:00Z")


@pytest.mark.parametrize("bad", ["gap", "duplicate", "reversed", "nan", "negative", "zone", "top_zone", "factor", "flow", "estimated", "missing_metadata", "hourly"])
def test_bad_coverage_and_unverified_basis_reject_without_a_passing_cache(tmp_path, monkeypatch, bad):
    from src.local_web.regional_carbon import values

    def corrupt(result):
        rows = result["data"]
        if bad == "gap": rows.pop()
        elif bad == "duplicate": rows.append(deepcopy(rows[-1]))
        elif bad == "reversed": result["data"] = rows[::-1]
        elif bad == "nan": rows[0]["carbonIntensity"] = float("nan")
        elif bad == "negative": rows[0]["carbonIntensity"] = -1
        elif bad == "zone": rows[0]["zone"] = "US-CAL-CISO"
        elif bad == "top_zone": result["zone"] = "US-CAL-CISO"
        elif bad == "factor": rows[0]["emissionFactorType"] = "direct"
        elif bad == "flow": rows[0]["flowTraced"] = False
        elif bad == "estimated": rows[0]["isEstimated"] = "false"
        elif bad == "missing_metadata": rows[0].pop("emissionFactorType")
        elif bad == "hourly": result["temporalGranularity"] = "hourly"
        return result

    mock_provider(monkeypatch, corrupt)
    r = carbon_request()
    with pytest.raises(ValueError): values(r, tmp_path, native_index(r))
    assert not (tmp_path / "carbon-source.json").exists()


@pytest.mark.parametrize("damage", ["csv", "raw", "request"])
def test_saved_source_reaudit_rejects_modified_data_or_request(tmp_path, monkeypatch, damage):
    from src.local_web.regional_carbon import values
    calls = mock_provider(monkeypatch)
    r = carbon_request()
    index = native_index(r)
    original, _ = values(r, tmp_path, index)
    assert values(r, tmp_path, index)[0] == pytest.approx(original)
    assert len(calls) == 1
    if damage == "csv":
        path = tmp_path / "carbon-source.csv"
        path.write_bytes(path.read_bytes() + b"\n")
    elif damage == "raw":
        path = next((tmp_path / "carbon-source").glob("*.json"))
        path.write_bytes(path.read_bytes() + b"\n")
    else:
        r = carbon_request("2025-07-02")
        index = native_index(r)
    with pytest.raises(ValueError): values(r, tmp_path, index)
    assert len(calls) == 1


def test_optional_carbon_preserves_old_requests_and_missing_credentials_never_becomes_zero(tmp_path, monkeypatch):
    from src.local_web.regional_carbon import values
    r = carbon_request()
    monkeypatch.delenv("ELECTRICITY_MAPS_API_KEY", raising=False)
    for disabled in (None, "missing"):
        old = deepcopy(r)
        if disabled == "missing": old.pop("carbon")
        else: old["carbon"] = None
        prepare(old)
        data, meta = values(old, tmp_path, native_index(old))
        assert data is None and meta["status"] == "not_requested"
    with pytest.raises(ValueError, match="credential|ELECTRICITY_MAPS_API_KEY"):
        values(r, tmp_path, native_index(r))


@pytest.mark.parametrize("change", ["miso", "forged_operator", "region", "assumed", "timezone", "five_minutes", "2024", "future"])
def test_eligibility_and_dates_do_not_follow_state_or_wholesale_identifiers(change):
    from src.local_web.regional_carbon import validate
    r = carbon_request()
    if change in ("miso", "forged_operator"):
        r = defaults("ameren_illinois", "residential")
        r["carbon"] = deepcopy(SPEC)
        if change == "forged_operator": r["regional_account"]["grid_operator"] = "PJM"
    elif change == "region": r["carbon"]["region"] = "US-CAL-CISO"
    elif change == "assumed": r["carbon"] = {"source": "assumed", "value": 300}
    elif change == "timezone": r["timezone"] = "America/Chicago"
    elif change == "five_minutes": r["timestep_minutes"] = 5
    elif change == "2024": r["start_date"] = r["end_date"] = "2024-01-01"
    elif change == "future": r["start_date"] = r["end_date"] = "2027-01-01"
    # Utility clock selection is enforced by the regional public contract;
    # the carbon parser itself is also usable on a supplied aware time grid.
    with pytest.raises(ValueError):
        prepare(r) if change == "timezone" else validate(r)


@pytest.mark.parametrize("kwargs,extra", [
    ({"flow_traced": True, "emission_factor_type": "lifecycle"}, {"flowTraced": "true", "emissionFactorType": "lifecycle"}),
    ({"flow_traced": False, "emission_factor_type": "direct"}, {"flowTraced": "false", "emissionFactorType": "direct"}),
    ({}, {}),
])
def test_http_request_explicit_basis_and_legacy_default_contract(monkeypatch, kwargs, extra):
    import src.signal_pipeline.electricity_maps_data as provider
    calls = []

    class Response:
        def raise_for_status(self): pass
        def json(self): return {"test": "response"}

    def get(url, **request):
        calls.append((url, request))
        return Response()

    monkeypatch.setattr(provider.requests, "get", get)
    assert provider.get_carbon_intensity_range("offline-test-only", ZONE,
        "2025-01-01T05:00:00Z", "2025-01-02T05:00:00Z", **kwargs) == {"test": "response"}
    url, request = calls[0]
    assert url == "https://api.electricitymaps.com/v4/carbon-intensity/past-range"
    assert request["params"] == {"zone": ZONE, "start": "2025-01-01T05:00:00Z",
        "end": "2025-01-02T05:00:00Z", "temporalGranularity": "15_minutes", **extra}
    assert request["headers"] == {"auth-token": "offline-test-only"}
    assert request["timeout"] == 30


def test_interval_import_emissions_reconcile_and_do_not_change_bills_or_dispatch(tmp_path, monkeypatch):
    mock_provider(monkeypatch)
    r = carbon_request("2025-07-01", "2025-07-02", 30)
    grid, *_ = prepare(r)
    enabled, disabled = tmp_path / "enabled", tmp_path / "disabled"
    for folder in (enabled, disabled):
        folder.mkdir()
        (folder / "engine.json").write_text(json.dumps({"id": "offline-carbon-accounting"}))
    execute(enabled, r)
    no_carbon = deepcopy(r)
    no_carbon["carbon"] = None
    execute(disabled, no_carbon)
    carbon = np.array([row["carbonIntensity"] for row in payload(native_index(r)[0], native_index(r)[-1] + pd.Timedelta(minutes=15))["data"]]).reshape(-1, 2).mean(axis=1)
    comparison = pd.read_csv(enabled / "comparison.csv").set_index("scenario")
    old_comparison = pd.read_csv(disabled / "comparison.csv").set_index("scenario")
    inputs = pd.read_csv(enabled / "inputs.csv")
    assert inputs.carbon_intensity_g_co2e_per_kwh.to_numpy() == pytest.approx(carbon)
    emissions = {}
    for name in ("grid_only", "pv_only", "pv_battery"):
        dispatch = pd.read_csv(enabled / ("dispatch-" + name + ".csv"))
        old = pd.read_csv(disabled / ("dispatch-" + name + ".csv"))
        pd.testing.assert_frame_equal(dispatch[old.columns], old, check_dtype=False, atol=1e-7, rtol=1e-7)
        interval = dispatch.grid_import_kw.to_numpy() * grid.timestep_hours * carbon / 1000.
        emissions[name] = float(interval.sum())
        assert dispatch.grid_import_emissions_kg_co2e.to_numpy() == pytest.approx(interval)
        assert comparison.loc[name, "grid_import_emissions_kg_co2e"] == pytest.approx(emissions[name])
        assert comparison.loc[name, "utility_bill_usd"] == old_comparison.loc[name, "utility_bill_usd"]
        assert comparison.loc[name, "optimization_objective_usd"] == pytest.approx(old_comparison.loc[name, "optimization_objective_usd"])
    for name, amount in emissions.items():
        assert comparison.loc[name, "emissions_difference_vs_grid_kg_co2e"] == pytest.approx(emissions["grid_only"] - amount)
    result = json.loads((enabled / "result.json").read_text())
    assert result["input_provenance"]["carbon"]["zone"] == ZONE
    assert result["ac_validation"]["all_intervals_feasible"]
    assert any("marginal" in warning.lower() for warning in result["warnings"])
    old_result = json.loads((disabled / "result.json").read_text())
    assert old_result["input_provenance"]["carbon"]["status"] == "not_requested"


def test_alternative_tariffs_reuse_the_identical_carbon_source(tmp_path, monkeypatch):
    calls = mock_provider(monkeypatch)
    r = carbon_request("2025-07-01", "2025-07-02", 30)
    r["tariff_comparisons"] = ["1"]
    r["solar"]["dc_capacity_kw"] = r["pv_capacity_kw"] = 0.
    r["battery"] = None
    (tmp_path / "engine.json").write_text(json.dumps({"id": "offline-carbon-alternative"}))
    execute(tmp_path, r)
    comparison = pd.read_csv(tmp_path / "comparison.csv")
    assert len(calls) == 1
    assert set(comparison.tariff) == {"1T", "1"}
    assert comparison.grid_import_emissions_kg_co2e.nunique() == 1
    assert comparison.emissions_difference_vs_grid_kg_co2e.eq(0).all()


def test_existing_verified_export_service_receives_no_carbon_credit(tmp_path, monkeypatch):
    mock_provider(monkeypatch)
    r = carbon_request("2025-07-01", "2025-07-02", 30)
    r["battery"] = None
    r["load"].update(mode="constant", power_kw=1.)
    r["operating_contract"].update(mode="net_metering", grid_charging_confirmed=False)
    r["account"].update(solar_program="net_metering", net_metering_confirmed=True,
        recs_assignment_confirmed=True)
    (tmp_path / "engine.json").write_text(json.dumps({"id": "offline-carbon-no-export-credit"}))
    execute(tmp_path, r)
    dispatch = pd.read_csv(tmp_path / "dispatch-pv_only.csv")
    assert dispatch.grid_export_kw.sum() > 0
    carbon = pd.read_csv(tmp_path / "inputs.csv").carbon_intensity_g_co2e_per_kwh.to_numpy()
    imports_only = dispatch.grid_import_kw.to_numpy() * .5 * carbon / 1000.
    assert dispatch.grid_import_emissions_kg_co2e.to_numpy() == pytest.approx(imports_only)
    comparison = pd.read_csv(tmp_path / "comparison.csv").set_index("scenario")
    assert comparison.loc["pv_only", "grid_import_emissions_kg_co2e"] == pytest.approx(imports_only.sum())
    assert imports_only.sum() > float(((dispatch.grid_import_kw - dispatch.grid_export_kw) * .5 * carbon / 1000.).sum())
