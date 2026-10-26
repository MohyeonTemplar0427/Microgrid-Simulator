# PPL Pennsylvania and AEP Ohio validation

Reviewed October 25, 2026. This is a local development candidate on `main`,
with pre-existing Alliant and other changes retained. It is not a stable-engine
promotion, public deployment or certification of a customer's actual account.
The local browser and shared backend are the active interfaces; native desktop
GUI tests and development remain excluded.

## Account and date scope

| Utility | Selected plans | Executable complete calendar cycles |
| --- | --- | --- |
| PPL Electric Utilities, Pennsylvania | RS residential; ordinary single-phase GS-1 commercial; fixed GSC-1 default supply | January 2025–October 2026 |
| Ohio Power Company / AEP Ohio | RS residential; non-demand GS-1, named GS-NDM under filed No.22; SSO | January 2025–March 2026 and May–October 2026 |

AEP's Ohio Power and Columbus Southern legacy rate zones are explicit saved
account facts, independent of PJM's AEP transmission zone. PPL's transmission
designation is PPL. No pricing node is inferred, and wholesale prices never
replace default retail supply. Retail capacity/transmission components are
included once under their actual tariffs, without invented PLC/NSPL adders.

**April 2026 AEP bills are rejected:** April 10 prices are known, but the
allocation of base customer/energy charges across an April calendar cycle is
not verified. No day-weighted allocation, month-end substitution or provisional
permission is added. The complete-cycle limitation also excludes arbitrary
shifted or partial bills for both providers. Actual account eligibility,
tax jurisdiction, supply and approved ordinary non-export interconnection
must be confirmed separately from weather coordinates.

