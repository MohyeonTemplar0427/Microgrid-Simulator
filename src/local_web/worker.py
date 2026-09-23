"""Execute one offline study in a fresh process, from a saved source snapshot."""

from datetime import date
import hashlib
import json
from pathlib import Path
import sys

from .contract import validate_request
from ..billing.services import SERVICES, tariff_service


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, allow_nan=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def capabilities():
    from .socal_study import capabilities as socal_capabilities
    from .municipal_service import capabilities as municipal_capabilities
    from ..simulation.interface_analysis import retail_tariff_ids_for_region
    from ..billing import get_tariff
    from .contract import DEFAULT_SITE_REQUEST, DEFAULT_CANDIDATE_REQUEST, NSRDB_YEARS
    from ..equipment.ess import search
    from .site_profile import SITE_OPTIONS, SERVICE_CLASSES
    from .carbon import REGION_MAPPINGS
    return {"socal": socal_capabilities(), "carbon_regions": REGION_MAPPINGS, "site_options": SITE_OPTIONS, "service_classes": SERVICE_CLASSES, "municipal": municipal_capabilities(), "services": SERVICES, "candidate_defaults": DEFAULT_CANDIDATE_REQUEST, "ess_catalog": search(), "annual_orientation": True, "site_defaults": DEFAULT_SITE_REQUEST, "nsrdb_years": NSRDB_YEARS, "solar_export": {"program":"pge_nbt_monthly","scope":"Monthly comparison only; annual true-up and NSC not implemented"}, "tariffs": [
        {"id": key, "label": getattr(get_tariff(key), "name", key),
         "service": tariff_service(key),
         "notes": get_tariff(key).notes,
         "effective_start": str(get_tariff(key).effective_start),
         "effective_end": str(get_tariff(key).effective_end) if get_tariff(key).effective_end else None}
        for key in (*retail_tariff_ids_for_region("caiso_np15"), "pge_e_elec_residential_tier3_bundled_2026_06_01")
    ]}


