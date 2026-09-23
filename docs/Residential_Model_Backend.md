# Residential reference modeling backend

This opt-in Python module supports two study paths:

1. Replay and weight published ResStock dwelling end-use profiles.
2. Fit a temperature-response surrogate to matched load/weather, then generate
   a fixed-population scenario under another actual weather year.

It does not change browser controls, API routes, saved-study schemas, tariff
selection, existing load-source defaults, or existing PG&E reference files.
Import from `src.profiles.residential` explicitly. No new dependencies.

## Current boundary

Implemented: local CSV import with provenance and SHA-256 fingerprints; weighted
populations; gross-electricity end-use energy calibration; NOAA temperature
quality screening; surrogate fitting and prediction; comparison metrics; CLI
exports; an adapter to the existing `LoadProfileSource` interface.

Not claimed: a downloaded/validated PG&E population, automatic county-to-utility
mapping, EIA workbook/API parsing, live downloads, an EnergyPlus/ResStock rerun,
humidity/solar/thermal-lag effects, forecasts of appliance adoption, stochastic
appliance events, or validated out-of-sample regional accuracy. Test inputs are
explicit synthetic fixtures, not official ResStock or NOAA data.

Region is an explicit study identifier. Choose a PG&E climate subregion only
after selecting its dwelling stock, station, and geographic evidence. Labeling
California-wide benchmarks as a PG&E subregion is not valid calibration.

## Source selection

- ResStock: https://resstock.nlr.gov/datasets and
  https://natlabrockies.github.io/ResStock.github.io/docs/data.html
- RECS: https://www.eia.gov/consumption/residential/data/2020/index.php?view=consumption
- EIA-861: https://www.eia.gov/electricity/data/eia861/
- NOAA Global Hourly: https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database
- PG&E-specific local calibration evidence: CEC 2019 RASS,
  https://www.energy.ca.gov/publications/2021/2019-california-residential-appliance-saturation-study-rass

Choose a release with dwelling-level time series and identify its stock and
weather years separately. The release label is not the weather year. Training
requires the matching actual-weather identifier and timestamps. A single TMY
profile can be imported with the Python adapter, but population aggregation and
weather-model fitting reject TMY to prevent incoherent regional weather events.

## Published profile input

`read_resstock_csv` accepts a local CSV for **one dwelling**, using a mapping
from study end-use names to the actual release's column headers. Export Parquet
to CSV separately if needed; do not treat preweighted aggregate files as homes.

Required choices:

- `unit`: `kWh` per interval or interval-average `kW`. Never guessed.
- `timestamp_convention`: `start` or `end`; interval-end input is shifted back
  exactly one interval.
- `timestep_minutes`: actual source resolution.
- `source_timezone`: required for naive timestamps. For local standard time,
  use the documented fixed offset (e.g. `Etc/GMT+8` means UTC-08:00), not a DST
  zone. Mixed aware offsets are supported; ambiguous naive DST times fail.
- `end_use_columns`: disjoint electricity components, never a total plus its
  children. Exclude PV, gas, battery flows, and net-load columns.
- `total_column` (recommended): gross electricity total, which is not summed
  again. Unmapped energy becomes an explicit `unallocated` end use; a sum above
  the total fails (1e-6 kW rounding tolerance). Without total, mapping
  completeness cannot be verified and the manifest says so.

Missing/nonfinite/negative loads, duplicated or irregular timestamps fail.
No years are copied, repeated, or shifted to satisfy a requested horizon.

## Reproducible CLI

Run from the project root:

```bash
/usr/local/bin/python3 -m src.profiles.residential study.json --output results/residential_trial
```

Paths in the configuration are relative to the configuration file. Outputs are
`residential_load.csv` (UTC interval-start timestamps, per-end-use kW, and
`native_load_kw`) and `manifest.json` (source identifiers, fingerprints,
weights, represented households, energy totals and model diagnostics).
The command overwrites these two named files in the chosen output directory.

Example configuration, with **illustrative input headers**, not a bundled
dataset or an assertion about the column names in a particular release:

```json
{
  "schema_version": 1,
  "mode": "published",
  "provenance": {
    "region": "YOUR_VERIFIED_REGION",
    "release": "YOUR_RESSTOCK_RELEASE_AND_STOCK_YEAR",
    "weather_id": "amy2018",
    "weather_kind": "actual",
    "source": "EXACT_DATASET_URL_OR_IDENTIFIER",
    "timezone": "America/Los_Angeles"
  },
  "households": 100,
  "timestep_minutes": 60,
  "profiles": [
    {
      "path": "inputs/dwelling.csv",
      "weight": 1,
      "timestep_minutes": 15,
      "unit": "kWh",
      "timestamp_convention": "end",
      "source_timezone": "Etc/GMT+8",
      "end_use_columns": {
        "cooling": "cooling_kwh",
        "heating": "heating_kwh",
        "appliances": "appliances_kwh"
      },
      "total_column": "gross_electricity_kwh"
    }
  ]
}
```

