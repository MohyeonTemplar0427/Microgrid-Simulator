# Fresno County residential pilot

Real ResStock and NOAA inputs; **simulated electricity demand**, not measured Fresno household loads.

## Scope and sampling

ResStock 2025.1 baseline, circa-2018 housing stock, AMY2018. County G0600190.
256 seeded, stratified samples from 1236 county models;
dwelling type and installed cooling shares are preserved by expansion weights.
The study produces a 100-home expected community profile, not 100 independent occupant simulations.
Population basis: **occupied_housing_units**.
Vacant units are excluded when the occupied-only option is selected.
Full county modeled mean: 10574.4 kWh/home/year.
Sample mean: 10397.8; discrepancy -1.67%.
Estimated sampling standard error: 247.5 kWh/home/year;
this excludes building-model and geographic errors. Selection did not use annual energy.

## Scenario results

| Scenario | Hours | Total kWh/home | Cooling + fan kWh/home | Coincident peak kW/home |
|---|---:|---:|---:|---:|
| published_2018_full | 8760 | 10397.8 | 3802.5 | 3.282 |
| noaa_summer_2018 | 2928 | 4637.6 | 2641.1 | 3.377 |
| noaa_summer_2024 | 2928 | 4938.9 | 2948.4 | 3.852 |
| temperature_only_2024 | 2928 | 4938.9 | 2948.4 | 3.852 |

Summer is June–September in fixed Pacific Standard Time, 2,928 hours in each year.
The temperature-only scenario assigns 2024 summer temperatures to the identical
2018 month/day/hour calendar, isolating temperature from weekday/weekend changes.
Actual-year scenarios use their actual calendar. Stock and equipment are fixed.
Extrapolation counts are in scenario_summary.csv. No temperature gaps were filled.

## Held-out test

Fit January–August; test September–December 2018 against excluded ResStock outputs.
RMSE: 16.52 kW for 100 homes;
normalized RMSE: 15.5%;
energy bias: +1.7%.
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

- 256-model study; stock sampling uncertainty remains.
- Fresno County is not an exact PG&E service-area boundary and includes more than one climate zone.
- County simulation weather and airport observations are not identical.
- RECS California 2020 and CEC county statistics retained as context, not forced gross-load calibration.
- PG&E E-1/RES is a class-average profile; not a Fresno-specific validation series.
- Temperature-only fixed-stock scenarios; no adoption, efficiency, humidity, lag or capacity-limit model.
- Held-out reference is a building simulation, not independent measured demand.

Next: inspect the held-out error by end use and season, then reconcile a local
gross-consumption benchmark before applying calibration. Increase the sample
as needed before adopting the absolute load level; assess the sampling
discrepancy and standard error reported above. Browser code and
existing reference datasets are unchanged.

## Reproduce

From the repository root, with pyarrow==19.0.1 available (the study also looks
in .cache/residential_python):

```bash
/usr/local/bin/python3 tools/run_fresno_residential_study.py --download --sample-size {summary['sample_models']} {"--occupied-only" if summary.get("population_basis") == "occupied_housing_units" else ""} --output {output}
```

Omit --download to replay from cache without network access. Data selection,
seed, source release and fitting split are fixed in the script.
Use --sample-size to change the sample size (default 64).
Outputs are overwritten in results/residential_fresno_pilot (or --output).
