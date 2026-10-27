# Atlantic City Electric New Jersey implementation validation

Reviewed October 27, 2026, on `main`. Initial orientation HEAD was `cc8977f`.
During this task HEAD advanced externally to `d719295`; the engine/source pin
was unchanged and the index was empty when observed. No Git mutation was issued
by this task. Existing Pepco, Delmarva, Potomac Edison and validation-policy file
contents were preserved. The ACE changes remain unstaged. Earlier utility reports
retain their own engine/frontend pins and limitations. No deployment or
stable-engine promotion was performed.

## Verified billing scope and source gaps

Ordinary **RS residential** and measured **MGS-SECONDARY BGS-RSCP** use separately
verified distribution, supply, transmission, riders and included CBT/SUT. Source
price intersections are February–May, June, July–August and October–November2025,
and September–October2026. **Only exactly 30 complete local service days within one
calendar month, season and component regime can execute.** For example October1–30
works; October1–31 rejects. February itself cannot form such a within-month cycle.
The historical/current Section II 6.5 rule is verified; component proration for
other durations remains unresolved. January/September/December2025 and
January–August2026 source gaps are not filled by known adjacent prices.

Full-year2025 and annual billing/dispatch are unsupported and tested to reject.
No annual acceptance or joint annual optimum is claimed. Source windows do not
mean every arbitrary meter cycle in them is supported. October2026 has source/unit
acceptance, not a finished historical weather/electrical study as of October 27.

The initial account domain is one taxable120/240 V single-phase secondary meter,
unity billing PF, ordinary continuous service, no special contract/exemption/discount,
and explicitly confirmed BGS-RSCP. MGS uses measured15-minute peaks, actual import
peak at most100 kW and an independently assigned November generation-capacity PLS
strictly below500 kW. The correct procurement-year assignment is checked; monthly
load never establishes PLS or supplier eligibility. Other voltage, phase, reactive
billing, unmetered/computed loads and CIEP are unsupported.

All ordinary recurring components are modeled within the accepted domain. Supply
administration/capacity and CBT/SUT are embedded once; no wholesale LMP, PLC/NSPL
or extra tax multiplier is added. Negative2026 ZEC, adopted NGC deletion, the
May2025 TEC change and September/October2026 reconciliation clocks retain exact
signs, dates and component source pins. RS's mandatory -$30 July/August2025 and
+$10 September2025–February2026 apply only where the full stack is verified.
Negative raw or component-rounded post-credit balances reject, without forcing
imports or inventing credit carry/refund settlement.

MGS distribution/IIP demand charge all billed kW, and transmission charges only
billed kW above3. Final numeric billing rounds energy to0.01 kWh and demand to0.1 kW;
exact half ties reject because their convention is unverified. **MGS primary-cost
and minimum-cycling proofs apply to charges using quantities before measurement
rounding**, through the existing objective-input hook. The final quantity-rounded
bill is separately re-audited, with an explicit charge-error bound. No minimum
rounded-invoice claim is made. RS does not borrow MGS's quantity rounding.
Component half-up monetary cents are the existing study convention; exact
line/invoice rounding and printed customer invoices have not been calibrated.
The generic ledger's complete-bill scope describes ordinary component completeness;
the saved `metrics.optimization_objective_scope` records the distinct proof basis.

PV/storage requires written approved ordinary ClassI/NEM-account parallel service,
zero exports, no opening bank and no special/standby fees; study combined capacity
is at most25 kW. **MGS 2025 DER rejects** because its historical six-month generation-
availability standby rule is unmodeled. MGS 2026 uses the adopted December2025 rule
and explicit ordinary approval. RS historical NEM leaves support ordinary zero-
export operation. No export compensation, community solar, annual true-up or
standalone storage is enabled. Grid-only removes DER assertions while retaining
PLS, tariff and other account facts.

Utility, default supplier, NJ jurisdiction, PLS, tax status, written interconnection
approval and PJM **AECO** metadata remain independent. Hypothetical39.45 N/74.58 W
coordinates do not establish service or a wholesale price node.

The [source ledger](utility_sources/atlantic_city_electric/README.md) retains
**20 unique originals, 38 excerpt pins and 5 rendered receipts**; all 90
reference hashes passed. Originals are under ignored `.cache/atlantic_city_electric/sources/`.
Adopted books, proposed/redline context, direct revision continuity, historical
Section II pages, blocked routes and explicit gaps remain distinguishable. Official
PTC images have a stale page-heading/date conflict, retained rather than backdated.
See [account and billing details](Atlantic_City_Electric_New_Jersey.md).

## Frozen candidate and selected checks

Engine: `80215c709132721a0471d9aaed7c8dc531fab1e2cc3e791e63db4c9cc1f0c367`.
Source/frontend/test/tool/dependency identity:
`.cache/atlantic_city_electric/candidate_frozen_1.json`.
All recorded tests, matrices, HTTP audits and browser runs match this candidate.
Documentation/private-receipt edits do not change source identity.