def execute(directory):
    import pandas as pd
    from ..dispatch.battery import Battery
    from ..simulation.model_specifications import MicrogridSpecification
    from ..simulation.interface_analysis import run_integrated_csv_analysis, RESULT_TABLE_COLUMNS

    directory = Path(directory)
    request = validate_request(json.loads((directory / "request.json").read_text()))
    if request["schema_version"] == 6:
        from .socal_study import execute as execute_socal
        execute_socal(directory, request)
        return
    if request["schema_version"] == 5:
        from .grid_only import execute as execute_grid_only
        return execute_grid_only(directory, request)
    if request["schema_version"] == 4:
        from .municipal_study import execute_study
        return execute_study(directory, request)
    source = directory / "input.csv"
    site_run = request["schema_version"] >= 2
    if not site_run and hashlib.sha256(source.read_bytes()).hexdigest() != request["dataset_id"]:
        raise ValueError("Saved input checksum does not match the study request.")
    if request["tariff_id"] not in {None, *(t["id"] for t in capabilities()["tariffs"])}:
        raise ValueError("This engine snapshot does not support the selected tariff.")

    def progress(message):
        write_json(directory / "progress.json", {"message": message})

    progress("Validating the study horizon and input intervals")
    extra_tables, provenance, replay = {}, {}, None
    if site_run:
        from .site_inputs import build_site_inputs
        progress("Building weather-derived solar generation and building load")
        frame, replay, extra_tables, provenance = build_site_inputs(request, directory)
    else:
        frame = pd.read_csv(source)
    # UTC serialization avoids pandas' mixed-offset object dtype on autumn DST.
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    start = pd.Timestamp(request["start_date"], tz=request["timezone"])
    end = pd.Timestamp(request["end_date"], tz=request["timezone"]) + pd.DateOffset(days=1)
    expected = pd.date_range(start, end, freq=f'{request["timestep_minutes"]}min', inclusive="left")
    selected = frame.loc[(frame.timestamp >= start) & (frame.timestamp < end)].copy()
    if not pd.DatetimeIndex(selected.timestamp).equals(expected.tz_convert("UTC")):
        raise ValueError("CSV must cover every study interval exactly once, in order, at the selected resolution; no filling or resampling is applied.")
    pv_column = "pv_available_kw" if "pv_available_kw" in selected else "pv_kw"
    load_column = "native_load_kw" if "native_load_kw" in selected else "load_kw"
    if selected[pv_column].max() > request["pv_capacity_kw"] + 1e-8:
        raise ValueError("PV AC capacity must be at least the largest available PV value in the selected CSV intervals.")
    selected.to_csv(directory / "normalized.csv", index=False)
    if "solar_export" in request:
        from .export_study import execute as execute_export
        execute_export(directory, request, selected, provenance)
        return
    specification = MicrogridSpecification(
        battery=Battery(**request["battery"]),
        pv_capacity_kw=request["pv_capacity_kw"], load_kw=float(selected[load_column].max()),
        pv_replay=replay,
    )
    result = run_integrated_csv_analysis(
        specification, directory / "normalized.csv",
        start_date=request["start_date"],
        number_of_days=(date.fromisoformat(request["end_date"]) - date.fromisoformat(request["start_date"])).days + 1,
        timestep_minutes=request["timestep_minutes"], expected_timezone=request["timezone"],
        selected_scenarios=tuple(request["strategies"]), carbon_weights=(request["carbon_weight"],),
        degradation_cost_per_kWh=request["degradation_cost_per_kWh"],
        tariff_id=request["tariff_id"], progress_callback=progress,
    )
    labels = dict(RESULT_TABLE_COLUMNS)
    labels.update({
        "ghi_w_per_m2": "Global horizontal irradiance (W/m²)",
        "dni_w_per_m2": "Direct normal irradiance (W/m²)",
        "dhi_w_per_m2": "Diffuse horizontal irradiance (W/m²)",
        "temperature_c": "Air temperature (°C)", "wind_speed_m_per_s": "Wind speed (m/s)",
        "solar_zenith_degrees": "Solar zenith (°)", "solar_azimuth_degrees": "Solar azimuth (°)",
        "plane_of_array_irradiance_w_per_m2": "Panel irradiance (W/m²)",
        "estimated_cell_temperature_c": "Estimated cell temperature (°C)",
        "pv_module_dc_power_kw": "Module DC power (kW)",
        "pv_dc_after_system_losses_kw": "DC after system losses (kW)",
        "pv_ac_before_clipping_kw": "AC before clipping (kW)",
        "pv_inverter_clipping_kw": "Inverter clipping (kW)",
        "pv_available_kw": "Available PV AC power (kW)",
    })
    tables = []

    def save_table(key, label, table):
        # pandas emits JSON null for unavailable numeric diagnostics, never NaN.
        payload = json.loads(table.to_json(orient="split", index=False, date_format="iso", double_precision=15))
        payload["labels"] = [labels.get(c, c.replace("_", " ")) for c in payload["columns"]]
        write_json(directory / f"{key}.json", payload)
        table.to_csv(directory / f"{key}.csv", index=False)
        tables.append({"id": key, "label": label, "row_count": len(table)})

    save_table("comparison", "Scenario comparison", result.comparison)
    billing_columns = [c for c in result.comparison if c in {
        "scenario", "energy_cost", "demand_charge", "customer_charge", "export_credit",
        "cleanpowersf_generation_charge", "pge_delivery_charge", "pcia_charge", "franchise_fee_charge",
        "hetch_hetchy_energy_charge", "hetch_hetchy_premium_charge",
        "cca_generation_charge", "cca_product_premium_charge", "cca_vintage_adjustment_charge",
        "total_utility_charge", "total_explicit_cost", "billed_peak_kw", "degradation_cost",
    }]
    save_table("costs", "Cost summary", result.comparison[billing_columns])
    if site_run:
        save_table("inputs", "Simulation inputs", selected)
        for key, table in extra_tables.items():
            save_table(key, {"weather": "Weather · irradiance, temperature & wind", "pv": "Solar generation · model diagnostics"}[key], table)
    run = next(iter(result.runs_by_carbon_weight.values()))
    for scenario, table in run.dispatch_scenarios.items():
        save_table(f"dispatch-{scenario}", f"Dispatch · {scenario.replace('_', ' ')}", table)
    for scenario, table in run.powerflow_scenarios.items():
        save_table(f"ac-{scenario}", f"AC validation · {scenario.replace('_', ' ')}", table)
    warnings = list(result.warnings) + [
        "AC replay uses the representative balanced 12.47 kV / 480 V network and 750 kVA transformer.",
        "CSV load and PV values are used directly. PV capacity sets the AC rating; it does not scale the CSV profile.",
    ]
    if site_run:
        warnings = [w for w in warnings if not w.startswith(("CSV load and PV", "Dispatch was optimized against the price column"))]
        warnings.extend(provenance["warnings"])
    if request.get("ess"):
        warnings.extend(request["ess"]["assumptions"])
    for _, row in result.comparison.iterrows():
        if row.get("feasible_intervals", 0) < row.get("interval_count", 0):
            count = int(row["interval_count"] - row["feasible_intervals"])
            warnings.append(f"{row['scenario']}: {count} interval(s) did not pass electrical feasibility checks. Inspect this scenario's AC validation table.")
    if request["tariff_id"] is None and not site_run:
        warnings.append("Costs use CSV energy prices plus battery degradation; no utility tariff bill is calculated.")
    write_json(directory / "result.json", {
        "schema_version": request["schema_version"], "tables": tables, "warnings": warnings,
        "engine": json.loads((directory / "engine.json").read_text()),
        "dataset_sha256": request.get("dataset_id", hashlib.sha256((directory / "normalized.csv").read_bytes()).hexdigest()), "request": request,
        "input_provenance": provenance, "ess": request.get("ess"), "solar_optimization": request.get("solar_optimization"),
    })
    progress("Results saved")