Add more dwelling entries and their documented stock weights. Weights are
represented dwelling counts; `households` rescales their mix to the requested
community size. Omitting it preserves their sum. This weighted sum is an
expected population profile, not 100 independently simulated occupants.
Matching region/release/weather/timezone/grids/components are required.

The optional top-level `timestep_minutes` explicitly coarsens each profile
using averages and preserves energy. Partial coarse bins fail. The initial
NOAA adapter produces hourly weather, so use hourly load for this workflow.
Upsampling is not implemented: repeating hourly data would not recover
15-minute peaks. Published 15-minute load can still be replayed at 15 minutes.

## Weather-responsive path

Change `mode` to `weather_response` and add:

```json
{
  "training_weather": {
    "path": "inputs/noaa_training.csv",
    "station": "EXACT_STATION_ID",
    "weather_id": "amy2018"
  },
  "prediction_weather": {
    "path": "inputs/noaa_scenario.csv",
    "station": "EXACT_STATION_ID",
    "weather_id": "amy2024"
  },
  "response_by_end_use": {
    "cooling": "cooling",
    "heating": "heating",
    "appliances": "schedule",
    "unallocated": "schedule"
  },
  "heating_balance_c": 18,
  "cooling_balance_c": 22,
  "allow_extrapolation": false
}
```

NOAA input needs `STATION`, `DATE` (UTC), and `TMP` (e.g. `+0250,1`). The
default accepted temperature QC flags are `1` and `5` (passed quality checks).
Missing sentinels, other flags, and impossible Celsius values are excluded;
an hour without accepted observations fails. Repeated instants are averaged,
then accepted observations are averaged per hour. No neighboring station or
missing hour is silently substituted. Clip files to the same complete training
period in advance. Record how the chosen station represents the study region.

The Python `TemperatureWeather` class also accepts an already screened,
regular timezone-aware temperature frame, including 15-minute inputs when
those are supported by actual source data.

Every end use must be explicitly classified. Do not assume `unallocated` is
weather-insensitive without investigating its composition. Air handlers can be
classified separately by heating/cooling operation. A gas-heated home can
still have heating-related electric fan demand.

The fitted surrogate is:

```
component_kw(t) = weekday_or_weekend_hour_intercept(t)
                  + nonnegative_slope * degree_difference(t)
cooling degree_difference = max(temperature - cooling_balance, 0)
heating degree_difference = max(heating_balance - temperature, 0)
schedule degree_difference = 0
```

Fit uses within-hour temperature variation to distinguish schedule from
weather. It requires every weekday/weekend hour and fails unidentifiable
temperature responses. A zero component stays zero: the model does not invent
AC adoption. A full annual training set is preferable to the minimum schedule
coverage; winter-only data cannot identify unobserved summer cooling.
Balance temperatures are configurable assumptions to evaluate on held-out
data, not geographic constants. Nonnegative coefficients are fitted by
convergent block coordinate least squares.

Prediction holds household stock and equipment fixed. By default it rejects
temperatures outside the training range. Explicitly enabled extrapolation
records affected intervals, but still does not capture capacity saturation,
humidity, thermal memory, or extreme-event physics. Coefficients and training
errors are exported; training error is not validation. No full building
simulator is installed or invoked by this path.

## EIA/local calibration

The optional `benchmarks_csv` points to a **normalized** table with columns:

```
region,start,end,end_use,kwh_per_household,source,basis
```

`start` and exclusive `end` must have explicit UTC offsets and exactly cover
the input load period. `basis` defaults to `gross_electricity`; `grid_sales`
is rejected. Targets must use kWh per **all represented dwellings**, not kWh
per household using a particular appliance. Convert conditional-use RECS
means using equipment prevalence before using them, and align geography and
year. Account count and dwelling count are not automatically interchangeable.

For each supplied disjoint end use the scaling factor is:

```
target kWh per dwelling * represented dwellings / modeled component kWh
```

