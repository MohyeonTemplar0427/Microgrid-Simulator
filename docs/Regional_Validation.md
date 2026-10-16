# Eastern regional validation driver

`tools/run_regional_validation.py` prepares explicit historical weather and
reproduces schema-11 studies through the ordinary immutable Application queue
and independent worker. Inputs, complete requests, bills, CSVs, results and
price-derived summaries remain in the ignored `.cache` tree. No API credentials
are included in artifacts. The driver never refreshes a source pin or promotes
the candidate engine.

Preparation and execution are separate:

```sh
/usr/local/bin/python3 tools/run_regional_validation.py --prepare-inputs
/usr/local/bin/python3 tools/run_regional_validation.py --execute --output .cache/regional_validation_reviewed_candidate
```

Only run the second command after reviewing the candidate source. An existing
output folder with a different source pin rejects; choose a fresh folder.
`--include-ciep` adds a separate optional PSE&G commercial hourly-supply study,
using the private official residual aggregate CSV and metadata from
`.cache/regional_historical_inputs/pseg`. It never substitutes a hub, generic
zonal price, auction price or constant supply price for missing CIEP data.

| Region | Representative plans | Monthly period | Historical year |
|---|---|---|---|
| Dominion North Carolina | Residential 1T; commercial 5P | July 2025 | 2025 |
| PSE&G New Jersey | Residential RS; commercial GLP | July 2025 | 2025 |
| Dominion Virginia, current | Residential 1G; commercial GS-2T | September 2026 | These plans have no executable 2025 history |
| Dominion Virginia, historical opt-in | Residential 1; commercial GS-1 | July 2025 | 2025 verified charges subtotal, excluding explicitly missing historical taxes |

NC and New Jersey use actual 2025 NSRDB satellite weather at the declared
representative coordinates. Virginia uses explicitly selected September 2026
ERA5 reanalysis via Open-Meteo; its hourly radiation is held across the four
quarter-hour physical intervals, with the existing adapter's timestamp and
sampling disclosure. These weather sources are not interchangeable and no
fallback occurs. Preparation saves request, retrieval, provider and checksum
metadata. Weather may be reused unchanged in a new engine-scoped cache.

`--include-va-history` adds the two historical Virginia plans. Their actual
2025 NSRDB weather is stored separately in
`dominion_energy_virginia/nsrdb_2025`; September 2026 ERA5 cannot satisfy that
input. To prepare and execute only the four historical monthly/annual studies:

```sh
/usr/local/bin/python3 tools/run_regional_validation.py --prepare-inputs --include-va-history --utility dominion_energy_virginia --plan VA-1 --plan VA-GS1 --inputs .cache/regional_historical_inputs/weather_20261015_final
/usr/local/bin/python3 tools/run_regional_validation.py --execute --include-va-history --utility dominion_energy_virginia --plan VA-1 --plan VA-GS1 --inputs .cache/regional_historical_inputs/weather_20261015_final --output .cache/regional_validation_va2025_reviewed_candidate
```

The historical Virginia amounts are **verified charges subtotals**, not complete
utility bills. Sales/use tax surcharge and local utility-consumer tax are
excluded throughout 2025; consumption tax is also excluded for cycles ending
before August 16, 2025. Missing decision-dependent taxes mean even a proven
subtotal optimum does not prove a complete-bill optimum. The audit requires the
exact historical rate version, exclusion list, completeness flag and warning;
it rejects every other incomplete-bill scope. Saved CSV/JSON records retain
`is_complete_bill=False`, `objective_scope=verified_charges_subtotal` and each
excluded component. There is no substitution of later tax rates.

Demand uses the existing deterministic household or office archetype,
serialized and imported as a complete native-load CSV. It is synthetic, not
measured consumption, utility meter purchases, a customer forecast or a
regionally calibrated load. The numerical study settings are:

