"""Reproduce an indicative utility-footprint population estimate, offline.

This is not a tariff-eligibility count or a GIS population intersection.
Only public EIA distribution-account and Census household-size evidence is used.
No API, environment credentials, customer bills or private location data is read.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUTS = ROOT / "docs/utility_sources/pjm_population/inputs.json"


def estimate(inputs_path=DEFAULT_INPUTS):
    inputs_path = Path(inputs_path)
    config = json.loads(inputs_path.read_text())
    if config.get("format_version") not in (1, 2):
        raise ValueError("Unsupported population input format.")
    source = inputs_path.parent / config["eia"]["extract_file"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != config["eia"]["extract_sha256"]:
        raise ValueError("The public EIA snapshot changed; review and repin its provenance.")
    rows = list(csv.DictReader(source.open(newline="")))
    seen = set()
    for row in rows:
        key = tuple(row[k] for k in ("utility_id", "state", "part", "service_type", "ba_code"))
        if key in seen:
            raise ValueError("Duplicate utility/state/service row would double count delivery accounts.")
        seen.add(key)
        if row["ba_code"] != "PJM" or row["service_type"] not in ("Bundled", "Delivery"):
            raise ValueError("Only PJM distribution-service rows are permitted; energy marketers would double count accounts.")
        row["utility_id"] = int(row["utility_id"])
        row["res_customers"] = int(row["res_customers"])
        if row["res_customers"] < 0 and row["utility_id"] != 99999:
            raise ValueError("Negative customer counts require an identified EIA adjustment row.")
    denominator_accounts = sum(row["res_customers"] for row in rows)
    if denominator_accounts != config["eia"]["expected_account_total"]:
        raise ValueError("PJM distribution-account denominator differs from the reviewed source extract.")
    household = config["household_size"]["states"]
    implemented = config.get("implemented_repository_keys")
    if implemented is not None:
        if len(set(implemented)) != len(implemented):
            raise ValueError("Duplicate declared repository workflow.")
        declared = {key for utility in config["included_utilities"]
                    for key in utility["repository_keys"]}
        if set(implemented) != declared:
            raise ValueError("Selected utilities and declared repository workflows must agree.")
    merged_requirements = {item["utility_id"]: item
                           for item in config.get("merged_utility_requirements", [])}
    for utility in config["included_utilities"]:
        if utility["utility_id"] == 66101:
            required = {"firstenergy_pa_met_ed", "firstenergy_pa_penelec",
                        "firstenergy_pa_penn_power", "firstenergy_pa_west_penn"}
            rule = merged_requirements.get(66101)
            if (rule is None or set(rule["required_repository_keys"]) != required
                    or set(rule["states"]) != {"PA"}
                    or set(utility["states"]) != {"PA"}
                    or set(utility["repository_keys"]) != required
                    or not required.issubset(set(implemented or []))):
                raise ValueError("Merged FirstEnergyPA counts require all four implemented PA districts; exclude NY.")
    numerator = []
    selected_keys = set()
    for utility in config["included_utilities"]:
        for state in utility["states"]:
            identity = (utility["utility_id"], state)
            if identity in selected_keys:
                raise ValueError("Duplicate selected utility/state footprint.")
            selected_keys.add(identity)
            selected = [row for row in rows if row["utility_id"] == identity[0] and row["state"] == state]
            if not selected:
                raise ValueError("Selected utility/state is absent from the source extract.")
            accounts = sum(row["res_customers"] for row in selected)
            size = household[state]["persons"]
            record = dict(utility=utility["label"], state=state,
                residential_accounts=accounts, persons_per_household=size,
                estimated_household_population=accounts*size,
                evidence="EIA2024 residential distribution accounts times statewide Census household size")
            if config["format_version"] >= 2:
                record.update(utility_id=utility["utility_id"], repository_keys=utility["repository_keys"])
            numerator.append(record)
    west = config["west_penn"]
    merged_selected = any(key[0] == west["excluded_merged_utility_id"] for key in selected_keys)
    if merged_selected and west.get("counted_currently", True):
        raise ValueError("Do not add an inferred West Penn district to the merged FirstEnergyPA count.")
    rate, half = west["reported_switched_fraction"], west["fraction_rounding_half_width"]
    if not 0 < rate-half < rate+half < 1:
        raise ValueError("Invalid published fraction/rounding precision.")
    west_accounts = west["residential_switched_accounts"] / rate
    size = household[west["state"]]["persons"]
    if west.get("counted_currently", True):
        numerator.append(dict(utility=west["label"], state=west["state"],
            residential_accounts=west_accounts, persons_per_household=size,
            estimated_household_population=west_accounts*size,
            evidence="District accounts estimated from published switched count divided by rounded switched percentage"))
    people = sum(row["estimated_household_population"] for row in numerator)
    accounts = sum(row["residential_accounts"] for row in numerator)
    denominator_people = config["pjm"]["reported_population"]
    share = people / denominator_people
    sensitivity = config["sensitivity"]["household_occupancy_relative_change"]
    if not 0 <= sensitivity < 1:
        raise ValueError("Sensitivity must be a relative factor below one.")
    result = dict(
        research_date=config["research_date"],
        reported_headline=f"About {share:.0%} of PJM's population, approximately {people/1e6:.0f} million people, as an indicative household-based utility-footprint proxy",
        metric="Estimated household population in implemented utility footprints divided by rounded PJM population",
        is_geospatial_population_count=False, is_tariff_eligible_population_count=False,
        numerator=numerator, estimated_people=people, denominator_people=denominator_people,
        population_share=share,
        selected_residential_distribution_accounts=accounts,
        pjm_residential_distribution_accounts=denominator_accounts,
        residential_account_share_crosscheck=accounts/denominator_accounts,
        west_penn_accounts_rounding_only_bounds=[west["residential_switched_accounts"]/(rate+half),
                                               west["residential_switched_accounts"]/(rate-half)],
        illustrative_occupancy_sensitivity_share=[share*(1-sensitivity), share*(1+sensitivity)],
        sensitivity_is_confidence_interval=False,
        alliant_change_in_pjm_population=config["alliant_effect_on_pjm"],
        limitations=config["limitations"],
        source_inputs_sha256=hashlib.sha256(inputs_path.read_bytes()).hexdigest(),
        source_extract_sha256=config["eia"]["extract_sha256"],
    )
    if config["format_version"] >= 2:
        if not implemented:
            raise ValueError("Current-format estimates require declared implemented repository workflows.")
        additions = []
        addition_keys = set()
        for item in config.get("current_additions", []):
            key = (item["utility_id"], item["state"])
            if key in addition_keys:
                raise ValueError("Duplicate current utility/state addition.")
            addition_keys.add(key)
            match = [row for row in numerator if (row.get("utility_id"), row["state"]) == key]
            if len(match) != 1 or item["repository_key"] not in match[0]["repository_keys"]:
                raise ValueError("Current addition does not match a selected implemented utility/state.")
            additions.append(match[0])
        added_people = sum(row["estimated_household_population"] for row in additions)
        added_accounts = sum(row["residential_accounts"] for row in additions)
        baseline_config = config["baseline"]
        baseline_path = inputs_path.parent / baseline_config["estimate_file"]
        baseline_input_path = inputs_path.parent / baseline_config["inputs_file"]
        if (hashlib.sha256(baseline_path.read_bytes()).hexdigest() != baseline_config["estimate_sha256"]
                or hashlib.sha256(baseline_input_path.read_bytes()).hexdigest() != baseline_config["inputs_sha256"]):
            raise ValueError("Historical baseline evidence changed; preserve its original identity.")
        baseline = json.loads(baseline_path.read_text())
        result.update(
            implemented_utility_state_district_workflows=len(implemented),
            implemented_repository_keys=implemented,
            merged_firstenergy_pa_counted_once=merged_selected,
            legacy_west_penn_estimate_counted=west.get("counted_currently", True),
            current_additions=additions,
            added_residential_accounts_this_implementation=added_accounts,
            added_estimated_people_this_implementation=added_people,
            added_population_percentage_points=100*added_people/denominator_people,
            estimated_people_before_current_additions=people-added_people,
            population_share_before_current_additions=(people-added_people)/denominator_people,
            implemented_workflows_before_current_additions=len(implemented)-len(additions),
            historical_baseline=dict(research_date=baseline["research_date"],
                implemented_workflows=baseline_config["implemented_workflow_count"],
                estimated_people=baseline["estimated_people"],
                population_share=baseline["population_share"],
                source_estimate_sha256=baseline_config["estimate_sha256"]),
        )
        # This rounding range belongs only to the old inferred district estimate.
        result["west_penn_accounts_rounding_only_bounds"] = None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--output", type=Path, help="Optional JSON output; no data retrieval occurs")
    args = parser.parse_args()
    result = estimate(args.inputs)
    content = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content)
    print(content, end="")


if __name__ == "__main__":
    main()
