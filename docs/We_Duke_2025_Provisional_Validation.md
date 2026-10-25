# We Energies and Duke Indiana: provisional 2025 studies

The user authorized provisional assumptions for the remaining source gaps on
October 24, 2026. This supplements the source investigation in
[We_Duke_2025_History.md](We_Duke_2025_History.md); it does not close those
verified-rate gaps or relabel the earlier candidate's results.

## Evidence and scope

Verified-only is the default. A study must explicitly choose
`rate_evidence_mode="provisional_2025"` and set
`provisional_assumptions_accepted=true`. Missing, false, string or otherwise
ambiguous acceptance cannot authorize assumed prices. Verified service windows
keep their existing arithmetic and evidence status even in accepted mode.

| Missing evidence | Provisional study treatment |
| --- | --- |
| We July–December 2025 ECC | Hold June's verified factor: $0.00055/kWh residential and $0.00050/kWh small commercial. Do not backdate January 2026 factors. |
| Duke January–February 26 missing rider tables | Use verified preceding base/available rider values; explicitly substitute same-class March-reset values for the unrecovered rider components. The reset's cost reallocation makes this materially uncertain. |
| Duke April–June FAC143 sign | Use negative $0.004801/kWh supported by the official calculations; flag the conflict with the printed positive sign and missing final tariff. |
| Duke July–December ECR/renewable-project tables | Hold the same-class March factors despite known later supersession; do not call them verified later factors. |
| Duke December credit67 expiry treatment | Hold the approved September credit, explicitly flagging the unresolved December treatment. |
| Duke cycles crossing civil months | Use the explicit designated billing month for whole-cycle riders, preserving one full monthly charge and block set for a complete regular cycle. This allocation is separately labeled where unverified. |

Verified We base/TOU prices, fuel and September refund remain in place.
Verified Duke quarterly FAC and September credits are used on their applicable
clocks. Each bill records only assumptions actually used, with an identifier,
dates, affected charge components, values, explanation and source references.
Dependent taxes/fees remain marked where an assumed charge enters their base.
Numeric billing and optimization consume the same selected components.

These assumptions are replaceable modeling inputs. Neither arithmetic
reconciliation, solver proof nor OpenDSS can establish their historical
accuracy. No uncertainty range or measured customer-bill calibration is
claimed. In particular, the Duke pre-reset and superseded rider assumptions
are more uncertain than the small We ECC carry-forward.

