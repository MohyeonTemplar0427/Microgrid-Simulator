# Rockland Electric NJ implementation and targeted validation

Recorded 2026-10-27T23:11:14.066581+00:00. Implemented **SC1 non-TOD residential** and
**SC2 secondary metered non-demand-billed BGS-RSCP**, limited to independently
confirmed **Bergen County/Eastern Division/PJM accounts and October 2026
complete calendar cycles**. Earlier 2025–2026 gaps remain unsupported.
Read [account and billing scope](Rockland_Electric_New_Jersey.md), the
[source ledger](utility_sources/rockland_nj/README.md) and
[source pins](utility_sources/rockland_nj/sources.json).

## Candidate and preservation

Checkout: `/Users/junhayang/Desktop/EnergyEngineerSession/Microgrid_Simulator`,
`main`, HEAD `d7192951874eabcb7a88307f82f03146cf9406ae`. Frozen engine:
`3bea00f0f86c0378564447ad3536391fcec0be8b2a357ec4cdf74eb91b2317d9`.
Changed `regional.js` SHA256:
`0c9b52538eedf0fc96c661871fe3128b0a106a3422e79b842c18dbf2dc294e74`.
All source/dependency/frontend/test/tool/configuration fingerprints are retained
at `.cache/rockland_electric_nj/candidate_frozen_1.json` and remain unchanged.

New runtime modules are `src/billing/rockland_nj.py` and `rockland_nj_rates.py`;
tests are `test/test_rockland_nj.py` and `test/test_rockland_integration.py`.
Registry, explicit study defaults, absent-DER counterfactual, browser field
visibility, coverage and targeted validation selection were extended. Existing
billing math, dispatch algorithms, API/worker schema, PV/storage physics and
OpenDSS replay are reused without shared behavioral changes. No GUI was opened.

The preservation baseline covers **1,862 files**, including ACE/JCP&L changes
and ignored CLAUDE instructions. Only eight intended shared wiring/documentation
paths changed; the other 1,854 remain byte-identical. Architecture additions
preserve the previous document as an exact prefix. Final hashes, instruction-file,
HEAD/index and local-link checks are recorded at
`.cache/rockland_electric_nj/final_preservation.json`. No stage, commit, push,
deployment or stable-engine promotion was performed. Earlier utilities' reports
and immutable engine/frontend identities remain attributed to their original pins.

## Verification boundaries

**2025–2026 tariffs were researched before implementation; full-year coverage
was not established.** The executable intersection is October 2026 only.
Missing earlier generation/rider/base chains, September–November 2025
reconciliation and adopted August/September 2026 transmission versions were
not filled with current rates, stale search text or proposals. The old official
full-book URL resolves to the same current bytes, and the September 2026
transmission order provides no numeric prior tariff appendix. Failed/blocked
routes and bounded gap searches remain in the source records.

Only Bergen/Eastern/PJM is enabled. Central/Western divisions have different
control-area context; PJM RECO metadata does not assign their tariff, supplier
or wholesale node. Proposed filings are excluded from adopted prices. The
retained BPU notice is used only for descriptive control-area context.

The ordinary period rule is **26–34 days**. Calendar service and bill months
match the BGS reconciliation rule for all usage billed in the indicated month.
Fixed charges and the SC1 600-kWh monthly block stay whole. July 16, 2026's
nonlinear tier credit crossing, irregular periods and unsupported dates reject.
October has no DST transition: timezone/interval integrity and rejection of
missing/duplicate/naive/hourly data are tested; November/March grids reject
outside coverage. No accepted DST-transition billing study is claimed.

SC2 eligibility is **retained non-demand BILLING**, including proposed
PV/storage operation, not the absence of a demand-capable AMI meter. No numeric
threshold/history or November PLS was invented. The official non-demand PTC
all-kWh row independently resolves the inactive $2.79/kW transmission branch;
adjacent demand-billed rows price kW separately. The source standby rider names
demand-billed SC2/SC7. CIEP, competitive supply, TOD, primary/three-phase,
unmetered and special-service calculations remain outside scope.

