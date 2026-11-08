# Third five-utility PJM batch: verified scope and targeted validation

Work began on `main` at `e6c581b19b931fd8d4cf5a4efff8ec2584d1adfc`, with a clean
checkout. The requested scope is ordinary residential and small-commercial
2025–2026 service for Rappahannock, Duke Kentucky, South Central Power, Delaware
Electric Cooperative and Shenandoah Valley Electric Cooperative. Initial
operation is non-export. No staging, commit, push, deployment or stable-engine
promotion is authorized or performed.

## Executable scope and source gaps

| Utility / plans | Verified 2025 service | Verified 2026 service | Boundary |
| --- | --- | --- | --- |
| [Duke Energy Kentucky RS/DS](Duke_Energy_Kentucky.md) | April–June | April–June | Separate following billing month and first-business-day bill date; ordinary unincorporated Boone County/Boone school district. DS independent demand/history stays within its free first 15 kW and first 6,000-kWh block. |
| [Delaware Electric Cooperative R/GS](Delaware_Electric_Cooperative.md) | January–December | January–October | Complete matching calendar meter/read/bill cycles; ordinary unincorporated Sussex scope. GS retained assignment and actual prior demands below 50 kW require independent evidence. |
| [Rappahannock A-1/B-1](Rappahannock_Virginia.md) | Unavailable | Unavailable | Missing dated cooperative federal-power tax adjustment/nonapplicability and unresolved county-tax details. Known energy components are not a complete bill. |
| [South Central Power R/SGS](South_Central_Power_Ohio.md) | Unavailable | Unavailable | Actual monthly generation/transmission factors and applicability are missing. A dated sample invoice is not a generic monthly tariff. |
| [Shenandoah A-15/B-16](Shenandoah_Valley_Virginia.md) | Unavailable | Unavailable | Historical base/tax sheets, STS successor applicability and dated cooperative tax intersections remain unverified. |

Every other period fails closed. Catalog presence does not establish billing
support, uniform two-year coverage, actual customer eligibility or a successful
study. The three unavailable providers cannot create a priced API/worker study.
SMECO remains unresolved in its original scope and is not part of new acceptance.

The source ledgers are
[Duke KY](utility_sources/duke_ky/sources.json),
[DEC](utility_sources/delaware_coop_de/sources.json),
[REC](utility_sources/rappahannock_va/sources.json),
[SCP](utility_sources/south_central_oh/sources.json) and
[SVEC](utility_sources/shenandoah_va/sources.json).
They preserve originals/hashes, dated components, unit conflicts, blocked
retrievals and source grades. No missing factor is set to zero. No supplier,
PJM zone, market price or adjacent utility tariff substitutes for retail evidence.

## Material billing and account decisions

* Duke's ESM basis differs by class: RS includes base charges and riders; DS
  excludes its embedded base fuel and FAC. The six selected FAC/PSM/ESM stacks
  retain their actual billing dates and signs. A generic next-day bill is not
  used when the filed boundary is the first business day. DS requires independent
  service demand, contract/history and ordinary auxiliary-service terms; PV
  savings cannot establish eligibility or erase those obligations. Official
  Kentucky school-tax tables for the relevant fiscal years corroborate Boone's
  3% school tax; RS domicile exemption and DS sales-tax status are separate facts.
* DEC's ordinary R delivery factor is distinct from R-BTP. Its May 1, 2026 PCA
  is $0.012161/kWh, replacing a $0.001500/kWh credit. The notice's prose uses
  incorrect cents units; the filed tariff's dollar units and bill-impact
  arithmetic govern. Residential PUT exemption and commercial 4.25% tax on the
  pre-tax gross amount remain separate. The independently assigned GS history
  is supplied per cycle, not inferred from modeled PV-reduced imports.
* Virginia's qualifying-federal-power adjustment is cooperative/taxable-period
  based. REC/SVEC cannot establish a zero factor by confirming ordinary taxable
  service. Neither known state/SCC rates nor a PCA-only source resolves it.
* Both executable providers require final written approval for the exact
  non-export installation, active before service, preserving ordinary import
  charges. DEC additionally requires the exact battery supplement and its
  less-than-100-kW DC agreement scope. Storage charges only from PV. Export
  settlement, standalone/grid-charged storage and unverified standby treatment
  are not enabled.

## Frozen candidate and validation selection

