# The Illuminating Company, Ohio

This local-development adapter covers The Cleveland Electric Illuminating
Company (FirstEnergy's The Illuminating Company), Ohio, P.U.C.O. No. 13.
Ordinary **RS Residential Service** and **GS General Service–Secondary** use
**Standard Service Offer (SSO)** supply. The source-reviewed component
intersections are January and June 2025, September–December 2025, and October
2026. Only complete matching calendar measurement/bill months execute.

The local browser, queued worker and existing regional dispatch/OpenDSS path
share this adapter. Source evidence is in the [aggregate ledger](utility_sources/illuminating_oh/sources.json),
[delivery review](utility_sources/illuminating_oh/delivery/research.md),
[supply/tax review](utility_sources/illuminating_oh/supply/research.md) and
[eligibility review](utility_sources/illuminating_oh/rules/research.md).
Acceptance evidence and limitations are recorded in the
[implementation report](Illuminating_Company_Ohio_Implementation_Validation.md).
Desktop GUI work remains paused; no stable engine is promoted.

## Account and date scope

The account independently confirms Company service, Ohio jurisdiction, ordinary
SSO enrollment throughout the cycle, one 120/240 V single-phase secondary meter,
unity billing PF, and absence of municipal/franchise charges, special tax
arrangements, extra facilities and recurring optional meter fees. A hypothetical
unincorporated Geauga County site is explicitly labeled; coordinates do not
establish service territory, tax status, enrollment or approval.

RS serves a family unit's exclusively residential use. Mixed commercial use on
the same meter and shared apartment facilities require an appropriate general
schedule. Legacy heating/distribution credits, assistance, shopping/aggregation,
optional TOU/CPP/PTR/RTP, AMI opt-out, primary-side metering, three-phase/reactive
service and special contracts are outside this first scope. Mandatory ordinary
credits and riders are retained despite these exclusions.

GS uses a Company-measured, aligned **30-minute integrated import peak**. Its
billing demand is the maximum of that peak, **5 kW**, and the documented actual
contract demand. The capacity price for the first 5 kW is **one flat monthly
amount**, followed by a per-kW price above 5 kW. There is no invented trailing
eleven-month ratchet. Contract demand is an independent obligation: it must not
be inferred from PV/battery-reduced demand. The sample retains an explicit
hypothetical 12 kW contract across all scenarios. Estimated demand, unmetered
accounts and special meter arrangements are excluded.

The model bounds native and imported interval demand at 25 kW for RS and 100 kW
for GS and usage at 833,000 kWh per cycle, keeping high-use USF blocks inactive.
These conservative study limits do not restate the full GS tariff's eligibility.

## Verified component intersections

| Service/bill months | Supply energy, $/kWh | RS/GS capacity, $/kWh | Main source distinction |
| --- | ---: | ---: | --- |
| January 2025 | .073408 | .003130 / .002846 | ESP V; DCR base-distribution percentage and positive VMC |
| June 2025 | .073661 | .022112 / .021864 | ESP IV summer GEN19 and April quarterlies; original June snapshot |
| September 2025 | .066966 | .022112 / .021864 | Winter energy and July quarterlies; September DCR54 |
| October–November 2025 | .066966 | .022112 / .021864 | October quarterlies; DCR54 |
| December 2025 | .066966 | .022112 / .021864 | DCR55 effective December 1 |
| October 2026 | .072774 | .028612 / .021729 | GEN20; October quarterlies, post-March distribution and September DCR |

Before March 1, 2026, RS base delivery is $4/month plus $.029510/kWh; GS is
$7/month, $13.6800 for the first 5 billing kW, then $7.4790/kW above 5. From
March 1 the filed bases are RS $6.50 plus $.048397/kWh and GS $10 plus
$26.6451 for the first 5 kW and $12.5319/kW above 5. These filed base dates
alone do **not** establish complete March–September 2026 billing coverage.

All ordinary nonzero GEN, AER, DRR, DUN, GCR, AMI, PUR, NDU, EDR plus its
separate automaker recovery, NMB, DCR, TSA, DSE, PIR, RER/CCR, CRC, LGR, SGF,
VMC and USF components are independently dated. DCR uses only base distribution
for January's percentage; later RS DCR is per kWh and GS DCR per billing kW.
The delivery ledger gives exact amounts, units, revisions and percentage bases.

Important safeguards include January PIR's superseding $.000427/kWh rather
than the stale $.000449 in one retained composite; mandatory 2025 CRC of
−$0.51/month RS or −$.000298/kWh GS; and ordinary positive 2025 RS RER even
without legacy heating-credit eligibility. October 2026 uses CCR, with RER
zero, avoiding a double charge. Historical printed CDR/TAS2 credits expressly
ceased and are not applied. Explicitly zero ordinary riders and inapplicable
special programs remain documented in the source review.

Retail GEN already converts energy/capacity to $/kWh; transmission/non-market
charges are in NMB. No additional LMP, PJM PLC/NSPL, loss, capacity, transmission
or generic whole-bill tax is added. The adapter records exact source versions
and raw itemized arithmetic, followed by the shared study's component half-up
cent rounding. It does not claim an exact printed invoice or rounded-cash
optimization proof.

## Taxes and calendars

Sheet 92 incorporates Ohio Revised Code 5727.81. State-kWh tax uses $.00465,
$.00419 and $.00363/kWh and the explicit CAT gross-up `1 / (1 − .0026)`.
Exactly 30 measurement days use cumulative thresholds 2,000 and 15,000 kWh.
For other periods the statute specifies daily average bands: cumulative
thresholds are **67 × local calendar days** and **500 × local calendar days**.
A 31-day cycle therefore uses 2,077 and 15,500 kWh; it does not silently reuse
the 30-day bands. Wired electricity is sales-tax exempt under ORC5739.02(B)(7).
No self-assessor exemption, municipal charge or special tax contract is modeled.

Complete 15-minute Eastern-time grids reject missing, duplicated, unordered or
substituted hourly data. DST changes elapsed intervals, not local measurement
days. November 2025 has 30 days and 721 hours; its tax bands remain 2,000/15,000.
Fixed monthly charges are whole, and service month, designated billing month
and final-day bill date must match. Irregular, partial, shifted or midmonth
fixed-charge transition cycles reject without sourced allocation rules.

## PV, storage and market separation

The exact PV and paired-storage configuration must already have Company final
approval, required metering and ordinary qualifying renewable treatment before
service. Ohio's current net-metering rule requires the underlying ordinary
retail components and charges; eligibility/sizing, primarily onsite use and the
120% requirements limit still need independent confirmation. The study does not
establish them from coordinates, equipment size or reduced imports.

The implemented subset uses PV-only storage charging, zero exports and no
credit bank, with combined study output at most 25 kW. It excludes standalone
storage, Partial Service, standby and export/NEM settlement. Old tariff cash
refund language differs from the current state's continuous-credit rule; this
unresolved settlement is not enabled. The grid-only counterfactual removes DER
approval assertions and activation date while retaining tariff, SSO, actual
contract and other account obligations.

PJM, ATSI transmission context and **FE-ATSI control area** are metadata. The
distribution Company, Ohio jurisdiction, SSO arrangement, explicitly selected
wholesale pricing location and optional **US-MIDA-PJM regional-average carbon**
are separate identities. The existing carbon path is available independently;
it is not a utility-specific intensity or a retail charge.

## Remaining gaps

February–May 2025 lacks complete intermediate ESP-IV component chronology;
July's LGR revision and August 14 fixed-charge allocation remain unverified.
January–September 2026 lacks complete earlier rider/credit intersections.
Two archive captures were intrinsically truncated; bounded recovery produced
no usable pages, and those responses were not treated as tariff evidence.
No missing rate is interpolated, carried forward or replaced with a current
rate. There is no provisional mode and no full-year 2025 acceptance claim.