| Case | Native peak | PV DC / inverter AC | Battery energy / charge-discharge rating |
|---|---:|---:|---:|
| NC residential | 3 kW | 5 / 4 kW | 10 kWh / 3 kW |
| PSE&G residential | 4 kW | 5 / 4 kW | 10 kWh / 3 kW |
| VA residential | 3 kW | 5 / 4 kW | 10 kWh / 3 kW |
| NC commercial | 40 kW | 10 / 8 kW | 30 kWh / 8 kW |
| PSE&G commercial | 40 kW | 6.25 / 5 kW | 30 kWh / 5 kW |
| VA commercial | 90 kW | 10 / 8 kW | 30 kWh / 8 kW |
| VA historical GS-1 | 15 kW | 10 / 8 kW | 30 kWh / 5 kW |

SOC begins at 50%, operates within 20–80%, and is restored only at the final
study boundary. Charge/discharge efficiencies are each 95%. PV tilt is 30°,
azimuth 180°, system losses 14%, and nominal inverter efficiency 96%.
Hypothetical authorization permits grid charging. The utility-bill objective
excludes battery wear; its separate estimate remains reported. These are
different representative account sizes, so their absolute bills must not be
ranked as an equal-consumption regional tariff comparison. The saved monthly
native kWh makes that distinction visible.

Historical VA-1 uses the same 3 kW residential reference. Historical GS-1 keeps
its explicitly hypothetical 20 kW contract and eleven prior 20 kW peaks identical
across scenarios. Its single-phase 240 V service uses the existing 75 kVA
commercial representative transformer; that rating is an electrical study
assumption, not inferred utility equipment.

PSE&G commercial combined rated output remains
below the ordinary/standby threshold as the starting history rolls out;
other utility-specific eligibility is validated without changing enrollment.
Starting histories, contracted capacities and utility-assigned obligations are
hypothetical assumptions, identical across the three scenarios. PSE&G
generation and transmission obligations remain distinct; each cycle explicitly
identifies the applicable June–May obligation year.

Every case compares grid-only, PV-only and PV-plus-storage using the same
native demand and available solar. Export remains disabled. Optimization uses
historical perfect foresight within each cycle. SOC is continuous across cycles,
and only the final study boundary restores initial energy. Each scenario carries
its actual own credit/history state forward; the driver does not claim a jointly
optimized annual minimum or a strategy executable without future knowledge.

The audit independently reads saved interval tables and recalculates every
cycle with the authoritative numeric billing adapter. It checks itemized totals,
component savings, objective reconciliation, actual state propagation, demand
eligibility, equipment ratings, SOC recursion, charge/discharge exclusivity,
curtailment and non-export limits. OpenDSS must evaluate every interval of every
scenario using a declared representative circuit. Electrical violations remain
reported results; they never alter scheduled billing flows. The driver records
whether minimum cycling was proven separately from the primary cost optimum.
When a saved candidate records its relaxation or strict-solver proof, the audit
also checks that the physical bill and throughput attain their reported lower
bounds within the explicitly saved numerical tolerances. An older result with
no such metadata is labeled `legacy_not_recorded`, not given a new proof method.
Short deterministic tests verify that the audit detects a changed saved charge.

`validation.json`, `study-comparison.csv`, `monthly-comparison.csv` and
`billing-components.csv` and `period-components.csv` retain the study IDs,
engine/driver hashes, source
artifact hashes and failed validations. Official-rate arithmetic benchmarks are
also tested in the utility-specific test modules. Actual CIEP input coverage
alone is not evidence of a completed annual study; validation status is recorded
only after the immutable worker and every saved-artifact audit complete.

For a compact JSON report, execution also writes `validation-summary.json`.
It can be rebuilt without new weather or market requests:

```sh
/usr/local/bin/python3 tools/run_regional_validation.py --summarize --output .cache/regional_validation_reviewed_candidate
```

The report preserves failed/pending cases, physical and bill assumptions,
scenario savings, cycle-proof methods and gaps, electrical counts, warnings,
source URLs and artifact hashes. Source catalogs are read from that result's
immutable worker, rather than today's main-branch tariffs. It records a separate
saved summary-driver hash so later report improvements remain reproducible.
Raw native, weather and market rows are excluded; credentials in source links
are removed. Unknown legacy proof details stay unknown.

## Explicit custom-date validation

