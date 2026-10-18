# FirstEnergy candidate validation — October17,2026

Candidate engine `cfb6cb1f3897485736c62540942f5b34bcb8b89ad887d58a6c5ae4c404a1aae5`.

Stable engine remains unchanged. These are hypothetical ordinary-service, zero-export studies with imported synthetic native loads and explicitly selected actual2025 ERA5 reanalysis. They are not customer-bill calibration, real-time forecasts or an annual optimal-control proof.

| Utility / class | Period | Grid only | PV only | PV + battery | Intervals per scenario |
|---|---|---:|---:|---:|---:|
| West Penn / residential | 2025-01-01 → 2025-12-31 | $2,310.62 | $1,647.72 | $1,416.35 | 35,040 |
| West Penn / commercial | 2025-01-01 → 2025-12-31 | $10,906.39 | $9,285.93 | $9,162.88 | 35,040 |
| Ohio Edison / residential | 2025-09-01 → 2025-12-31 | $794.99 | $588.75 | $509.95 | 11,716 |
| Ohio Edison / commercial | 2025-09-01 → 2025-12-31 | $3,927.43 | $3,492.21 | $3,319.63 | 11,716 |

All12 scenarios passed representative OpenDSS QSTS with zero failed intervals;280,536 interval replays in total. Complete measurements and feasibility remain separate from scheduled meter billing. Every cycle was rebilled from its saved schedule and checked against itemized amounts, evolving demand/refund state and dispatch objectives. CSV/ZIP endpoint checks are recorded separately.

**Ohio full-year2025 remains blocked.** Earlier2025 component versions, including the intermediate LGR sheet and ESP transition composite, are not yet fully verified. The executable Ohio window is September–December; no earlier rate was inferred and these four-month totals must not be called annual totals.

Residential: generic3kW-peak household,5kWDC PV /4kWAC inverter,10kWh battery with3kW limits. Commercial: generic20kW-peak office,10kWDC /8kWAC,30kWh battery with8kW limits. Both use tilt30°, azimuth180°,14% modeled system losses and96% inverter efficiency. Starting battery energy is5kWh residential /15kWh commercial. Full ESS limits, efficiencies, timestamped inputs and account assumptions are retained in each request. Battery wear is excluded from the utility-bill objective.

West Penn annual native energy:13,887.536kWh residential /79,878.216kWh commercial. Ohio four-month native energy:4,640.923kWh residential /26,827.400kWh commercial. Seasonal/weather calibration of native loads was not claimed.

Private reproducible evidence (ignored local paths):

- `.cache/firstenergy_pa_2025_final/validation.json` and `validation-summary.json` — two annual cases.
- `.cache/firstenergy_oh_2025_final/validation.json` and `validation-summary.json` — two four-month cases.
- `.cache/firstenergy_weather_2025/weather-input-manifest.json` — exact weather hashes and retrieval provenance.
- `.cache/firstenergy_candidate_evidence/` — candidate/front-end fingerprints, case summary and HTTP artifact checks.
- `.cache/firstenergy_release_final/report.json` — final non-GUI regression outcome and phase runtimes. Check its final status rather than assuming a running report is a pass.

[Scope, sources and tariff assumptions](FirstEnergy.md). Earlier development-probe studies retain their original engine IDs and are not relabeled as this candidate.


Final non-GUI release verification: **2,811 passed,1 skipped** in388.11s pytest runtime; all seven JavaScript syntax checks passed. The skip is the separately configured real Caddy TLS test; the three paused native-GUI modules were excluded. The final source fingerprint remained unchanged.

Browser acceptance on the same frozen candidate verified West Penn configuration, restored annual ERA5/native-load inputs, actual submission, identical rerun bills, post-result naming and saved reopening by direct URL. Ohio commercial configuration, coverage limits and rendered results were inspected. One history-button action encountered a transient stale-element error and was not retried; history-button reopening itself remains unconfirmed. Direct-link reopening and API persistence passed. No browser timeout or download/filechooser event wait was used. Evidence is `.cache/firstenergy_candidate_evidence/browser-acceptance.json`; rerun31.98s.


## Ohio historical recovery follow-up — October17,2026