def main():
    if sys.argv[1] == "capabilities":
        print(json.dumps(capabilities()))
        return
    if sys.argv[1] == "candidate":
        directory = Path(sys.argv[2])
        task = json.loads((directory / "resource-request.json").read_text())
        try:
            if task["kind"] in ("utility-resolution", "municipal-eligibility", "municipal-bill"):
                from .municipal_service import execute as municipal_execute
                result = municipal_execute(task["kind"], task["request"])
            elif task["kind"] == "ess":
                from ..equipment.ess import resolve
                result = resolve(**task["request"])
            else:
                from .solar_orientation import optimize
                result = optimize(directory, task["request"]["study"])
            write_json(directory / "resource.json", result)
        except (ValueError, TypeError, KeyError) as exc:
            write_json(directory / "error.json", {"error": str(exc)})
            raise SystemExit(1) from None
        return
    if sys.argv[1] == "resource":
        from .site_inputs import resolve_location, retrieve_weather
        directory = Path(sys.argv[2])
        task = json.loads((directory / "resource-request.json").read_text())
        try:
            result = resolve_location(task["request"]["query"]) if task["kind"] == "location" else retrieve_weather(directory, task["request"])
            write_json(directory / "resource.json", result)
        except Exception:
            # Provider exceptions can embed credential-bearing request URLs.
            write_json(directory / "error.json", {"error": "Location/weather retrieval failed. Check the location, provider availability, and (for NSRDB) credentials and coverage. No substitute weather was used."})
            raise SystemExit(1) from None
        return
    directory = Path(sys.argv[1])
    try:
        execute(directory)
    except Exception as exc:
        write_json(directory / "error.json", {"error": f"{type(exc).__name__}: {exc}"})
        raise


if __name__ == "__main__":
    main()