PPL GS-1 includes one 15-minute monthly maximum rounded to whole kW, half up,
with no modeled ratchet. The study domain is below 100 kW. A 0.01 W numerical
guard around half-kW discontinuities is documented in [PPL's scope](PPL_Pennsylvania.md);
inputs in the unsupported numerical band reject. The commercial AEP plan has
no customer demand charge and requires utility-confirmed non-demand membership
and import below 10 kW, including battery charging. These are distinct selected
commercial classes, not general industrial or data-center coverage.

Both plans enforce zero scheduled exports and retain PV curtailment. No export
credit, NEM bank, annual true-up, standalone-storage or unverified standby
agreement is implied. The [PPL](PPL_Pennsylvania.md) and [AEP](AEP_Ohio.md)
notes contain the full filed-price, source-conflict and eligibility boundaries.

## Inputs and physical assumptions

All annual studies use January 1–December 31, 2025, twelve explicitly
hypothetical calendar meter cycles, and the exact `America/New_York` 15-minute
grid. The year has 35,040 intervals, including 92 on March 9 and 100 on
November 2. Grid only, PV only and PV plus battery share the same native load
and available solar within each study.

| Input | Residential, both utilities | PPL commercial GS-1 | AEP commercial GS-1 |
| --- | --- | --- | --- |
| Native demand | Synthetic household, 3 kW reference peak | Synthetic office, 20 kW reference peak | Synthetic small office, 3 kW reference peak |
| PV DC / inverter AC | 5 / 4 kW | 10 / 8 kW | 5 / 4 kW |
| Battery capacity / charge-discharge limit | 10 kWh / 3 kW | 30 kWh / 8 kW | 10 kWh / 3 kW |
| Initial energy / permitted SOC | 50% / 20–80% | 50% / 20–80% | 50% / 20–80% |
| Representative electrical service | 25 kVA, 100 A split-phase 120/240 V | 75 kVA, 400 A single-phase 240 V | 75 kVA, 400 A single-phase 240 V |

The commercial references deliberately satisfy different tariff scopes; their
raw bill totals are not an equal-facility ranking of the two utilities. Native
profiles are deterministic synthetic inputs serialized and re-imported through
the ordinary CSV contract. They are not measured customers or estimates of
average regional consumption.

The annual native totals are 13,887.5364 kWh for both residential references,
79,878.2160 kWh for PPL's office and 11,981.7324 kWh for AEP's small office.

PV is south-facing at 30 degrees, with 14% system losses and 96% inverter
efficiency. Battery charge and discharge efficiencies are each 95%. The shared
AC-coupled model carries SOC between cycles and restores initial energy at the
final boundary. The $0.03/kWh throughput wear estimate is reported separately
and excluded from the bill-minimization objective unless explicitly selected.
Installation costs, incentives and payback are excluded.

Historical ERA5 weather is cached for PPL's hypothetical Lehigh County site
(40.63 N, 75.61 W) and AEP's hypothetical unincorporated Delaware County site
(40.22 N, 83.03 W). These coordinates do not establish service territory or tax
status. Inputs include full-year 2025 and January–September 2026, requested in
UTC with end padding. Previous-hour radiation means are shifted to interval
starts and held over quarter hours; hourly reanalysis is not measured
15-minute site weather. The Open-Meteo/Copernicus attribution, native units,
source timestamps, requests and raw hashes remain with each saved study.

Each accepted scenario receives shared OpenDSS quasi-static replay at every
interval. Replay uses actual scheduled PV output, charging/discharging and
SOC, preserving curtailment and absent equipment. PCC measurements and losses
remain separate from scheduled billing flows. These are representative-network
checks after dispatch, not site-specific, transient or protection validation,
and network limits are not added to the economic optimizer.

Dispatch uses historical perfect foresight within each cycle and continuous
SOC across cycles. Per-cycle solver proofs are retained; no jointly optimized
annual minimum or next-day operating strategy is claimed.

## Independent rate and source checks

The checked-in source ledgers preserve 36 PPL and 26 AEP extracted records,
including retrieval methods, pages, hashes and indexed-only limitations.
Original PDFs/workbooks remain in ignored cache storage. Fresh source checks
verify 35 PPL and 10 AEP original-document references; repeated references may
point to the same original binary. Indexed records are not relabeled as
downloaded originals. No credentials or customer billing data are included.

Eight literal benchmarks independently reproduce every cent-rounded component:

| Period | Utility / plan | Input | Bill |
| --- | --- | --- | ---: |
| July 2025 | PPL RS | 1,000 kWh | $191.49 |
| July 2025 | PPL GS-1 | 1,000 kWh, 3 kW peak | $171.44 |
| June 2026 | PPL RS | 1,000 kWh | $200.88 |
| June 2026 | PPL GS-1 | 1,000 kWh, 3 kW peak | $180.06 |
| April 2025 | AEP RS | 1,000 kWh | $171.22 |
| April 2025 | AEP GS-1 | 1,000 kWh, non-demand | $167.18 |
| October 2026 | AEP RS | 1,000 kWh | $211.51 |
| October 2026 | AEP GS-NDM | 1,000 kWh, non-demand | $206.38 |

These are filed-arithmetic benchmarks and utility-calculator examples, not
calibration against a real customer's statement. Statement component rounding
is kept separate from the unrounded optimization and reconciliation arithmetic.
PPL embedded residential riders, commercial riders, TCJA/DSIC/STAS ordering,
and July 2026 resets are checked without double counting. AEP's February 2025
CSP credit, August 14 LGR/SGF cancellation, and applicable No.22 EDCR versus an
obsolete sheet retained in the utility's October book are explicitly tested.

## Reproduction and evidence

Use `/usr/local/bin/python3 tools/validate.py` with explicit tiers. Weather
preparation is a separate live-data action; tests and matrix execution use
only prepared files under `.cache/ppl_aep_ohio/weather`.

```sh
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_ppl_pa.py --test test/test_aep_ohio.py \
  --test test/test_ppl_aep_integration.py

/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_ppl_aep_integration.py::test_full_year_native_form_roundtrip_preserves_dst_and_cycles \
  --regional --utility ppl_electric_pennsylvania --utility aep_ohio \
  --period annual --inputs .cache/ppl_aep_ohio/weather \
  --output .cache/ppl_aep_ohio/annual-reproduction --matrix-timeout 1800

/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_ppl_aep_integration.py::test_aep_historical_matrix_selects_zone_without_changing_other_utilities \
  --regional --utility aep_ohio --aep-rate-zone columbus_southern \
  --period annual --inputs .cache/ppl_aep_ohio/weather \
  --output .cache/ppl_aep_ohio/csp-annual-reproduction --matrix-timeout 1200
```

Choose a fresh output directory for a different frozen candidate, input,
period or legacy district. Resume requires matching source, validator,
execution selection, request and saved artifact hashes. API/CSV/ZIP and browser
acceptance receipts are separate from pytest and matrix completion.

## Frozen historical results

The accepted matrix candidate is
`b2d8a2d63ebe49271c25f18bc346a33cd8bd1a1d6aff5942f5ec5d15efb5c215`.
Its complete source/frontend/test/tool fingerprint is
`.cache/ppl_aep_ohio/candidate_frozen_2.json`. The preceding
`33cfd27f86dc` candidate passed 354 focused tests before independent review
found that numerical PPL billing accepted exactly the documented 100-kW study
cap. The correction makes numerical billing reject that boundary, matching
the below-100-kW dispatch scope, with three added boundary tests. Earlier
receipts retain their original engine and are not relabeled.

Annual 2025 bills, summing twelve itemized cycles, are:

| Utility / plan / legacy zone | Grid only | PV only | PV plus battery |
| --- | ---: | ---: | ---: |
| PPL RS | $2,530.05 | $1,815.98 | $1,553.92 |
| PPL GS-1 | $11,382.77 | $9,644.45 | $9,460.95 |
| AEP RS / Ohio Power | $2,617.07 | $1,869.38 | $1,598.24 |
| AEP GS-1 / Ohio Power | $2,197.47 | $1,369.98 | $1,265.51 |
| AEP RS / Columbus Southern | $2,616.88 | $1,869.23 | $1,598.11 |
| AEP GS-1 / Columbus Southern | $2,197.47 | $1,369.98 | $1,265.51 |

May 1–September 30, 2026 studies exercise PPL's July base/supply reset and
AEP's new No.22 base and June/July riders with actual 2026 weather. They are
five-month studies, not annual 2026 simulations:

| Utility / plan / legacy zone | Grid only | PV only | PV plus battery |
| --- | ---: | ---: | ---: |
| PPL RS | $1,177.71 | $799.64 | $671.55 |
| PPL GS-1 | $5,292.81 | $4,394.81 | $4,297.19 |
| AEP RS / Ohio Power | $1,235.94 | $827.98 | $688.38 |
| AEP GS-1 / Ohio Power | $1,106.32 | $644.41 | $590.68 |

The ten studies comprise 30 scenarios and 276 independently rebilled monthly
cycles. All 92 battery-cycle primary objectives were proven within their saved
tolerances. Every bill reconciles against the shared expressions within
$0.0000011 before statement rounding. Secondary minimum cycling is proven for
81/92 storage cycles; **eight annual and three 2026 PPL GS-1 cycles remain
unproven for that secondary objective**. Their feasible primary bill-optimal
results remain accepted, without a claim of minimum possible cycling/wear.
No jointly optimized annual optimum is claimed.

All 806,976 representative OpenDSS interval checks converged and passed, with
zero voltage, line-loading, transformer-loading, setpoint or inverter-capability
violations. The aggregate voltage range is approximately 0.99278–0.99995 pu.
These results apply to the declared representative networks and equipment.

Local HTTP verification matched all ten saved requests/result manifests,
130 CSV table payloads and ten ZIP bundles to their saved bytes. Each ZIP's
manifest and table hashes reconcile. This API evidence does not substitute
for the separate visual browser acceptance below.

| Evidence | Receipt under `.cache/ppl_aep_ohio/` | Result / phase wall time |
| --- | --- | --- |
| Unchanged pre-implementation billing/dispatch baseline | `baseline/report.json` | 383 passed; 99.95 s |
| Final focused billing, form/worker, electrical, coverage and validation-tool checks | `focused_2/report.json` | 357 passed; 43.65 s |
| Full regression and JavaScript syntax on frozen candidate 2 | `release_2/report.json` | 4,494 passed, one optional HTTPS skip; 809.97 s pytest phase; all seven JavaScript checks passed |
| Four ordinary full-year 2025 studies | `annual_main_2/report.json` | Passed; 171.18 s matrix phase |
| Both Columbus Southern full-year studies | `annual_csp_2/report.json` | Passed; 86.99 s matrix phase |
| Four May–September 2026 studies | `changes_2026_2/report.json` | Passed; 83.47 s matrix phase |
| Independent source and benchmark review | `review/sourcepack_hash_audit_frozen_2.json`, `review/benchmark_review_receipt_frozen_2.json` | All source hashes/byte counts and eight benchmarks passed |
| Saved HTTP/CSV/ZIP verification | `api_artifact_receipt_2.json` | Ten studies, 130 tables passed; 13.30 s |
| Display-label-only frontend 3 affected checks | `frontend_3/report.json` | Eight passed; 2.62 s; `node --check src/local_web/static/regional.js` also passed |
| Current frontend 3 HTTP/CSV/ZIP verification | `api_artifact_receipt_3.json` | Ten studies, 130 tables passed; 12.62 s |
| Combined numerical/electrical/proof counts | `matrix_summary_2.json` | Source-pinned aggregate of the three matrices |
| Generated private coverage view | `coverage_2.md`, `coverage_2.csv` | New ordinary plans and distinct date windows retained; earlier evidence keeps its own pins |

Each matrix folder's `regional/` directory retains `validation.json`,
`study-comparison.csv`, `monthly-comparison.csv`, `period-components.csv` and
source-hashed per-study artifacts. Matrix launcher pytest selections repeat
some focused tests and must not be added to the focused count. The jobs ran
concurrently, so phase times are overlapping wall measurements and are not
additive development or CPU time. No live provider requests occurred during
tests or matrix execution. Existing saved stores and the stable engine were
not upgraded.

The release run excludes the three paused desktop GUI test modules. Its single
skip is the optional real-HTTPS test because a Caddy configuration was not
provided. The release count is 4,494 passing tests plus one skipped test,
not 4,495 passing tests. The preceding baseline/focused/matrix counts overlap
the release run and are not additional unique passing tests.

## Final frontend and bounded browser acceptance

After the full regression completed, the PPL `default_ptc` account value gained
the readable display label "Default supply · fixed Price to Compare (GSC-1)".
This changes only `src/local_web/static/regional.js`; the billing engine,
other source, tests, tools and configuration match candidate 2 exactly.
The current fingerprint is `.cache/ppl_aep_ohio/candidate_frozen_3.json`, with
`regional.js` SHA-256
`91bedbc21289b7d3e60a413564ba5f8ef951128e157f3d100dfe7f1f615f2018`.
Eight affected account/form/DST round-trip checks and a new static syntax check
passed, followed by fresh HTTP verification of all ten studies and their
current frontend, saved CSVs and ZIPs. Earlier release and matrix receipts
retain candidate 2's frontend identity; they are not relabeled as frontend 3
browser evidence. The backend engine remains `b2d8a2d63ebe`.

An isolated loopback preview uses `.cache/ppl_aep_ohio/browser_preview_2`.
Its independently audited seed studies are PPL GS-1 for July 2026 and AEP RS
in the Columbus Southern district for February 2025. The latter explicitly
exercises that district's credit. Both seeds passed the ordinary queued worker,
itemized rebilling and three-scenario electrical checks; seed generation is
API/artifact evidence, not a browser submission.

The single visual acceptance pass verified PPL's provider, account/source/date
controls, explicit confirmations, restored weather and native CSV, PV/inverter
and battery inputs, excluded-wear objective, review and actual submission.
The resulting study `3d0e936572b745af9a617470e34d6a6d` completed in 5.17 s.
The browser displayed all three scenarios, their verified itemized-bill status,
and passing representative electrical indicators. It then saved successfully
as "PPL GS-1 · validated July 2026", with the name shown in the results and
recent-study entry. Its July bills are $1,100.80 grid only, $907.85 PV only and
$887.32 PV plus battery.

**Visual acceptance is partial.** The next automation operation, selecting the
electrical-summary table by its accessible label, reported no matching element
and exceeded its deadline (3.07 s tool wall time). In accordance with
`AGENTS.md`, that route was stopped without retrying, increasing its timeout or
using download/file-chooser waits. The electrical-summary selector, reopening
the saved result from history, and AEP's visual configuration/submission/save/
reopen remain unverified. This does not establish a product selector defect;
it identifies the exact assertion the automation could not verify.

Post-pass API checks confirm the PPL result is saved without expiry, the
downloaded settings use its chosen name, every other request field round-trips
unchanged, all 13 CSVs match disk bytes, and all three scenarios pass rebilling,
physical balance, SOC and representative OpenDSS checks. Its 8,928 interval
checks are additional browser-case evidence, excluded from the 806,976 matrix
count. The original submitted settings remain immutable while the download
overlays the saved display name, as the existing save contract specifies.

The receipt is `.cache/ppl_aep_ohio/browser_acceptance_receipt_3.json`, and the
captured result is `.cache/ppl_aep_ohio/browser_acceptance_3.png`. Browser-pass
wall time was 151.99 s, including observations and work between calls; it is
not active-development time or cumulative browser-tool waiting. The recorded
failed selector call was 3.07 s, and the actual PPL worker runtime was 5.17 s.

No stable engine promotion, staging, commit, push, public deployment or GUI
launch was performed. Existing Alliant, population-analysis and other work was
preserved, and the README was not edited.
