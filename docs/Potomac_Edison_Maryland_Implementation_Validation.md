# Potomac Edison Maryland implementation validation

Development snapshot reviewed October 26, 2026, on `main`, base HEAD `cc8977f`.
Pre-existing Pepco, Delmarva and targeted-policy changes are preserved. No stage,
commit, push, deployment or stable-engine promotion was issued. Earlier reports
retain their recorded source/engine identities and limitations.

## Source coverage and executable boundaries

The initial common R residential/G Type I SOS window is **September–October
2026**, matching complete calendar service/billing cycles and final-day bill
dates. Full-year 2025 is unsupported and tested to reject: historical ECA/admin
credits and adopted G EmPOWER evidence are incomplete. January–May 2026 final
supply originals and June–August G transmission versions remain unrecovered.
R's generation/transmission leaf supports June onward, but G's transmission
leaf starts September 1; its June–September generation table does not backdate
transmission. Known prices, proposed alternatives and pending redlines do not
fill these gaps. November/December and shifted/partial cycles reject.

R has complete ordinary tariff-component coverage in this window, including
source-labeled zero 2026 RRC, residential sales-tax exemption and no historical
adjustments/opening bank. Legislative posting months are outside the scope.
G is a **verified-charge subtotal**, excluding transmission minimum/capacity
and state sales-tax calculation. Omitted charges are not zero or exemptions and
can change dispatch rankings; no complete G bill or complete-bill optimum is
claimed. Complete component coverage is separate from printed-invoice calibration
and a globally rounded-cash objective.

G is restricted to an explicitly utility-approved unmetered method, unchanged
with PV/storage, and exactly 12 consecutive prior calendar import observations.
Each scenario carries its own history. Numeric acceptance requires actual
30-minute peak below 7.5 kW, `C+0.25<=7.5kW`, and distribution energy charges at least
`1.70*(C+0.25)`, where `C=max(current_kWh,0.5*prior12_max_kWh)/250`. This
conservatively makes distribution minima/excess-capacity branches inactive under
unresolved half-kW rounding/floor placements. The optimizer never forces extra
imports to enter the domain; an unverified candidate rejects. Transmission's
separate minimum/capacity combination remains excluded. Its known energy tiers
and inclusive supply-administration decomposition are charged once.

Locality is explicitly hypothetical unincorporated Washington County. Absence
of an ordinary local energy levy is an inventory-based inference plus account
confirmation, not a zero-tax certificate. Utility, jurisdiction, SOS, Type I,
USC, method/history and NEM-account approval are independent facts. APS/FE-AP
metadata does not select another state's tariff or a wholesale node. Ordinary
NEM-account rules retain capacity/history; zero exports do not enable a credit
bank or export settlement. Standalone storage, AGS/standby, special tax/service
and general metered/assessed G billing are unsupported.

The [source ledger](utility_sources/potomac_edison_md/README.md) preserves
23 originals, 23 scoped excerpts and eight rendered receipts; all
83 original/derivative/receipt hashes passed. Originals remain under
ignored `.cache/potomac_edison_md/sources/`. Blocked routes, accounting dash
normalization, proposed/current columns, alternative allocations and dated
history gaps remain explicit. Failed recovery does not prove a source does not
exist. See [billing and eligibility scope](Potomac_Edison_Maryland.md).

## Targeted acceptance selection and candidate

Engine: `f47f55675153825a2036de701b38c6d3d19b0ee3b547d57ea3453c2f890218c0`.
Full source/frontend/test/tool/dependency pin: `.cache/potomac_edison_md/candidate_frozen_1.json`.
All accepted test/matrix/browser evidence matches that pin. Documentation and
private receipts do not change source identity.

Impact is a new utility-specific adapter/rate table, registry/site/default entries,
new account-field visibility, initial-state validation for this utility, and its
validation/coverage selectors. Shared BillingMath, dispatch algorithms, PV/storage
physics, worker/API serialization contracts and electrical replay were unchanged.
The updated targeted policy therefore selects new-utility tests and direct
consumers; **full release and full workflow tiers were not run or claimed**.
Unrelated historical matrices were not rerun. GUI tests were excluded; no native
GUI was opened and no GUI compatibility is claimed.

| Check | Result | Receipt under `.cache/potomac_edison_md/` |
| --- | --- | --- |
| Utility/source/numeric-symbolic/form/worker/save/CSV-ZIP/coverage/driver tests | 177 passed, no skips | `focused_1/report.json` |
| Direct shared absent-DER counterfactual regression | 12 passed, no skips | `acceptance_frozen_1/report.json` |
| Changed JavaScript syntax | passed | `node_syntax_receipt_1.json` |
| One September2026 new-utility matrix | R/G × grid-only/PV-only/PV+battery: 6 scenarios, 17,280 representative OpenDSS interval checks | `acceptance_frozen_1/regional/validation.json` |
| Independent filed arithmetic on saved flows | All 6 monthly scenario bills reconcile, maximum unrounded difference 2.84e-14 USD | `independent_study_benchmarks_1.json` |
| Real HTTP CSV/ZIP and artifact audits | 4 distinct matrix/browser studies, 52 CSVs, 4 valid ZIPs | `matrix_api_receipt_1.json`, `post_browser_api_receipt_1.json` |
| Sources/preservation | 83 hashes, 1605 pre-existing files and staged content preserved | `source_preservation_audit_1.json` |

There are 189 selected test cases across the two non-overlapping selections;
this is targeted acceptance, not a full-suite count. No optional HTTPS skip is
borrowed from earlier release reports. Tests make no live API calls. Independent
benchmarks include R 1,000 kWh distribution $28.87 and G 5 kW/730 kWh ordinary
distribution $21.22 from the rate-case **current** column, never its proposed
prices. Full R 1,000 kWh raw September arithmetic is $178.799, rounded modeled
components $178.80. MES raw $0.149 becomes $0.15 through the numeric half-up cents
rule. G's omitted minimum and statutory sales-tax calculation are not benchmarked
by those fixtures.

