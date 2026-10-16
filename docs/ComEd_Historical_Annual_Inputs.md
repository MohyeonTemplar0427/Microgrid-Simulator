# ComEd historical weather and annual imports

The local schema-10 candidate now accepts full-year native-load and hourly-price
imports and matching historical NSRDB weather. Both the local browser and modern
desktop GUI use this same form/backend. Web UI v1.0.1 and all existing engine
pins remain unchanged; this is candidate development, not a hosted release.

## Input contracts

- Native consumption: `timestamp,native_load_kw`, one finite nonnegative average
  kW value per exact study interval, at most 2 MiB / 35,136 rows. Residential
  intervals are 15, 30 or 60 minutes; commercial intervals are 15 or 30 minutes.
  Meter purchases/net imports at a PV/storage site cannot silently become native
  consumption. Users must confirm the basis and identify measured, reference or
  synthetic data in the source field.
- Normalized BESH prices: `timestamp,residual_lmp_usd_per_mwh`, one finite signed
  value per physical hour, at most 2 MiB / 8,784 rows. This is raw PJM real-time
  residual ComEd LMP, not an adjusted retail price, hub, generic zone, day-ahead
  price or five-minute estimate. A source declaration alone does not authenticate
  a file's origin.
- Official PJM files: select `pjm_csv` and supply the original Data Miner CSV,
  at most 8 MiB. `pjm_metadata` requires `market=REAL_TIME_HOURLY`, official
  `source_url`, timezone-aware `retrieved_at`, `unit=$/MWh` and
  `usage_permission=internal_use_only`. The shared `PJMProvider` historical-file
  path bypasses the live adapter's 186-day guard without downloading all nodes.
  ComEd additionally requires node **116472935 / COMED_RESID_AGG**, type
  **RESIDUAL_METERED_EDC**. PJM leaves this aggregate's native transmission-zone
  field blank. Preserve that blank rather than inventing a zonal value; the
  customer's separate PJM transmission-zone designation remains COMED.
- PJM revisions: choose the unique current row at the highest revision number
  for each UTC hour; reject missing/stale/conflicting revisions. Retain the raw
  file in private saved settings, its SHA-256, revision numbers, source URL,
  retrieval timestamp, native units and aggregate identity in result provenance.
  Tariff HEC factors apply once to raw LMP; capacity, transmission and procurement
  remain separate filed components.
- Historical weather: reuse `/api/weather` and its owner-checked resource cache.
  NSRDB GOES CONUS PSM v4 provides historical satellite-derived irradiance and
  meteorology; this is not a forecast or a site weather-station measurement.
  Source URL, retrieval time, request, row count, parameters, interval-label
  conversion and saved-file checksum are retained. Weather location, actual year,
  timezone and interval must match the study. Changes to bytes, gaps or mismatched
  years fail rather than falling back to clear-sky data. Credentials stay local.

Normalized timestamps require `Z` or explicit UTC offsets and interval-start
semantics. There is no interpolation, resampling, scaling or timezone guessing.
PJM's specifically named UTC column is interpreted as UTC even where its native
export omits an offset. UTC mapping preserves both repeated fall-back hours and
the missing spring-forward wall-clock hour.

The form offers a full calendar-year study with explicitly hypothetical calendar
billing cycles, in addition to actual documented utility cycles. All twelve rate
versions must exist. Studies are bounded to 366 service days and 12 cycles;
verified retail coverage remains January–December 2025 and January–October 2026.
NSRDB currently supports actual historical years through 2025. Schema 9's monthly
normalized import limit remains 6,000 rows.

## Official data used for the 2025 validation

