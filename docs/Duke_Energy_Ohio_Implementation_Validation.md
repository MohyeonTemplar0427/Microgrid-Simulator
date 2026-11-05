# Duke Energy Ohio implementation and validation

Recorded November 4, 2026 on `main` at base commit `85545a3`. The [account guide](Duke_Energy_Ohio.md) defines ordinary single-phase RS and retained DM SSO, non-export equipment and complete June 2025 and October 2026 cycles. All other periods reject pending verification. The [source ledger](utility_sources/duke_ohio/sources.json) pins both tariff books, the separate October DCI revision and the official calculator workbooks with page locators and hashes.

## Evidence and tariff boundaries

The June PUCO book and October PUCO book establish the dated rate stack. October's book has an older DCI sheet even though the index dates the new revision to October 1. The separate filed Duke Sheet 103.46 establishes 18.624% and supersedes the July 18.124% sheet. Sheet 126.5 withdraws PSR from June 1, 2025. The older Sheet 85.2 rider matrix also predates the DM DDR addition, residential DSM/DSMR and USR-to-PIPP replacement. The later filed rider terms govern their applicability. Ohio law and the OET filing are recorded separately. The October retail rider follows its printed kWh blocks, corroborated by the workbook, while the distributor's statutory non-30-day remittance rules differ.

Independent [Duke calculator checks](../.cache/duke_ohio/benchmarks/duke_official_calculators_20261104.md) cover 15 single-phase cases across both classes and rate periods, including DM at 2,800 and 6,000 kWh and October RS above 1,000 kWh. Recalculation confirmed that spreadsheet rounding of distribution, RC and RE blocks explains all observed differences of up to **$0.0104** versus unrounded filed arithmetic. The DM workbook visually labels the first OET quantity as 2,800 in one cell, but its tax formulas use 2,000. At 750 kWh the filed RS total rounded at the end agrees with the [PUCO survey](../.cache/duke_ohio/benchmarks/puco_utility_rate_survey_20261103.md) at **$145.15** for June and **$143.76** for October. The survey's Duke commercial series is DP primary and was excluded from DM benchmarking. Invoice rounding remains unverified.

## Frozen candidate and selected checks

Engine `2213f660a46351a49183f45930bba6b7fdc272504b552a33fb0b512cdf9a26b4`. The [frozen receipt](../.cache/duke_ohio/candidate_frozen.json) pins runtime source, frontend, test and tool hashes, the tariff ledger and the accepted weather input receipt. The additive registry, default-site, counterfactual and validator wiring uses the existing worker, API schema, dispatch, battery physics and OpenDSS replay. No JavaScript changes. Desktop GUI and full release testing were excluded under the targeted policy. The initial sandboxed development check recorded 58 passes and two loopback permission errors. The final loopback-enabled run passed **218 tests** with zero errors, failures or skips.

```sh
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_duke_oh.py --test test/test_duke_oh_integration.py \
  --test test/test_regional_counterfactual.py --test test/test_regional_coverage.py \
  --test test/test_regional_validation_driver.py --test test/test_regional_weather_timezones.py \
  --test test/test_validation_launcher.py \
  --regional --utility duke_energy_ohio --period monthly \
  --inputs .cache/duke_ohio/weather --output .cache/duke_ohio/acceptance
```

The [launcher receipt](../.cache/duke_ohio/acceptance/report.json) records 24.70 s for the tests and 20.74 s for the June matrix. June has **17,280** OpenDSS checks across all intervals of its six selected cases, using site- and year-matched Open-Meteo ERA5 and synthetic native loads. The October queued-worker tests add **17,856** checks across six complete-cycle **modeled clear-sky** cases. The retrieved ERA5 series returned missing hourly values from October 30 at 00:00 UTC, preventing an all-interval historical October study. The [weather receipt](../.cache/duke_ohio/weather/weather-input-manifest.json) records both the accepted June input and the rejected October response. The supported dates exclude a full year and the DST transition months, so tests exercise the DST grids and fail-closed date rejection. All scenario electrical checks are representative.

| Period and weather | Plan | Grid only | PV only | PV plus battery |
| --- | --- | ---: | ---: | ---: |
| June 2025 ERA5 | RS | $214.92 | $138.96 | $114.79 |
| June 2025 ERA5 | DM | $587.73 | $418.74 | $398.56 |
| October 2026 clear sky | RS | $211.48 | $149.25 | $117.85 |
| October 2026 clear sky | DM | $600.56 | $422.82 | $393.45 |

Eight optimized cycle bill-cost proofs and four battery minimum-cycling proofs passed. Maximum optimization-to-rebill difference was approximately $0.000001. An [independent Decimal re-audit](../.cache/duke_ohio/independent_audit.json) rebilled all 12 saved scenarios from their meter flows with maximum component difference of $3×10⁻¹⁴, and checked alignment and feasibility of the 35,136 saved electrical rows. The [historical case manifest](../.cache/duke_ohio/acceptance/regional/validation.json) and [coverage report](../.cache/duke_ohio/coverage.md) record the June artifacts at this candidate pin. October integration separately verified saved settings and each returned CSV/ZIP table against the saved bytes.

## Browser acceptance

The one frozen-candidate pass opened a saved October DM clear-sky case. It restored the provider, Ohio SSO and PJM DEOK identity, exact demand history, UE-GEN facts, date window and native load selection through the review screen. The browser submitted a new study, rendered all three bills, saved the result, opened the RS result, and reopened the new saved DM result from history. The new saved request matched the original request field for field. The browser rerun added 8,928 clear-sky electrical intervals, reported separately from the matrix and integration evidence. Its worker reported 8.66 s. Browser file-picker and download event automation were outside this pass. The [saved result preview](http://127.0.0.1:59173/#22ac4886e535428293d71727366cd89b), [screenshot](../.cache/duke_ohio/browser_acceptance.jpg) and [browser receipt](../.cache/duke_ohio/browser_acceptance.json) record this result.

The working tree retains the changes unstaged. No commit, push, deployment or stable-engine promotion was performed.
