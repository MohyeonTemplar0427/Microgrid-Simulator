# Ameren Illinois DS-1 and standard DS-2

The shared local-browser study supports **DS-1 residential / BGS-1** and
**standard DS-2 small commercial / BGS-2**, with verified monthly rate coverage
**January 2025–October 2026**. Both use ordinary secondary-side metering and
the **non-interval, non-lighting Rider TS billing classification**. Native
15-minute simulation inputs do not establish that retail classification.
All three utility-assigned Rate Zones I, II and III are supported; the account
must identify its actual zone. This is Ameren **Illinois**, not Ameren Missouri.

## Scope and account confirmation

Confirm distribution utility, Illinois jurisdiction, Ameren BGS retail supplier,
ordinary tariff eligibility, retail TS classification and Rate Zone separately
from geographic coordinates. The supplied unincorporated Sangamon County site
and Rate Zone II account are **hypothetical assumptions**, not a territory
finding. State, nearest market node and MISO zone cannot establish eligibility.

DS-1 covers an ordinary individually metered residential account. Standard
DS-2 is secondary service up to 600 V and requires historical eligibility for
DS-2/BGS-2. The tariff describes demand below 150 kW, historical reclassification
and, for accounts without demand metering, a 1,200-kWh/day criterion. The
implementation conservatively constrains every commercial simulated import below
150 kW and still requires independent historical eligibility confirmation.
It does not predict future utility reclassification or support the optional
DS-2 demand path for reassigned DS-3 customers.

Ordinary service only: no ARES/municipal aggregation, PSP/RTP hourly supply,
self-directed renewable/EE arrangements, exemptions, utility DER rebates,
discounts, special facilities or transformation adjustments. Municipal tax,
excess franchise (EF), government compliance (GC) and infrastructure maintenance
(IMF) additions are unsupported; absence requires independent confirmation.
The ordinary state electricity excise and EDT recovery are included. Secondary
240-V single phase (split-phase residential) and 480-V three-phase commercial
are supported by the representative electrical replay. No primary-side metering
or custom power-factor billing adjustment is inferred.

## Components and dates

The [source manifest](utility_sources/ameren_il/manifest.json) retains official
URLs, original PDF hashes, selected page numbers and extracted-text hashes.
The Python runtime tables are included in immutable engine snapshots; research
PDFs remain in ignored cache. Image-only PBR-R tables were visually reviewed;
their [reviewed transcription](utility_sources/ameren_il/reviewed-tables.md)
records the 2025/2026 columns. Earlier published 2026 projections superseded by
the August 28, 2025 appendix are not used.

| Component | Calculation |
|---|---|
| Customer and meter | Applicable-year PBR-R appendix, full monthly amount |
| Distribution | Summer June–September flat kWh; winter first 800 kWh DS-1 or 2,000 kWh DS-2, then lower tail rate |
| BGS supply | Monthly official informational sheets; DS-1 winter first 800/tail block; standard secondary BGS-2 flat kWh |
| PEA and supply adjustments | Actual monthly PEA, non-EUA SCA and supply EUA; EUA is not counted twice |
| Transmission | Dated non-interval TS cents/kWh, separate from BGS once |
| Supplemental customer | Renewable/coal assistance, BEAC, UCB/POR and $0.04 DS-1 PSP program recovery; PSP enrollment is not assumed |
| Delivery EUA | Dated fixed charge/credit, separate from uncollectibles already included in base rates |
| MAP-R, PBR-R AAF, RBA and EDITA | Each independently multiplies customer + meter + distribution + EDT; excludes supplemental charges and other riders; no compounding |
| EEA | Monthly actual service-rate Zone I/III values; not applicable in Zone II |
| HMAC | Filed zero for Zone III in 2025 and 2026; not applicable elsewhere |
| CEAC, REA, EE, USS, ETAC, CSESC | Dated mandatory volumetric riders |
| CGC | Dated fixed customer-generation recovery applies to **all accounts**, including grid-only |
| State electricity excise | Filed declining kWh tax blocks; separate from EDT, not a percentage of total charges |

BGS already recovers generation capacity. No MISO auction capacity, PLC or
wholesale LMP is added. Rider TS separately recovers the listed transmission
schedules. An **interval-billed TS account** needs its company-system-peak
determinants and different $/kW-day calculation; this adapter rejects it.

Standard DS-1/DS-2 have **no intraday TOU pricing or measured demand charge**.
Weekends and holidays therefore have the same seasonal energy-block rules.
The hourly PSP/RTP programs and optional DS-2 demand rates are separate future
work, not approximated using MISO prices or a generic holiday calendar.

## Billing-cycle boundary

The first scope accepts **complete calendar-month cycles**, with a matching
designated billing month and bill date at the final service day. Each year may
contain twelve explicitly hypothetical calendar cycles. No claim is made that
these are a customer's real meter-reading schedule.

RPEC/non-EUA supply adjustments use calendar dates, while multiple other riders
use designated billing months. Limiting this first adapter to matching complete
months avoids inventing cross-month declining-block allocation or proration.
Partial, initial, final, rerouted and crossing-month cycles are rejected. The
Customer Terms specify special proration and a 24–40-day regular-cycle range;
those statements alone do not supply a complete allocation implementation.

