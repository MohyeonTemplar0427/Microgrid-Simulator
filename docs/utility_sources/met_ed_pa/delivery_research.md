# Met-Ed Pennsylvania RS / GS-S — delivery evidence

Research date: October27,2026. Utility is **FirstEnergy Pennsylvania Electric Company, Met-Ed rate district**, plansRS andGS-Small. All prices below are **Met-Ed columns**, not Penelec/PennPower/WestPenn. SupplyPTC, jurisdiction/tax eligibility, percentage bases, billing clocks and ordinary DER approval have separate reviews.

## Originals and provenance

Existing `docs/utility_sources/firstenergy/manifest.json` was consulted first. Every retained PA original selected from that manifest matched its recorded SHA256; no duplicate regulator downloads were needed. Originals remain in `.cache/firstenergy_research/`; scoped text was written only under the new Met-Ed delivery cache. The [official tariff index](https://www.firstenergycorp.com/customer_choice/pennsylvania/pennsylvania_tariffs.html) supplies the current248-pagebook and historicalPTC workbook. One current download was preserved, SHA256`665736ea46b7860651226605624c298b6990e3c0581166e543ccf27bd25b8f9d`, matching the already-retained current file. The historicalworkbook is handed to supply research and is not delivery-rate authority.

Specific additional provenance verification resolved two useful retained books: the [datedJanuary2026 official book](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/PA/tariffs/fe-pa-retail-tariff-1-1-26.pdf) downloaded bytes match retained `pa-2026-01.pdf`, SHA256`6161113b3a7e6a1ee77b25d600eadbc6c60dbd1ba7c44f6864961a8510c76202`; the [datedApril2026 official book](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/PA/tariffs/fe-pa-retail-tariff-4-1-26.pdf) was preserved, SHA256`2d63d379fab461a3e602d9d7b43cd0625f1acf8005613c92fda03b1c92749dbb`.

Retained June2024officialbook provenance is independently matched to archivecapture20240607145718 through its exact SHA1base32`LAPNWKRBA5KWKCBCEAKI6IYYTFSIZXAN` in the existingCDX receipt; SHA256`8a9865ed187ebe37352751eccdb48f908ef8c3282e8ea210c59c6c723b732e69`. Retained June12,2025book matches its existing archive-download receipt, SHA256`950266135e6348aac8d173a794aa6117e65868cde47636a71a9c0922e17d410b`.

Durable packet:

- `.cache/met_ed_pa/sources/delivery/delivery_records.json`:23original/index/workbook receipts, exactURL/hash/pagecount and reused-original paths.
- `delivery_snapshots.json` in that directory:29component versions,22monthly delivery rows, exact physical/printed page/revision/effective/excerpt hashes, qualifiers and gaps.
- [delivery_excerpts](delivery_excerpts/):44selected original page excerpts. Ten critical tables were rendered and visually reviewed for district, sign and units; the packet lists exact reviewed pages. No PDF was modified.

## Dated Met-Ed prices

Dollar units unless a percentage is explicitly shown. The source tables often print cents/kWh: divide by100. Percentages below are percentages, not decimal fractions.

| Component |2025 dates / RS |2025 dates / GS-S |2026 known prices |
|---|---|---|---|
| Base customer/month |11.25, fromJan1|23.78, fromJan1|Unchanged|
| Base distribution/kWh |.05138|.05092|Unchanged|
| USC/kWh, residentialonly |.00612 Jan–Jul; .00900 Aug–Dec|Notapplicable, not a waived price|RS .01283 Jan–Dec|
| EEC/kWh |.00176 Jan–May; .00210 Jun–Dec|.00392 Jan–May; .00322 Jun–Dec|Jan–May same; fromJun1 RS .00215 /GS-S .00178|
| SMT/month |+.13|+.58|RS+.06 /GS-S **−.04** fromJan1|
| DSS/kWh |.00317 Jan–May; **.00123** Jun–Dec|.00052 Jan–May; **−.00018** Jun–Dec|Jan–May same; fromJun1 RS .00546 /GS-S .00208|
| StandaloneSPVRC/kWh |−.00001 Jan–May;0 Jun–Dec|Same|0 throughMay31; currentJune2026SPVbalance component explicit0 withinDSS|
| TCJA |0% Jan–Jun; **+1.12%** Jul–Dec|Same|0% fromJan1|
| STAS |+.02% Jan–Dec|Same|−.02% fromJan1|
| January2025one-time refund |**−6.53/bill**|**−4.18/bill**|No continuation|

DSIC exact quarterly percentages:2025Jan–Mar0%;Apr–Jun **.17%**;Jul–Sep0%;Oct–Dec0%.2026Jan–Mar0%;Apr–Jun **.12%**;**July–Septemberunverified**;October–December **2.02%**. No neighboring district or quarterly carryforward fills that gap. The bounded missing-window search stopped after the gap was recorded.

These prices establish a proposed delivery intersection of full2025,January–June2026 andOctober2026 within the requested horizon. Complete bills still require the independently verifiedPTC, account/date rules, refund treatment and percentage bases. No validation or simulation claim follows from a complete price packet.

## Replacement sheets and important units

January2025base rates are Supplement14, approved as effective by operation of law in the retained PUC December31,2024letter (`papuc-1860899`). Supplement14's originally printed zeroSMT was replaced at the sameJanuary1effective date by Supplement16: use the secondrevised198, not zero.

DSS has another material replacement. The original May1,2025filing and May15archivedbook show residential .12447cents andGS-S−.01601cents on thirdrevised213. The **June12official archivedbook** and independently verified January2026officialbook instead show **fourthrevised213**, supersedingthird, with the sameJune1effective date and .123/−.018cents. Those replacements produce the dollar rates in the table. Do not use the earlier higher-precision submission as the executed June rate. The annualDSS computational period isJune1–May31; its actual published total is applied once. Its non-market transmission, uncollectible, administration and other constituent costs are not additional retail adders to reconstruct separately.

Met-EdSMT is a **fixed monthly charge/credit**. WestPenn's residential per-kWhSMT must not be copied. PositiveMet-EdTCJA1.12% is visually explicit despite stale generic prose saying “negative surcharge”; do not import WestPenn's−.53%. STAS is service-effective; TCJA is **bills-rendered**. Their exact bases/ordering are owned by tax/rules review and must not be guessed from a general subtotal.

## One-time credit and SPVRC

The January2025refund is documented in `papuc-1858401` physical4, with amounts already grossed up forGRT. PUCacceptance `papuc-1860899` physical1–2 confirms the one-time **January2025bills-rendered** credit, separately labeled “Refund for Non-eligible costs.” The filing says the eventual actual refunds will be reported later. Require an established eligible January-billed account; do not extend it, double-gross it up or imply an account actually received it without evidence. The source packet retains the accepted class amounts and their approval.

Pre-June2025SPVRC is a small **credit**, not zero. Its self-generation exclusion is not a genericPV exemption: first qualification on printed234 is expressly restricted toGS-Large/GP/TP. Separate rules review confirms RS/GS-S therefore retain the credit on delivered imports in grid/PV/storage scenarios. June2025standaloneSPVRC is explicitly0 and the residual is recovered throughDSS. CurrentJune2026printed215A likewise publishes a0SPVcomponent insideDSS; its generic amortization narrative retainsJune2025–May2026dates, so post-May2026standalone/absorbed treatment needs the separately documented rules interpretation rather than an invented standalone price.

## Eligibility and scope safeguards

RS is single-phase, one residential meter, allowing no more than2000W incidental nonresidential connected load in the Met-Ed/Penelec provision. RS printed62 adds a special excess25kW demand charge and a75%prior-eleven-month excess-demand minimum when applicable. It also identifies demand-meter installation triggers. An ordinary no-demand scope must independently exclude that active branch; PV/storage does not erase history.

Met-EdGS-S requires nonresidential service **without a demand meter**, one delivery/transformer location and confirmed utility assignment. If usage exceeds1500kWh in two consecutive months within the latest12months, the utility may transfer the account based on estimated demand. This is not JCP&L's10kW rule or Rockland's mere nondemand-billing category. The contract, history, quantities used for eligibility, standby/PartialService and interconnection rules remain separately owned. GS-S has a one-yearDeliveryService contract; fixed-usage/special/computed load and unusual facilities are separate branches.

No generic “SBC” is added: the Met-Edrider matrix separately identifiesSTAS,TCJA,USC,EEC,SMT,DSS,SPVRC,DSIC and specializedLEDC. No extraPLC/NSPL, wholesaleLMP or neighboring-utility fee belongs in ordinaryRS/GS-S defaultPTC bills. No independent complete invoice benchmark was recovered in this bounded delivery pass; the publishedPTC benchmark is supplied separately. The retained refund schedule is an independent fixed-credit check, not whole-bill calibration.
