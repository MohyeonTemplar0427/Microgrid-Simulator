# PECO provisional billing-cycle allocation

This is a **study approximation**, authorized separately from verified tariff
research. Prices remain the filed 2025–October 19, 2026 values. The operational
allocation questions in [the evidence review](PECO_Billing_Cycle_Review.md)
remain unanswered. Passing arithmetic, solver and electrical checks validates
this implementation, not PECO's actual partial/crossing bill policy.

## Explicit opt-in

The default is `rate_evidence_mode="verified"`. Old requests without the new
fields keep that behavior. To estimate an otherwise unsupported cycle, set
`rate_evidence_mode="provisional_cycles_v1"` and
`provisional_assumptions_accepted=true` on the account. Both are available in
the existing local-browser account controls and are retained on save/restore.
Cycle overrides cannot enable the mode or change acceptance. Selecting the
mode does not relabel an otherwise verified cycle as provisional.

Versioned model: `peco_cycle_allocation_v1`. Changing its policy requires a
new model designation; do not reinterpret earlier saved estimates.

## Assumed arithmetic

| Item | Provisional rule |
|---|---|
| Supported lengths | 1–45 complete local calendar days, regular/initial/final. No partial clock days. This is a study scope, not a statement of permitted utility billing schedules. |
| Monthly factor | One for 26–35 days; otherwise local service days / 30. A 12-day factor is 0.4; a 36-day factor is 1.2. Never use elapsed hours / 720 across DST. |
| Energy | Integrate actual interval-average import kW over physical hours. Never scale measured kWh by the monthly factor or invent missing intervals. |
| Delivery energy | Actual interval kWh at each service date's delivery components. Keep embedded riders included once. |
| Monthly delivery charges | Apply the monthly factor, with each dated fixed/demand price weighted by its share of local service days. |
| GS demand | One maximum aligned 30-minute average for the whole cycle, rounded to 0.1 kW with the existing tariff arithmetic. Do not sum segment peaks. |
| GS low usage | Compare cycle kWh against 1100 × factor. Below that threshold, use the lesser of rounded demand and kWh / (175 × factor), still at least 1.2 kW. The minimum remains a kW quantity; scale the monthly price, not demand again. This normalization is assumed, not verified. |
| GSA/TOU and TSC date | Use the final **inclusive service date** as a proxy for the scheduled-cycle date. One GSA/TOU price set and TSC price for the whole cycle. No blended supply prices; bill issuance does not select supply. The proxy can differ from the actual closing read date and is not a verified interpretation of Rule 1.3. |
| GS transmission | Full-cycle billing demand × selected TSC price × monthly factor. |
| STAS | Apply each segment's STAS to its delivery energy plus its allocated fixed/demand charges; exclude GSA/TSC. |
| DSIC | Preserve the verified bills-rendered rule: bill-date percentage × (whole-cycle distribution + segment STAS). Its underlying subtotal can still be provisional. |
| Sales tax | Preserve the existing residential exemption or explicit ordinary commercial 6%/8% jurisdiction, after adjustments. Its underlying subtotal can be provisional. |

If a non-DSIC component changes only between service end and issue date, the
end-of-service proxy still makes the bill provisional. It does not backdate
new supply or delivery prices into completed service. Changes only affecting
another class/unused option do not trigger this policy. DSIC-only crossings
of an otherwise supported cycle remain verified.

All earlier territory, enrollment, procurement-class, non-export, equipment,
tax and date-coverage guards remain. This does not extend rates past their
verified coverage or implement PECO net metering. The two cycle-boundary
discontinuities (25/26 and 35/36 days) are part of this declared assumption;
do not optimize service dates or artificially split a real cycle to exploit them.

## Evidence and optimization

Billing and dispatch call the same charge expressions. Saved bills report
`rate_evidence_status="provisional"`, `price_evidence_status="verified"`,
`billing_allocation_status="provisional"`, the model ID and only the assumptions
actually used. The legacy rate-evidence field conservatively labels the entire
bill whenever the allocation is assumed; it does not mean a price was invented.
Component rows include downstream STAS/DSIC/tax assumption links. The comparison
uses `objective_scope="provisional_modeled_bill"`; warnings and the downloadable
`billing-assumptions.csv` describe the policy and values. The same evidence is
present in `result.json`, the billing-cycle metrics and ZIP.

