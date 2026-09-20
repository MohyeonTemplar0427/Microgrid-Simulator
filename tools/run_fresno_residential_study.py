"""Reproduce the real-data Fresno pilot; network access only with --download.

Optional study dependency: pyarrow==19.0.1 (may live in .cache/residential_python).
Large source files stay in .cache; compact evidence and results go to results.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".cache/residential_python"))

import numpy as np
import pandas as pd
import requests

from src.profiles.residential import (
    Provenance, ResidentialProfile, TemperatureWeather, WeatherResponseModel,
    aggregate_population, coarsen_profile, compare_profiles, read_noaa_global_hourly,
    read_resstock_csv,
)

BASE = "https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/"
REGION = "Fresno County, CA (G0600190)"
CACHE = ROOT / ".cache/residential_fresno"
TOTAL = "out.electricity.total.energy_consumption..kwh"
NET = "out.electricity.net.energy_consumption..kwh"
PROVENANCE = Provenance(REGION, "ResStock 2025.1; stock circa 2018; upgrade 0", "amy2018",
                        BASE, "America/Los_Angeles")
SOURCE_URLS = {
    "metadata.parquet": BASE + "metadata_and_annual_results/by_state/full/parquet/state=CA/CA_upgrade0.parquet",
    "weather_2018.csv": BASE + "weather/state=CA/G0600190_2018.csv",
    "dictionary.tsv": BASE + "data_dictionary.tsv",
    "noaa_2018.csv": "https://www.ncei.noaa.gov/data/global-hourly/access/2018/72389093193.csv",
    "noaa_2024.csv": "https://www.ncei.noaa.gov/data/global-hourly/access/2024/72389093193.csv",
    "cec_county_monthly.xlsx": "https://www.energy.ca.gov/filebrowser/download/9337?fid=9337",
    "eia_state_end_uses.xlsx": "https://www.eia.gov/consumption/residential/data/2020/state/xls/ce4.1.el.st.xlsx",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fetch(url, path, download):
    if path.exists():
        return path
    if not download:
        raise FileNotFoundError(f"Missing cached input {path}; run with --download.")
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    if path.suffix == ".xlsx" and not response.content.startswith(b"PK"):
        raise ValueError(f"Expected XLSX data, received a different response from {url}")
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_bytes(response.content)
    temporary.replace(path)
    return path


def select_population(county, size=64, seed=20260920):
    """Stratified random sample by dwelling type and installed cooling.

    Two or more per stratum, remaining slots allocated proportional to stock.
    Study weights expand sampled homes to the full stratum. Annual energy is
    deliberately NOT used for selecting a favorable sample.
    """
    frame = county.sort_values("bldg_id").copy()
    frame["stratum"] = frame["in.geometry_building_type_recs"] + " | " + np.where(
        frame["in.hvac_cooling_type"] == "None", "no cooling", "cooling installed")
    groups = list(frame.groupby("stratum", sort=True))
    if size < 2 * len(groups) or size > len(frame):
        raise ValueError("Sample size must permit at least two homes per stratum and not exceed population.")
    counts = np.array([len(g) for _, g in groups])
    allocations = np.minimum(2, counts)
    while allocations.sum() < size:
        priority = counts / len(frame) * size - allocations
        priority[allocations >= counts] = -np.inf
        allocations[np.argmax(priority)] += 1
    rng = np.random.default_rng(seed)
    selected, strata = [], []
    for (name, group), n in zip(groups, allocations):
        if not np.allclose(group.weight, group.weight.iloc[0]):
            raise ValueError("This sampling design expects equal published weights within strata.")
        chosen = group.iloc[rng.choice(len(group), int(n), replace=False)].copy()
        chosen["study_weight"] = float(group.weight.sum()) / int(n)
        chosen["inclusion_probability"] = int(n) / len(group)
        selected.append(chosen)
        strata.append(dict(stratum=name, population_models=len(group), sample_models=int(n),
                           represented_dwellings=float(group.weight.sum())))
    return pd.concat(selected).sort_values("bldg_id"), strata


def prepare_dwelling(bldg_id, download):
    import pyarrow.parquet as pq
    path = CACHE / f"dwelling_{bldg_id}.csv.gz"
    evidence = CACHE / f"dwelling_{bldg_id}.json"
    if path.exists() and evidence.exists():
        return path, json.loads(evidence.read_text())
    if not download:
        raise FileNotFoundError(f"Missing dwelling {bldg_id}; run with --download.")
    url = BASE + f"timeseries_individual_buildings/by_state/upgrade=0/state=CA/{bldg_id}-0.parquet"
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    data = io.BytesIO(response.content)
    names = pq.read_schema(data).names
    columns = [c for c in names if c.startswith("out.electricity.") and c.endswith("..kwh")]
    columns += ["timestamp", "out.outdoor_air_drybulb_temp..c"]
    data.seek(0)
    frame = pd.read_parquet(data, columns=columns)
    frame.to_csv(path, index=False, compression={"method": "gzip", "mtime": 0})
    record = dict(url=url, original_parquet_sha256=hashlib.sha256(response.content).hexdigest(),
                  normalized_csv_sha256=sha(path), columns=columns, building_id=int(bldg_id))
    evidence.write_text(json.dumps(record, indent=2))
    return path, record


def component_name(column):
    return column.split(".")[2]


def response_mapping(columns):
    return {c: "cooling" if c in {"cooling", "cooling_fans_pumps"} else
            "heating" if c.startswith("heating") else "schedule" for c in columns}


def save_profile(profile, output, name):
    profile.frame().to_csv(output / f"{name}.csv.gz", index=False,
                           compression={"method": "gzip", "mtime": 0})
    (output / f"{name}.json").write_text(json.dumps(profile.manifest(), indent=2, allow_nan=False))


def run(output, download=False):
    output.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCE_URLS.items():
        fetch(url, CACHE / name, download)
    metadata = pd.read_parquet(CACHE / "metadata.parquet")
    county = metadata.loc[(metadata["in.county"] == "G0600190") & (metadata.completed_status == "Success")].copy()
    selected, strata = select_population(county)
    metadata_columns = ["bldg_id", "weight", "study_weight", "stratum", "inclusion_probability",
                        "in.county", "in.county_name", "in.cec_climate_zone",
                        "in.geometry_building_type_recs", "in.hvac_cooling_type", "in.heating_fuel", TOTAL]
    selected[metadata_columns].to_csv(output / "selected_households.csv", index=False)
    pd.DataFrame(strata).to_csv(output / "sampling_strata.csv", index=False)
    print(f"Selected {len(selected)} of {len(county)} county models", flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        files = list(pool.map(lambda i: prepare_dwelling(int(i), download), selected.bldg_id))
    print("Dwelling downloads/extraction complete", flush=True)
    profiles, evidence, temp_frames = [], [], []
    for (path, record), (_, row) in zip(files, selected.iterrows()):
        raw = pd.read_csv(path)
        mapping = {component_name(c): c for c in raw if c.startswith("out.electricity.")
                   and c.endswith("..kwh") and component_name(c) not in {"total", "net", "pv"}}
        # Source rounds energy columns to 5 decimal places. Worst-case sum of
        # independent rounding errors: (n components + total) * half-unit.
        tolerance = (len(mapping) + 1) * .000005 * 4 + 1e-6
        p = read_resstock_csv(path, provenance=replace(PROVENANCE, source=record["url"]),
            end_use_columns=mapping, total_column=TOTAL, unit="kWh", timestamp_convention="end",
            source_timezone="Etc/GMT+5", timestep_minutes=15, rounding_tolerance_kw=tolerance)
        p = coarsen_profile(p, 60)
        profiles.append(p)
        temperatures = raw["out.outdoor_air_drybulb_temp..c"].to_numpy().reshape(-1, 4).mean(axis=1)
        temp_frames.append(temperatures)
        evidence.append(record)
    # All county homes must use the same weather. Do not average away a mismatch.
    if not all(np.allclose(t, temp_frames[0], atol=1e-5) for t in temp_frames):
        raise ValueError("County homes have different weather; model separate weather groups.")
    population = aggregate_population(profiles, selected.study_weight, households=100)
    weather = TemperatureWeather(pd.DataFrame({"temperature_c": temp_frames[0]}, index=population.end_uses_kw.index),
        60, REGION, "amy2018", "ResStock embedded outdoor-air temperature (same simulation intervals)",
        {"origin": "ResStock weather constructed from NOAA ISD, NSRDB and MesoWest",
         "timestamp_basis": "EST interval ends converted to UTC interval starts"})
    # Publication wraps the final 3 local hours into the start of the EST year.
    # Exclude those from fitting/validation; preserve original full-year replay.
    fit_start = pd.Timestamp("2018-01-01 00:00", tz="Etc/GMT+8")
    usable = population.end_uses_kw.index >= fit_start
    training_population = replace(population, end_uses_kw=population.end_uses_kw.loc[usable])
    training_weather = replace(weather, frame=weather.frame.loc[usable])
    mapping = response_mapping(population.end_uses_kw.columns)
    # Real held-out contiguous period; no calibration or threshold selection on it.
    split = pd.Timestamp("2018-09-01", tz="Etc/GMT+8")
    before = training_population.end_uses_kw.index < split
    train = replace(training_population, end_uses_kw=training_population.end_uses_kw.loc[before])
    train_w = replace(training_weather, frame=training_weather.frame.loc[before])
    valid = replace(training_population, end_uses_kw=training_population.end_uses_kw.loc[~before])
    valid_w = replace(training_weather, frame=training_weather.frame.loc[~before])
    held_model = WeatherResponseModel.fit(train, train_w, response_by_end_use=mapping)
    predicted = held_model.predict(valid_w, allow_extrapolation=True)
    metrics = compare_profiles(predicted, valid.native_load_kw)
    metrics["reference"] = "Held-out ResStock simulated Sep-Dec loads; NOT measured-household validation"
    metrics["relative_energy_bias_pct"] = 100 * metrics["energy_bias_kwh"] / valid.energy_kwh().sum()
    metrics["normalized_rmse_pct"] = 100 * metrics["rmse_kw"] / valid.native_load_kw.mean()
    metrics["extrapolated_intervals"] = predicted.diagnostics["extrapolated_intervals"]
    end_use_metrics = []
    for c in valid.end_uses_kw:
        error = predicted.end_uses_kw[c] - valid.end_uses_kw[c]
        end_use_metrics.append(dict(end_use=c, rmse_kw=float(np.sqrt((error**2).mean())),
            reference_kwh=float(valid.energy_kwh()[c]), predicted_kwh=float(predicted.energy_kwh()[c])))
    pd.DataFrame(end_use_metrics).to_csv(output / "held_out_end_use_metrics.csv", index=False)
    save_profile(population, output, "published_100_homes_2018")
    save_profile(predicted, output, "held_out_prediction_2018")
    model = WeatherResponseModel.fit(training_population, training_weather, response_by_end_use=mapping)
    save_profile(model.predict(training_weather), output, "fitted_2018")
    scenarios, noaa_weather = {}, {}
    for year in [2018, 2024]:
        w = read_noaa_global_hourly(CACHE / f"noaa_{year}.csv", station="72389093193", region=REGION,
            weather_id=f"noaa-fresno-{year}", start=f"{year}-06-01T00:00:00-08:00", end=f"{year}-10-01T00:00:00-08:00")
        noaa_weather[year] = w
        scenarios[year] = model.predict(w, allow_extrapolation=True)
        save_profile(scenarios[year], output, f"noaa_summer_{year}")
        w.frame.rename_axis("timestamp").to_csv(output / f"noaa_summer_temperature_{year}.csv")
    # Isolate temperature from differences in weekday/weekend calendar:
    matched_frame = noaa_weather[2024].frame.copy()
    matched_frame.index = noaa_weather[2018].frame.index
    matched = replace(noaa_weather[2024], frame=matched_frame,
                      weather_id="2024 summer temperatures on 2018 summer calendar",
                      diagnostics={**noaa_weather[2024].diagnostics,
                                   "calendar_reassignment": "Same month/day/hour; 2024 temperatures assigned to 2018 timestamps"})
    temperature_only = model.predict(matched, allow_extrapolation=True)
    save_profile(temperature_only, output, "temperature_only_2024_on_2018_calendar")
    station_error = (noaa_weather[2018].frame.temperature_c -
                     training_weather.frame.temperature_c.reindex(noaa_weather[2018].frame.index))
    weather_comparison = dict(
        station_minus_simulation_mean_c=float(station_error.mean()),
        station_vs_simulation_rmse_c=float(np.sqrt((station_error**2).mean())),
        noaa_summer_mean_c={str(y): float(w.frame.temperature_c.mean()) for y, w in noaa_weather.items()})
    summaries = []
    for name, p in [("published_2018_full", population), ("noaa_summer_2018", scenarios[2018]),
                    ("noaa_summer_2024", scenarios[2024]), ("temperature_only_2024", temperature_only)]:
        summaries.append(dict(scenario=name, hours=len(p.end_uses_kw), households=p.households,
            kwh_per_home=float(p.energy_kwh().sum()/p.households),
            cooling_kwh_per_home=float((p.energy_kwh().cooling+p.energy_kwh().cooling_fans_pumps)/p.households),
            peak_kw_per_home=float(p.native_load_kw.max()/p.households),
            extrapolated_hours=p.diagnostics.get("extrapolated_intervals", 0)))
    pd.DataFrame(summaries).to_csv(output / "scenario_summary.csv", index=False)
    energies = population.energy_kwh() / population.households
    pd.DataFrame({"kwh_per_home": energies, "share_pct": energies / energies.sum()*100}).to_csv(output / "end_use_breakdown.csv", index_label="end_use")
    # Sampling discrepancy against all county ResStock annual models, not meters.
    county_mean = float(np.average(county[TOTAL], weights=county.weight))
    sample_mean = float(np.average(selected[TOTAL], weights=selected.study_weight))
    # Design-based SE for stratified SRS, finite-population correction included.
    variance = 0.0
    for name, group in county.assign(stratum=county["in.geometry_building_type_recs"] + " | " + np.where(
            county["in.hvac_cooling_type"] == "None", "no cooling", "cooling installed")).groupby("stratum"):
        sample = selected[selected.stratum == name]
        variance += (group.weight.sum()/county.weight.sum())**2 * (1-len(sample)/len(group)) * sample[TOTAL].var(ddof=1)/len(sample)
    # Independent CEC county totals: retain as context, do not force calibration
    # across unresolved purchased/net-vs-gross and occupied-dwelling boundaries.
    cec = pd.read_excel(CACHE / "cec_county_monthly.xlsx")
    cec = cec[(cec.COUNTY_NAME == "FRESNO") & (cec.SECTOR == "Residential") & cec.YEAR.isin([2018, 2024])]
    cec.to_csv(output / "cec_county_residential_context.csv", index=False)
    # Save source EIA California row(s) verbatim for audit, not a county target.
    book = pd.ExcelFile(CACHE / "eia_state_end_uses.xlsx")
    eia_rows = []
    for sheet in book.sheet_names:
        frame = pd.read_excel(book, sheet_name=sheet, header=None)
        for _, row in frame.loc[frame.apply(lambda r: r.astype(str).str.strip().eq("California").any(), axis=1)].iterrows():
            eia_rows.append({"sheet": sheet, "values": [None if pd.isna(v) else v for v in row.tolist()]})
    if not eia_rows:
        raise ValueError("EIA workbook has no California row; check source schema.")
    eia_physical = next(r["values"] for r in eia_rows if r["sheet"] == "physical units")
    eia_context = dict(year=2020, geography="California", housing_units_million=eia_physical[1],
        electricity_billion_kwh=eia_physical[2], shares_pct=dict(
            space_heating=eia_physical[4], water_heating=eia_physical[6],
            air_conditioning=eia_physical[8], refrigerators=eia_physical[10], other=eia_physical[12]))
    summary = dict(region=REGION, release=PROVENANCE.release, population_models=len(county),
        sample_models=len(selected), seed=20260920, county_represented_dwellings=float(county.weight.sum()),
        full_county_mean_kwh=county_mean, sample_mean_kwh=sample_mean,
        sample_discrepancy_pct=100*(sample_mean/county_mean-1), sampling_standard_error_kwh=float(np.sqrt(variance)),
        climate_zone_model_counts=county["in.cec_climate_zone"].value_counts().to_dict(),
        installed_cooling_weighted_pct=float(np.average(county["in.hvac_cooling_type"] != "None", weights=county.weight)*100),
        held_out=metrics, scenarios=summaries, weather_comparison=weather_comparison,
        eia_california_context=eia_context, eia_raw_rows=eia_rows,
        cec_annual_context_gwh=cec.groupby("YEAR").GWH.sum().to_dict(),
        calibration_applied=False, empirical_household_validation=False,
        timestamp_audit="Published EST interval-end; 3 wrapped hours excluded from fitting; exact embedded simulation temperatures used",
        limitations=["64-model pilot; stock sampling uncertainty remains.",
          "Fresno County is not an exact PG&E service-area boundary and includes more than one climate zone.",
          "County simulation weather and airport observations are not identical.",
          "RECS California 2020 and CEC county statistics retained as context, not forced gross-load calibration.",
          "PG&E E-1/RES is a class-average profile; not a Fresno-specific validation series.",
          "Temperature-only fixed-stock scenarios; no adoption, efficiency, humidity, lag or capacity-limit model.",
          "Held-out reference is a building simulation, not independent measured demand."])
    (output / "study_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False))
    (output / "sources.json").write_text(json.dumps({"sources": [dict(name=n,url=u,sha256=sha(CACHE/n)) for n,u in SOURCE_URLS.items()],
        "dwellings": evidence, "retrieved_utc": pd.Timestamp.now(tz="UTC").isoformat()}, indent=2))
    draw_report(population, predicted, valid, scenarios, summary, output)
    print(json.dumps({k: summary[k] for k in ["sample_mean_kwh", "sample_discrepancy_pct", "held_out", "scenarios"]}, indent=2), flush=True)


def draw_report(population, prediction, reference, scenarios, summary, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10})
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    energy = population.energy_kwh().sort_values(ascending=False).head(10)/population.households
    energy.iloc[::-1].plot.barh(ax=axes[0,0], color="#357a9c")
    axes[0,0].set(title="Published 2018: largest electricity end uses", xlabel="kWh per represented home")
    for name, p in [("Published ResStock", population), ("Held-out reference", reference), ("Held-out prediction", prediction)]:
        local = p.native_load_kw.tz_convert("Etc/GMT+8")
        local = local.loc[local.index >= pd.Timestamp("2018-01-01", tz="Etc/GMT+8")]
        local.resample("MS").mean().plot(ax=axes[0,1], label=name)
    axes[0,1].set(title="Monthly average demand — 100-home community", ylabel="kW", xlabel="Month");axes[0,1].legend()
    for year, p in scenarios.items():
        local = p.native_load_kw.tz_convert("America/Los_Angeles") / p.households
        local.groupby(local.index.hour).mean().plot(ax=axes[1,0], label=f"NOAA {year} summer")
    axes[1,0].set(title="Fixed-stock modeled summer demand", xlabel="Local clock hour", ylabel="kW per home");axes[1,0].legend()
    x = reference.native_load_kw.resample("D").mean();y = prediction.native_load_kw.resample("D").mean()
    axes[1,1].scatter(x,y,s=12,alpha=.7);bound=[min(x.min(),y.min()),max(x.max(),y.max())]
    axes[1,1].plot(bound,bound,"k--",linewidth=1)
    axes[1,1].set(title="Held-out September–December daily means", xlabel="ResStock reference kW", ylabel="Surrogate prediction kW")
    fig.suptitle("Fresno County residential pilot • 64 sampled models • simulated loads", fontsize=16)
    fig.savefig(output / "study_overview.png", dpi=160)
    plt.close(fig)
    rows = "\n".join(f"| {s['scenario']} | {s['hours']} | {s['kwh_per_home']:.1f} | {s['cooling_kwh_per_home']:.1f} | {s['peak_kw_per_home']:.3f} |" for s in summary["scenarios"])
    report = f"""# Fresno County residential pilot

