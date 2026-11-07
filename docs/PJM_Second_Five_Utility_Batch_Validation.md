# Second five-utility PJM batch: scope and validation

Development checkout: `main`, initial HEAD `e77ad60`, initially clean.
Research target: 2025–2026 ordinary residential and small-commercial service,
non-export only. Existing changes and earlier evidence identities are preserved.
No staging, commit, push, deployment or stable-engine promotion is authorized.

## Verified executable scope

| Utility / plans | 2025 service cycles | 2026 service cycles | Principal boundary |
| --- | --- | --- | --- |
| [Potomac Edison WV R/G](Potomac_Edison_West_Virginia.md) | August–December | August–November | Ordinary unincorporated scope; independent non-demand G assignment and actual twelve-month kWh minimum history. |
| [Wheeling Power WV RS/SGS](Wheeling_Power_West_Virginia.md) | October–November | September–October | Joint Tariff21 evidence; CRRC is Appalachian-only. Other component intersections remain blocked. |
| [Kentucky Power RS/GS](Kentucky_Power_Kentucky.md) | December | January–August | Explicit following utility billing month and next-day bill; RS study at most 2,000 kWh, GS independently no-demand and at most 4,449 kWh/9.49 kW. |
| [SMECO MD R/GSS SOS](SMECO_Maryland.md) | Unavailable | Unavailable | Approved complete monthly PCA/BSA/rider/tax intersections were not established; pending amounts and PTC are not complete bills. |
| [NOVEC VA R-1/SC-1](NOVEC_Virginia.md) | January–December | Unavailable | Ordinary taxable unincorporated Prince William account; actual historical PCA/levy, independent SC-1 history. Primary2026 full stack remains unresolved. |

Coverage is component-specific evidence, not a claim of uniform two-year
support. Actual eligibility, tax locality, meter assignment, history and
written DER approval are independent account facts. Hypothetical study inputs
are labeled explicitly. No real customer invoice or interconnection agreement
was supplied.

Source ledgers retain official references, source grades, component clocks,
checksums, blocked retrievals and the excluded periods:
[Potomac](utility_sources/potomac_edison_wv/sources.json),
[Wheeling](utility_sources/wheeling_wv/sources.json),
[Kentucky](utility_sources/kentucky_power_ky/sources.json),
[SMECO](utility_sources/smeco_md/sources.json), and
[NOVEC](utility_sources/novec_va/sources.json).

## Acceptance evidence

The finished runtime and frontend were frozen before final acceptance. Engine:

`f11bddc4f6bbd552e5e9377bf7de9ad92343de261ce09fb5421ba42fb534967d`

The [engine snapshot](../.cache/pjm_batch_next5/candidate/engine.json) pins
274 Python source files and runtime dependencies. The
[frozen-candidate receipt](../.cache/pjm_batch_next5/candidate_frozen.json)
also pins 241 test, tooling, frontend, source-ledger and weather files.
Earlier development receipts retain their original identities. No earlier
utility acceptance is automatically attributed to this candidate.

**Targeted acceptance passed: 549 distinct tests, 22 studies, 180 scenario-month
bills, and 525,936 OpenDSS interval checks.** All 120 optimized-cycle bill-cost
proofs and 60 battery minimum-cycling proofs passed. Grid-only direct bills
have no optimization-proof claim. The
[final read-only re-audit](../.cache/pjm_batch_next5/final_acceptance.json)
checks these counts, source identities, 660 saved-artifact fingerprints and
preservation of the previous utility modules and repository instructions.

## Source findings and account safeguards

* Potomac Edison WV's ECC and normalization factors differ from Mon Power's,
  although the supported 1,000-kWh totals happen to coincide. Independently
  downloaded Potomac notices and filed sheets establish the separate factors.
  G retains the active maximum-current/prior-twelve-month-kWh capacity minimum,
  with actual scenario imports carried forward and riders additional.
* Wheeling's joint sheets explicitly identify Tariff No. 21. The CRRC rider
  applies to Appalachian Power only. Wheeling uses the joint filed ENEC factor
  without adding or subtracting an Appalachian credit; a separate official
  Wheeling workbook corroborates the direct factors. Stale workbook ECS
  precision and tax lookup errors do not override filed sheets. The revised
  ENG begins bills rendered December 12, 2025, despite the November filename.
  Historical raw PDF routes returned 404, so retained official-index excerpts
  and their source grades remain explicit.
* Kentucky's utility-designated billing month is independent of service dates.
  Initial hypothetical calendar studies use a following-month bill issued the
  next day, with explicit cycle evidence. Filed monthly FAC windows are checked;
  calculator filenames do not set the billing clock. January 2026 ES uses
  regulator factors `.048531/.087593`, correcting the stale calculator's
  `.050112/.086949`. Filed/ordered SSR includes DR; DR does not include SSR.
  The RS 2,000-kWh boundary is inclusive, unlike the stale calculator formula.
  These corrections were independently reviewed against original sources.
