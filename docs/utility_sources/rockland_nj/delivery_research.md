# Rockland Electric New Jersey — SC1/SC2 delivery research

Research date: October27,2026. Scope is ordinary **SC1 non-Time-of-Day residential** and **SC2 secondary non-demand-billed metered BGS-RSCP**. This packet verifies numeric delivery components; supplier enrollment, county supply branch, billing clocks, nondemand assignment, taxes, NEM and standby approval have separate reviews. It does not itself establish an executable complete bill.

## Preserved official evidence

The [official NJ tariff index](https://www.oru.com/en/rates-tariffs/rates/new-jersey/electric) links a current153-page tariff through an Azure mirror. Its exact URL, originalSHA256, byte count, physical-page count and text path are in `.cache/rockland_electric_nj/sources/delivery/delivery_records.json`. The non-Azure origin URL was fetched once as a potential historical source; its bytes are **identical** to the current mirror, SHA256 `3721612c3d326d280467ba05cbe581f2f0253adef57a88ab4035eb2c265dd841`. Search indexing exposes older2025 leaves, but it does not recover older PDF bytes. That route was stopped.

The current assembled PDF contains erroneous **New York Orange and Rockland PSC** pages at physical4,131,132. They are excluded from NJ evidence. The original remains unchanged. NJ pages explicitly identify Rockland Electric Company, BPU No.3. `page_inventory.json` records jurisdiction/page headings.

Additional adopted originals:

- [May21,2025 RGGI/SBC/CIP order](https://www.nj.gov/bpu/pdf/boardorders/2025/20250521/2K%20ORDER%20RECO%20RGGI%20SBC%20CIP.pdf),112pages; SHA256 `73693fd6f74f005879a8d82e80e1f93f74a4d19bc01349a2a59f0a77ebcd9094`.
- [September25,2025 USF/Lifeline order](https://www.nj.gov/bpu/pdf/boardorders/2025/20250925/2A%20ORDER%20USF%20Lifeline.pdf),16pages; SHA256 `d3c916fc98cbfb0bd63be120878d54301ee3e3dfa0dce96741db47ea2903ba57`.
- [June30,2026 base-rate order](https://www.nj.gov/bpu/pdf/boardorders/2026/20260630/2D%20ORDER%20RECO%20Base%20Rate%20Case.pdf),113pages; SHA256 `bc6c49995e285cf18e89d77c569b190e19537d3b6ee51d10f61b91caab1aa63c`.

`delivery_snapshots.json` in the same private directory contains18 component versions, exact rates and original/excerpt/page/revision/effective pins, plus coverage limitations. Checked-in selected page text is in [delivery_excerpts](delivery_excerpts/). Thirteen critical rate-table/authority/redline pages were visually reviewed from PDFium renders, in addition to text extraction. Parentheses/signs, including-SUT columns, cents-to-dollars conversion and old/new strikeout text were checked visually.

## Delivery component history: August–September2026

All following rates are **dollars per unit, including published taxes**. Source tables often print cents/kWh; divide those printed values by100. Do not add CBT/SUT again. June–September are summer **billing months**; rules review must establish their exact application.

| Component | SC1 non-TOD | SC2 secondary non-demand metered | Source |
|---|---:|---:|---|
| Customer/month |6.00|16.00|Current physical101/107, leaves82/87, July1,2026|
| Summer distribution |First600kWh .06886; excess .08671|AllkWh .03975|Physical101/108, leaves82/88, July1,2026|
| Distribution adjustment |First600kWh −.01416; excess −.01783|No SC2 adjustment published|Physical102, original82.1, **July16,2026**|
| SBC aggregate |.008619|.008619|Adopted component assembly below|
| RGGI aggregate |.006867|.006867|Physical61,22nd leaf58, June1,2025, retained current|
| CIP |+.006170|−.001480|Physical76, original65D, July1,2026; groupsphysical73/65A|
| ZEC aggregate |−.004265|−.004265|Physical68,8th leaf61, **July15,2026**|
| Residential2025 relief/recovery |0 inAugust/September2026|Not residential|Physical66,15th leaf59|

SC1's summer net distribution pair is .05470/.06888 after separately retaining base and credit lines. Winter base is .06886/kWh and adjustment −.01416/kWh. The customer is6.00. The credit leaf permits modification/elimination after advance workpapers; do not extend it beyond a subsequently verified change or invent an end date. **July2026 cannot receive a whole-month July16 credit.** A nonlinear partial-month tier-credit allocation is unverified here.

SC2 winter nondemand distribution is .03601/kWh. Its unmetered-energy service has a separate14.00 customer charge; that is not the same as ordinary metered energy without demand billing. Demand-billed/primary branches are reference-only in the packet, not substitutes for the requested nondemand class.

## Adopted SBC component chain

The original old32nd leaf56 is not separately recoverable from the mutable fullbook. Numerical authority instead comes from retained **adopted** orders:

1. May21,2025 orderphysical12–13 approves DSM/CEP .003590/kWh and uncollectible .000521/kWh, with the full June1 SBC .007080. The attached clean ExhibitB is physical102; it must be read with the Board's adoption, not treated as an independently effective draft.
2. September25,2025 orderphysical10 **orders**, includingSUT, USF .003728/kWh and Lifeline .000780/kWh. Physical11 makes the rates effectiveOctober1,2025. Thus .003590+.000521+.003728+.000780 = **.008619/kWh**.
3. The official search index independently exposes32nd leaf56, issuedSeptember26,2025/effectiveOctober1,2025, with the same .8619cents aggregate/components. This is an **indexed crosscheck**, not retained historical PDF bytes and not the sole numerical authority.
4. Current33rd leaf56 explicitly supersedes32nd and retains DSM/CEP/uncollectible prices. It changes USF/Lifeline October1,2026 to .002870/.000715, yielding **.007696**. That October aggregate must not be applied to August/September.

This is exact adopted component assembly, not interpolation, pending-proposal adoption or a generic last-known-rate fallback. The receipt retains the source type and gaps explicitly.

## Other rider arithmetic and exclusions

Current RGGI leaf58's .006867/kWh reconciles to: low-incomeII −.000332 + low-incomeIII .000212 + SREC I −.000448 + SREC II0 + TREC .002941 + SuSI .000307 + CleanEnergyAct I .002578 + CleanEnergyAct II .001410 + communitysolar .000199. The May21 order's headline .5457cents **excludes** the separately approved .1410cents EEII component; its physical10 footnote28 and current complete leaf prevent that omission. Do not add the components to their already-included aggregate a second time.

CIP customer-group revenue targets are regulatory accounting, not fixed retail charges. The actual charge table is physical76/65D. CurrentJuly2026 prices equal the expressly adopted June1,2025 CIP: groupA .006170, groupB −.001480, groupC −.001100.

Current ZEC's table is explicitly negative .4265cents/kWh. Its old narrative describing the original positive statutory charge is not an additional current charge. Pre-July15,2026 ZEC history has not been established by this packet.

GI35's residential deferral is mandatory −30/month July/August2025 and +10/month September2025–February2026, includingSUT. Its under/over-recovery flows through the Company's RGGI filing; it is not an individual customer credit bank. No extension afterFebruary2026 is inferred. Negative customer-balance/refund settlement remains outside the verified scope.

The Temporary Tax Act Credit leaf60 explicitly applies only July2018–June2021. It is expired in2025/2026. IIP leaf81A says its resulting charges are **combined with individual base distribution charges**; leaf81B's SC1/SC2 incremental entries are zero, effectiveJanuary2023. Do not double-add IIP or infer a new annual IIP increase from the targeted filing schedule alone.

## Eligibility, minima and commercial transmission scope

SC1 is residential service, with separately described church/auxiliary-building provisions. The initial ordinary scope excludes those special arrangements, voluntaryTOD, multiple-meter combination, special contracts and exemptions. Currentleaf84 states6.00 monthly minimum and not less than36.00 per contract; rules review owns the exact initial-account contract/minimum interpretation.

SC2 is general secondary or primary service; initial scope is **utility-assigned secondary non-demand-billed metered** service. No numerical nondemand eligibility threshold was verified in this delivery pass. Do not infer assignment from simulated peak, equate non-demand-billed with unmetered-energy service, or borrow JCP&L's10kW rule. Currentleaf91 sets16.00 monthly minimum for metered nondemand; demand-billed branches use connected-load or15-minute demand, at least90%kVA, and winter demand at least70% of the previous June–September maximum. Rules/eligibility review is separate.

**Transmission demand was unresolved in the delivery-only pass:** SC2leaf89/physical109 lists2.79/kW on allkW plus .00579/kWh and applies to BGS customers without an explicit nondemand exception on that leaf. Its mere existence does not prove the demand is zero for nondemand-billed accounts. The separate rules/PTC review subsequently confirmed the published non-demand category treatment; its original and interpretation are owned by that review. The initial account must retain Company-assigned non-demand billing across all operation. No numerical10kW/PLS eligibility rule is borrowed from JCP&L, and no general demand formula is claimed.

Delivery rates are not county-varying on these leaves. County/Eastern–Central–Western distinctions in transmission applicability and BGS supply remain separate. Delivery utility, NJ jurisdiction, BGS enrollment, county division and wholesale metadata must each be confirmed.

## Final joint intersection and historical limits

The coordinated source review selects **October1–31,2026 only**, ordinary SC1/SC2 in the separately confirmed Eastern/Bergen/PJM branch. For October, SC1 uses customer6.00, winter distribution .06886 and credit−.01416; SC2 metered nondemand uses customer16.00 and distribution .03601. Both use OctoberSBC .007696, RGGI .006867 and ZEC−.004265; CIP is SC1+.006170 or SC2−.001480. Supply and rules have separate source pins. **August/September complete bills remain unsupported because their historical transmission surcharge was not verified**, even though the delivery-only components above were recovered. Do not label a simulated full October as completed historical weather/electrical evidence on October27.

## Historical limits and benchmark

The June2026 adopted base-rate order includes existing-price redlines: SC1 customer5.75 and distribution .05470/.06888 summer, .05470 winter; SC2 nondemand energy .04078 summer/.03695 winter and customer16.00. These existing-price references do **not** establish every2025 effective-date chain. No complete2025 bill coverage is claimed; pre-June2025 RGGI/CIP and complete historical base/rider chronology remain gaps. The broader historical pass stopped after these specific gaps were recorded.

The same orderphysical29 reports a typical925kWh **annualized monthly** bill247.91→261.94, increase14.03, includingSUT, based on rates effectiveMarch1,2026. County/supply basis and the laterJuly16 residential adjustment are not matched here, so this is preserved as an independent BRC impact reference, not a calibrated August/September bill fixture. Published SBC and RGGI component totals independently reconcile; saved-study/solver/OpenDSS/browser validation has not been performed by this research task.