Already-active executed ordinary Class I PV/storage approval, required metering,
permitted charging and sizing are independent facts. No borrowed 20-day rule
applies. Exports/opening banks and standalone storage are rejected. Ordinary
AMI/AMR with no opt-out/manual-reading/changeout fee is explicitly required.
Post-adjustment raw and component-cent totals must meet the ordinary monthly
minimum; unknown floor/contract settlement cases reject without forcing imports.
Grid-only removes DER assertions while retaining the independently assigned class.

## Sources and independent benchmarks

The ledger preserves **20 unique originals, 54 checked-in excerpts, two private
metadata excerpts and 28 render receipts**. Of the renders, 22 are marked
visually reviewed and six are retained without that assertion. All **134 hash
checks passed**; unreviewed renders are not mislabeled as visual evidence.
The official compiled PDF contains stray New York pages 4/131/132; those pages
are excluded from NJ component extraction while original bytes remain intact.
Two wrapped revision/footer labels were corrected before the candidate freeze;
rates and original/excerpt bytes were unaffected.

Ledger SHA256: `157e8b79d13c78b638995d8d1b4cf1199f131bfc24faac145ee2361a9aa35b53`.
Source audit: `.cache/rockland_electric_nj/source_preservation_audit_1.json`.
Snapshot-safe runtime data preserve effective dates, physical pages, printed
leaves/revisions, URLs, original/excerpt hashes and component status. No network
or ignored evidence file is read at runtime.

Independent October source arithmetic at 1,000 raw kWh gives unrounded SC1
$241.478 and SC2 $172.138. SBC/RGGI constituent sums, negative CIP/ZEC/RC,
separate SC1 adjustment, embedded CBT/SUT/admin and bundled RMR/EL05-121/TEC
are counted once. TTAC expired June 2021, EGCC ended February 2026 and IIP is
combined in base rates. No individual regulatory credit bank is invented.

The official annual PTC has an older transmission vintage: current October
ex-reconciliation supply differs by $0.00006/kWh SC1 and $0.00002/kWh SC2.
That difference is reconciled rather than erased. The adopted BRC's 925-kWh
example concerns its base-rate change, not an October whole invoice. No actual
customer whole-invoice calibration or exact printed monetary-rounding rule
was recovered. Existing component half-up cents and unrounded operating proofs
are not minimum rounded-cash invoice claims.

## Focused and modeled acceptance

`tools/validate.py --tier focused` passed **192 tests in
20.85s**, with no skip/failure, selecting:

- `test/test_rockland_nj.py` and `test/test_rockland_integration.py`;
- `test/test_regional_coverage.py`;
- `test/test_regional_validation_driver.py`;
- `test/test_regional_counterfactual.py`.

Checks cover source arithmetic/pins, raw quantities/600-kWh metadata, six fixed-flow
numeric/symbolic parity cases including zero imports, eligibility/state/county,
minima, dates/missing data, unsupported export/settlement, browser serialization,
queued worker, saved settings and CSV/ZIP reconciliation. Python syntax,
changed-JavaScript syntax and diff checks passed. Launcher/JUnit/log receipts are
at `.cache/rockland_electric_nj/acceptance_1/`; syntax receipt is `syntax_receipt.json`.

**Historical and full-year acceptance remain unverified.** On October 27 the
complete October actual-weather period is unavailable, and earlier source
coverage is incomplete. Therefore one explicitly labeled **modeled clear-sky
matrix** was selected on the finished frozen candidate, using the unchanged
queued worker and complete regional bill/dispatch/state/electrical audits.
It did not retrieve, backfill or replace historical/future weather. Clear-sky
irradiance with assumed 20°C air/1m/s wind is a model, not a forecast or actual
weather. Synthetic native loads and hypothetical approved accounts remain labeled.

**Two studies, six scenarios and 17,856 OpenDSS interval checks passed**:
2,976 intervals per complete October scenario. Every interval in each selected
case is checked; this is not sampled or annual electrical evidence.

| Plan | Modeled study ID | Grid / PV / PV+battery utility charges | Interval checks |
| --- | --- | ---: | ---: |
| SC1 | 668972543f234f7393dc48be9dcf017b | $283.85 / $191.07 / $149.46 | 8,928 |
| SC2 | 311ac025c96a4d72b811ae8a698b1feb | $174.25 / $85.90 / $73.40 | 8,928 |

