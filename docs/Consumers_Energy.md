# Consumers Energy Michigan · bounded full-service integration

The local-browser regional workflow supports residential **RSP** (summer TOU),
**RSH** (Smart Hours, year-round TOU), commercial secondary **GS**, and **GSTU**
(commercial TOU). Verified service and designated billing-month coverage is
**January 1, 2025–June 30, 2026**. Later actual billed PSCR factors are absent
from the downloaded MPSC snapshot and are rejected, even where a maximum
allowable factor or current base rate exists. No provisional rates are used.

## Account, region and equipment

Choose Consumers Energy as both distribution utility and full-service retail
supplier, Michigan jurisdiction, and the actual tariff independently of the map.
A hypothetical Grand Rapids-area site is a study assumption, not an address or
service-territory finding. MISO, LRZ7 resource adequacy, METC transmission owner,
and optional explicitly sourced wholesale cpnode are separate metadata. LRZ7 is
not a price node. No MISO price/carbon retrieval, CAISO substitute, wholesale
capacity, transmission-tag or PLC surcharge is added to the bundled retail bill.

Ordinary secondary-side metered service only: no retail choice, resale,
educational/senior/low-income credits, self-directed EE, special minimums,
non-transmitting meters, DR/critical events, standby/SG, special facilities,
franchise/locality additions or tax exemptions. These account exclusions require
explicit confirmation. RSH/GSTU require confirmed TOU enrollment and supporting
metering/infrastructure. Residential eligibility and approved individual/total
connected equipment must be checked against D-14/D-36; this is not a hyperscale
commercial tariff model.

The three returned scenarios are grid-only, PV-only and PV-plus-battery.
PV/storage requires independently approved **C11.3 DG**, annual sizing and storage
arrangement, with a conservative implementation limit of PV nameplate (larger of
DC/AC) plus battery discharge rating **≤20 kW**. This bound keeps the case inside
the historical small-DG scope; it is not the current statutory maximum. Before
March 14, 2025 the eligible generator annual output limit was 100% of historic
annual consumption; the revised definition permits 110%. Approval evidence must
cover the actual study period; eligibility is never inferred from non-export
operation alone. The first version accepts zero exports and zero opening credits
only; it does not claim to implement Consumers DG export settlement or legacy
NEM. Standalone storage is unsupported. No new capital/interconnection charges
are included in recurring utility bills.

## Rates, clocks and calendars

