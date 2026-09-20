# Southern California billing candidate

Tariff data version: `socal-2026-09-19.2`. This is a bounded recurring-bill and non-export dispatch implementation, not complete reproduction of every account bill. See the handoff for the tested engine pin and browser cases.

## Implemented schedules and coverage

| Utility | Residential | Ordinary commercial | Verified study dates |
|---|---|---|---|
| LADWP | R-1A standard; R-1B TOU | A-1A, A-1B secondary; A-2B 4.8 kV; A-3A 34.5 kV | 2025-01-01 through 2026-09-17 |
| SCE bundled residential | D; TOU-D 4–9, 5–8, PRIME, non-CPP | — | 2025-01-01 through 2026-09-17 |
| SCE bundled commercial | — | TOU-GS-1 E/D; TOU-GS-2 D; TOU-GS-3 D; TOU-8 D, secondary service, non-CPP | 2026-06-25 through 2026-09-17 |

SCE's downloaded price sheets are effective June 1, 2026 (5829-E); some current terms and component sheets are effective June 25 (5837-E). The intersection is deliberately used for commercial schedules. SCE residential uses five verified 2025 versions plus January 1 and June 1, 2026 versions per plan. Explicit cancellation links establish continuous residential coverage; see [2026 audit](utility_sources/socal/history_2026/README.md). No current tariff is silently backdated. LADWP's July 2019 base prices are combined with separately versioned 2025–2026 quarterly adjustments.

The study covers one account billing cycle, with inclusive end date. SCE is limited to 40 days, LADWP to 93 days. Supply complete 15-minute interval-start timestamps with explicit UTC offsets; hourly data and missing/duplicate intervals are rejected. DST uses actual instants. Daily load shapes are explicitly hypothetical, not inferred meter data.

## Territory and account identity

Delivery uses the existing California Energy Commission distribution polygons, AgencyNum 58970 (LADWP) and 86250 (SCE). City/county text never selects a provider. Point intersections plus a 100 m boundary screen return approximate, ambiguous or unsupported; only recorded bill/utility attestation produces verified status. Overlapping Metropolitan Water District polygons are preserved, not silently discarded. CCA polygons supply availability suggestions only.

The existing service step includes a bill-confirmed delivery override; original map evidence, retrieval/version metadata, response hashes and confirmation reference remain saved. Avoid account numbers in references. Delivery does not establish generation enrollment. SCE bundled and CCA selections are stored separately. Actual unsupported CCA bills are rejected by the API as well as the form; a separately labelled hypothetical bundled comparison is allowed.

Climate regions are **account-confirmed inputs**, not inferred from the delivery polygon. LADWP zones 1/2 and SCE baseline regions 5/6/8/9/10/13/14/15/16 are supported. Automatic address-to-climate-region mapping is not implemented. The confirmation and selected region are saved with the site. Basic/all-electric allocation and heat-pump water-heater allowance require account confirmation.

## Billing and dispatch

- LADWP R-1A uses zone-dependent tier blocks, independently supplied annual PAC tier, capped-ordinance minimum and incremental charges, with consumption allocated by billing days across seasonal/quarterly boundaries. PAC is not inferred from the study month's consumption. R-1A rejects annual monthly average at or above 3,000 kWh.
- LADWP TOU uses weekday high peak 13:00–17:00, low peak 10:00–13:00 and 17:00–20:00, otherwise base. No SCE holiday rule is reused. Commercial facilities ratchets require all 11 previous monthly peaks, including the 4/30 kW minimum. A-2/A-3 reactive-charge cases are rejected unless confirmed outside that charge's scope.
- SCE keeps delivery and bundled generation separate. FRC is added once; CCA-only MCAM is not added to bundled service. D tiers and TOU baseline credits use daily seasonal quantities from Preliminary Statement H. PRIME requires qualifying technology.
- SCE TOU honors the filed holidays (including Monday observation when specified holidays fall on Sunday, not Friday observation for Saturday). Demand uses 15-minute maxima and nearest-whole-kW billing. The optimizer uses integer peak variables to match that rounding.
- Fixed monthly quantities use the explicit billing-month factor. A days/30 default in the billing API is an **allocation approximation**, not an assertion of a utility meter-read factor. Partial-cycle results must be treated as study estimates. SCE demand charges remain one complete monthly-cycle charge; a partial study does not prove the unseen peak.
- Local tax rate is separately confirmed or explicitly assumed. The implementation applies it to the recurring tariff subtotal; special jurisdiction-specific tax bases/exemptions are not modeled. State energy surcharge is $0.00030/kWh. A bill-confirmed SCE residential climate-credit amount can be applied once after local tax and state surcharge. No automatic award, cross-cycle credit ledger, or jurisdiction-specific franchise-fee treatment is modeled. Arrears, account corrections, special riders, optional RTEM/meter fees and other one-off items are excluded.

The optimizer and post-bill evaluator share `charge_lines`. Battery efficiencies, power/SOC bounds and final-energy equality use the existing `Battery` definition. Simultaneous charging/discharging and objective/bill disagreement are rejected. No AC network feasibility claim is made for schema 6.

