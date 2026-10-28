# Penelec Pennsylvania default PTC supply

Reviewed2026-10-28. Runtime utility key `firstenergy_pa_penelec`; module `penelec_pa`; initial plans **RS and GS-S (GS-Small)**. This packet verifies Penelec PA default PTC supply, not other FEPA rate districts, NewYork/Waverly service, customer eligibility or simulation results. No old utility files, runtime, tests or Git state were edited.

## Filed final prices and service clocks

All prices are **USD/kWh final PTCDefault composites**. Only the Penelec residential/commercial columns were transcribed.

| Service-rendered dates | RS residential | GS-S commercial | Original / physical page / printed203 revision |
|---|---:|---:|---|
| December1,2024–May31,2025 | .10474 | .10382 | Supplement11 /3 /Third |
| June1–November30,2025 | .11003 | .11405 | Supplement19 /3 /Fifth |
| December1,2025–May31,2026* | .11747 | .12155 | Supplement28 /3 /Sixth |
| June1–November30,2026 | .13142 | .12920 | Supplement36 /6 /Seventh; identical current fullbook203 |

The four windows establish requested January2025–October2026 **supply-source** coverage. Complete-bill coverage remains the intersection with independently verified Penelec delivery/riders, tax, billing rules and account facts. No full-year study or customer invoice is proved here.

`*` Supplement28 literally ends its rate window on **May30,2026**. The exact current official December2025 bill-insert link, `10693-Penelec-ABCs-Of-Shopping.pdf`, and the separately dated April2026 Penelec insert both explicitly publish the same .11747/.12155 prices **through May31,2026**. Original rider204 defines the six-month period beginningDecember1. These direct Penelec sources support May31 while the conflicting raw tariff wording remains preserved. No Met-Ed customer insert is used as Penelec date proof.

The PTC price changes apply to **service rendered**, with explicit June1/December1 boundaries. The price is calculated to the nearest .001cent/kWh; this rounds the published price, not the customer's kWh or cash bill. No partial-cycle allocation, customer quantity rounding or exact cash rounding is invented by this supply packet.

## Original preservation and applicability

`.cache/penelec_pa/sources/supply/supply_records.json` pins original URLs/SHA256s, full extracted text, physical pages,25 checked-in excerpt references, retained renders and the unavailable indexed route. `supply_snapshots.json` contains exact normalized prices, clocks, class conditions, formula composition and benchmark limits. Excerpts are in `supply_excerpts/`. Original bytes and full text remain ignored or in the previously retained common-source cache.

The common originals were reused **after SHA256 equality and Penelec-column/class inspection**, not after copying Met-Ed values:

- Supplement11 SHA `1f9ba4c52c8baf416018477039aff367396eb893f8479c8e668dee99a2633b39` and Supplement19 SHA `d11bc4fd1e9254c2d4648410919b578cdc00608a80e46b8ea0d162effe57e4f0`, retained in `.cache/firstenergy_research/` and pinned by the existing FirstEnergy manifest.
- [Supplement28](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/PA/tariffs/FEPA-Supp-No-28-PTC-HPS-Rider-Changs-12-1-2025.pdf) SHA `a5ebbe14bac4ca4807c8ce477323ffad850b34cc854f302b1e64f694e7ffb336`, retained by Met-Ed's source stream; unchanged original bytes reused.
- [Supplement36](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/PA/tariffs/FEPA-PTC-Effective-06-1-26.pdf) SHA `a8b0ff4be057ec7d19b9da1d5a9342054a00904b30f5d4797feff50b2e5e0eae`, with actual filed Penelec leaf203 and supporting Penelec schedules. Filing-transmittal proposal language is not alone adoption proof; the identical issued leaf currently published in the complete tariff corroborates the rates.
- Shared current248-page FEPA tariff SHA `665736ea46b7860651226605624c298b6990e3c0581166e543ccf27bd25b8f9d`, reused from `.cache/met_ed_pa/sources/delivery/tariff_current.pdf`, with Penelec applicability independently read. Delivery owns common-book preservation; there was no duplicate download.
- Shared [historical workbook](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/PA/tariffs/Historical-Rates.xlsx) SHA `b2d50924124cc6f760473950bd31988d3b46a23e447c900a0d77159373dc4a85`, `PTC - Res and Small Comm` Penelec rows8/14, columnsL–O. All eight numeric prices match; **June2025/2026 headers literally say June24**, whereas the filed leaves sayJune1. Preserve those raw headers but use the filed clock. Full workbook cells were already extracted and are hash-pinned separately from the original.

The four filed-rate tables and the provision matrix were rendered and visually checked. The Penelec row is the second district table; adjacent Met-Ed/PennPower/WestPenn values are excluded. June2025 and the correct current December2025 insert were visually checked for their date/price statements. Additional generated insert renders are retained as rendered-only until separately viewed; receipt flags distinguish them.

