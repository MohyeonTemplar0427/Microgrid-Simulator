# Rockland Electric NJ BGS-RSCP supply evidence

Research date: 2026-10-27. Ownership: supply evidence only. The delivery stream owns the shared current tariff original. No production, test, Git or prior utility files were changed.

The complete supply-source intersection recovered in this bounded pass is **October2026**, conditional on independently confirmed Bergen/Eastern SC1 non-TOD or SC2 secondary **non-demand-billed** BGS-RSCP account assignment, ordinary nonexempt taxes and the parent's billing-cycle restrictions. This is source coverage, not customer eligibility or simulation proof. Full2025 coverage is not established.

Machine packet: `.cache/rockland_electric_nj/sources/supply/supply_snapshots.json`; original/text/hash/selected-page and render receipts: `supply_records.json` in the same directory. Checked-in source excerpts are in `supply_excerpts/`. Physical pages are one-based. The shared tariff SHA256 is `3721612c3d326d280467ba05cbe581f2f0253adef57a88ab4035eb2c265dd841`.

## October2026 component snapshot

All numeric charges below are **dollars/kWh**, including applicable embedded taxes. No separate auction tranche, LMP, administrative adder or TEC/RMR adder should be added.

| Component | SC1 non-TOD winter | SC2 non-demand secondary winter | Adopted evidence |
|---|---:|---:|---|
| BGS energy/capacity/ancillary, including ISO administration | .14435 | .11305 | Current tariff physical53, leaf50/22nd, effectiveJune1,2026, BPUFebruary12,2026 ER25040190 |
| Base transmission | .01809 | .00579 | Physical103 leaf83/55th effectiveOctober1,2026; SC2 physical109 leaf89/5th effectiveJanuary1,2024 |
| Transmission surcharge, including RMR/EL05-121/TEC | .02187 | .01247 | Physical103 leaf83/55th and physical110 leaf90/52nd, effectiveOctober1,2026, BPUSeptember24,2026 ER26070406 |
| BGS-RSCP reconciliation | -.02000 | -.02000 | Quarterly original September2026 physical1 leaf54/90th; current book physical57 |
| Supply component sum | **.16431** | **.11131** | Arithmetic only; delivery/riders/account credits excluded |

SC2 base transmission leaf89 contains a $2.79/kW demand row alongside .00579/kWh. The official PTC explicitly separates its non-demand-billed row (only allkWh) from secondary demand-billed rows (allkWh **and** allkW). The initial branch therefore requires an independently confirmed non-demand account; simulated peak alone does not establish this classification. This is corroboration of the utility's published branch treatment, not a categorical small-system exemption inferred from capacity.

Generation summer billing months are June–September; all other billing months are winter. From June1,2026, SC1 summer first600kWh=.08465 and excess600=.17944; SC2 non-demand summer allkWh=.12678 (physical53). No partial-cycle block allocation is inferred here.

## Reconciliation history: billed-month clock

Every recovered quarterly leaf54 says the charge includes all applicable taxes and applies to **all usage billed in the month indicated**. This is distinct from an interval service-date rate. Quarters start March, June, September and December; reconciliation is capped at2c/kWh includingSUT perquarter, with residual regulatory balance carried forward. Do not replace billed-month assignment with interval allocation without separate billing-rule proof.

| Billed months | RSCP dollars/kWh | Original/revision |
|---|---:|---|
| December2024–February2025 | -.01076 | `reco_rc_202412.pdf` physical1,83rd |
| March–May2025 | +.02000 | `reco_rc_202503.pdf` physical1,84th |
| June–August2025 | .00000 | `reco_rc_202506.pdf` physical1,85th |
| September–November2025 | **unknown** |86th absent from current archive; exact quarter URL404 |
| December2025–February2026 | -.02000 | `reco_rc_202512.pdf` physical1,87th |
| March–May2026 | .00000 | `reco_rc_202603.pdf` physical1,88th |
| June–August2026 | .00000 | `reco_rc_202606.pdf` physical1,89th |
| September–November2026 | -.02000 | `reco_rc_202609.pdf` physical1,90th |

