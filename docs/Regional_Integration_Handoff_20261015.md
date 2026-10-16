# Eastern utility integration handoff · October 16, 2026

Dominion Energy Virginia, Dominion Energy North Carolina and PSE&G New Jersey
are integrated through the ordinary main setup form, schema 11 and isolated
simulation queue. This is a reviewed **local candidate**, not a public deployment
or stable promotion. Evidence below belongs to its recorded immutable engine;
later source changes require a new pin and verification.

## Preview and release boundary

- Checkout: `/Users/junhayang/Desktop/EnergyEngineerSession/Microgrid_Simulator`, `main`.
- Review browser: <http://127.0.0.1:19031/>.
- Saved NEM study: <http://127.0.0.1:19031/#8362f48aef2c41b2833002e52bdeefeb>.
- Regular-study store: `.cache/regional_validation_reviewed_20261016`.
- Immutable engine: `9e84bc5be182dabec955247f35e7b80bc5b609fb13348d2b2b089e8c8df73ae7`.
- Visible designation remains **Web UI v1.0.1**. No stable engine or public deployment changed.

Static frontend files come from the checkout; Python snapshots do not package
those files or a separate dependency environment. This handoff records a verified
snapshot, not a promise that a subsequently modified checkout matches the pin.
To restart this store without refreshing its engine, first stop any existing
server on port 19031, then run:

```sh
cd /Users/junhayang/Desktop/EnergyEngineerSession/Microgrid_Simulator
/usr/local/bin/python3 -m src.local_web.server --port 19031 --data-dir .cache/regional_validation_reviewed_20261016
```

Future adoption follows the [explicit engine-upgrade process](Local_Web_Application.md).
Do not refresh a production or unrelated store merely to view this candidate.

## Implemented scope and model boundaries

There are **33 executable structures**: 15 Virginia, 7 North Carolina and 11
PSE&G, with 36 enabled plan/supply combinations. Special, closed, unsupported and
future arrangements remain separately identified. The generated
[coverage matrix](Regional_Utility_Coverage.md) and [CSV](Regional_Utility_Coverage.csv)
retain their own dated evidence; regenerate them through their tool, not by hand.
Rows include coverage segments and unavailable entries, not just implemented plans.
The current generated matrix has 103 rows and evidence for fourteen complete-bill
studies plus four qualified subtotals. The macOS desktop launcher
`src/simulation/desktop_application.py` uses the same local Application/main form,
so it inherits these regional controls; separate legacy Tk parity is not claimed.

| Jurisdiction | Executable dates | Principal conditions |
|---|---|---|
| Dominion Virginia | All 15 ordinary structures, January 1–October 15, 2026; 2025 Schedule 1/GS-1 qualified subtotals | Complete ordinary bundled bills use verified Henrico local tax; other localities have named exclusions. Demand-rate crossings need confirmed allocation |
| Dominion North Carolina | Seven structures, January 1, 2025–October 15, 2026 | Enrollment, history/contracts and metering confirmed; unity-PF/zero-reactive billing; transformer-side metering unavailable; fixed-rider crossings need allocation confirmation |
| PSE&G New Jersey | Eleven structures, billing dates January 1, 2025–October 15, 2026 | Three-period residential TOU begins December 8, 2025; closed enrollment and RSCP/CIEP obligations remain explicit |

Utility, state jurisdiction, retail supplier, customer class/tariff, PJM zone and
wholesale location remain distinct facts. Location does not prove account
eligibility. Bundled bills receive no extra LMP, capacity PLC or transmission
adder. PSE&G generation/transmission obligations retain separate June–May periods;
CIEP requires its correct residual-aggregate hourly signal and rejects mismatches.

Shared numeric/optimization expressions preserve tiers, ratchets, minimums,
history, rider dates and taxes. Every accepted dispatch is independently rebilled,
with rounded line items and unrounded reconciliation retained. Multicycle studies
use historical perfect foresight per billing cycle, continuous SOC and evolving
scenario-specific state; only the final boundary restores starting energy. They
are **not jointly optimized annual minima** or prospective operating strategies.
Battery wear is optional in the objective and reported separately.

## Official sources and dated reconstruction