New frozen candidate: `5311ba6b83be2f6a9024b1b2d829bc4805b2bb9e895e6f0462100e25160be6b2`.
Earlier results above retain their original candidate. Complete executable Ohio
coverage now includes January and June, alongside September–December. Full-year
2025 remains unverified and explicitly rejected; the annual rejection is not an
annual simulation pass.

| Cycle / class | Grid only | PV only | PV + battery | Intervals per scenario |
|---|---:|---:|---:|---:|
| January / residential RS | $192.61 | $150.75 | $136.62 | 2,976 |
| January / commercial GS | $905.03 | $826.30 | $800.94 | 2,976 |
| June / residential RS | $201.86 | $128.88 | $105.87 | 2,880 |
| June / commercial GS | $998.39 | $849.94 | $788.32 | 2,880 |

All12 returned scenarios passed their independent schedule-to-bill, SOC/energy
balance and OpenDSS checks:35,136 QSTS intervals, no failed or infeasible
intervals. The equipment, generic synthetic household/office inputs, actual2025
ERA5 provenance and representative circuits match the assumptions above. These
are independent single-cycle studies, not a linked or annual optimization.

January's ESP-V DCR percentage includes base customer/distribution charges and
excludes riders. June's ESP-IV DCR prices kWh or30-minute billing demand. Both
include then-applicable LGR/SGF charges; January also includes VMC, while June
includes restored DSE and summer GEN. Independent Decimal benchmarks exercise
RS and GS for both months. Missing-version rejection and catalog metadata keep
the unsupported periods visible.

Evidence: `.cache/ohio_gapfill_january/`, `.cache/ohio_gapfill_june/`,
`.cache/ohio_gapfill_annual_blocked/`, and `.cache/ohio_gapfill_evidence/`.
The four monthly studies completed and were audited. Both annual RS/GS requests
rejected during preparation, before a study was queued. Matrix wall time:
January14.94s; June15.49s; annual rejection4.52s. These aggregate timings do not
separate solver from OpenDSS runtime.

Focused offline/API/worker verification:44 passed in34.85s. Broad regression
and browser acceptance are recorded below only after completion.

Broad non-GUI release: **2,823 passed,1 skipped** in396.05s pytest runtime;
launcher phase396.64s and session397.73s. All seven JavaScript syntax checks
passed. The skip is the separately configured real Caddy TLS test; three paused
native-GUI modules remain excluded. Engine and frontend fingerprints stayed
unchanged. Report: `.cache/ohio_gapfill_release/report.json`.

HTTP JSON, comparison/dispatch/electrical CSV and ZIP bytes match June worker
artifacts for both classes. Browser acceptance verified June GS bills/feasibility,
new coverage/limitations and restored settings through Economics. Automation
requested `Next` at Economics, where the actual control is `Review study`; its
3000ms selector deadline was reached and the failing operation was not retried.
Browser submission, saving a new rerun and reopening that rerun remain unverified
in this pass. API form-to-worker/save/restore checks passed independently; they
are not substituted for those browser assertions. No application simulation
failure or long browser stall was observed. See
`.cache/ohio_gapfill_evidence/browser-acceptance.json`.

## August14 coverage follow-up — October17,2026

Frozen candidate: `883942c3eb27b3da325df2072977786a4777556585198f8c3da1bbcf55d8cbbb`.
Only `src/billing/firstenergy_oh.py` differs in engine Python from the preceding
candidate. Stable was not promoted and the frontend fingerprints are unchanged.
Earlier evidence remains attributed to its original engine.

The recovered court exhibits do not contain the missing GEN18 or LGR12 rate
sheets. February–May and July1–August13 remain rejected. The already verified
August25 official-book capture does establish a complete component intersection
from August14, after LGR/SGF become zero. Complete cycles beginning on/after
August14 are now executable; the full August calendar month and cycles crossing
the LGR removal are still rejected. No fixed-charge proration was inferred.

The following results cover **one hypothetical31-day cycle, August14–September13,
2025**, not a year. Both cases use the same generic annual synthetic native-load
profiles and cached actual2025 ERA5 weather used in the preceding validation,
sliced to the declared dates. Equipment and representative circuit assumptions
remain as documented above. There are18 summer service days and13 winter days;
the September bill date selects DCR54 for the complete cycle.

| Class | Grid only | PV only | PV + battery | Intervals per scenario |
|---|---:|---:|---:|---:|
| Residential RS | $203.41 | $129.72 | $103.24 | 2,976 |
| Commercial GS | $982.12 | $815.74 | $768.70 | 2,976 |