* NOVEC's published notices establish the 2025 PCA halves, and filed R-1 plus
  visually inspected scanned SC-1 sheets establish base components. The actual
  SCC levy changes August 1, 2025; the statutory maximum is not substituted.
  Prince William's consumer tax is separate from state/local consumption
  taxes. The older actual levy has an official statewide-tax-table
  corroboration rather than an original NOVEC notice; that source grade is
  retained. Original utility tax-table evidence supports Kentucky's Pike
  County scope rather than an independent county ordinance. Actual accounts
  must independently establish the locality and applicable tax treatment.
* SMECO's supply-only PTC history and approved August 2026 base step do not
  establish a complete bill. Mandatory approved monthly PCA/BSA, dated delivery,
  rider/tax intersections and residential relief remain unresolved. Direct PSC
  retrieval returned 403; a distinct media archive exposed formulas but no
  sufficient monthly factors. The current November 2026 factors are explicitly
  pending. Every 2025–2026 bill and dispatch route remains blocked.

Independent reviews are retained under
[WV component review](../.cache/smeco_md/review_wv.json),
[NOVEC component review](../.cache/smeco_md/review_novec.json), and
[Kentucky source review](../.cache/novec_va/review_kentucky.json).
They supplement candidate-specific artifact audits; they are not actual
customer-invoice calibration.

All runnable plans require independent utility/meter/classification/locality
facts. PV and paired storage require final approval active before the cycle and
a written utility agreement preserving ordinary import billing for the exact
installation. Storage charges only from PV. Export settlement, standalone
storage, optional programs, unsupported taxes and unverified dates reject.
Utility, supplier, jurisdiction, PJM transmission metadata and wholesale price
location remain separate. SMECO's emergency transmission zone is SMECO; PEPCO
forecast/market aggregation is a different identity.

## Selected test receipts

The focused selection contains the five utility test modules, new batch form/
worker/artifact tests, directly affected counterfactual/coverage/driver/resume/
weather/launcher tests and selected existing browser contracts. It verifies
literal Decimal benchmarks, numeric/symbolic parity, date clocks, boundaries,
DST, missing/duplicate data, native-load limits, eligibility and unsupported
settlement, queued workers, saved settings and CSV/ZIP byte equality.

The initial [focused receipt](../.cache/pjm_batch_next5/acceptance/report.json)
has 539 passes and ten local-socket setup errors. The environment prevented the
local HTTP fixtures from binding. Only those ten nodes were rerun with the
required loopback permission: nine passed in the
[API receipt](../.cache/pjm_batch_next5/api_acceptance/report.json). The new
SMECO rejection test initially expected a successful JSON response, while the
API correctly returned HTTP 400. Only that test assertion/import changed; the
runtime and frontend were unchanged. Its corrected node passed in the
[final focused receipt](../.cache/pjm_batch_next5/acceptance_final/report.json),
which also runs the first six historical cases. Original failed receipts and
the earlier test fingerprint are preserved. The aggregate verifies the 549
distinct-node result and that the other test functions did not change.

The first focused phase took 38.29 launcher seconds, the API subset 43.57,
the corrected node 3.15, and its regional phase 33.53. These are check runtimes,
not active development time. Separate matrix jobs overlapped; their elapsed
times must not be added into a development-time claim.

The changed `regional.js` passed
[Node syntax checking](../.cache/pjm_batch_next5/javascript_syntax.json).
An independent wiring review identified an unavailable-provider blank-date
callback dereference, which was fixed before freezing and covered by a focused
test of the actual callback. The browser also guards missing defaults and
requires documented Kentucky cycles. No shared billing math, solver, time-grid,
PV/storage physics, worker API or electrical-replay implementation changed.

## Historical, dispatch and electrical studies

| Utility | Selected service periods | Studies | Scenario-month bills | OpenDSS interval checks |
| --- | --- | ---: | ---: | ---: |
| Potomac Edison WV R/G | November 2025; August–September 2026; October 2026 workers | 6 | 24 | 70,296 |
| Wheeling RS/SGS | November 2025; September 2026; October 2026 workers | 6 | 18 | 52,440 |
| Kentucky RS/GS | December 2025; January–August 2026; August 2026 workers | 6 | 60 | 175,656 |
| NOVEC R-1/SC-1 | Full-year 2025; November 2025 workers | 4 | 78 | 227,544 |
| SMECO R/GSS | No executable verified period | 0 | 0 | 0 |
| **Total** | Grid-only, PV-only and PV-plus-battery in each study | **22** | **180** | **525,936** |

