# Pepco Maryland delivery and rider research

Retrieved October 26, 2026. Research only; no production changes. Values are
USD per billed kWh except monthly customer/fixed amounts. Maryland and DC
must remain separate; proposed tariff files are not rate authority.

## Verified schedule scope and seasons

Original August2025 tariff physical pages8–9 (tariff3/3.1) R and12–13
(tariff5/5.1) GS establish secondary ordinary service. R permits primarily
domestic service/farm on the same meter, excludes five or more rooms for hire,
separately metered seasonal loads, and temporary/auxiliary/emergency service.
Standard single-phase120/240V or120/208V; initial candidate may bound120/240V.

GS is low voltage ordinary service, excluding railway propulsion, secondary
temporary service, and supplementary loads separately metered from other usage.
It has **no demand charge or winter energy tiers** in its base rates. Schedule
eligibility is separate: maximum30-minute demand must remain below25kW in every
one of12billing months; usage must not exceed6000kWh in two consecutive winter
months, or7500kWh in a single summer month. Reclassification annually in June.
A conservative model may cap every winter month6000 but must disclose that
restriction and independently confirm existing utility-assigned classification.

**Distribution billing seasons: June–October summer, November–May winter.**
These are billing-month designations, not identical to supply source periods.

| Base component | R | GS |
|---|---:|---:|
| Monthly customer (April2024–August10,2026) |8.44|12.66|
| Summer energy |.08760|.08130|
| Winter energy |.04328|.04272|
| Monthly customer (August11–27,2026) |8.67|13.02|
| Summer energy (August11–27,2026) |.09713|.09220|
| Winter energy (August11–27,2026) |.05469|.05447|
| Monthly customer (August28–October31,2026) |8.44|12.66|
| Summer energy (August28–October31,2026) |.08760|.08130|
| Winter energy (August28–October31,2026) |.04328|.04272|

The current filed book explicitly shows those adopted date ranges; do not
replace them with proposed November2026 revisions. It also shows an exactly
offsetting RDM rate duringAugust11–27 (below). Preserve both components and
clocks; do not claim an independently benchmarked transition allocation merely
because the sum cancels. The GS schedule has no separate minimum clause in its
two pages; the fixed customer charge remains payable at zero usage. No optional
AMI opt-out fees or competitive consolidated-supplier billing credits apply to
an ordinary utility-billed SOS study (Rcredit.61,GS.74 only where applicable).

## Non-monthly riders and exact dates

| Component | Period | R | GS |
|---|---|---:|---:|
| EmPOWER E-MD | January–December2025 billing months |.013790|.008044|
| EmPOWER E-MD | January2026 billing month onward |.020618|.011986|
| MYP | throughMarch31,2025 |.00020|.00015|
| MYP | April1,2025–March31,2026 |.00091|.00068|
| MYP | May1,2026–April30,2027 |.00168|.00123|
| RDM recovery, fixed monthly | September1,2024–March31,2025 |.05|.03|
| RDM recovery, winter energy | September1,2024–March31,2025 |.00238|.00113|
| RDM recovery, summer energy | September1,2024–March31,2025 |.00400|.00235|
| RDM deferral, fixed monthly | August11–27,2026 |-.23|-.36|
| RDM deferral, summer energy | August11–27,2026 |-.00953|-.01090|
| RDM deferral, winter energy | August11–27,2026 |-.01141|-.01175|
| ERR customer/summer/winter | current filed April2024 onward table |0|0|
| GRC | current and August2025 filed tables |0|0|
| DRS | current and August2025 filed tables |0|0|

MYP April2026 needs explicit handling of its gap: prior table endsMarch31;
next startsMay1. Do not extend the expired rate. No April charge was independently
calibrated to a customer bill or component ledger. Current RDM table explicitly
zeroAugust28–October31,2026, and TBDNovember–December2026; do not treatTBDaszero.

R-DLC/NR-DLC/DP credits require optional program enrollment/events/baseline
proof; no enrollment or event benefit is inferred. RRC (RGGI) is a quarterly
fixed residential customer credit by tariff50, with current value published
separately; **its2025/26 amounts remain unrecovered**. It is not listed in either
recovered CSEG variable-credit table, which cannot prove its absence.

## Exact recovered BSA monthly retail rates

BSA is computed monthly for application in the second succeeding **billing
month**, then bundled with the distribution charge. Primary CSEG tables express
credits: invert the sign of each component to obtain the retail charge.

```python
# None = missing rate evidence, never zero/fallback.
BSA_R_2025 = [.003928,-.001328,-.003096,-.005530,None,None,None,None,None,None,None,None]
BSA_GS_2025 = [.005600,.005659,.005801,.005987,None,None,None,None,None,None,None,None]
# 2026 known May–October only:
BSA_R_2026_MAY_OCT = [-.004705,.002223,-.000852,.002386,-.007579,.004347]
BSA_GS_2026_MAY_OCT = [.006200,.010035,.009858,.009855,.009906,.009998]
```

Independent published variable composite before county tax and beforeGRT:

```python
# Includes generation+admin+PCA+retailtransmission+distribution+BSA+franchise+
# MES+EmPOWER+AC+applicableMYP/RDM. Excludes fixed customer/USC/RRC and GRT.
CSEG_R_2025_JAN_FEB = [.18550650,.18145860]
CSEG_GS_2025_JAN_FEB = [.15972880,.16105280]
CSEG_R_2026_MAY_OCT = [.19581930,.24860570,.24586150,.24991550,.23922230,.26611460]
CSEG_GS_2026_MAY_OCT = [.17054370,.21370970,.21260160,.21142420,.21104700,.22374430]
```