[NSRDB's official API](https://developer.nlr.gov/docs/solar/nsrdb/nsrdb-GOES-conus-v4-0-0-download/)
lists 2025 and 30-minute data as available. The Chicago request is latitude
41.8781, longitude -87.6298, year 2025, `America/Chicago`, 30 minutes. It returns
17,520 records. The canonical weather CSV SHA-256 is
`e2e2e2a0f8c879497947e6722af08c5bb0749d70ff842cbe2a67f6021616c7e5`.

The [official PJM real-time hourly feed](https://dataminer2.pjm.com/feed/rt_hrl_lmps)
was queried in its public browser interface and exported using its CSV control,
without an API credential. Source window: January 1, 2025 00:00 through January 1,
2026 00:00 **Eastern Prevailing Time**, node 116472935. The original export has
8,761 rows; trimming by UTC to the Chicago calendar year selects exactly 8,760
hours. Current revision details are retained in private provenance. Raw file SHA-256:
`39825226ac8923b2be6ae862d04a39c5cfc157f7d8361fa89ad148a70ce4e209`.
Signed prices are preserved without clipping. This is the
final real-time hourly publication with current revision flags; it is not the
separate monthly settlements-verified feed or ComEd's estimated five-minute API.

[PJM's published access rules](https://www.pjm.com/markets-and-operations/etools/data-miner-2)
permit internal use and restrict redistribution. Raw prices and price-derived
schedules/results remain private local study data under this candidate; hosted
ComEd studies remain disabled pending permission and release review. No public
market-data download service is added. See also
[ComEd's API terms](https://hourlypricing.comed.com/comed-hourly-pricing-apis-terms-of-service/):
the public five-minute API is not used to build a permanent historical database
or substituted for final hourly billing prices.

## Reproduction and validation

Place the original PJM export at `pjm-residual-2025.csv` and its five-field source
metadata at `pjm-metadata.json` in a private ignored input folder. Then run:

```sh
/usr/local/bin/python3 tools/run_comed_year_validation.py \
  --historical-inputs .cache/comed_actual_2025_inputs \
  --output .cache/comed_actual_2025_validation
```

The tool reads only weather credentials from `src/.env`, retrieves/caches the
matching actual-year weather under a new immutable engine pin, and compares
grid-only, PV-only and PV plus battery through the independent worker. Existing
pins are never refreshed. A store with a different source revision rejects;
choose a fresh output directory. Private outputs include saved requests,
monthly/annual component tables, dispatch, weather/PV diagnostics, representative
OpenDSS replay, input hashes and a driver snapshot.

Load profiles remain **synthetic**: the same deterministic 3-kW residential and
60-kW office profiles as the earlier BES benchmark, now serialized and imported
through the native CSV path. They do not model weather-dependent HVAC or measured
Chicago consumption. PV/storage specifications also remain the same: residential
5/4 kW DC/AC PV and 13.5 kWh/5 kW storage; commercial 40/35 kW PV and 100 kWh/30 kW
storage. SOC 10–90%, charge/discharge efficiencies 95% each, initial and annual
terminal SOC 50%. BESH billed capacity obligations are explicitly hypothetical,
fixed at 2 kW residential and 40 kW commercial; current-year peak shaving does not
reduce them. Non-export ordinary accounts and calendar billing cycles are assumed.

The audit independently calculates hourly energy charges with Decimal arithmetic,
checks fixed capacity arithmetic, remeasures every monthly demand peak, verifies
line-item sums and cost-objective rounding bounds, and checks every interval's
power balance, SOC recursion, battery modes, limits and curtailment. March has 743
physical hours; November has 721. Representative balanced OpenDSS replay does not
establish site-specific circuit feasibility or dynamic response.

Results minimize filed **subtotals**, before final line-cent rounding, with
historical perfect foresight. Battery wear at $0.03 per charge-plus-discharge kWh
is reported separately and excluded from the chosen objective. State excise tax,
municipal taxes, franchise charges, export settlement, capital costs and
forecast-driven control remain outside scope. A failed optional cycling tie-break
retains the proven primary cost optimum and reports its warning; it does not prove
the least-wearing schedule among equal-cost optima.

Primary solve limits are 60 seconds for one cycle and 60 seconds per explicitly
linked cycle capped at 300 seconds. New cycling-refinement candidates use the
same bounded secondary budget and retain validated cost-neutral improvements;
the original validation below used a 60-second secondary limit. See
[ComEd cycling refinement](ComEd_Cycling_Refinement.md). The original 60-second annual commercial attempt was preserved as a
failed candidate. Increasing the compute budget does not accept an inaccurate or
unproven optimum, relax battery modes, or replace a year with monthly solves.

## Annual dispatch formulation

The real-price commercial case also failed to prove optimality with a 300-second
budget in the original all-interval binary formulation. The candidate therefore
uses an equivalent reduction, validated against a fully exclusive MILP oracle
for residential/commercial cases, positive/mixed/zero marginal prices and optional
wear costs. Mode selection uses total marginal costs after tariff adjustments,
which differ from the raw hourly market prices. Dataset-specific counts are
retained in the private validation artifacts.

At nonnegative marginal energy prices with nonnegative demand charges, a
simultaneous charging/discharging pair cannot improve the optimum: remove `x` kW
of charging and `eta_charge * eta_discharge * x` kW of discharge. SOC is unchanged.
Reduce grid imports by the conversion-loss difference, curtailing PV if imports
reach zero. The existing discharge limit at native load guarantees enough grid
plus PV supply to make that adjustment. Imports and every measured demand peak
can only fall; battery wear also falls. Therefore the original feasible exclusive
schedule is recovered without increasing any objective component. Negative
marginal intervals retain binary modes. If a future tariff has a negative demand
component, all intervals conservatively retain binaries.

Every returned schedule still passes exclusive-flow, power-balance and objective
checks; the annual audit also checks SOC transitions and all device limits.
Unproven primary solves remain errors. There is no monthly decomposition,
rounded SOC grid, relaxed exported power, omitted demand component, or weaker
optimality tolerance. This reduction applies only to the ComEd non-export model
with freely curtail-able PV and fixed positive efficiencies; it is not applied to
other utilities' export/settlement optimizers.

## Validated 2025 results

Final candidate engine: `b54356c031d2c8158cbfcbc35830d98679a68a8084bda5dbf15c2c5a8e22209b`.
Private validation store: `.cache/comed_actual_2025_equivalent`.
Driver snapshot SHA-256:
`812eb38425ab823215790e12f5ad911fad79b6a37467fab357c30dd4ff593bcc`.

Price-derived annual and monthly figures, demand measurements and schedules
are retained in the **private ignored** validation store, including
`validation-report.md`, `annual-comparison.csv`, `annual-components.csv` and
`monthly-components.csv`. They are not included in publishable repository docs
or enabled as public hosted downloads. Native consumption remains the shared
synthetic residential/office input, independent of prices.

Both primary cost optima are proven. Residential minimum-throughput refinement
also proved optimal; the optional commercial refinement timed out and retained
the proven primary optimum, with an explicit saved/browser warning. The reported
commercial wear is for that feasible schedule, not proven least wear at equal
cost. All 105,120 scenario intervals passed representative OpenDSS replay.
The audit checks power balance and SOC recursion at the specified tolerances.
Every monthly subtotal sums its line items, and bill/objective differences remain
within the declared rounding bounds. Exact audit measurements remain private.

An additional full-year residential run was submitted through the actual browser
controls after restoring both complete CSV inputs and matching cached weather.
It completed at the same three subtotals and preserved the input hashes.
Native CSV upload and official PJM CSV upload controls were inspected; an actual
1.2-MiB PJM file was loaded through the browser chooser. Saved settings retain
the full inputs and source metadata. Unsupported general strategy/orientation
controls stay hidden for ComEd; summary results distinguish physical interval
import peaks from commercial billed demand.

Final regression: **1,886 passed, 1 skipped**, using `/usr/local/bin/python3`.
The equivalence suite includes 12 comparisons with the all-binary oracle plus
direct SOC/power-preservation checks. Tests cover complete annual imports, DST,
missing/duplicate/naive/shifted records, revisions, wrong node/type/zone/market,
weather hash/year mismatch, browser request serialization, ownership/storage
boundaries and immutable worker execution. JavaScript syntax and `git diff
--check` passed. No live provider calls run inside tests.

Both failed all-interval-binary attempts remain in separate ignored stores;
their engine pins were not changed or presented as completed annual validation.
No files were staged, committed, pushed or deployed by this work. Concurrent
README changes were preserved.
