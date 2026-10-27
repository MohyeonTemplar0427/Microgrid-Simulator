# Pepco Maryland implementation validation

Reviewed October 26, 2026. Local development on `main`, base HEAD `cc8977f`.
During orientation the pre-existing staged BGE/policy work was committed
externally: HEAD changed from `21541dc` to `cc8977f` before baseline capture.
This agent issued no stage, commit, push, deploy or stable-engine promotion.
The post-commit staged content and `AGENTS.md`/ignored `CLAUDE.md` are preserved. Existing
BGE and PPL/AEP code/evidence retain their original identities and limitations.

## Executable scope and unresolved evidence

R residential SOS and secondary GS Type I SOS support **January–February 2025
and July–October 2026**, matching complete calendar service/billing months only.
The initial locality is explicitly confirmed unincorporated Montgomery County.
Supplier, tax locality, GS historical classification/USC assignment, interconnection
and the PEPCO PJM zone remain independent facts. Maryland does not inherit DC
rates. Exports/NEM, community-solar settlement and special/standby service are
not enabled. See [account, pricing and netting scope](Pepco_Maryland.md).

Both plans deliberately return verified-charge **subtotals**, not complete bills:
R excludes unrecovered residential RGGI/RRC and legislative fixed credits; GS
excludes unresolved state sales-tax compound-base/bracket calculation. Omitted
amounts are not zero or exemptions. The ordinary GS USC $1.85 band must be
independently confirmed throughout each modeled year, including before and after
its first-quarter update; modeled usage does not assign it.

Full-year 2025 is **unsupported and tested to reject**. March 2025–April 2026
monthly PCA/BSA/counterpart tax history remains unrecovered. May–June 2026
rejects the unreconciled published MES $0.000151/kWh versus statutory cap;
no neighboring/current rate is substituted. Future November–December 2026
coverage is unverified. Separate source notes also identify a BGE G state-tax
rounding question requiring follow-up; existing BGE code was not changed or
represented as corrected by this work.

The source ledger `docs/utility_sources/pepco_md/sources.json` retains 37 source
records with exact originals, physical pages, hashes and exclusions. Its 28
scoped excerpts, 10 rendered receipts and other derivatives passed 134 hash
checks. Original bytes remain in ignored `.cache/pepco_md/sources/`. Proposed,
DC/Type II-only, future, blank and blocked material is distinguished from actual
selected prices. Failure to recover a document is not proof it does not exist.

August 2026 is supported through **net-of-RDM** charges: dated base increases
and offsets cancel on identical clocks and share GRT treatment. Raw versions
remain in metrics and source records; the published August composite corroborates
the net price. No individual transition allocation or separately rounded original
base/RDM invoice-line parity is claimed. The shared rounding bound describes
modeled component rounding, not a guarantee of an exact printed utility invoice.

## Frozen candidate and checks

Engine: `59ee2349ce460f72e88b71ef86c61e2308193a6b2013e3e9dcab0a53fe313716`.
Full source/frontend/test/tool/dependency pin: `.cache/pepco_md/candidate_frozen_1.json`.
All accepted tests, matrices and browser checks match that pin. Documentation
and ignored receipt writes do not change this source identity.

| Check | Result | Receipt under `.cache/pepco_md/` |
| --- | --- | --- |
| Focused pricing/form/worker/coverage/launcher | 137 passed | `focused_1/report.json` |
| Required workflow | 112 passed; 7 JavaScript checks | `workflow_frozen_1/report.json` |
| Full release regression | 4,693 passed, 1 optional HTTPS skip; 7 JavaScript checks | `release_2025_frozen_1/report.json` |
| January–February 2025 | R/GS, 6 scenarios, 33,984 representative OpenDSS interval checks | `release_2025_frozen_1/regional/validation.json` |
| July–September 2026 | R/GS, 6 scenarios, 52,992 representative interval checks | `boundaries_2026_frozen_1/regional/validation.json` |
| Independent source arithmetic on saved study flows | All 30 monthly scenario subtotals reconcile, maximum unrounded difference below $0.000001 | `independent_study_benchmarks_1.json` |
| Real HTTP saved CSV/ZIP bytes | 8 distinct matrix/seed/browser studies, 104 CSVs, 8 valid ZIPs | `2025_api_receipt_1.json`, `2026_api_receipt_1.json`, `preview_api_receipt_1.json`, `post_browser_api_receipt_1.json` |
| Sources and preservation | 134 source hashes, preserved instructions/staged content/base HEAD | `source_preservation_audit_1.json` |