The driver also accepts `--period custom --start-date YYYY-MM-DD --end-date
YYYY-MM-DD`. Both inclusive dates are required, must remain in one calendar
year, and cannot be combined with the monthly/annual selectors. The native
reference profile is generated for that full year and then cropped, so the
same timestamp does not acquire a different assumed load in another slice.
Opening historical month labels and PSE&G obligation periods follow the chosen
start. Actual cycle, tariff, weather and required market coverage still reject
unsupported inputs; this flag does not fill a coverage gap.

Custom execution uses explicitly prepared weather and cannot invoke the
default `--prepare-inputs` route. For the additional Virginia January–September
2026 study, the original ERA5 request is January 1–September 30 at
37.63, -77.52. Its bytes are retained at
`.cache/regional_historical_inputs/weather_va2026_extended/dominion_energy_virginia/era5.json`,
SHA-256 `c0ad75d45c84d1ef5d14046848bb1663a5ecc72e4ab0c3f58750a75f59edfa73`.
The source manifest is
`.cache/regional_historical_inputs/va_2026_year_to_date/manifest.json`.
The adapter validates all 26,204 physical quarter-hour intervals, including the
spring DST transition, against the original hourly source. It holds hourly
radiation means; it does not claim quarter-hour weather measurements.

```sh
/usr/local/bin/python3 tools/run_regional_validation.py --execute --utility dominion_energy_virginia --plan VA-1G --plan VA-GS2T --period custom --start-date 2026-01-01 --end-date 2026-09-30 --inputs .cache/regional_historical_inputs/weather_va2026_extended --output .cache/regional_validation_va2026_reproduction
```

This is a nine-month rolling study, not a full 2026 annual study. The older
default September weather file cannot satisfy it. No weather year is shifted
and no source fallback occurs. A fresh source retrieval would have its own
retrieval timestamp and hash; exact reproduction reuses the retained bytes.

## Candidate evidence recorded October 15, 2026

Both final matrices used immutable engine
`359beabc5341c8c20d93ffcc1e24f19960d65d213ab3438b8691edc241789921`:

| Private report folder | Cases passed | Bill scope |
|---|---:|---|
| `.cache/regional_validation_release_20261015` | 12/12 | Complete supported NC/PSE&G bills and September 2026 Virginia bills |
| `.cache/regional_validation_va_history_20261015` | 4/4 | Explicitly incomplete 2025 Virginia verified charges subtotals |

Each folder contains its own `validation-summary.json`, original requests,
engine/driver source artifacts, input hashes and downloadable interval tables.
Together they contain 48 scenario results and 279 independently recalculated
billing cycles. All 815,616 scheduled 15-minute scenario intervals were replayed
through OpenDSS, with zero failed intervals and every scenario electrically
feasible under its declared representative circuit. These results do not
establish actual site feasibility.

Every primary objective was proven or had no dispatch decision. Historical
Virginia proofs apply only to verified subtotals, because the documented taxes
remain missing. Minimum cycling was separately proven in 13 of 16 storage
studies; current Virginia GS-2T and historical GS-1 monthly/yearly studies retain
an explicitly unproven cycling tie-break. No yearly result is labeled an annual
optimum. The earlier `.cache/regional_validation_final_20261015` matrix remains
separate evidence from its previous engine pin; it is not relabeled as the final
engine. The final regular matrix reproduced all of its reported bill amounts.

The PSE&G CIEP studies use actual 2025 hourly residual-aggregate prices. Raw
prices and their derived study reports remain private; this validation does not
grant public redistribution permission.

## October 16 bounded-formulation refinement

Candidate `9e84bc5be182dabec955247f35e7b80bc5b609fb13348d2b2b089e8c8df73ae7`
differs from `3a417a7724d0` only in `src/billing/regional_math.py`; dependencies,
utility arithmetic, dispatch objectives and strict proof requirements are
unchanged. Constant-rate dot products now retain the registered physical
aggregate-energy bound. Varying signed rates retain per-interval bounds.
Repeated identical scalar predicates share one selector, with distinct slices
and mutable parameters kept separate. Conditional branch constraints use their
own valid asymmetric bounds instead of a single wider span.

