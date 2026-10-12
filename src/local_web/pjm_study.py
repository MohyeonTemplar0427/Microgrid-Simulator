"""Schema 8 regional candidate; immutable inputs and ordinary queued workers."""
from dataclasses import asdict
from datetime import date
import json
from pathlib import Path
import numpy as np
import pandas as pd
from ..regional.account import RegionalAccount
from ..billing.dominion import PLAN, SOURCE_URLS, bill, validate_account, validate_index
from ..dispatch.battery import Battery
from ..timeseries.interval_table import build_interval_index


def defaults():
    return {"schema_version": 8, "name": "Untitled study", "start_date": "2026-09-01", "end_date": "2026-09-30",
            "timezone": "America/New_York", "timestep_minutes": 30,
            "site": {"latitude": 37.6, "longitude": -77.5, "label": "Hypothetical Henrico commercial facility"},
            "regional_account": asdict(RegionalAccount("dominion_energy_virginia", "VA", "dominion_bundled", "commercial",
                "dominion_gs2t", "PJM", "DOM", None, {"kind": "hypothetical_case", "reference": "Synthetic representative case, not an actual utility account"})),
            "account": {"locality": "henrico", "eligibility_confirmed": True, "history_peaks_kw": [90.]*11,
                "power_factor": .95, "metering_side": "secondary", "special_riders": False,
                "parallel_operation_approved": True, "contract_demand_kw": 90., "minimum_contract_charge": 0.,
                "billing_month": 9, "facility": "commercial_non_datacenter"},
            "load": {"mode": "synthetic_late_commercial", "scale": 1.},
            "solar": {"dc_capacity_kw": 40., "inverter_ac_kw": 35., "tilt": 25., "azimuth": 180.},
            "battery": {"capacity_kWh": 80., "energy_kWh": 40., "max_charge_kw": 20., "max_discharge_kw": 20.,
                        "SOC_min": .2, "SOC_max": .8, "charge_efficiency": .95, "discharge_efficiency": .95},
            "weather": None, "market_data": None, "degradation_cost_per_kWh": .03,
            "include_degradation_in_optimization": False, "export_mode": "non_export"}


def capabilities():
    version = PLAN.versions[0]
    return {"status": "candidate", "schema_version": 8, "defaults": defaults(), "source_urls": SOURCE_URLS,
            "effective_start": str(version.effective_start), "effective_end": str(version.effective_end),
            "full_historical_year_supported": False,
            "scope": "Local-only Henrico bundled GS-2T, approved non-export parallel service, existing qualifying demand history. Low-load-factor storage scope proven before solving.",
            "market_permissions": "PJM data and derived market outputs stay private/internal-use; no public downloads."}


def validate(r):
    if not isinstance(r, dict) or set(r) != set(defaults()) or type(r.get("schema_version")) is not int or r["schema_version"] != 8:
        raise ValueError("Supply exactly the schema 8 PJM candidate fields.")
    if not isinstance(r["name"], str) or not 1 <= len(r["name"].strip()) <= 120:
        raise ValueError("Provide a temporary or saved study name.")
    if r["timezone"] != "America/New_York" or r["timestep_minutes"] != 30 or r["export_mode"] != "non_export":
        raise ValueError("The Dominion candidate requires Eastern time, 30-minute intervals and non-export operation.")
    region = RegionalAccount(**r["regional_account"]).validate_dominion()
    validate_account(r["account"])
    from .contract import number
    site = r["site"]
    if not isinstance(site, dict) or set(site) != {"latitude", "longitude", "label"} or not isinstance(site["label"], str):
        raise ValueError("Provide site coordinates and a label; this is not a territory lookup.")
    number(site["latitude"], "Latitude", -90, 90); number(site["longitude"], "Longitude", -180, 180)
    grid = build_interval_index(r["start_date"], r["end_date"], r["timezone"], 30)
    validate_index(grid.index)
    if not isinstance(r["load"], dict) or set(r["load"]) != {"mode", "scale"} or r["load"]["mode"] != "synthetic_late_commercial":
        raise ValueError("Choose the labeled synthetic reference facility; measured interval loads are separate future work.")
    number(r["load"]["scale"], "Load scale", .1, 5)
    solar = r["solar"]
    if not isinstance(solar, dict) or set(solar) != {"dc_capacity_kw", "inverter_ac_kw", "tilt", "azimuth"}:
        raise ValueError("Provide PV and inverter ratings and orientation.")
    for key, bounds in {"dc_capacity_kw": (0, 500), "inverter_ac_kw": (.001, 500), "tilt": (0, 90), "azimuth": (0, 359.999)}.items():
        number(solar[key], key, *bounds)
    Battery(**r["battery"])
    number(r["degradation_cost_per_kWh"], "Wear", 0, 10)
    if type(r["include_degradation_in_optimization"]) is not bool:
        raise ValueError("Choose whether to include battery wear.")
    weather = r["weather"]
    if not isinstance(weather, dict) or set(weather) != {"provider", "raw_json", "request", "retrieved_at"} or weather["provider"] != "open_meteo_era5" or not isinstance(weather["raw_json"], str) or len(weather["raw_json"].encode()) > 8*1024*1024:
        raise ValueError("Retrieve matching historical ERA5 weather; missing weather is not replaced with clear sky.")
    wanted = {"latitude": site["latitude"], "longitude": site["longitude"], "models": "era5", "timezone": "UTC", "wind_speed_unit": "ms"}
    if not isinstance(weather["request"], dict) or any(weather["request"].get(k) != v for k, v in wanted.items()) or pd.Timestamp(weather["retrieved_at"]).tzinfo is None:
        raise ValueError("Weather request metadata must match the configured site, model, units and time standard.")
    from ..profiles.era5 import parse_era5
    parse_era5(weather["raw_json"], grid, site["latitude"], site["longitude"])
    if r["market_data"] is not None:
        if region.wholesale_pricing_location is None or not isinstance(r["market_data"], dict) or set(r["market_data"]) != {"csv", "metadata"}:
            raise ValueError("Supply a separately verified pricing location and PJM CSV/provenance.")
        from ..signal_pipeline.providers.pjm import PJMProvider
        PJMProvider.import_historical_file(r["market_data"]["csv"], r["market_data"]["metadata"], grid.start, grid.end, region.wholesale_pricing_location)
    return r


