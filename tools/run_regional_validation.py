"""Private, reproducible schema-11 regional billing/dispatch validation.

Preparation retrieves explicit actual weather only. Execution is a separate
opt-in and pins the current source in Application's ordinary isolated worker.
Native loads and account histories are synthetic assumptions, never measured.
The annual strategy rolls across billing cycles; it is not an annual optimum.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.billing.regional import adapter, calculate_cycle, cycle_account, bill_scope  # noqa: E402
from src.local_web.regional_study import SITES, _load, calendar_cycles, defaults, prepare  # noqa: E402
from src.timeseries import build_interval_index  # noqa: E402
from tools.validation_support import atomic_json, output_lock, positive_seconds, utc_now, value_hash
from tools.regional_validation_resume import previous_manifest, reusable, validator_files, archived_attempt

SCENARIOS = ("grid_only", "pv_only", "pv_battery")
DEFAULT_CASES = (("dominion_energy_north_carolina", "residential", "1T"),
                 ("dominion_energy_north_carolina", "commercial", "5P"),
                 ("pseg", "residential", "RS"), ("pseg", "commercial", "GLP"),
                 ("dominion_energy_virginia", "residential", "VA-1G"),
                 ("dominion_energy_virginia", "commercial", "VA-GS2T"))
VA_HISTORY_CASES = (("dominion_energy_virginia", "residential", "VA-1"),
                    ("dominion_energy_virginia", "commercial", "VA-GS1"))
FIRSTENERGY_CASES = (("firstenergy_pa_west_penn", "residential", "RS"),
                    ("firstenergy_pa_west_penn", "commercial", "GS-M"),
                    ("firstenergy_ohio_edison", "residential", "RS"),
                    ("firstenergy_ohio_edison", "commercial", "GS"))
PECO_CASES = (("peco", "residential", "R"), ("peco", "residential", "R-TOU"),
              ("peco", "commercial", "GS"), ("peco", "commercial", "GS-TOU"))


def selected_cases(utilities=None, plans=None, *, include_ciep=False, include_va_history=False):
    selected = [row for row in DEFAULT_CASES if not utilities or row[0] in utilities]
    if utilities:
        selected.extend(row for row in FIRSTENERGY_CASES + PECO_CASES if row[0] in utilities)
    if include_va_history and (not utilities or "dominion_energy_virginia" in utilities):
        selected.extend(VA_HISTORY_CASES)
    if include_ciep:
        if utilities and "pseg" not in utilities:
            raise ValueError("--include-ciep requires PSE&G in the selected utilities")
        selected.append(("pseg", "commercial", "GLP_CIEP"))
    if plans:
        selected = [row for row in selected if row[2] in plans]
    if not selected:
        raise ValueError("No selected representative plans match --plan; 2025 VA plans require --include-va-history")
    return selected


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    atomic_json(path, value)


def private_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to((ROOT/".cache").resolve()):
        raise ValueError("Validation inputs and price-derived outputs must stay under this checkout's ignored .cache directory.")
    return path


def custom_bounds(period, start_date=None, end_date=None):
    """Validate inclusive custom dates without shifting a source year.

    Custom studies remain within one calendar year and at most366 local service
    days. Tariff eligibility, actual meter-cycle/proration rules and exact source
    coverage are subsequently checked by the ordinary request preparation path.
    """
    if period not in ("monthly", "annual", "custom"):
        raise ValueError("Choose an explicit monthly, annual or custom validation period.")
    if period != "custom":
        if start_date is not None or end_date is not None:
            raise ValueError("Explicit start/end dates are accepted only for a custom validation period.")
        return None
    if start_date is None or end_date is None:
        raise ValueError("Custom validation requires --start-date and --end-date together.")
    try:
        if not all(isinstance(x,str) and len(x)==10 and date.fromisoformat(x).isoformat()==x for x in (start_date,end_date)):
            raise ValueError
        first,last=(date.fromisoformat(x) for x in (start_date,end_date))
    except (TypeError,ValueError) as exc:
        raise ValueError("Custom bounds must be valid YYYY-MM-DD inclusive local dates.") from exc
    if first>last or (last-first).days>=366:
        raise ValueError("Custom validation needs1–366 ordered inclusive service days.")
    if first.year!=last.year:
        raise ValueError("Custom validation currently requires one calendar year; weather and prices are never shifted between years.")
    return start_date,end_date


def validation_periods(periods, start_date=None, end_date=None):
    periods=tuple(periods)
    if not periods:
        raise ValueError("Choose at least one validation period.")
    if "custom" in periods and periods!=("custom",):
        raise ValueError("Custom dates require --period custom alone; monthly/annual defaults are separate runs.")
    for period in periods:
        custom_bounds(period,start_date,end_date)
    return periods


def case_request(utility, kind, period="annual", *, plan=None, ciep_inputs=None, allow_va_history=False,
                 start_date=None, end_date=None, allow_ohio_provisional=False):
    """Complete explicit hypothetical account, local dates and imported load."""
    custom=custom_bounds(period,start_date,end_date)
    r = defaults(utility, kind, plan)
    va_history_plan=utility == "dominion_energy_virginia" and allow_va_history and plan in ("VA-1", "VA-GS1")
    if custom is not None:
        start,end=custom
    elif utility == "dominion_energy_virginia" and not va_history_plan:
        if period == "annual":
            raise ValueError("Dominion Virginia 2025 composite retail rates are not verified; current September2026 rates cannot substitute for2025.")
        start, end = "2026-09-01", "2026-09-30"
    else:
        start, end = ("2025-01-01", "2025-12-31") if period == "annual" else ("2025-07-01", "2025-07-31")
    if utility=="firstenergy_ohio_edison" and custom is None and period=="monthly":
        start,end="2025-10-01","2025-10-31"
    if custom is not None and utility=="dominion_energy_virginia" and start.startswith("2025-") and not va_history_plan:
        raise ValueError("Custom2025 Virginia validation requires --include-va-history and an implemented VA-1/GS1 subtotal; no current-rate substitution.")
    va_history=va_history_plan and start.startswith("2025-")
    name=(f"{utility} {r['account']['tariff']} {start}–{end} custom" if custom is not None else f"{utility} {kind} {start[:4]} {period} validation")
    r.update(name=name, start_date=start, end_date=end,
             billing_cycles=calendar_cycles(start, end))
    account = r["account"]
    if utility=="firstenergy_ohio_edison" and allow_ohio_provisional:
        account.update(rate_evidence_mode="provisional_2025",provisional_assumptions_accepted=True)
        r["name"] += " PROVISIONAL historical rates and billing assumptions"
    if utility == "dominion_energy_virginia":
        account.update(parallel_operation_approved=True, parallel_service=True)
        if va_history or custom is not None:
            opening_month=pd.Timestamp(start).replace(day=1)
            months=pd.date_range(opening_month-pd.DateOffset(months=11),periods=11,freq="MS")
            for row,month in zip(account["history"],months):
                row["billing_month"]=month.month
        if va_history:
            r["name"] += " verified charges subtotal (historical taxes incomplete)"
            if kind == "commercial":
                # The inherited20kW contract/history is the same in all three
                # scenarios. Only actual subsequent history evolves.
                r["load"]["power_kw"] = 15.
                r["solar"]["dc_capacity_kw"] = 10.
                r["pv_capacity_kw"] = 8.
                r["battery"].update(max_charge_kw=5., max_discharge_kw=5.)
    if utility == "dominion_energy_north_carolina":
        # Explicit starting history for the eleven months before this study;
        # the worker then evolves it independently for every scenario.
        months = pd.date_range(pd.Timestamp(start).replace(day=1)-pd.DateOffset(months=11), periods=11, freq="MS")
        account["history_billing_months"] = months.month.tolist()
    if utility == "pseg":
        for cycle in r["billing_cycles"]:
            cycle["account_overrides"] = adapter(utility).hypothetical_obligation_overrides(account["tariff"], cycle["billing_month"])
        if kind == "commercial":
            # Keep rated DER below the ordinary-versus-standby threshold even
            # after all starting40kW peaks have rolled out of the history.
            r["load"]["power_kw"] = 40.
            r["solar"]["dc_capacity_kw"] = 6.25
            r["pv_capacity_kw"] = 5.
            r["battery"].update(max_charge_kw=5., max_discharge_kw=5.)
        if ciep_inputs is not None:
            if kind != "commercial":
                raise ValueError("PSE&G residential default supply is RSCP, not CIEP.")
            folder = private_path(ciep_inputs)
            account.update(supply="bgs_ciep", obligation_enrollment_confirmed=True,
                market_data={"csv_text": (folder/"rt_hrl_lmps_pseg_resid_agg_2025_boundary.csv").read_text(),
                             "metadata": json.loads((folder/"metadata.json").read_text())})
            r["regional_account"]["wholesale_pricing_location"] = deepcopy(adapter(utility).RESIDUAL_LOCATION)
            r["name"] += " CIEP"
    r["operating_contract"].update(interconnection_confirmed=True, grid_charging_confirmed=True,
        reference="Explicit hypothetical utility-approved non-export PV/storage account; no export compensation assumed")
    if utility.startswith("firstenergy_"):
        r["operating_contract"].update(grid_charging_confirmed=False,renewable_only_charging=True)
    r["solar"].update(tilt_degrees=30., azimuth_degrees=180., system_losses_fraction=.14,
                       inverter_efficiency=.96)
    # Read back the generated native series through the same CSV contract as
    # customer imports. This does not transform synthetic data into measured data.
    settings = r["load"]
    grid = build_interval_index(start, end, r["timezone"], r["timestep_minutes"])
    if start.startswith("2025") or custom is not None:
        year=start[:4]
        year_grid = build_interval_index(year+"-01-01", year+"-12-31", r["timezone"], r["timestep_minutes"])
        annual_native = pd.Series(_load(settings, year_grid, kind), index=year_grid.index)
        native = annual_native.reindex(grid.index).to_numpy()
    else:
        native = _load(settings, grid, kind)
    text = pd.DataFrame({"timestamp": grid.index, "native_load_kw": native}).to_csv(index=False, float_format="%.9f")
    settings.update(mode="csv", power_kw=None, archetype=None, csv=text, native_basis_confirmed=True,
        source="Deterministic generic household/office archetype, serialized native interval load; synthetic, not measured or regionally calibrated")
    prepare(r)
    return r


def weather_request(utility):
    lat, lon, _ = SITES[utility]
    return dict(latitude=lat, longitude=lon, year=2025, timezone="America/New_York", timestep_minutes=15)


def prepare_inputs(folder, *, env_file=None, utilities=None, include_va_history=False, va_history_only=False):
    """Retrieve once; validate cached weather without refreshing its bytes."""
    from src.credentials import DEFAULT_ENV_PATH, WEATHER_CREDENTIALS, load_credentials
    from src.local_web.site_inputs import retrieve_weather
    from src.profiles.era5 import fetch_era5, parse_era5
    folder = private_path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    utilities = utilities or tuple(SITES)
    load_credentials(DEFAULT_ENV_PATH if env_file is None else env_file, names=WEATHER_CREDENTIALS)
    previous_file = folder/"weather-input-manifest.json"
    previous = json.loads(previous_file.read_text()) if previous_file.exists() else {}
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "sources": deepcopy(previous.get("sources", {}))}
    for utility in utilities:
        path = folder/utility
        path.mkdir(exist_ok=True)
        if utility.startswith("firstenergy_") or utility == "peco" or utility == "dominion_energy_virginia" and not va_history_only:
            file = path/"era5.json"
            expected = previous.get("sources", {}).get(utility, {}).get("sha256")
            if expected is not None:
                require(file.exists() and digest(file) == expected, "Prepared ERA5 bytes changed; choose a new input folder")
            start,end=("2025-01-01","2025-12-31") if utility.startswith("firstenergy_") or utility == "peco" else ("2026-09-01","2026-09-30")
            request = dict(latitude=SITES[utility][0], longitude=SITES[utility][1], start_date=start, end_date=end)
            payload = json.loads(file.read_text()) if file.exists() else fetch_era5(**request)
            require(payload["request"]["latitude"] == request["latitude"] and payload["request"]["longitude"] == request["longitude"],
                    "Prepared ERA5 coordinates differ; retrieve the exact site in a new input folder")
            grid = build_interval_index(request["start_date"], request["end_date"], "America/New_York", 15)
            _, provenance = parse_era5(payload["raw_json"], grid, request["latitude"], request["longitude"])
            if not file.exists():
                write_json(file, payload)
            manifest["sources"][utility] = {"sha256": digest(file), "provenance": provenance,
                                             "retrieved_at": payload["retrieved_at"]}
        elif utility != "dominion_energy_virginia":
            file = path/"weather.json"
            if file.exists():
                metadata = json.loads(file.read_text())
                require(metadata["request"] == weather_request(utility), "Cached weather request differs")
                require(digest(path/"weather.csv") == metadata["sha256"], "Cached weather bytes changed")
            else:
                metadata = retrieve_weather(path, weather_request(utility))
            manifest["sources"][utility] = metadata
        if utility == "dominion_energy_virginia" and include_va_history:
            # Separate artifacts prevent a2025 study from accidentally reading
            # the current-month ERA5 cache or replacing its source provenance.
            historical = path/"nsrdb_2025"
            historical.mkdir(exist_ok=True)
            file = historical/"weather.json"
            if file.exists():
                metadata = json.loads(file.read_text())
                require(metadata["request"] == weather_request(utility), "Cached historical VA weather request differs")
                require(digest(historical/"weather.csv") == metadata["sha256"], "Cached historical VA weather bytes changed")
            else:
                metadata = retrieve_weather(historical, weather_request(utility))
            manifest["sources"][utility+"_2025"] = metadata
    write_json(folder/"weather-input-manifest.json", manifest)
    return manifest


def attach_weather(app, request, inputs):
    utility = request["site"]["utility"]
    source = private_path(inputs)/utility
    va_history = utility == "dominion_energy_virginia" and request["start_date"].startswith("2025-")
    if utility.startswith("firstenergy_") or utility == "peco":
        payload=json.loads((source/"era5.json").read_text())
        from src.profiles.era5 import parse_era5
        lat,lon,_=SITES[utility]
        require(payload["request"]["models"]=="era5" and payload["request"]["latitude"]==lat
            and payload["request"]["longitude"]==lon, "Prepared regional ERA5 source/site mismatch")
        parse_era5(payload["raw_json"],build_interval_index(request["start_date"],request["end_date"],request["timezone"],request["timestep_minutes"]),lat,lon)
        request.update(weather_source="era5",weather_id=None,weather=payload)
    elif utility == "dominion_energy_virginia" and not va_history:
        request.update(weather_source="era5", weather_id=None,
                       weather=json.loads((source/"era5.json").read_text()))
    else:
        if va_history:
            source = source/"nsrdb_2025"
        weather = weather_request(utility)
        if request["start_date"][:4]!=str(weather["year"]) or request["end_date"][:4]!=str(weather["year"]):
            raise ValueError("Prepared NSRDB validation inputs are explicitly2025; no weather-year substitution. Supply supported exact-year inputs through an explicit preparation path.")
        metadata = json.loads((source/"weather.json").read_text())
        require(metadata["request"] == weather, "Historical weather request mismatch")
        require(digest(source/"weather.csv") == metadata["sha256"], "Historical weather checksum mismatch")
        # Application scopes weather IDs to the immutable engine and owner.
        # Rebind unchanged prepared data, then use the normal verified cache path.
        key = hashlib.sha256(json.dumps([app.engine["id"], "weather", weather, None], sort_keys=True).encode()).hexdigest()
        dest = app.store.directory/"weather"/key
        dest.mkdir(parents=True, exist_ok=True)
        for name in ("weather.csv", "weather.json"):
            if (dest/name).exists():
                require(digest(dest/name) == digest(source/name), "Refusing to replace a different pinned weather input")
            else:
                shutil.copyfile(source/name, dest/name)
        write_json(dest/"resource.json", metadata)
        result = app.resource("weather", weather)
        request.update(weather_source="nsrdb", weather_id=result["id"], weather=None)
    prepare(request)
    return request


def checked_bill_scope(bill, utility, account, index, *, allow_va_history=False, allow_ohio_provisional=False):
    """Allow exactly the documented historical VA tax gap, by explicit opt-in."""
    if bill.get("rate_evidence_status")=="provisional":
        if utility == "peco":
            from src.billing.peco import ALLOCATION_MODEL, allocation_evidence
            expected = allocation_evidence(account, index)
            require(account.get("rate_evidence_mode") == "provisional_cycles_v1"
                    and account.get("provisional_assumptions_accepted") is True
                    and bill.get("assumption_model") == ALLOCATION_MODEL
                    and bill.get("rate_assumptions")
                    and all(bill.get(k) == expected[k] for k in expected)
                    and any("Provisional PECO billing estimate" in w for w in bill.get("warnings", [])),
                    "Provisional PECO bills require explicit opt-in and intact allocation provenance")
            return "provisional_modeled_bill", []
        from src.billing.firstenergy_oh_provisional import MODEL, evidence
        expected=evidence(pd.DatetimeIndex(index),account)
        require(allow_ohio_provisional and utility=="firstenergy_ohio_edison"
                and account.get("rate_evidence_mode")=="provisional_2025"
                and account.get("provisional_assumptions_accepted") is True
                and bill.get("assumption_model")==MODEL and bill.get("rate_assumptions")
                and bill["rate_assumptions"]==expected["rate_assumptions"]
                and any("Provisional historical estimate" in w for w in bill.get("warnings",[])),
                "Provisional historical bills require explicit Ohio opt-in and intact assumption provenance")
        return "provisional_modeled_bill", []
    if bill["is_complete_bill"]:
        return "complete_utility_bill", []
    idx = pd.DatetimeIndex(index)
    expected = {"sales_use_tax_surcharge", "local_utility_consumer_tax"}
    if idx[-1].date() < pd.Timestamp("2025-08-16").date():
        expected.add("consumption_tax_before_2025_08_16")
    require(allow_va_history and utility == "dominion_energy_virginia"
            and account["tariff"] in ("VA-1", "VA-GS1")
            and idx[0].year == idx[-1].year == 2025
            and bill["metrics"].get("rate_version") == "dominion_va_2025_dated_components"
            and set(bill.get("excluded_components", [])) == expected
            and set(bill["metrics"].get("historical_tax_components_excluded", [])) == expected
            and not expected.intersection(bill["lines"])
            and ("consumption_tax" in bill["lines"]) == (idx[-1].date() >= pd.Timestamp("2025-08-16").date())
            and any("Missing decision-dependent taxes" in warning for warning in bill.get("warnings", [])),
            "The tariff bill is an incomplete subtotal outside the explicitly allowed VA2025 tax scope")
    return "verified_charges_subtotal", sorted(expected)


def audit(directory, request, engine_id, *, allow_va_history=False, allow_ohio_provisional=False):
    """Rebill each cycle and verify continuous physical and billing state."""
    directory = Path(directory)
    result = json.loads((directory/"result.json").read_text())
    grid, native, cycles, equipment = prepare(request)
    index, dt = grid.index, grid.timestep_hours
    require(result["engine_id"] == engine_id, "Worker engine differs from the pin")
    utility = request["site"]["utility"]
    require(result["ac_validation"]["status"] == "completed", "Representative circuit was not evaluated")
    require(len(result["ac_validation"]["scenarios"]) == len(SCENARIOS), "An electrical scenario is missing")
    inputs = pd.read_csv(directory/"inputs.csv")
    require(pd.DatetimeIndex(pd.to_datetime(inputs.timestamp, utc=True)).equals(index.tz_convert("UTC")), "Input timestamp grid changed")
    require(np.allclose(inputs.native_load_kw, native, atol=1e-8, rtol=0), "Native input changed")
    comparison = pd.read_csv(directory/"comparison.csv").set_index("scenario")
    saved_lines = pd.read_csv(directory/"billing-components.csv")
    saved_cycles = pd.read_csv(directory/"billing-cycles.csv")
    rows, lines, physics = [], [], []
    for scenario in SCENARIOS:
        outcomes = result["optimization"][scenario]["cycles"]
        require(len(outcomes) == len(cycles), "Optimizer lost a billing cycle")
        require(all(x["cost_optimum_proven"] is not False for x in outcomes), "Primary optimum was not proven")
        dispatch = pd.read_csv(directory/f"dispatch-{scenario}.csv")
        require(pd.DatetimeIndex(pd.to_datetime(dispatch.timestamp, utc=True)).equals(index.tz_convert("UTC")), "Dispatch grid incomplete")
        require(np.isfinite(dispatch.select_dtypes(include="number").to_numpy()).all(), "Nonfinite dispatch")
        require(np.allclose(dispatch.native_load_kw, native, atol=1e-8, rtol=0), "Scenarios use different loads")
        pv = inputs.pv_available_kw.to_numpy() if scenario != "grid_only" else np.zeros(len(index))
        require(np.max(abs(dispatch.pv_available_kw-pv)) < 1e-6, "Scenarios use different solar inputs")
        charge, discharge, soc = (dispatch[k].to_numpy() for k in ("battery_charge_kw", "battery_discharge_kw", "energy_kWh"))
        imbalance = float(np.max(abs(dispatch.grid_import_kw+dispatch.pv_output_kw+discharge-native-charge-dispatch.grid_export_kw)))
        require(imbalance < 1e-5, "Interval power imbalance")
        require(np.max(abs(dispatch.pv_output_kw+dispatch.pv_curtailed_kw-pv)) < 1e-5, "PV curtailment changed")
        require(np.min(dispatch.grid_import_kw) >= -1e-6 and np.max(abs(dispatch.grid_export_kw)) < 1e-6, "Non-export contract violated")
        require(np.max(np.minimum(charge, discharge)) < 1e-5, "Battery charge/discharge is simultaneous")
        terminal = outcomes[-1]["terminal_energy_kwh"]
        has_storage = scenario == "pv_battery"
        soc_error = 0.
        if has_storage:
            b = request["battery"]
            changes = dt*(charge*b["charge_efficiency"]-discharge/b["discharge_efficiency"])
            soc_error = float(np.max(abs(np.r_[soc[1:], terminal]-soc-changes)))
            require(soc_error < 1e-5, "Continuous SOC recursion failed")
            require(abs(soc[0]-b["energy_kWh"]) < 1e-5 and abs(terminal-b["energy_kWh"]) < 1e-5, "Study boundary SOC changed")
            require(min(soc.min(), terminal) >= b["capacity_kWh"]*b["SOC_min"]-1e-5 and max(soc.max(), terminal) <= b["capacity_kWh"]*b["SOC_max"]+1e-5, "SOC limits violated")
            require(charge.max() <= b["max_charge_kw"]+1e-5 and discharge.max() <= b["max_discharge_kw"]+1e-5, "Battery power ratings violated")
        else:
            require(np.max(abs(np.r_[charge, discharge, soc])) < 1e-6, "Absent battery operated")
        state = None
        total = 0.
        scenario_bills=[]
        for i, block, cycle in cycles:
            a = cycle_account(request["account"], cycle)
            equipment_one = {**equipment, "pv": scenario != "grid_only", "battery": has_storage,
                "pv_ac_kw": request["pv_capacity_kw"] if scenario != "grid_only" else 0.,
                "battery_kw": request["battery"]["max_discharge_kw"] if has_storage else 0.}
            bill = calculate_cycle(utility, index[block], dispatch.grid_import_kw.to_numpy()[block],
                dispatch.grid_export_kw.to_numpy()[block], a, state=state, equipment=equipment_one)
            state = bill["next_state"]
            scenario_bills.append(bill)
            scope, excluded = checked_bill_scope(bill, utility, a, index[block], allow_va_history=allow_va_history, allow_ohio_provisional=allow_ohio_provisional)
            require(abs(bill["total_usd"]-sum(bill["lines"].values())) < 1e-7, "Itemized bill does not sum")
            ledger = saved_cycles.loc[(saved_cycles.scenario == scenario)&(saved_cycles.cycle_index == i)].iloc[0]
            require(bool(ledger.is_complete_bill) == bill["is_complete_bill"], "Saved completeness flag differs")
            require(ledger.objective_scope == scope, "Saved objective scope differs")
            if bill.get("rate_evidence_status"):
                require(ledger.rate_evidence_status==bill["rate_evidence_status"],"Saved rate evidence differs")
                require(json.loads(ledger.rate_assumption_ids)==[v["id"] for v in bill["rate_assumptions"]],"Saved assumption IDs differ")
                saved=result["billing"][scenario][i]
                require(all(saved.get(k)==bill.get(k) for k in ("rate_evidence_status","assumption_model","rate_assumptions")),"Saved assumption provenance differs")
                if bill["rate_assumptions"]:
                    assumptions=pd.read_csv(directory/"billing-assumptions.csv")
                    selected_assumptions=assumptions.loc[(assumptions.scenario==scenario)&(assumptions.cycle_index==i)]
                    require(set(selected_assumptions.assumption_id)=={v["id"] for v in bill["rate_assumptions"]},"Assumption download incomplete")
                    for value in bill["rate_assumptions"]:
                        row=selected_assumptions.loc[selected_assumptions.assumption_id==value["id"]].iloc[0]
                        require(row.assumption_model==bill["assumption_model"] and json.loads(row.assumed_values)==value["assumed_values"],"Assumed values changed in download")
            require(abs(ledger.total_usd-bill["total_usd"]) < .00001, "Saved cycle bill differs")
            require(abs(outcomes[i]["reconciliation_difference_usd"]) < .0001, "Dispatch objective does not reconcile")
            if outcomes[i].get("cost_optimum_proven") and "primary_lower_bound_usd" in outcomes[i]:
                proof = outcomes[i]
                objective = bill["unrounded_total_usd"]
                if request["include_degradation_in_optimization"]:
                    objective += request["degradation_cost_per_kWh"]*dt*float((charge[block]+discharge[block]).sum())
                require(proof["cost_proof_method"] in ("strict_milp","physical_relaxation_bound"), "Unknown primary proof method")
                require(abs(objective-proof["primary_lower_bound_usd"]) <= proof["primary_proof_tolerance_usd"], "Physical bill does not attain its proven lower bound")
                if proof["minimum_cycling_proven"]:
                    throughput = dt*float((charge[block]+discharge[block]).sum())
                    require(abs(throughput-proof["cycling_lower_bound_kwh"]) <= proof["cycling_proof_tolerance_kwh"], "Physical throughput does not attain its proven lower bound")
            saved_state = json.loads(ledger.closing_state)
            def same_state(left, right):
                if isinstance(left, dict) and isinstance(right, dict):
                    return set(left) == set(right) and all(same_state(left[k], right[k]) for k in left)
                if isinstance(left, list) and isinstance(right, list):
                    return len(left) == len(right) and all(same_state(x, y) for x, y in zip(left, right))
                if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                    return abs(left-right) < 1e-6
                return left == right
            require(same_state(saved_state, state), "History/credit state was not propagated")
            for name, value in bill["lines"].items():
                selected = saved_lines.loc[(saved_lines.scenario == scenario)&(saved_lines.cycle_index == i)&(saved_lines.component == name)]
                require(len(selected) == 1 and abs(selected.iloc[0].amount_usd-value) < .000001, "Saved bill component differs")
                if bill.get("rate_evidence_status"):
                    related=[x["id"] for x in bill["rate_assumptions"] if name in x["components"]]
                    require(json.loads(selected.iloc[0].rate_assumption_ids)==related,"Saved component assumptions differ")
                    require(selected.iloc[0].rate_evidence_status==("provisional" if related else "verified"),"Saved component evidence differs")
                lines.append(dict(scenario=scenario, cycle_index=i, billing_month=cycle["billing_month"], component=name, amount_usd=value))
            start, stop = block.start, block.stop
            opening = float(soc[start])
            closing = float(soc[stop]) if stop < len(soc) else float(terminal or 0.)
            if has_storage:
                require(abs(closing-outcomes[i]["terminal_energy_kwh"]) < 1e-5, "Cycle SOC boundary differs")
            rows.append(dict(scenario=scenario, cycle_index=i, billing_month=cycle["billing_month"],
                physical_intervals=stop-start, physical_hours=(stop-start)*dt,
                native_kwh=float(native[block].sum()*dt), import_kwh=bill["import_kwh"],
                utility_bill_usd=bill["total_usd"], opening_battery_kwh=opening, closing_battery_kwh=closing,
                is_complete_bill=bill["is_complete_bill"], objective_scope=scope,
                rate_evidence_status=bill.get("rate_evidence_status","not_recorded"),
                excluded_components=json.dumps(excluded),
                cost_proof_method=outcomes[i].get("cost_proof_method","legacy_not_recorded"),
                primary_optimality_gap_usd=outcomes[i].get("primary_optimality_gap_usd"),
                cycling_proof_method=outcomes[i].get("cycling_proof_method","legacy_not_recorded"),
                rate_metrics=json.dumps(bill["metrics"], sort_keys=True, default=str)))
            total += bill["total_usd"]
        require(abs(total-comparison.loc[scenario, "utility_bill_usd"]) < .00001, "Annual/monthly comparison differs")
        if any(b.get("rate_evidence_status")=="provisional" for b in scenario_bills):
            require(result.get("rate_evidence_status")==comparison.loc[scenario,"rate_evidence_status"]=="provisional"
                    and comparison.loc[scenario,"objective_scope"]=="provisional_modeled_bill","Provisional scenario was mislabeled")
        ac = next(x for x in result["ac_validation"]["scenarios"] if x["scenario"] == scenario)
        require(ac["checked_intervals"] == len(index), "OpenDSS omitted intervals")
        replay = pd.read_csv(directory/f"{ac['interval_table']}.csv")
        require(len(replay) == len(index), "Electrical interval download incomplete")
        # Electrical infeasibility is a result, not a reason to change bills.
        physics.append(dict(scenario=scenario, checked_intervals=len(index), max_power_balance_error_kw=imbalance,
            max_soc_recursion_error_kwh=soc_error, ac_failed_intervals=ac["failed_intervals"],
            ac_all_intervals_feasible=ac["all_intervals_feasible"],
            all_minimum_cycling_proven=all(x["minimum_cycling_proven"] is not False for x in outcomes)))
    require(comparison.loc["pv_only", "utility_bill_usd"] <= comparison.loc["grid_only", "utility_bill_usd"]+.02, "PV-only unexpectedly worsens the optimum")
    # Independent rolling policies can produce different endogenous histories;
    # do not claim a joint annual optimum or impose an invalid annual ordering.
    return pd.DataFrame(rows), pd.DataFrame(lines), physics


def summarize(directory):
    """Reproduce a compact private report from saved artifacts, without APIs.

    Raw native/weather/market rows and credential material are never embedded.
    A failed or previously unvalidated case remains visibly unvalidated.
    """
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    directory=private_path(directory)
    manifest=json.loads((directory/"validation.json").read_text())
    # A later main-branch rate edit must not enter a historical summary. Read
    # catalog sources from the actual immutable worker, not today's adapters.
    pinned_catalog={}
    if (directory/"engines"/manifest["engine_id"]).is_dir():
        from src.local_web.runtime import command,verify_snapshot,worker_environment
        engine=json.loads((directory/"engine.json").read_text())
        require(engine["id"]==manifest["engine_id"],"Summary engine pointer differs from the validation pin")
        verify_snapshot(directory,engine)
        reply=subprocess.run(command(directory,engine["id"],"capabilities"),capture_output=True,
            text=True,check=True,timeout=90,env=worker_environment())
        capabilities=json.loads(reply.stdout)["regional_simulation"]["utilities"]
        pinned_catalog={utility:{row["id"]:{key:row.get(key) for key in ("label","sources","coverage")}
            for row in value["plans"]} for utility,value in capabilities.items()}
        write_json(directory/"regional-source-catalog.json",{"engine_id":engine["id"],"utilities":pinned_catalog})
    def clean(value):
        if isinstance(value,dict):return {str(k):clean(v) for k,v in value.items()}
        if isinstance(value,(list,tuple)):return [clean(v) for v in value]
        if isinstance(value,np.generic):return clean(value.item())
        if isinstance(value,float) and not np.isfinite(value):return None
        return value
    def urls(value):
        found=set()
        if isinstance(value,dict):
            for one in value.values():found.update(urls(one))
        elif isinstance(value,(list,tuple)):
            for one in value:found.update(urls(one))
        elif isinstance(value,str) and value.startswith("https://"):
            parsed=urlsplit(value)
            query=[(k,v) for k,v in parse_qsl(parsed.query) if k.lower() not in
                   {"api_key","apikey","key","token","access_token","email","password","secret"}]
            # Official source links never need embedded HTTP credentials.
            host=parsed.hostname or ""
            if parsed.port is not None:host += ":"+str(parsed.port)
            found.add(urlunsplit((parsed.scheme,host,parsed.path,urlencode(query),"")))
        return found
    summary_source=Path(__file__).read_bytes()
    summary_hash=hashlib.sha256(summary_source).hexdigest()
    summary_driver="summary-driver-"+summary_hash[:12]+".py"
    (directory/summary_driver).write_bytes(summary_source)
    report={"engine_id":manifest["engine_id"],"driver_sha256":manifest["driver_sha256"],
        "summary_driver_sha256":summary_hash,"summary_driver_file":summary_driver,
        "pinned_source_catalog_sha256":digest(directory/"regional-source-catalog.json") if pinned_catalog else None,
        "privacy":"Private internal validation; no raw market-data redistribution permission is inferred.",
        "scope":manifest["scope"],"blocked_scope":manifest.get("blocked_scope",{}),
        "case_count":len(manifest["cases"]),"passed":0,"failed":0,"pending":0,"cases":[]}
    all_urls=set()
    for entry in manifest["cases"]:
        record={k:entry.get(k) for k in ("case","utility","class","period","study_id","status","validation","error")}
        report["cases"].append(record)
        if entry.get("validation")!="passed":
            report["failed" if entry.get("validation")=="failed" else "pending"]+=1
            continue
        report["passed"]+=1
        folder=directory/"runs"/entry["study_id"]
        result=json.loads((folder/"result.json").read_text())
        request=json.loads((folder/"request.json").read_text())
        comparison=pd.read_csv(folder/"comparison.csv")
        plan=pinned_catalog.get(entry["utility"],{}).get(request["account"]["tariff"],{})
        sources=urls(plan.get("sources",[]))|urls(result.get("billing",{}))|urls(result.get("input_provenance",{}))
        all_urls.update(sources)
        load=pd.read_csv(folder/"inputs.csv",usecols=["native_load_kw"])
        record.update(start_date=request["start_date"],end_date=request["end_date"],
            timezone=request["timezone"],timestep_minutes=request["timestep_minutes"],
            tariff=request["account"]["tariff"],supply=request["account"].get("supply",request["account"].get("supplier",request["account"].get("supply_arrangement"))),
            assumptions={"native_load_source":request["load"]["source"],
                "native_kwh":float(load.native_load_kw.sum()*request["timestep_minutes"]/60),
                "pv_dc_kw":request["solar"]["dc_capacity_kw"],"pv_ac_kw":request["pv_capacity_kw"],
                "battery":request["battery"],"operating_contract":request["operating_contract"],
                "wear_in_objective":request["include_degradation_in_optimization"]},
            source_urls=sorted(sources),source_artifact_sha256=entry.get("source_artifacts",{}),
            input_provenance=result.get("input_provenance",{}),warnings=result.get("warnings",[]),
            is_complete_bill=result.get("is_complete_bill"),
            rate_evidence_status=result.get("rate_evidence_status","not_recorded"),
            reported_amount_kind=("provisional historical estimate; inspect assumption ledger" if result.get("rate_evidence_status")=="provisional" else "verified charges subtotal; historical taxes incomplete" if result.get("is_complete_bill") is False
                else "complete utility bill" if result.get("is_complete_bill") is True else "legacy completeness not recorded"),
            excluded_components=sorted({value for bills in result.get("billing",{}).values()
                for bill in bills for value in bill.get("excluded_components",[])}),scenarios=[])
        for row in comparison.to_dict("records"):
            name=row["scenario"]
            cycles=result["optimization"][name]["cycles"]
            ac=next(item for item in result["ac_validation"]["scenarios"] if item["scenario"]==name)
            methods=Counter(item.get("cost_proof_method","legacy_not_recorded") for item in cycles)
            gaps=[item["primary_optimality_gap_usd"] for item in cycles if item.get("primary_optimality_gap_usd") is not None]
            record["scenarios"].append({
                "scenario":name,"utility_bill_usd":row["utility_bill_usd"],
                "is_complete_bill":row.get("is_complete_bill"),
                "objective_scope":row.get("objective_scope","legacy_not_recorded"),
                "savings_vs_grid_usd":row["savings_vs_grid_usd"],
                "import_kwh":row["import_kwh"],"export_kwh":row["export_kwh"],
                "estimated_battery_wear_usd":row["estimated_battery_wear_usd"],
                "optimization":{"cycle_count":len(cycles),"annual_optimum_proven":result["optimization"][name]["annual_optimum_proven"],
                    "primary_proof_methods":dict(methods),
                    "all_primary_optima_proven_or_direct":all(item["cost_optimum_proven"] is not False for item in cycles),
                    "all_minimum_cycling_proven":all(item["minimum_cycling_proven"] for item in cycles) if name=="pv_battery" else None,
                    "maximum_primary_gap_usd":max(gaps) if gaps else None,
                    "maximum_reconciliation_difference_usd":max(item["reconciliation_difference_usd"] for item in cycles),
                    "strict_fallback_cycles":sum(bool(item["strict_fallback_used"]) for item in cycles)
                        if all("strict_fallback_used" in item for item in cycles) else None},
                "electrical":{"checked_intervals":ac["checked_intervals"],"failed_intervals":ac["failed_intervals"],
                    "all_intervals_feasible":ac["all_intervals_feasible"],"measurements_complete":ac.get("electrical_measurements_complete"),
                    "network":result["ac_validation"]["network_configuration"]}})
    report["source_urls"]=sorted(all_urls)
    write_json(directory/"validation-summary.json",clean(report))
    return clean(report)


def run(output, inputs, *, include_ciep=False, ciep_inputs=None, include_va_history=False, cases=None, periods=("monthly", "annual"),
        start_date=None, end_date=None, resume=False, case_timeout=2100, allow_ohio_provisional=False):
    periods = validation_periods(periods, start_date, end_date)
    case_timeout = positive_seconds(case_timeout)
    output, inputs = private_path(output), private_path(inputs)
    output.mkdir(parents=True, exist_ok=True)
    with output_lock(output, ".regional-validation.lock"):
        return _run(output, inputs, include_ciep=include_ciep, ciep_inputs=ciep_inputs,
            include_va_history=include_va_history, allow_ohio_provisional=allow_ohio_provisional, cases=cases, periods=periods,
            start_date=start_date, end_date=end_date, resume=resume, case_timeout=case_timeout)


def _run(output, inputs, *, include_ciep, ciep_inputs, include_va_history, cases, periods,
         start_date, end_date, resume, case_timeout, allow_ohio_provisional):
    from src.local_web.runtime import Application
    for utility in SITES:
        adapter(utility)
    selections = list(cases or DEFAULT_CASES)
    if include_ciep:
        selections.append(("pseg", "commercial", "GLP_CIEP"))
    if include_va_history and cases is None:
        selections.extend(VA_HISTORY_CASES)
    require(any(period != "annual" or utility != "dominion_energy_virginia"
        or (include_va_history and plan in ("VA-1", "VA-GS1"))
        for utility, _, plan in selections for period in periods), "No executable cases in this selection")
    execution = dict(cases=[list(c) for c in selections], periods=list(periods),
        start_date=start_date, end_date=end_date, inputs=str(inputs),
        ciep_inputs=str(private_path(ciep_inputs)) if ciep_inputs is not None else None,
        include_va_history=include_va_history, case_timeout=case_timeout, allow_ohio_provisional=allow_ohio_provisional)
    old = previous_manifest(output, resume, execution)
    app = Application(output)
    started = time.monotonic()
    print("Pinned regional validation engine", app.engine["id"], flush=True)
    manifest = {"format_version": 2, "engine_id": app.engine["id"], "driver_sha256": digest(__file__),
        "validator_files": validator_files(), "execution": execution, "cases": [], "sessions": [],
        "scope": "Actual site/year weather; imported synthetic native loads and hypothetical accounts; non-export; rolling-cycle perfect foresight with continuous SOC and actual evolving histories; no annual optimum or site-specific electrical claim",
        "blocked_scope": {"dominion_energy_virginia_2025": "VA-1/GS1 verified 2025 bundled charges are available only as explicit opt-in subtotals. Historical sales/use surcharge and local consumer-tax originals are missing; pre-August16 consumption tax is also excluded. Other 2025 plans remain unavailable; 2026 coverage follows the pinned Virginia catalog and rejects missing intermediate component versions."}}
    session = {"started_at": utc_now(), "resumed": resume, "executed_cases": 0, "reused_cases": 0}
    manifest["sessions"] = deepcopy(old.get("sessions", [])) if old else []
    manifest["sessions"].append(session)
    if periods == ("custom",):
        manifest["custom_date_bounds"] = {"start_date": start_date, "end_date": end_date,
            "interpretation": "Inclusive local dates; custom study, not an annual case"}
    monthly, components, summaries, failures = [], [], [], []
    validated = False
    loop_finished = False
    try:
        require({p.relative_to(ROOT).as_posix(): digest(p) for p in (ROOT/"src").rglob("*.py")} == app.engine["files"],
            "Store pins different source; select a fresh output directory")
        if old is not None and old["engine_id"] != app.engine["id"]:
            raise ValueError("Resume engine changed; use a fresh output directory")
        if old:
            manifest["cases"] = deepcopy(old["cases"])
        validated = True
        (output/("validation-driver-"+manifest["driver_sha256"][:12]+".py")).write_bytes(Path(__file__).read_bytes())
        write_json(output/"validation.json", manifest)
        for utility, kind, plan in selections:
            for period in periods:
                if utility == "dominion_energy_virginia" and period == "annual" and not (include_va_history and plan in ("VA-1", "VA-GS1")):
                    continue
                suffix = f"custom-{start_date}_to_{end_date}" if period == "custom" else period
                identity = f"{utility}-{plan}-{suffix}"
                prior = next((e for e in manifest["cases"] if e["case"] == identity), None)
                entry = {"case": identity, "utility": utility, "class": kind, "period": period}
                if prior:
                    entry["attempts"] = deepcopy(prior.get("attempts", []))+[archived_attempt(prior)]
                case_started = time.monotonic()
                timing = {}
                reuse = False
                preserve_prior = False
                waiting = None
                try:
                    r = case_request(utility, kind, period, plan="GLP" if plan == "GLP_CIEP" else plan,
                        ciep_inputs=ciep_inputs if plan == "GLP_CIEP" else None, allow_va_history=include_va_history, allow_ohio_provisional=allow_ohio_provisional,
                        start_date=start_date if period == "custom" else None, end_date=end_date if period == "custom" else None)
                    attach_weather(app, r, inputs)
                    timing["input_preparation_seconds"] = time.monotonic()-case_started
                    if prior and prior.get("request_fingerprint") not in (None, value_hash(r)):
                        raise ValueError("Prepared case inputs changed; use a fresh output directory.")
                    if prior and prior.get("study_id"):
                        directory = output/"runs"/prior["study_id"]
                        if reusable(prior, r, directory, app.engine["id"]):
                            audited = time.monotonic()
                            try:
                                rows, lines, physics = audit(directory, r, app.engine["id"], allow_va_history=include_va_history, allow_ohio_provisional=allow_ohio_provisional)
                                reuse = True
                            except (AssertionError, ValueError, OSError, KeyError):
                                # Preserve the old attempt; a failed audit cannot stay a pass.
                                reuse = False
                            timing["resume_audit_seconds"] = time.monotonic()-audited
                    if reuse:
                        entry = deepcopy(prior)
                        session["reused_cases"] += 1
                        entry.setdefault("resume_checks", []).append({"checked_at": utc_now(), "timing": timing})
                        print(identity, "reused after fingerprint and independent audit checks", flush=True)
                    else:
                        if prior:
                            entry["attempts"] = deepcopy(prior.get("attempts", []))+[archived_attempt(prior)]
                            if prior.get("study_id"):
                                previous_state = app.store.get(prior["study_id"])
                                if previous_state["status"] in ("queued", "running", "cancelling"):
                                    app.store.cancel(prior["study_id"])
                        entry["request_fingerprint"] = value_hash(r)
                        job = app.store.submit(r, app.engine)
                        session["executed_cases"] += 1
                        entry.update(study_id=job["id"], status="queued", validation="pending", timing=timing)
                        manifest["cases"] = [entry if e["case"] == identity else e for e in manifest["cases"]]
                        if prior is None:
                            manifest["cases"].append(entry)
                        write_json(output/"validation.json", manifest)
                        waiting = time.monotonic()
                        deadline = waiting+case_timeout
                        marker = None
                        while True:
                            state = app.store.get(job["id"])
                            current = (state["status"], state["progress"])
                            if current != marker:
                                print(identity, *current, flush=True)
                                marker = current
                            if state["status"] in ("completed", "failed", "cancelled"):
                                break
                            if time.monotonic() >= deadline:
                                app.store.cancel(job["id"])
                                raise TimeoutError("Regional case exceeded its validation deadline; cancellation requested.")
                            time.sleep(min(1., max(.01, deadline-time.monotonic())))
                        timing["queue_and_worker_wait_seconds"] = time.monotonic()-waiting
                        timing["worker_reported_seconds"] = state.get("runtime_seconds")
                        entry["status"] = state["status"]
                        if state["status"] != "completed":
                            raise ValueError(state.get("error") or "Worker did not complete")
                        directory = output/"runs"/job["id"]
                        audited = time.monotonic()
                        rows, lines, physics = audit(directory, r, app.engine["id"], allow_va_history=include_va_history, allow_ohio_provisional=allow_ohio_provisional)
                        timing["artifact_audit_seconds"] = time.monotonic()-audited
                        entry.update(validation="passed", physics=physics,
                            is_complete_bill=bool(rows.is_complete_bill.all()),
                            objective_scope="provisional_modeled_bill" if (rows.objective_scope=="provisional_modeled_bill").any() else "complete_utility_bill" if rows.is_complete_bill.all() else "verified_charges_subtotal",
                            rate_evidence_status="provisional" if (rows.rate_evidence_status=="provisional").any() else "verified" if (rows.rate_evidence_status=="verified").all() else "not_recorded",
                            request_sha256=digest(directory/"request.json"),
                            source_artifacts={p.name: digest(p) for p in directory.iterdir() if p.suffix in (".csv", ".json")})
                    for frame in (rows, lines):
                        frame.insert(0, "case", identity)
                    monthly.append(rows); components.append(lines)
                    comparison = pd.read_csv(directory/"comparison.csv")
                    comparison.insert(0, "case", identity); summaries.append(comparison)
                except (AssertionError, ValueError, OSError, KeyError) as exc:
                    if "Prepared case inputs changed" in str(exc):
                        # Never replace evidence with results from altered inputs.
                        preserve_prior = True
                        raise
                    entry.update(validation="failed", error=str(exc)); failures.append(identity)
                    if isinstance(exc, TimeoutError):
                        entry["status"] = "timed_out"
                except KeyboardInterrupt:
                    entry.update(validation="interrupted", status="interrupted")
                    raise
                finally:
                    if waiting is not None:
                        timing.setdefault("queue_and_worker_wait_seconds", time.monotonic()-waiting)
                    timing["total_seconds"] = time.monotonic()-case_started
                    if not reuse:
                        entry["timing"] = timing
                    if preserve_prior:
                        pass
                    elif prior is None and not any(e["case"] == identity for e in manifest["cases"]):
                        manifest["cases"].append(entry)
                    elif prior is not None:
                        manifest["cases"] = [entry if e["case"] == identity else e for e in manifest["cases"]]
                    write_json(output/"validation.json", manifest)
        loop_finished = True
    finally:
        app.close()
        session.update(finished_at=utc_now(), elapsed_seconds=time.monotonic()-started,
            status="completed" if loop_finished and not failures else "failed_or_interrupted")
        if validated:
            write_json(output/"validation.json", manifest)
    for filename, frames in (("monthly-comparison.csv", monthly), ("billing-components.csv", components), ("study-comparison.csv", summaries)):
        if frames:
            pd.concat(frames, ignore_index=True).to_csv(output/filename, index=False)
    if components:
        annual = pd.concat(components, ignore_index=True).groupby(["case", "scenario", "component"], as_index=False).amount_usd.sum()
        baseline = annual.loc[annual.scenario == "grid_only"].set_index(["case", "component"]).amount_usd
        annual["savings_vs_grid_usd"] = [baseline.get((row.case, row.component), 0.)-row.amount_usd for row in annual.itertuples()]
        annual.to_csv(output/"period-components.csv", index=False)
    summarize(output)
    if failures:
        raise ValueError("Validation failed for "+", ".join(failures)+"; inspect the private validation.json")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=ROOT/".cache/regional_historical_inputs/weather")
    parser.add_argument("--output", type=Path, default=ROOT/".cache/regional_validation")
    parser.add_argument("--prepare-inputs", action="store_true", help="Retrieve actual NSRDB2025/ERA5September2026 weather; never silently substitute")
    parser.add_argument("--execute", action="store_true", help="Explicitly run all studies using a new immutable source pin")
    parser.add_argument("--summarize", action="store_true", help="Rebuild the private JSON summary from an existing validation folder, without API calls")
    parser.add_argument("--include-ciep", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Reuse only same-pin/input/validator cases after artifact verification and independent re-audit")
    parser.add_argument("--case-timeout", type=positive_seconds, default=2100., help="Per-case queue/worker deadline in seconds; requests cancellation on expiry")
    parser.add_argument("--allow-ohio-provisional", action="store_true", help="Explicitly accept documented Ohio Edison2025 provisional rate and billing assumptions; never verified coverage")
    parser.add_argument("--include-va-history", action="store_true", help="Also prepare/run 2025 VA-1/GS1 verified-charge subtotals, with explicitly missing historical taxes")
    parser.add_argument("--ciep-inputs", type=Path, default=ROOT/".cache/regional_historical_inputs/pseg")
    parser.add_argument("--utility", action="append", choices=tuple(SITES), help="Limit preparation/execution to named utility; repeatable")
    parser.add_argument("--plan", action="append", help="Limit execution to named plan IDs after optional cases are added; repeatable")
    parser.add_argument("--period", action="append", choices=("monthly","annual","custom"), help="Limit execution period; custom requires explicit inclusive dates and is used alone")
    parser.add_argument("--start-date",help="Custom inclusive local start date YYYY-MM-DD; no weather retrieval or year shifting")
    parser.add_argument("--end-date",help="Custom inclusive local end date YYYY-MM-DD")
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    try:
        periods=validation_periods(tuple(args.period or ("monthly","annual")),args.start_date,args.end_date)
    except ValueError as exc:
        parser.error(str(exc))
    if "custom" in periods and (not args.execute or args.prepare_inputs):
        parser.error("Custom dates require --execute with explicitly prepared cached weather; custom weather preparation is not implemented.")
    if args.resume and (not args.execute or args.prepare_inputs):
        parser.error("--resume requires --execute without input retrieval")
    if args.prepare_inputs:
        prepare_inputs(args.inputs, env_file=args.env_file, utilities=args.utility, include_va_history=args.include_va_history,
            va_history_only=bool(args.include_va_history and args.plan and set(args.plan).issubset({"VA-1","VA-GS1"})))
    if args.execute:
        try:
            selected = selected_cases(args.utility, args.plan, include_ciep=args.include_ciep,
                                      include_va_history=args.include_va_history)
        except ValueError as exc:
            parser.error(str(exc))
        run(args.output, args.inputs, ciep_inputs=args.ciep_inputs,
            include_va_history=args.include_va_history, allow_ohio_provisional=args.allow_ohio_provisional, cases=selected, periods=periods,
            start_date=args.start_date,end_date=args.end_date, resume=args.resume, case_timeout=args.case_timeout)
    if args.summarize:
        summarize(args.output)
    if not args.prepare_inputs and not args.execute and not args.summarize:
        parser.print_help()


if __name__ == "__main__":
    main()