Originals are linked from the [official NJ electric tariff index](https://www.oru.com/en/rates-tariffs/rates/new-jersey/electric). Exact source URLs, original SHA256s and extracted-text hashes are preserved in `supply_records.json`.

## Eligibility and jurisdiction

Current tariff physical55/leaf52 specifies mandatory BGS-CIEP for SC7 and SC2 customers maintaining billing demand of500kW or more during **any two months of a calendar year**. Do not import JCP&L's annual November PLS rules. Physical54/leaf51 permits eligible SC2 metered customers in EasternDivision to elect CIEP by the second business day ofJanuary for the twelve months startingJune1; RSCP return uses the same notice clock. Shopping and returning within that annual term does not erase the CIEP assignment. BGS-CIEP and its PJM/LMP/capacity formulas are excluded.

Physical7/leaf6 lists EasternDivision=Bergen municipalities, Central=Passaic municipalities and Western=Sussex municipalities, including partial municipal territories. County/ZIP is not account territory proof. Physical8 defines power supply against PJM **or NYISO** requirements. The present supply packet does not establish current all-county PJM membership. Keep tariff jurisdiction, utility territory, supplier assignment and RTO metadata separate.

Physical54 states SUT is included in BGS generation; physical57 states reconciliation includes taxes; SC1 physical104 and SC2 physical111 state schedule charges include CBT/SUT. Apply no duplicate percentage tax to these ordinary nonexempt literals. Tax exemptions require a separate supported branch.

## Independent utility PTC benchmark and its limits

The corrected [official supplier page](https://www.oru.com/en/save-money/shop-for-energy-suppliers/how-to-choose-your-energy-service-company-esco) links a renamed `price-to-compare-nj.pdf`. Its exact Azure URL is in the receipt. The original is `ptc_current_linked.pdf` (two pages), headedJune1,2026–May31,2027, **excluding BGS reconciliation**.

| PTC class | Bergen physical1 summer / winter | Passaic/Sussex physical2 summer / winter |
|---|---:|---:|
| SC1 first600kWh | .12455 / .18425 | .10646 / .16616 |
| SC1 excess600kWh | .21934 / .18425 | .20125 / .16616 |
| SC2 non-demand allkWh | .14502 / .13129 | .13923 / .12550 |

The PTC differences exactly match base transmission: .01809/kWh SC1 and .00579/kWh SC2. Tariff physical103/109 explains base transmission remains payable for Central/Western shopping customers but not Eastern shopping customers. Thus **PTC is an avoidable shopping-credit comparison**, not evidence of differing full-service BGS rates by county. It does not resolve current county control-area membership.

PTC's implied surcharge is .02181/kWh SC1 and .01245/kWh SC2, consistent with June-era components but different from the adopted October2026 .02187/.01247. The PTC annual heading does not establish unchanged rates throughout that year. It supports class/units/branch reconciliation, not exact October whole-bill calibration. No independent dated whole-bill source was recovered by this supply stream.

PTC physical1, current tariff physical53/109/110 and September2026 reconciliation were rendered and visually reviewed. The PTC shows only allkWh for non-demand; adjacent secondary and primary classes each carry separate allkW rows. Renders and hashes remain in the ignored evidence cache.

## Gaps and stopped routes

- January2025–May2026 generation originals and preOctober2026 transmission surcharge versions were not recovered. The official search index still exposes June2025 leaf50/21st text, but the direct URL now serves the identical current153-page book. Stale web-index text is **not used as executable rate evidence**.
- September2025 reconciliation is missing from the official archive. The specific expected `bgs-202509.pdf` returned404 once; no carryforward or unchanged retry.
- The old `recopricetocomparenj.pdf` URL and one migration mirror returned404. The corrected current page provided the exact renamed working asset. Old2025/26 PTC indexed text was not substituted for an original.
- Regulator `DocumentHandler.ashx?document_id=1415794` returned403 to the parent; no unchanged retry.
- No neighboring utility, proposed transmission filing, wholesale price, or auction tranche was used to fill gaps. The bounded history pass stopped after these targeted gaps.
- Export settlement, CIEP, TOD, primary service, demand-billed SC2, tax exemption, account-specific bill relief and partial/crossing-cycle allocation are outside this packet. Delivery/tax research remains separately owned; October complete bill scope depends on their intersection.

## Final bounded prior-transmission check

The adopted [September24,2026 transmission order](https://www.nj.gov/bpu/pdf/boardorders/2026/20260923/2P%20ORDER%20July%2026%20NITS%20TEC.pdf), preserved as `bpu_transmission_order_2026sep24.pdf`, is five pages. Physical2 approves October1,2026 despite the petition requesting September1, and reports an approximate$0.05 increase at650kWh includingSUT. It contains no prior rate sheets or tariff appendices; pages4–5 are service lists. Targeted prior54thleaf83/51stleaf90 and Julyjointfiling searches did not recover adopted historical numeric sheets. March2026 proposed figures are not adopted proof. **August–September2026 transmission remains unverified.** This bounded follow-up stopped without broad archive retries.

October2026 is a tariff-source intersection only. As ofOctober27,2026 a full actual October weather month is unavailable; this packet makes no full-month simulation claim and supplies no future-weather substitute.
