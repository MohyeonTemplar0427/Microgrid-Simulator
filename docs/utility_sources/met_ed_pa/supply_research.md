# Met-Ed Pennsylvania default PTC supply

Reviewed2026-10-27. Runtime utility key `firstenergy_pa_met_ed`; module `met_ed_pa`; initial plans **RS residential and GS-S (GS-Small), non-demand metered**, ordinary default PTC only. Utility/rate district, supplier enrollment, account classification, PA jurisdiction and PJM metadata remain separate. This is supply-source evidence, not customer eligibility or simulation proof.

Original/filed values below are **USD/kWh final PTCDefault composites**. Apply each once; do not substitute another FE PA district's column, an auction tranche or an hourly PJM price.

| Service-rendered window | Met-Ed RS | Met-Ed GS-S | Original source / physical page |
|---|---:|---:|---|
| December1,2024–May31,2025 | .11011 | .11048 | Supplement11,3rd revised203,physical3 |
| June1–November30,2025 | .11903 | .11574 | Supplement19,5th revised203,physical3 |
| December1,2025–May31,2026* | .12965 | .12931 | Supplement28,6th revised203,physical3; May31 corroborated below |
| June1–November30,2026 | .13951 | .12864 | Supplement36,7th revised203,physical6; identical current fullbook physical203 |

These windows cover the requested January2025–October2026 **supply** dates. Complete-bill scope depends on separately verified delivery, riders, account facts, billing rules and validation. This packet does not enable December2026 prices or claim a historical matrix passed.