All six scenarios passed schedule-to-bill, SOC/energy balance and representative
OpenDSS audits:17,856 intervals, no failed or infeasible intervals. Worker
runtimes were15.35s residential and16.08s commercial. Annual RS/GS preparation
was attempted separately and rejected before queueing, at the missing February
composite. Those rejections are not annual simulation passes.

Focused tests via `/usr/local/bin/python3 tools/validate.py`: **68 passed** in
72.93s pytest runtime,73.30s launcher phase. They include independent Decimal
RS/GS tariff arithmetic across September1, the August13/14 coverage boundary,
rejection of unverified earlier August days, and browser-form serialization to
HTTP/worker/save/restore for both new complete-cycle cases. Regional-study
regressions are included; native-GUI tests remain excluded. This is a focused
run, not a new full-suite release claim. `node --check` for `regional.js`,
`git diff --check` and all23 unchanged source-excerpt hash checks passed.

One browser acceptance pass on the same frozen candidate verified the updated
coverage, account restrictions, exact non-calendar cycle restoration, cached
weather/equipment review, submission, identical commercial bills and electrical
success, naming on save, and reopening from history. Residential results also
rendered correctly. The browser commercial rerun took5.97s and its three saved
schedules were independently rebilled and electrically audited. No browser
operation stalled. API checks verified JSON settings and exact comparison,
dispatch, electrical CSV and ZIP bytes against both original worker artifacts.

Evidence: `.cache/ohio_august14_focused/report.json`,
`.cache/ohio_august14_cases/`, and `.cache/ohio_august14_evidence/`.
The private `run_cases.py` reproduces the explicit cycle and re-audits matching
saved requests without rerunning them. An initial summary-write attempt rejected
NaN fields from the audit DataFrame; the report was repaired to serialize those
missing fields as JSON null, then finalized by re-auditing the original saved
runs. No simulation or billing result was changed by that report repair.

To finish full-year validation, obtain the approved February1 compliance
composite (including GEN Sheet114 revision18) and subsequent applicable revisions
from PUCO14-1297-EL-SSO and related rider cases; LGR Sheet135 revision12 with its
actual effective date/rates from24-1062-EL-RDR; and the August6 compliance order
or another filed fixed-charge allocation rule for the August14 transition.

## Provisional full-year Ohio Edison — October17,2026

Frozen candidate: `a57dd94ef0f4c6f8229a82ca6b619624c874f1e8a3a973fef160dd6c5c355052`. Earlier evidence above retains its original pin. No stable promotion or deployment.

Full calendar2025 is now executable only through explicitly accepted **provisional** mode. Six calendar months (February–May and July–August) contain unverified rate or allocation assumptions. Verified-only coverage remains January, June and August14–December31. See [the complete assumption ledger](Ohio_Edison_Provisional_2025.md).

| Class | Grid only | PV only | PV + battery | Savings vs grid (PV + battery) |
|---|---:|---:|---:|---:|
| Residential | $2,335.48 | $1,640.19 | $1,393.90 | $941.58 |
| Commercial | $11,417.32 | $9,927.12 | $9,407.53 | $2,009.79 |

All amounts are provisional historical modeled bills; these are not reconciliations against real customer bills. Native energy is13,887.5364kWh residential /79,878.216kWh commercial. PV available AC energy is6,872.5095 /13,745.0190kWh. Equipment matches the previously documented residential3kW-peak household /commercial20kW-peak office assumptions. Weather is the exact cached2025 ERA5 payload at the declared Ohio site; loads remain generic synthetic profiles, not measured or regionally calibrated.

Each of the six annual scenarios includes35,04015-minute intervals. All210,240 representative OpenDSS replays passed with complete measurements and no failed intervals. All72 monthly bills were independently rebuilt from the saved schedules and itemized amounts. Primary optima were proven or evaluated directly for all cycles; all24 storage-cycle minimum-cycling refinements were proven. Maximum saved bill/objective reconciliation difference was less than$0.000002. SOC is continuous across cycles and returns to starting energy only at year end. No jointly optimized annual optimum is claimed.

Annual matrix wall time77.53s, including input preparation and artifact audits. Worker-reported times33.99s residential /38.11s commercial include solver and OpenDSS work; they are not separate solver timings. No browser automation was used for this annual matrix.