GRT footnote marks transmission, base distribution,BSA,franchise,MES,EmPOWER,
RDM andMYP. Administrative credit is unmarked and must not automatically enter
the GRT base. Tax specialist owns final fixed-charge/GRT/state-tax interpretation.
Current CSEG originalMayJune2026MES.000151,JulyOct.000150 (do not substitute
BGE's2025/26constantMES). Current CSEG May/June2026MCS R.0113227/GS.0202499;
JulyOct R.0113242/GS.0202525. Supply specialist owns exact SOS/PCA/AC components.

## General terms: monthly charge and rate changes

GTC physical22 (printed19), section7(b): nondemand periods16–45days use monthly
rates; >45days nearest multiple of monthlyrates; <16days combined with nextfull
bill except final<16 billed monthly. This supports one fixed customer charge for
complete28/29/30/31day calendar cycles without days/30proration of the ordinary
monthly charge.

GTC physical24 (printed21), section7(e): a specified-date rate change is prorated
by days the new rate applies divided by an assumed30day billing period unless
the Commission otherwise orders. A change effective with bills rendered applies
to all recorded/billed consumption in that designated nominal billing month;
with meters read applies to all consumption read on/after the date. Do not
silently replace this with actual interval consumption across a service boundary.
August2026 has multiple specific-date components; one source-backed/calibrated
allocation implementation or an explicit unsupported crossing-cycle boundary is
required. Complete calendar billing/service months avoid ordinary shifted-cycle
allocation, but do not erase August's intramonthrate changes.

## Gaps and blocked routes

Full-year2025 cannot yet be claimed: BSA May–December2025 (and supply/tax
counterpart gaps) are missing. BSA January–April2026 missing. RRC quarterly
fixed values unrecovered. April2026MYP has explicit date gap and no bill
calibration. August2026transition allocation unbenchmarked. November2026future
RDM TBD and proposed tariff revisions must stay unsupported.

Seven guessed legacycommunity-solar routes returned404; no retries. Root
MyGreenPowerConnection category succeeded; followed actual child links through
solar-for-home-business and developers-contractors/community-solar-resources
until the current billing page was found. Both current BSA/CSEG pages list only
current documents; no historical archive is exposed there. Sitemap/robots URLs
returnedAngularHTMLshell, so no sitemap evidence was inferred.

## Sources and preserved evidence

- August2025 book: https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blte8a580e4cc79e2c4/6883d6c9ef057227af7274a2/9478_Pepco_MD_Green_Rider_Update_Current_Clea_.pdf?branch=prod_alias
- Current filed book: exactURL/hash in `.cache/pepco_md/sources/supply/supply_records.json`; physicalR8–9/GS12–13, MYP150–153, RDM154–155. Re-audit physicalpage identity before quoting.
- BSAcurrent: https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blt048e03b25e5de0cf/6abfc95f15d5b747d1b1848e/Pepco_MD_BSA_-_102026.pdf?branch=prod_alias
- BSAFebruary–April2025: https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blt048e03b25e5de0cf/67ec27843c6595589ce5236f/Pepco_MD_BSA_-_042025.pdf?branch=prod_alias
- CSEGcurrentMay–October2026 (physicalR1/GS4): https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blt184aa0644dce17a4/6abebe49c7c45d25867c0a5a/CSEG_MD_Pepco_-_10_2026_.pdf?branch=prod_alias
- CSEGSeptember2024–February2025 (physicalR1/GS5), preserved bytaxagent: https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blt184aa0644dce17a4/67a0f1215b6934124e523dd3/Pepco_MD_CSEG_-_02012025.pdf?branch=prod_alias
- GTC: https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/bltb770f5b6804c804c/6939d02c4b4e4a1bd61743cd/MD_Terms_and_Conditions_-_master_file.pdf?branch=prod_alias
- Current CSEG page: https://www.pepco.com/smart-energy/my-green-power-connection/developers-contractors/community-solar-resources/community-solar-resources-md/project-subscriber-billing
- Current BSApage: https://www.pepco.com/my-account/my-dashboard/rates-tariffs/maryland/bill-stabilization-adjustment

### SHA256 of preserved delivery originals

- `.cache/pepco_md/sources/delivery/august2025_tariff.pdf`: `0a894b875445810b98feb25e62b45508504a3103c5be36a08541b561e8e17036`
- `.cache/pepco_md/sources/delivery/bsa_2026.pdf`: `4d4d312c0f92638c61884b7e45045c1fcd1bc9edc759878d9fc530b6661a9558`
- `.cache/pepco_md/sources/delivery/bsa_april2025.pdf`: `3a31091439a42c9f0459c2e99ec98f074d0424c4392b800077c1de24382721ba`
- `.cache/pepco_md/sources/delivery/cseg_oct2026.pdf`: `9dc4f996d1a1c596dfc9409abbdff50f44bc65db9460f2e502e0de98d5b1931a`
- `.cache/pepco_md/sources/delivery/gtc_current.pdf`: `bcb76372dbe3d2780b014568611399f13335e6936212556e46d92479a62f570d`
