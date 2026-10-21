# Utility and electricity provider guide

Find the electricity company serving your study location, understand how its regional service works, and see which account arrangements the simulator can model. Each profile gives a short introduction, a service-area description, relevant regional distinctions, and links to official information and detailed model coverage.

**Reviewed October 15, 2026.** This guide covers 19 providers with implemented billing paths and one separate Dominion Virginia candidate. “Implemented” means selected account arrangements work in the repository; it does not mean the entire tariff book, every historical date, or every solar program is supported. A running browser may use an older engine snapshot.

## Start with the electricity account

Use the electric section of a recent bill to identify the delivery utility, generation provider, rate schedule, and any solar program. A city, county, ZIP code, gas bill, or map match alone may not establish the electric service arrangement.

| Term | What it means for the user |
| --- | --- |
| Delivery utility | Operates the local electric network serving the account. |
| Generation provider | Supplies or purchases the electricity; it can be the delivery utility or a separate provider. |
| Municipal utility | Publicly owned utility serving its defined local territory. |
| Community-choice provider or CCA | Public electricity purchaser whose customers generally retain the existing utility’s delivery service. |
| Tariff or rate plan | The prices, eligibility conditions, and billing rules applicable to the account. |
| CAISO or PJM | Regional grid/wholesale-market organizations; their names alone do not identify a customer’s retail tariff. |

The provider profiles link to official descriptions of these service relationships. For billing and simulation terms, see the [short glossary](utility_guide/glossary.md).

## Bay Area and Northern California

Several distinct arrangements coexist here. Alameda city has AMP; Santa Clara city has SVP. Other nearby communities can have PG&E delivery with a separate CCA. San Francisco’s Hetch Hetchy Power and CleanPowerSF are different services even though both are operated by SFPUC. Confirm the actual account rather than choosing the nearest familiar company name.

| Provider | Service area at a glance | Modeled account scope |
| --- | --- | --- |
| [Pacific Gas and Electric Company](utility_guide/pge.md) | Northern and Central California | Selected residential and commercial plans; bounded solar programs |
| [Alameda Municipal Power](utility_guide/amp.md) | City of Alameda, California | Residential and commercial imports/storage |
| [Silicon Valley Power](utility_guide/svp.md) | City of Santa Clara, California | Residential and commercial imports/storage |
| [Hetch Hetchy Power](utility_guide/hetch_hetchy.md) | Eligible San Francisco accounts and projects | Selected small/medium commercial accounts |
| [CleanPowerSF](utility_guide/cleanpowersf.md) | San Francisco, California | Commercial B-1 generation + PG&E delivery |
| [WestLight Energy formerly Peninsula Clean Energy](utility_guide/westlight.md) | San Mateo County and Los Banos, California | Commercial B-1 generation + PG&E delivery |
| [Silicon Valley Clean Energy](utility_guide/svce.md) | Participating Santa Clara County communities, California | Commercial B-1 generation + PG&E delivery |
| [San José Clean Energy](utility_guide/sjce.md) | City of San José, California | Commercial B-1 generation + PG&E delivery |

For studies across these service areas, use local weather and building-specific heating and occupancy inputs. A Bay Area utility label does not determine one residential or commercial load shape. These are study-design considerations, not measured customer profiles.

## Los Angeles and surrounding Southern California

Los Angeles city, Los Angeles County, and the greater metropolitan area are different geographic scopes. LADWP, SCE, and several municipal utilities serve different parts of the region. Some boundaries are smaller than a city: IPU serves only selected properties in City of Industry. The linked profiles explain each case.

| Provider | Service area at a glance | Modeled account scope |
| --- | --- | --- |
| [Los Angeles Department of Water and Power](utility_guide/ladwp.md) | City of Los Angeles and separately served Owens Valley communities, California | Selected residential/commercial plans; bounded R-1A solar |
| [Southern California Edison](utility_guide/sce.md) | Parts of Central, coastal, and Southern California | Selected residential/commercial plans; bounded solar programs |
| [Glendale Water and Power](utility_guide/gwp.md) | City of Glendale, California | Selected residential/commercial import plans |
| [Pasadena Water and Power](utility_guide/pwp.md) | City of Pasadena, California | Selected legacy residential/small-commercial flat plans |
| [Burbank Water and Power](utility_guide/bwp.md) | City of Burbank, California | Selected residential/non-demand commercial plans; bounded EV solar |
| [Azusa Light and Water](utility_guide/alw.md) | Azusa electric service area, California | Residential D and non-demand commercial G-1 imports |
| [Industry Public Utilities](utility_guide/ipu.md) | Selected properties in City of Industry, California | Domestic D only; commercial service not modeled |