Real ResStock and NOAA inputs; **simulated electricity demand**, not measured Fresno household loads.

## Scope and sampling

ResStock 2025.1 baseline, circa-2018 housing stock, AMY2018. County G0600190.
64 seeded, stratified samples from {summary['population_models']} county models;
dwelling type and installed cooling shares are preserved by expansion weights.
The study produces a 100-home expected community profile, not 100 independent occupant simulations.
Full county modeled mean: {summary['full_county_mean_kwh']:.1f} kWh/home/year.
Sample mean: {summary['sample_mean_kwh']:.1f}; discrepancy {summary['sample_discrepancy_pct']:+.2f}%.
Estimated sampling standard error: {summary['sampling_standard_error_kwh']:.1f} kWh/home/year;
this excludes building-model and geographic errors. Selection did not use annual energy.

## Scenario results

| Scenario | Hours | Total kWh/home | Cooling + fan kWh/home | Coincident peak kW/home |
|---|---:|---:|---:|---:|
{rows}

Summer is June–September in fixed Pacific Standard Time, 2,928 hours in each year.
The temperature-only scenario assigns 2024 summer temperatures to the identical
2018 month/day/hour calendar, isolating temperature from weekday/weekend changes.
Actual-year scenarios use their actual calendar. Stock and equipment are fixed.
Extrapolation counts are in scenario_summary.csv. No temperature gaps were filled.

