# BGE delivery/rider research — retrieved October 25, 2026

Official current source catalog recovered via public BGE content API. Directly
retrieved originals replace the initial indexed-only evidence. Earlier permanent
Community Solar URL returned422 and must not be retried; current timestamp URL works.

## Primary sources

- ScheduleR: https://azure-na-assets.contentstack.com/v3/assets/blt71bfe6e8a1c2d265/blt10129d1f47260cd7/P3_SCH_R.pdf
- ScheduleG: https://azure-na-assets.contentstack.com/v3/assets/blt71bfe6e8a1c2d265/bltae5a035d36f7f19e/P3_SCH_G.pdf
- Component ledger, current official59-page PDF: https://www.bge.com/cdn/assets/v3/assets/blt71bfe6e8a1c2d265/blt8ad3da6ba8d050f5/6acfc043f4251ab7b699fb93/Rdr32_CS_Current_Rates_12.pdf?branch=prod_alias
- R25 historical: https://www.bge.com/cdn/assets/v3/assets/blt71bfe6e8a1c2d265/blt5d58e3f9b4655346/6abe7c86a1315212b30adbc1/Rider_25_Historical_Chart.pdf?branch=prod_alias
- R8/R10 historical, revised8/27/2026: https://www.bge.com/cdn/assets/v3/assets/blt71bfe6e8a1c2d265/bltf75afad89af14ef3/6acce6326214c42d62238ff5/POLR_RateAdjustmentChart_1.pdf?branch=prod_alias
- R2: https://azure-na-assets.contentstack.com/v3/assets/blt71bfe6e8a1c2d265/blt0b5280aebf1a4a36/Rdr_2.pdf
- R15: https://azure-na-assets.contentstack.com/v3/assets/blt71bfe6e8a1c2d265/blt95b3f3254f635c76/Rdr_15.pdf
- R16/17: https://azure-na-assets.contentstack.com/v3/assets/blt71bfe6e8a1c2d265/blt722af29653644b4e/Rdr_16_17.pdf
- R25 rule: https://azure-na-assets.contentstack.com/v3/assets/blt71bfe6e8a1c2d265/blt8ca2dfc58e27bd9a/Rdr_25.pdf
- R26/27: https://azure-na-assets.contentstack.com/v3/assets/blt71bfe6e8a1c2d265/bltbcb53d4782e3ba22/Rdrs_26_27.pdf
- R34: https://azure-na-assets.contentstack.com/v3/assets/blt71bfe6e8a1c2d265/blt0bfdbd25fd81f70c/Rdr_33_34.pdf

## Delivery and non-monthly riders

All dollar rates per importedkWh unless specified.

| Component | R2025 | G2025 secondary | R2026 | G2026 secondary |
|---|---:|---:|---:|---:|
| Customer/month |9.65|15.10|10.00|15.60|
| Base delivery |.04751|.04819|.04859|.04965|
| Rider2 EE |.00764|.02059|.01097|.03526|
| Rider15 DR |.00251|0|.00198|.00027|
| Rider26 PTR |.00013|.00011|.00015|.00013|
| EmPOWER total |.01028|.02070|.01310|.03566|

R2/15/26 originals Suppl742 effective with January2026 billings; current R2 G
rate.03526 and R15 G.00027 are combined as.03553 in the Community Solar
ledger's row labeled Rider2. Preserve the correct separate component amounts.
R34 original Suppl709 offsets explicitly apply to usageJan1–Dec31,2024 only;
no R34 offset in2025/26 ledger. R31 ERI shows zero throughout2025–Oct2026.
R16 current Suppl747 filed12/30/2025 explicitly ratesFeb1,2026–Dec31,2027:
R.00086,G.00041. Previous R16 onlyJan–Feb2025 R.00254,G.00241 in original
historical component ledger; March2025–January2026 zero.

## Exact monthly arrays

2025 arrays orderedJan–Dec.2026 arrays orderedJan–Oct;Nov/Dec not verified.
Parentheses in sources denote credits, represented as negatives.

