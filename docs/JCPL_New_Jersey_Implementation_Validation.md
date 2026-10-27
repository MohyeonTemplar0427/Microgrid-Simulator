# JCP&L New Jersey implementation and targeted validation

Recorded 2026-10-27T22:00:21.626823+00:00. Implemented ordinary **RS residential** and the
bounded **Company-assigned GS secondary no-demand-meter BGS-RSCP branch** in
the shared backend/local browser. Verified components cover **January 2025–
October 2026 complete calendar cycles**. Actual account eligibility is conditional;
the validated accounts are explicitly hypothetical. Read [billing scope](JCPL_New_Jersey.md)
and the [official-source ledger](utility_sources/jcpl_nj/README.md) before reuse.

## Candidate and preserved checkout

- Checkout: `/Users/junhayang/Desktop/EnergyEngineerSession/Microgrid_Simulator`,
  `main`, HEAD `d7192951874eabcb7a88307f82f03146cf9406ae`.
- Frozen immutable engine: `17d6ca6a9c3a17dee7c1feabbae717454e960ab1577ebdcc53d3921b03e8d6e8`.
- Changed browser file `regional.js` SHA256:
  `0531f516b7e7506136f308197a7c9f0de83ca2ecffbcd7740a13f5b11de1bd19`.
- Full source/dependency/frontend/test/tool/configuration fingerprints:
  `.cache/jcpl_new_jersey/candidate_frozen_2.json`.
- The first freeze had the same engine/frontend/tools; only the source-test
  selector was corrected afterward. Both freeze identities and original logs
  remain preserved. No mismatched-pin resume or old-result relabeling occurred.
- Final baseline, index, instruction-file and fingerprint checks:
  `.cache/jcpl_new_jersey/final_preservation.json`. All 1,696 baseline files were
  rechecked; only the eight intended shared wiring/documentation paths changed.
  Prior ACE and earlier utility changes were retained. Architecture additions
  preserve the previous file as an exact prefix.
- No staging, commit, push, deployment or stable-engine promotion was performed.
  Native GUI development/testing remained paused.

New runtime paths are `src/billing/jcpl_nj.py` and `jcpl_nj_rates.py`; new tests
are `test/test_jcpl_nj.py` and `test/test_jcpl_integration.py`. Existing regional
registry, counterfactual, study defaults/initial-state checks, browser field
visibility, coverage tooling and explicit utility matrix selection were extended.
Billing math, dispatch algorithms, API/worker schema, PV/storage physics and
electrical replay were reused without shared behavioral changes.

## Source and billing acceptance

The source ledger pins **25 unique originals, 283 excerpt references across
152 distinct checked-in excerpts, and five visually reviewed render receipts**.
All referenced originals/text/excerpts/derivatives were hash-checked in
`.cache/jcpl_new_jersey/source_preservation_audit_1.json`.
Ledger SHA256: `dbf2f43b15306fe3f2d91f27eb3738f31f162005a93c2ddd2bf8c98f9e4722df`.

Fifteen adopted Part III books preserve independently dated distribution,
supply and rider leaves; historical/current Parts I/II preserve billing terms.
No missing rate was inferred, current rate backfilled or neighboring utility's
rounding/cycle restriction imported. Utility, BGS supplier, NJ tax jurisdiction,
PJM JCPL market label and FE-JC emergency region remain separate; no wholesale
LMP, PLC/NSPL or extra tax/admin amount is added to inclusive retail charges.

Independent arithmetic covers all 22 source months × both plans; exact source
dates, SBC/RRC constituent sums, retained TEC owner blocks, raw kWh, 600/1,000-kWh
monthly blocks, mandatory RS relief/recovery and nonnegative postcredit balances.
Unequal interval-energy tests prove actual service-date allocation at September
15, 2025 and July 15, 2026; February 15, 2026 ZEC reservation is not backdated.
Six fixed-flow numeric/symbolic parity cases passed. Official September 2026 PTC
and May 2025/July 2026/October 2026 BPU 650-kWh transmission impacts reconcile.
No independent whole customer invoice was recovered; these remain component
benchmarks and independent source-literal bill calculations, with no exact
printed-invoice rounding or minimum rounded-cash optimum claim.