Unspecified components remain unchanged. Scaling a zero end use to positive
energy fails. Factors and source references are recorded. Calibration happens
on the training baseline **before** weather-response fitting, never by forcing
a hot-weather prediction back to normal-year energy. This first version scales
end uses; it does not optimize stock weights or propagate survey uncertainty.
Utility grid-sales data need explicit PV/battery and population reconciliation
outside this adapter before becoming gross-load targets.

## Programmatic use and validation

```python
from src.profiles.residential import ResidentialLoad, compare_profiles

# result is the ResidentialProfile from run_study() or model.predict().
load_source = ResidentialLoad(result)
native_kw = load_source.build_load_kw(existing_interval_index)
# Independent held-out gross meter series, same instants and interval length:
metrics = compare_profiles(result, held_out_gross_load_kw)
```

The existing adapter requires exact resolution and complete horizon coverage;
it can select a covered subperiod without changing energy values. DST folds
are distinct instants. Output remains gross load; downstream PV/battery
accounting is unchanged. No browser integration is enabled.

Validation should use excluded years or households, compare monthly energy,
hourly shape, extremes, and coincident peaks, and check measurement boundaries
in the PG&E E-1/RES data. `compare_profiles` supplies RMSE, MAE, energy bias,
and peak bias. Its reference must be gross nonnegative load, not an unexplained
net-meter series. Do not use total balancing-authority load as residential
ground truth.

Offline regression tests:

```bash
/usr/local/bin/python3 -m pytest -q test/test_residential_model.py
```

## Real-data Fresno pilot

Run `python3 tools/run_fresno_residential_study.py --download` to acquire the
pinned public sources and generate the study; omit `--download` for an offline
cache replay. The script requires pyarrow (tested with 19.0.1), openpyxl,
requests and matplotlib in addition to the backend dependencies.
See `results/residential_fresno_pilot/README.md` for results, limitations,
source hashes, selected building IDs, and sampling weights.

This pilot uses 64 stratified ResStock AMY2018 county models, exact embedded
simulation temperatures, and complete June–September NOAA records for 2018
and 2024. EIA California 2020 and CEC Fresno totals are contextual evidence;
no cross-geography or net/gross calibration is applied. The 100-home output
is a weighted expected community, not 100 independently simulated homes.

The source adapter accepts `rounding_tolerance_kw` for documented source
precision. Within that bound, negative closure residuals proportionally reduce
mapped end uses to preserve the authoritative total; the energy correction is
recorded. Larger deficits fail. Positive residuals remain `unallocated`.
The pilot computes its bound from the source's five-decimal kWh precision.

`read_noaa_global_hourly` accepts paired timezone-aware, hour-aligned `start`
and exclusive `end` arguments. Every hour in that window must have an accepted
temperature observation, including boundary hours; missing hours are never
filled. This allows a complete summer study despite gaps elsewhere in a year.

### Expanded Fresno study and benchmark audit

The expanded run is saved separately in `results/residential_fresno_expanded`,
preserving the 64-model pilot. Reproduce it with `--sample-size 256 --output
results/residential_fresno_expanded`. The sample size is chosen before inspecting
annual energy. This is a new stratified draw with the same seed and design,
not a nested extension of the pilot. The plot shows the published reference
for all twelve months, one held-out prediction line, and the train/test divider.

Run `python3 tools/reconcile_fresno_benchmarks.py` after that study to compare
sampling uncertainty and local benchmark accounting. Its report records CEC
annual county totals, full-population ResStock gross and signed-net energy,
and a Census housing-count cross-check. Signed-net energy is not positive grid
imports. ResStock includes vacant housing units; counts of occupied households
and utility accounts cannot silently replace its denominator. The CEC export
does not isolate residential self-generation. Diagnostic ratios are therefore
exported without modifying the load profiles or enabling calibration.

### Occupied-home study

For community load estimates, exclude vacant units before sampling and
recomputing expansion weights:

```bash
python3 tools/run_fresno_residential_study.py --occupied-only --sample-size 256 --download --output results/residential_fresno_occupied
```

The selected-household export includes vacancy status; the summary and profile
provenance diagnostics record `occupied_housing_units`. The reference annual
mean and sampling error are computed against occupied county models only.
The earlier all-unit studies remain available as historical comparisons.
County-wide CEC energy still includes vacant-unit consumption and must not be
divided by occupied households and used as an exact calibration target without
reconciling that contribution.

## Full local-year hourly generator: Fresno and Alameda

The reusable CLI defaults to occupied homes, 256 stock models, 100 represented
homes, and weather year 2024. Available counties are `fresno` and `alameda`:

```bash
python3 tools/build_county_residential_year.py --county fresno --download
python3 tools/build_county_residential_year.py --county alameda --download
```

