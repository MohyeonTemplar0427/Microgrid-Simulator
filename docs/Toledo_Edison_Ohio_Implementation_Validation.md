# Toledo Edison Ohio implementation and validation

Recorded November 1, 2026. This is targeted local-development acceptance for
Toledo Edison **RS residential** and measured **GS secondary** with ordinary
Standard Service Offer (SSO). Complete matching calendar service/bill cycles
are verified for **January and June 2025, September–November 2025, and October
2026**. Other dates reject; full-year 2025 coverage is unavailable.

The [utility guide](Toledo_Edison_Ohio.md) records eligibility, component units,
tax and billing rules, DER restrictions and unsupported dates. The
[aggregate source ledger](utility_sources/toledo_oh/sources.json) pins 39
retained evidence files and links independent delivery, supply/tax and rules
reviews. Original PDFs, download receipts, selected page images and blocked
source receipts are private under `../.cache/toledo_oh/sources/`.

## Candidate and impact

Work began on clean `main` at
`62d3ed9037bd43e128ed536ab645409b312fd209`. The frozen engine is
`74af60638fd3fcb70809a5a6f8bede09b088cccb7b0d4daae8e71843bd0d46ab`.
The [freeze receipt](../.cache/toledo_oh/candidate_frozen_1.json) retains 246
runtime Python hashes, 11 frontend hashes and source-manifest SHA-256
`10aa75b4c3bb2ec22633d39dc72192924c3c4143f90e1cef0dbb6200dd000624`.
The frontend is unchanged. Final hashes and Git state are recorded in the
[integrity receipt](../.cache/toledo_oh/final_integrity_1.json).

New `src/billing/toledo_oh.py` and `toledo_oh_rates.py` supply utility-specific
account checks and dated numeric/symbolic bill components. Additive entries
connect the regional registry, grid-only counterfactual, browser account/default
site, validation selection and coverage tools. Existing worker/API contracts,
solver, time grid, PV/storage physics, credit logic and electrical replay are
reused. Population-proxy documentation and regression guards include Toledo.

Toledo GS uses the highest **15-minute integrated import kW**, independently
verified in both schedule versions. Billing demand retains the maximum of
that peak, 5 kW and the documented Company contract. The first-five-kW amount
is flat monthly; there is no history ratchet. Neither the 30-minute CEI rule
nor another affiliate's rates are substituted. The synthetic GS account has
an explicit hypothetical 12 kW contract in all scenarios.

January uses the applicable VMC revision, base-only percentage DCR and PIR;
ordinary credits, signed October 2026 DUN/PUR, RER/CCR transition and separate
automaker recovery remain itemized. State-kWh tax uses statutory local-day
bands, its specified CAT gross-up and wired-electricity sales-tax exemption.
Utility, SSO supplier arrangement, Ohio jurisdiction, PJM/ATSI metadata,
wholesale pricing and optional PJM regional-average carbon remain separate.

## Targeted checks

The [launcher report](../.cache/toledo_oh/acceptance_1/report.json) records
**336 passed, zero failed, zero errors and zero skipped** on the frozen
candidate. This is a focused-tier policy selection, not a full-release pass.

```text
/usr/local/bin/python3 tools/validate.py --tier focused
  --test test/test_toledo_oh.py
  --test test/test_toledo_benchmarks.py
  --test test/test_toledo_integration.py
  --test test/test_pjm_population_coverage.py
  --test test/test_regional_counterfactual.py
  --test test/test_regional_coverage.py
  --test test/test_regional_validation_driver.py
  --test test/test_regional_weather_timezones.py
  --test test/test_validation_launcher.py
  --regional --utility firstenergy_ohio_toledo --period custom
  --start-date 2025-09-01 --end-date 2025-11-30
  --inputs .cache/toledo_oh/weather --output .cache/toledo_oh/acceptance_1
```

The command above is wrapped for readability; the report retains exact argv.
Checks cover all six supported months and blocked adjacent periods, source
versions, independent component arithmetic, numeric/symbolic parity, the
15-versus-30-minute discriminator, contract/floor rules, half-cent boundaries,
non-30-day statutory tax thresholds, DST, missing/duplicate/out-of-order data,
eligibility and unsupported export/standalone storage. Sixty independently
specified benchmarks include 36 numeric bills, 10 symbolic cases, 12 tax
boundaries and two half-cent/contract cases.

Four queued-worker integration cases cover RS/GS in June 2025 and October
2026, saved settings, account/grid-only contracts and saved CSV/ZIP artifacts.
Python syntax, unchanged regional JavaScript syntax and whitespace checks
passed. GUI modules were excluded and no desktop GUI was launched. Full
workflow/release tiers and unaffected utilities' matrices were excluded because
this addition does not change shared behavior or API/worker contracts.

## Historical billing, dispatch and electrical acceptance

One selected matrix covers **September 1–November 30, 2025** with both tariffs
and grid-only, PV-only and PV-plus-battery operation. This is **two fresh
studies, six scenarios, 18 cycle bills and 52,440 OpenDSS interval checks**,
with zero failed intervals. Every selected scenario interval was checked;
the period is a three-month sample of supported coverage, not an annual pass.

| Plan | Study ID | Grid-only bill | PV-only bill | PV + battery bill | Electrical intervals across three scenarios |
| --- | --- | ---: | ---: | ---: | ---: |
| RS | `6a6339cec9a648c7923874be47077093` | $604.78 | $431.47 | $362.81 | 26,220 |
| GS | `f926d82cea984db7a19f335233e40cc4` | $2,919.79 | $2,545.95 | $2,404.66 | 26,220 |

