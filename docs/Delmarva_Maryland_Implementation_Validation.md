# Delmarva Maryland implementation validation

Reviewed October 26, 2026. Development on `main`, base HEAD `cc8977f`.
Existing Pepco work, repository instructions and staged content are preserved.
This work issued no stage, commit, push, deployment or stable-engine promotion.
BGE/Pepco/PPL/AEP evidence retains its recorded source identity and limitations.

## Coverage and billing scope

R residential SOS and **utility-assigned E.3 estimated-demand SGS-S Type I SOS**
support January–June 2025, September 2025 and May–October 2026, matching complete
calendar service/billing months only. Initial locality is explicitly confirmed
unincorporated Wicomico County. Local no-additional-energy-levy scope is a
code-based inference plus account confirmation, not a zero-tax certificate.
Utility, supplier, jurisdiction, Type I history, demand method, USC assignment,
interconnection and multi-state DPL metadata remain independent facts.

Both plans are verified-charge **subtotals**, not complete bills. R excludes
unrecovered RGGI/RRC and legislative relief/refunds. SGS-S excludes unresolved
state sales-tax base/bracket calculation. Exclusions are not zero/exemptions;
complete-bill savings and complete-bill optima are not established. Full-year
2025 rejects. July/August 2025 intramonth MES/transmission allocation and
October 2025–April 2026 monthly component history remain unverified. No current
rate, proposed filing, Delaware rate or neighboring utility fills a gap.

SGS-S distribution demand is real: $4.303679 per billed kW. The utility must
have assigned E.3 estimation and approved retaining it across the study scenarios.
Each scenario imports at most 3,500 kWh/month with actual 15-minute peak below
20 kW; billed demand is kWh/175. Distribution demand is charged, transmission's
first 20 kW is free and its first 3,500 kWh energy block is charged. Metered,
assessed, off-peak and larger-account options reject. No half-kW rounding tie is
invented. Year-specific USC evidence must establish the assigned band before
and after its first-quarter update; it is not recomputed by the optimizer.

Delmarva GRT is embedded in applicable filed rates. No Pepco-style percentage
adder is applied. The actual filed retail MES $0.000151/kWh is retained in its
verified periods; its unexplained distinction from the statutory assessment cap
is disclosed without an invented decomposition. An archived July 6, 2026 filing
explicitly makes $0.000150 effective July 1. See [scope and rules](Delmarva_Maryland.md)
and [source ledger](utility_sources/delmarva_md/README.md).

The source ledger preserves 29 originals, 26 scoped excerpts and 13 rendered
receipts. All 113 original/derivative/receipt hash checks passed; originals
remain in ignored `.cache/delmarva_md/sources/`. Blocked routes, proposed pages,
blank future entries, missing history and visual transcriptions are labeled.
Failure to recover a source is not proof it does not exist.

## Frozen candidate and validation

Engine: `8f8f1c069120c62812a1bdaa1d6e92488a038dde4642d26042c2d7b1f95a6d3c`.
Full source/frontend/test/tool/dependency pin: `.cache/delmarva_md/candidate_frozen_1.json`.
All accepted tests, matrices and browser evidence match this pin. Documentation
and private receipts do not change source identity. Earlier evidence is not
relabeled as validation of this candidate.

| Check | Result | Receipt under `.cache/delmarva_md/` |
| --- | --- | --- |
| Focused pricing/form/worker/coverage/launcher | 148 passed | `focused_1/report.json` |
| Required workflow | 112 passed; 7 JavaScript checks | `workflow_frozen_1/report.json` |
| Full release | 4,797 passed, 1 optional HTTPS skip; 7 JavaScript checks | `release_2025_frozen_1/report.json` |
| January–June 2025 | 6 scenarios, 104,232 representative OpenDSS interval checks | `release_2025_frozen_1/regional/validation.json` |
| September 2025 | 6 scenarios, 17,280 representative interval checks | `boundary_sep2025_frozen_1/regional/validation.json` |
| May–September 2026 | 6 scenarios, 88,128 representative interval checks | `boundaries_2026_frozen_1/regional/validation.json` |
| Independent published arithmetic on saved flows | 72 monthly scenario subtotals reconcile within $0.000001 | `independent_study_benchmarks_1.json` |
| Real HTTP CSV/ZIP bytes | 10 distinct matrix/seed/browser studies, 130 CSVs, 10 valid ZIPs | `*_api_receipt_1.json` |
| Source/preservation audit | 113 hashes; unchanged instructions/Pepco/staged content | `source_preservation_audit_1.json` |

