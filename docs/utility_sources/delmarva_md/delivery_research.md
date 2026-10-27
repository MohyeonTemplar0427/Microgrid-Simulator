# Delmarva Maryland delivery research

Verified on 2026-10-26. Scope: R residential and ordinary secondary SGS-S Type I SOS. These findings concern delivery components; supply, jurisdiction taxes, USC account assignments, residential RGGI credits and legislative refunds have separate research owners. No production, Git index, deployment or stable-engine mutation was made by this research.

## Source inventory and recovered coverage

Originals, text extractions, SHA256 and URLs: `.cache/delmarva_md/sources/delivery/delivery_sources.json`. Literal retail-sign monthly components and independent published totals: `monthly_components.json` beside it. Its 30 R/SGS rows sum exactly with Decimal arithmetic to utility-published variable composites; overlapping April/May2025 values agree between two originals. The source data has January–September2025 and May–October2026 monthly values. This does not authorize crossing-month allocation or a complete amount-due claim.

- [cseg_may2025](https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6813cee9952c500a8dd0aae0/DPL_MD_CSEG_-_05012025.pdf?branch=prod_alias), SHA256 `8064e1cc3cf30cc1d2faf9499d5b01f087d64fbf5b55cf7a3986e82748bcd94f`.
- [cseg_sep2025](https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/68b731f3c1561b3668f1c405/DPL_MD_CSEG_-_09012025.pdf?branch=prod_alias), SHA256 `fac1c860d4f21a05a38feaee53c18c5a978621cba71e370faf67ca6c659efe07`.
- [cseg_oct2026](https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias), SHA256 `de819389d11ad0ae05bdc76997d3fccb756b3318d865fa58ee937fa4a4b402f3`.
- [bsa_current](https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/bltbc8859786ea995d7/6abd95feaf264f00d4bbc05e/DPL_MD_BSA_-_102026_.pdf?branch=prod_alias), SHA256 `494cc2b66123653f143d88fb65cdeca726d23873a9009f65b1b0e5e0e6d42bc3`.
- [ac_current](https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt919c5f716ed2f78e/6abd979dd463366c81c10b3a/DPL_MD_Admin_Credit_-_102026_.pdf?branch=prod_alias), SHA256 `6537256fbe95237cf34e69825a91b27080f7544371af1d5a02194e24cba98893`.

The May2025 and September2025 CSEG sheets have R physical p1 and SGS-S TypeI p2. October2026 has R p1 and SGS-S TypeI p4. CSEG signs are credits; the literal file inverts signs to retail charges positive and delivery credits negative. GRT is already embedded in applicable Delmarva rates; no additional Pepco-style percentage is justified.

## Base rates and rules

Full books are shared preserved originals under `.cache/delmarva_md/sources/supply/`; exact URLs/hashes are in that owner's `supply_records.json`. Selected delivery excerpts with physical page labels are in this delivery cache. Current book physical p48 (Leaf45): R customer $9.43/month and distribution $.071482/kWh, summer and winter. Current p56 (Leaf47): SGS-S customer $26/month, distribution $.041549/kWh plus $4.303679/kW, summer and winter. These prices agree with December2024 book R48/SGS55 and March2025 book R48/SGS55. March5 filing effective February3,2025 changes the printed RateYear3 endpoint to June30,2026 without changing those prices; no numerical delivery allocation is needed for February. The current book removes that endpoint. Supply administrative changes are separate.

R availability: single private dwelling/dwelling unit, farmstead/estate and pertinent detached buildings, Maryland territory, current Leaf57. SGS-S availability current p87/Leaf61: secondary voltage and monthly measured maximum below300kW; a month at/above300 transfers to LGS-S next month. This alone does not establish TypeI SOS or E3 estimated-demand assignment.

Current p88/Leaf62 E1 measures greatest15-minute demand, nearest whole kW, **except paragraphs2/3**. E3 permits the Company, for demands below20kW, to measure, assess after test, or estimate; estimated demand is monthly kWh divided by175hours, not estimated above20kW. G says billing demand is that month's maximum measured demand; no separate ratchet. H minimum monthly charge is the customer charge. These provisions are unchanged since effective June1,2004. E3 is an affirmative utility assignment, never inferred from modeled load or selected by an optimizer. Nearest-whole-kW metered demand and tie rules are outside the initial implementation.

Independent E3 fixture:1750kWh/175h=10kW. Distribution demand10*$4.303679=$43.03679; distribution energy1750*$.041549=$72.71075; customer$26; subtotal of these three=$141.74754. Transmission first20kW has no charge; first3500kWh still has its dated energy rate. CSEG SGS variable composite excludes fixed/customer/USC and **all demand charges**; do not treat it as complete bill or multiply its transmission energy beyond3500kWh. A narrow study can require utility-approved E3 retained across scenarios, physical15-minute peak<20kW and imports<=3500kWh/month.

Off-peak contracts have separate clocks and $8.85/month adder, excluded. Opt-out costs $75 enrollment paid in three installments plus$17/month, excluded through ordinary AMI account confirmation. No customer/fixed-charge proration rule is established here; support only complete matching hypothetical calendar meter/billing cycles, and reject partial/shifted periods. Fullbook rate footers distinguish usage dates from E-MD billing-month clock.

## Other delivery riders

