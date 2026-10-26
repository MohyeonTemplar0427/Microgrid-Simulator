# BGE Maryland implementation validation

Reviewed October 25, 2026. Development candidate on `main`, base HEAD `21541dc`.
No staging, commit, push, deployment or stable-engine promotion. Original
`AGENTS.md` changes and ignored `CLAUDE.md` are preserved byte-for-byte. The
[PPL/AEP report](PPL_AEP_Ohio_Implementation_Validation.md), its original evidence
pins, AEP April 2026 gap, 11 unproven PPL commercial cycling proofs and partial
browser assertions remain unchanged.

## Scope and source evidence

BGE R residential and secondary G Type I SOS support matching complete calendar
service/billing months January 2025–October 2026. The selected tax locality is
explicitly confirmed unincorporated Anne Arundel County. Existing G Type I and
USC annual-delivery bracket, ordinary service and non-export interconnection
are independently asserted account facts. No export credit, NEM bank, wholesale
price substitution or inferred territory is enabled. See [BGE scope](BGE_Maryland.md).

**R returns a verified recurring-tariff subtotal**, excluding historical-account
legislative relief refunds whose eligibility, amounts and posting cycles are
unverified. G includes ordinary taxes under the documented Maryland taxable-price
rules; actual G customer-statement calibration remains unavailable. These are
explicit scope limits, not provisional or substituted rate values.

The checked-in `docs/utility_sources/bge_md/sources.json` has 31 source records
with original/excerpt identities and physical page references. Originals are in
ignored `.cache/bge_md/sources/`. All 87 retained original/extraction/excerpt
hashes passed audit. Blocked older URLs and PSC notices remain recorded as
unretrieved; final downloaded utility component history supplies the executable
rates. The current CSEG ledger verifies final June–September 2026 supply;
pending-transmission projections were not substituted. Independent review
found no blocking billing defect.

## Frozen candidate and checks

Engine: `2863c3ea5ea424d914c1db40f49b625cd137f5a7d19a41f06a82ea58e1bd6f79`.
Full source/frontend/test/tool/dependency fingerprints:
`.cache/bge_md/candidate_frozen_1.json`. They remained unchanged through release,
matrices and browser acceptance. Documentation/evidence writes do not alter this
source identity.

| Check | Result | Receipt under `.cache/bge_md/` |
| --- | --- | --- |
| Frozen focused billing/main-form/worker | 106 passed | `focused_frozen_1/report.json` |
| Required API/queued-worker/electrical workflow | 112 passed; 7 JavaScript syntax checks passed | `workflow_frozen_1/report.json` |
| Full release regression | 4,600 passed; 1 optional HTTPS skip; 7 JavaScript checks passed | `release_annual_frozen_1/report.json` |
| Annual 2025 matrix | R/G, 6 scenarios, 210,240 representative OpenDSS interval checks | `release_annual_frozen_1/regional/validation.json` |
| January–September 2026 matrix | R/G, 6 scenarios, 157,224 representative interval checks | `boundaries_2026_frozen_1/regional/validation.json` |
| Independent published arithmetic on actual study flows | 126 monthly scenario bills reconcile; maximum unrounded difference below $0.000001 | `independent_study_benchmarks_1.json` |
| HTTP CSV/ZIP and saved bytes | 4 matrix, 2 seed and 2 actual browser studies; 104 CSV tables and 8 ZIPs verified | `annual_api_receipt_1.json`, `boundaries_2026_api_receipt_1.json`, `preview_api_receipt_1.json`, `post_browser_api_receipt_1.json` |
| Source/preservation audit | 87 source hashes, unchanged instructions/HEAD/main, no staged paths | `source_and_preservation_audit_1.json` |

Counts overlap: focused/workflow/matrix-selected tests are included in the
release count and are not additional unique passing tests. The earlier agent
run executed 99 tests successfully but was correctly invalidated by concurrent
checkout edits; `focused_agent/report.json` is retained as invalidated evidence.
A metadata-only physical-page correction preceded the accepted frozen candidate.
The optional real-TLS test was skipped because `MICROGRID_TEST_CADDY` was unset.
The three paused desktop GUI modules were excluded; no native GUI was launched
or GUI compatibility claimed.

The 44 independently transcribed utility-published variable composites verify
all selected plan/month combinations. Literal itemized/tax-base fixtures and
numerical/convex parity supplement them. A legislative 901-kWh residential
example corroborates delivery and tax components only; its shifted-cycle supply
is not relabeled as a complete-calendar benchmark. DST, missing/duplicate data,
unverified dates, partial cycles, supplier/tax facts, Type I thresholds, export
rejection and absent-DER counterfactuals are checked explicitly.

## Historical results and physical inputs

| Period | Plan / amount scope | Grid only | PV only | PV plus battery |
| --- | --- | ---: | ---: | ---: |
| 2025 full year | R · subtotal | $2,798.32 | $1,978.31 | $1,676.66 |
| 2025 full year | G · ordinary bill | $2,715.20 | $1,548.66 | $1,394.18 |
| January–September 2026 | R · subtotal | $2,304.48 | $1,591.18 | $1,334.85 |
| January–September 2026 | G · ordinary bill | $2,321.94 | $1,255.19 | $1,118.33 |