## PV and solar settlement — material remaining scope

Only confirmed **non-export** interconnection is enabled. Surplus PV is curtailed. NEM, NEM-ST and NBT selections/exports fail explicitly; they are never represented by a zero-valued export tariff or PG&E rules. Commercial parallel-generation/standby eligibility must be confirmed separately. The browser compares grid-only, PV self-consumption, and PV plus battery operating costs, excluding capital cost, incentives and lifetime payback.

PV uses the repository's existing WeatherDerivedPV chain (PVWatts, Hay–Davies, SAPM temperature, PVWatts inverter) with explicit clear-sky assumptions: 20 °C air, 1 m/s wind, 14% system losses, 96% inverter efficiency, DC/AC ratio 1.2. Diagnostics and weather export with the bill. Historical weather and equipment selection remain available in existing Bay Area paths but are not yet wired to schema 6. This limitation must not be described as measured production or a weather forecast.

The official solar documents were researched and archived, but settlement is **unfinished**:

- LADWP NEM rider effective September 1, 2008: cycle netting, applicable-rate credits, bank carry-forward, restrictions on applying credits to taxes/minimum charges and account closure forfeiture require a separate bank ledger.
- SCE NBT: eligible import tariff, interval NBCs, hourly EEC vintage/lock-in, separate ACC Plus eligibility and balances, relevant-period accounting, true-up and net-surplus compensation require separately verified price data and ledgers. NEM/NEM-ST have different rules.

The full requested solar-program/vintage/export/true-up scope is therefore not complete. Enabling export programs requires additional implementation and tests, not simply enabling the form options.

## Sources

Retrieved 2026-09-17. Extracted official PDF texts and PDF/text SHA-256 hashes with direct URLs are in `utility_sources/socal/manifest.json`. Some SCE links require first opening the public SharePoint folder linked by the tariff-book page.

- [LADWP residential schedules and NEM rider](https://www.ladwp.com/account/customer-service/electric-rates/residential-rates)
- [LADWP filed-rate summary effective July 1, 2019](https://www.ladwp.com/sites/default/files/documents/Electric_Rate_Summary_effective_7_1_2019_with_factors_referenced_rev1.pdf)
- [LADWP capped ordinance](https://www.ladwp.com/sites/default/files/documents/LADWP_Electric_Rates.pdf)
- [LADWP residential quarterly adjustments](https://www.ladwp.com/account/customer-service/electric-rates/residential-adjustment-billing-factors)
- [LADWP commercial quarterly adjustments](https://www.ladwp.com/account/customer-service/electric-rates/commercial-adjustment-billing-factors)
- [LADWP commercial schedules](https://www.ladwp.com/account/understanding-your-rates/commercial-electric-rates)
- [SCE official tariff books](https://www.sce.com/regulatory/regulatory-information/tariff-books): D, TOU-D, TOU-GS-1/2/3, TOU-8, Preliminary H; research-only NEM, NEM-ST, NBT.
- [CDTFA electrical energy surcharge](https://cdtfa.ca.gov/taxes-and-fees/special-taxes-and-fees-tax-rates/): January 2019–present, $0.00030/kWh.

## Architecture and saved studies

Schema 6 uses the existing HTTP server, durable SQLite queue, independent worker, immutable Python engine snapshot, saved requests, itemized result tables and CSV downloads. The form consumes the candidate's plan metadata; server-side eligibility is authoritative. Account/location changes invalidate confirmation; date and plan changes invalidate schedule acceptance. Old schemas and saved results remain readable.

The ordinary `/api/studies` route rejects schema 6. Submit through `/api/v1/socal/studies` with a saved `resolution_id`; injected client map evidence is rejected. The worker revalidates against its immutable engine. Each run stores engine identity, dependency versions, tariff-data version and adjustment versions.

## Residential refinement — September 19, 2026

SCE residential uses the shared generic `RatePlan` timeline with utility-specific immutable rate versions. Numeric billing and convex dispatch use the same dated charge expressions. Applied versions, source sheets, service dates and baseline quantities are saved in the result table and CSV. Runtime source data are Python modules so immutable workers retain their exact rates.

The November 15, 2025 boundary switches the pre-BSC basic/minimum rules to the daily Base Services Charge. Daily charges count local service days, including DST. Apartment/unit profiles select the multifamily basic charge. D minimum comparisons exclude WFC; generation, FRC and state surcharge remain outside that minimum. HPWH allowance is limited to TOU-D 4–9/5–8.

**Remaining allocation limitation:** baseline quantities and minimum charges across rate or seasonal changes use day-prorated subperiods. Preliminary H includes consumption-based seasonal allocation; exact utility meter-read reconciliation across these boundaries is not implemented. The result explicitly warns about this approximation. A negative bill exposes amount due and remaining credit separately, without claiming a multi-bill carry-forward ledger.

See [historical sources](utility_sources/socal/history_2025/README.md) and [validation](validation/SCE_Residential_Refinement.md). CCA, additional municipal providers and export settlement remain deferred.
