# Delmarva Delaware R and SGS-ND fixed-price SOS

The regional adapter models ordinary Delaware PSC No. 8 residential R and
secondary SGS-ND with Delmarva as distribution utility and fixed-price SOS
supplier. Initial scope is one 120/240 V single-phase meter in unincorporated
Sussex County, with separately confirmed territory, classification and taxes.

## Verified dates

Complete matching calendar service and bill cycles are executable for
December 2025 and September–November 2026. The whole monthly charge applies
and the bill date is the final service day. Shifted/partial cycles require a
separate verified allocation model.

The September 2025 and September 2026 tariff books supply the dated rates.
The utility's June–December 2026 RPCR table explicitly includes December
2025's QFCP charge. That comparison column is not extrapolated to earlier
2025 bills. January–August 2026 are blocked pending superseded DSIC and
transmission intersections and the July interim-rate allocation. December
2026 crosses the next interim base-rate step on December 9 and is blocked.
No complete-year study is supported. The
[source ledger](utility_sources/delmarva_de/sources.json) records source
grades, hashes, effective dates, visual RPCR transcription and remaining gaps.

## Account and bill

R covers ordinary household use under Leaf 53. Confirm that the distinct
electric space-heating classification under Leaves 40 and 54 does not apply.
The December 2025 customer/distribution charges are $13.50 and
$0.046594/kWh. The July 9, 2026 interim step changes these to $14.72 and
$0.050660/kWh for the supported 2026 cycles. Both 500 kWh energy blocks
have equal marginal rates in this scope.

SGS-ND Leaf 60 requires secondary voltage and maximum monthly use below
3,500 kWh. Two consecutive months at or above 3,500 kWh trigger MGS-S
transfer, retained for at least 12 billing months. Obtain utility-retained
SGS-ND assignment, independent prior-usage review below 3,500 kWh and
confirmation that no MGS-S transfer obligation remains. The study also
bounds native load and imports at 3,499 kWh per cycle and 10 kW. R's
study peak is 25 kW. PV-reduced imports do not establish eligibility.

SGS-ND customer/distribution rates are $18.77 and $0.062487/kWh in
December 2025, then $19.79 and $0.070076/kWh in the supported 2026
cycles. Billed-demand service is outside this scope.

The bill itemizes customer/distribution, SOS, PCA, Green Energy, Low-Income,
RPS, QFCP-RC, applicable EE, EDIT, storm expense, DSIC, UFRC, transmission
and public utility tax. December 2025 DSIC is 5.32% of customer plus
volumetric distribution base. The supported 2026 cycles use the filed zero
DSIC. UFRC, ordinary R/SGS-ND EDIT and SSER are filed zero.

Rider SOS transmission charges use an independent company-assigned PLC in
kW, multiplied by $5.782620/kW-month for December 2025 and
$5.952635/kW-month from September 2026. Enter the actual billed
determinant, source and validity dates. Each complete cycle must fit within
those dates. The study retains the obligation across all scenarios.

The filed rates retain embedded PSC assessment treatment. Ordinary R use
has the residential public utility tax exemption in 30 Del. C. §5506(e).
Ordinary SGS-ND pays 4.25% on the taxable subtotal. Manufacturing or
agribusiness reduced rates, other exemptions and Wilmington's 2% local
franchise tax are outside this unincorporated Sussex scope. Supplier,
utility, locality, PJM DPL zone and optional wholesale prices remain separate.

## Non-export generation

Leaf 27 requires written notice and utility consent for another source of
electric supply. The generator must not feed current into the delivery
system unless a contract permits it. Document final approval for the exact
PV or PV-plus-storage no-sale installation, preserving ordinary import
billing. Storage charges only from onsite PV. Export settlement, NEM credit
banks, Rider X sales, standalone batteries, community solar, special
assistance and optional demand-response credits remain outside scope.

## Validation

Utility tests independently rebill all supported stacks with Decimal
arithmetic, compare filed base components with the July 8, 2026 compliance
schedule, check symbolic/numeric parity and retained transmission obligations,
and exercise date/account/DER rejection, fall DST and malformed intervals.
No customer invoice was supplied. Full-bill checks use a separate tariff
transcription. The root batch report records worker, matrix and browser
acceptance on its final frozen candidate.