def inputs(r):
    from ..profiles import WeatherDerivedPV, WeatherDerivedPVConfiguration
    from ..profiles.era5 import parse_era5
    grid = build_interval_index(r["start_date"], r["end_date"], r["timezone"], 30)
    weather, provenance = parse_era5(r["weather"]["raw_json"], grid, r["site"]["latitude"], r["site"]["longitude"])
    s = r["solar"]
    production = WeatherDerivedPV(WeatherDerivedPVConfiguration(latitude=r["site"]["latitude"], longitude=r["site"]["longitude"],
        rated_pv_capacity_kw=s["dc_capacity_kw"], inverter_ac_capacity_kw=s["inverter_ac_kw"], tilt_degrees=s["tilt"], azimuth_degrees=s["azimuth"]),
        weather_data=weather, weather_source=provenance["source"]).build_detailed(grid)
    h, weekday = grid.index.hour, grid.index.dayofweek < 5
    # Explicit study assumption: evening-operating commercial premises,
    # 8 kW closed, 30 kW daytime, 50 kW evenings, 90 kW 20:00–21:00;
    # weekend open demand 16 kW. No appliance or calibration claim.
    load = np.where(weekday, np.where((h>=7)&(h<19), 30., np.where((h>=19)&(h<22), 50., 8.)), np.where((h>=9)&(h<20),16.,8.))
    load = np.where(weekday&(h==20),90.,load)*r["load"]["scale"]
    frame = pd.DataFrame({"timestamp": grid.index, "native_load_kw": load, "pv_available_kw": production.pv_available_kw.to_numpy()})
    provenance.update(retrieved_at=r["weather"]["retrieved_at"], request=r["weather"]["request"],
                      load_kind="synthetic", load_assumptions=r["load"], pv_model="existing WeatherDerivedPV, AC coupled")
    return frame, weather, production, provenance


