"""Offline evidence and territory-scope safeguards for the population proxy."""
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path

import pytest

from tools.estimate_pjm_population_coverage import DEFAULT_INPUTS, estimate


@pytest.fixture
def inputs(tmp_path):
    config = json.loads(DEFAULT_INPUTS.read_text())
    names = [config["eia"]["extract_file"], config["baseline"]["estimate_file"],
             config["baseline"]["inputs_file"]]
    previous = config.get("previous_implementation_snapshot")
    if previous:
        names += [previous["estimate_file"], previous["inputs_file"]]
    for name in names:
        (tmp_path / name).write_bytes((DEFAULT_INPUTS.parent / name).read_bytes())
    target = tmp_path / "inputs.json"
    target.write_text(json.dumps(config))
    return target, config


def save(inputs):
    path, config = inputs
    path.write_text(json.dumps(config))
    return path


def test_current_proxy_and_aes_increment_have_distinct_denominators():
    result = estimate()
    assert result["implemented_utility_state_district_workflows"] == 23
    assert result["implemented_workflows_before_current_additions"] == 22
    assert result["selected_residential_distribution_accounts"] == 21_012_771
    assert result["pjm_residential_distribution_accounts"] == 27_756_201
    assert result["estimated_people"] == pytest.approx(51_963_435.6)
    assert result["estimated_people_before_current_additions"] == pytest.approx(50_828_819.43)
    assert result["added_residential_accounts_this_implementation"] == 478_741
    assert result["added_estimated_people_this_implementation"] == pytest.approx(1_134_616.17)
    assert result["population_share"] == pytest.approx(51_963_435.6 / 67_000_000)
    aes = [row for row in result["numerator"] if row["utility_id"] == 4922]
    assert len(aes) == 1
    assert aes[0]["state"] == "OH"
    assert aes[0]["residential_accounts"] == 132_522 + 346_219
    assert aes[0]["repository_keys"] == ["aes_ohio"]
    assert not result["is_geospatial_population_count"]
    assert not result["is_tariff_eligible_population_count"]
    assert result["sensitivity_is_confidence_interval"] is False


def test_multistate_companies_and_firstenergy_merger_do_not_double_count():
    result = estimate()
    rows = result["numerator"]
    merged = [row for row in rows if row["utility_id"] == 66101]
    assert len(merged) == 1
    assert merged[0]["state"] == "PA"
    assert merged[0]["residential_accounts"] == 1_802_612
    assert len(merged[0]["repository_keys"]) == 4
    for uid in (5027, 15263, 15270):
        assert {row["state"] for row in rows if row["utility_id"] == uid} == {"MD"}
    assert {row["state"] for row in rows if row["utility_id"] == 19876} == {"VA", "NC"}
    assert result["legacy_west_penn_estimate_counted"] is False
    assert result["west_penn_accounts_rounding_only_bounds"] is None


def test_original_seven_workflow_baseline_retains_exact_evidence_identity():
    config = json.loads(DEFAULT_INPUTS.read_text())
    root = DEFAULT_INPUTS.parent
    expected = json.loads((root / config["baseline"]["estimate_file"]).read_text())
    assert estimate(root / config["baseline"]["inputs_file"]) == expected
    assert expected["population_share"] == pytest.approx(0.42232337643132656)


def test_latest_toledo_snapshot_retains_exact_evidence_identity():
    config = json.loads(DEFAULT_INPUTS.read_text())
    root = DEFAULT_INPUTS.parent
    previous = config["previous_implementation_snapshot"]
    expected = json.loads((root / previous["estimate_file"]).read_text())
    assert estimate(root / previous["inputs_file"]) == expected
    assert expected["implemented_utility_state_district_workflows"] == 22
    assert expected["population_share"] == pytest.approx(50_828_819.43 / 67_000_000)


def test_fixed_cei_snapshot_retains_exact_evidence_identity():
    root = DEFAULT_INPUTS.parent
    expected = json.loads((root / "estimate_2026-10-31.json").read_text())
    assert estimate(root / "inputs_2026-10-31.json") == expected
    assert expected["implemented_utility_state_district_workflows"] == 21
    assert expected["population_share"] == pytest.approx(50_168_030.25 / 67_000_000)


def test_duplicate_utility_state_rejected(inputs):
    inputs[1]["included_utilities"].append(deepcopy(inputs[1]["included_utilities"][0]))
    with pytest.raises(ValueError, match="Duplicate selected utility/state"):
        estimate(save(inputs))


def test_merged_company_requires_every_supported_district(inputs):
    config = inputs[1]
    merged = next(row for row in config["included_utilities"] if row["utility_id"] == 66101)
    merged["repository_keys"].remove("firstenergy_pa_penelec")
    config["implemented_repository_keys"].remove("firstenergy_pa_penelec")
    with pytest.raises(ValueError, match="all four implemented PA districts"):
        estimate(save(inputs))


def test_merged_company_cannot_include_new_york_or_old_west_penn_estimate(inputs):
    config = inputs[1]
    merged = next(row for row in config["included_utilities"] if row["utility_id"] == 66101)
    merged["states"].append("NY")
    with pytest.raises(ValueError, match="exclude NY"):
        estimate(save(inputs))
    merged["states"].remove("NY")
    config["west_penn"]["counted_currently"] = True
    with pytest.raises(ValueError, match="inferred West Penn"):
        estimate(save(inputs))


@pytest.mark.parametrize("mode", ["hash", "energy_supplier", "duplicate_row"])
def test_source_corruption_and_energy_supplier_overcount_rejected(inputs, mode):
    path, config = inputs
    source = path.parent / config["eia"]["extract_file"]
    if mode == "hash":
        source.write_bytes(source.read_bytes() + b"\n")
        expected = "snapshot changed"
    else:
        rows = list(csv.DictReader(source.open(newline="")))
        fields = list(rows[0])
        if mode == "energy_supplier":
            rows[0]["service_type"] = "Energy"
            expected = "Only PJM distribution"
        else:
            rows.append(deepcopy(rows[0]))
            expected = "Duplicate utility/state/service"
        with source.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        config["eia"]["extract_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match=expected):
        estimate(save(inputs))


@pytest.mark.parametrize("snapshot,expected", [("baseline", "Historical baseline"),
                                               ("previous_implementation_snapshot", "Previous implementation snapshot")])
def test_changed_historical_baseline_is_not_relabelled(inputs, snapshot, expected):
    path, config = inputs
    baseline = path.parent / config[snapshot]["estimate_file"]
    baseline.write_bytes(baseline.read_bytes() + b"\n")
    with pytest.raises(ValueError, match=expected + " evidence changed"):
        estimate(save(inputs))
