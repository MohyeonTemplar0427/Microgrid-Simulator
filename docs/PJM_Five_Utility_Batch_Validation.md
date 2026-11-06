# Five-utility PJM batch: implementation and targeted validation

Recorded November 5, 2026 (acceptance receipts use UTC November 6).

## Scope and candidate

This batch implements Appalachian Power West Virginia RS/SGS, Pepco DC
R/GS-ND SOS, Delmarva Delaware R/SGS-ND SOS, Mon Power West Virginia A/B,
and I&M Michigan RS/GS Standard Service. These are the five recommendations
selected for this batch. Potomac Edison West Virginia remains a separate
follow-up; its tariff is not interchangeable with Mon Power's.

The requested research window was 2025–2026. Executable dates below are the
verified intersections of all required bill components, not a claim of uniform
two-year coverage. Every other cycle fails closed. Initial operation is
non-export, with account-specific eligibility and approval requirements.

Work remains on `main`, based on HEAD `6d51e06`, with all changes unstaged.
No commit, push, deployment or stable-engine promotion was performed.
Existing Appalachian Power Virginia and I&M Indiana implementation files,
tests, source ledgers and reports were preserved byte for byte, as were
`AGENTS.md` and the ignored `CLAUDE.md`. Existing shared-file changes were
retained while adding the new utility wiring.

Frozen engine ID:

`d381b6746053a202496dc63c518336ada1a92df0f5bf6ab942ca38d4235f4c62`

The private [frozen candidate](../.cache/pjm_batch5/candidate_frozen.json)
records runtime dependencies and frontend, test, tooling, ledger and weather
fingerprints. The [engine snapshot](../.cache/pjm_batch5/candidate/engine.json)
pins all 264 Python source files. The final read-only artifact re-audit
confirmed those sources and frozen files still match. Documentation added
after acceptance does not alter that engine.

## Supported plans and complete calendar cycles

| Utility / plans | Verified 2025 cycles | Verified 2026 cycles | Principal account restriction or unresolved gap |
| --- | --- | --- | --- |
| [Appalachian Power WV](Appalachian_Power_West_Virginia.md), RS 015 / SGS 231 | October | September–October | Ordinary single-phase service outside local electric-tax districts; SGS independently below 10 kW. November 2025–January 2026 ENEC/CRRC reconciliation is unresolved. |
| [Pepco DC](Pepco_DC.md), R / GS-ND SOS | June | June–October | GS-ND requires retained classification, non-demand metering, current Company review and independent prior demand/energy history. Missing monthly administrative-credit evidence blocks other dates. |
| [Delmarva DE](Delmarva_Delaware.md), R / SGS-ND SOS | December | September–November | Initial unincorporated Sussex scope. SGS-ND classification and transmission PLC must be independently supplied. Earlier component intersections and transition allocations remain unresolved. |
| [Mon Power WV](Mon_Power_West_Virginia.md), A / non-demand-metered B | August–December | August–November | Initial unincorporated scope. B requires independent normal requirements below 10 kW and twelve actual prior bills for the active capacity minimum. Intermediate component intersections remain unresolved. |
| [I&M Michigan](Indiana_Michigan_Power_Michigan.md), RS 015/016 / non-demand secondary GS 215/218 | January–April; June–December | January–December | GS requires retained non-demand metering and under-10-kW EWR classification. May 2025 tax-rider service/bill-clock allocation is unresolved. |

All five use complete matching service and bill months, final-day bill dates,
full monthly charges, and consecutive 15-minute `America/New_York` data.
Partial/shifted cycles and unverified dates reject. These calendar study
restrictions do not describe every utility's actual meter-reading schedule.
There is no supported full-year 2025 study in this batch.

Each adapter separates the distribution utility, retail supply arrangement,
jurisdiction and PJM metadata. APCo and I&M use AEP, Mon Power APS, Pepco
PEPCO and Delmarva DPL metadata. Wholesale prices are separate inputs and
add no retail charge to these schedules.

PV and paired storage require final approval effective before the cycle and
a written utility agreement preserving ordinary import billing for the exact
installation. Storage charges only from onsite PV. The model does not infer
eligibility from a smaller simulated import, assume a special agreement for an
actual account, or enable export settlement. Test accounts explicitly declare
hypothetical approvals.

## Sources and billing safeguards

The utility guides link dated source ledgers under `docs/utility_sources/`:
[APCo WV](utility_sources/appalachian_wv/sources.json),
[Pepco DC](utility_sources/pepco_dc/sources.json),
[Delmarva DE](utility_sources/delmarva_de/sources.json),
[Mon Power WV](utility_sources/mon_power_wv/sources.json), and
[I&M Michigan](utility_sources/im_mi/sources.json). They retain official utility,
commission and statutory references, component dates, units, hashes, source
grades, blocked retrieval routes and unresolved scope. Downloaded material and
long review evidence remain in the corresponding ignored `.cache` directories.