Definitions, eligibility, source URLs, dates, sheet references and hashes are in:

- [Virginia billing/history/NEM](Dominion_Virginia_General.md) and `docs/utility_sources/dominion/`.
- [North Carolina billing/NEM](Dominion_North_Carolina.md) and `docs/utility_sources/dominion_nc/`.
- [PSE&G billing/supply/NEM](PSEG_New_Jersey_Billing.md) and `docs/utility_sources/pseg/`.

The former Virginia January–August 2026 gap is closed: **19 components, 35 dated
versions, 262 unit-labeled coefficients**. January bases use actual filings;
Schedule 10 uses replacement SCC document 385824. CERC's nominal January filing
was suspended and never implemented; its actual charge begins March 1 (386988,
clean page 5, narrative page 2). Deferred fuel changes in February/August, GEN in
April, CE in May, DIST/RBB in June, fuel in July and the September riders are dated.
RBB is separate through May and withdraws in June. The exact July T1 original was
recovered from the official CDN's July 19 archive, SHA-256
`d95972e31c015c58983634cbad1cfbf41298dccfbf7bca64f0a6e7bdd2f76651`.
Its ordinary prices are verified unchanged; the standby threshold changes from
above 15 to above 20 kW. No missing base/rider original remains for this 2026 scope.
The indexed April CE URL returning 404 does not block the retained May clean sheet.

Energy uses actual interval dates. Demand-rate crossings require an explicit
supported allocation/source; no segment-peak rule is inferred. Monthly NEM
netting across changed prices remains unavailable. Required 2025 Schedule 1/GS-1
recurring components are integrated; missing taxes remain exclusions. Many source
rows for other 2025 structures are retained but their adapters are not reconciled.
Ten-year research inventories do not establish ten-year executable billing.

| Independent flat-load benchmark | Unrounded verified result |
|---|---:|
| NC Schedule 1, August 2026, 744 kWh, including 7% tax | $124.2238328 |
| PSE&G RS, January 2025, 744 kWh | $163.341120 |
| PSE&G RS, July 2025, 744 kWh, including filed $30 credit | $198.240240 |
| VA Schedule 1, January 2026, 744 kWh | $132.785592 |
| VA GS-1, January 2026, 7,440 kWh | $970.853120 |
| VA GS-2T, January 2026, 66,960 kWh | $6,034.206640 |
| VA Schedule 1 / GS-1, full 2025, 8,760 / 87,600 kWh | $1,338.809717 / $10,255.789940, incomplete-tax subtotals |

These fixtures independently verify filed arithmetic, not measured bills or an
equal-size tariff ranking. Utility tests cover every executable structure,
holidays, demand averaging, effective dates, proration, histories and netting.

## Completed simulation evidence

All three matrices below use engine `9e84bc5be182`. Their requests, hashes,
itemization, solver evidence and intervals remain ignored/private:

| Store under `.cache/` | Passed / failed / pending |
|---|---|
| `regional_validation_reviewed_20261016` | 12 / 0 / 0 |
| `regional_validation_va_history_reviewed_20261016` | 4 / 0 / 0, qualified 2025 tax subtotals |
| `regional_validation_va2026_reviewed_20261016` | 2 / 0 / 0, January 1–September 30, 2026 |

| Plan / supply | Monthly study | Annual 2025 study |
|---|---|---|
| NC 1T | `013bd8eef3514e848f86c539155dc529` | `a2f63bf1576648908a5201c3a19b165d` |
| NC 5P | `65a7bb9dc8534ef09a4f4cff8b3b68bd` | `cb51165a37ce4847bad6cb3171592892` |
| PSE&G RS / RSCP | `e0c5f44dc41d446b8668401c6675c675` | `7e35c5d4c4554c08835084a6f0457e8f` |
| PSE&G GLP / RSCP | `4db05a34aa9e47fe8e6e2c76a382ecbb` | `78be8575ccf54c9785e1d466a4859624` |
| PSE&G GLP / CIEP | `c6a84147daeb4e299e0b8a768f9ec38d` | `6f8f099c29df4483a554247b80caa29f` |
| VA 1G, September 2026 | `1f9c5108e7a342e1925c13f1a912c042` | No 2025 adapter |
| VA GS-2T, September 2026 | `dde497e4504f4129b48cbf80884373dc` | No 2025 adapter |
| VA 1, qualified subtotal | `a68510158e614da0b8e4b52627e4a0da` | `8fd47d6e713f4515a0e0b69dc8db3b34` |
| VA GS-1, qualified subtotal | `5d590cf0d23e4b8f90036ef36b767e82` | `b04cdf8c1f624647b76206bc7df59b78` |

