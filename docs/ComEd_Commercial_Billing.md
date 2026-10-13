# ComEd commercial billing and browser integration

Implemented October 12, 2026. The verified composite rate window is **September
and October 2026 billing months**, restricted to complete calendar-month study
cases. These are itemized subtotals, not complete utility bills. No actual
customer statement has yet been reconciled end to end.

## Supported commercial accounts

`src/billing/comed_commercial.py` provides `ComEdCommercialAccount`,
`build_comed_commercial_plans()` and `calculate_comed_commercial_bill()`.
Residential uses the existing independent adapter described in
[ComEd residential billing](ComEd_Residential_Billing.md).

| Delivery class | Required account basis |
|---|---|
| Watt-Hour | Confirmed legacy pre-2022 account, or separately metered EV charging service; secondary service only in this adapter |
| Small Load | Highest 30-minute demand in preceding 12 billing periods ≤100 kW |
| Medium Load | >100 through 400 kW |
| Large Load | >400 through 1,000 kW |
| Very Large Load | >1,000 through 10,000 kW |
| Extra Large Load | >10,000 kW |
| High Voltage | Single service point at or above 69 kV |

Demand classes support secondary or primary service, with primary transformer
charges only when the utility supplies transformation. High Voltage supports
one high-voltage service point; mixed-voltage allocations are not implemented.
The secondary adapter requires utility transformation to below 2.4 kV. No
new-account class is inferred from an incomplete demand history.

BES fixed-price supply is supported only for eligible accounts. Explicit utility
competitively declared status is required, and BES also rejects a previous year
with at least two months at or above 100 kW. The tariff includes utility judgment,
previous declarations and specific exceptions; the simulator does not issue an
eligibility determination. Ordinary accounts with no special exemptions are the
supported scope. Large established commercial customers generally need BESH or
a separately modeled supplier contract, not BES merely because a delivery rate
exists in the catalog.

Legacy Watt-Hour-only metering is conservatively rejected for BESH; its interval
supply eligibility cannot be inferred. Dedicated EV Watt-Hour delivery uses the
Demand supply subgroup. The electric space-heating subgroup must be confirmed
from the account and is distinct from the delivery class.

## Demand and billing arithmetic

Meter imports are average kW at timezone-aware interval starts. Commercial
requires complete 15- or 30-minute data; hourly values cannot establish a
30-minute peak. Fifteen-minute values are averaged into aligned, nonoverlapping
30-minute blocks. America/Chicago determines calendar boundaries and hours.

The model keeps four quantities distinct:

1. **Current billed MKD:** maximum 30-minute imports on weekdays 09:00–18:00,
   excluding NERC holidays (ratebook PDF page 174).
2. **Current overall peak:** maximum 30-minute imports across all hours,
   separately reported for inspection.
3. **Prior 12-month overall peak:** customer-supplied class assignment history;
   it does not create a demand ratchet on the current month.
4. **Prior 12-month maximum MKD:** separately required for High Voltage.
   The HV distribution/transformer tiers change only when this exceeds 10 MW.

The previous **calendar-year** overall peak separately determines RCA and
low-income-discount recovery: below 10 MW versus at least 10 MW. It must not be
substituted with the rolling 12-month peak or current MKD. BESH capacity uses a
separately documented billed capacity obligation, never one of these peaks.

All monetary literals are dollars. Each delivery adjustment contribution is
rounded independently before adding it to the base price. Commercial classes
use their own IDUF, RBAF and DGRA; High Voltage DFC/TC omit DGRA per sheet 64.17.
The commercial energy-efficiency rider is also class-specific. Signed credits
and negative residual hourly LMPs are preserved.

| BES supply component, $/kWh | September 2026 | October 2026 |
|---|---:|---:|
| Legacy Watt-Hour, non-electric heat | 0.08704 | 0.08433 |
| Demand, non-electric heat | 0.08813 | 0.08470 |
| Nonresidential electric space heat | 0.07649 | 0.08111 |
| Transmission | 0.01704 | 0.01672 |

BESH uses the same verified system-average hourly energy factors, capacity,
transmission, miscellaneous procurement and monthly supply adjustments documented
in the residential adapter. Commercial delivery charges remain separate.
Commercial versions have their own identifiers and supply fields.

