# Ameren Missouri integration handoff · October 21, 2026

Started on clean main at `c33bbf1` (Ameren Illinois commit). No stage, commit,
push, deploy, stable-engine promotion, origin change, clone copy or GUI launch.
README remains untouched. Local browser/shared backend are the active scope.

## Boundary and architecture

See [supported accounts and source rules](Ameren_Missouri.md) and
[23 retained official-source records](utility_sources/ameren_mo/manifest.json).
The source review includes the actual June 2025 FAC filing (not its blank
replacement template), RESRAM rebasing, EEIC totals, nine actual Smart holidays,
ordinary bundled 1(M)/2(M), non-export/standby exclusions and dated ColeCounty taxes.
Runtime rates are Python literals in immutable snapshots.

Six residential choices: Anytime, EMS, SmartA/B and OvernightA/B; standard 2(M)
commercial. Verified service window January 2025–October 21, 2026; complete calendar
meter cycles only, latest complete month September 2026. No proration or invented
future weather/rates. Tax-inclusive first scope is explicitly confirmed
unincorporated Cole County 00000-051-000, domestic 0%, commercial 5.6%. No additional
local/special charges, NEM/export/standby, Ultimate demand, legacyTOD, commercial
optional rates, missing-history refunds or standalone storage.

Utility, Missouri jurisdiction, bundled supplier, America/Chicago, MISO LRZ5,
transmission ownership and optional verified wholesale cpnode stay separate.
Scheduled retail flows remain the bill basis; OpenDSS PCC/losses are diagnostics.
Commercial May/October/summer billed-import history evolves per scenario; it is
not native load and is not reset in the absent-DER reference. The same numeric
and symbolic block/TOU/rider/tax expressions calculate bills and cost objectives.
Rolling-cycle historical perfect foresight is not a joint annual optimum.

## Validation development history

Pre-edit fingerprints exactly matched `.cache/ameren_final_frontend_checks/report.json`;
prior baseline was 3,281 passed / 1 skipped, with 106 final focused checks. No newly rerun
baseline is claimed.

First focus `.cache/ameren_mo_focus_1`: 209 passed / 7 failed. Failures were fixtures:
old Illinois test assumed all other utilities were Eastern; January 2026 Smart
benchmark overcounted eligible hours; symbolic-parity fixture passed a NumPy
export constant as a constraint instead of a CVXPY constant. Corrected focus
`.cache/ameren_mo_focus_2`: 285 passed in 43.07 s (launcher 43.40 s).

Initial engine `d8b963a0fc6922e015af09f795a20c09b1dc897a46e7713cec019fb4f52a4875`
completed all six residential annual 2025 cases and all seven Jan–Sep 2026 cases.
Annual commercial 2(M) correctly exposed a new model defect at November: the
preceding-summer date checker expected prior-year September after October.
Those results remain attributed to that original pin in
`.cache/ameren_mo_validation_2025/` and `.cache/ameren_mo_validation_2026/`.
The first broad regression was interrupted cleanly after 326.24 s to repair and
re-freeze; it is not a passing full-regression result.

The repair introduces one shared preceding-summer helper, reused by the
validation driver. Explicit January/June/July/October/November/December fixtures
and October→January consecutive-state regression prevent recurrence. Two
independent commercial 1,000-kWh floor benchmarks were added as well.

Corrected engine:
`d3e9c7bb032eb6721fd027d52e72e1104669e7e313be76f24344b5ef613a0d2f`.
Final fingerprint file `.cache/ameren_mo_candidate.json`; old pin separately in
`.cache/ameren_mo_candidate_initial.json`. Final validation uses fresh folders,
not resume across changed source or relabeling old receipts.

## Reproduction

```sh
/usr/local/bin/python3 tools/validate.py --tier focused --test test/test_ameren_mo.py --test test/test_ameren_il.py --test test/test_regional_validation_driver.py --test test/test_regional_coverage.py --timeout 240
/usr/local/bin/python3 tools/run_regional_validation.py --execute --utility ameren_missouri --period annual --inputs .cache/ameren_mo_historical_inputs --output .cache/ameren_mo_repeat_2025 --env-file /dev/null
/usr/local/bin/python3 tools/run_regional_validation.py --execute --utility ameren_missouri --period custom --start-date 2026-01-01 --end-date 2026-09-30 --inputs .cache/ameren_mo_historical_inputs_2026 --output .cache/ameren_mo_repeat_2026 --env-file /dev/null
```

Original weather
bytes are prepared separately for each actual year/site. New source/input/driver
requires a fresh evidence folder. No raw private data or credentials are in docs.

Final results and acceptance receipts are recorded below.

## Completed historical comparisons

### Full-year 2025

| Plan | Grid only | PV only | PV + battery |
|---|---:|---:|---:|
| 1M | $1,757.86 | $1,277.63 | $1,080.12 |
| 1M-EMS | $1,756.60 | $1,270.67 | $1,070.62 |
| 1M-SMART-A | $1,785.68 | $1,223.95 | $756.66 |
| 1M-SMART-B | $1,757.51 | $1,221.48 | $933.38 |
| 1M-OVERNIGHT-A | $1,758.31 | $1,150.69 | $842.19 |
| 1M-OVERNIGHT-B | $1,761.57 | $1,234.12 | $970.30 |
| 2M | $11,900.45 | $10,340.21 | $10,338.85 |

### January–September 2026

