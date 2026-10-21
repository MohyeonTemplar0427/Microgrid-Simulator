# Ameren Illinois integration handoff · October 20, 2026

Main started clean at `b6f32dd` (Consumers Energy commit). No stage, commit,
push, deploy, stable-engine promotion, origin changes or browser-clone copies.
README is untouched; native GUI development and tests remain paused.

## Implemented boundary

- `src/billing/ameren_il.py` / `ameren_il_rates.py`: ordinary DS-1/BGS-1 and
  **standard secondary** DS-2/BGS-2. Official monthly supply evidence spans
  January 2025–October 2026; dated delivery, transmission, supplemental fees,
  percentage adjustments, mandatory riders and ordinary state excise included.
- Three utility-assigned retail Rate Zones I/II/III; confirmed **non-interval
  retail TS** billing only. A 15-minute native input is not proof of an
  interval-billed utility account. Interval TS needs company-system-peak billing
  determinants and remains unsupported.
- Complete calendar billing months only. Cross-month/partial/initial/final
  proration, PSP/RTP, ARES, optional DS-2 demand rates, local/municipal additions,
  tax exemptions/special service and standalone storage are rejected.
- Non-export approved renewable PV/storage, no rebates, zero opening credits
  and no credit ledger. Aggregate PV nameplate plus storage discharge is
  conservatively bounded to 50 kW in this implementation. The CGC fee applies
  to all accounts and is retained in the absent-DER grid-only reference.
- Standard DS-2 has **seasonal energy blocks, no measured demand fee or
  intraday TOU price**. BGS capacity is bundled; non-interval Rider TS is added
  once separately. MISO LMP/PLC costs are not substituted or added.
- `regional.py`: Illinois/MISO/LRZ4/Ameren Illinois transmission owner, retail
  supplier and optional verified wholesale cpnode remain distinct metadata.
  Address/nearest-node/state inference cannot establish territory or eligibility.
- Shared regional study, browser and historical driver now select a per-utility
  timezone. Ameren uses America/Chicago; previous utilities retain Eastern time.
  Existing solar, ESS, exact bill expressions, worker isolation, saved artifacts,
  save naming and shared representative OpenDSS replay are reused.

See [scope and rates](Ameren_Illinois.md), the
[official-source manifest](utility_sources/ameren_il/manifest.json) and
[visually reviewed appendix transcription](utility_sources/ameren_il/reviewed-tables.md).
Full research PDFs remain ignored. Runtime tables are Python literals included
in immutable snapshots, not paths into research cache.

## Candidate and completed simulation evidence

Backend engine:
`ea4a8f130f39b47b995b4707508d506845fc27a46a6af55568796279efa92d5e`.
Web UI v1.0.1 retained. Isolated preview data lives in
`.cache/ameren_il_browser`, localhost port 19049, using `/dev/null` instead
of loading a credential file. Existing Consumers preview/store was preserved.

Baseline evidence was reused only after confirming all pre-edit fingerprints
matched `.cache/consumers_release_final/report.json`: 3,195 passed, 1 skipped,
seven JS checks. This was not a newly rerun baseline claim.

An initial focused run had 73 passes and one solver-time-limit failure in the
residential winter dispatch case (58.22 s pytest). Exact filled-block algebra
was simplified locally to share repeated thresholds and prune thresholds outside
proven aggregate-energy bounds. Billing arithmetic was unchanged. The next
focused run passed all 74 tests in 18.31 s (18.66 s launcher); a further twelve
tax and fixed-schedule MILP parity cases are included in the final regression.
Earlier fingerprints/results are retained in `.cache/ameren_focus_1/` and
`.cache/ameren_focus_2/`, not relabeled as final-source evidence.

Matrices: `.cache/ameren_il_validation_2025/validation-summary.json` and
`.cache/ameren_il_validation_2026/validation-summary.json`. Four studies, twelve
scenarios, 126 cycle bills and 367,464 electrical intervals passed independent
artifact/bill/dispatch audits; zero failed electrical intervals. All cost optima
were proven or direct bills; **42/42 battery-cycle minimum-cycling results
proven**. Maximum bill/objective difference approximately $0.000001. No joint
annual optimum or actual-customer bill calibration is claimed.

| Plan | Period | Grid only | PV only | PV + battery |
|---|---|---:|---:|---:|
| DS-1 | 2025 | $2,422.26 | $1,731.08 | $1,449.88 |
| DS-2 standard | 2025 | $16,692.05 | $14,240.95 | $14,237.96 |
| DS-1 | Jan–Sep 2026 | $1,933.62 | $1,352.90 | $1,123.78 |
| DS-2 standard | Jan–Sep 2026 | $13,330.91 | $11,327.66 | $11,325.59 |