## Held-out test

Fit January–August; test September–December 2018 against excluded ResStock outputs.
RMSE: {summary['held_out']['rmse_kw']:.2f} kW for 100 homes;
normalized RMSE: {summary['held_out']['normalized_rmse_pct']:.1f}%;
energy bias: {summary['held_out']['relative_energy_bias_pct']:+.1f}%.
This is surrogate validation against a simulator, **not empirical validation**.
Final scenario model is subsequently fitted on the complete usable 2018 baseline.
Thresholds (18°C heating/22°C cooling) were not tuned on the test period.

## Source and boundary audit

Exact source URLs and hashes: sources.json. Selected IDs and weights:
selected_households.csv. All end uses: end_use_breakdown.csv.
Input energy is converted from kWh/15-minute to average kW, EST interval-end to
UTC interval-start, then averaged to hourly. A bounded rounding reconciliation
preserves the authoritative gross total. Three year-wrapped local hours are
excluded from fitting. Matched simulation weather comes directly from the same
dwelling output timestamps, avoiding a guessed weather-file timezone.

EIA RECS California 2020 rows are preserved in study_summary.json. They describe
a different geography/year and are not used to force Fresno calibration.
Statewide electricity shares: 4% space heating, 5% water heating, 18% air
conditioning, 13% refrigerators, 60% other (published rounded percentages).
The ResStock breakdown resolves many of those other uses explicitly; remaining
plug loads still represent a broad category.
CEC Fresno residential monthly totals are in cec_county_residential_context.csv;
the QFER/self-generation accounting and dwelling/customer denominators still
require reconciliation before they are defensible gross-load targets.
Existing PG&E E-1/RES files describe a customer class, not Fresno County.
They are therefore contextual evidence, not a validation target.

## Limitations and next decision

""" + "\n".join("- " + s for s in summary["limitations"]) + """

Next: inspect the held-out error by end use and season, then reconcile a local
gross-consumption benchmark before applying calibration. Increase the sample
before adopting the absolute load level: this pilot underestimates the full
county simulation mean by about 10%. Browser code and
existing reference datasets are unchanged.

## Reproduce

From the repository root, with pyarrow==19.0.1 available (the study also looks
in .cache/residential_python):

```bash
/usr/local/bin/python3 tools/run_fresno_residential_study.py --download
```

Omit --download to replay from cache without network access. Data selection,
seed, source release, sample size and fitting split are fixed in the script.
Outputs are overwritten in results/residential_fresno_pilot (or --output).
"""
    (output / "README.md").write_text(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT/"results/residential_fresno_pilot")
    args = parser.parse_args()
    run(args.output, args.download)