Independent September benchmark: Small Load, secondary, 20 kW constant imports,
14,400 kWh, 40 kW historical peaks, no competitive declaration: **$1,811.04
subtotal**. Of this, $258.00 is distribution demand (20 kW × $12.90/kW). This is
a synthetic arithmetic fixture, not a measured commercial building or bill.

## Browser workflow

The [main simulation integration](ComEd_Simulation_Integration.md) additionally
connects these subtotals to native load, shared PV/inverter/ESS configuration,
physical non-export optimization and scenario comparisons in the existing setup
wizard. The standalone workflow below remains a schema-9 tariff-checking tool.

The main browser links to `/comed.html` when its pinned engine advertises the
ComEd capability. The form offers residential/commercial classes, BES/BESH,
billing month, account eligibility, interval CSV or explicitly synthetic constant
imports, and BESH hourly prices/capacity. No API key is needed for local CSV
replay. Actual historical price retrieval is not part of this change.

Start the development preview from the repository using its working Python:

```sh
/usr/local/bin/python3 -m src.local_web.server --port 8878 --data-dir .cache/comed_preview --refresh-engine
```

Open `http://127.0.0.1:8878/comed.html`. Omit `--refresh-engine` when reusing the
same snapshot. This data directory is separate from existing browser releases.
An old pinned engine hides the navigation and rejects ComEd submissions.

- Meter CSV: `timestamp,grid_import_kw`; no inferred scaling or net-export data.
- BESH price CSV: `timestamp,residual_lmp_usd_per_mwh`; one value per physical
  hour, with the explicitly confirmed PJM real-time residual ComEd-zone basis.
- Timestamps require ISO dates/times plus `Z` or an explicit UTC offset.
  `T` and a space separator are accepted. Missing/duplicate/out-of-order data
  are rejected. Each file is bounded to 2 MiB and 4,000 rows.
- POST `/api/v1/comed/studies` uses schema 9 and the shared CSRF-protected local
  queue. Execution uses the existing isolated, immutable engine worker.
- Results show charges/credits, subtotal, energy, and both commercial peak
  measures. They can be named/saved and opened in the shared table/download
  viewer. The meter table is exported in UTC, preserving instants.
- Requests retain supplied source references and price data locally. Only
  aggregate price-derived charges are table exports. Hosted study execution
  and access remain disabled for this initial local integration.

## Explicit exclusions

No state electricity excise tax, municipal utility tax or franchise charge is
calculated. Illinois Electricity **Distribution** Tax is included. Every result
has `total_usd=None`, `is_complete_bill=False` and named excluded components.

No mixed-voltage/multi-meter accounts, tax or efficiency opt-outs, special
contracts, discount programs, lighting, railroads, alternative supplier bills,
BEST/distribution-TOU service, solar export/net metering, battery dispatch,
OpenDSS validation or cross-month meter cycles are modeled by this standalone
adapter. The main simulation candidate separately supports bounded non-export
dispatch and representative secondary-service replay, with explicit eligibility
assumptions and incomplete-subtotal labels.
Periods outside September–October 2026 fail rather than reusing current rates.

## Evidence and verification

[Official ComEd 2026 ratebook](https://www.comed.com/cdn/assets/v3/assets/blt3ebb3fed6084be2a/blt86ebee5fe6ed02f8/6ab16afb15d5b73190b00e59/2026_Ratebook.pdf?branch=prod_alias):
base commercial prices pp850/852/854; class definitions pp181–185; MKD p174;
supply pp782–788; riders pp790/799/801/821/824/839/845/864–866/876.
The full-source hash and retained commercial text excerpts are in
`docs/utility_sources/comed/manifest.json`. References are original one-based
PDF page numbers, not excerpt page positions. The official delivery guide
verifies the component-rounding method; its January prices are not reused.

The [PJM 2026 business calendar](https://www.pjm.com/-/media/DotCom/markets-ops/settlements/2026-business-calendar.pdf)
corroborates NERC holidays. Tests explicitly distinguish Labor Day from
Columbus Day and exclude nights/weekends from MKD.

Tests cover independently transcribed charge amounts, delivery boundaries,
primary/HV transformation, hourly negative-price and capacity handling,
eligibility rejection, CSV parity, real HTTP → pinned worker → saved-table
execution, and existing residential regression cases. Browser rendering and
interactions were checked in desktop and narrow mobile layouts with Chrome.