GS eligibility checks retain Company no-meter assignment, Contract Demand and
prior eleven actual created peaks at most 10 kW, current 15-minute imports at most
10kW, separate November PLS strictly below 500 kW and scenario-specific carried
conservative history. Annual 2025 overrides explicitly change from November 2023
to November 2024 at June 1; September 2026 uses November 2025. Initial missing history,
state gaps, invalid PLS dates and classification derived from modeled demand reject.
DER requires already-active ordinary Class I approval, correct metering/initiation,
zero exports/bank, permitted charging and GS utility-confirmed no-STB/retained
no-meter treatment. No capacity-based standby exemption is asserted.

## Targeted checks and selected matrix

**267 unique targeted tests passed across two runs on the same production
engine/frontend.** The initial run recorded 266 passes and one source-preservation
guard failure: it counted the discovery HTML alongside 15 tariff PDFs. The guard
was narrowed to adopted PDF records; hash and rate-pin assertions stayed intact.
Only that affected check was rerun, and passed. The original failed report is
retained honestly at `.cache/jcpl_new_jersey/acceptance_1/report.json`; the final
affected-check/matrix report passed at
`.cache/jcpl_new_jersey/acceptance_2/report.json`.
The matrix never ran on the failed first report.

Initial explicit test selection:

- `test/test_jcpl_nj.py` and `test/test_jcpl_integration.py`;
- `test/test_regional_coverage.py`;
- `test/test_regional_validation_driver.py`;
- `test/test_regional_counterfactual.py`.

Checks include form serialization, queued worker, saved settings, real bill
reconciliation, CSV/ZIP contents, provider/jurisdiction/market identity rejection,
annual PLS overrides, inherited GS state, boundaries, DST, missing/duplicate data,
unsupported cycles/settlement and hidden scope/rounding changes. Python syntax,
`node --check src/local_web/static/regional.js` and whitespace checks passed;
see `.cache/jcpl_new_jersey/syntax_receipt.json`.

One final selected JCP&L matrix covers full-year 2025 and September 2026 for
both plans, each with grid-only, PV-only and PV-plus-battery scenarios:
**4 studies, 12 scenarios, 78 monthly scenario bills and 227,520 all-interval
representative OpenDSS checks**, all passed. This is not sampled electrical
coverage. The extra 2026 month checks the subsequent adopted supply/transmission
regime; other 2026 boundaries use source arithmetic/parity checks, not annual
electrical claims. No unaffected utility matrix was rerun.

| Case | Study ID | OpenDSS interval checks | Grid / PV / PV+battery utility charges |
| --- | --- | ---: | --- |
| RS-annual | 8708be01bb8d4461b7f06bf08b68b0f5 | 105,120 | $2,691.90 / $1,817.81 / $1,500.34 |
| RS-monthly | 736835fa45284e6a8f490c5a83b1f07b | 8,640 | $257.57 / $176.63 / $147.24 |
| GS-annual | 92a860393af44a819930b84f1c3861be | 105,120 | $3,873.53 / $2,920.16 / $2,856.77 |
| GS-monthly | 1471fa8e31e64db29f63a6bf6bf3e5b0 | 8,640 | $359.43 / $281.84 / $278.21 |

These are hypothetical operating studies, not customer savings predictions.
Both plans use 5 kW DC/4 kW AC PV, 10 kWh/3 kW storage; deterministic household/office
native loads have representative peaks 3/5 kW. GS hypothetical contract is 5 kW,
inherited actual-peak ceiling 10 kW and independently assigned PLS 10 kW. The
Monmouth County coordinates do not establish territory. Retained hourly ERA5
weather is held across 15-minute intervals, with Open-Meteo/Copernicus attribution;
it is reanalysis, not measured subhourly/site weather. Inputs are pinned by
`.cache/jcpl_new_jersey/weather/weather-input-manifest.json` and each study.