```python
R25_R_2025 = [.00330,.00424,-.00019,.00371,.00475,-.00295,.00321,.00118,-.00148,.00475,-.00475,.00200]
R25_G_2025 = [.00419,.00064,-.00475,-.00482,-.00340,-.00411,.00046,.00192,-.00171,.00332,-.00482,-.00387]
R25_R_2026 = [.00367,-.00095,-.00189,-.00333,.00482,.00031,.00210,-.00005,-.00152,-.00173]
R25_G_2026 = [-.00086,-.00243,.00250,-.00497,-.00307,-.00477,-.00084,.00297,.00220,.00066]
R10_R_2025 = [-.00097]+[-.00101]*4+[-.00096]*7
R10_G_2025 = [-.00065]+[-.00061]*4+[-.00064]*4+[-.00063]*3
R10_R_2026 = [-.00096]+[-.00111]*4+[-.00107]*4+[-.00108]
R10_G_2026 = [-.00063]+[-.00062]*4+[-.00064]*4+[-.00063]
R16_R_2025 = [.00254]*2+[0]*10
R16_G_2025 = [.00241]*2+[0]*10
R16_R_2026 = [0]+[.00086]*9
R16_G_2026 = [0]+[.00041]*9
# Independent utility-published composite before locality, excluding fixed charges:
CSEG_R_2025 = [.18265,.18332,.17635,.18025,.18129,.18052,.18668,.18465,.21448,.22966,.22016,.19441]
CSEG_G_2025 = [.19423,.19179,.18399,.18392,.18534,.18512,.18969,.19115,.20949,.21860,.21046,.18944]
CSEG_R_2026 = [.19998,.19514,.22670,.22526,.23341,.20865,.21044,.20829,.20682,.20191]
CSEG_G_2026 = [.20887,.21438,.24128,.23381,.23571,.21725,.22118,.22499,.22422,.21754]
```

Composite includes generation+transmission+R8+distributionbase+R25+R16+R10+
EmPOWER+franchise.00062+EES.000150; no fixed customer, USC, localtax, sales tax.
The composite is an independent published arithmetic check, not evidence that
community-solar credit/export settlement is implemented. Source explicitly warns
rounding and customer billing-period timing can change actual credits.

## Scope and rules

R is domestic secondary service; G is secondary general service for customers
not qualifying for another schedule. SOS TypeI is separate eligibility, verified
by supply research; do not infer assignment merely from modeled usage.
G minimum is net delivery customer charge; no demand or energy tiers in base
secondary schedule. R competitive billing credit.62/month,G.47/month applies
only where applicable under§7.7, not automatically to default bundled bills.
R25 monthly change is capped10%; carried imbalances do not imply substituting
neighboring values. Whole calendar service cycles with matching designated
billing month avoid unverified cross-month allocation. Several riders are
explicitly effective with billing-month billings; do not prorate them silently
by service dates. R34 removed2025 by explicit end-date, not by inference.

Tax jurisdiction and mandatory2025/2026 relief credits require separate proof
before the candidate can claim complete all-in bills. Tax specialist owns those.

## Legislative relief is account-specific, separate from recurring tariff charges

Official BGE page:
https://www.bge.com/my-account/customer-support/assistance-programs/legislative-energy-relief-refund
Current content obtained from BGE public content API. Winter eligibility requires
active residential electric account November 1, 2025, and electric usage during
October 1, 2024–September 30, 2025. Average monthly kWh determines refund:
0–435 $30.50;436–1305 $43;1306–2610 $54;2611+ $66. Page identifies winter
refund February–March2026, and prior summer refund August–September2025.
Historical summer tier values and exact per-account posting month are not
established by the current page. Never substitute flat$80 news estimates.
Synthetic annual profiles cannot prove this eligibility or historical usage.
If excluded, outputs must explicitly describe recurring tariff costs before
account-specific legislative refunds, arrears, assistance, optional programs
and prior balances, not a reconstructed account amount due.

Bounded follow-up: The official PSC June27,2025 release states one summer
phase in August **or** September2025 and one winter phase. It does not authorize
duplicating the refund in both listed months. Current BGE text calls the winter
payment the second of two credits and lists the winter tier amount as the total
credit. No source says divide that tier amount across two winter bills. Exact
account posting month remains unverified. Summer eligibility: active residential
account June1,2025, recorded usage in12months endingMarch31,2025, active when
credited. The current BGE page does not preserve primary summer2025 tier values.

PSC source:
https://psc.maryland.gov/news/2025/psc-sets-plan-to-distribute-legislative-relief-fund-to-utility-customers/
The roughly$80 quoted there is an estimated average for both phases combined,
not an exact BGE credit and not permission to apply$80 each season.
