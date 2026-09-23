# Alameda County, CA: 2024 occupied-home hourly load

Generated 8,784 consecutive hourly rows for the complete local calendar
year, representing 100 occupied homes. All timestamps identify interval
starts. UTC timestamps are unique; local timestamps include offsets for DST.
Loads are interval-average kW, so one hourly row contributes that many kWh.

Main deliverable: hourly_load_with_quality.csv. It includes each end use,
`native_load_kw`, temperature, weather-quality flag, extrapolation flag,
local timestamp and occupied-home count. monthly_energy.csv supplies monthly
kWh, average kW and elapsed-hour counts. hourly_load.json records fitted
coefficients and provenance; sources.json records input hashes and URLs.

## Weather and model limits

Station: Oakland International Airport (72493023230). 2
interior missing hours were interpolated between accepted adjacent observations;
every replacement is flagged in weather_hourly_audit.csv. Gaps longer than one
hour and missing boundary hours are rejected. Adjoining 2025 UTC observations
supply the end of the local year. 20 hours
lie outside the simulation training temperature range and are explicitly flagged.

Stock and equipment remain at the ResStock circa-2018 baseline. This is a weather
scenario, not a forecast incorporating 2024 adoption, efficiency or household
changes. Vacant units are excluded before sampling and weighting. The sample
contains 256 of 2306 occupied county models; its baseline annual
mean differs from the full occupied county model population by
+0.91%.

The airport is a weather proxy, not spatially weighted county weather. Alameda
in particular spans coastal Oakland and warmer inland locations; a county-wide
absolute estimate needs geographically matched stock/weather groups. The current
county model is a documented initial scenario. No local calibration is applied.

Held-out September–December simulation test: energy bias
+1.16%, hourly normalized RMSE 12.25%.
This measures agreement with ResStock, not measured-household validation. Heating,
cooling, and hourly schedules are approximations; humidity and thermal lag are absent.

## Reproduce

```bash
python3 tools/build_county_residential_year.py --county alameda --year 2024 --sample-size 256 --households 100 --download --output /Users/junhayang/Desktop/EnergyEngineerSession/Microgrid_Simulator/results/residential_alameda_2024_hourly
```

Omit --download for a cache-only replay. No browser feature is changed.