Counts overlap: focused/workflow and matrix-selected tests are not added to the
release total. The optional real-TLS test skipped because `MICROGRID_TEST_CADDY`
was unset. Three paused desktop GUI modules were excluded; no native GUI was
launched and no GUI compatibility is claimed.

Twelve independently published plan/month variable composites and literal
itemized/GRT fixtures verify prices and component inclusion, including exclusion
of administrative credit/MCS from GRT and separate transmission GRT. Numerical/
convex parity, Type I/domain boundaries, year-specific USC evidence, malformed
inputs, missing/duplicate timestamps, source/date gaps and false-complete-bill
audit tampering are checked. The source's 987-kWh bill supports transmission/GRT
only; its shifted/blended supply is not treated as a calendar-month bill.
DST grids preserve 92/100 intervals, but March/November Pepco billing rejects
outside evidence coverage; no accepted Pepco DST-month study is claimed.

## Historical results and proof limits

| Period | Plan / amount scope | Grid only | PV only | PV plus battery |
| --- | --- | ---: | ---: | ---: |
| January–February 2025 | R subtotal | $458.75 | $340.44 | $291.42 |
| January–February 2025 | GS subtotal | $385.92 | $229.44 | $207.73 |
| July–September 2026 | R subtotal | $933.41 | $627.66 | $518.84 |
| July–September 2026 | GS subtotal | $753.54 | $392.48 | $353.51 |

These are synthetic household/small-office studies, not customer measurements or
promised savings. Both reference peaks are 3 kW. Equipment is 5-kW DC PV / 4-kW
AC inverter and 10-kWh storage at 3-kW charge/discharge, initial 5 kWh, 20–80%
SOC and 95% directional efficiencies. PV is south-facing at 30 degrees, 14%
system loss, 96% inverter efficiency. Estimated wear $0.03/kWh throughput is
reported separately and excluded from the cost objective. Capital costs,
incentives, payback and carbon monetization are excluded.

Native profiles are serialized/re-imported through the normal CSV contract.
Exact-site actual-year ERA5 at hypothetical 39.05 N, 77.18 W is preserved under
`.cache/pepco_md/weather/`, with raw/request hashes, UTC end padding and
Open-Meteo/Copernicus attribution. Hourly reanalysis held across quarter hours
is not measured 15-minute weather. The 2025 studies have 5,664 intervals each;
2026 studies 8,832 each. They are two- and three-month studies, not annual
validation. October prices have unit/benchmark coverage, but no completed full
October weather study is claimed as of October 26.

All **12 scenarios and 86,976 representative OpenDSS interval checks passed**.
Bills, zero exports, curtailment, balance, SOC continuity/final energy and saved
state passed artifact audits. All 10 battery-cycle primary-subtotal-cost and
minimum-cycling proofs passed their saved tolerances. This proves only the
modeled rolling-cycle subtotal objective, not a joint annual or complete-bill
optimum. Each study carries SOC across its own consecutive cycles and restores
initial energy at its final boundary; the separated studies do not bridge the
unsupported gap.

Residential 25-kVA split-phase and commercial 75-kVA single-phase replay are
representative post-dispatch steady-state checks. Actual scheduled PV, curtailment,
charge/discharge and interval-start SOC feed replay. Scheduled meter flows remain
authoritative for bills; replay losses/PCC measurements are separate. No site
survey, dynamic/protection study or network-constrained dispatch is implied.