def execute(directory, r):
    from .worker import write_json, summarize_ac_validation
    from .table_store import save_table
    from ..dispatch.dominion import optimize
    from ..opendss.opendss_handoff import create_opendss_handoff
    from ..opendss.opendss_analysis import replay_dispatch_timeseries
    directory = Path(directory)
    validate(r)
    frame, weather, production, provenance = inputs(r)
    write_json(directory/"progress.json", {"message": "Comparing retail bills and perfect-foresight storage"})
    index = pd.DatetimeIndex(frame.timestamp)
    baseline, solar = frame.copy(), frame.copy()
    for out, output in ((baseline, np.zeros(len(frame))), (solar, np.minimum(frame.native_load_kw, frame.pv_available_kw))):
        out["pv_output_kw"] = output
        out["grid_import_kw"] = out.native_load_kw-output
        out["grid_export_kw"] = 0.
        out["pv_curtailed_kw"] = out.pv_available_kw-output
        out["battery_charge_kw"] = out["battery_discharge_kw"] = 0.
        out["battery_soc_kWh"] = r["battery"]["energy_kWh"]
    optimized = optimize(frame, r["account"], r["battery"], r["degradation_cost_per_kWh"], r["include_degradation_in_optimization"])
    schedules = {"grid_only": baseline, "pv_only": solar, "pv_battery": optimized["dispatch"]}
    bills = {key: bill(index, out.grid_import_kw, r["account"]) for key, out in schedules.items()}
    rows, lines, tables, ac = [], [], [], {}
    def save(key, label, table):
        # The shared result viewer labels timestamp columns as UTC. Preserve
        # instants explicitly; billing and PV continue to use Eastern indexes.
        table = table.copy()
        if "timestamp" in table:
            table["timestamp"] = pd.to_datetime(table.timestamp, utc=True)
        save_table(directory, key, [c.replace("_", " ") for c in table.columns], table)
        tables.append({"id": key, "label": label, "row_count": len(table)})
    for key, out in schedules.items():
        billed = bills[key]
        rows.append({"scenario": key, "utility_bill": billed["total"], "savings_vs_grid": bills["grid_only"]["total"]-billed["total"],
            "import_kWh": billed["import_kWh"], "measured_peak_kw": billed["peak_kw"], "on_peak_kw": billed["on_peak_kw"],
            "distribution_contract_kw": billed["distribution_demand_kw"], "load_factor": billed["load_factor"],
            "degradation_cost": optimized["degradation_cost"] if key=="pv_battery" else 0.,
            "strategy": "historical perfect foresight" if key=="pv_battery" else "instantaneous self consumption" if key=="pv_only" else "grid supply"})
        lines.extend({"scenario": key, "component": k, "charge": v, "savings_vs_grid": bills["grid_only"]["lines"][k]-v} for k,v in billed["lines"].items())
        replay = out.rename(columns={"native_load_kw": "load_kw", "pv_output_kw": "pv_kw"})
        replay["load_power_factor"] = r["account"]["power_factor"]
        handoff = create_opendss_handoff(replay, timestep_minutes=30, expected_timezone=r["timezone"])
        handoff["load_power_factor"] = r["account"]["power_factor"]
        ac[key] = replay_dispatch_timeseries(handoff, battery=Battery(**r["battery"]), pv_capacity_kw=r["solar"]["inverter_ac_kw"])
        rows[-1]["all_intervals_feasible"] = bool(ac[key].feasible.all())
        save("ac-"+key, "Representative AC replay · "+key, ac[key])
        save("dispatch-"+key, "Dispatch · "+key, out)
    save("comparison", "Scenario comparison", pd.DataFrame(rows))
    save("billing-components", "Itemized bill and savings", pd.DataFrame(lines))
    save("inputs", "Native load and available PV", frame)
    save("weather", "Historical gridded weather", weather)
    save("ac-summary", "Representative OpenDSS replay", pd.DataFrame([{
        "scenario": k, "checked_intervals": len(v), "feasible_intervals": int(v.feasible.sum()),
        "minimum_voltage_pu": float(v.minimum_voltage_pu.min()), "maximum_voltage_pu": float(v.maximum_voltage_pu.max()),
        "maximum_line_loading_percent": float(v.line_loading_percent.max()),
        "maximum_transformer_loading_percent": float(v.transformer_loading_percent.max()),
        "feeder_loss_kWh": float(v.feeder_real_loss_kw.sum()*.5),
        "transformer_loss_kWh": float(v.transformer_real_loss_kw.sum()*.5),
        "replayed_pcc_import_kWh": float(v.pcc_grid_import_kw.sum()*.5)} for k,v in ac.items()]))
    market = {"status": "not supplied", "used_for_retail_billing": False}
    if r["market_data"] is not None:
        from ..signal_pipeline.providers.pjm import PJMProvider
        observations, market = PJMProvider.import_historical_file(r["market_data"]["csv"], r["market_data"]["metadata"], index[0], index[-1]+pd.Timedelta(minutes=30), r["regional_account"]["wholesale_pricing_location"])
        observations.to_csv(directory/"private-pjm-market.csv", index=False)
        market.update(status="validated private historical import", used_for_retail_billing=False)
    priority = {"comparison": 0, "billing-components": 1, "ac-summary": 2}
    tables.sort(key=lambda t: priority.get(t["id"], 3))
    write_json(directory/"result.json", {"engine_id": json.loads((directory/"engine.json").read_text())["id"], "tables": tables,
        "regional_account": r["regional_account"], "tariff_version": PLAN.versions[0].tariff_id, "source_urls": SOURCE_URLS,
        "provenance": provenance, "market_data": market, "objective_gap": optimized["objective_gap"], "ac_validation": summarize_ac_validation(ac),
        "warnings": ["Candidate only; full historical-year tariff coverage is not yet verified.",
            "Facility load and prior demand history are synthetic study assumptions, not measured data.",
            "Same confirmed parallel-service contract is retained for all counterfactual scenarios; distribution demand savings are consequently zero.",
            "Bundled generation includes capacity recovery; base transmission plus Rider T1 recover transmission. No wholesale LMP, capacity PLC or transmission NSPL charge is added.",
            "Storage uses historical perfect foresight; this is an operating-cost benchmark, not a deployable forecast/control strategy. PV-only uses instantaneous self-consumption.",
            "No export compensation, capital cost, carbon claim or dynamic/site-specific validation.",
            "OpenDSS uses the representative balanced 12.47 kV / 480 V circuit and 750 kVA transformer; inverter kVA equals AC kW, Q=0. Feeder losses are reported by replay, not fed back into the ideal-meter tariff optimizer.",
            provenance["sampling"]]})
    write_json(directory/"progress.json", {"message": "Results saved; inspect the bill breakdown and representative circuit replay"})
