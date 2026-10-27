# Atlantic City Electric delivery research

Verified 2026-10-27. Scope is Atlantic City Electric New Jersey RS ordinary residential and MGS-Secondary ordinary general service, with BGS-RSCP supply verified separately. Delivery utility, supplier, jurisdiction, PJM territory and wholesale prices remain separate facts. No production/test/shared-file or Git mutation was made by this research.

## Preserved evidence

The exact primary-source packet is `.cache/atlantic_city_electric/sources/delivery/delivery_snapshots.json`: one object per adopted February2025, June2025, July2025, October2025, September2026 and October2026 tariff book. Each object retains original URL/SHA256/physical-page count, rate-table physical page, printed sheet and its own effective date. It contains literal RS/MGS customer, distribution, transmission and non-BGS riders. This is a set of source snapshots, not an interpolated monthly ledger. Full originals/text and the expanded receipt are beside it in `delivery_records.json`; selected original wording is checked in under `delivery_excerpts/`.

Official current index discovery: the public content API at `https://eudapi.atlanticcityelectric.com/content-api/api/content/products/other/pages`, queried with `url=/MyAccount/MyBillUsage/Pages/Current-Tariffs.aspx&environment=live`, returned an explicit redirect to `/my-account/my-dashboard/rates-tariffs/current-tariffs`. That target yielded the actual current document catalog. Both JSON responses are preserved. The current index has no historical archive link. Specific indexed historical books and a cited official September2026 book were then retrieved; unchanged failed routes were not retried.

Primary books:

