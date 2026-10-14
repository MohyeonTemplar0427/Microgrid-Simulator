"""Schema 10: ComEd in the main location/PV/ESS study workflow.

Schema 9 remains an unchanged meter-import billing replay. Here native demand
is projected through an explicitly confirmed non-export operating contract.
"""
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .comed_study import defaults as bill_defaults, capabilities as bill_capabilities, parse_prices, _csv_series
from .contract import DEFAULT_SITE_REQUEST, number
from .site_profile import customer_class
from ..billing.comed_residential import ComEdResidentialAccount, _month_grid, _numeric_series
from ..billing.comed_commercial import ComEdCommercialAccount
from ..billing.comed_costs import calculate
from ..dispatch.battery import Battery
from ..timeseries import build_interval_index


def defaults(kind="residential"):
    old = bill_defaults(kind)
    common = deepcopy(DEFAULT_SITE_REQUEST)
    return {"schema_version": 10, "name": "Untitled study", "site": {
        "latitude": 41.8781, "longitude": -87.6298, "label": "Hypothetical Illinois site", "utility": "comed"},
        "site_profile": {"site_type": kind, "subtype": "house" if kind == "residential" else None},
        "regional_account": {"distribution_utility": "comed", "state_jurisdiction": "IL",
            "retail_supplier": "comed", "grid_operator": "PJM", "transmission_zone": "COMED",
            "verification_kind": "hypothetical_case", "reference": "Explicit hypothetical ComEd account; no territory lookup"},
        "account": old["account"], "prices": None, "start_date": "2026-09-01", "end_date": "2026-09-30",
        "timezone": "America/Chicago", "timestep_minutes": 30,
        "load": {"mode": "constant", "power_kw": 1. if kind == "residential" else 20.,
                 "archetype": "residential" if kind == "residential" else "office", "csv": None,
                 "source": "Synthetic native demand assumption, not measured usage", "native_basis_confirmed": False},
        "solar": {**common["solar"], "dc_capacity_kw": 5. if kind == "residential" else 40.},
        "pv_capacity_kw": 4. if kind == "residential" else 35., "weather_source": "clear_sky", "weather_id": None,
        "battery": {**common["battery"], "capacity_kWh": 10., "energy_kWh": 5., "max_charge_kw": 3., "max_discharge_kw": 3.},
        "ess": None, "degradation_cost_per_kWh": .03, "include_degradation_in_optimization": False,
        "operating_contract": {"mode": "approved_non_export", "interconnection_confirmed": False,
            "standard_tariff_confirmed": False, "grid_charging_confirmed": False, "reference": ""}}


def capabilities():
    return {"schema_version": 10, "defaults": {k: defaults(k) for k in ("residential", "commercial")},
            "billing_months": bill_capabilities()["billing_months"],
            "billing_months_by_supply": bill_capabilities()["billing_months_by_supply"],
            "billing_cycle_support": True,
            "scope": "Non-export ComEd subtotals; only listed, complete verified billing-month composites. Documented meter cycles or calendar studies; short-service allocations require explicit evidence; local candidate only"}


