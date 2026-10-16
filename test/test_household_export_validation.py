"""Synthetic energy scaling and reproducible residential stress studies; offline."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
import pytest

from src.local_web.contract import validate_request
from src.local_web import export_study, site_inputs, worker
from src.opendss.residential_service import ResidentialService
from src.profiles import SyntheticLoad, LoadScaling
from src.timeseries import build_interval_index
from tools.run_residential_export_validation import study_request, concentrate_evening, CASES
from test_export_ac_replay import fixture_results


@pytest.mark.parametrize("start,end,intervals", [
    ("2026-07-01", "2026-07-31", 2976),
    ("2026-03-01", "2026-03-31", 2972),
    ("2026-11-01", "2026-11-30", 2884),
])
def test_horizon_energy_exact_repeatable_and_dst_aware(start, end, intervals):
    grid = build_interval_index(start, end, "America/Los_Angeles", 15)
    source = SyntheticLoad("residential", LoadScaling.TOTAL_ENERGY_KWH, total_energy_kWh=744.)
    a, b = source.build_load_kw(grid), source.build_load_kw(grid)
    pd.testing.assert_series_equal(a, b)
    assert len(a) == intervals
    assert a.sum() * grid.timestep_hours == pytest.approx(744., abs=1e-9)
    assert a.min() > 0 and a.max() > 1.8
    assert "SYNTHETIC DATA" in source.describe()
    assert a[grid.index.hour == 18].mean() > a[grid.index.hour == 3].mean()
    frame = pd.DataFrame({"timestamp": grid.index, "load_kw": a})
    stressed = concentrate_evening(frame, .8)
    original_daily = frame.groupby(frame.timestamp.dt.date).load_kw.sum() * .25
    stressed_daily = stressed.groupby(stressed.timestamp.dt.date).load_kw.sum() * .25
    assert stressed_daily.to_numpy() == pytest.approx(original_daily)
    evening = stressed.loc[stressed.timestamp.dt.hour == 18].groupby(stressed.timestamp.dt.date).load_kw.sum() * .25
    assert evening.to_numpy() == pytest.approx(original_daily * .8)
    assert not np.array_equal(frame.load_kw, stressed.load_kw)


@pytest.mark.parametrize("bad", [
    dict(mode="constant", archetype="residential", total_energy_kWh=744.),
    dict(mode="synthetic", archetype="residential", total_energy_kWh=744., power_kw=1.),
    dict(mode="synthetic", archetype="residential", total_energy_kWh=-1.),
    dict(mode="synthetic", archetype="residential", total_energy_kWh=float("nan")),
    dict(mode="synthetic", archetype="residential", total_energy_kWh=True),
])
def test_contract_rejects_ambiguous_or_invalid_energy(bad):
    r = study_request()
    r["load"] = bad
    with pytest.raises(ValueError):
        validate_request(r)


def test_legacy_peak_requests_retain_the_same_profile(tmp_path):
    r = study_request()
    r["load"] = dict(mode="synthetic", archetype="residential", power_kw=2.)
    validate_request(r)
    frame, _, _, provenance = site_inputs.build_site_inputs(r, tmp_path)
    grid = build_interval_index(r["start_date"], r["end_date"], r["timezone"], 15)
    expected = SyntheticLoad("residential", peak_kw=2.).build_load_kw(grid)
    assert frame.load_kw.to_numpy() == pytest.approx(expected)
    assert provenance["load"]["is_synthetic"] is True
    assert provenance["load"]["measured"] is False


def form_request(request):
    """Execute the actual shared browser/desktop form serializer in Node."""
    source = Path("src/local_web/static/app.js").read_text()
    function = "function readRequest() {" + source.split("function readRequest() {", 1)[1].split('\nform.addEventListener("submit"', 1)[0]
    driver = r"""
const r=JSON.parse(require('fs').readFileSync(0,'utf8'));
const template=structuredClone(r), weatherId=null, siteLabel=r.site.label;
const values={...r,...r.battery,...r.solar,latitude:r.site.latitude,longitude:r.site.longitude,utility:r.site.utility,
 load_mode:'synthetic',load_power_kw:999,load_scaling:'energy',load_total_energy_kWh:744,archetype:'residential'};