- E-MD2025: R$.012649/kWh, SGS$.011191/kWh, effective billing monthJanuary2025 (March2025 book Leaf132, filedDecember19,2024). E-MD2026: R$.020055, SGS$.014937, effective billing monthJanuary2026, current p173/Leaf132, filedDecember31,2025. Annual rider cannot be shifted by service-date assumption.
- DRS: zero for both schedules, current p181/Leaf139, filedOctober21,2022/effective usageNovember1,2022; also present unchanged in March2025 book. GRC: zero, current p184/Leaf142, filedJune28,2019/effective usageJuly1,2019; unchanged in March2025 book.
- MYP current p198/Leaf150a expressly August1,2024–June30,2025 R credit$.002647/SGS$.001756 per kWh. Current p199/Leaf150b expressly July1,2025–June30,2026 Rcredit$.000256/SGS$.000171. The current official October2026 CSEG independently publishes these latter credits **for July–October2026**. Cite that monthly primary publication for those months; do not silently extend the expired standalone leaf.
- MCAM-S current p200–203/Leaves151–154 effectiveMay1,2026: interconnection fees, not a monthly kWh rider. Residential $231/interconnection plus$.82/application; small commercial$151/nameplate-kW plus$.01/kW administrative fee, subject to applicability/exemptions and actual utility process. Preserve these as project/interconnection costs; do not fold into recurring retail energy. PV/storage needs approved ordinary-service evidence and separately documented applicable project fees.
- Administrative credit current one-page original is a credit applicable to delivery service customers. June–September2026 R$.001380/TypeI$.000843; October2026 R$.001420/TypeI$.000901. May2026 R$.001393/TypeI$.000802 is preserved in CSEG.

## Exact monthly delivery literals

All rates $/kWh, retail signs; negative numbers are credits. Customer and demand are stated above. MES/tax interpretation is owned separately.

| Month | R BSA | SGS BSA | R admin credit | SGS admin credit | R MYP | SGS MYP | R published variable | SGS published variable |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025-01 | 0.00784000 | 0.00556300 | -0.00120100 | -0.00050600 | -0.00264700 | -0.00175600 | 0.21340320 | 0.17833940 |
| 2025-02 | 0.00087900 | -0.00182500 | -0.00119800 | -0.00046100 | -0.00264700 | -0.00175600 | 0.20700160 | 0.17093330 |
| 2025-03 | -0.00443200 | -0.00090000 | -0.00119800 | -0.00046100 | -0.00264700 | -0.00175600 | 0.20131260 | 0.17264300 |
| 2025-04 | -0.00823600 | -0.00707700 | -0.00119800 | -0.00046100 | -0.00264700 | -0.00175600 | 0.19738450 | 0.16687750 |
| 2025-05 | -0.00054200 | 0.00088800 | -0.00119800 | -0.00046100 | -0.00264700 | -0.00175600 | 0.20405540 | 0.17404620 |
| 2025-06 | 0.00832800 | -0.00257200 | -0.00128200 | -0.00081600 | -0.00264700 | -0.00175600 | 0.21260700 | 0.16759550 |
| 2025-07 | 0.00098600 | 0.00083800 | -0.00128200 | -0.00081600 | -0.00025600 | -0.00017100 | 0.20866430 | 0.17303380 |
| 2025-08 | 0.00571600 | 0.00183400 | -0.00128200 | -0.00081600 | -0.00025600 | -0.00017100 | 0.21541460 | 0.17552330 |
| 2025-09 | -0.00810200 | -0.00595000 | -0.00128200 | -0.00081600 | -0.00025600 | -0.00017100 | 0.20373650 | 0.16727660 |
| 2026-05 | -0.00862800 | -0.00605600 | -0.00139300 | -0.00080200 | -0.00025600 | -0.00017100 | 0.20930940 | 0.16963030 |
| 2026-06 | -0.00160300 | -0.00057900 | -0.00138000 | -0.00084300 | -0.00025600 | -0.00017100 | 0.21960090 | 0.17925560 |
| 2026-07 | 0.00264400 | 0.00323000 | -0.00138000 | -0.00084300 | -0.00025600 | -0.00017100 | 0.22438190 | 0.18331610 |
| 2026-08 | 0.00230500 | 0.00054700 | -0.00138000 | -0.00084300 | -0.00025600 | -0.00017100 | 0.22598030 | 0.18157170 |
| 2026-09 | -0.00255700 | -0.00085200 | -0.00138000 | -0.00084300 | -0.00025600 | -0.00017100 | 0.22253980 | 0.18053180 |
| 2026-10 | 0.00857800 | 0.00186500 | -0.00142000 | -0.00090100 | -0.00025600 | -0.00017100 | 0.24130430 | 0.18806470 |

## Gaps and exclusions

No BSA/admin-credit monthly original or indexed CSEG was recovered for October2025–April2026. Current index/archives were inspected once, then specific missing-CSEG searches returned no new source. The current BSA table contains June–October2026 filled rates and later blanks; blanks are missing, never zero. No full-year2025 proof is available.

July2025 has MES usage-date transition July2 (tax owner's original), so a full calendar cycle requires allocation proof; August2025 transmission changed usageAugust27, while September CSEG still prints the older August rate. Reject both crossing cycles without allocation proof; do not let a monthly CSEG composite override an actual filed usage-date change. May/June2026 MES$.000151 is retained as published evidence with statutory-rate conflict recorded by tax owner, not automatically approved. July–October2026 CSEG publishes MES$.000150. The tax researcher additionally recovered the adopted July2026 environmental-update book (`.cache/delmarva_md/sources/tax/book_2026jul06.pdf`, R48/SGS55), filedJuly6/effective usageJuly1, confirming the boundary; its URL/hash is retained in the tax source ledger. May/June2026 actual filed$.000151 remains a separately documented rate, not silently substituted with a statutory assessment cap.

The June2025 supply archive contains proposed tariff leaves; not an adopted delivery-price authority. Use December2024/March2025 and current identical base prices plus adopted supply records, rather than treating proposed pages as effective. No export, NEM/community-solar settlement, missing-rate fallback, actual customer bill identity, complete amount due, or whole-bill optimum is established here.