The nine-month 2026 studies are VA 1G `44c406f294a94b0b86caa701ef12660e`
and GS-2T `11a5752988cf4f46b245036e99bfc060`. Grid/PV/PV-plus-battery bills:
**$1,830.10 / $1,238.96 / $930.29** and **$35,819.69 / $34,677.00 / $34,219.91**,
respectively. Account sizes differ; these are not equal-consumption comparisons.

Together: **18 studies, 54 scenarios, 333 independently rebilled cycles and
972,840 OpenDSS 15-minute scenario-intervals**. All primary objectives were proven
within recorded tolerances or directly billed; all representative replays passed,
with no failed intervals. Minimum cycling was proven in **14/18** storage studies.
It remains unproven for September GS-2T, nine-month GS-2T and 2025 GS-1 monthly/yearly;
that does not invalidate their accepted primary cost proofs.

The older `3a417a7724d0` June GS-2T proof failure remains diagnostic history only.
Stronger physical/expression bounds and caching now allow the ordinary worker to
finish the reviewed case, preserving bill arithmetic and dependencies. No new
solver was introduced, and strict rejection of unproven primary results remains.

Loads are explicitly synthetic household/office profiles imported as native CSVs.
NC/New Jersey and 2025 Virginia use matching actual 2025 NSRDB; 2026 Virginia uses
matching Henrico ERA5 with disclosed hourly-to-quarter-hour sampling. These are
not measured customers or site weather observations. Each store retains
`validation.json`, `validation-summary.json`, comparison/component CSVs and runs.
The matrix totals exclude the additional browser reruns below.

## Actual browser acceptance and downloads

Seven actual main-wizard reruns on `9e84bc5be182` traversed setup, restored
utility/tariff and weather, submitted, rendered results and saved chosen names.
Settings/weather remained unchanged and all three scenarios were audited:

| Browser case | Saved rerun |
|---|---|
| NC residential 1T | `9d62b1e83e1c402785faf0aa8cd14f38` |
| NC commercial 5P | `f959e8983ba34a72a221d2d330fee9f4` |
| PSE&G residential RS | `6715dbe82c8041afa4e5c7b410009131` |
| PSE&G commercial GLP / RSCP | `75ce25b319e9444d8d037687d87b8ed1` |
| VA residential 1G | `cd13013fbab44a6f8775db2457571a69` |
| VA commercial GS-2T | `22d32491a53a4916950304679c70cf22` |
| PSE&G commercial GLP / CIEP | `38a61f3cd8754337ba6384495220ac83` |

Proof: `browser-acceptance-reviewed.json` in the regular reviewed store.
The eighth rerun, Virginia NEM `8362f48aef2c41b2833002e52bdeefeb`, has separate
`browser-acceptance-nem-reviewed.json`: **$198.88 / $102.96 / $97.93**, all bills
and electrical replays verified. Fresh preview confirms the current engine;
screenshot: `.cache/regional_browser_reviewed_20261016.png`.

Current HTTP download routes were independently checked byte-for-byte: CSV and
ZIP with thirteen CSVs plus `result-manifest.json`, 2,594,885 bytes. Evidence is
`download-verification-reviewed.json` in the same store. The final in-app-browser
download-event automation timed out; **no current filesystem download is claimed**.
This is an automation limitation, not evidence of an application download defect.
Earlier `feb77f24553a` and `359beabc5341` rendered UI/download checks remain
separately dated in `.cache/regional_final_browser_20261015` and
`.cache/regional_release_review_20261015`; they are not relabeled as current proof.

## Verification and reproduction