`is_complete_bill=true` means all modeled charge components are included. It
does **not** mean that the allocation policy, customer bill or savings has been
verified. Solver proofs establish the optimum conditional on this model.
OpenDSS separately checks representative electrical operation.

## Verification

Focused tests: `test/test_peco_provisional.py`, alongside existing PECO cycle
and tariff tests. Independent benchmarks cover partial/extended periods,
spring/fall DST, nonuniform usage across rate changes, one GS peak, rounded
demand, normalized low usage, TOU boundaries/holidays, STAS/DSIC/tax ordering
and issue-date gaps. Form-to-worker cases cover residential/commercial partial
and crossing cycles with all three scenarios, bill/dispatch reconciliation,
representative electrical replay, assumption CSV/ZIP and save/restore.

Tests use deterministic synthetic load and clear-sky solar, not measured
accounts or actual historical weather. No live provider requests are needed.
The new candidate's results and identity are recorded after validation; prior
PECO validation reports remain attributed to their original engines.

### Validated candidate, October 19, 2026

Engine `715ac93920149e1cb51d0a3394349d678ef2dc4606a7902e1b1c1ff2a5b5848a`:

- Focused regional and validation-tooling tier: **1,066 passed**, no skips or
  failures, using `/usr/local/bin/python3`. Pytest201.03s; launcher pytest
  phase201.39s. GUI modules excluded. Seven JavaScript syntax checks passed.
  Report: `.cache/peco_provisional_verified/report.json`.
- Four new automated form-to-worker cases cover R-TOU residential and GS-TOU
  commercial partial periods, an R June/July2026 delivery crossing, and a
  GS-TOU May/June2025 supply/delivery crossing. Each runs grid-only, PV-only
  and PV-plus-battery, audits saved bills/dispatch/electrical results, checks
  assumption CSV/ZIP bytes, save/restore and tampered-provenance rejection.
- Two additional persistent API/worker studies below passed independent
  artifact audits. All six scenarios passed **12,084 representative15-minute
  OpenDSS checks** (3×1,148 residential;3×2,880 commercial). Both cost and storage
  minimum-cycling proofs passed; maximum unrounded bill/objective difference
  was below$0.000002. Grid-only requires no optimization.

| Provisional case | Native load | Grid-only bill | PV-only bill | PV + battery bill |
|---|---:|---:|---:|---:|
|R-TOU, March4–15,2025 initial cycle;12 days spanning DST|302.6808kWh|$63.12|$36.14|$23.03|
|GS-TOU, May20–June18,2025 regular crossing cycle;30 days|6,655.632kWh|$1,108.31|$819.47|$727.58|

Inputs are the unchanged generic synthetic household/office shapes scaled to
2/20-kW peaks. PV5/10kW DC, inverter4/8kW AC; battery10/30kWh and3/8kW.
Clear-sky conditions assume20°C and1m/s; these are not actual weather or
measured bills. The residential factor is0.4; commercial monthly factor1,
with12/30 and18/30 delivery shares. No export or wear cost enters dispatch.
The API runs took4.13s and13.12s including queue/poll/audit/download work;
worker-reported runtimes were2.91s and12.51s. These overlapping wall times
are not active-development or separate solver/OpenDSS CPU measurements.
See the [scenario CSV](PECO_Provisional_Validation.csv) and ignored evidence in
`.cache/peco_provisional_development/preview_api.json`.

One concise browser pass rendered the provisional result, saved/reopened it,
restored the account mode/acceptance and documented12-day cycle, and verified
that unchecked acceptance blocks progress. Navigation reached step8. A selector
for “Next” then timed out because that step offers “Review study”; automation
stopped without retrying the failing operation. **Browser rerun submission is
unverified.** This is an automation boundary, not evidence of a billing defect.
API/worker checks do not substitute for that missing UI assertion. The receipt
and screenshot are in `.cache/peco_provisional_development/browser_acceptance.json`
and `browser-acceptance.png`. No source, frontend, test or tool changed after
the candidate freeze; no stable engine was promoted.
