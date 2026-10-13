# ComEd main simulation integration — October 12, 2026 candidate

ComEd is now selectable in the **main location/customer → service → dates →
PV/inverter/weather → ESS → Economics → review/results workflow**. The separate
`/comed.html` calculator and schema-9 meter-bill studies remain supported. The
new schema-10 adapter is a local development candidate; Web UI v1.0.1 and
existing immutable engine pins are retained, with no release promotion.

## Account and supported dates

Distribution utility ComEd, Illinois jurisdiction, ComEd retail supply, PJM
operator/COMED transmission zone and the BESH wholesale-price contract are
separate fields. The current territory resolver covers California, so ComEd
is an explicitly **manual** service option. It is never assigned from Illinois,
Chicago, ZIP codes, coordinates or a pricing node. The user supplies bill/utility
evidence or selects a clearly hypothetical case. This confirmation records
evidence; it does not authenticate a bill or issue a utility eligibility ruling.

Residential and commercial classes, heating subgroups, voltage, transformer
ownership, competitive-supply eligibility and capacity obligations retain the
existing authoritative adapter checks. Complete **September or October 2026
calendar months** only, with America/Chicago boundaries. Residential intervals
may be 15/30/60 minutes; commercial intervals must be 15/30 minutes. No hourly
demand reconstruction, actual cross-month meter-cycle proration, neighboring
rate substitution or historical-year shifting is introduced.

Current billed MKD is the maximum aligned 30-minute weekday 09:00–18:00
import, excluding NERC holidays. Fifteen-minute pairs are averaged before
measuring it. Current all-hours/interval peaks are reported separately. Prior
12-month overall classification peak, prior HV MKD, previous-calendar-year
peak/month-count rider history and BESH capacity remain fixed across scenarios.
Current optimized demand never reclassifies the account or reduces its capacity
obligation. Future-obligation modeling remains unsupported.

## Meter projection and non-export contract

The original calculators accept ordinary meter **imports**, rather than
generation/export settlement. Schema 10 explicitly projects native building
demand through an approved or hypothetical **non-export** installation, then
passes each resulting nonnegative import Series to those same calculators.

PV/storage requires separate confirmations of interconnection/non-export
operation, continued applicability of the ordinary tariff without DER rebate,
standby or other special charges, and permitted grid charging for storage.
The approval or hypothetical assumption reference is saved. An equipment
configuration does not prove actual account eligibility or interconnection
compliance. Net metering, export compensation, generation rebates, special DER
charges and controller/protection design are not calculated. Those account
arrangements remain unsupported, rather than receiving invented credits.

Native input choices reuse `ConstantLoad`, `SyntheticLoad` and `CSVLoad`.
Generic synthetic archetypes are explicitly assumptions, not calibrated
Illinois residential/commercial profiles or California retail schedules.
Native CSVs require `timestamp,native_load_kw`, timezone-aware starts matching
the exact study grid, a source reference and confirmation of native consumption
**before** PV/battery. Utility purchases from a site already containing PV or
storage cannot silently become native demand. No scaling, interpolation, gap
filling or resampling is performed. Files are limited to 2 MiB/4,000 rows.

PV uses the same `build_site_generation` weather/PV physics and the main form's
DC rating, inverter AC rating/efficiency, orientation and losses. The shared
weather/PV helper is independent of retail price and carbon mapping. Current
NSRDB years end in 2025 and do not overlap this 2026 tariff window; the initial
main workflow therefore supports explicitly labeled **clear-sky** studies.
There is no shifted historical weather, CAISO carbon assignment or emissions
claim. Historical 2026 weather is remaining work.

ESS uses the existing `Battery` model and optional reviewed equipment catalog
resolution. A `None` battery represents actual absent storage; the browser can
disable it or accept zero capacity. Zero PV is supported, including storage-only
studies. OpenDSS now supports replay without creating a fictitious battery.

## Authoritative costs and physical optimization

`src/billing/comed_costs.py` compiles fixed, energy and demand expressions from
the **validated charge lines produced by the existing calculators**. No filed
rate, delivery-factor rounding, commercial threshold or rider arithmetic is
duplicated. BES never receives additional wholesale/capacity/procurement costs.
BESH validates explicitly identified COMED real-time residual hourly LMPs in
USD/MWh, maps them by physical UTC hour, and applies the filed HEC multiplier
once. Filed capacity/procurement/transmission amounts are not multiplied again.

