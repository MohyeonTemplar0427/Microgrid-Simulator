# The Illuminating Company Ohio implementation validation

Reviewed October 31, 2026. Work began on clean `main` at
`e92f1de9af8071403cd65bdfd97f1bce3ce855cf`. The same HEAD and an empty index
were retained. No stage, commit, push, deployment or stable-engine promotion
was performed. Native desktop GUI work remains paused and was not launched.

Scope: [RS residential and measured GS secondary ordinary SSO](Illuminating_Company_Ohio.md).
Complete matching calendar service/bill cycles execute in **January and June
2025, September–December 2025, and October 2026**. Full-year 2025 is unavailable;
missing periods and unsupported export settlement reject without substitutions.
The GS actual contract and measured 30-minute/5-kW floor are independent of DER.

## Changes and source review

New utility-owned rate/billing modules, registry/counterfactual entries, default
site, equipment metadata and native-envelope checks reuse the existing regional
form, worker, PV/storage, optimizer and OpenDSS replay. Historical-driver and
coverage/launcher registrations are additive. No shared billing arithmetic,
solver, time-grid, physics, electrical replay or API/worker schema changed.
The existing generic browser form consumes the new catalog; JavaScript bytes
were unchanged. The new utility remains separate from Ohio Edison.

The [aggregate source ledger](utility_sources/illuminating_oh/sources.json)
pins **37 retained evidence files**, including component ledgers, selected
primary excerpts, effective dates, units, original PDF hashes and statutory
rules. Original public PDFs and failed/truncated routes remain under ignored
`.cache/illuminating_oh/sources/`. Direct retrieval used the system certificate
store after the initial default trust-store failure; certificate checks were
not disabled. Complete archived June/August 2025 editions supplement current
and year-end composites. May 2025/2026 archive responses were intrinsically
truncated; bounded recovery yielded no pages and they were excluded as evidence.

Independent source review retained superseding January PIR, ordinary mandatory
CRC/TSA credits, base-only January DCR percentages, positive ordinary 2025 RS
RER, and October 2026's CCR replacement. Canceled historical printed CDR/TAS2
credits were not applied. GS first-five-kW capacity is a monthly lump sum.
State-kWh tax uses incorporated statutory non30-day local-day bands and its
specified CAT gross-up, without a generic sales tax or duplicate CAT/wholesale
capacity/transmission adder. The guide records exact limits and remaining gaps.

## Frozen candidate and targeted checks

Engine: `1dbf0a453c68f50cb5a6b0f06edca7b67aa5682e2c32c097467c097ae2152b6b`.
`candidate_frozen_1.json` pins 244 runtime Python files, all 11 frontend files,
HEAD and the aggregate source-manifest hash. `frozen_candidate_1/` preserves the
immutable development snapshot. Acceptance, historical studies and preview
all used this engine; runtime/frontend/source bytes were rechecked afterward.

**358 tests passed**, zero skips, failures or errors. The focused selection was:

```sh
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_illuminating_oh.py \
  --test test/test_illuminating_benchmarks.py \
  --test test/test_illuminating_integration.py \
  --test test/test_pjm_population_coverage.py \
  --test test/test_regional_counterfactual.py \
  --test test/test_regional_coverage.py \
  --test test/test_regional_validation_driver.py \
  --test test/test_regional_weather_timezones.py \
  --test test/test_validation_launcher.py \
  --regional --utility firstenergy_ohio_illuminating --period custom \
  --start-date 2025-09-01 --end-date 2025-12-31 \
  --inputs .cache/illuminating_oh/weather \
  --output .cache/illuminating_oh/acceptance_1
```

The tests include 127 utility rule/account/date tests and 66 independent literal
benchmarks, numeric/symbolic parity, tax boundaries, demand/contract floors,
DST, missing/duplicate data, unsupported settlement, activation and service
eligibility, native limits independent of PV-reduced imports, counterfactuals,
form serialization, pinned workers and saved-settings/CSV/ZIP contracts.
Queued-worker cases cover both plans in June 2025 and October 2026 using
explicit modeled clear-sky inputs; they are not actual-weather validation.
Python syntax, unchanged `regional.js` syntax, diff and local-link checks passed.

Development checks exposed RS fixtures incorrectly carrying a GS contract and
exact-half-cent fixture assumptions; those fixtures were corrected. Dedicated
half-cent tests retain the study's saved-raw-float half-up contract. No shared
rounder or unsourced meter rounding was introduced. Local HTTP fixtures were
rerun with loopback binding permission. Earlier development receipts remain
attributed to their original selection/pin and are not extra final test counts.

Targeted acceptance is the AGENTS.md policy selection, not a full-release pass.
GUI tests, unaffected utility historical matrices and full workflow/release
tiers were excluded because shared behavior/contracts did not change. Only
matching frozen evidence could be resumed; these cases were freshly executed.

## Historical and electrical acceptance

The single selected historical matrix covers **September–December 2025**:
**2 studies, 6 scenarios, 24 cycle bills and 70,296 OpenDSS interval checks**,
zero electrical failures. Every interval in every selected case was checked;
there was no sampling or audit bypass. A full-year run would cross unverified
tariff periods and was intentionally rejected. January/June and October 2026
have separate source, numeric/symbolic and affected worker checks; this matrix
is not all-month or annual electrical coverage.