def prepare(r):
    if not isinstance(r, dict) or set(r)-{"billing_cycles"} != set(defaults()) or type(r.get("schema_version")) is not int or r["schema_version"] != 10:
        raise ValueError("Supply exactly the ComEd simulation schema 10 fields.")
    if not isinstance(r["name"], str) or not 1 <= len(r["name"].strip()) <= 120:
        raise ValueError("Supply a draft or saved study name.")
    kind = customer_class(r["site_profile"])
    if r["timezone"] != "America/Chicago" or type(r["timestep_minutes"]) is not int or r["timestep_minutes"] not in ((15, 30, 60) if kind == "residential" else (15, 30)):
        raise ValueError("ComEd uses Central time and 15/30-minute commercial demand; hourly commercial inputs are unsupported.")
    region = r["regional_account"]
    expected = {"distribution_utility": "comed", "state_jurisdiction": "IL", "retail_supplier": "comed",
                "grid_operator": "PJM", "transmission_zone": "COMED"}
    if (not isinstance(region, dict) or set(region) != set(defaults(kind)["regional_account"])
            or any(region[k] != v for k, v in expected.items())
            or region["verification_kind"] not in ("hypothetical_case", "electricity_bill", "utility_confirmation")
            or not isinstance(region["reference"], str) or not 1 <= len(region["reference"].strip()) <= 500):
        raise ValueError("Confirm ComEd distribution and supply separately from PJM or a city label; document service or a hypothetical case.")
    site = r["site"]
    if not isinstance(site, dict) or set(site) != set(defaults()["site"]) or site["utility"] != "comed" or not isinstance(site["label"], str) or not site["label"].strip():
        raise ValueError("Supply explicit ComEd site coordinates and a label.")
    number(site["latitude"], "Latitude", -90, 90); number(site["longitude"], "Longitude", -180, 180)
    a = r["account"]
    if not isinstance(a, dict) or set(a) != set(bill_defaults(kind)["account"]):
        raise ValueError("Supply the exact account facts for this customer class.")
    try:
        month = date.fromisoformat(a["billing_month"])
        grid = build_interval_index(r["start_date"], r["end_date"], r["timezone"], r["timestep_minutes"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Supply valid ComEd service dates and the confirmed utility billing month.") from exc
    from ..billing.comed_cycles import parse_cycles
    cycles = parse_cycles(r.get("billing_cycles"))
    if cycles is None:
        _month_grid(grid.index, month)
    cls = ComEdResidentialAccount if kind == "residential" else ComEdCommercialAccount
    account = cls(**{**a, "billing_month": month})
    prices = parse_prices(r["prices"], grid.index)
    # Authoritative validation covers eligibility, historical account facts,
    # applicable versions, external price coverage and fixed capacity charges.
    calculate(pd.Series(0., index=grid.index), account, prices, cycles)
    load = r["load"]
    if not isinstance(load, dict) or set(load) != set(defaults(kind)["load"]) or not isinstance(load["source"], str) or not 1 <= len(load["source"].strip()) <= 500 or type(load["native_basis_confirmed"]) is not bool:
        raise ValueError("Supply a labeled native-load source and basis.")
    from ..profiles import ConstantLoad, SyntheticLoad, BuildingArchetype, LoadScaling, CSVLoad
    if load["mode"] == "csv":
        if load["native_basis_confirmed"] is not True or load["power_kw"] is not None or load["archetype"] is not None:
            raise ValueError("Confirm native consumption before PV/storage; meter purchases cannot silently become native load or carry scaling.")
        series = _csv_series(load["csv"], "native_load_kw")
        if not series.index.equals(grid.index.tz_convert("UTC")):
            raise ValueError("Native-load CSV must match the exact complete study grid; no resampling or gap filling.")
        _numeric_series(series, grid.index.tz_convert("UTC"), "native load", nonnegative=True)
        values = CSVLoad(pd.DataFrame({"timestamp": series.index, "native_load_kw": series.values}), load_column="native_load_kw").build_load_kw(grid)
    elif load["mode"] in ("constant", "synthetic"):
        if load["csv"] is not None:
            raise ValueError("A synthetic assumption must not silently ignore a load file.")
        number(load["power_kw"], "Native power", 0, 100000)
        allowed = ("residential", "multifamily") if kind == "residential" else ("office", "retail", "school", "industrial")
        if load["archetype"] not in allowed:
            raise ValueError("Choose a generic synthetic profile appropriate to the account; no California profile is assigned.")
        model = ConstantLoad(load["power_kw"]) if load["mode"] == "constant" else SyntheticLoad(
            archetype=BuildingArchetype(load["archetype"]), scaling=LoadScaling.PEAK_KW,
            peak_kw=load["power_kw"], variability_fraction=0, random_seed=20260101)
        values = model.build_load_kw(grid)
    else:
        raise ValueError("Choose constant/synthetic assumptions or native-load CSV.")
    if not isinstance(r["solar"], dict) or set(r["solar"]) != set(DEFAULT_SITE_REQUEST["solar"]):
        raise ValueError("Supply the shared PV model settings.")
    for key, bounds in {"dc_capacity_kw": (0, 100000), "tilt_degrees": (0, 90), "azimuth_degrees": (0, 359.999999),
                        "system_losses_fraction": (0, .999999), "inverter_efficiency": (.001, 1),
                        "temperature_c": (-95, 65), "wind_speed_m_per_s": (0, 120)}.items():
        number(r["solar"][key], key, *bounds)
    number(r["pv_capacity_kw"], "Inverter AC kW", 0, 100000)
    if r["solar"]["dc_capacity_kw"] > 0 and r["pv_capacity_kw"] <= 0:
        raise ValueError("A positive PV array requires a positive AC inverter rating.")
    if r["weather_source"] not in ("clear_sky", "nsrdb") or (r["weather_source"] == "clear_sky" and r["weather_id"] is not None):
        raise ValueError("Choose the shared clear-sky or historical-weather contract.")
    if r["weather_source"] == "nsrdb":
        # Historical rate availability does not establish a reviewed weather
        # import path. Keep the existing candidate's clear-sky limitation.
        raise ValueError("NSRDB weather import is not enabled for ComEd studies yet. Use a labeled clear-sky study; no weather year shifting.")
    battery = r["battery"]
    if battery is not None:
        Battery(**battery)
    if r["ess"] is not None:
        from ..equipment.ess import validate_resolution
        if validate_resolution(r["ess"])["battery"] != battery:
            raise ValueError("Battery values differ from the reviewed equipment configuration.")
    number(r["degradation_cost_per_kWh"], "Wear", 0, 10)
    if type(r["include_degradation_in_optimization"]) is not bool:
        raise ValueError("Choose whether wear is part of optimization.")
    contract = r["operating_contract"]
    if not isinstance(contract, dict) or set(contract) != set(defaults()["operating_contract"]):
        raise ValueError("Supply the non-export operating contract.")
    if any(type(contract[k]) is not bool for k in ("interconnection_confirmed", "standard_tariff_confirmed", "grid_charging_confirmed")):
        raise ValueError("Operating confirmations must be explicit booleans.")
    equipment = r["solar"]["dc_capacity_kw"] > 0 or battery is not None
    if equipment and (contract["mode"] != "approved_non_export" or contract["interconnection_confirmed"] is not True
                      or contract["standard_tariff_confirmed"] is not True
                      or battery is not None and contract["grid_charging_confirmed"] is not True
                      or not isinstance(contract["reference"], str) or not contract["reference"].strip()):
        raise ValueError("Confirm approved non-export operation, unchanged standard import tariff without special DER/standby charges, grid charging for storage, and source evidence or hypothetical assumptions.")
    if not equipment and contract["mode"] not in ("grid_only", "approved_non_export"):
        raise ValueError("Choose grid-only or approved non-export operation.")
    return grid, values.to_numpy(dtype=float), account, prices


def validate(r):
    prepare(r)
    return r


def execute(directory, r):
    from .worker import write_json, summarize_ac_validation
    from .table_store import save_table
    from .site_inputs import build_site_generation
    from ..dispatch.comed import optimize
    from ..opendss.opendss_handoff import create_opendss_handoff
    from ..opendss.opendss_analysis import replay_dispatch_timeseries
    directory = Path(directory)
    grid, load, account, prices = prepare(r)
    available = np.zeros(len(grid.index)); source_tables = {}; warnings = []
    pv_provenance = {"source": "no PV configured"}
    if r["solar"]["dc_capacity_kw"] > 0:
        pv, weather, weather_source, warnings = build_site_generation(r, directory, grid)
        available = pv.pv_available_kw.to_numpy()
        source_tables = {"weather": weather, "pv-production": pv.diagnostics}
        pv_provenance = {"weather": weather_source, "pv": pv.provenance}
    inputs = pd.DataFrame({"timestamp": grid.index, "native_load_kw": load, "pv_available_kw": available})
    from ..billing.comed_cycles import parse_cycles
    cycles = parse_cycles(r.get("billing_cycles"))
    results = {"grid_only": optimize(inputs.assign(pv_available_kw=0.), account, prices, billing_cycles=cycles),
               "pv_only": optimize(inputs, account, prices, billing_cycles=cycles),
               "pv_battery": optimize(inputs, account, prices, r["battery"],
                   wear=r["degradation_cost_per_kWh"], include_wear=r["include_degradation_in_optimization"], billing_cycles=cycles)}
    comparisons, items, tables, ac, cycle_rows = [], [], [], {}, []
    def save(key, label, data):
        data = data.copy()
        if "timestamp" in data:
            data["timestamp"] = pd.to_datetime(data.timestamp, utc=True)
        save_table(directory, key, [c.replace("_", " ") for c in data.columns], data)
        tables.append({"id": key, "label": label, "row_count": len(data)})
    for key, result in results.items():
        bill, dispatch = result["bill"], result["dispatch"]
        warnings.extend(key+": "+message for message in result["warnings"])
        for i, cycle_bill in enumerate(bill.get("cycles", [])):
            cycle_rows.append({"scenario": key, "cycle_index": i,
                **cycle_bill["billing_cycle"], "version_id": cycle_bill["version_id"],
                "import_kwh": cycle_bill["import_kwh"], "subtotal_usd": cycle_bill["subtotal_usd"],
                "billed_mkd_kw": cycle_bill.get("billed_mkd_kw"),
                "overall_30min_peak_kw": cycle_bill.get("overall_30min_peak_kw"),
                "charge_factors": json.dumps(cycle_bill["billing_cycle"]["charge_factors"]),
                "is_complete_bill": False})
        battery = Battery(**r["battery"]) if key == "pv_battery" and r["battery"] is not None else None
        replay = dispatch.rename(columns={"native_load_kw": "load_kw", "pv_output_kw": "pv_kw"})
        handoff = create_opendss_handoff(replay, timestep_minutes=r["timestep_minutes"], expected_timezone=r["timezone"])
        # The present replay represents secondary, balanced service only.
        supported_ac = not isinstance(account, ComEdCommercialAccount) or account.service_voltage == "secondary"
        if supported_ac:
            ac[key] = replay_dispatch_timeseries(handoff, battery=battery,
                pv_capacity_kw=r["pv_capacity_kw"] if key != "grid_only" and r["solar"]["dc_capacity_kw"] > 0 else 0.)
        comparisons.append({"scenario": key, "subtotal_usd": bill["subtotal_usd"],
            "subtotal_savings_vs_grid_usd": results["grid_only"]["bill"]["subtotal_usd"]-bill["subtotal_usd"],
            "total_usd": None, "is_complete_bill": False, "import_kwh": bill["import_kwh"],
            "overall_30min_peak_kw": bill.get("overall_30min_peak_kw"), "billed_mkd_kw": bill.get("billed_mkd_kw"),
            "overall_interval_peak_kw": float(dispatch.grid_import_kw.max()),
            "capacity_obligation_kw": account.capacity_obligation_kw,
            "pv_curtailed_kwh": float(dispatch.pv_curtailed_kw.sum()*grid.timestep_hours),
            "battery_charge_kwh": float(dispatch.battery_charge_kw.sum()*grid.timestep_hours),
            "battery_discharge_kwh": float(dispatch.battery_discharge_kw.sum()*grid.timestep_hours),
            "degradation_cost_usd": result["degradation_cost_usd"],
            "optimization_objective_usd": result["objective_usd"], "recalculated_objective_usd": result["recalculated_objective_usd"],
            "rounding_difference_usd": result["rounding_difference_usd"], "rounding_bound_usd": result["rounding_bound_usd"],
            "solver_gap_usd": result["solver_gap_usd"], "terminal_energy_kwh": result["terminal_energy_kwh"],
            "cost_optimum_proven": result["cost_optimum_proven"],
            "throughput_tie_break_status": result["throughput_tie_break_status"],
            "all_intervals_feasible": bool(ac[key].feasible.all()) if supported_ac else None})
        base_lines = {(x.get("cycle_index"), x["name"]): x["amount_usd"] for x in results["grid_only"]["bill"]["lines"]}
        items.extend({**line, "scenario": key, "subtotal_savings_vs_grid_usd": base_lines[(line.get("cycle_index"), line["name"])]-line["amount_usd"],
                      "source_pdf_pages": ", ".join(map(str, line["source_pdf_pages"]))} for line in bill["lines"])
    save("comparison", "ComEd modeled subtotal comparison", pd.DataFrame(comparisons))
    save("billing-components", "Itemized modeled charges, credits and savings", pd.DataFrame(items))
    if cycle_rows:
        save("billing-cycles", "Subtotals and demand by documented meter cycle", pd.DataFrame(cycle_rows))
    save("inputs", "Native load and available AC PV", inputs)
    for key, result in results.items():
        save("dispatch-"+key, "Dispatch · "+key, result["dispatch"])
        if key in ac:
            save("ac-"+key, "Representative AC replay · "+key, ac[key])
    for key, data in source_tables.items():
        save(key, key.replace("-", " ").title(), data)
    warnings += ["Modeled subtotals and subtotal savings exclude state excise tax, municipal taxes and franchise fees; this is not a complete bill.",
                 "Non-export import projection only: no net-metering, DER rebate, standby rider, export credit or account reclassification is modeled.",
                 "Prior delivery-class peak, prior HV MKD, previous-calendar-year rider history and BESH billed capacity remain fixed across all scenarios.",
                 "Historical perfect foresight. PV curtailment can be economic at negative marginal prices; exclusive storage modes prevent simultaneous charging/discharging.",
                 "The objective uses the filed subtotal before final line-cent rounding. Rounding discrepancies and a bound are reported; capital costs and carbon emissions are not modeled.",
                 "Load source: "+r["load"]["source"]+". Generic synthetic shapes are not calibrated to Illinois or weather-driven HVAC.",
                 "Utility service is explicitly confirmed or hypothetical, never inferred from a state, city, ZIP code or wholesale node.",
                 "Representative balanced 12.47 kV/480 V, 750 kVA OpenDSS circuit; Q=0 inverter and assumed 0.95 load PF. Losses are reported, not added to ideal-meter bills; no site-specific or dynamic validation."]
    if not ac:
        warnings.append("AC replay is unsupported for primary/high-voltage service; retail subtotals do not imply electrical feasibility.")
    if cycles:
        warnings.append("Rates use each explicitly designated utility billing month, not service-date calendar splits. Demand and fixed charges are assessed once per documented cycle. The comparison peak is the maximum across cycles; inspect the billing-cycles table for separate charged peaks.")
        if any(c.kind == "short_service" for c in cycles):
            warnings.append("Short-service charge factors are documented account inputs. The model has not verified a universal proration rule or the authenticity of the supplied allocation source; it never assumes days/30. Every actual-cycle interval is required.")
    if prices and r["prices"]["mode"] == "constant_example":
        warnings.append("BESH prices are explicitly synthetic assumptions, not observed ComEd-zone market data.")
    if prices:
        warnings.append("BESH hourly price source: "+prices.source+". Declared COMED real-time residual basis; source authenticity is not independently verified by the importer.")
    write_json(directory/"result.json", {"schema_version": 10, "tables": tables, "warnings": warnings,
        "total_usd": None, "is_complete_bill": False, "excluded_components": results["grid_only"]["bill"]["excluded_components"],
        "regional_account": r["regional_account"], "account": r["account"], "operating_contract": r["operating_contract"],
        "billing": {k: v["bill"] for k, v in results.items()}, "ac_validation": summarize_ac_validation(ac) if ac else None,
        "optimization": {k: {field: v[field] for field in ("cost_optimum_proven", "throughput_tie_break_status", "strategy", "solver")}
                         for k, v in results.items()},
        "input_provenance": {"load": {k: v for k, v in r["load"].items() if k != "csv"}, "pv": pv_provenance,
            "native_csv_sha256": hashlib.sha256(r["load"]["csv"].encode()).hexdigest() if r["load"]["csv"] else None,
            "price_csv_sha256": hashlib.sha256(r["prices"]["csv"].encode()).hexdigest() if r["prices"] and r["prices"]["csv"] else None,
            "request_sha256": hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest(),
            "wholesale_pricing_location": {"zone": prices.zone, "basis": prices.price_basis, "source": prices.source} if prices else None},
        "engine_id": json.loads((directory/"engine.json").read_text())["id"]})
    write_json(directory/"progress.json", {"message": "ComEd subtotal comparisons and dispatch saved"})
