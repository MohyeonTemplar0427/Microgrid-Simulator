# Penn Power PA default PTC supply

Reviewed2026-10-29. Initial utility key `firstenergy_pa_penn_power`, module `penn_power_pa`, plans **RS residential and GS-S (GS-Small)**, PennPower rate district of FirstEnergy Pennsylvania Electric Company. This packet owns supply evidence only; no runtime, tests, old source ledgers or Git state were changed.

## Filed prices and clocks

All numbers are **USD/kWh final PTCDefault composites** from the PennPower columns, independently read and visually checked.

| Service-rendered dates | RS | GS-S | Supplement / physical page / printed203 revision |
|---|---:|---:|---|
| December1,2024–May31,2025 | .11168 | .12098 |11 /3 /Third |
| June1–November30,2025 | .11857 | .12726 |19 /3 /Fifth |
| December1,2025–May31,2026* | .12606 | .13729 |28 /3 /Sixth |
| June1–November30,2026 | .13477 | .13729 |36 /6 /Seventh; identical currentbook203 |

These establish the requested January2025–October2026 **supply-source** coverage, not complete-bill or simulation coverage. June2026 GS-S's final price is unchanged from December2025, although the supporting supply/reconciliation computation changes. Preserve both filed windows and component provenance.

`*` Supplement28 literally prints an end date ofMay30,2026. PennPower's **actual current December2025 index link**, `10694-Penn-Power-ABCs-Of-Shopping.pdf`, and the separately dated April2026 PennPower insert publish the same .12606/.13729 prices **through May31,2026**. Original rider204 defines the six-month period beginningDecember1. Those direct PennPower sources support May31 while retaining the raw inconsistent wording; no neighboring district's insert is substituted.

PTC prices are for **service rendered**, with explicitJune1/December1 boundaries. The filed price is determined to the nearest .001cent/kWh. This statement does not round customer quantities or cash bills and does not establish partial-cycle allocation rules.

## Provenance and preservation

`.cache/penn_power_pa/sources/supply/supply_records.json` pins original URLs/SHA256s, complete extracted text,26 selected excerpt references and render-review flags. `supply_snapshots.json` contains exact normalized prices, class restrictions, composition and source limits. Checked-in excerpts are in `supply_excerpts/`. Common original bytes were reused read-only after equality checks against earlier retained receipts and independent **PennPower** applicability review:

- Supplement11 SHA `1f9ba4c52c8baf416018477039aff367396eb893f8479c8e668dee99a2633b39`; Supplement19 SHA `d11bc4fd1e9254c2d4648410919b578cdc00608a80e46b8ea0d162effe57e4f0`, retained in `.cache/firstenergy_research/` with the existing FirstEnergy manifest.
- [Supplement28](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/PA/tariffs/FEPA-Supp-No-28-PTC-HPS-Rider-Changs-12-1-2025.pdf) SHA `a5ebbe14bac4ca4807c8ce477323ffad850b34cc854f302b1e64f694e7ffb336` and [Supplement36](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/PA/tariffs/FEPA-PTC-Effective-06-1-26.pdf) SHA `a8b0ff4be057ec7d19b9da1d5a9342054a00904b30f5d4797feff50b2e5e0eae`, reused from the retained Met-Ed supply cache. A filing cover's proposed-effective language alone is not adoption proof; the identical issued June2026 leaf in the currently published complete tariff corroborates the final rate.
- Common current248-page FEPA tariff SHA `665736ea46b7860651226605624c298b6990e3c0581166e543ccf27bd25b8f9d`, reused from `.cache/met_ed_pa/sources/delivery/tariff_current.pdf`; no duplicate download. Relevant unchanged original rider pages204–209 carry January2024/June2026 footers as individually retained.
- [Official historical workbook](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/PA/tariffs/Historical-Rates.xlsx) SHA `b2d50924124cc6f760473950bd31988d3b46a23e447c900a0d77159373dc4a85`: `PTC - Res and Small Comm`, **PennPower rows9/15**, columnsL–O, confirms all eight numeric prices. Raw June2025/2026 headers sayJune24; the actual filedJune1 clock controls. Full cell extraction and scoped raw values remain pinned.

The four filed-price tables, current provision matrix and June/current-December inserts were rendered and viewed. PennPower is the **third** district table. Other retained renders are labeled rendered-only where they were not separately viewed. No utility ledger is aggregated yet.

## Composite components and separate DSS

Original rider204–207 defines `PTCDefault=(PTCCurrent+E)/(1−T)` and `PTCCurrent=currentCost×PTCloss+administration+PTCNITS`. Filed PTC includes applicable procured energy/capacity/PJM supply charges, line loss, administration, AEPS net expenses, applicable NITS, reconciliation and PA GRT. Add **no separate LMP, auction tranche, PLC/NSPL capacity charge, administration or second GRT gross-up**.

Page206 expressly excludes non-market-based transmission charges identified in DSS from PTC DSExp2. Applicable non-bypassable DSS remains separately priced once under the delivery packet; PTC does not waive delivery/riders or any independently applicable sales tax.

Supplement36 physical27/30 gives PennPower-specific June2026 supporting calculations:

