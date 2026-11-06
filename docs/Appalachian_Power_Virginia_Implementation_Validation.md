# Appalachian Power Virginia implementation and validation

Recorded November 4, 2026 on `main`, base commit `6d51e06`. The checkout
was clean before edits. The [utility guide](Appalachian_Power_Virginia.md)
defines the RS 015 and SGS 231 non-export Standard Service scope and the
[dated ledger](utility_sources/appalachian_va/sources.json) records tariff
sources, rate evidence grades, locality and interconnection rules.

## Source and bill checks

| Calendar cycle | RS 015 at 1,000 kWh before external taxes | SGS 231 at 1,000 kWh before external taxes |
| --- | ---: | ---: |
| January 2025 | $173.95 | $154.86 |
| November 2025 | $163.88 | $144.61 |
| January 2026 | $163.70 | $144.43 |
| October 2026 dated reconstruction | $169.85 | $148.41 |
| November 2026 | $169.35 | $147.91 |

The four available dated APCo charge tables were compared with filed rider
arithmetic. The October checks instead use the independently transcribed
applicable sheets and the superseded PIPP rate. The official 2025 and 2026
archive gaps are described in the ledger. The January 2025 SGS comparison
uses the later corrected summary and Sheet 59. The older illustrative
summary shows a conflicting energy-efficiency rider. At 1,000 kWh the
November 2026 RS result also matches the utility's headline example.
Its 2,000 kWh headline doubles the fixed charge and is excluded as a bill
benchmark. The itemized benchmark applies the basic charge once. The filed
generation credit uses its exact percentage, while the utility table displays
rounded unit rates.

The consumption tax checks use the actual state levy, its effective
versions, and the separate Roanoke consumer utility tax. City rates are
from the City's current published tax guidance with historical residential
corroboration in the FY2025–26 county comparison. An independent full City
ordinance revision history and exact invoice rounding remain outside the
evidence. No real customer bill or written special agreement was supplied.
The validation equipment cases explicitly model hypothetical approved
agreements that preserve ordinary billing. The application's actual-account
scope requires independent written approval for the exact configuration.

## Targeted validation

The frozen engine is
`bde153332feebad38b8cf51ce5e1268d0a6f33685a525b47e1d55023e7fcea3a`.
The [candidate receipt](../.cache/apco_va/candidate_frozen.json) pins the
runtime, unchanged frontend, tests, tooling, and source and weather manifests.
The adapter adds utility-specific account fields, registry, counterfactual,
browser wiring and historical case selection. Shared billing math, solver,
physics, API schema and frontend code are unchanged. Full release testing
and desktop GUI compatibility were outside targeted acceptance.

The [focused launcher receipt](../.cache/apco_va/acceptance_final/report.json)
records **187 passed**, with zero failures, errors or skips. The first attempt
had two test failures because a carbon compatibility fixture selected a
November 2026 cycle that had not ended. The fixture now uses the completed
November 2025 cycle. The runtime and frontend pins are the same. Carbon
coverage itself was not retrieved or tested.

```sh
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_appalachian_va.py --test test/test_appalachian_va_integration.py \
  --test test/test_regional_counterfactual.py --test test/test_regional_coverage.py \
  --test test/test_regional_validation_driver.py --test test/test_regional_weather_timezones.py \
  --test test/test_validation_launcher.py \
  --regional --utility appalachian_power_virginia --period monthly \
  --inputs .cache/apco_va/weather --output .cache/apco_va/acceptance_final

/usr/local/bin/python3 tools/run_regional_validation.py --execute \
  --utility appalachian_power_virginia --period custom \
  --start-date 2026-01-01 --end-date 2026-01-31 \
  --inputs .cache/apco_va/weather --output .cache/apco_va/historical_2026
```

The selected matrix has grid-only, PV-only and PV-plus-battery cases for
both plans. November 2025 uses historical ERA5 and covers the fall DST
transition. January 2026 uses the same site and exact-year ERA5, with the
new 2026 S.U.T. rider. The two historical dates use separate driver runs
because the launcher cannot select disjoint date windows. The November 2026
queued-worker integration uses clear-sky weather and verifies the securitized
rate stack, settings restoration, and exact CSV and ZIP bytes. January 2025
and October 2026 received bill, effective-date and source checks without
separate electrical runs. The available October ERA5 response lacked the
end of that cycle.

| Period | Weather | Studies | Scenario bills | OpenDSS intervals |
| --- | --- | ---: | ---: | ---: |
| November 2025 | Site-matched ERA5 | 2 | 6 | 17,304 |
| January 2026 | Site-matched ERA5 | 2 | 6 | 17,856 |
| November 2026 | Modeled clear sky | 2 | 6 | 17,304 |

Every interval in each selected study was checked. All 12 primary bill-cost
and six battery minimum-cycling proofs passed, with a maximum
optimization-to-rebill difference of approximately $0.000001. The
[independent Decimal re-audit](../.cache/apco_va/independent_rebill.json)
reconciled all **18 bills** and checked 52,464 saved electrical rows. Its
largest raw component difference was below $0.00000000000004. Results use
synthetic native loads and representative circuits. There was no annual
study or site-specific electrical claim. The
[coverage report](../.cache/apco_va/coverage.md) and
[weather receipt](../.cache/apco_va/weather/weather-input-manifest.json)
retain the selected cases and inputs. The launcher reported 19.67 s for
the tests and 14.64 s for its matrix phase. The January driver session took
10.87 s. These are phase/session durations, not development time.

## Browser acceptance

The frozen browser pass rendered the saved November 2026 SGS case. It
restored the Virginia account, PJM AEP identity, city tax confirmation,
hypothetical special-agreement terms, and the 12 recorded demand values.
The wizard reached review and submitted a rerun. The browser timed out
waiting for the Save result button and that route stopped. The worker later
completed, with exact input equality and the same three bill totals. Fresh
result rendering, save and reopen remain unverified in the UI. The
[seed study](http://127.0.0.1:59174/#b3ac895b9e4649b8a7dc021b2b49d3d3)
and [browser receipt](../.cache/apco_va/browser_acceptance.json) preserve
the split between browser observations and saved-artifact checks. No browser
download or file-picker automation was used.

The changes remain unstaged on `main`. No commit, push, deployment or
stable-engine promotion was performed.
