# DTE Electric Michigan · bundled residential and commercial bills

Local-browser schema 11 uses the shared regional worker, PV/inverter and ESS
models, authoritative retail bill expressions, CSV/ZIP results and OpenDSS
replay. Desktop GUI work remains paused. No engine promotion or deployment is
part of this addition.

## Supported accounts and dates

| Schedule | Scope | Verified service dates | Peak energy period |
|---|---|---|---|
| D1.11 | Single/double occupancy residential, 120/240 V split phase | January 1, 2025–September 30, 2026 | Monday–Friday 3–7 p.m. |
| D3 | Ordinary commercial secondary service, ≤1000 kW | January 1, 2025–September 30, 2026 | Flat energy |
| D3.11 | Ordinary commercial TOU secondary service, ≤1000 kW, confirmed enrollment and 12-month commitment | June 1, 2025–September 30, 2026 | Monday–Friday 1–5 p.m. |

Summer is June–September. Weekday holidays keep these peak periods: C11's
holiday exclusions explicitly name D4/D11/D8/R3, rather than these schedules.
D3.11's original sheet says availability no later than June 1, 2025; this
implementation does not infer an earlier enrollment date. A full-year 2025
D3.11 study is rejected; use June–December or a supported individual cycle.

Only complete regular **26–35-day cycles with confirmed full monthly charges**
are accepted. This is a conservative implementation guard, not a claim that
DTE defines every normal cycle this way. Document actual meter dates and bill
date, or label calendar cycles hypothetical. Initial/final/partial/extended
period proration is unsupported. Fixed charges are charged once per cycle;
no days/30 assumption is borrowed from PECO. Service-date rate changes are
allocated to the actual dated interval imports. Bill-month riders use the
explicit bill rendered date and matching designated billing month.

C4.5 calls for approximately monthly reads and monthly schedules for these
accounts. Its estimated-bill/lowest-hourly-rate treatment when hourly reads
cannot be retrieved is outside this interval-data path: missing records reject.
C4.4 generally restricts rate changes within twelve months unless DTE waives
the restriction. A hypothetical tariff comparison does not establish actual
permission to switch enrollment.

Ordinary full service only: no retail choice, RIA/low-income discount,
self-directed EWR, separately metered EV/interruptible programs, tax exemptions
or extra local/franchise charges. Users must confirm these account facts.
The hypothetical Ann Arbor-area coordinates are weather inputs; they establish
neither service territory nor absence of municipal fees.

## Filed arithmetic and two date clocks

`src/billing/dte_rates.py` stores USD values converted from filed cents/kWh.
`docs/utility_sources/dte/manifest.json` records official download SHA-256s,
selected one-based PDF pages and retained text hashes. Full PDF archives stay
in ignored research cache. Page tables are evidence, not runtime dependencies;
prices are part of the immutable Python engine.

* **Local service date:** capacity energy, non-capacity energy, distribution,
  nuclear surcharge and IRM. Base changes are February 6, 2025 and March 5,
  2026; IRM also changes January 1, 2026.
* **Bill rendered month/date:** actual PSCR, River Rouge and TCSC power
  securitization, delivery securitization, EWR and LIEAF. December 2025 TCSC is
  verified by final MPSC order U-21338, December 5, 2025, exhibit B.
* PSCR actual billed factor is $0.00250/kWh for 2025 and January–February
  2026, then $0.01877/kWh March–September 2026. October–December actual entries
  are blank in the retrieved C62 table. The authorized maximum is **not** used
  to fill them. Bill dates after September 30, 2026 reject.
* EWR is a residential per-kWh charge or a commercial monthly consumption-band
  fee. Commercial upper bounds are 850 and 1650 imported kWh; the model uses
  continuous interval energy at those bounds. Floating-point ties within
  0.000001 kWh are snapped only for band selection; other lines retain actual
  energy. Exact MILP ties select the lower fee. These are not demand charges.
  The same exact fee expression enters dispatch and independent rebilling.