Engine: `27b51e1a910ed360cfe7320c0fc1c0460f831666ffabfb64a5244720d87300e3`.
The private `.cache/pjm_batch3/candidate_frozen.json` records all 284 Python
source files, dependency identity, frontend/test/tool fingerprints and 15
additional source-ledger/transcription/weather files. Candidate source was
frozen before final acceptance. Earlier development results and prior utility
evidence retain their original pins.

The focused launcher selected the five new utility modules, batch form/API/
worker/saved-artifact checks, directly affected counterfactual, coverage, driver,
resume, timezone and launcher checks, plus five bounded existing study-contract
nodes. **711 tests passed**, with no skips or errors. Pytest took 32.94 seconds.
Changed JavaScript passed `node --check`. The report is
`.cache/pjm_batch3/acceptance/report.json`; passing queued-worker artifacts were
retained in `.cache/pjm_batch3/modeled_worker/` without rerunning them.

## Selected historical and electrical acceptance

All eight selected driver studies completed with verified complete bills, zero
export, and grid-only, PV-only and PV-plus-battery scenarios. Each selected case
retains every 15-minute dispatch and OpenDSS interval. This is not a reduced
electrical sample within those cases.

| Selected service / both classes | Studies | Scenario-month bills | OpenDSS interval checks | Manifest |
| --- | ---: | ---: | ---: | --- |
| DEC R/GS, January–December 2025 | 2 | 72 | 210,240 | `.cache/pjm_batch3/acceptance/regional/validation.json` |
| DEC R/GS, May 2026, after PCA change | 2 | 6 | 17,856 | `.cache/pjm_batch3/dec_2026/validation.json` |
| Duke RS/DS, April–June 2025 | 2 | 18 | 52,416 | `.cache/pjm_batch3/duke_2025/validation.json` |
| Duke RS/DS, April–June 2026 | 2 | 18 | 52,416 | `.cache/pjm_batch3/duke_2026/validation.json` |
| **Historical total** | **8** | **114** | **332,928** | Same frozen engine |

All **76 primary cost proofs** and **38 battery minimum-cycling proofs** passed.
DEC's full-year study includes both DST transitions. Focused tests separately
cover rate boundaries, unsupported dates, native-load/account eligibility,
missing/duplicate intervals, numeric/symbolic parity and rejection of unsupported
export/grid charging. Duke has no verified full-year tariff intersection; no
annual Duke study is presented. No full-year 2026 study is claimed for either
provider. The selected 2026 electrical cases do not imply every covered 2026
month has a separate historical replay.

The four queued-worker integration studies retained from the 711-test run add
12 scenario-month bills and 35,136 interval checks, with eight cost and four
battery-cycling proofs. They cover each live plan once using explicitly
hypothetical clear-sky inputs; they were copied from the passing fixture without
rerunning it. The two browser-path studies below add six bills, 17,280 interval
checks, four cost and two cycling proofs. Across these distinct retained runs,
the total is **14 studies, 42 scenarios, 132 scenario-month bills, 385,344 OpenDSS
interval checks, 88 cost proofs and 44 battery-cycling proofs**, all passing.
These counts exclude intermediate development runs and earlier utility evidence.

## Independent rebilling and retained evidence

Separate source reviews used literal Decimal rate arithmetic, rather than
deriving benchmark factors from the executable rate tables. They reviewed
dated tariff/filing/tax source hashes, 30 DEC and 10 Duke fixed benchmarks,
then independently reconstructed all **114 historical scenario-month bills**
from saved physical meter flows. Maximum component discrepancy was less than
**$5.3e-14**. Recorded primary/cycling lower bounds, dispatch, SOC, closing state,
component/credit ledgers and every selected electrical interval were audited.

Receipts are `.cache/pjm_batch3/independent_dec_rebill.json` and
`.cache/pjm_batch3/independent_duke_ky_rebill_v2.json`; independent source reviews
are `.cache/south_central_oh/review_dec.json` and
`.cache/delaware_coop_de/review_duke_ky.json`. The additional shared form/account
review is `.cache/duke_ky/development/shared_wiring_review.json`.