Private reproducible evidence: `.cache/ohio_provisional_2025/validation.json`, `validation-summary.json`, the two run folders, reconciled component/cycle CSVs, `.cache/ohio_provisional_development/candidate.json` and `preview-api.json`. API preview checks compare every CSV download with saved bytes and its ZIP member. Regression and browser outcomes are recorded below after completion.


### Residential provisional annual study by cycle

| Calendar cycle | Rate evidence | Grid only | PV only | PV + battery |
|---|---|---:|---:|---:|
| 2025-01 | Verified rates | $192.61 | $150.75 | $136.16 |
| 2025-02 | Provisional | $172.51 | $131.34 | $117.27 |
| 2025-03 | Provisional | $190.56 | $130.61 | $106.77 |
| 2025-04 | Provisional | $180.31 | $123.34 | $104.13 |
| 2025-05 | Provisional | $186.39 | $124.11 | $103.67 |
| 2025-06 | Verified rates | $201.86 | $128.88 | $105.87 |
| 2025-07 | Provisional | $208.10 | $131.82 | $105.80 |
| 2025-08 | Provisional | $208.15 | $130.59 | $103.79 |
| 2025-09 | Verified rates | $192.22 | $125.53 | $98.96 |
| 2025-10 | Verified rates | $202.47 | $143.43 | $118.55 |
| 2025-11 | Verified rates | $197.50 | $154.73 | $139.26 |
| 2025-12 | Verified rates | $202.80 | $165.06 | $153.67 |

These battery-cycle amounts can differ from independent one-month studies because linked cycles do not reset SOC every month.


### Commercial provisional annual study by cycle

| Calendar cycle | Rate evidence | Grid only | PV only | PV + battery |
|---|---|---:|---:|---:|
| 2025-01 | Verified rates | $905.03 | $826.30 | $788.96 |
| 2025-02 | Provisional | $866.54 | $776.61 | $736.73 |
| 2025-03 | Provisional | $909.40 | $760.90 | $703.80 |
| 2025-04 | Provisional | $886.99 | $765.34 | $720.40 |
| 2025-05 | Provisional | $895.85 | $775.38 | $725.13 |
| 2025-06 | Verified rates | $998.39 | $849.94 | $788.32 |
| 2025-07 | Provisional | $1,035.68 | $870.52 | $853.88 |
| 2025-08 | Provisional | $992.01 | $809.92 | $769.75 |
| 2025-09 | Verified rates | $946.87 | $790.11 | $741.25 |
| 2025-10 | Verified rates | $1,014.31 | $888.60 | $838.72 |
| 2025-11 | Verified rates | $954.82 | $874.66 | $832.32 |
| 2025-12 | Verified rates | $1,011.43 | $938.84 | $908.27 |

These battery-cycle amounts can differ from independent one-month studies because linked cycles do not reset SOC every month.


Final verification for this provisional candidate: **2,850 passed,1 skipped**
in411.10s pytest runtime (411.70s launcher phase); seven JavaScript syntax checks
passed. The skip is the opt-in real Caddy TLS test; three paused native-GUI
modules were excluded. A final browser check found and corrected only Step3's
stale verified-coverage explanatory text. Backend engine and annual artifacts
are unchanged. The updated frontend fingerprint is retained separately in
`.cache/ohio_provisional_development/candidate-acceptance.json`; its syntax check,
**21 affected tests** and the affected browser checks passed after that correction.
The earlier candidate/frontend evidence remains attributed to its original hash.

Browser acceptance used one restored February RS case, not the annual matrix:
explicit assumptions and opt-in controls, missing-acceptance rejection, accepted
provisional coverage, cached weather/native-load restoration, submission,
rendered warning/comparison/assumption ledger, post-result naming and history
reopening passed. The browser-submitted run finished in4.56s. Its comparison CSV
was byte-identical to the API case, and schedules/bills/SOC/QSTS were independently
audited. Saved name/status were confirmed separately by API. No browser stalls
or upload/download-event waits occurred. Evidence is `browser-acceptance.json`,
`browser-worker-audit.json`, screenshot and DOM under
`.cache/ohio_provisional_development/`. The preview is on local port19039.
No commit, push, deployment or stable-engine promotion was performed.