The tests cover700kWh decreasing tiers, administration included once, exact
exclusions/completeness, historical-state carry, low-energy/high-history capacity
rejections, actual30-minute peaks, date and missing/duplicate interval rejection,
USC $1.84, MES $0.000149 and numeric/symbolic charges. DST 92/100-interval grids remain
correct, but March/November Potomac Edison billing rejects outside source scope;
no accepted DST-month historical study is claimed. Component cents/rounding bounds
do not certify an exact printed invoice or globally optimal rounded-cash payment.

## September2026 results and proof scope

| Amount scope | Grid only | PV only | PV plus battery |
| --- | ---: | ---: | ---: |
| R ordinary bill | $202.91 | $145.16 | $124.88 |
| G verified subtotal | $180.42 | $112.83 | $103.37 |

The September matrix uses two synthetic household/small-office loads, each 3 kW
reference peak, re-imported through the native CSV contract. Each study contains
2,880 intervals. PV is 5 kW DC/4 kW AC,30-degree south orientation,14% system loss and
96% inverter efficiency. Storage is 10 kWh, 3 kW charge/discharge,initial 5 kWh,20–80%
SOC and 95% directional efficiencies. G starts with explicit hypothetical 1,000 kWh
imports in each of the prior 12 calendar cycles; this is not customer data or
classification proof. Each study restores initial SOC at its final boundary.
Wear $0.03/kWh throughput is separately reported and excluded from optimization;
capital costs, incentives, payback and carbon monetization are excluded.

Actual-year ERA5 at hypothetical 39.60 N, 77.73 W is cached with request/raw hashes
and UTC end padding under `.cache/potomac_edison_md/weather/`. Open-Meteo/
Copernicus attribution is retained. Hourly means held across quarter hours are
not measured 15-minute weather. A full 2025 weather file does not establish tariff
coverage. October has source/unit coverage, not a completed monthly weather study
as of October 26.

All 6 scenarios and 17,280 representative electrical interval checks passed.
All 2 battery primary-cost and minimum-cycling proofs passed their saved tolerances,
with power/SOC/curtailment/zero-export/state and itemized charge reconciliation.
Proofs concern unrounded modeled charges and the accepted domain. G's unknown
transmission minimum/capacity and state tax prevent a complete-bill optimality
claim. This is per-cycle historical perfect foresight, not a joint annual optimum
or surveyed-site/customer-savings validation.

## Browser and saved-artifact acceptance

One concise background pass used [the isolated preview](http://127.0.0.1:59161),
only `.cache/potomac_edison_md/browser_preview_1`. Completed matrix studies were
copied byte-for-byte as seeds; no new seed simulations or changes to original
matrix results were needed. Both plans visibly restored provider/MD-versus-APS,
locality, confirmations, dates/cycles, native CSV, ERA5, PV/inverter, storage and
wear-excluded objective. G's unmetered approval, full 12-month history, USC and
subtotal exclusions were explicitly observed. Both submitted actual reruns,
rendered 3 scenarios and completeness/electrical indicators, saved a custom name
and reopened it from history. No browser operation stalled or timed out.

| Plan | Actual browser study | Saved name | Worker runtime |
| --- | --- | --- | ---: |
| R | `8d2df01a7b9c4d2d8ca2b891606a140e` | Potomac Edison MD R · validated September 2026 | 4.55 s |
| G | `2f41168b2b5f480e84134ea26c3fccf0` | Potomac Edison MD G · validated September 2026 subtotal | 8.15 s |

API readback proves every saved/submitted configuration field equals the original
seed except the chosen name; both saved results have no expiry. Actual browser
runs add 17,280 representative interval checks, excluded from the primary matrix
count and providing no broader date coverage. Proof is in `browser_*_steps_1.txt`,
`browser_residential_1.png`, `browser_commercial_1.png`,
`browser_acceptance_receipt_1.json` and `post_browser_api_receipt_1.json`.
Browser file-chooser/upload and download-event waits were excluded; real HTTP
checks prove saved/downloaded bytes. The electrical-detail dropdown was not
separately exercised. The preview does not promote or refresh a stable store.

## Timing and reproduction

- focused_1: 23.29s launcher wall; pytest 23.21s.
- acceptance_frozen_1: 17.93s launcher wall; pytest 0.42s, regional 17.39s.
- Browser pass: 280.71s elapsed wall, including observations/work between calls; not cumulative tool waiting or active-development time.
- Matrix worker-reported runtime: R 4.54s, G 7.81s.

API work can overlap other wall measurements. Do not add these as CPU/active
development time or infer isolated solver/OpenDSS runtime from worker aggregates.

```sh
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_potomac_edison_md.py \
  --test test/test_potomac_edison_integration.py \
  --test test/test_regional_coverage.py \
  --test test/test_regional_validation_driver.py
/usr/local/bin/node --check src/local_web/static/regional.js
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_regional_counterfactual.py --regional \
  --utility potomac_edison_maryland --period monthly \
  --inputs .cache/potomac_edison_md/weather \
  --output .cache/potomac_edison_md/new-targeted-matrix
```

Use fresh outputs for changed candidates/selections. Resume still requires exact
fingerprints and independent saved-artifact re-audit. Private `coverage_1.md/.csv`
select only this utility's evidence: one complete R case and one G subtotal case;
other utilities' earlier pins are not relabeled. Next evidence work is historical
adjustments/adopted leaves, exact G transmission minima, floor-active/rounded G
billing and statutory state sales tax. Unknown values or eligibility are never
invented to extend coverage.