`*` **Preserved source discrepancy:** Supplement28 literally says “through May30,2026.” The independently published [Met-Ed ABCs shopping bill insert](https://www.firstenergycorp.com/content/dam/customer/billinserts/10692-Met-Ed-ABCs-Of-Shopping.pdf), original physical1, explicitly states the same RS12.965c and GS-Small12.931c **through May31,2026**. Original PTC rider204 also defines the six-month period beginningDecember1. The source packet therefore supports May31 with that direct utility publication plus the unchanged rider clock, while retaining the raw conflicting tariff text. It does not silently edit the original or infer a neighboring rate. The insert is dated by publication code `COMM10692-01-26-AI`.

## Receipt and authority hierarchy

`.cache/met_ed_pa/sources/supply/supply_records.json` pins URLs, original/text SHA256s, physical pages,23 checked-in excerpt references and visual receipts. `supply_snapshots.json` contains normalized exact literals, dates, class rules and limitations. Selected source text is in `supply_excerpts/`; full originals/extractions remain ignored.

- Supplements11 and19 reuse `.cache/firstenergy_research/` originals after matching SHA256 against `docs/utility_sources/firstenergy/manifest.json` and inspecting the **Met-Ed** RS/commercial columns. No old ledger was changed. Their hashes are `1f9ba4c52c8baf416018477039aff367396eb893f8479c8e668dee99a2633b39` and `d11bc4fd1e9254c2d4648410919b578cdc00608a80e46b8ea0d162effe57e4f0`.
- [Supplement28](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/PA/tariffs/FEPA-Supp-No-28-PTC-HPS-Rider-Changs-12-1-2025.pdf) is the published December2025 rate leaf. Its date discrepancy is explicitly retained.
- [Supplement36](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/PA/tariffs/FEPA-PTC-Effective-06-1-26.pdf) includes the filed June2026 leaf and supporting computations. Its actual rates are corroborated by the current published tariff, official historical workbook and same district/class. The transmittal's “proposed” filing language does not alone establish adoption; the identical leaf currently in force supplies that confirmation.
- The delivery stream owns the single current248-page FE PA fullbook, `.cache/met_ed_pa/sources/delivery/tariff_current.pdf`, SHA256 `665736ea46b7860651226605624c298b6990e3c0581166e543ccf27bd25b8f9d`. This stream reuses its relevant unchanged January2024/January2025 leaves without another download.
- The [official historical workbook](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/PA/tariffs/Historical-Rates.xlsx), sheet `PTC - Res and Small Comm`, Met-Ed rows7 and13, columnsL–O, independently repeats all eight numeric prices. Its **raw June2025/2026 headers say June24**; adopted rate leaves explicitly sayJune1 and control the clock. Workbook dates are not substituted for the filed dates. Both raw header values and all workbook cells are preserved in `historical_rates_cells.json` and the scoped cell excerpt. A duplicate same-content workbook was also downloaded by delivery before coordination completed; aggregation should deduplicate by hash.
- [Met-Ed June2026 illustrative calculations](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/PA/tariffs/ME-Rate-District-PTC-and-HP-Illustrative-6-1-2026.pdf) are retained as **estimated/illustrative only**, not independent adopted composite authority. No tranche or hourly formula replaces the actual filed rate.

The four rate leaves and bill insert were rendered and visually reviewed: Met-Ed columns, signs, units, revision/effective statements and May30/May31 discrepancy were checked. The four-window montage is a derivative review aid, not a source original.

## Included costs versus separate delivery riders

Current tariff original pages204–207, issuedDecember22,2023/effectiveJanuary1,2024, specify:

`PTCDefault = (PTCCurrent + E) / (1-T)`

`PTCCurrent = (current cost component × loss factor) + administration + PTCNITS`

The procured default supply/PJM costs, capacity, ancillary services, losses, administration, AEPS net expenses, applicable NITS, reconciliation and Pennsylvania gross-receipts-tax gross-up are already represented in the filed PTCDefault. Page207 definesT as applicable Pennsylvania gross-receipts tax. Add **no extra LMP, PLC/NSPL capacity charge, administrative fee, AEPS charge or second GRT multiplier** to this composite. GRT and separately applicable sales taxes are distinct; the tax stream owns the latter.

Page206 expressly excludes the **Non-Market Based Services Transmission Charges identified in the Default Service Support Rider** from PTC's DSExp2. DSS is non-bypassable and separately applicable to delivery customers, so this supply packet does not absorb or waive the independently verified DSS charge. Delivery/rider totals still add once according to their own source schedules.

Supplement36 supporting physical9/12 independently reconcile June2026 final prices:

| Filed supporting quantity | RS | Commercial GS-S |
|---|---:|---:|
| Current procured cost | .12157 | .11099 |
| Loss factor |1.0515|1.0515|
| Loss-adjusted cost | .12783 | .11671 |
| Administration | .00006 | .00006 |
| Current total before GRT | .12789 | .11677 |
| Current including GRT (5.90%; factor1.062699) | .13591 | .12409 |
| Reconciliation including GRT | .00360 | .00455 |
| Filed final PTCDefault | **.13951** | **.12864** |

These rounded supporting entries explain the final composite; they are not separately rebilled. Historical component decompositions are not invented where only the final adopted composite is retained. Exact final literals, rather than reconstructed rounded arithmetic, govern the model.

## Eligibility and enrollment

Current physical65/printed65, first revision effectiveJanuary1,2025, defines **Met-Ed/Penelec GS-Small** as nonresidential service without demand meters at one delivery location, secondary service with stated transformer-capacity terms. An existing customer's usage **over1500kWh in two consecutive months in the most recent twelve months** may cause loss of eligibility and reassignment based on the utility's estimate of demand. This is not a blanket initial1500kWh cap copied from PennPower/WestPenn's separately worded clause. Require independently confirmed utility-assigned and retained GS-S classification plus history; study peak or monthly usage alone does not establish the account class. Parent may impose a stricter study bound without representing it as a tariff threshold.

Physical65 says GS-S uses default PTC unless it elects hourly default supply. Physical66's special GSDS rule places customers with historical billing demand500kW or more, otherwise qualifying GP/TP but on GS-S because they lack a contract, on hourly pricing. That branch is excluded. Physical208 allows qualifying GS-S customers with required smart metering to elect hourly service voluntarily. Confirm no HP/TOU election, no GSDS condition and no competitive supplier; no JCP&L PLS/November or NJ500kW rule is imported. RS is expressly in the residential PTC class, while GS-S is in commercial PTC.

The filed PTC clock is **service rendered**, changingJune1 andDecember1; the price is determined to the nearest .001cent/kWh. That statement rounds the published **price**, not the customer's kWh or cash bill. Quantity/cash rounding and unsupported partial/transition-cycle allocation are not invented by supply research; tax/rules review controls those boundaries.

## Independent benchmarks and remaining limits

The separately published workbook confirms all four rate windows' numeric values, with date-header limitations above. The ABCs bill insert confirms the December2025 rates, exact May31 endpoint, GS-Small class label and that PTC pays for generation/transmission while other monthly costs remain separate. Neither supplies an independently itemized complete Met-Ed bill. The supporting June2026 schedules provide rate-component arithmetic, not a customer invoice or optimization proof.

The bounded pass recovered all requested PTC windows without a blocked numerical source route. No repeated unchanged archive/PUC route, neighboring district substitution, proposed/estimated-rate adoption, missing-rate backfill or wholesale settlement was used. Default-service applicability, active account/interconnection facts, delivery/rider history and numerical validation remain separate required checks. Exports/NEM settlement, hourly/TOU, GSDS, other rate districts and unverified account classes are outside this packet.