* APCo's 2025 original tariff PDF routes returned 404. Preserved official-index
  excerpts establish the limited October stack; they are labeled cached filed
  tariff evidence. The current 2026 book was downloaded. Original ENG factors
  are **0.00313 cents/kWh RS** and **0.00245 cents/kWh SGS**. CRRC is collected
  once inside ENEC. A later CRRC change cannot be applied without reconciling
  that embedded amount, so the affected historical cycles remain blocked.
  Current filed rates reproduce the utility's $183.07 and $344.53 residential
  examples at 1,000 and 2,000 kWh. Stale summary/workbook labels do not override
  the filed customer charge or original factor precision.
* Mon Power's July 2025 notice supplies the historical component stack; the
  2026 notice corroborates continued vegetation collection. Schedule B prices
  the greater of customer-plus-energy charges and `$2.41 × capacity`, with
  capacity equal to the maximum current/prior-twelve-month actual kWh divided
  by 120. Riders are additional. Actual scenario imports carry forward,
  including zero-import months. Independent 1,000 kWh calculations and the
  WVPSC historical residential table corroborate the filed arithmetic.
* Pepco retains the residential first-30-kWh generation/administration and
  transmission minimums, separate distribution/EDIT blocks, PCA, monthly
  administrative credit, BSA and statutory riders/taxes. Blank credit-chart
  columns do not establish zero rates. BSA continuation has rate-table and
  commission-filing corroboration. GS-ND energy-triggered demand metering and
  reclassification require independent account facts as well as study bounds.
* Delmarva keeps its company-assigned transmission PLC separate from simulated
  peaks and preserves it across scenarios. R has the statutory residential
  public-utility-tax exemption; ordinary SGS-ND uses 4.25%. Source comparisons
  corroborate the interim base step, DSIC basis and supported rider stacks.
* I&M uses **actual billed PSCR**, including the negative July–December 2026
  factor, rather than the authorized maximum. Supply capacity, non-capacity,
  delivery, EWR, realignment, LIEAF and tax credits remain separate. Michigan
  sales tax excludes LIEAF under the state Treasury ruling. The published
  2026 PSCR reduction corroborates the factor change independently.

Independent source reviews caught the APCo embedded-CRRC issue and Pepco's
energy-triggered metering rules before the frozen runtime was accepted.
No actual customer invoice was supplied. Bill benchmarks use separate literal
tariff transcriptions and official examples/tables; they are not customer-bill
calibration or proof of a real account's eligibility.

## Implementation and selected tests

Each utility owns a billing adapter, dated rate module and focused unit tests.
Shared changes are limited to utility dispatch/catalog wiring,
counterfactual normalization, local-browser account/default-site preparation,
and validation/coverage tooling. Existing regional optimization, PV/storage,
worker, export and electrical-replay components are reused. No solver,
shared billing-math, time-grid, physics or frontend implementation was changed.

The focused launcher selected the five utility test modules,
`test/test_pjm_batch5_integration.py`, and directly affected regional
counterfactual, coverage, validation-driver, weather/timezone and launcher
tests. This includes independent Decimal bills, numeric/symbolic parity,
dated boundaries, DST, malformed/missing intervals, eligibility, unsupported
settlement, native/import bounds, form preparation, queued workers,
save/reopen and CSV/ZIP byte checks.

**461 distinct focused tests passed.** The original
[acceptance receipt](../.cache/pjm_batch5/acceptance/report.json) retains
451 passes and ten failures in a new worker-test assertion: deterministic
grid-only billing has no optimization proof. An intermediate assertion also
mistook CSV boolean text for a Python boolean. The corrected assertion checks
typed saved optimization proofs for the two optimized scenarios. The
[affected-node rerun](../.cache/pjm_batch5/worker_artifacts_final/report.json)
passed all ten cases. Runtime sources did not change during these corrections;
the original failed receipts were not rewritten as passing reports. The
private aggregate records the combined distinct-node result.

The first focused pytest run took about 60 seconds and the final ten-worker
rerun about 48 seconds, as measured by their launchers. These are check runtimes,
not total active development time. Simulation and browser work overlap other
activity; no total active-time estimate is asserted.

## Selected historical and electrical acceptance

All studies below use the same frozen engine. Each runs grid-only, PV-only
and PV-plus-battery with itemized bills, rolling-cycle state and dispatch
reconciliation. Every interval in each selected electrical case was checked;
this is selected-month coverage, not sampled intervals within an annual run.

