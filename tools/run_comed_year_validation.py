"""Reproduce two offline 2025 ComEd comparisons using the immutable study worker.

Uses the existing synthetic-load, clear-sky PV, billing, dispatch and OpenDSS
paths without substituting rates or market prices. Output is ignored study data.
The full-year MILP must satisfy the engine's existing optimality/time limits.
"""
from __future__ import annotations

import argparse
from calendar import monthrange
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.billing.comed_costs import calculate, compile_costs  # noqa: E402
from src.billing.comed_commercial import mkd_mask  # noqa: E402
from src.local_web.comed_simulation import defaults, prepare  # noqa: E402
from src.local_web.runtime import Application  # noqa: E402
from src.billing.comed_cycles import parse_cycles  # noqa: E402

SCENARIOS = ("grid_only", "pv_only", "pv_battery")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def request(kind):
    r = defaults(kind)
    r.update(name=f"ComEd 2025 {kind} BES full-year validation",
             start_date="2025-01-01", end_date="2025-12-31")
    r["account"].update(supply="BES", billing_month="2025-01-01",
                        ordinary_import_only_confirmed=True)
    if kind == "commercial":
        r["account"].update(previous_12_month_peak_kw=60.,
                            previous_calendar_year_peak_kw=60.,
                            previous_year_months_ge_100kw=0)
    r["load"].update(mode="synthetic", power_kw=3. if kind == "residential" else 60.,
        source="Deterministic generic residential/office weekday-weekend archetype; hypothetical native load, not measured or calibrated Illinois consumption")
    r["solar"].update(tilt_degrees=30., azimuth_degrees=180.,
                       system_losses_fraction=.14, inverter_efficiency=.96,
                       temperature_c=20., wind_speed_m_per_s=1.)
    # Shared defaults are 5/4 kW DC/AC residential and 40/35 kW commercial.
    capacity, power = (13.5, 5.) if kind == "residential" else (100., 30.)
    r["battery"].update(capacity_kWh=capacity, energy_kWh=capacity/2,
        SOC_min=.1, SOC_max=.9, max_charge_kw=power, max_discharge_kw=power,
        charge_efficiency=.95, discharge_efficiency=.95)
    r["operating_contract"].update(interconnection_confirmed=True,
        standard_tariff_confirmed=True, grid_charging_confirmed=True,
        reference="Hypothetical approved non-export account with ordinary BES import tariff; no special DER or standby charges")
    r["billing_cycles"] = [dict(start_date=str(date(2025, m, 1)),
        end_date=str(date(2025, m, monthrange(2025, m)[1])),
        billing_month=str(date(2025, m, 1)), kind="regular", charge_factors=None,
        source="Synthetic calendar-designated billing cycle for validation; not an actual meter-reading schedule")
        for m in range(1, 13)]
    prepare(r)
    return r


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(directory, r, engine_id):
    """Independently inspect every saved interval and monthly bill component."""
    result = json.loads((directory / "result.json").read_text())
    grid, expected_load, account, prices = prepare(r)
    index, dt = grid.index, grid.timestep_hours
    cycles = parse_cycles(r["billing_cycles"])
    require(len(index) == 17520 and dt == .5, "Unexpected full-year physical grid")
    require(result["engine_id"] == engine_id, "Worker used a different engine")
    require(result["total_usd"] is None and not result["is_complete_bill"], "Lost subtotal scope")
    require(result["ac_validation"]["all_intervals_feasible"], "Representative AC replay failed")
    require(all(x["checked_intervals"] == len(index) and x["failed_intervals"] == 0
                for x in result["ac_validation"]["scenarios"]), "Incomplete AC replay")
    inputs = pd.read_csv(directory / "inputs.csv")
    require(pd.DatetimeIndex(pd.to_datetime(inputs.timestamp, utc=True)).equals(index.tz_convert("UTC")), "Input timestamps changed")
    require(np.allclose(inputs.native_load_kw, expected_load, atol=1e-10, rtol=0), "Native load changed")
    costs = compile_costs(index, account, prices, cycles)
    comparison = pd.read_csv(directory / "comparison.csv").set_index("scenario")
    monthly, components, physics = [], [], []
    for scenario in SCENARIOS:
        require(result["optimization"][scenario]["cost_optimum_proven"], "Unproven primary optimum")
        d = pd.read_csv(directory / f"dispatch-{scenario}.csv")
        times = pd.DatetimeIndex(pd.to_datetime(d.timestamp, utc=True))
        require(times.equals(index.tz_convert("UTC")), "Dispatch timestamps incomplete")
        numeric = d.select_dtypes(include="number").to_numpy()
        require(np.isfinite(numeric).all(), "Nonfinite dispatch")
        require(np.allclose(d.native_load_kw, expected_load, atol=1e-10, rtol=0), "Scenario load differs")
        available = np.zeros(len(index)) if scenario == "grid_only" else inputs.pv_available_kw.to_numpy()
        require(np.allclose(d.pv_available_kw, available, atol=1e-10, rtol=0), "Scenario PV differs")
        c, discharge, soc = (d[k].to_numpy() for k in ("battery_charge_kw", "battery_discharge_kw", "battery_soc_kWh"))
        balance = float(np.max(np.abs(d.grid_import_kw+d.pv_output_kw+discharge-d.native_load_kw-c)))
        require(balance < 1e-5, "Interval power balance failed")
        require(np.min(d.grid_import_kw) >= -1e-7 and d.grid_export_kw.eq(0).all(), "Unexpected export/negative import")
        require(np.max(np.abs(d.pv_output_kw+d.pv_curtailed_kw-available)) < 1e-6, "PV energy balance failed")
        require(np.min(d.pv_curtailed_kw) >= -1e-7, "Negative curtailment")
        require(np.min(c) >= -1e-7 and np.min(discharge) >= -1e-7, "Negative battery power")
        exclusivity = float(np.max(np.minimum(c, discharge)))
        require(exclusivity < 1e-6, "Simultaneous battery charge/discharge")
        end = float(comparison.loc[scenario, "terminal_energy_kwh"])
        soc_error = 0.
        if scenario == "pv_battery":
            b = r["battery"]
            changes = dt*(c*b["charge_efficiency"]-discharge/b["discharge_efficiency"])
            soc_error = float(np.max(np.abs(np.r_[soc[1:], end]-soc-changes)))
            require(soc_error < 1e-5, "Battery state recursion failed")
            require(abs(soc[0]-b["energy_kWh"]) < 1e-5 and abs(end-b["energy_kWh"]) < 1e-5, "Initial/annual-terminal energy changed")
            require(soc.min() >= b["capacity_kWh"]*b["SOC_min"]-1e-5 and soc.max() <= b["capacity_kWh"]*b["SOC_max"]+1e-5, "SOC bounds failed")
            require(c.max() <= b["max_charge_kw"]+1e-6 and discharge.max() <= b["max_discharge_kw"]+1e-6, "Battery power limit failed")
        else:
            require(np.max(np.abs(np.r_[c, discharge, soc, end])) < 1e-7, "Absent battery has nonzero operation")
        bill = calculate(pd.Series(d.grid_import_kw.to_numpy(), index=index), account, prices, cycles)
        require(len(bill["cycles"]) == 12, "Incomplete year of bills")
        require(abs(bill["subtotal_usd"]-comparison.loc[scenario, "subtotal_usd"]) < .011, "Saved bill mismatch")
        difference = float(bill["subtotal_usd"]-costs.subtotal(d.grid_import_kw.to_numpy()))
        require(abs(difference) <= costs.rounding_bound_usd, "Annual objective/Decimal bill mismatch")
        require(abs(comparison.loc[scenario, "solver_gap_usd"]) < 1e-4, "Solver residual too large")
        for m, one in enumerate(bill["cycles"], 1):
            mask = index.month == m
            require(one["version_id"].endswith(f"_2025_{m:02}"), "Wrong monthly version")
            subtotal = sum((Decimal(str(x["amount_usd"])) for x in one["lines"]), Decimal(0))
            require(subtotal == Decimal(str(one["subtotal_usd"])), "Monthly itemized charges do not sum")
            require(abs(one["import_kwh"]-float(d.loc[mask, "grid_import_kw"].sum()*dt)) < 1e-5, "Monthly kWh mismatch")
            require(not any(x["name"] in ("capacity", "hourly_electricity_supply") for x in one["lines"]), "BES received wholesale/capacity charges")
            peak = None
            if r["site_profile"]["site_type"] == "commercial":
                eligible = mkd_mask(index[mask])
                peak = float(d.loc[mask, "grid_import_kw"].to_numpy()[eligible].max())
                require(abs(one["billed_mkd_kw"]-peak) < 1e-6, "Monthly demand measurement mismatch")
                line = next(x for x in one["lines"] if x["name"] == "distribution_demand")
                charge = (Decimal(str(peak))*Decimal(str(line["rate_usd"]))).quantize(Decimal(".01"), rounding="ROUND_HALF_UP")
                require(charge == Decimal(str(line["amount_usd"])), "Demand charge arithmetic mismatch")
            monthly.append(dict(case=r["site_profile"]["site_type"], scenario=scenario, month=f"2025-{m:02}",
                physical_intervals=int(mask.sum()), physical_hours=float(mask.sum()*dt),
                native_kwh=float(inputs.loc[mask, "native_load_kw"].sum()*dt),
                import_kwh=one["import_kwh"], subtotal_usd=one["subtotal_usd"], billed_mkd_kw=peak,
                version_id=one["version_id"], opening_battery_kwh=float(soc[np.flatnonzero(mask)[0]]),
                closing_battery_kwh=float(soc[np.flatnonzero(mask)[-1]+1]) if m<12 else end))
            for line in one["lines"]:
                require(line["source_documents"] and all(len(s["sha256"]) == 64 for s in line["source_documents"]), "Missing rate provenance")
                components.append(dict(case=r["site_profile"]["site_type"], scenario=scenario,
                    month=f"2025-{m:02}", name=line["name"], category=line["category"],
                    amount_usd=line["amount_usd"]))
        physics.append(dict(scenario=scenario, checked_intervals=len(index),
            max_power_balance_error_kw=balance, max_soc_recursion_error_kwh=soc_error,
            max_simultaneous_charge_discharge_kw=exclusivity,
            annual_rounding_difference_usd=difference, annual_rounding_bound_usd=costs.rounding_bound_usd))
    require(comparison.loc["pv_only", "subtotal_usd"] <= comparison.loc["grid_only", "subtotal_usd"]+.02, "PV-only worsens optimum")
    require(comparison.loc["pv_battery", "subtotal_usd"] <= comparison.loc["pv_only", "subtotal_usd"]+.02, "Battery worsens optimum")
    monthly = pd.DataFrame(monthly)
    monthly["billed_mkd_kw"] = pd.array(monthly["billed_mkd_kw"], dtype="Float64")
    require(monthly.loc[monthly.month == "2025-03", "physical_hours"].eq(743).all(), "Spring DST count incorrect")
    require(monthly.loc[monthly.month == "2025-11", "physical_hours"].eq(721).all(), "Fall DST count incorrect")
    return monthly, pd.DataFrame(components), physics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/".cache/comed_2025_year_validation")
    args = parser.parse_args()
    output = args.output.resolve()
    app = Application(output)  # Creates a new pin, or reuses an existing immutable pin.
    try:
        current_files = {p.relative_to(ROOT).as_posix(): digest(p) for p in (ROOT/"src").rglob("*.py")}
        require(current_files == app.engine["files"],
                "Output store pins a different source revision; choose a fresh --output directory. Existing pins are never refreshed by this tool.")
    except BaseException:
        app.close()
        raise
    manifest = {"year": 2025, "engine_id": app.engine["id"], "cases": [],
                "driver_sha256": digest(__file__),
                "scope": "Synthetic loads, clear-sky PV, non-export BES subtotals; historical perfect foresight with continuous annual SOC and annual terminal constraint; excludes taxes, franchise fees, capital costs and forecast-driven operation"}
    manifest["driver_path"] = "validation-driver-"+manifest["driver_sha256"][:12]+".py"
    (output/manifest["driver_path"]).write_bytes(Path(__file__).read_bytes())
    monthly, components, summaries, failures = [], [], [], []
    try:
        for kind in ("residential", "commercial"):
            r = request(kind)
            job = app.store.submit(r, app.engine)
            entry = {"case": kind, "study_id": job["id"], "status": "queued"}
            manifest["cases"].append(entry)
            last, started = None, time.monotonic()
            while True:
                state = app.store.get(job["id"])
                marker = (state["status"], state["progress"])
                if marker != last:
                    print(kind, *marker, flush=True); last = marker
                if state["status"] in ("completed", "failed", "cancelled"):
                    break
                time.sleep(1)
            entry.update(status=state["status"], elapsed_seconds=time.monotonic()-started)
            if state["status"] != "completed":
                entry["error"] = state.get("error"); failures.append(entry)
                print(json.dumps(entry), flush=True)
                continue
            directory = output/"runs"/job["id"]
            try:
                rows, lines, physics = audit(directory, r, app.engine["id"])
            except (AssertionError, ValueError) as exc:
                entry.update(validation="failed", error=str(exc)); failures.append(entry)
                print(json.dumps(entry), flush=True)
                continue
            monthly.append(rows); components.append(lines)
            comparison = pd.read_csv(directory/"comparison.csv")
            comparison.insert(0, "case", kind); summaries.append(comparison)
            entry.update(validation="passed", physics=physics,
                artifacts={p.name: digest(p) for p in directory.glob("*.csv")},
                request_sha256=digest(directory/"request.json"))
            print(comparison[["scenario", "subtotal_usd", "import_kwh", "battery_charge_kwh", "battery_discharge_kwh"]].to_string(index=False), flush=True)
    finally:
        app.close()
        (output/"validation.json").write_text(json.dumps(manifest, indent=2)+"\n")
    if summaries:
        pd.concat(summaries).to_csv(output/"annual-comparison.csv", index=False)
        pd.concat(monthly).to_csv(output/"monthly-comparison.csv", index=False)
        details = pd.concat(components)
        details.to_csv(output/"monthly-components.csv", index=False)
        annual = details.groupby(["case", "scenario", "name", "category"], as_index=False).amount_usd.sum()
        baseline = annual.loc[annual.scenario == "grid_only"].set_index(["case", "name"]).amount_usd
        annual["savings_vs_grid_usd"] = [baseline.loc[(row.case,row["name"])]-row.amount_usd for _,row in annual.iterrows()]
        annual.to_csv(output/"annual-components.csv", index=False)
    if failures:
        raise SystemExit("Full-year validation failed; inspect validation.json. No relaxed or monthly substitute was used.")


if __name__ == "__main__":
    main()