const field=(name)=>({value:values[name],checked:false});
const form={elements:new Proxy({namedItem:field},{get:(obj,key)=>key in obj?obj[key]:field(key)})};
const $=(id)=>({hidden:false,querySelectorAll:()=>r.strategies.map(value=>({value}))});
const gridOnly=()=>false, energyLoadAvailable=()=>true,siteProfile=()=>r.site_profile;
const carbonSettings=()=>({source:'electricity_maps',region:'from_location'});
const exportActive=()=>true,readExportControls=()=>r.solar_export;
""" + function + "\nprocess.stdout.write(JSON.stringify(readRequest()));"
    return json.loads(subprocess.run(["node", "-e", driver], input=json.dumps(request), text=True,
                                     capture_output=True, check=True).stdout)


def test_form_to_shared_worker_preserves_energy_and_builds_744_kwh(tmp_path, monkeypatch):
    request = form_request(study_request())
    assert request["load"] == dict(mode="synthetic", archetype="residential", total_energy_kWh=744.)
    validate_request(request)
    # Only the carbon client is mocked; real contract, load/PV generation and
    # worker routing run without any live data requests or reoptimization.
    from src.local_web import carbon
    monkeypatch.setattr(carbon, "values", lambda r, d, idx: (np.ones(len(idx)), {"warning": "Offline carbon fixture"}))
    captured = {}
    def capture(directory, r, frame, provenance, *, pv_replay=None):
        captured.update(rows=len(frame), energy=frame.load_kw.sum() * .25, peak=frame.load_kw.max(),
                        pv=pv_replay, provenance=provenance)
    monkeypatch.setattr(export_study, "execute", capture)
    (tmp_path / "request.json").write_text(json.dumps(request))
    worker.execute(tmp_path)
    assert captured["rows"] == 2976 and captured["energy"] == pytest.approx(744., abs=1e-9)
    assert captured["peak"] > 1.8 and captured["pv"] is not None
    assert captured["provenance"]["load"]["native_load_energy_kWh"] == pytest.approx(744.)
    assert pd.read_csv(tmp_path / "normalized.csv").load_kw.sum() * .25 == pytest.approx(744.)


def test_network_overrides_saved_with_correct_warnings_without_changing_bills(tmp_path, monkeypatch):
    results = fixture_results()
    original = deepcopy(results)
    monkeypatch.setattr(export_study, "compare", lambda *args, **kwargs: results)
    (tmp_path / "engine.json").write_text('{"id":"test"}')
    service = ResidentialService(service_length_km=.15, l1_load_fraction=.85, l2_load_fraction=.05)
    request = study_request()
    request["pv_capacity_kw"] = 6.  # Match this persistence fixture's AC availability.
    export_study.execute(tmp_path, request, pd.DataFrame({"timestamp": results["grid_only"]["dispatch"].timestamp}),
                         {"warnings": []}, residential_service=service)
    manifest = json.loads((tmp_path / "result.json").read_text())
    network = manifest["ac_validation"]["network_configuration"]
    assert network["service_length_km"] == .15 and network["l1_load_fraction"] == .85
    assert any("150 m" in w and "85% L1" in w for w in manifest["warnings"])
    bills = json.loads((tmp_path / "solar_bills.json").read_text())
    for scenario in bills:
        assert bills[scenario]["bill"] == original[scenario]["bill"]
        pd.testing.assert_frame_equal(results[scenario]["dispatch"], original[scenario]["dispatch"])


@pytest.mark.parametrize("case", CASES)
def test_all_validation_cases_have_explicit_valid_requests(case):
    request = study_request(case)
    assert request["load"]["total_energy_kWh"] == 744.
    assert request["solar_export"]["account"]["reference"].startswith("Hypothetical")


def test_stress_redistribution_rejects_naive_or_missing_intervals():
    frame = pd.DataFrame({"timestamp": pd.date_range("2026-07-01", periods=96, freq="15min"), "load_kw": 1.})
    with pytest.raises(ValueError, match="timezone-aware"):
        concentrate_evening(frame, .8)
    frame.timestamp = frame.timestamp.dt.tz_localize("America/Los_Angeles")
    with pytest.raises(ValueError, match="continuous"):
        concentrate_evening(frame.drop(index=3), .8)