## Browser acceptance and saved artifacts

One concise native-accessibility pass followed all required regression and
historical checks, on the same frozen engine/frontend. R February 2025 and GS
August 2026 passed configuration restore, review, actual submission, rendered
three-scenario subtotals/electrical indicators, named save and reopen from
history. The account page visibly retained Maryland/PEPCO separation, Type I,
year-specific USC and subtotal acknowledgments. No browser operation stalled.

| Plan | Actual browser-submitted study | Saved name | Worker runtime |
| --- | --- | --- | ---: |
| R | `7c776edd30094c249e52271679b89190` | Pepco MD R · validated February 2025 subtotal | 4.34 s |
| GS | `14b2cc9e05e84582ba344cb3c109e674` | Pepco MD GS · validated August 2026 subtotal | 4.74 s |

Saved downloads preserve every configuration field except the intentionally
changed display name; original submitted settings remain unchanged and both
saved results have no expiry. Actual browser cases passed another 16,992
representative interval checks, excluded from the matrix count. Files:
`browser_acceptance_receipt_1.json`, `post_browser_api_receipt_1.json`,
`browser_residential_1.png`, `browser_commercial_1.png` and the two
`browser_*_steps_1.txt` accessibility captures. Browser file-chooser/upload and
download-event waits were excluded; HTTP checks establish saved/downloaded bytes.
The electrical-summary dropdown was not separately exercised; comparison-table
electrical pass indicators were observed.

The isolated [development preview](http://127.0.0.1:59159) uses only
`.cache/pepco_md/browser_preview_1`; it does not refresh another saved store or
promote the stable engine. Earlier BGE/PPL/AEP evidence retains its recorded pin.

## Timing and reproduction

- Focused launcher: 15.15 s wall; phases pytest 15.09 s.
- Workflow launcher: 135.03 s wall; phases pytest 133.99 s.
- Release plus2025 matrix launcher: 818.64 s wall; phases pytest 797.82 s, regional 19.70 s.
- 2026 boundary launcher: 26.06 s wall; phases pytest 1.05 s, regional 24.94 s.
- Browser pass: 245.43 s elapsed wall, including observations/work between calls; not cumulative browser waiting or active development.
- Worker-reported historical runtimes: R January–February 2025 6.79 s, GS January–February 2025 7.01 s, R July–September 2026 9.45 s, GS July–September 2026 9.86 s.

Preview/API work overlapped other wall measurements. Times are not additive CPU
or active-development measurements; solver and OpenDSS time are not separately
inferred from worker aggregates.

```sh
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_pepco_md.py --test test/test_pepco_integration.py
/usr/local/bin/python3 tools/validate.py --tier workflow
/usr/local/bin/python3 tools/validate.py --tier release --regional \
  --utility pepco_maryland --period custom \
  --start-date 2025-01-01 --end-date 2025-02-28 \
  --inputs .cache/pepco_md/weather --output .cache/pepco_md/new-release
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_pepco_md.py::test_august_filed_same_clock_cancellation_preserves_raw_versions \
  --regional --utility pepco_maryland --period custom \
  --start-date 2026-07-01 --end-date 2026-09-30 \
  --inputs .cache/pepco_md/weather --output .cache/pepco_md/new-2026
```

Fresh candidate/selection requires fresh output paths. Resume must match frozen
source and re-audit saved artifacts. Private coverage views `coverage_1.md/.csv`
select Pepco evidence only and do not supersede other utilities' retained reports.
Next evidence work is missing monthly history, RRC/refund amounts/posting, MES
May/June reconciliation, and exact GS state sales-tax billing. No rate or
eligibility is invented to close those gaps.

Final preservation audit: all staged entries still match base HEAD and every Pepco
change remains unstaged. The index file byte hash changed during status refresh;
its tracked modes/blob IDs did not change. `preservation_final_1.json` records
this distinction, frozen-fingerprint equality and documentation-link checks.