| Included quantity | RS | Commercial GS-S |
|---|---:|---:|
| Current procured cost | .11735 | .11005 |
| **PTC** loss factor |1.0661|1.0661|
| Loss-adjusted cost | .12511 | .11732 |
| Administration | .00006 | .00006 |
| Current total before GRT | .12517 | .11738 |
| Current including GRT,5.90%,factor1.062699 | .13302 | .12474 |
| Reconciliation including GRT | .00175 | .01255 |
| Filed final PTCDefault | **.13477** | **.13729** |

These rounded components explain the filed final price, not additional bill lines. Historical decompositions are not invented. **PennPower default-PTC loss1.0661 differs from its HP GS-S loss1.0515 on209**; the hourly factor is not used for ordinary PTC. Illustrative future/HP formulas and December2026 estimates are outside adopted initial rate scope.

## PennPower class rules and exceptions

Current65's PennPower/WestPenn clause describes secondary light/power through one metering installation for “loads up to1,500kWh.” Its ongoing rule says an existing customer exceeding1500kWh/month in two consecutive months of the most recent twelve months may lose GS-S eligibility. This PennPower wording differs from the Met-Ed/Penelec availability clause. Independently confirm utility assignment/history and actual operating classification; model quantities alone do not establish it. Interpretation of qualification gross/native/net quantities belongs to the full rules packet.

The provision matrix on66 visually marks **PennPower A+B+C+F**. ProvisionB genuinely applies to PennPower: customers with **historical billing demand500kW or above**, **otherwise qualifying forGP/TP**, but onGS-S **because they are not under contract**, are placed on hourly default service. All stated conditions are retained; this is not a neighboring utility's annualPLS/November rule or an instantaneous-study-peak test. Initial ordinary PTC excludes GSDS and voluntary HP/TOU/competitive supply. Page208 allows voluntary HP for qualifying GS-S with required smart metering and the next-scheduled-meter-read clock.

A is contract terms and C is Company-imputed fixed usage; initial ordinary metered scope excludes C and special/early-termination arrangements. **A bounded two-route primary-source review recovered the literal F definition.** The archived official June2024 fullbook, Original67 physical67, explicitly labels **F. THREE-PHASE**, with F marked for PennPower on Original66. Current Original67 labels the same substantive paragraph **C. THREE-PHASE**, despite both carrying the January1,2024 effective footer. The normalized clause body is identical (SHA256 `b69c335423e63168301ed8b855e819d65ea988e9c2d7134de743fe8bd2480de2`). This is direct historical lettering evidence, not an inferred D/E/F mapping. The paragraph describes available standard single/three-phase secondary service, separate billing unless feasible combined-meter wiring, and customer lighting equipment for three-phase service; it prints no standalone numeric charge. Accepted Supplement14 revises65/66 then68, without a67 revision in that packet. The version-label inconsistency remains visible. Initial ordinary scope requires Company-confirmed single-phase/single-meter service with no combined account, three-phase equipment, added facilities or special recurring treatment. The independent tax reviewer separately read/rendered both and confirmed the identical body; there is no remaining F-specific subtotal exclusion for that known narrow branch. Do not borrow Penelec's A+C-only matrix.

The customer shopping insert's shorthand “General Primary-GS-Small and Medium” does not override the adopted **General Service Secondary—Non-Demand Metered** GS-S designation. Other listed commercial schedules do not become supported merely by sharing a PTC price.

## Independent benchmarks and remaining limits

The [actual official PennPower bill-insert index](https://www.firstenergycorp.com/help/billingpayments/about_your_bill/bill_inserts/penn_power.html), exact linked originals and dates are preserved. No stale indexed December filename was guessed or retried.

- June2025 original correctly gives .11857/.12726 but its header wrongly extends throughMay31,2026. FiledSupplement19 endsNovember30,2025 and controls; do not extend June prices into December.
- The correct current December2025 link `10694-Penn-Power-ABCs-Of-Shopping.pdf`, publication code `COMM10694-01-26-AI`, and April2026 insert correctly give .12606/.13729 throughMay31,2026.
- August2026 gives .13477/.13729 and an apparent “November3o” letter-o typography in extracted original text; the filed rate leaf explicitly saysNovember30,2026 and controls.
- The provider workbook confirms first-window January–May2025 prices; no separate December2024 customer insert was linked in the scoped current index. This is a benchmark availability limit, not a missing filed-rate window.

These are generation/transmission **component benchmarks**. They expressly exclude other monthly costs; no independently matched actual complete PennPower invoice was established. All exact linked requests succeeded; no blocked numerical source or unchanged-route retry was needed. Delivery, mandatory riders, taxes, minima, full class/contract terms, active interconnection/account facts and dated simulation acceptance remain separate. Exports, HP/GSDS/TOU, imputed quantities, special contracts and unverified settlement are excluded.

## Bounded F comparison receipt

Only two specific retained primary routes were inspected: the official archived June2024 tariff (`pa-june2024.pdf`, SHA `8a9865ed187ebe37352751eccdb48f908ef8c3282e8ea210c59c6c723b732e69`) and accepted PUC Supplement14 (`papuc-1858451.pdf`, SHA `b74772efdc7b2c5a7bb527f6b34b007826b8e17a1e9efd387d6f5777f1e0ae99`). The already-inspected current book was the comparator. No new network request or unchanged failed route was used; the lookup stopped after two. Exact original/excerpt/render pins, raw and normalized bodies, and the literal F-to-C diff are in `.cache/penn_power_pa/sources/supply/gap_review_f/`. Existing source bytes were preserved.