Profiles are synthetic generic household/office shapes, imported through exact
native interval CSVs. Actual ERA5 historical reanalysis is site/year matched at
39.75, -89.70. Residential 2025 native energy is 13,887.54 kWh; commercial is
99,847.77 kWh. Residential PV 5 kW DC / 4 kW AC, battery 10 kWh / 3 kW;
commercial PV 10 kW DC / 8 kW AC, battery 30 kWh / 8 kW. Both: south-facing
30° PV, 14% system loss, 96% PV inverter efficiency, 95% battery charge and
discharge efficiency, 20–80% SOC range, initial/final 50% SOC. Wear is excluded
from the objective and reported separately. No exports, MISO carbon or capital
costs. Ordinary BGS/non-interval TS/locality exclusions are hypothetical facts,
not confirmed real accounts.

Electrical replay uses existing representative 25-kVA/100-A split-phase
residential and balanced 480-V/750-kVA commercial networks. These are not
surveyed sites or Ameren service standards. Every 15-minute actual scheduled
PV/battery interval is replayed. PCC losses/measurements remain separate from
billing; no network constraints, protection or transient validation is added.

Workers reported 44.91 s and 35.88 s for the two 2025 studies; 33.45 s and
27.28 s for the 2026 studies. The matrices overlapped each other and the full
regression; their sum is not total elapsed development time.

## Reproduce without silently retrieving new inputs

```sh
/usr/local/bin/python3 tools/validate.py --tier focused --test test/test_ameren_il.py --timeout 240
/usr/local/bin/python3 tools/run_regional_validation.py --execute --utility ameren_illinois --period annual --inputs .cache/ameren_il_historical_inputs --output .cache/ameren_repeat_2025 --env-file /dev/null
/usr/local/bin/python3 tools/run_regional_validation.py --execute --utility ameren_illinois --period custom --start-date 2026-01-01 --end-date 2026-09-30 --inputs .cache/ameren_il_historical_inputs_2026 --output .cache/ameren_repeat_2026 --env-file /dev/null
```

Use new output folders after changes; `--resume` is only for identical frozen
inputs/source/validator evidence. Historical load assumptions and original
weather bytes/hashes remain in ignored private artifacts. Do not relabel their
engine pins, export private data into docs or promote the candidate implicitly.

## Final regression and browser acceptance

- Full release: **3,281 passed, 1 skipped**, all seven JavaScript checks passed.
  Pytest 565.24 s; launcher pytest phase 565.88 s, complete launcher 566.99 s.
  `.cache/ameren_release_final/report.json` retains the original full fingerprints.
  GUI modules excluded. The skip is opt-in Caddy HTTPS. Twelve existing DTE
  HiGHS option-forwarding warnings and one NumPy reduction warning in an unchanged
  SCE test were reported; no Ameren warning or failed test.
- A duplicated word in the frontend's unsupported-date error was corrected
  after that run. **Backend, tests and tooling hashes and engine ID did not
  change.** The final frontend was frozen separately; `node --check` passed,
  and the final targeted run passed **106 tests without warnings** in 44.31 s
  (44.59 s launcher): Ameren, shared regional form/worker tests and the isolated
  SCE warning case. The SCE warning did not reproduce. Do not relabel the full
  report's older frontend fingerprint as the corrected one.
- Final `regional.js` SHA-256:
  `3c2a706a56157ab5904e551a440962241a1e624e9863f9f33e1d21b8ee6d42d2`.
  Final full fingerprint set: `.cache/ameren_final_candidate.json`; matching
  targeted report: `.cache/ameren_final_frontend_checks/report.json`.
- One browser acceptance pass on that final backend/frontend pair confirmed
  Ameren/Illinois/MISO/LRZ4 identity, DS-1/BGS-1, source links and supported dates,
  Rate Zone II/non-interval TS account facts, restored exact dates/native CSV,
  PV, inverter, ERA5 and battery settings, submission, three rendered bills,
  name-on-save, saved-history reopen and all three electrical table rows.
  Each electrical row evaluated/converged all 2,976 intervals; all passed.
  API readback showed the browser-submitted request **exactly matched the seed**
  before naming and produced identical itemized bills. ZIP bytes had 14 expected
  entries; downloads were verified through APIs, without browser download events.
- Browser comparison: **$266.39 / $170.59 / $136.85** for grid-only, PV-only and
  PV-plus-battery in July 2026. Named saved result:
  [Ameren Illinois DS-1 · July 2026 validation](http://127.0.0.1:19049/#3a9703d2a96c4f3b91e631dca5c34647).
  Receipt `.cache/ameren_il_browser_acceptance.json`; screenshot
  `.cache/ameren-il-browser-results.png`; electrical AX readback
  `.cache/ameren-il-browser-electrical-ax.txt`.
- Browser stalls: **0**. Browser-tool calls totaled approximately **11.37 s**;
  this excludes the time between calls spent on API/artifact checks and reporting,
  and is not a claim about active development time.
- Final source/frontend/tests/tool hashes matched the final focused report;
  the full release backend/tests/tool hashes still match. Git whitespace checks
  passed, nothing staged, README unchanged. No commit/push/deploy/promotion.