These are deterministic synthetic household/office studies, not observed
customer consumption or promised savings. Both reference peaks are 3 kW, with
5-kW DC PV / 4-kW AC inverter and 10-kWh storage limited to 3 kW in each direction.
Initial energy is 5 kWh, SOC limits 20–80%, charge/discharge efficiencies 95%,
and inverter efficiency 96%. PV faces south at 30 degrees with 14% system losses.
Wear is excluded from the bill objective and reported separately at $0.03/kWh
throughput. Capital costs, incentives and payback are excluded.

The 2025 native totals are 13,887.5364 kWh residential and 11,981.7324 kWh for the
small office. Inputs are serialized/re-imported through the ordinary native CSV
contract. Exact-site ERA5 at hypothetical 39.08 N, 76.57 W is retained in
`.cache/bge_md/weather/`, including original requests, raw hashes, end padding
and Open-Meteo/Copernicus attribution. Hourly reanalysis is held over quarter
hours; it is not measured 15-minute weather. Full-year 2025 has 35,040 intervals,
including 92 on March 9 and 100 on November 2. The 2026 studies cover nine months,
26,204 intervals each; they are not annual 2026 validation. October rates have
unit/benchmark coverage but no full October historical-weather study.

All 12 matrix scenarios and **367,464 representative OpenDSS interval checks**
passed. SOC continuity, terminal energy, directional balance, zero exports,
curtailment, bills and credit/state reconciliation passed independent saved-artifact
audits. All 42 battery-cycle primary-cost and minimum-cycling proofs passed their
saved tolerances. This is rolling historical perfect foresight, not a joint
annual-optimum proof. Representative residential 25-kVA split-phase and commercial
75-kVA single-phase circuits are post-dispatch steady-state checks; scheduled
meter flows remain authoritative for bills. No site survey, protection/transient
validation or network-constrained dispatch is implied.

## Browser acceptance and timing

One concise native-accessibility browser pass ran after release and both
historical matrices passed, on the same frozen engine/frontend. It covered R in
February 2026 and G in November 2025. Restored account/source/tax/USC controls,
cycles, native CSV, cached weather, PV/inverter/battery, excluded-wear objective,
review, actual submission, rendered three-scenario results, named save and
reopening from recent history all passed. R visibly showed its subtotal and
refund exclusion; G showed complete bills within its account scope. No operation
stalled. File-chooser/upload and download-event automation were excluded; HTTP
checks verified saved bytes instead. The electrical-summary dropdown was not
separately exercised; comparison-table electrical pass indicators were observed.

| Browser case | Actual submitted study | Saved name | Worker runtime |
| --- | --- | --- | ---: |
| R | `85e5a8802bc3412bb2732a60c4cdec05` | BGE R · validated February 2026 subtotal | 4.36 s |
| G | `6086fd2e8b6c43649b70fcf967c1ce76` | BGE G · validated November 2025 Type I | 4.76 s |

All submitted configuration fields except the intentionally changed display name
exactly match their audited seeds and saved downloads. The original submissions
remain unchanged; saved studies have no expiry. Actual browser studies passed
another 16,716 representative interval checks, excluded from the matrix total.
Receipts: `.cache/bge_md/browser_acceptance_receipt_1.json` and
`post_browser_api_receipt_1.json`; screenshots `browser_residential_1.png` and
`browser_commercial_1.png`. The isolated development preview is
[localhost port 58367](http://127.0.0.1:58367), using only
`.cache/bge_md/browser_preview_1` and its pinned development engine.

Frozen focused launcher wall time was 13.92 s; workflow 137.70 s. Release plus
annual matrix launcher wall time was 854.59 s, including 778.30 s pytest and
75.13 s matrix phases. The 2026 launcher took 60.50 s, including its 59.33 s
matrix phase. Worker-reported runtimes were 33.05/34.09 s for 2025 R/G and
25.24/26.29 s for 2026 R/G. Browser-pass elapsed wall time was 431.82 s,
including observations and work between calls; this is not active development
or cumulative browser-tool waiting. Preview/API work overlapped other wall
measurements, so times must not be added as CPU time. No browser wait stalled.

## Reproduction and remaining boundaries

```sh
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_bge_md.py --test test/test_bge_integration.py
/usr/local/bin/python3 tools/validate.py --tier workflow
/usr/local/bin/python3 tools/validate.py --tier release --regional \
  --utility bge_maryland --period annual --inputs .cache/bge_md/weather \
  --output .cache/bge_md/new-release
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_bge_md.py::test_dst_uses_elapsed_intervals_not_days_times_96 \
  --regional --utility bge_maryland --period custom \
  --start-date 2026-01-01 --end-date 2026-09-30 \
  --inputs .cache/bge_md/weather --output .cache/bge_md/new-2026
```

Use fresh output paths for a changed candidate or selection. Resume requires
matching immutable source and artifact re-audit; no old passing report is proof
for changed source. Private coverage views are `.cache/bge_md/coverage_1.md`
and `.csv`; they select BGE evidence only and do not supersede other utilities'
retained receipts. Still outside scope: exact residential relief amount/posting,
G customer-statement tax calibration and USC reclassification timing,
partial/shifted cycles, other localities/classes/suppliers, GS TOU, export/NEM
settlement, and November–December 2026 rates. No missing rate is inferred.