Fourteen driver cases passed with no failed or pending cases. Manifests are
under `.cache/pjm_batch_next5/` in `acceptance_final/regional`, `novec_2025`,
`kentucky_2026`, `potomac_2026` and `wheeling_2026`. The private
[coverage snapshot](../.cache/pjm_batch_next5/coverage.md) re-audits their
request/result fingerprints and records 14 complete-bill cases, not subtotals.
Eight additional normal queued-worker cases are retained under
`modeled_worker/runs`.

NOVEC's two annual studies check every interval of 2025 for all three scenarios:
210,240 annual OpenDSS interval checks. Other evidence covers the explicitly
selected periods, with every interval checked in each selected case. None of
the annual electrical data was subsampled. Rolling-cycle optimization carries
SOC and actual applicable billing state; it does not establish a jointly
optimized annual minimum. NOVEC's classification history remains an independent
per-cycle fact rather than an inference from PV-reduced imports.

Historical cases use seven exact-site/year ERA5 files from the
[prepared-weather manifest](../.cache/pjm_batch_next5/weather/weather-input-manifest.json).
Native demand is synthetic and imported through the normal CSV contract.
The eight API worker cases explicitly use modeled clear-sky weather. Circuits
are representative single-phase 120/240-V services, not surveyed utility
feeders or site-specific electrical approval.

The driver audits and three separate saved-artifact Decimal auditors cover
itemized components, component-rounded cash bills, dispatch, carried state/SOC
and corresponding electrical intervals on the same engine. Maximum unrounded
component error is `$1e-13`:

* [WV rebill](../.cache/pjm_batch_next5/independent_wv_rebill.json): 42 bills,
  122,736 intervals, maximum component error `$5e-14`.
* [Kentucky rebill](../.cache/kentucky_power_ky/independent_rebill.json): 60 bills,
  175,656 intervals, maximum component error `$1e-13`.
* [NOVEC rebill](../.cache/novec_va/independent_rebill.json): 78 bills,
  227,544 intervals, maximum component error `$4e-14`.

All selected primary cost and secondary battery-cycling proofs passed within
their recorded tolerances. No actual customer invoice was supplied; source
transcriptions, official examples and model reconciliation are distinct from
measured customer-bill validation.

## Browser acceptance

One concise pass used the frozen candidate and recorded frontend fingerprints.
It rendered a Kentucky GS study, saved it by name, returned home, reopened it,
restored settings and observed all five provider choices. SMECO GSS appeared
disabled with an explicit PCA/BSA/full-component gap, and Next remained blocked.
The saved Kentucky settings were restored again. August 1–31 service dates,
September 1 utility billing month/date, documented cycle JSON, non-export and
PV-only storage were visible before submission. The rerun completed on the
same engine with identical inputs except the study name.

Saved study: `d9fc24834a624e9e9dea6055ffef8456`, named
`Second PJM batch acceptance — Kentucky Power GS`.
Restored rerun: `3ccfbd5e55ca4bf784429fdab4fb1acc`.
Both show **$177.51 / $132.82 / $132.30** grid/PV/battery bills and all-interval
electrical feasibility. The rerun's worker runtime was 4.64 seconds. This is a
hypothetical flat-1-kW, clear-sky example, not a customer savings estimate.

The [browser receipt](../.cache/pjm_batch_next5/browser_acceptance.json) records
UI observations, saved database state, exact request readback and fingerprints.
Both runs were copied to durable ignored `browser_evidence/runs` before the
temporary rerun expires. The [screenshot](../.cache/pjm_batch_next5/browser_acceptance.jpg)
shows the completed rerun. These two runs are excluded from core counts above.
The other three runnable utilities were not separately exercised through a
browser wizard; their forms/workers/artifacts passed automated acceptance.
CSV/ZIP bytes were checked through APIs without browser upload/download-event
waits. No browser operation stalled; calls used 10–15-second limits.

## Exclusions and outstanding source work

This is **targeted acceptance using the focused tier**, not a full-release
pass. Unchanged utilities' historical matrices and the full regression suite
were excluded because their shared engine behavior was unchanged. Desktop GUI
tests were excluded and no native GUI was launched. No engine was promoted.

SMECO billing/dispatch remains unavailable until approved complete monthly
components can be obtained. NOVEC's 2026 prior PCA and revised November base
vectors lack sufficient primary evidence; rounded increase notices and a stale
2022 sample bill were not substituted. Other listed date gaps, additional
localities, broader commercial classes, transition allocations and export
settlement remain unsupported. Scope can expand only after source verification
and acceptance appropriate to the resulting change.

Git changes remain unstaged. Existing utility source modules, `AGENTS.md`,
ignored `CLAUDE.md` and the targeted-validation guide were preserved. Nothing
was committed, pushed, deployed or promoted during this task.