The official IURC July 1, 2025 residential survey provides a useful external
check: at 1,000 kWh its Duke bill is $157.98 before tax. The provisional model
calculates $163.0677 before component rounding and tax, $5.0877 (about 3.22%)
higher. That difference is retained and tested, because the held March ECR
and renewable-project factors are scenario assumptions. The survey's rounded
tracker amounts are not used to invent exact class factors. See the
[official survey](https://secure.in.gov/iurc/files/2025-Electric-Residential-Bill-Survey-UPDATED.pdf)
and [Duke assumption ledger](utility_sources/duke_in/provisional2025-assumptions.json).

## Reproducible cases

The annual matrix selects We Rg1/Rg2 residential, Cg1/Cg6 small commercial,
and Duke RS residential/CS small commercial. It compares grid-only, PV-only
and PV-plus-battery with identical native demand and weather within each
site/class. Duke RS-TOU/CS-TOU are not annual 2025 plans: they did not exist at
the start of that year, and provisional selection does not waive eligibility.
The four chosen We plans and two Duke plans have no demand charges.

Weather is the retained actual-year Open-Meteo ERA5 reanalysis under
`.cache/we_duke_weather`, including its raw hashes and sampling disclosure.
Hourly previous-hour radiation means are held over four physical quarter-hour
intervals. Loads are the existing deterministic generic household/office
archetypes, serialized through native-load CSV import. They are synthetic,
not measured, regionally calibrated or a weather-driven customer forecast.

The household peaks at 3 kW, with 5 kW DC / 4 kW AC PV and a 10 kWh / 3 kW
battery. The small office peaks at 10 kW, with 10 kW DC / 8 kW AC PV and a
30 kWh / 8 kW battery. PV uses 30-degree tilt, south azimuth, 14% system losses
and 96% inverter efficiency. Storage starts at 50% SOC, operates between
20–80%, and has 95% efficiency in each direction. Wear is reported at
$0.03/kWh throughput but excluded from the utility-bill objective.

We uses twelve explicitly hypothetical calendar cycles. Duke uses twelve
hypothetical regular 26–34-day cycles: January 1–26, January 27–February 26,
February 27–March 31, then April–December calendar cycles. This avoids a
February 27 base-rate crossing, covers each interval once and avoids adding a
thirteenth customer charge. It is not a real customer's meter-read schedule.

Dispatch has historical perfect foresight within each cycle; SOC carries
continuously across cycles and returns to its initial energy at year end.
This is a rolling strategy, not a jointly optimized annual minimum or a
deployable forecasting strategy. Exports, capital costs and incentives are
excluded. All returned scenarios receive the existing representative OpenDSS
15-minute replay; losses and PCC measurements remain separate from the
scheduled flows used for billing. The residential reference is 25 kVA/100 A
split phase; Duke commercial is 75 kVA/400 A single phase. We commercial
retains the explicit balanced 750 kVA/480 V reference. These are circuit
assumptions, not site-specific equipment or network-constrained optimization.

The validation launcher requires `--allow-we-duke-provisional` in addition to
the selected utilities/plans. The flag enters the immutable resume selection.
The audit rechecks exact evidence ledgers, itemized bills, objective proofs,
SOC/power balance, curtailment, non-export constraints and every electrical
interval. Saved JSON/CSV/ZIPs preserve provisional status and assumption IDs;
the catalog's verified coverage remains separate.

With the retained weather inputs, reproduce the annual matrix using:

```sh
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_regional_validation_driver.py \
  --test test/test_regional_validation_resume.py \
  --test test/test_validation_launcher.py --regional \
  --utility we_energies_wisconsin --utility duke_energy_indiana \
  --plan Rg1 --plan Rg2 --plan Cg1 --plan Cg6 --plan RS --plan CS \
  --period annual --allow-we-duke-provisional \
  --inputs .cache/we_duke_weather --output .cache/we_duke_2025_provisional_annual
```

Use a new output folder for changed inputs/source, or `--resume` only when the
frozen source, inputs, tests, validator and selection match the original run.
The separate broad regression command is
`/usr/local/bin/python3 tools/validate.py --tier release --output .cache/we_duke_2025_provisional_release`.

## Validation record

Frozen engine:
`1a246035b6823b9c85f172df9654a986567d34ddbe98719a6584f0bc3cb4373d`.
The complete frontend/source/test/tool fingerprints are retained in
`.cache/we_duke_2025_provisional_candidate.json` and each launcher report.
The stable local application pin has not been promoted.

The new model's development focused run passed 646 checks and found three
driver-test failures: two overlong generated annual titles, and an old mocked
component table missing the newly required evidence columns. Titles and the
fixture contract were corrected. Read-only review also tightened the artifact
audit against relabeled provisional status and altered CSV source/date fields.
The initial report remains superseded evidence, not a final pass. The final
matrix launcher has passed all 92 validation-driver/resume/launcher tests.

The full-year matrix passed all six studies: 18 scenarios, 216 independently
reconciled cycle bills and 630,720 converged, feasible 15-minute OpenDSS
scenario intervals. No failed electrical intervals, voltage violations, line
overloads or transformer overloads were recorded under the declared reference
circuits. All 72 storage-cycle primary cost optima and minimum-cycling
refinements were proven; the maximum objective/rebilling difference was below
$0.000002. None is labeled a jointly optimized annual optimum.

The following are **provisional annual utility-bill estimates**, in USD:

| Utility / plan | Grid only | PV only | PV + battery |
| --- | ---: | ---: | ---: |
| We Rg1 | 2,790.77 | 1,976.20 | 1,674.08 |
| We Rg2 TOU | 2,596.50 | 1,706.57 | 1,285.46 |
| We Cg1 | 7,197.87 | 4,971.15 | 4,759.65 |
| We Cg6 TOU | 8,217.94 | 5,405.62 | 4,601.58 |
| Duke RS | 2,239.52 | 1,662.27 | 1,441.76 |
| Duke CS | 6,207.57 | 4,517.57 | 4,353.01 |

These are synthetic-load operating comparisons with assumed missing tariff
components, not actual customer bills, regional average bills, installation
payback or proof of historical tariff accuracy. Component savings and all
monthly bills remain in the matrix's `period-components.csv`,
`billing-components.csv` and `monthly-comparison.csv`. Their evidence columns
distinguish assumed components from verified ones; assumption IDs survive
annual aggregation.

Annual evidence is in `.cache/we_duke_2025_provisional_annual/report.json`
and its `regional/validation-summary.json`. The 92 test checks took 9.15
seconds; the matrix phase took 405.52 seconds, including six fresh studies
and their audits. Matrix-session elapsed time was 401.52 seconds. These
wall-clock measurements overlap the separate regression run and are not
additive CPU or active-development time.

The temporary local API verification passed for all six annual studies:
downloaded requests and manifests matched saved bytes/values, every ZIP
passed CRC and exact membership checks, and every bundled CSV matched its
saved table. The assumption CSVs and explicit permission/evidence fields
survived download. Restored annual requests retained all 35,040 intervals and
twelve cycles. All eleven served frontend files matched the freeze. This
5.69-second check used no external API and closed its temporary server.
Evidence is `.cache/we_duke_2025_provisional_api_artifacts.json`.

The final broad release tier passed **4,027 tests, with one skip and twelve
warnings**, plus all seven JavaScript syntax checks. Its pytest runtime was
755.01 seconds (755.71 seconds for the phase). The twelve warnings are the
existing DTE tests' SciPy/HiGHS option-forwarding warnings. The real Caddy HTTPS
check was skipped because `MICROGRID_TEST_CADDY` was not configured; no public
HTTPS/deployment acceptance is claimed. Evidence is
`.cache/we_duke_2025_provisional_release/report.json` and the adjacent logs/XML.
After all runs, source, frontend, test, tool and configuration fingerprints
still matched the frozen candidate. `git diff --check` passed; no changes were
staged, committed or pushed, and the initial unrelated edits were preserved.

Browser acceptance is unverified: the browser inventory tool aborted before
dispatch and was not retried. API and artifact checks do not establish a
rendered UI action. GUI tests remain excluded by the paused-GUI policy.
No promotion, commit, push or deployment is authorized by this validation.
