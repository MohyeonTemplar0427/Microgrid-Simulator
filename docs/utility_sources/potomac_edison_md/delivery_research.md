# Potomac Edison Maryland delivery evidence

Research snapshot:2026-10-26. Own delivery evidence only; supply/admin-credit/ECA and taxes/USP/RGGI/relief/eligibility have distinct research owners. Main and existing changes were preserved. No Git mutation or production/test edit was performed.

## Primary originals and date coverage

Originals and selected text live under `.cache/potomac_edison_md/sources/delivery/`. `delivery_sources.json` lists exact URLs, SHA256, sizes and paths for five PDFs. `delivery_components.json` contains fixture-ready base/rider literals and independently published current-price benchmark rows. `book_delivery_selected.txt` preserves physical page labels. The live FirstEnergy Maryland tariff index was captured once, with its actual links; it exposes current tariffs and pending changes, not a historical archive. Specific historical-rider searches were bounded and no missing rate was inferred.

- Current [retail tariff](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/maryland/tariffs/PotomacEdisonRetailTariff.pdf):189 physical pages. Current Rphysical62/tariff6, Gphysical69–72/tariff7–7-3. Current prices are separate from the pending2026 base-rate filing.
- [2026 PURPA filing](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/maryland/tariffs/pending-tariff-revisions/pe-annual-surcharge-filing.pdf): physical5/16 redline records prior2025 adopted leaf (issuedNov27,2024, effectiveJan1,2025, approvedDec18,2024), with old R$.00833/G$.01172 per kWh. Redline new and old figures concatenate in plain extraction; preserve original visual styling. Current adopted bookp52 corroborates the selected2026 R$.00806/G$.00953, issuedNov17,2025, effectiveJan1,2026, approvedDec23,2025. The same filing contains an **alternative allocation** R$.00862/G$.00893; this is not the adopted rate.
- [2025 EmPOWER filing](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/maryland/tariffs/pending-tariff-revisions/PE-2025-EmPower-Tariff-Update-112724.pdf): contains three alternative amortization methods. Proposed utility method R$.01009/G$.01022; other alternatives differ. This proposal alone is **not adoption proof**. Official [OPC datedFebruary2025 appendix](https://opc.maryland.gov/LinkClick.aspx?fileticket=jhkXijSzngo%3D&mid=2652&portalid=0&tabid=1151) independently quotes R$.01009, Rdistribution$.02287 and customer$6, but a dated adopted G2025 leaf remains a gap in this research. Machine literals retain2025 EmPOWER null rather than silently choosing an alternative.
- [September4,2026 base-rate filing](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/maryland/tariffs/PE-MD%202026-09-04%20Base%20Rate%20Filing.pdf):928 pages. Outline ExhibitRV-13 is physical172–178. Only its **current distribution bill** column is used as an independent benchmark. Its proposed rate column is not effective and is not used.

## Delivery component table

All rates dollars. Actual monthly adjustment coverage is determined separately by supply owner; base/rider coverage alone is not complete billing coverage.

| Component | R | G | Authority/date |
|---|---:|---:|---|
| Fixed distribution monthly |6.00|4.85|Current R62 and G69; G adoptedMarch1,2024, R2025 independently corroborated by OPC|
| Distribution energy per kWh |.02287|.02243|Same pages; no R tier, G all kWh|
| Distribution minimum capacity per kW |none|1.70|G69, minimum-charge capacity rule G71|
| Distribution measured capacity above7.5kW |none|2.12/kW|G69; separate from minimum-charge floor|
| Reactive capacity |none|.40/kvar above25% of kW capacity|G69; meters installed above200kW, G71|
| PURPA termination2025 per kWh |.00833|.01172|Prior adopted leaf visible in2026 filing physical5/16|
| PURPA termination2026 per kWh |.00806|.00953|Current adopted book52, effective serviceJanuary1,2026|
| EmPOWER2025 per kWh |null; R.01009 corroborated|null; proposed.01022|Adoption distinction above; do not infer G|
| EmPOWER2026 per kWh |.01376|.01142|Current adopted book56, effectiveJanuary1,2026, approvedDecember23,2025|
| EDIS2025/2026 |canceled|canceled|Current book61: cancellation effectiveJanuary17,2024, approved same date|

PURPA applies in addition to any schedule minimum and before tax surcharge. EmPOWER is also in addition to schedule minimum, before tax; its calculation includes gross-receipts-tax and Commission-assessment adjustments. No additional blanket gross-up is established by these delivery pages. Administrative delivery credit is a separate per-kWh credit, not the SOS supply administrative charge; current book59 says credits adjust June/October/January or more often. Supply owner preserves the combined dated adjustment sheet. Do not net wholesale LMP, PLC/NSPL or supplier costs into these delivery components.

## G capacity, history and minimum rules

Current book physical71/tariff7-2, effectiveMarch23,2019:

- Metered CapacityRequired is highest30-minute kW demand in billing period. kW and reactive kVA are computed to nearest0.5; tie convention not resolved here. Minimum-charge capacity is current month but at least half the highest CapacityRequired in previous12months.
- For connections without a demand meter, CapacityRequired for the minimum is `max(current_month_kWh, .5 * highest_previous_12_month_kWh) /250`. An account must affirmatively have no demand meter. Missing historical months are not zero; retain all12 completed prior monthly values and advance history after each scenario's cycle. Do not substitute a single annual total or reset history when PV/storage is added.
- G transmission page70 has minimum$.34/month and minimum-kW$.19/kW; measuredkWabove7.5$.24/kW; energy first700$.00440/kWh and excess$.00214 (current dated supply leaf; supply owner verifies historical transmission rates). The word minimum must not become routine additive capacity.
- Current physical10/Rule1(l) says fixed distribution recovers presence costs regardless of energy or CapacityRequired; physical12/Rule1(cc) defines variable distribution as costs not recovered in fixed. G69 puts minimum-kW1.70 under variable distribution, separately from fixed4.85. This supports fixed4.85 plus the greater of actual variable distribution and1.70*minimumCapacity. It is a tariff-structure interpretation; no independent floor-active low-energy published benchmark was recovered. Do not claim that boundary independently reconciled. Likewise exact nesting of the transmission$.34 and$.19*minimumCapacity floors needs explicit interpretation/benchmark before claiming general billing support.
- A utility-confirmed no-demand-meter study with actual30-minute peak strictlybelow7.5kW avoids rounded measured-demand and above7.5 charges, but still retains minimum-capacity/history rules. It does not establish TypeI status automatically. A minimum-inactive restriction can avoid the unverified floor branch only if every candidate's energy/charges is checked against the history-dependent minimum, including PV/storage outcomes.
- G is unavailable for standby/maintenance service. Term up to25kW singlephase month-to-month; other service has contractual terms. Special monthly-service surcharges start10% firsttwo months and phase down tozero after12continuousmonths (p72), so initial ordinary scope needs confirmation of established regular service and no special connection/minimum-revenue agreement. Voltage discounts apply only2kV+ and customer-owned facilities; unityPF/secondary study does not earn them.

R is single-phase through one meter. Mixed residential/commercial premises only remain R if nonresidential installation<=500W; grandfathered multiresidence and farm rules can alter fixed charges (p63). Restrict to one ordinary dwelling/meter unless separately modeled.

## Independent published distribution fixtures

ExhibitRV-13 physical172 R1000kWh current distribution **$28.87** =6+.02287*1000; R100kWh$8.29 rounded. Physical173 G5kW/730kWh current distribution **$21.22** =4.85+.02243*730, and G10kW/1460kWh **$42.90** =4.85+.02243*1460+2.12*(10-7.5). G20kW/2920kWh **$96.85** agrees with the same formula. These independently reject routine addition of1.70*minimumCapacity to every bill. They cover base distribution only, at nonbinding minimum; surcharge/tax/SOS amounts are not thereby proven. Do not label the rounded “TotalBill%Change” column a dollar bill benchmark.

## Open boundaries

The source pass does not establish a complete2025 delivery-rider intersection because GEmPOWER adoption and separate monthly admin-credit/ECA history remain unverified here. Current2026 adopted base/PURPA/EmPOWER is explicit; actual executable window also requires supply/tax source intersections. No current-rate substitution into2025 is permitted. Pending GridPrograms/large-load/base-rate cases are not effective tariffs. Export/NEM settlement and DER capacity adjustments require separate verified eligibility and account terms; no export credit is authorized. Actual partial/crossing-period proration, floor-active G invoice behavior and nearest0.5 ties are not independently benchmarked.