| Plan | Grid only | PV only | PV + battery |
|---|---:|---:|---:|
| 1M | $1,469.95 | $1,029.81 | $847.29 |
| 1M-EMS | $1,468.43 | $1,023.49 | $838.83 |
| 1M-SMART-A | $1,493.30 | $977.05 | $586.99 |
| 1M-SMART-B | $1,474.77 | $977.74 | $698.73 |
| 1M-OVERNIGHT-A | $1,470.56 | $924.46 | $652.11 |
| 1M-OVERNIGHT-B | $1,473.88 | $986.77 | $737.54 |
| 2M | $9,729.17 | $8,411.68 | $8,411.14 |

These are synthetic facility comparisons under the confirmed hypothetical account
facts, not calibrated customer bills. All use actual site/year-matched ERA5,
south-facing PV at 30° tilt, 14% system losses and 96% inverter efficiency.
Residential: 3 kW generic peak, 5 kW DC / 4 kW AC PV, 10 kWh / 3 kW storage.
Commercial: 25 kW generic peak, 10 kW DC / 8 kW AC PV, 30 kWh / 8 kW storage.
Battery charge/discharge efficiency is 95% each, with 20–80% SOC and initial/final
50%; SOC continues across cycles. Wear is excluded from the default bill
objective and reported separately.

All 14 studies / 42 scenarios passed independent audits: 441 cycle bills and
1,286,124 electrical intervals, zero electrical failures; maximum unrounded
objective/bill difference $0.00000100. Every primary cycle cost optimum was
proven or a direct bill. Minimum cycling was proven for 142/147 battery cycles;
five retained the verified primary cost-optimal schedule with an explicit
warning (2025 EMS April, Overnight A February, Overnight B January; 2026 EMS
March, Smart B April). This secondary refinement limitation does not invalidate
the primary cost proof.

Representative electrical circuits: 25 kVA / 100 A 120/240 V split-phase
residential and balanced 480 V / 750 kVA commercial, 0.95 lagging physical load
PF. These are not surveyed networks or Ameren service standards. No protection,
transient or network-constrained optimization claim.

Evidence: `.cache/ameren_mo_validation_2025_final/validation-summary.json` and `.cache/ameren_mo_validation_2026_final/validation-summary.json`, engine `d3e9c7bb032eb6721fd027d52e72e1104669e7e313be76f24344b5ef613a0d2f`. Original failed-candidate artifacts retain their own pin.

## Regression clock fixture correction

The corrected-engine broad run encountered the existing
`test_oidc_rejects_invalid_signed_claims[changes6]` fixture: it evaluated
`time.time()+1000` at test collection, allowing the supposed future-issued claim
to become a valid past claim after a sufficiently long or suspended run. The
seven isolated parameter cases passed, establishing its time-dependent behavior.
The fixture now computes that timestamp at test execution. Production
`src/local_web/auth.py`, hosting behavior and credentials are unchanged. The
intermediate report `.cache/ameren_mo_release_corrected/` was stopped and marked
invalidated after 827.66 s; it is not passing evidence. Final full regression uses
`.cache/ameren_mo_release_verified/`. Final test hashes were recorded separately;
the engine, frontend and completed historical matrices keep the same final pin.


## Final regression and browser acceptance

The release-tier run `.cache/ameren_mo_release_verified/report.json` passed:
**3,421 passed, 1 skipped, 13 warnings**, pytest 814.98 s, phase 816.08 s,
launcher session 817.36 s. Seven JavaScript syntax checks also passed. The skip
is the opt-in Caddy HTTPS check. Three desktop GUI modules were excluded per
repository policy. Twelve warnings concern existing DTE/HiGHS option forwarding;
one is an existing PECO GS-TOU solver accuracy warning. These are distinct from
the five historical Ameren secondary-cycling proof warnings noted above.

Final focused run `.cache/ameren_mo_focus_final/report.json`: 295 passed,
pytest 42.30 s, phase 42.66 s. All final source/frontend/test/tool fingerprints
match the release report and `.cache/ameren_mo_candidate.json`.

One concise browser acceptance pass on the frozen candidate verified:

- Restored location, account, all six residential plan choices, dates, equipment,
  ERA5 source, native-load provenance, bill objective and representative circuit.
- Submitted restored settings without re-fetching weather or automating file
  choosers. The browser-to-worker result is
  `56b0e56ceb6b4cad9324181a7453535d`, runtime 10.05 s, engine `d3e9c7bb032e`.
- July 2026 Smart Saver A bills: $212.97 grid only, $121.78 PV only, $71.07 PV plus
  battery. Each scenario checked and converged at all 2,976 intervals, with no
  voltage/line/transformer failures.
- Named and saved the completed result as “Ameren Missouri Smart Saver · July
  2026 verified”, then reopened it from recent studies. The API readback confirms
  persistence, exact restored settings apart from the name, unchanged itemized
  bills and the final engine pin.
- Fourteen ZIP entries validated; corresponding direct CSV bytes match the ZIP
  bytes, without browser download-event waits. Receipt:
  `.cache/ameren_mo_browser_acceptance.json`. Rendered evidence:
  `.cache/ameren-mo-browser-electrical-ax.txt` and
  `.cache/ameren-mo-browser-results.png`.

Preview: `http://127.0.0.1:19050/#56b0e56ceb6b4cad9324181a7453535d`.
Web UI remains v1.0.1; this is an unpromoted development snapshot. No browser
operation stalled or timed out. Test and worker runtimes are execution timings,
not active development time; background work overlapped and wall clocks advanced
during long/suspended periods. Original candidate evidence was not relabeled.

Final Git review: main remains at c33bbf1, all task changes are unstaged,
README unchanged, no merge conflicts, `git diff --check` clean. No commit, push,
deployment, native GUI launch or change to either clone's origin was performed.