Supply data may be a clearly synthetic assumption or an identified hourly CSV
with source/basis confirmation. Source declarations do not authenticate a
dataset. Actual historical-price retrieval is not implemented. Raw prices stay
in local saved inputs; hosted schema-10 submission and result/request access
are blocked pending market-data permission and candidate release review.

`src/dispatch/comed.py` uses SciPy HiGHS through CVXPY. Non-export balance is
`grid + PV + discharge = native load + charge`. PV output is bounded by its
available AC power; all curtailed energy is reported. Battery mode is binary:
charging and discharging cannot occur together, including at negative prices.
Discharge is bounded by native load as well as inverter rating, tightening the
non-export feasible set. SOC limits, both efficiencies and charge/discharge
power are retained. Terminal energy equals initial energy; energy cannot be
dumped into a fictitious export or sink to earn negative-price payments.

Real cycling at distinct intervals may still be economically beneficial at
negative prices and has physical conversion losses. Optional wear can penalize
that behavior. Wear is excluded from the default subtotal-minimizing objective
and reported separately. PV-only operation also minimizes its subtotal; at
negative marginal prices it may economically curtail PV. Consequently storage
savings compare against **optimized PV without storage**, rather than assigning
all curtailment-control benefits to the battery.

The model is historical perfect foresight, not a forecast-driven controller.
Each solve and throughput tie-break has a 60-second limit. An unproven optimum
or failed physical/billing reconciliation rejects the case; a relaxed schedule
is never substituted. Long, strongly negative-price blocks can be difficult for
the MILP. Faster solve policies/operational controllers remain future work.

The objective is the filed subtotal **before final line-cent rounding**, plus
wear when selected. Every completed schedule is recalculated by the Decimal
bill calculator. Result columns report unrounded objective, recalculated
objective, solver residual, cent-rounding difference and a worst-case bound of
$0.005 per variable charge line. This does not claim the exact minimum of a
discontinuous cent-rounded invoice. Fixed cent-rounded account charges remain
in both expressions and all reported subtotals.

## Results and feasibility

Grid-only, PV-only and PV plus storage share dates, native loads, account
history, tariff version and BESH obligations. Results contain itemized signed
charges/credits, subtotal savings by component, imports, peaks, curtailment,
storage operation, terminal energy and reconciliation. `total_usd=None` and
`is_complete_bill=False` are retained: state excise tax, municipal taxes and
franchise fees remain excluded. Illinois distribution tax is included.

Secondary service is replayed on the existing balanced representative
12.47 kV/480 V circuit and 750 kVA transformer, with assumed load PF 0.95 and
inverter kVA equal to AC kW, Q=0. Circuit limits and setpoint tracking are checked
per interval. Network losses are reported rather than fed back into the
ideal-meter cost optimizer. Primary/high-voltage accounts retain retail
calculations but explicitly have **no applicable AC replay**. No results imply
site-specific, unbalanced, protection, transient or islanding validation.

## Candidate operation and acceptance

```sh
/usr/local/bin/python3 -m src.local_web.server --port 19013 --data-dir .cache/comed_simulation_preview --refresh-engine
# Reuse that immutable pin on subsequent starts: omit --refresh-engine.
```

Open **http://127.0.0.1:19013/**, choose customer type/location, then manually
select ComEd and provide the account basis. Use the main PV/inverter/weather/ESS
controls and select ComEd BES/BESH in Economics. Review native load before
running. Naming, saving, loading settings and CSV/ZIP downloads use the existing
results interface. Schema 10 uses `POST /api/v1/comed/simulations`; schema 9
remains at `POST /api/v1/comed/studies`. A pin lacking the new capability cannot
accept or advertise ComEd simulations. Both modern desktop and browser use this
shared local service. Promotion follows `Local_Web_Application.md` explicitly.

Initial baseline: **1,687 passed, 1 skipped**. Validation includes independent
existing bill benchmarks, BES/BESH cost reconciliation for both customer types,
MKD/holiday/quarter-hour handling, transformer/HV history, demand shaving,
hourly negative-price arbitrage, zero-load dissipation rejection, physical and
terminal-SOC checks, zero equipment, source/date/account rejection, production
form-to-pinned-worker tests, ownership/hosted restrictions, saving and downloads.

