# Alameda regional occupied-home scenario, 2024

Split by ResStock CEC climate-zone metadata, not invented city boundaries.
Zone 12 metadata names Livermore, Pleasanton and Dublin; zone 3 is the Bay-side
proxy group. Hills and transition areas are not separately resolved.
128 homes per group by default are independently sampled within dwelling-type
and cooling-ownership strata. Sample proportions are NOT county proportions.
Population expansion weights set each group's contribution to 100 occupied homes.

| Group | CEC zone | County occupied share | Installed cooling | Annual kWh/home | Sample baseline error vs full group |
|---|---:|---:|---:|---:|---:|
| bay_side | 3 | 86.30% | 70.0% | 7177 | +1.02% |
| inland | 12 | 13.70% | 75.9% | 9493 | -2.05% |

## Outputs and comparisons

combined_hourly_load_with_quality.csv contains 8784 UTC hourly intervals,
local timestamps, end uses, total kW, regional contributions, temperatures and
quality/extrapolation flags. Group files each represent 100 occupied homes;
combined contributions use the county shares above. monthly_energy_kwh.csv
contains local-calendar monthly energy. Manifests and source hashes accompany data.

Combined annual estimate: 7494.8 kWh/home.
Compared with the SAME region-specific stock and fitted models all receiving
Oakland weather, using Livermore inland changes annual energy by
+2.27%. The separate comparison to the old
county model also changes sampling and fitting; it is not purely a weather effect.

## Weather and validity

Bay-side uses Oakland; inland uses Livermore. Oakland has two isolated hourly
interpolations. Livermore has 66 missing hours, replaced using Oakland plus a
month/hour station-difference correction. One replacement also relies on an
interpolated Oakland hour. All replacements are flagged. Correction validation
holds days 10–11 of each month out of offset fitting; metrics are in summary.json.
These are estimated replacements, not observations. The gap sensitivity shifts
only replacement temperatures by plus/minus held-out RMSE; it is not a confidence interval.

ResStock assigned the same Hayward baseline weather to these county homes,
including inland models. Fits use their matched embedded 2018 temperatures;
we did NOT rerun inland EnergyPlus with Livermore baseline weather. Higher
inland temperatures can therefore require extrapolation, explicitly flagged.
Stock remains circa 2018. This split improves geographic detail, but increased
empirical accuracy is not established. No local calibration has been applied.

CEC climate-zone reference: https://www.energy.ca.gov/programs-and-topics/programs/building-energy-efficiency-standards/climate-zone-tool-maps-and

## Reproduce

```bash
python3 tools/build_alameda_regional_year.py --download --sample-size 128 --households 100 --output /Users/junhayang/Desktop/EnergyEngineerSession/Microgrid_Simulator/results/residential_alameda_regional_2024
```

Omit --download to replay cached inputs. Browser features remain unchanged.