* Residential sales tax is 4%, ordinary commercial tax 6%. LIEAF is excluded
  from the taxable subtotal (Michigan Treasury letter ruling 2013-5 and DTE
  Explanation of Charges). REPS is zero for these accounts; it is not added
  again through a summary table. Amounts round per reported component, with
  unrounded filed arithmetic and a rounding bound also retained.

These plans have **no measured kW demand charge**. Their capacity energy
charges and bundled supply are billed once. No MISO auction price, LMP,
capacity PLC or transmission tag is added. This feature does not calculate
large-customer demand tariffs or hyperscale data-center bills.

## PV, storage and export boundary

Grid-only is an ordinary absent-DER counterfactual. PV and PV-plus-battery
require independently confirmed Category 1 **Rider 18 DG** enrollment,
interconnection, approved annual sizing and storage arrangement. This is not
an assumption that operating without export automatically waives Rider 3
standby treatment. Conservatively, PV DC/AC nameplate (whichever is larger)
plus battery discharge rating must be ≤20 kW. Standalone storage and larger
DG require separate rules and are rejected.

Rider 18 charges inflow under the retail tariff and riders. This first path
requires **zero outflow and zero opening export-credit bank**. Curtailment is
preserved, not turned into compensated exports. Outflow credit calculation,
legacy Rider 16 NEM and credit carryover/settlement are not implemented.
Prior to March 13, 2025, annual eligible-generation sizing is limited to 100%
of prior consumption; the later rule permits 110%. Utility-confirmed sizing
must cover the actual study dates; a synthetic month's load cannot prove it.
Application/interconnection installation costs, including the nonrecurring DG
application fee, are outside these recurring operating bills and savings.

## MISO is a separate configuration layer

Distribution utility (`dte_electric`), Michigan jurisdiction, retail supplier,
tariff, grid operator (`MISO`), resource-adequacy zone (`LRZ7`), transmission
owner (`ITC Transmission`) and optional wholesale pricing location are separate
facts. The legacy PJM-style transmission-zone field is null for DTE. LRZ7 is
not a price node or a service-territory determination. Existing PJM account
schemas retain their original shape.

A wholesale identity may remain null, or explicitly supply `cpnode`,
`node_type` and `source`. This is metadata only: no live MISO price retrieval,
retail price pass-through, marginal-carbon signal or hub substitution is
implemented. Do not attach CAISO carbon to this Michigan case. See MISO's
[regional resource assessment](https://cdn.misoenergy.org/2023%20Regional%20Resource%20Assessment%20Report630736.pdf)
and the MPSC [service-area map](https://www.michigan.gov/mpsc/consumer/electricity/electric-utility-service-area-map).

## Reproducible studies and electrical limits

The regional validation driver selects all three DTE schedules. It imports a
deterministic synthetic native household/office series, clearly distinct from
meter measurements. Prepared 2025 ERA5 hourly reanalysis uses the exact site
coordinates; previous-hour radiation is shifted to interval starts and held
over four 15-minute intervals. This is not measured subhourly weather. Explicit
clear-sky and NSRDB options retain their existing separate source contracts.

Grid-only, PV-only and PV-plus-battery use identical native load and weather.
Dispatch minimizes the retail bill by default, with optional wear cost. Linked
cycles preserve SOC and impose final study SOC equal to its starting value.
This is historical perfect foresight within each cycle, not a forecast-driven
controller or proof of a jointly optimized annual policy.

Every returned scenario receives shared quasi-static OpenDSS replay at each
15-minute interval. Residential uses the existing representative split-phase
25-kVA/100-A service model; commercial 480-V three-phase uses the existing
750-kVA circuit. These are disclosed study assumptions, not DTE equipment or
a surveyed customer's wiring. Actual PV curtailment, absent equipment, SOC
mapping, convergence, voltages, loading and losses follow the shared replay
contract. Scheduled billing flows remain separate from replay PCC flows and
losses. Replay is after optimization; there are no network constraints or
transient/stability claims.

Run prepared, private historical inputs through the validation launcher; no
credentials or market downloads are needed for bundled billing. Historical
data and study artifacts stay in ignored `.cache`. Validation evidence and
exact candidate fingerprints are recorded separately in the DTE handoff.