Impact is limited to the new adapter/rate data, registry/default/equipment metadata,
new account-field visibility and utility-specific validation/coverage/audit branches.
Shared BillingMath, dispatch algorithms, worker/API serialization contracts,
time-grid/PV/storage physics and electrical replay are unchanged. Existing
objective-input behavior is reused. This meets the targeted utility policy;
**full release and full workflow tiers were not run or claimed**. GUI tests were
excluded and no native GUI launched. No optional HTTPS skip is borrowed from older
reports; this selection has no skipped tests. Unaffected utility matrices were
not rerun or relabeled.

| Check | Result | Evidence under `.cache/atlantic_city_electric/` |
| --- | --- | --- |
| Utility arithmetic/source/eligibility/quantity/parity/DST plus direct form/worker/save/CSV-ZIP/counterfactual/coverage/driver tests | 217 passed; zero failures/errors/skips | `focused_1/report.json` |
| Changed JavaScript syntax | passed | `node_syntax_receipt_1.json` |
| Selected frozen historical batch | 5 studies, 15 scenarios, 43,212 representative OpenDSS interval checks | `acceptance_batch_1/batch.json` and four exact-date driver manifests |
| Independent source-literal scenario bills | All15 reconcile; max unrounded difference $5.68e-14; all component cents match | `independent_study_benchmarks.json` |
| Primary and cycling proofs | 10 primary proofs, including5 battery proofs; all 5 battery minimum-cycling proofs passed | saved results and independent audit |
| HTTP CSV/ZIP/artifact readback | 7distinct matrix/browser studies,91 CSVs,7validZIPs | `*_api_receipt_1.json` |
| Browser acceptance | Both plans passed restore/submit/results/save/reopen | `browser_acceptance_receipt_1.json`, screenshots and AX steps |
| Source preservation | 90 source-reference hashes passed | `source_preservation_audit_1.json` |

The focused selection uses the two ACE test files plus directly affected regional
counterfactual, coverage and driver tests. It is not a full-suite count. No test
calls live APIs. It covers the May TEC provenance, signed riders, tier/demand
boundaries, separate PLS dates, unsupported settlements, monetary-negative relief
edge, raw/objective/final quantity parity and external rounding-bypass rejection.
Spring DST92-interval days and fall100-interval days are unit checked. The selected
November2025 matrix also checks every interval across fall DST; no spring-DST
historical electrical pass is claimed. An isolated worker test additionally checks
2025 MGS grid-only and historical DER rejection; it is outside the matrix counts.

The independent calculator uses standalone source-valued Decimal arithmetic, not
production rate/math imports, and hashes every saved dispatch/result it reads.
The official BPU650 kWh October2026 transmission/TEC increase independently matches
$1.5977 raw → $1.60. Residential PTC values are rounded comparison figures, and
commercial PTC transmission averages are not an account's per-kW charge. There is
no independently calibrated actual customer invoice. MGS final-minus-proxy charge
difference was at most$0.380394, below its$0.491538 bound; that bound compares
unrounded component sums, before monetarycent effects.

## Historical results and physical assumptions

| Service dates | Tariff | Grid only | PV only | PV plus battery |
| --- | --- | ---: | ---: | ---: |
| 2025-04-01–2025-04-30 | RS | $278.04 | $188.32 | $158.52 |
| 2025-07-01–2025-07-30 | RS | $314.77 | $183.07 | $139.85 |
| 2025-11-01–2025-11-30 | RS | $350.09 | $263.38 | $227.39 |
| 2026-09-01–2026-09-30 | RS | $341.44 | $239.05 | $204.63 |
| 2026-09-01–2026-09-30 | MGS-SECONDARY | $604.81 | $501.85 | $490.31 |

One frozen acceptance batch uses four distinct existing custom-date selections.
This is needed for noncontiguous supported regimes, mandatory relief/recovery,
fall DST and MGS's different historical DER eligibility. Tests are run once;
passing suites/matrices are not repeated. The selected 5 studies cover legacy winter,
summer relief, winter recovery/DST and current2026 summer. Other effective-date
changes have source/unit acceptance rather than broader electrical claims.
No sampling/audit bypass or new launcher tier/flag was introduced. Each selected
case checks every interval for all 3 scenarios; interval totals are cumulative
scenario timesteps, not independent test cases or annual coverage.

Loads are deterministic synthetic household3 kW and small-office8 kW reference peaks,
serialized through the native CSV contract. These are not customer measurements
or regionally calibrated demand forecasts. PV is5 kWDC/4 kWAC,30degrees south,
14% system loss and96% inverter efficiency. Storage is10 kWh,3 kW,initial5 kWh,
20–80%SOC and95%directional efficiency. The final boundary restores initial energy.
Wear$0.03/kWh throughput is reported and excluded from optimization. Capital costs,
incentives, payback and carbon monetization are excluded.