For comparison studies, keep building load and equipment assumptions comparable, but apply each account’s actual eligibility and billing rules. A nearby utility’s lower bill does not mean a customer can switch the local delivery network.

## San Diego region

SDG&E provides delivery, while participating accounts can receive generation from SDCP or CEA. San Diego city, unincorporated county areas, and neighboring cities are separate jurisdictions. The simulator’s modeled fee conditions can be narrower than a provider’s real service area.

| Provider | Service area at a glance | Modeled account scope |
| --- | --- | --- |
| [San Diego Gas and Electric](utility_guide/sdge.md) | San Diego County and southern Orange County, California | Selected residential imports only |
| [San Diego Community Power](utility_guide/sdcp.md) | Participating San Diego County jurisdictions, California | Selected residential generation + SDG&E delivery |
| [Clean Energy Alliance](utility_guide/cea.md) | Seven North County San Diego cities, California | Selected residential generation + SDG&E delivery |

The current San Diego extension supports selected residential import studies. Commercial service exists in the real region but is not implemented by that extension.

## Northern Illinois

| Provider | Service area at a glance | Modeled account scope |
| --- | --- | --- |
| [Commonwealth Edison](utility_guide/comed.md) | Northern Illinois, including the Chicago region | Residential/commercial BES and BESH; non-export PV/storage |

ComEd introduces separate retail supply arrangements within PJM. The account’s plan determines whether hourly market prices affect the retail bill. Use the same building load, weather year, and equipment when comparing scenarios; do not substitute wholesale prices for retail charges.

## Dominion candidate and work in progress

[Dominion Energy Virginia](utility_guide/dominion_virginia.md) already has a limited commercial GS-2T candidate. The wider Virginia residential/commercial expansion, Dominion North Carolina, and PSE&G are active implementation work and are not included in the completed-provider count above. Recheck their accepted coverage and main-browser validation before moving them into the main directory.

Other providers may appear in location research without an executable account model. The current [LA coverage notes](LA_County_Utilities.md) and `src/billing/la_coverage.py` distinguish these records. Vernon, Cerritos, Lancaster Energy, Pico Rivera PRIME, Pomona Choice, and Palmdale EPIC are not listed here as implemented services. Clean Power Alliance has a limited solar-credit accounting component but no complete main-account billing integration in the inspected workflow; it is also excluded from the completed list.

## Michigan · DTE Electric

The local candidate supports bundled D1.11 residential Standard TOU, D3
commercial General Service and D3.11 commercial TOU. D1.11/D3 prices cover
2025 through September 2026; D3.11 starts June 2025. Complete regular monthly
cycles, confirmed account eligibility and zero exports are required. PV and
storage require approved small-DG enrollment; a map location alone does not
establish it. MISO LRZ7 describes resource adequacy, not a price node or retail
service territory. See [DTE scope and source evidence](DTE.md).

## Michigan · Consumers Energy

The local candidate supports residential summer TOU RSP, year-round Smart Hours
RSH, commercial secondary GS and commercial TOU GSTU. Verified coverage is
January 2025–June 2026, bounded by actual billed PSCR evidence. Commercial EE
surcharges use a documented utility-assigned annual-review tier, not current
cycle consumption. Complete regular monthly cycles and confirmed non-export DG
eligibility are required. MISO LRZ7 and METC transmission metadata remain
separate from retail bills. See [Consumers scope, sources and limitations](Consumers_Energy.md).

## Before running a comparison

1. Confirm delivery utility and generation enrollment from the account.
2. Select an eligible residential or commercial plan and a verified date window.
3. Use native building load before PV/battery effects, with an explicit source.
4. Match the weather year, local timezone, PV equipment, and battery configuration to the study.
5. Confirm whether the selected path supports import-only, non-export PV, or a particular export program.
6. Read the results’ bill-completeness, optimization, and electrical-validation notes.

Savings are modeled results under these assumptions. A utility profile is not an enrollment decision or a promise of savings. Representative OpenDSS checks describe the modeled circuit, not approval of a real installation.

## Keeping this guide current

Profiles contain introductions rather than duplicate price tables. Use the linked implementation notes and active engine catalog for exact rates and dates. Publication dates on this guide are review dates, not tariff expiration dates. [Maintenance and evidence notes](utility_guide/maintenance.md) describe how to update coverage without confusing implemented code with a promoted browser release.