Counts overlap and are not added to the release total. The first focused attempt
could not bind loopback sockets in the sandbox; its diagnostics remain saved.
The same candidate/selection resumed with required loopback access and passed.
The real Caddy HTTPS test skipped because `MICROGRID_TEST_CADDY` was unset.
Three paused desktop GUI modules were excluded, no native GUI was launched and
no GUI compatibility is claimed.

Twenty-six independently published monthly variable composites and separate
literal component/customer/USC/demand fixtures establish arithmetic. A 1,750-kWh
SGS-S case independently gives 10 estimated kW and $43.03679 distribution demand.
Numerical/symbolic parity, date/coverage boundaries, peak/energy caps, missing or
duplicate timestamps, eligibility/USC/DER evidence and false-complete-bill audit
tampering are tested. March 2025 uses 743 elapsed hours and a 92-interval DST
day; November's 100-interval grid is preserved but unsupported billing rejects.
These are component/source benchmarks, not customer-invoice calibration. Shared
component half-up cent rounding and its bound do not prove exact printed invoice
line rounding or the omitted state-tax calculation.

## Historical results and proof limits

| Period | Plan / amount scope | Grid only | PV only | PV plus battery |
| --- | --- | ---: | ---: | ---: |
| January–June 2025 | R subtotal | $1,476.85 | $1,016.80 | $848.13 |
| January–June 2025 | SGS-S subtotal | $1,331.96 | $739.78 | $654.16 |
| September 2025 | R subtotal | $241.98 | $171.21 | $147.51 |
| September 2025 | SGS-S subtotal | $219.41 | $133.54 | $123.99 |
| May–September 2026 | R subtotal | $1,331.74 | $877.02 | $717.57 |
| May–September 2026 | SGS-S subtotal | $1,159.30 | $607.18 | $542.85 |

These are synthetic household/small-office studies, not customer measurements
or promised savings. Both reference peaks are 3 kW. Equipment is 5-kW DC PV /
4-kW AC inverter and 10-kWh storage at 3-kW charge/discharge, initial 5 kWh,
20–80% SOC and 95% directional efficiencies. PV is south-facing at 30 degrees,
14% system loss and 96% inverter efficiency. Wear $0.03/kWh throughput is reported
separately and excluded from the optimization objective. Capital costs,
incentives, payback and carbon monetization are excluded.

Native profiles are serialized/re-imported through the normal CSV contract.
Exact-site actual-year ERA5 at hypothetical 38.40 N, 75.65 W is preserved under
`.cache/delmarva_md/weather/`, with request/raw hashes, UTC end padding and
Open-Meteo/Copernicus attribution. Hourly reanalysis held across quarter hours
is not measured 15-minute weather. Per-study intervals are 17,372 for the
six-month 2025 window, 2,880 for September 2025 and 14,688 for May–September 2026.
These are partial-year windows, not annual validation. October prices have
unit/benchmark coverage; no completed October weather study is claimed as of
October 26.

All **18 scenarios and 209,640 representative OpenDSS interval checks passed**.
Bills, zero exports, curtailment, power balance, SOC continuity/final energy and
saved state passed artifact audits. All 24 battery-cycle primary-subtotal-cost
and minimum-cycling proofs passed saved tolerances. The study carries SOC between
its own consecutive cycles and restores initial energy only at the final boundary.
This is rolling-cycle subtotal optimization, not a joint annual or complete-bill
optimum. Secondary-circuit replay is representative, not surveyed-site approval.

## Browser/API acceptance