| Plan | Period | Grid / PV / PV-plus-battery bills | Electrical intervals | Study ID |
| --- | --- | ---: | ---: | --- |
| RS | September–December 2025 | $778.27 / $579.50 / $505.14 | 35,148 | `6b7257927aa748d08fac0c8b79bce06b` |
| GS | September–December 2025 | $4,179.78 / $3,755.46 / $3,544.33 | 35,148 | `3c4e844ff6634470817aa8d552e30468` |

Exact hypothetical-site/year ERA5 inputs were prepared once with coordinates,
raw JSON, request identity, retrieval time, hashes and provider attribution.
Hourly reanalysis is held across 15-minute intervals, not measured subhourly
irradiance. Native CSVs are deterministic generic household/office profiles,
not customer measurements or locally calibrated forecasts. Representative
circuits and billing PF are separately declared assumptions.

All **16 optimized cycle primary cost proofs** and **8 battery-cycle secondary
minimum-cycling proofs** passed; no strict fallback was used. Eight direct
grid-only bills make no optimizer claim. Maximum objective/rebill difference
was approximately $1.000006e-6 within retained tolerances. Continuous SOC and
unchanged contract obligations reconcile, but rolling-cycle perfect foresight
is not a joint annual optimum or prospective customer savings.

The standalone literal Decimal auditor imports no production billing, rates,
math or test code and makes no API/simulation call. It reconciled all 24 bills,
itemized/cycle/comparison tables, native/dispatch/SOC and every electrical row.
Maximum raw component error was **$5.684341886080802e-14**; no exact-Decimal
half-cent exception occurred in this matrix. This remains study arithmetic,
not an exact printed-invoice or rounded-cash optimality claim.

Receipts: `acceptance_1/report.json`, JUnit/logs,
`acceptance_1/regional/validation.json`, `validation-summary.json`, pinned
driver copies and `independent_audit_1.json`, all under `.cache/illuminating_oh/`.
Pytest phase: 32.59 s. Launcher matrix phase: 29.23 s; contained matrix session:
25.59 s, with worker runtimes 11.29/11.53 s. These nested scopes are not added
as CPU or active-development time.

## API and partial browser acceptance

The isolated preview at `http://127.0.0.1:59170/` retains copied matrix artifacts
and the same engine/frontend. Two additional **modeled clear-sky October 2026**
RS/GS seeds passed independent rebilling and **17,856 additional** electrical
interval checks; they are separate from the historical matrix count.

| Plan | Grid / PV / PV-plus-battery bills | Study ID |
| --- | ---: | --- |
| RS | $246.05 / $168.29 / $132.57 | `746ddea2767b40679abbe3f7b1d0ec1a` |
| GS | $1,161.42 / $945.06 / $883.21 | `b2e6f0070c1c4265871cb68258acb924` |

Both preview seeds passed primary and secondary cycle proofs, with no strict
fallback. They took 14.19/14.37 s respectively. The HTTP audit passed all four
saved studies, **52 CSV endpoints**, paged table metadata and exact ZIP
bytes/content/manifests. Receipts: `browser_seeds.json`,
`preview_independent_audit_1.json` and `api_audit_1.json`.

**Browser acceptance is partial.** One concise pass visibly verified completed
RS results, restored residential location/settings, the new utility, Ohio/PJM/
ATSI and separate wholesale identity, RS/SSO selection, eligibility/tax/DER
controls and the supported date windows. Carbon remained off and visibly
not calculated rather than zero. The attempt to open advanced account details
using a role selector returned a selector deadline/no-match. The route stopped
immediately under AGENTS.md; there was no retry, timeout extension, sleep loop
or upload/download-event automation.

The advanced disclosure action, GS browser configuration/results, browser
submission/restore-rerun and Save/home/reopen remain **unverified**. Successful
API/worker/settings/CSV/ZIP checks do not establish those UI actions. Actual
browser download handling was not attempted. The partial receipt and screenshot
are `browser_acceptance_partial_1.json` and `browser_partial_RS_1.png`; the tab
is retained as a local preview. The failed browser tool reported 3.08 s wall
time with a 10 s locator/30 s tool timeout request. Full task wall time and
active-development time were not separately instrumented.

## PJM progress

The [updated PJM footprint report](PJM_Population_Coverage.md) and guarded offline
reproducer now count **21 utility/state-district workflows**, including ComEd's
separate path. The existing final 2024 EIA account snapshot and household proxy
give approximately **50.17 million people / 74.9%**, appropriately headlined
**about 75%**. Immediately before CEI: 20 workflows / 72.5%; this addition
contributes about 1.60 million proxy people / 2.39 percentage points.

These are implemented utility footprints, not the population on supported
tariffs, complete 2025–2026 date coverage, eligible accounts or annual acceptance
passes. All four FirstEnergy PA districts now permit counting the merged PA
company once, without also adding the older inferred West Penn district.
Maryland-only affiliates do not add their Delaware/DC/West Virginia accounts.
The original October 25 input/output payloads and unchanged source extract are
preserved. Ten reporting guards are included in the final 358 tests; no MISO or
California utility adds to this PJM numerator. Earlier utility acceptance
remains attributed to its own recorded engine/frontend.