No staging, commit, push, deployment or stable-release replacement is authorized
by this implementation. Existing uncommitted ComEd billing and browser work is
preserved; the two original authoritative bill calculators and rate file remain
unchanged. Generated CSVs, study files and screenshots stay under ignored cache.

### Final verification and reviewed cases

Final `/usr/local/bin/python3 -m pytest -q`: **1,714 passed, 1 skipped**.
`node --check` passed for `app.js` and `comed_simulation.js`; `git diff --check`
passed. The California capability contract remains unchanged, with regional
adapters advertised separately. Source-preservation checks confirmed the
original ComEd rates, both bill calculators, standalone HTML/JS, CSS and three
existing ComEd test files retain their original bytes.

Candidate pin: `6435c025b3ed146d7dc61656505b4d90c188219b1200d438260fbe447472b2a9`.
It matches all current checkout Python files. Stable preview pointers were not
modified, including `.cache/san_diego_preview/` and `.cache/comed_preview/`.

Actual **main-wizard** browser acceptance covered residential/commercial
selection, manual ComEd confirmation, delivery class, BES/BESH selection,
shared PV/inverter/ESS controls, interval/price-file uploads, execution,
comparison, naming after completion, saved-setting restoration and ZIP download.
The downloaded ZIP passed integrity checks. Leaving ComEd was checked to restore
the ordinary shared battery/weather controls. All four original browser requests
were replayed on the final pin and produced identical comparison tables.

These are hypothetical September 2026 studies, not measured bills or tariff
recommendations:

| Case | Grid subtotal | PV subtotal | PV + storage subtotal | Final pinned study |
|---|---:|---:|---:|---|
| Residential BES | $137.45 | $87.55 | $59.82 | `d55d7a7baefd4f99a3d5ad3b24136ff0` |
| Residential BESH, synthetic hourly CSV | $147.46 | $108.61 | $48.64 | `409a70dd237a40dba8afdc3123dcbd84` |
| Commercial BES, synthetic native CSV | $2,057.88 | $1,324.26 | $1,277.18 | `3c1999c41c2a45d8aaf2483ffc6e801d` |
| Commercial BESH, synthetic $50/MWh | $1,653.62 | $1,096.46 | $1,052.25 | `963e468e500d47138d0b5a896e275f2a` |

All use 30-minute intervals, tilt 20°, azimuth 180°, 14% PV system losses,
96% nominal inverter efficiency, clear-sky irradiance, assumed 20°C/1 m/s
meteorology, and a 10 kWh/3 kW AC-side battery with SOC 0.2–0.8, initial/final
5 kWh and 0.95/0.95 efficiencies. Wear is estimated at $0.03/kWh throughput
and excluded from the optimization objective.

Residential native load is constant 1 kW (720 kWh); delivery class is single
family without electric heat; PV is 5 kW DC/4 kW AC. The BESH hourly fixture is
explicitly synthetic: -$120/MWh at 03:00, $250/MWh at 17:00–22:00, otherwise
$30/MWh. It is not observed ComEd/PJM data.

Commercial native CSV has 8 kW outside weekday 09:00–18:00, 36 kW in that
window and 60 kW at 15:00–16:00, totaling 11,832 kWh. The Small Load secondary
account assumes utility transformation, no heating subgroup or competitive
declaration, prior 12-month/previous-calendar-year peaks of 40 kW and zero
previous-year months >=100 kW. PV is 40 kW DC/35 kW AC. Current billed MKD
changes 60 → 43.0955 → 40.0955 kW; the optimized all-hours peak is separately
40.6439 kW. Both BESH cases retain a **synthetic fixed 2 kW capacity obligation**
and its $20.20 charge across every scenario.

Every scenario passed all 1,440 representative AC replay intervals. A further
actual browser restore/re-submit on the final pin is saved as
`63a9afd834d34244bb0de7f75b628fda` (“ComEd commercial BESH · final browser
validation”), with the same commercial results. These checks validate the
bounded software path and independent tariff arithmetic, not an actual customer
invoice or installation. Remaining limits are those above: taxes/franchise,
export/DER settlement, real meter cycles, verified historical rate expansion,
actual hourly-price acquisition/permissions, historical 2026 weather, faster
hard-negative-price solves, operational forecasting and site-specific circuits.