Both plans use generic native shapes with representative 3-kW peak,
5-kW DC/4-kW AC PV and 10-kWh/3-kW storage. The hypothetical Bergen location
is not territory proof. Per-cycle perfect foresight, retained SOC and scheduled
meter flows are modeled; representative 120/240V/25kVA/100A replay and 0.95
lagging load PF do not establish surveyed-site adequacy or alter billing PF.

The private matrix harness initially used two incorrect metadata fields; both
errors and original harness versions are preserved. After exact request, engine
and frozen-fingerprint checks, the completed SC1 study was re-audited rather
than simulated again. SC2 ran once. The source/test/production candidate never
changed. See `modeled_acceptance_1/harness_failure_1.json`, `harness_failure_2.json`
and its final `validation.json` under `.cache/rockland_electric_nj/`.

The standalone independent calculator imports no production/test/rate/math code.
It reconciled all six saved bills and constituent CSVs, credits/minima, account
approval, dispatch power/PV balance, SOC bounds/recursion/terminal state,
throughput, objectives and proof flags. Maximum unrounded component difference
was 1.42e-14USD; bill difference was zero,
with no Decimal/runtime cent discrepancies. All four PV cases have primary
unrounded cost proofs and both battery cases have secondary minimum-cycling
proofs. All annual-optimum flags are null. The independent receipt documents
ten CSV files that lacked original manifest hashes: the auditor independently
read/hashed/reconciled their bytes without claiming earlier hash pins existed.
See `.cache/rockland_electric_nj/independent_audit.json` and `independent_audit.py`.

The selected matrix worker runtimes total
8.65s; harness recovery/audit
and research wall time are separate. Matrix API checks verified 26 CSV tables
and ZIP manifests/content bytes. No unaffected utility matrix, broad regional,
workflow/full release or native GUI suite was rerun. This is targeted modeled
acceptance, not a full-release or historical acceptance pass.

## Browser pass and final evidence

One concise background pass on the frozen engine covered both plans: restore
seed settings, inspect scope/account/equipment/clear-sky controls, submit new
studies, read rendered results, name/save, return home and reopen from history.
SC2 advanced fields visibly retained non-demand billing, no-CIEP and active DER
evidence. One native Next click did not advance SC2; the current labeled control
succeeded. No operation timed out or stalled. The normal stop-on-stall rule was
not bypassed.

- SC1 browser study: `84336bb86a8e40bc996aecd29d1c73b2`.
- SC2 browser study: `37b4178e72794fe7be1f553f0ade407d`.
- Isolated preview: `http://127.0.0.1:59164/`, data at
  `.cache/rockland_electric_nj/browser_preview_1`; previous servers preserved.
- Validated modeled store copied byte-for-byte as seed, without seed simulations.
- Seventeen configuration fields per plan matched the validated requests exactly.
- The two browser reruns have a **separate 17,856** modeled electrical checks,
  not added to or relabeled as the selected matrix's count.
- Browser-created study API audits verified another 26 CSV tables and ZIP bytes.
  Browser download-event/chooser, uploads, live weather, manual territory discovery,
  alternate table-selector and native GUI assertions were excluded. API byte
  checks do not prove those UI actions occurred.

Receipts: `.cache/rockland_electric_nj/browser_acceptance.json`,
`browser_configuration_audit.json`, `browser_api_artifact_audit_1.json`,
`api_artifact_audit_1.json`, observations and two screenshots. Browser observations
span 127.10s wall-clock, including tool waits and analysis; browser
worker runtimes total 9.32s. As of this report, elapsed wall time from orientation
is 25.53minutes, including source research,
authoring, errors, tool waits and overlapping work. It is not measured active
development time.

![Reopened modeled SC2 result](../.cache/rockland_electric_nj/browser_preview_1/browser_sc2_result.png)

Unverified scope remains: all earlier 2025–2026 composite periods, actual
historical weather/full-year studies, other divisions/control areas, actual
customer eligibility/invoice calibration, irregular cycles, demand/standby/CIEP,
TOD/special service, standalone storage, export banking/cashout, joint annual
and rounded-cash minima, and surveyed-site engineering/interconnection approval.
