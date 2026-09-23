# Weather coverage and occupied-home calibration

The NOAA input files span the full UTC calendar years. Under accepted TMP
quality flags 1/5 and the hourly aggregation used by the backend, 2018 lacks
82 usable hours (1 in January, 81 in November); leap-year 2024 lacks 2 usable
hours (March 14 01:00 UTC and May 1 07:00 UTC). Both June–September fixed-PST
windows have zero missing hours. Details: weather_coverage_audit.json.
These are gaps after screening, not a claim that NOAA has no observations.

The summer-only comparison is a study choice, not a model restriction.
Full-year estimates need a documented gap policy: short isolated gaps can be
interpolated and flagged after checking adjacent observations; longer gaps
need a checked secondary station or gridded weather source. Local-calendar
years also need the adjoining UTC-year boundary observations. No filling or
full-year NOAA prediction has been performed in this study.

The separate published ResStock baseline already spans a full year. The
weather surrogate is trained against matched embedded simulation weather;
NOAA record gaps do not truncate the published baseline.

Occupied homes are selected before sampling and weighting. Existing all-unit
studies are preserved. A 100-home output now means 100 occupied homes.

Local calibration should match occupied-home gross consumption, geography,
weather year, timestamps and equipment mix. With monthly observations, start
with a small set of identifiable parameters: a background-load multiplier
and heating/cooling response multipliers, constrained by plausible ranges.
Reserve months or households before fitting and report monthly energy,
hourly shape (if available), and peak errors. Monthly totals alone cannot
validate hourly peaks or separately calibrate every appliance category.

For homes with PV/batteries, utility-meter energy is not automatically gross
household demand. Obtain appropriately measured generation, import/export
and battery flows, or instead compare modeled meter flows with observations.
County CEC totals include vacant-unit use and have unresolved residential
self-generation coverage in the exported rows. They are not yet an exact
occupied-home target; no calibration factor has been applied.