The independent calculator imports no production billing/rate/math/test code.
It checked every saved monthly charge, component CSV, cents, scenario sum,
service-date energy split, history/PLS/DER fact, objective and dispatch balance.
Max unrounded component difference: 2.84e-14USD;
max bill difference: 5.68e-14USD;
no source-Decimal/runtime cent discrepancies. Its only adjusted private audit
schema assumption was that a single-cycle study records annual proof as null
while annual studies record false; neither claims a joint annual optimum.
See `.cache/jcpl_new_jersey/independent_audit.json` and `independent_audit.py`.

All 26 PV-only and 26 PV-battery cycles have primary unrounded cost proofs; all 26
battery cycles have secondary minimum-cycling proofs. Grid-only is a direct
baseline. No joint annual optimum is claimed. SOC, charge/discharge, no-export,
power balance, credits/history and bill/dispatch reconciliation passed; replay
does not replace scheduled billing flows with lossy PCC diagnostics. Representative
120/240 V split-phase/25 kVA/100 A electrical assumptions do not establish actual
customer equipment adequacy or interconnection approval.

The matrix API audit verified **52 CSV tables** and ZIP manifests/content bytes
across all four saved studies, without browser download events. Private coverage
was generated from the new evidence at `.cache/jcpl_new_jersey/coverage.md` and
`coverage.csv`; published historical coverage/evidence was preserved. Workflow,
full release, broad regional suite, unrelated utility matrices and GUI checks
were excluded under the current impact policy. This is targeted acceptance,
not a full-release pass.

## Browser acceptance and retained evidence

One concise background-browser pass on the frozen engine covered both plans:
restore validated settings, inspect the affected form/account fields, submit a
new study, read rendered results, name/save, return home and reopen from history.
GS advanced controls visibly retained contract/history/November PLS/active DER
and explicit utility no-STB evidence. No browser operation stalled or timed out.

- RS browser study: `daeafb43925e44bfa1fa5fe8fca08278`.
- GS browser study: `9562aa1ff6df458e9cd43ef75bc8786c`.
- Preview: `http://127.0.0.1:59163/`, isolated data under
  `.cache/jcpl_new_jersey/browser_preview_1`; previous local servers were preserved.
- Exact validated matrix store was copied as the seed; no new seed simulation.
- Browser-created studies preserved 17 configuration fields each, including
  accounts/cycles, native load, cached weather, equipment and operating approval.
- Their two reruns have a separate 17,280 representative interval checks, not
  added to or relabeled as the selected matrix's 227,520 checks.
- Browser result APIs verified 26 CSV tables plus ZIP bytes. Browser download-event,
  file-chooser/upload, live weather retrieval, manual territory discovery and
  alternative table-selector UI assertions were excluded. API success does not
  prove those excluded UI actions.
- Receipts: `.cache/jcpl_new_jersey/browser_acceptance.json`,
  `browser_configuration_audit.json`, `browser_api_artifact_audit_1.json`,
  `api_artifact_audit_1.json`, plus browser observations and two screenshots.

![Reopened GS browser result](../.cache/jcpl_new_jersey/browser_preview_1/browser_gs_result.png)

Timing is separated: the initial test phase took
30.58s, the affected-check rerun
1.15s, and the matrix phase
127.50s including its artifact audits.
Matrix worker-reported runtime totals
113.34s,
which is included in that matrix phase, not additional time. Browser observations
span 170.39 s wall-clock, including tool waits and analysis; two
browser rerun workers took 12.60 s combined. As of this record, total wall time
since checkout orientation is49.50minutes, including research, tools,
authoring and overlapping work; it is not an active-development measurement.

## Remaining limits

No general metered GS demand/ratchet/standby formulas, three-phase/primary,
special provisions, irregular-period proration, negative credit settlement,
standalone storage, export/NEM banking/cashout or post-October 2026 prices are
enabled. The conditional GS no-STB/ordinary service facts need real utility
evidence for an actual customer. Full-year 2026 electrical acceptance, actual
customer invoice calibration, joint annual optimization, rounded-cash minima,
surveyed-site electrical validation and excluded browser actions remain unproven.
Earlier utilities' reports keep their original candidate and frontend pins.