Actual-year ERA5 at the explicit hypothetical site is cached in
`weather/atlantic_city_electric_new_jersey/era5_2025.json` and `era5_2026.json`, with
request/raw hashes and UTC-end padding in `weather/weather-input-manifest.json`.
Open-Meteo/Copernicus attribution is retained; hourly means held across quarter
hours are not measured15-minute weather. Cached2025 weather is not tariff evidence.
Representative residential/commercial circuits check all selected intervals; their
0.95 lagging PF and equipment assumptions are diagnostics separate from unity
billing PF. This is not surveyed-feeder, protection, commissioning or field proof.

## Browser and saved artifacts

One concise background pass used the isolated
[development preview](http://127.0.0.1:59162), data only in `browser_preview_1`.
Finished September2026 matrix stores were copied byte-for-byte as seeds, without
new seed simulations or changing original evidence. Both plans visibly restored
configuration, supplier/NJ/AECO separation,30-day cycle, approved non-export PV,
inverter, cachedERA5, battery, wear choice and nativeCSV. MGS's independent10 kW
November1,2025PLS, measured method and raw-quantity objective acknowledgment were
observed. Both submitted actual reruns, displayed3results and proxy/completeness
warnings, saved a custom name and reopened from the empty home/history view.

| Plan | Actual browser study | Worker runtime |
| --- | --- | ---: |
| RS | `037c14efd94a42ec97dcef9b4691bbaf` | 5.18 s |
| MGS-SECONDARY | `ba5482426c9b46688515acbea4ae2a1b` | 4.54 s |

HTTP readback confirms saved/submitted settings exactly match their seed except
for the chosen name; both results are saved without expiry. Actual browser reruns
add 17,280 representative checks, excluded from the primary 43,212 matrix count and
providing no new date coverage. The two copied seeds are not counted as distinct
studies again. Real HTTP audits verify all 91 CSVs and7 ZIP CRC/member hashes/result
manifests across5 matrix plus 2 actual browser studies, with frozen frontend bytes.

No browser operation stalled or timed out. One local helper expected the label
Next at Step8; it stopped before a UI call, and the freshly observed Review study
control was used. File-chooser/upload and download-event waits were excluded;
HTTP verifies downloaded bytes separately. The electrical-detail dropdown was not
separately exercised. Evidence is `browser_*_steps_1.txt`, `browser_*_1.png`,
`browser_acceptance_receipt_1.json` and `post_browser_api_receipt_1.json`. The preview
does not promote or refresh the stable store.

## Timing, reproduction and preservation

- Focused launcher wall: 23.05s; pytest phase:22.97s, JUnit:22.39s.
- Selected historical batch wall:42.09s. This includes preparation/queue/worker/audit overhead, not isolated solver/OpenDSS CPU time.
- Browser pass elapsed wall:810.18s, including observations and work between calls; not cumulative tool waiting or active development time.
- Actual browser worker times:RS5.18s, MGS4.54s.

These wall intervals can overlap; do not add them as active engineering or CPU
time. Source research, documentation and browser observations are outside test
phase runtimes.

```sh
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_atlantic_city_electric.py \
  --test test/test_atlantic_city_electric_integration.py \
  --test test/test_regional_coverage.py \
  --test test/test_regional_validation_driver.py \
  --test test/test_regional_counterfactual.py
/usr/local/bin/node --check src/local_web/static/regional.js
/usr/local/bin/python3 tools/run_regional_validation.py --execute \
  --utility atlantic_city_electric_new_jersey --period custom \
  --start-date 2026-09-01 --end-date 2026-09-30 \
  --inputs .cache/atlantic_city_electric/weather \
  --output .cache/atlantic_city_electric/new-current-matrix
```

Use fresh outputs for changed candidates/selections. The exact four selected
commands and elapsed times are in `acceptance_batch_1/batch.json`; the three2025
selections choose RS only. Resume still requires matching fingerprints and an
independent saved-artifact re-audit. Private `coverage_1.md/.csv` attaches five
audited complete ordinary-component cases to this pin, never older utility evidence.
The public coverage snapshot was not overwritten.

The preservation baseline is `orientation.json`; the external Git observation is
`external_git_observation_1.json`. Final readback is in `preservation_final_1.json`.
1639 pre-existing file contents are unchanged, and the eight existing edited files
contain scoped ACE additions while preserving earlier work. AGENTS.md, ignored
CLAUDE.md, Development_Validation.md and all prior utility files remain byte-identical
to the initial working baseline. No stage/commit/push/deploy/promotion action was
issued. The external commit is preserved.

Next evidence work is missing component windows, component proration, historical
MGS standby history and exact quantity/monetary tie and invoice rules. None is
filled by adjacent rates, inferred eligibility or an export credit assumption.