| Utility | Selected periods | Studies | Scenario-month bills | OpenDSS interval checks |
| --- | --- | ---: | ---: | ---: |
| APCo WV | October 2025; September and October 2026 | 6 | 18 | 52,992 |
| Pepco DC | June 2025; June–September and October 2026 | 6 | 36 | 105,408 |
| Delmarva DE | December 2025; September and November 2026 | 6 | 18 | 52,440 |
| Mon Power WV | November 2025; August–September and November 2026 | 6 | 24 | 69,744 |
| I&M Michigan | January 2025; March, July–September and separate September 2026 worker cases | 8 | 36 | 105,960 |
| **Total** | Both classes in every selected period | **32** | **132** | **386,544** |

The seven driver manifests retain **22 passed studies**, with no failed or
pending cases: `historical_2025`, `apco26`, `mon26`, `dc26`, `de26`,
`im_mar26` and `im_jul_sep26` under `.cache/pjm_batch5/`. Their retained
request/result fingerprints and source pins were re-audited. The private
[coverage snapshot](../.cache/pjm_batch5/coverage.md) attaches all 22 as
audited complete-bill cases. Ten successful queued-worker cases are retained
separately in `.cache/pjm_batch5/modeled_worker/runs/`.

Historical cases use exact site/year ERA5 reanalysis from the pinned
[weather manifest](../.cache/pjm_batch5/weather/weather-input-manifest.json),
with original provider material and checksums retained. The ten final worker
cases use explicitly modeled clear-sky weather, including later 2026 months.
Native loads are deterministic synthetic archetypes, not measured consumption.
Circuits are representative single-phase service models, not calibrated
utility feeders or site-specific electrical approval.

Four independent saved-artifact Decimal auditors cover all 132 bills and
386,544 intervals. Maximum component discrepancy is less than `$7e-14`.
Dispatch/objective reconciliation stays within the recorded solver tolerance
(the Pepco maximum is approximately `$0.000001000005`). All **88 optimized
cycle cost proofs** and **44 battery minimum-cycling proofs** pass. Grid-only
direct bills have no optimization-proof claim, and rolling-cycle proofs do
not establish an annual perfect-foresight optimum.

Auditor receipts:

* [WV rebill](../.cache/pjm_batch5/independent_wv_rebill.json): 42 bills.
* [Pepco DC rebill](../.cache/pepco_dc/independent_rebill.json): 36 bills.
* [Delmarva DE rebill](../.cache/delmarva_de/independent_rebill.json): 18 bills.
* [I&M Michigan rebill](../.cache/im_mi/independent_rebill.json): 36 bills.

The [final aggregate](../.cache/pjm_batch5/final_acceptance.json) rechecks 960
artifact fingerprints, distinct test outcomes, source identities, proofs and
electrical counts. Its read-only generator is retained beside the receipt.

## Browser acceptance

One concise local-browser pass used the frozen engine and unchanged frontend.
It observed all five utilities in the service selector and exercised Mon Power
B with an active inherited capacity minimum: rendered results, named save,
reopen, load settings, restored tariff/history, review, submit and completed
rerun. There was no stalled operation or repeated failing route.

Saved study `373c7c78d1014088b14ffba0ed6a844a` is named
`PJM batch acceptance — Mon Power B`. Restored rerun
`9b34faeaf4a441f1b62745b251ca9f5d` completed on the same engine. Both show
grid/PV/battery bills of **$130.07 / $127.87 / $127.87** and all-interval
electrical feasibility. The restored numeric history is identical; its
description was corrected to one 6,000-kWh month and eleven 1,000-kWh months.
Saved database state and request/result readback corroborate the UI actions.
The [browser receipt](../.cache/pjm_batch5/browser_acceptance.json) records
these observations and fingerprints. These two browser runs are excluded
from the core totals above.

The other four utilities were not each rerun through a separate browser wizard.
Their form and worker/artifact paths passed automated acceptance. CSV/ZIP bytes
and endpoints were tested through APIs; no browser download/upload wait was
used. UI observations are not proof of actual account eligibility.

## Exclusions and remaining work

This is targeted acceptance using the existing **focused** tier, not a full
release pass. The full release tier, unrelated utilities' historical matrices
and native GUI were excluded under the targeted policy. No GUI was launched.
The unchanged frontend required no new JavaScript syntax checks.

Full-year 2025 acceptance is blocked by tariff gaps for all five utilities.
I&M Michigan has twelve verified 2026 tariff months, but no completed annual
2026 simulation is claimed: the acceptance uses selected historical months
and explicitly modeled worker cases, with actual future-year weather still
unavailable. Other utilities' uncovered months, transition allocation,
additional localities/taxes, broader commercial classifications and export
settlement require separate source verification and acceptance.

Earlier utility evidence retains its original engine/frontend identity.
Nothing in this report promotes those results to this candidate or promotes
this candidate to the stable engine.