The first private Duke auditor incorrectly compared the primary-stage objective
with a gap reported for the final cycling-refined dispatch. Its failed receipt
remains `.cache/pjm_batch3/independent_duke_ky_rebill.json`. The corrected auditor
uses independently reconstructed final dispatch cost against the primary lower
bound, and verifies both the nonnegative optimality gap and absolute
reconciliation gap to $1e-8. The existing $1e-4 proof-attainment tolerance was
unchanged. Deliberately zeroed gaps and an unattained lower bound were rejected.
No production code, frozen pin or study was changed to repair the auditor;
`.cache/delaware_coop_de/duke_auditor_correction.json` preserves both script
identities and the three negative controls.

DS's independently supplied classification/ratchet review can differ from
scenario-reconstructed monthly peaks. The accepted cases remain inside the
same free 15-kW block under both. This evidence is not a finding that the
external history was measured at the modeled hypothetical site.

The final read-only aggregation is `.cache/pjm_batch3/final_acceptance.json`.
It checks 364 retained artifact hashes, the matching engine/frontend/test/tool
fingerprints and all 15 extra source/weather files. All 274 original Python
sources were compared with the starting baseline: only the three intended
registry/counterfactual/study integration files changed. All previous utility
rate modules and shared algorithms remain unchanged. The private generated
coverage table is `.cache/pjm_batch3/coverage.md` and `.csv`; eight exact
plan/period records are audited complete bills on this engine. The repository's
older cumulative coverage reports retain their original evidence identities.

## One concise browser acceptance pass

Local development server: `http://127.0.0.1:65218`, using the frozen development
snapshot, not a stable-engine promotion. The representative Duke DS April 2026
case uses a hypothetical flat 1-kW native load and clear-sky PV. Its written
agreement/account confirmations are labeled hypothetical, not actual approval.

Observed UI checks passed:

* All five new providers appeared in the catalog. Duke DS displayed its separate
  jurisdiction/supplier/DEOK identity, date limits and eligibility. DEC GS
  displayed its DPL metadata, verified dates, sources and initially unchecked
  approval fields.
* REC, SCP and SVEC displayed unavailable plans and specific missing-source
  reasons. Attempting Next on REC stayed at the service step with the rejection.
  API tests independently reject study creation for all three providers.
* The API-seeded Duke study was saved through the browser and reopened from
  Recent studies. Load these settings restored its account, following-month
  billing clock, equipment, PV-only battery charging, non-export contract,
  clear-sky weather and stated native-load assumption.
* Browser submission created a new study and completed. The three displayed
  bills reproduced $116.77 grid-only, $82.13 PV-only and $81.15 PV-plus-battery.
  The rerun was saved. No browser operation stalled.

Seed study: `63178c2994774368a412b26a9f19ba13`; UI-submitted rerun:
`c42ffd8bcc4642f9b1fae1e1907ff423`. API readback verified both persisted without
expiration, identical billing results and settings identical except the study
name. Saved-name changes are reflected in exported settings while immutable
worker requests retain their original names. CSV and all 13 ZIP table payloads
per study matched the retained bytes. Download checks used the API; no browser
download event, upload or file chooser is claimed. The remaining live classes
have form/worker/artifact tests, not separate browser-submitted studies.

Browser receipt: `.cache/pjm_batch3/browser_acceptance.json`; accessibility
readback: `.cache/pjm_batch3/browser_acceptance.txt`; screenshot:
[completed saved rerun](../.cache/pjm_batch3/browser_acceptance.jpg).

The launcher records 32.94 seconds for focused pytest and 71.08 seconds for its
DEC annual driver phase. Additional selected matrix sessions and their timings
are in `.cache/pjm_batch3/selected_matrix_sessions.json`; each manifest retains
worker and artifact-audit timings. Browser seed and rerun workers reported 4.18
and 4.59 seconds. Tool waits, research, overlapping jobs and total wall-clock
elapsed time are not represented as active development or simulation runtime.

## Exclusions and interpretation

The full release suite, unrelated utilities' historical matrices and all native
GUI testing are excluded under the targeted policy. No shared billing/solver/
time-grid/physics/replay algorithm or worker/API schema changed. This is targeted
acceptance, not a full-release or GUI pass. No stable engine was promoted.

Inputs are synthetic native loads and explicit hypothetical account/circuit
facts. Historical matrices use actual year/site ERA5 weather. Representative
OpenDSS services are not surveyed utility feeders or interconnection approval.
Rolling-cycle optimization and raw/unrounded bill-cost proofs do not establish
a joint annual optimum or a minimum rounded cash invoice. Independent per-cycle
classification/history facts are distinct from simulated scenario peaks and
must not be presented as measured customer records.