Baseline: **2,118 passed, 1 skipped**. Final strengthened full suite:
**2,833 passed, 1 skipped in 367.60 seconds**, recorded at
`.cache/regional_development/full-regression-strengthened.log`.
The focused reviewed run passed 627 tests; eighteen bound tests and three storage
proof cases are included in the full suite. Offline tests make no live API calls.

```sh
/usr/local/bin/python3 -m pytest -q
node --check src/local_web/static/app.js
node --check src/local_web/static/regional.js
node --check src/local_web/static/comed_simulation.js
git diff --check
# Rebuild summaries without new provider requests.
/usr/local/bin/python3 tools/run_regional_validation.py --summarize --output .cache/regional_validation_reviewed_20261016
/usr/local/bin/python3 tools/run_regional_validation.py --summarize --output .cache/regional_validation_va_history_reviewed_20261016
/usr/local/bin/python3 tools/run_regional_validation.py --summarize --output .cache/regional_validation_va2026_reviewed_20261016
```

Fresh execution uses retained private inputs and new output folders:

```sh
/usr/local/bin/python3 tools/run_regional_validation.py --execute --include-ciep --inputs .cache/regional_historical_inputs/weather_20261015_final --output .cache/regional_reproduce_regular
/usr/local/bin/python3 tools/run_regional_validation.py --execute --include-va-history --utility dominion_energy_virginia --plan VA-1 --plan VA-GS1 --inputs .cache/regional_historical_inputs/weather_20261015_final --output .cache/regional_reproduce_va2025
/usr/local/bin/python3 tools/run_regional_validation.py --execute --utility dominion_energy_virginia --plan VA-1G --plan VA-GS2T --period custom --start-date 2026-01-01 --end-date 2026-09-30 --inputs .cache/regional_historical_inputs/weather_va2026_extended --output .cache/regional_reproduce_va2026
```

These commands pin **current source**, not an old engine identity. New input
retrieval requires its own access/credentials and source provenance. Existing
report directories reject pin changes. Regenerate coverage using the three
reviewed `validation.json` files; generated tables do not themselves execute tests.

## Precise remaining limits

- **2025 Virginia taxes:** actual Schedule 1/GS-1 sales/use surcharge sheets and
  their 2025 transition chain are missing; retained live/archived sheets show 2026.
  The pre-August 16 meter-reading consumption-tax table is missing; four retained
  archive checks returned no snapshot. Henrico's dated 2025 consumer-tax evidence
  is missing; official upload IDs 34230/35032 returned HTTP 403. Comparative SCC
  workpapers reference 2024 taxes, not applicable 2025 rates. Snippets/later rates
  are not substitutes. These studies retain named exclusions,
  `is_complete_bill=False` and `verified_charges_subtotal`; no complete-bill optimum.
- **History:** other 2025 Virginia structures need retained rows normalized and
  reconciled; this is not uniformly an external-source blocker. Complete ten-year
  composites are not reconstructed. The 2026 ordinary-rate gap is closed.
- **Solar:** VA NEM begins February 5, 2026, residential 1/1G/1S, at most 15 kW AC
  before July and 20 kW thereafter. Earlier terms, larger standby, commercial
  NEM, annual/PPA settlement, 1G seasonal crossings and cross-price netting remain
  unavailable. Batteries charge from PV only and do not export. NC/PSE&G rules
  remain provider-specific; PSE&G CIEP NEM and unverified surplus payouts reject.
- **Credit economics:** opening credits reduce bills but are excluded from the
  default objective; closing banks have no invented cash value. Minimum cycling
  proves neither minimum curtailment nor an annual optimum.
- **Electrical:** 25 kVA split-phase residential, 75 kVA eligible single-phase
  commercial and 750 kVA eligible 480 V three-phase circuits are representative.
  Primary/HV/unmatched service may bill while replay remains unavailable; no
  site feeder, protection, transient, islanding or interconnection approval.
- **Permissions/release:** CIEP uses private `116472957 / PSEG_RESID_AGG` data,
  with 8,761 original hourly rows and one boundary hour excluded from 2025.
  No redistribution right is inferred. Schema-11 hosted access/downloads remain
  disabled. Stable promotion, public hosting and licensed-data use need review.

Existing concurrent changes, generated-artifact deletions, README and utility-guide
ownership were preserved. No files were staged, committed, pushed or deployed.