The runtime rate tables are Python literals retained in immutable engine
snapshots. The [source manifest](utility_sources/consumers/manifest.json) includes
URLs, PDF hashes, one-based selected pages and extracted-text hashes. Full PDFs
remain in ignored research cache. Primary sources are the [MPSC current and
canceled books](https://www.michigan.gov/mpsc/consumer/electricity/data-price/electric-rate-books/mpsc-approved-consumers-energy-electric-rate-books-and-cancelled-sheets).

| Component | Applicable clock or rule |
|---|---|
| Non-capacity energy, capacity, distribution | Interval local service date; base changes April 4, 2025 and May 1, 2026 |
| Demand-response surcharge, IRM, FCM, deferral | Explicit service-date windows; ended surcharges become zero, never carried forward |
| Actual PSCR | Utility-designated billing month; actual billed column, not authorized maximum |
| EE, power-plant and Karn securitization, LIEAF | Utility-designated billing month |
| Refund and IRM reconciliation | One-time February 2025 and May 2026 bill-month amounts, respectively |
| Residential season | Actual calendar date: June 1–September 30 summer |
| GS/GSTU season | Designated utility billing month: June–September summer |
| Michigan sales tax | Ordinary residential 4%, commercial 6%; LIEAF excluded under Treasury ruling 2013-5 |

RSP has weekday 14:00–19:00 peak in summer and flat winter pricing. RSH uses
weekday 14:00–19:00 peak all year. **Both include weekday holidays.** GSTU summer
weekdays have off-peak 23:00–07:00, mid-peak 07:00–14:00 and 18:00–23:00, and
peak 14:00–18:00. GSTU winter weekdays have peak 07:00–23:00. GSTU weekends and
six actual holidays are off-peak: January 1, Memorial Day, July 4, Labor Day,
Thanksgiving and December 25. **No Friday/Monday observed substitute** is added.
These rules are Consumers-specific, not the DTE or PJM holiday calendar.

**Commercial EE is a utility-assigned tier (1–10), not a current-month usage
fee.** D-2.10 describes a January annual review and possible subsequent
reclassification based on the previous year's average consumption; absent
history the utility uses the lowest applicable category. The account must supply
the assigned tier and evidence/effective period. Explicit cycle overrides may
represent documented reclassification. The simulator does not automatically
predict a future utility tier from present PV/storage dispatch. Hypothetical
commercial defaults explicitly hold tier 3 constant across scenarios.

RSP/RSH/GS/GSTU have no measured demand charge. The `demand_response` component
is a per-kWh surcharge, not a peak-kW fee. GSD and primary-voltage plans remain
unsupported; do not infer their rules from these GS/GSTU bills.

## Cycles and arithmetic boundary

Support is bounded to complete **26–35-day regular monthly meter cycles**, with
full monthly system-access and assigned non-consumption charges confirmed.
This is an implementation guard, not a claimed universal Consumers proration
rule. Partial, initial and final cycles are rejected. A cycle crossing a service
rate change allocates actual interval energy to dated rates; commercial season
and rendered riders still use its utility-designated billing month. The first
scope requires that designation to match the bill-rendered calendar month.
Hypothetical calendar cycles must remain explicitly labeled; an actual meter
schedule is never inferred from them.

All intervals are explicit Eastern time, consecutive 15/30-minute averages in
elapsed time, including repeated/missing local DST clock hours. No interpolation
or missing-data fill. Line components retain unrounded arithmetic and are
individually half-up rounded to cents for the study bill. No customer-statement
calibration claim is made.

## Dispatch, physical replay and reproducibility

The existing regional optimizer uses this same complete numeric/expression bill,
including taxes and every applicable rider. Assigned fixed fees are constants.
Default objective excludes battery wear; estimated wear remains separately
reported. Historical optimization has per-cycle perfect foresight and continuous
SOC between cycles, with study-end SOC restored; it is not an annual joint
optimum or a causal/forecast controller. PV is curtailed as necessary for the
explicit non-export contract.

OpenDSS checks every 15-minute interval of all three scenarios after dispatch,
using actual curtailed PV and storage flows. Residential circuit: representative
25-kVA, 100-A, 120/240-V split-phase. Commercial: existing balanced 480-V,
750-kVA reference, or supported single-phase reference when selected. These are
not Consumers service specifications or surveyed circuits. Voltage/loading,
convergence and losses are reported; PCC replay/losses do not change scheduled
retail billing. No dynamic validation or network-constrained optimization.

```sh
/usr/local/bin/python3 tools/validate.py --tier focused --area regional --area validation --timeout 600
/usr/local/bin/python3 tools/run_regional_validation.py --prepare-inputs --utility consumers_energy --inputs .cache/consumers_historical_inputs --env-file /dev/null
/usr/local/bin/python3 tools/run_regional_validation.py --execute --utility consumers_energy --period annual --inputs .cache/consumers_historical_inputs --output .cache/consumers_annual_repeat
/usr/local/bin/python3 tools/run_regional_validation.py --execute --utility consumers_energy --period custom --start-date 2026-01-01 --end-date 2026-06-30 --inputs .cache/consumers_historical_inputs_2026 --output .cache/consumers_2026_repeat
```

For 2026 preparation use the existing explicit provider functions:
`fetch_era5('2026-01-01','2026-06-30',42.96,-85.67)` then `parse_era5` on the exact
study grid; retain the returned request/retrieval metadata and raw source bytes
under `consumers_energy/era5.json` in a new private input folder. Do not shift
2025 weather into 2026. The standard preparation command prepares 2025 only.

Prepared weather and simulation artifacts stay in ignored `.cache`. ERA5 is
hourly reanalysis with explicit interval conversion, not a local measurement at
15-minute resolution. Native household/office profiles are deterministic generic
synthetic assumptions, not measured load or Michigan population averages.
Browser acceptance follows the frozen-candidate policy in
[Development Validation](Development_Validation.md); desktop GUI tests are opt-in
and GUI development remains paused. Stable engine promotion, commits, pushes
and public deployment require separate authorization.