## Composite contents and separate DSS

Current original rider204–207, effectiveJanuary1,2024, defines:

`PTCDefault = (PTCCurrent + E) / (1-T)`

`PTCCurrent = current supply cost × loss factor + administration + PTCNITS`

The filed final PTC includes applicable default energy/capacity/PJM charges, loss adjustment, administration, AEPS net expenses, applicable NITS, reconciliation and PA gross-receipts-tax gross-up. **No additional auction tranche, LMP, PLC/NSPL capacity fee, PTC administration or second GRT multiplier is added.** Non-market-based transmission charges identified in DSS are expressly excluded from PTC DSExp2 on206; applicable non-bypassable DSS remains separately payable once under the delivery packet. PTC does not absorb delivery/riders or independently waive applicable sales tax.

Supplement36 physical18/21 provides these Penelec supporting calculations:

| Included supporting quantity | RS | Commercial GS-S |
|---|---:|---:|
| Current procured cost | .11435 | .11115 |
| Penelec loss factor |1.0573|1.0573|
| Loss-adjusted cost | .12091 | .11752 |
| Administration | .00006 | .00006 |
| Current total before GRT | .12097 | .11758 |
| Current including GRT,5.90%,factor1.062699 | .12855 | .12496 |
| Reconciliation including GRT | .00287 | .00424 |
| Filed PTCDefault | **.13142** | **.12920** |

These rounded supporting entries explain the already-filed final composite; they are not additional charges. Historical decompositions are not invented from Met-Ed or neighboring district calculations. Illustrative/estimated future or hourly computations are not used as adopted composite authority. December2026 prices are outside the initial requested source window.

## Penelec class and enrollment rules

Current physical65, first revised printed65 effectiveJanuary1,2025, explicitly groups **Met-Ed and Penelec**: nonresidential customers without demand meters, one delivery location, secondary service with stated transformer-capacity terms. An existing customer whose consumption exceeds1500kWh in two consecutive months within the most recent twelve months **may lose eligibility**, with utility reassignment based on estimated demand. This is not PennPower/WestPenn's differently worded initial “loads up to1500kWh” clause. Independently confirm assignment/history; a low study peak or isolated monthly usage does not prove eligibility.

**Physical66's visual provision matrix matters:** Penelec is marked **A and C**, notB. A is contract terms; C permits utility-imputed fixed usage. ProvisionB, the historical500kW **GSDS** rule, is marked **PennPower only**. The generic HP rider208 mentions GSDS but does not override this schedule-specific matrix. Do not assert Penelec has an automatic500kW GSDS transfer rule based on that generic paragraph. The initial ordinary metered branch excludes utility-imputed fixed usageC, hourly/TOU election, competitive supply and unverified classification. No NJ annualNovember PLS rule is imported.

Physical65 says PTC applies unless GS-S elects hourly service. Physical208 permits voluntary HP for GS-S/GS-M(PTC) with required smart metering, beginning on the stated next scheduled meter read. Confirm ordinary PTC enrollment; do not implement the HP LMP/capacity formula. RS is explicitly in the residential PTC class. Other commercial schedules listed in the PTC table do not become supported merely by sharing a price.

## Independent benchmark receipts and source traps

The [official Penelec bill-insert index](https://www.firstenergycorp.com/help/billingpayments/about_your_bill/bill_inserts/penelec.html) and exact linked original PDFs are retained.

| Actual retained source | Numeric check and date limitation |
|---|---|
| December2024 insert | .10474/.10382 throughMay31,2025, matchingSupplement11 |
| June2025 insert | .11003/.11405 matchSupplement19; **printed end header wrongly extends throughMay31,2026**. The adopted November30,2025 endpoint controls. Do not apply those prices to December2025 onward. |
| Current index's December2025 link, `10693-Penelec-ABCs-Of-Shopping.pdf` | **Correct** .11747/.12155 throughMay31,2026, code `COMM10693-01-26-AI` |
| April2026 insert | Correct .11747/.12155 throughMay31,2026 |
| August2026 insert | Correct .13142/.12920 throughNovember30,2026 |

**Separate unavailable indexed asset:** web search exposed a different `2025-12%20Penelec%20ABCs%20Of%20Shopping.pdf` URL with stale June prices. That URL returned404; no original bytes were retained and it is not numeric or date authority. It is distinct from the actual correct current December2025 link above. Do not describe the retained current December original as wrong. The failed route is recorded once and was not retried unchanged.

The PTC benchmark is generation/transmission **component-only**; inserts expressly exclude the other monthly bill costs. No independently matched actual complete Penelec bill was found by this supply stream. NY/Waverly materials also appear in the provider index and remain excluded from PA source scope. Delivery/taxes/account approvals, minima, missing-data/DST checks and all engine/matrix/browser acceptance remain separately required. No original/source ledger/runtime/test/Git edits outside the owned new supply packet were performed.