These changes tighten the formulation, without replacing the filed charge
expressions or accepting an unproven primary solve. Independent bound tests
check signed and zero rates, aggregate-energy limits, selector identity,
continuous boundaries and disjoint positive/negative branch ranges. Physical
exclusivity and authoritative rebilling remain mandatory after a solve.

The retained earlier nine-month GS-2T attempt
`a86ef61fa9bb48779fb790a20747d077` on engine `3a417a7724d0` failed in June:
its strict solver had a genuine remaining cost gap after 90 seconds. It is
preserved as a failed attempt. A separate diagnostic of that exact captured
June input/account/state proved the strengthened model in about 22 seconds;
the diagnostic does not itself constitute a new queued-study acceptance run.
Final reviewed studies must identify their own immutable engine and results.

Three additional offline main-form-to-worker tests exercise storage without
PV in Virginia, North Carolina and New Jersey. They check absent generation,
non-export operation, power balance, charge/discharge exclusivity, start-of-
interval SOC recursion, restored terminal energy, bill proof/reconciliation
and shared representative electrical replay.

## Reviewed queued-study acceptance · October 16, 2026

All three final matrices use the exact strengthened candidate
`9e84bc5be182dabec955247f35e7b80bc5b609fb13348d2b2b089e8c8df73ae7`:

| Private report folder | Accepted cases | Scope |
|---|---:|---|
| `.cache/regional_validation_reviewed_20261016` | 12/12 | NC/PSE&G monthly and 2025 annual studies, current VA monthly studies, and actual-price CIEP |
| `.cache/regional_validation_va_history_reviewed_20261016` | 4/4 | Explicitly incomplete VA 2025 Schedule 1 / GS-1 monthly and annual subtotals |
| `.cache/regional_validation_va2026_reviewed_20261016` | 2/2 | VA 1G and GS-2T, January 1–September 30, 2026; nine-month studies, not annual studies |

The normal immutable queue completed **18 studies, 54 scenarios and 333
independently rebilled cycles**. All **972,840** 15-minute scenario intervals
were replayed through OpenDSS; no intervals failed and all scenarios passed
their declared representative-circuit checks. Each primary objective is proven
or directly billed with no dispatch decision. Four historical Virginia studies
remain tax-incomplete subtotals; their proofs do not establish a full-bill
minimum. Annual/custom dispatch remains rolling-cycle historical perfect
foresight, with continuous SOC and propagated histories/credit state.

Minimum cycling is separately proven for all cycles in **14/18** storage
studies. September VA GS-2T, historical GS-1 monthly/annual and the nine-month
GS-2T study retain proven primary schedules with explicitly unproven cycling
refinements. In the nine-month GS-2T study all nine primary optima passed; the
cycling refinement passed in four of nine cycles. The earlier failed `3a`
attempt remains a failed artifact rather than being overwritten or relabeled.

Actual main-browser acceptance on the reviewed engine covers the six
jurisdiction/class pairs, plus PSE&G CIEP and Virginia residential NEM. The
eight saved reruns preserve the source account/load/equipment/weather inputs.
Proof files are `browser-acceptance-reviewed.json` and
`browser-acceptance-nem-reviewed.json` in the regular report folder. The NEM
saved study is `8362f48aef2c41b2833002e52bdeefeb`; its independently reconciled
grid/PV/PV-plus-battery bills are $198.88 / $102.96 / $97.93. All three replayed
scenarios passed, with SOC and power-balance errors below `6e-14`.

The current CSV route matches the saved comparison bytes. The ZIP route's
thirteen CSVs and result manifest all match their saved source bytes; see
`download-verification-reviewed.json`. Final in-app-browser download-event
automation stalled and did not confirm a new filesystem download. Earlier
actual browser-download evidence remains dated to its own engine; current
HTTP route verification is recorded separately. A fresh browser tab reopened
the saved final result and confirmed engine `9e84bc5be182`.

Final full regression: **2,833 passed, 1 skipped in 367.60 seconds**, recorded
in `.cache/regional_development/full-regression-strengthened.log`. Source
fingerprints in each final engine manifest match the current Python checkout;
dependencies are unchanged from `3a`. These are local candidate results, not
stable adoption, public hosting or site-specific electrical validation.