Timestamps use **America/Chicago**, consecutive 15/30-minute elapsed-time
averages. March/November DST hours are handled explicitly. Missing, duplicated
or shifted intervals fail validation. Other regional utilities retain their
existing Eastern-time defaults. Each item is retained unrounded and rounded
half-up to cents for the study bill; the rounding bound is reported.

## PV, storage and grid configuration

Grid-only, PV-only and PV-plus-battery use identical native consumption, weather,
tariff and recurring obligations. Approved non-export renewable PV/storage and
continued BGS eligibility require explicit evidence. Non-export operation alone
does not grant interconnection approval. The conservative first implementation
limits aggregate PV nameplate plus battery discharge rating to 50 kW; that is a
model boundary, not a statutory maximum. Standalone storage is unsupported.

Exports, opening credits and carried credit state must be zero. No legacy NMOS
netting, generation credits, export compensation, annual true-up, rebate-driven
hourly enrollment or capital/interconnection costs are modeled. NMOS's approved
on-site generation path is separate from PRSS, which the Customer Terms define
as partial utility/retail-supplier supply. Export settlement remains future work.

MISO, resource-adequacy **LRZ4**, transmission owner **Ameren Illinois**, retail
Rate Zone and optional wholesale cpnode are distinct metadata. LRZ4 is not a
pricing node. No node/hub, wholesale price, CAISO carbon or Illinois-wide utility
assignment is silently substituted.

Dispatch minimizes the authoritative unrounded bill, optionally including battery
degradation. Exact filled declining blocks are used in the numeric bill and
optimization, including state tax. A later cycle inherits physical SOC; these
are historical per-cycle perfect-foresight decisions, not an annual optimum or
a deployable next-day controller. All three schedules undergo shared OpenDSS
quasi-static replay at every 15-minute interval, preserving curtailment, absent
equipment and SOC semantics. Representative circuits are assumptions; PCC replay
losses/flows do not change retail billing or constrain the optimizer.

## Validation

Focused tests cover independent Decimal component benchmarks for both plans in
2025/2026, declining-block boundaries, negative PEA, monthly supply and rider
changes, all Rate Zones, Central-time DST, rejected unsupported accounts/dates,
unchanged grid-only CGC, bill/dispatch reconciliation and browser-form-to-worker
save/restore/CSV/ZIP/electrical checks. These are tariff arithmetic benchmarks,
not calibration against a real customer statement. The tariff's illustrative
bill forms are not used as authoritative substitutes for dated monthly PEA.

Frozen backend engine:
`ea4a8f130f39b47b995b4707508d506845fc27a46a6af55568796279efa92d5e`.
Private reproducible matrices are `.cache/ameren_il_validation_2025/` and
`.cache/ameren_il_validation_2026/`. Both plans passed full-year 2025 and
January–September 2026: four studies, twelve scenarios, 126 cycle bills and
367,464 checked electrical intervals, with zero failed intervals. Every dispatch
cost optimum was proven (or direct grid-only billing); all 42 battery-cycle
minimum-cycling results were proven. Maximum bill/objective difference was
approximately $0.000001. These are not proof of an annual joint optimum.

| Plan | Period | Grid only | PV only | PV + battery |
|---|---|---:|---:|---:|
| DS-1 | Full-year 2025 | $2,422.26 | $1,731.08 | $1,449.88 |
| DS-2 standard | Full-year 2025 | $16,692.05 | $14,240.95 | $14,237.96 |
| DS-1 | Jan–Sep 2026 | $1,933.62 | $1,352.90 | $1,123.78 |
| DS-2 standard | Jan–Sep 2026 | $13,330.91 | $11,327.66 | $11,325.59 |

These are utility bills, with battery wear reported separately. Native loads
are synthetic generic household/office profiles, serialized and re-imported
through the exact interval CSV contract, not measured customer data. Actual
ERA5 hourly historical weather is matched to year and site (39.75, -89.70).
Residential uses a 3-kW peak profile (13,887.54 kWh in 2025), 5-kW DC/4-kW AC
PV and a 10-kWh/3-kW battery. Commercial uses a 25-kW peak profile (99,847.77
kWh in 2025), 10-kW DC/8-kW AC PV and a 30-kWh/8-kW battery. Both have 20–80%
SOC bounds, 95% charge/discharge efficiency and starting/final SOC of 50%.
PV faces south at 30°, with 14% system losses and 96% inverter efficiency.

The small incremental commercial storage saving is expected: standard DS-2
has no demand charge or intraday price spread, and this daytime facility
consumes almost all available PV directly. No generalized battery-payback claim
is supported by these operation-only results.

GUI development/testing is excluded under repository policy. Stable engine
promotion, public deployment, staging, committing and pushing are not part of
this change.

Final regression: **3,281 passed, 1 skipped**, seven JavaScript syntax checks.
After a frontend error-message copy correction (backend unchanged), **106 focused
tests passed without warnings**, and one browser acceptance pass verified the
restored inputs, exact submitted request, three rendered bills/electrical rows,
save/reopen and ZIP artifacts. Detailed pins, timing, warnings, reproducible
commands and preview are in the [integration handoff](Ameren_Illinois_Integration_Handoff_20261020.md).
