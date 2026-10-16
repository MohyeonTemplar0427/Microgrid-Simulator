"""Offline July 2026 PG&E household/export/electrical stress comparison.

Run: /usr/local/bin/python3 tools/run_residential_export_validation.py
Generated artifacts go to .cache/residential_export_validation (must be empty).
All household and circuit inputs are hypothetical, not customer observations.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.local_web.contract import DEFAULT_SITE_REQUEST, validate_request
from src.local_web.export_study import TARIFF, execute
from src.local_web.runtime import snapshot
from src.local_web.site_inputs import build_site_inputs
from src.local_web.worker import write_json
from src.opendss.residential_service import ResidentialService


CASES = {
    "daily_household": {"description": "Synthetic weekday/weekend household shape; reference service"},
    "evening_peak": {"description": "80% of each day's energy between 18:00 and 19:00; balanced reference service",
                     "evening_fraction": .8},
    "large_pv": {"description": "36 kW DC / 30 kW AC PV and 30 kW export limit; intentionally oversized for the reference service",
                 "pv_dc_kw": 36., "pv_ac_kw": 30.},
    "uneven_legs": {"description": "Evening-peak load; 85% L1–N, 5% L2–N, 10% at 240 V",
                    "evening_fraction": .8, "service": {"l1_load_fraction": .85, "l2_load_fraction": .05}},
    "long_service": {"description": "Evening-peak load; balanced legs and 150 m service instead of 30 m",
                     "evening_fraction": .8, "service": {"service_length_km": .15}},
}


def study_request(case="daily_household"):
    spec = CASES[case]
    request = deepcopy(DEFAULT_SITE_REQUEST)
    request.update(name="Synthetic July household · " + case.replace("_", " "),
                   start_date="2026-07-01", end_date="2026-07-31", timezone="America/Los_Angeles",
                   timestep_minutes=15, tariff_id=TARIFF, carbon_weight=0.,
                   degradation_cost_per_kWh=.01, include_degradation_in_optimization=False,
                   carbon_intensity_g_per_kWh=0., pv_capacity_kw=spec.get("pv_ac_kw", 3.),
                   pv_battery_connection="ac_coupled")
    request["site"]["utility"] = "pge"
    request["site_profile"] = dict(site_type="residential", subtype="house")
    request["load"] = dict(mode="synthetic", archetype="residential", total_energy_kWh=744.)
    request["solar"]["dc_capacity_kw"] = spec.get("pv_dc_kw", 3.)
    request["battery"] = dict(capacity_kWh=4., energy_kWh=.8, max_charge_kw=2., max_discharge_kw=2.,
                              SOC_min=.2, SOC_max=.8, charge_efficiency=.95, discharge_efficiency=.95)
    account = dict(utility="pge", generation_provider="pge", customer_class="residential",
                   billing_plan="E-ELEC", program="NBT", income_tier=3, application_year=2026,
                   pto_date="2026-04-01", next_true_up_date="2027-04-01",
                   cycle_start="2026-07-01", cycle_end="2026-07-31", storage="renewable_only",
                   reference="Hypothetical validation fixture; no actual customer enrollment claimed",
                   enrollment_confirmed=True, ordinary_account_confirmed=True, cycle_confirmed=True,
                   no_local_tax_confirmed=True, no_other_adjustments_confirmed=True, bonus_eligible_confirmed=True)
    request["solar_export"] = dict(account=account, opening_balance=dict(generation=0., delivery=0., bonus=0.),
                                    export_limit_kw=request["pv_capacity_kw"])
    return validate_request(request)


def concentrate_evening(frame, fraction):
    """Redistribute, never add, each local day's native energy for a stress test.

    Preserve the base shape outside 18:00–19:00; set a flat one-hour pulse.
    Uses actual interval counts on each local date, including DST days.
    """
    if not 0 < fraction < 1:
        raise ValueError("Evening energy fraction must lie strictly between zero and one.")
    result = frame.copy()
    index = pd.DatetimeIndex(result.timestamp)
    if index.tz is None or len(index) < 2 or not np.all(np.diff(index.asi8) == 900_000_000_000):
        raise ValueError("Stress load requires continuous timezone-aware 15-minute timestamps.")
    values = result.load_kw.to_numpy(dtype=float).copy()
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Stress load requires finite nonnegative power.")
    for day in np.unique(index.date):
        daily = index.date == day
        evening = daily & (index.hour == 18)
        rest = daily & ~evening
        if evening.sum() != 4 or not rest.any() or values[rest].sum() <= 0:
            raise ValueError("Stress redistribution requires a complete evening hour and nonzero remainder.")
        total = values[daily].sum()
        values[evening] = fraction * total / evening.sum()
        values[rest] *= (1 - fraction) * total / values[rest].sum()
    result["load_kw"] = values
    return result


def run_case(case, output, engine):
    spec = CASES[case]
    directory = output / case
    directory.mkdir()
    request = study_request(case)
    frame, replay, extra, provenance = build_site_inputs(request, directory)
    if "evening_fraction" in spec:
        frame = concentrate_evening(frame, spec["evening_fraction"])
    service = ResidentialService(**spec.get("service", {}))
    provenance["load"].update(native_load_energy_kWh=float(frame.load_kw.sum() * .25),
                              native_load_peak_kw=float(frame.load_kw.max()))
    provenance["validation_case"] = dict(id=case, **spec, residential_service=asdict(service),
                                        runner="tools/run_residential_export_validation.py",
                                        input_csv="normalized.csv", input_csv_is_authoritative=True)
    provenance["warnings"] = [w for w in provenance["warnings"] if not w.startswith("Grid carbon intensity")]
    provenance["warnings"] += [
        "Synthetic electrical stress case: " + spec["description"] + ". Not typical or measured appliance behavior.",
        "Carbon is not assessed in this offline bill-only comparison; the legacy zero input is not an emissions estimate.",
        "Reproduce stress cases with the named validation runner and normalized.csv; loading request.json alone does not apply the stress redistribution or network overrides.",
        "Battery dispatch uses historical perfect foresight for the entire cycle, not an implementable forecast or real-time controller.",
    ]
    provenance["carbon"]["scope"] = "Not assessed; unused in this bill-only validation"
    write_json(directory / "request.json", request)
    write_json(directory / "engine.json", engine)
    frame.to_csv(directory / "normalized.csv", index=False)
    provenance["validation_case"]["input_sha256"] = hashlib.sha256((directory / "normalized.csv").read_bytes()).hexdigest()
    for key, table in extra.items():
        table.to_csv(directory / (key + ".csv"), index=False)
    execute(directory, request, frame, provenance, pv_replay=replay, residential_service=service)
    comparison = pd.read_csv(directory / "comparison.csv")
    assert len(comparison) == 5 and (comparison.interval_count == 2976).all()
    assert np.isclose(frame.load_kw.sum() * .25, 744., rtol=0, atol=1e-8)
    for scenario in comparison.scenario:
        table = pd.read_csv(directory / ("dispatch-" + scenario.replace("_", "-") + ".csv"))
        assert np.isclose(table.native_load_kw.sum() * .25, 744., rtol=0, atol=1e-8)
        residual = (table.grid_import_kw + table.pv_output_kw + table.battery_discharge_kw
                    - table.native_load_kw - table.battery_charge_kw - table.grid_export_kw)
        assert residual.abs().max() < 1e-5
        assert (table.pv_available_kw - table.pv_output_kw - table.pv_curtailed_kw).abs().max() < 1e-5
    comparison.insert(0, "case", case)
    comparison.insert(1, "native_energy_kWh", float(frame.load_kw.sum() * .25))
    comparison.insert(2, "native_peak_kw", float(frame.load_kw.max()))
    return comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".cache" / "residential_export_validation")
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output directory must be empty; preserve existing validation artifacts.")
    args.output.mkdir(parents=True, exist_ok=True)
    engine = snapshot(ROOT, args.output)
    rows = []
    for case in CASES:
        print("Running " + case, flush=True)
        result = run_case(case, args.output, engine)
        rows.append(result)
        print(result[["scenario", "amount_due", "failed_intervals"]].to_string(index=False), flush=True)
    report = pd.concat(rows, ignore_index=True)
    report.to_csv(args.output / "summary.csv", index=False)
    # Network-only changes must leave every scheduled bill component unchanged.
    for case in ("uneven_legs", "long_service"):
        assert json.loads((args.output / case / "solar_bills.json").read_text()) == json.loads(
            (args.output / "evening_peak" / "solar_bills.json").read_text())
    assert report.loc[report.case == "daily_household", "all_intervals_feasible"].all()
    assert report.loc[report.case == "large_pv", "failed_intervals"].sum() > 0
    for case in ("uneven_legs", "long_service"):
        assert report.loc[report.case == case, "failed_intervals"].sum() > 0
    for name, digest in engine["files"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, "Source changed during run; rerun validation."
    write_json(args.output / "validation.json", dict(
        status="passed", cases=len(CASES), scenarios=len(report), intervals=int(report.interval_count.sum()),
        energy_kWh_per_case=744., all_dispatch_balances_checked=True, network_only_bills_unchanged=True,
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), engine_id=engine["id"],
        scope="Internal deterministic validation, not measured-bill or site validation. Infeasible stress results are expected."))
    print("Validation complete: " + str(args.output / "summary.csv"), flush=True)


if __name__ == "__main__":
    main()