Use `--year`, `--sample-size`, `--households`, and `--output` to configure a run.
Omit `--download` for cache-only operation. The shared California source cache
uses the existing `.cache/residential_fresno` directory; building IDs and station
IDs keep counties' data distinct. No UI registration or browser code is changed.

Each output directory contains:

- `hourly_load_with_quality.csv`: UTC interval start, local timestamp with offset,
  disjoint end-use kW, `native_load_kw`, temperature, weather quality,
  temperature-extrapolation flag, and represented occupied-home count.
- `hourly_load.csv.gz` and `hourly_load.json`: the existing profile format and
  manifest, including coefficients, weather source, and occupied-stock basis.
- `weather_hourly_audit.csv`: observed and used temperatures; interpolated
  observations remain blank in the observed column.
- `monthly_energy.csv`: local-month kWh, elapsed hours, average kW, kWh/home.
- `summary.json`, `sources.json`, and selected model IDs/weights for audit.

`annual_noaa_weather` constructs the full local-calendar-year UTC index. For
2024, it contains 8,784 elapsed hours, including both fall-back hours. It reads
adjoining 2025 UTC observations for the end of December 31 in Pacific time.
It accepts temperature QC flags 1/5, averages duplicate timestamps and then
reports within each hour, and rejects missing boundary hours. The generator
explicitly permits only isolated interior one-hour gaps, linearly interpolated
between adjacent accepted hours; longer gaps fail without partial filling.
Every replacement is flagged. The original strict NOAA reader is unchanged.

The 2024 Fresno and Oakland station series each require two such replacements.
Oakland International Airport is the initial Alameda proxy. Alameda's inland
microclimates are not spatially weighted in this first county scenario; do not
treat Oakland weather as equally representative of every Alameda household.
Livermore's checked 2024 series has a longer gap and is not silently substituted.

The population and equipment remain circa 2018. Weather-year changes do not
imply updated heat-pump/EV adoption, efficiency or occupancy distributions.
The estimates remain uncalibrated, and held-out tests compare to simulation,
not customer meters. County-total calibration requires accounting reconciliation.

Offline verification:

```bash
python3 -m pytest -q test/test_residential_annual_weather.py test/test_residential_model.py test/test_site_profile.py
```

## Alameda regional stock and weather split

```bash
python3 tools/build_alameda_regional_year.py --download
```

The regional study selects occupied Alameda stock by `in.cec_climate_zone`:
zone 3 is the Bay-side proxy group; zone 12 metadata identifies Livermore,
Pleasanton and Dublin. It draws 128 models per group, with dwelling-type and
cooling-ownership strata inside each group. Actual stock expansion weights,
not sample counts, determine county shares (approximately 86.3% / 13.7%).
Per-group profiles represent 100 occupied homes; the county profile represents
100 occupied homes distributed across the two groups. `--households` changes
the county total, while per-group exports remain normalized to 100 homes.

`combine_regional_profiles` sums already-scaled regional loads on identical
grids and checks their occupied-home basis, stock release and end-use mapping.
It does not average temperatures before estimating demand. Contribution
manifests record scaling and the 100-home coefficient basis.

Zone 3 uses Oakland temperatures. Zone 12 uses Livermore, whose 2024 record
has 66 missing accepted hourly values. `regional_noaa_weather` replaces them
with Oakland plus month/hour mean Livermore-minus-Oakland offsets. Offset
validation withholds days 10–11 of each month; only observed paired data fit
offsets. Final gap reconstruction uses all valid pairs. The held-out weather
RMSE is approximately 2.59°C; replacements are estimates and are flagged.
One replacement relies on an isolated interpolated Oakland temperature,
which is separately flagged. Raw observed temperatures remain available.
Missing backup coverage or fewer than 10 month/hour pairs fails explicitly.

The study compares against both the previous county model and a controlled
same-stock/same-regional-model all-Oakland counterfactual. Only the latter
isolates prediction-weather effects. It also shifts replacement temperatures
by plus/minus held-out RMSE as a sensitivity check, not a confidence interval.

Both stock groups' original simulations used county-assigned Hayward weather.
The regional split preserves those matched training pairs; it does not rerun
EnergyPlus under inland baseline weather. Extrapolation flags remain material,
particularly inland. Empirical accuracy improvement and local calibration
have not been established. No browser integration is changed by this study.

Outputs: `results/residential_alameda_regional_2024/`, including per-region
and combined hourly CSVs, quality flags, monthly energy, summaries and hashes.