- [February1,2025 SectionIV](https://www.atlanticcityelectric.com/cdn/assets/v3/assets/blt407b5f1850a51a1b/blt433389f747df102f/679d15624d805f7db588d91a/NJ_Tariff_Section_IV_EFF_2.1.25_ZEC.pdf?branch=prod_alias),96physical pages.
- [June1,2025 SectionIV](https://www.atlanticcityelectric.com/cdn/assets/v3/assets/blt407b5f1850a51a1b/blt433389f747df102f/683f33006dffb339d38ca110/NJ_Tariff_Section_IV_EFF_6.1.25_BGS_BGS_RECO_1.pdf?branch=prod_alias),96pages.
- [July1,2025 SectionIV](https://www.atlanticcityelectric.com/cdn/assets/v3/assets/blt407b5f1850a51a1b/blt433389f747df102f/6865b21243e27fd3754fa950/NJ_Tariff_Section_IV_EFF_7.1.25_Elec_Rate_Mit.pdf?branch=prod_alias),96pages.
- [October1,2025 SectionIV](https://www.atlanticcityelectric.com/cdn/assets/v3/assets/blt407b5f1850a51a1b/blt433389f747df102f/68dd58af4ef0714a0f199592/NJ_Tariff_Section_IV_EFF_10.1.2025_BGS_Recon.pdf?branch=prod_alias),96pages.
- [September1,2026 SectionIV](https://www.atlanticcityelectric.com/cdn/assets/v3/assets/blt407b5f1850a51a1b/blt433389f747df102f/6aa85773fb097ba01be38a19/NJ_Tariff_Section_IV_Eff._09.01.2026_BGS_.pdf?branch=prod_alias),75pages.
- [October1,2026 SectionIV](https://www.atlanticcityelectric.com/cdn/assets/v3/assets/blt407b5f1850a51a1b/blt433389f747df102f/6abe603b9c1713f986c691b5/NJ_Tariff_Section_IV_Eff._10.01.2026_EECEC_T_.pdf?branch=prod_alias),75pages.

Also preserved: current SectionsI/III effectiveJune4,2026 (17pages); current SectionII effectiveDecember1,2025 (39pages); adopted [May21,2025 RGGI order](https://www.nj.gov/bpu/pdf/boardorders/2025/20250521/2D%20ORDER%20ACE%20Rider%20RGGI%20True%20Up.pdf) (84pages); adopted [November21,2025 base-rate order](https://www.nj.gov/bpu/pdf/boardorders/2025/20251121/2F%20ORDER%20ACE%20BRC.pdf) (380pages, including clean/redline settlement exhibits). Proposed-looking exhibit headings must be read with the dispositive adoption and final filed tariff; they do not independently authorize unrelated proposed rates.

## Base delivery and transmission

Dollar rates; original schedules include CBT/SUT provisions. Do not add a blanket tax percentage. Summer is June–September; winter October–May. Root's tax/rules review determines applicability and cycle allocation separately.

| Adopted leaf effective | RS fixed/month | RS summer first750/excess kWh | RS winter all kWh | MGS single/three-phase fixed | MGS summer/winter kWh | MGS summer/winter kW | RS transmission/kWh | MGS transmission summer/winter per kW above3 |
|---|---:|---|---:|---|---|---|---:|---|
| September1,2024 (Feb/Jun/Jul2025 snapshots) |6.75|.082119/.096411|.074735|12.55/14.60|.056849/.050317|3.49/2.86|.041092|8.24/7.86|
| September15,2025 (Oct2025 snapshot) |6.75|.082119/.096411|.074735|12.55/14.60|.056849/.050317|3.49/2.86|.035260|5.92/5.53|
| December1,2025 (Sep2026 snapshot) |6.75|.095030/.111568|.086485|13.99/16.27|.061560/.054488|3.89/3.19|.035260|5.92/5.53|
| October1,2026 (Oct2026 snapshot) |6.75|.095030/.111568|.086485|13.99/16.27|.061560/.054488|3.89/3.19|.037688|6.88/6.49|

RS winter sheet prints a first500kWh block, but both winter prices are identical. Reliability Must Run transmission surcharge is explicitly zero in these sheets. Transmission is part of BGS supply treatment and must not also be added as wholesale PJM charges. Physical source mapping: old RS7/printed5; old MGS16/printed11. Current RS7/printed5; current MGS12/printed8. Root's supply evidence owns BGS energy, reconciliation, TEC, eligibility and effective-date intersections.

## Non-BGS delivery riders

All per-kWh unless stated; negative rates are credits. SBC and RGGI/EECEC have component breakdowns in the JSON packet; their published totals were checked with Decimal arithmetic. The packet retains all non-overlapping components so a total is never added again to its subcomponents.

| Source regime | NGC | SBC total | RGGI/EECEC total | RS IIP | MGS IIP kWh + kW | RS CIP | MGS CIP | EDIT | ZEC inclSUT |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| Feb2025 snapshot |.003672|.011455|.005660|.001711|.001475 + .05/kW|.004224|-.013181|0|.004265|
| Jun/Jul2025 snapshots |deleted|.009300|.007121|.001711|.001475 + .05/kW|.008859|-.009008|0|0|
| Oct2025 snapshot |deleted|.010839|.007121|.001711|.001475 + .05/kW|.008859|-.009008|0|0|
| Sep2026 snapshot |deleted|.010672|.007121|0|0 + 0/kW|.007279|.002392|0|-.004265|
| Oct2026 snapshot |deleted|.009749|.010510|.000442|.000269 + .02/kW|.001819|.002096|0|-.004265|

These are snapshot rows with distinct effective dates, **not** rates automatically applied for the whole named year. In particular:

- NGC .003672 effectiveJanuary1,2025, old physical67/printed57. Adopted June1,2025 update makes that sheet intentionally blank: actual removal, rather than a silently omitted active rider.
- SBC early2025 effectiveJanuary1,2025; nextJune1,2025; nextOctober1,2025. September2026 table's SBC effectiveJune1,2026; October2026 update effectiveOctober1.
- RGGI early2025 effectiveJanuary1,2025; nextJune1,2025. The December1,2025 base-case reissue retains.007121. October1,2026 renames the rider EECEC and sets.010510. Solar, community-solar and efficiency program costs are mandatory delivery riders, not export credits or standalone wholesale purchases.
- IIP old rates effectiveDecember1,2023. December1,2025 roll-in explicitly zeros IIP, with corresponding base distribution changes; October1,2026 introduces the new IIP charges. IIP text requires adding the rider to the relevant base distribution rates for billing presentation: do not add it twice.
- CIP early rate effectiveJune1,2024; nextJune1,2025; September2026 snapshot's rate effectiveAugust1,2026; October2026 rate effectiveOctober1. An unseen intervening fifth revision prevents inventing January–July2026 CIP from later rates.
- ZEC .004265 includingSUT effectiveFebruary1,2025; zero effectiveJune1,2025; **credit-.004265** effectiveJune1,2026. Current source's negative reconciliation must not be mistaken for a positive charge. January2025 predecessor ZEC leaf remains unverified.
- SEC Transition Bond and MTC-Tax are explicitly zero. EDIT RS/MGS explicitly zero. Tax treatment is independently reviewed; zero rows do not authorize general tax exemptions.

Old rider physical pages: SEC66/printed56; NGC67/57; SBC69/58; RGGI82/64; EDIT84/66; ZEC85/67; IIP86/68; CIP87/69. Current pages: SEC49/40; ZEC50/41; SBC51/42; RGGI/EECEC63/48; EDIT64/49; IIP65/50; CIP66/51. The source's occasional inconsistent revision labels are preserved; numerical tables and actual effective dates are not silently repaired from revision-order assumptions.

## Residential capacity deferral

July2025 and October2025 books physical56/printed46 explicitly provide RS **-$30/month July/August2025**, followed by **+$10/month September2025 through February2026**. The rider applies to all residential customers for July1,2025–February28,2026 and includes SUT. Thus an October2025 recurring stack cannot omit the$10 recovery charge. It is not an inferred usage-band refund. Exact posting/allocation and eligible ordinary account facts are addressed by tax/rules research. Outside that interval, do not extrapolate either amount. June2025 book still has the predecessor blank leaf.

## Eligibility, demand, minima and rounding

RS: individually metered full domestic residential service, including qualifying rural domestic/agricultural pursuits. Ordinary first scope must exclude EV off-peak credits and special accounts. MGS-Secondary: nonresidential load at one point, metered at or compensated to delivery voltage, with adequate utility facilities. Utility-assigned RSCP membership/PLS election is separate from the delivery schedule.

MGS demand old physical18/printed13 and current physical14/printed10: maximum fifteen-minute demand during the month, rounded to nearest0.1kW. No historical ratchet or minimum-kW floor appears in this schedule's demand-determination text; do not import AGS summer-history rules. Reactive demand may be measured when expected demand exceeds100kW; charge applies to kvar above one-third of kW demand, old$.68/current$.76 per kvar, rounded to nearest0.1kvar. For connections without demand meters, summer June1–September30 demand is estimated as kWh/150; the schedule does not establish a winter estimated-demand rule. Do not infer utility metering assignment, rounding tie behavior or winter demand from this clause.

MGS energy billed to nearest0.01kWh. Its continuation sheet specifically states this; RS has no matching energy-rounding clause on its own schedule. General rules need separate review. Current MGS minimum is applicable customer charge plus applicable adjustments; old version says$12.55/month plus applicable adjustments. Ordinary positive-energy/positive-demand examples keep this inactive; do not infer general special-account floor treatment.

Special worship/veterans/small-commercial-development rates, grandfathered heating exclusion, fixed-load contracts, primary voltage, standby and export settlement remain separate eligibility branches. Old standby rider differs materially from December2025/current terms. Adopted November2025 order clean STB physical166 (ExhibitC109/151) introduces required standby for nonintermittent customer generation greater than100kW; redline322 (ExhibitD109/157) shows replacement of the old50%/six-month availability framework. The order adopts the stipulation, effective serviceDecember1,2025; current filed book supplies the final date. This does not by itself establish approval of a proposed PV/storage installation.

SectionII6.5 requires billing for periods other than30days to be prorated. A complete calendar month is not automatically a complete unprorated tariff cycle. Root's initial proposal is exactly30 consecutive completed service days, entirely inside one unchanged component regime and season, with an explicit documented hypothetical cycle. No31-day/February allocation rule is invented here.

## Independent benchmark and supported sample proposal

Adopted November21,2025 BPU base-rate order physical4 records the settlement's average649kWh residential bill impact:$190.61 to$197.38, increase$6.77 (3.55%), includingSUT. Physical35/ExhibitA2/14 independently records current/new RS distribution rates; physical36/ExhibitA3/14 does likewise for MGS. These are adopted rate-design/current-price evidence; the average bill impact is not a dated single-cycle full-bill fixture without the source's season and adjustment assumptions. No independently published complete MGS invoice was recovered in this bounded pass.

Candidate exact30day samples for joint supply/tax approval are April1–30, June1–30, July1–30 and October1–30,2025; September1–30 and October1–30,2026. The original component/effective-date packet, not this proposal, controls execution. September2025 crosses a September15 transmission change. January2025 ZEC predecessor is unverified. Earlier2026 joint supply/CIP revisions and general non30day allocation remain incomplete. Accordingly full-year2025 billing/dispatch coverage is **not** established. Neither missing factors, standby approval, export settlement nor proposed rates may be filled by a current-rate fallback.

Delivery-only continuity review supports February–May2025: NGC revision32 is replaced by33 effectiveJune1; SBC50 by51June1; RGGI29 by30June1; CIP3 by4June1; ZEC5February1 by6June1; IIP3,EDIT7,SEC25 and baseRS63/MGS64 persist unchanged between February and June originals. Supply/TEC continuity remains separately sourced. For November2025, RS64/MGS65 have direct successors65/66 effectiveDecember1; IIP3→4 and RGGI30→31 likewise. The adopted November21 order additionally preserves then-current SBC52 effectiveOctober1 at physical338 (clean181) and CIP4 effectiveJune1 at physical356 (clean199), unchanged numerically from the October snapshot. These current/redline and adopted successor records support a November30day sample if the source policy accepts this documented chain. A policy requiring a final standalone November/December compilation should retain the narrower October-only boundary; no such compilation was recovered here.