The single background browser pass used [the isolated preview](http://127.0.0.1:59160),
only `.cache/delmarva_md/browser_preview_1`, on the frozen candidate. Both plans
visibly restored provider/MD-versus-DPL metadata, Wicomico tax facts, subtotal
acknowledgment, Type I/E.3/USC evidence, dates/cycles, native CSV, ERA5, PV/inverter,
storage and wear-excluded objective; then submitted actual reruns, rendered all
three scenarios and incomplete-bill/electrical pass indicators, saved a custom
name and reopened it from history. SGS-S's estimation and year-specific evidence
fields were explicitly observed. No browser operation timed out or stalled.

The initial commercial off-screen Next activation did not advance. A screenshot
identified the visible navigation position; a root AX scroll target was detached.
The target was corrected using observed screen coordinates, and navigation then
completed. These were resolved interaction issues, not passing assertions inferred
from API checks. File chooser/upload and download-event automation were excluded;
real HTTP artifacts establish saved/downloaded bytes. The electrical-detail
dropdown was not separately exercised.

| Plan | Actual browser study | Saved name | Worker runtime |
| --- | --- | --- | ---: |
| R | `426d048886054e87bfb0586416434092` | Delmarva MD R · validated March 2025 subtotal | 4.75 s |
| SGS-S | `acd0c60bf39c400993f47d304dd83be1` | Delmarva MD SGS-S · validated August 2026 subtotal | 5.17 s |

Downloaded saved settings preserve every configuration field except the chosen
name; submitted settings remain unchanged and both saved results have no expiry.
The actual browser studies add 17,844 representative electrical interval checks,
excluded from the historical-matrix count. Proof files are `browser_*_steps_1.txt`,
`browser_residential_1.png`, `browser_commercial_1.png`,
`browser_acceptance_receipt_1.json` and `post_browser_api_receipt_1.json`.
The preview does not refresh another saved store or promote the stable engine.


## Timing and reproduction

- focused_1: launcher 15.06 s wall; phases pytest 15.01 s.
- workflow_frozen_1: launcher 140.54 s wall; phases pytest 139.41 s, node-app 0.11 s, node-comed 0.11 s, node-comed_simulation 0.11 s, node-municipal 0.11 s, node-pjm 0.11 s, node-regional 0.11 s, node-socal 0.11 s.
- release_2025_frozen_1: launcher 879.97 s wall; phases pytest 833.26 s, node-app 0.11 s, node-comed 0.11 s, node-comed_simulation 0.11 s, node-municipal 0.11 s, node-pjm 0.11 s, node-regional 0.10 s, node-socal 0.11 s, regional 45.51 s.
- boundary_sep2025_frozen_1: launcher 15.79 s wall; phases pytest 1.05 s, regional 14.66 s.
- boundaries_2026_frozen_1: launcher 38.89 s wall; phases pytest 1.05 s, regional 37.76 s.
- Browser pass: 260.45 s elapsed wall, including observations/work between calls, not active development or cumulative tool waits.
- Worker-reported historical runtimes: R January–June 2025 18.46 s, SGS-S January–June 2025 19.09 s, R September 2025 4.55 s, SGS-S September 2025 4.54 s, R May–September 2026 15.38 s, SGS-S May–September 2026 15.65 s.

Preview/API work overlapped other wall measurements; times are not additive CPU
or active-development measurements. Solver/OpenDSS times are not independently
inferred from aggregate worker runtimes.

```sh
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_delmarva_md.py --test test/test_delmarva_integration.py
/usr/local/bin/python3 tools/validate.py --tier workflow
/usr/local/bin/python3 tools/validate.py --tier release --regional \
  --utility delmarva_maryland --period custom \
  --start-date 2025-01-01 --end-date 2025-06-30 \
  --inputs .cache/delmarva_md/weather --output .cache/delmarva_md/new-release
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_delmarva_md.py::test_source_metadata_follows_actual_monthly_original \
  --regional --utility delmarva_maryland --period custom \
  --start-date 2025-09-01 --end-date 2025-09-30 \
  --inputs .cache/delmarva_md/weather --output .cache/delmarva_md/new-september2025
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_delmarva_md.py::test_source_metadata_follows_actual_monthly_original \
  --regional --utility delmarva_maryland --period custom \
  --start-date 2026-05-01 --end-date 2026-09-30 \
  --inputs .cache/delmarva_md/weather --output .cache/delmarva_md/new-2026
```

Fresh candidates/selections require fresh output paths. Resume must match frozen
source and re-audit saved artifacts. Private `coverage_1.md/.csv` selects only
Delmarva evidence and does not supersede retained reports for other utilities.
Next evidence work is missing monthly history, July/August 2025 allocation,
RRC/relief amounts/posting and exact SGS-S state sales-tax billing. No rate or
eligibility is invented to close those gaps.

Final preservation audit confirms the frozen fingerprint, base HEAD and all
staged modes/blob IDs remain unchanged; all Pepco/instruction file hashes match
the captured baseline. Delmarva changes remain unstaged. `preservation_final_1.json`
records these checks and local Markdown links. One private HTTP audit helper emitted
a shutdown-thread warning after all response/hash checks passed; its shutdown order
was corrected, and the original receipt retains that diagnostic. No engine source
change or missing HTTP assertion is hidden by that helper correction.