The period crosses October rider boundaries and the November DST fall-back;
November has 721 elapsed hours but 30 local tax days. Each scenario has 8,740
intervals. All 12 optimized primary cycle proofs and six battery secondary
minimum-cycling proofs passed, with zero strict fallback cycles. Six grid-only
cycle bills are direct calculations and make no optimizer claim. Maximum
reported primary gap and reconciliation difference are approximately
`1.00001023e-6 USD`. Rolling cycles preserve SOC and account obligations;
they do not establish a jointly optimized annual result or rounded-cash optimum.

The exact hypothetical site's 2025 ERA5 hourly reanalysis came through
Open-Meteo, with original response hash, grid coordinates, attribution and
sampling method retained. Prepared-input SHA-256 is
`6765041e8207c423283d62ea89733744b1d94613808ab20e336b00696b026bc5`.
Hourly radiation means are held over four 15-minute intervals; they are not
on-site measurements. Native loads are deterministic generic synthetic
archetypes, serialized as imported intervals, not measured or regionally
calibrated customer data. The default Wood County location, interconnection,
contract and service wiring are hypothetical. Representative electrical
feasibility is not surveyed-site, protection, transient or dynamic validation.

The [matrix summary](../.cache/toledo_oh/acceptance_1/regional/validation-summary.json)
retains original artifacts and proof labels. A separate
[independent auditor](../.cache/toledo_oh/independent_audit.py), importing no
production billing/rate/math code, reconciled all 18 bills and re-audited all
52,440 saved electrical rows, native flow and SOC recursion. The
[receipt](../.cache/toledo_oh/independent_audit_1.json) records maximum raw
component difference `5.684341886080802e-14 USD` and zero exact-Decimal
half-cent exceptions for these cases. Exact printed-invoice rounding is not
claimed; saved raw floating-point components are reconciled before the shared
half-up component rounding convention.

## Browser and artifact acceptance

One concise browser pass used the same frozen candidate at
[the private preview](http://127.0.0.1:59171/). Both RS and GS October 2026
seed results rendered. GS settings restored the explicit 15-minute demand,
12 kW contract, supplier/account facts, native CSV, hypothetical calendar,
non-export PV/storage and modeled clear-sky weather. The browser submission
completed, displayed results, saved a named study, returned home and reopened
that same completed study. There were no stalled browser operations.

The saved [GS browser result](http://127.0.0.1:59171/#76d248b03baa49638c5e4ba1c8c0c78b)
reports $1,043.98 / $852.81 / $805.94 for grid / PV / PV-plus-battery. The
[browser receipt](../.cache/toledo_oh/browser_acceptance_1.json) and
[screenshot](../.cache/toledo_oh/browser_acceptance_1.png) retain observed
assertions separately from API evidence. Exact restored requests match the
GS seed except the request name; native input and comparison CSV bytes match.
The saved display name is separate study metadata. Carbon was off and visibly
reported as not calculated, with missing emissions distinguished from zero.

October 2026 uses **modeled clear-sky weather**, not verified historical 2026
weather. The two seed studies add six bills and 17,856 electrical intervals;
the browser GS submission adds three bills and 8,928 intervals. Their
[seed audit](../.cache/toledo_oh/preview_independent_audit_1.json) and
[browser audit](../.cache/toledo_oh/browser_independent_audit_1.json) passed.
These counts are separate from the historical matrix. RS was not resubmitted
through the browser; both plans have queued-worker integration coverage.

The [post-browser API audit](../.cache/toledo_oh/browser_api_audit_1.json)
passed for five studies and 65 CSV endpoints, including metadata, exact saved
CSV bytes and ZIP members. Browser download/file-chooser handling was not
exercised. API checks do not prove those UI actions. Earlier CEI browser
assertions retain their original partial status and engine pin; this pass
does not renew another utility's evidence.

## Gaps, timing and PJM progress

February–May 2025 lacks complete ESP-IV/intermediate components; July's LGR
revision and August 14 fixed-charge allocation are unverified. December 2025
lacks a reproducible DCR55 primary sheet: retained books still carry DCR54.
A cached-search lead is explicitly unverified. January–September 2026 lacks
complete rider/credit intersections. Two truncated May archive captures
yielded no recoverable pages and were not substituted. No provisional rates,
full-year claim, export/NEM settlement or standalone storage are enabled.

Pytest phase elapsed time was 35.92 s; the regional phase was 25.49 s and
the launcher session 61.62 s. The matrix driver session was 21.39 s, with
RS/GS workers 9.23/9.68 s; these timings are nested, not additive. Modeled
seed workers took 14.62/15.22 s; browser worker time was 4.75 s. Full-task
wall time, active development and browser-tool waits were not separately
instrumented and are not inferred from simulation runtimes.

[PJM population coverage](PJM_Population_Coverage.md) now records **22
utility/state-district workflows**, up from 21. Toledo adds 278,814 residential
distribution accounts; the total proxy becomes 50.83 million people, about
**76%** of PJM's reported 67 million, versus about 74.9% previously. This is a
utility-territory population proxy, not eligible-customer, supported-date,
full-tariff, annual-electrical or carbon-data coverage.

No staging, commit, push, deployment or stable-engine promotion was performed.
The private preview and evidence remain available for review.
