# Delmarva Maryland tax, eligibility and billing rules

Read-only research, 2026-10-26. This evidence applies to **Maryland**, ordinary
R residential and a deliberately narrow SGS-S Type I SOS account. Delaware,
Pepco and BGE rate treatments are not substitutes. Originals, SHA-256 hashes,
URLs and selected excerpts are in `.cache/delmarva_md/sources/tax/`;
`tax_records.json` records originals retained by other source owners as well.
No production files or Git index entries were changed by this task.

## Primary pins and explicit locality

The principal historical original is the [July 2, 2025 tariff book](https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/bltefc1a0bec7ba2be7/6866ba338877742a736471bb/DPL_MD_Environmental_Surcharge_Update_Filing_.pdf?branch=prod_alias),
198 physical PDF pages. References below give **physical page / printed leaf**.
The [current October 2026 book](https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/bltefc1a0bec7ba2be7/6abbd8bb794a17e7adb9629e/9226_9056_9064_DPL_MD_CURRENT_CLEAN_Admin_Charge_RTOUND_eff_100126.pdf?branch=prod_alias)
is retained by supply research; page positions can differ.

Selected hypothetical tax scope: **ordinary unincorporated Wicomico County**.
Weather coordinate 38.40,-75.65 is independent metadata, not jurisdiction,
territory, schedule, supplier or tax-exemption proof. Require separate explicit
account confirmation. [Wicomico Code Chapter 203](https://ecode360.com/10172660)
lists eleven taxation articles, none imposing an electricity/fuel-energy excise.
The official [DLS Guide to Local Government Taxing Authority](https://dls.maryland.gov/pubs/prod/InterGovMatters/LocFinTaxRte/FinalGuidetoLocalGovernmentTaxingAuthority.pdf),
physical 87–89 / printed 83–85, likewise enumerates Wicomico tax authority without
an energy tax. Treat no additional ordinary county energy levy as a documented
**code-based inference**, not an express zero-rate certificate. Municipalities,
special agreements, exemptions and unverified extra local assessments are outside
scope. Direct county-code download returned 403; the web read succeeded and a
receipt is retained; do not describe its HTML as preserved.

## Eligibility, demand and minimum

- Historical 76/57: R covers household/related uses at one private dwelling or
  dwelling unit, farmstead or estate and pertinent detached buildings. Confirm
  ordinary R classification and no AMI opt-out, assistance or special charges.
- 86/61: SGS-S is available at secondary voltage with monthly maximum measured
  demand below 300 kW; a month at/above 300 transfers to LGS-S next month.
- 159/120: SOS Type I includes SGS-S except those assigned Type II. Type II
  triggers: measured demand at/above 25 kW in any of twelve billing months;
  energy above 6,000 kWh in two consecutive **October–May** winter billing
  months; or above 7,500 kWh in one summer billing month. SOS type changes
  annually with **June billing month**. A simulated load does not establish
  existing utility-assigned type or erase prior history.
- 87/62 E1: measured demand is greatest 15-minute demand, nearest whole kW,
  except E2/E3. Exact half-kW tie behavior is not stated. E2 is contracted
  off-peak service and remains excluded.
- 87/62 E3: for actual demands below 20 kW, the **utility** may choose measurement,
  test assessment or estimation. When estimated, demand is monthly kWh / 175,
  capped at 20 kW. E1 expressly excepts E3; do not add invented whole-kW rounding
  to this separate formula. Test-assessed/measured accounts are different facts.
- 87/62 G–H: billing demand is current month's maximum measured demand; no SGS-S
  ratchet is specified here. Minimum monthly charge is the customer charge.
- 55/47: SGS-S distribution demand charges apply per billing kW, including the
  first 20 kW. Transmission demand is free for first 20 kW, with a separate
  greater-than-20 charge; transmission energy applies to first 3,500 kWh only.

**Sound first executable SGS-S domain:** explicit utility-assigned E3 estimated
method, actual physical peak below 20 kW, imports at most 3,500 kWh each complete
cycle, existing Type I independently confirmed, and the same utility-approved E3
method retained across grid/PV/battery scenarios. Then estimated billing demand
is exactly E/175, transmission demand charge is zero, and transmission energy is
linear in E. This is a narrower account domain, not a new non-demand schedule.
Do not promise peak-shaving demand savings: E3 demand responds to imported energy.

## USP, franchise and embedded GRT

Historical 154/115, current 156/115, Tenth Revised USP rider, filed February 1,
2023 effective usage January 1, 2023:

- R: **$0.32/month/residential customer**.
- SGS-S: prior calendar year's annual **distribution** billing/revenue sets band;
  updated during **first quarter** each new year, not necessarily January 1.
  Under $175 => $0.25/month; $175–$1,299 => **$1.85/month**;
  $1,300–$2,599 => $6.14/month. Full remaining table is in preserved excerpt.
- For a fixed $1.85 hypothetical, require explicit independent confirmation that
  this utility-assigned band covers each entire modeled 2025 and 2026, before
  and after the first-quarter update. Never recompute from optimized bills.

Historical R48/45 and SGS55/47 explicitly list **franchise tax $0.000620/kWh**.
The official CSEG sheets state GRT is **embedded in applicable rates**; there is
no basis for adding Pepco's separate 2.0408% GRT to Delmarva's published rates.
This treatment is independently provider-verified. Preserve generation/admin,
PCA, transmission, delivery and franchise as separate retail components; do not
add wholesale PJM prices, PLC/NSPL charges or an extra inferred PSC assessment.
An embedded allocation does not establish the amount of every underlying tax.

## MES actual tariff versus statutory assessment

The July 2, 2025 filed original R48/45 and SGS55/47 prints **$0.000151/kWh**,
effective **usage on/after July 2, 2025**, expressly filed in compliance with
MDPSC's June 30, 2025 General Notice. This is a filed tariff value, stronger
rate authority than a community-solar table alone. [September 2025 CSEG](https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/68b731f3c1561b3668f1c405/DPL_MD_CSEG_-_09012025.pdf?branch=prod_alias)
physical 1/2 independently shows R/SGS MES $0.000150 April–June 2025 and
$0.000151 July–September 2025. [Current CSEG](https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias)
shows $0.000151 May–June 2026 and $0.000150 July–October 2026.
The recovered [July 6, 2026 archived tariff book](https://azure-na-assets.contentstack.com/v3/assets/blt47b6e332b18fb457/blt51d66aaf3a9d1f68/6a6d0cba9307daf5efc549e4/2026-07-06_MASTER_MD_DPL_Tariff_Book_1.pdf),
physical R48/45 and SGS55/47, explicitly prints $0.000150 and states filed
July 6, 2026, **effective usage on/after July 1, 2026**. Its cover identifies the
environmental-surcharge update effective July 1. This resolves the July 2026
effective-day question; that calendar month can be included if all other required
components are independently verified.

[Public Utilities §7-203](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gpu&section=7-203)
sets the environmental assessment maximum as lesser of 0.15 mill/kWh
($0.00015/kWh) or $1,000/month/account. [COMAR 20.50.01.04](https://regs.maryland.gov/us/md/exec/comar/20.50.01.04)
requires MES cent rounding with half-cent upward. These statewide provisions
apply to Delmarva Maryland. **Do not invent an explanation** that $0.000151 is
PSC/GRT gross-up: no explicit decomposition was recovered. Equally, do not
silently replace the explicit filed billed rate with $0.000150. Report the
actual filed billed component and retain the unreconciled distinction from the
statutory assessment cap. A small monthly import domain (e.g. R <=7,500 kWh,
SGS <=3,500) keeps any $1,000 cap inactive, but does not resolve the per-kWh
difference. Large accounts/cap allocation remain unsupported.

**July 2025 crossing:** the CSEG month label cannot override the tariff's July 2
usage date. Without a verified crossing-cycle allocation rule, reject the entire
calendar July 2025 cycle. Dated later complete cycles can use the actual filed
$0.000151 rate without claiming a verified underlying tax decomposition.

## State sales tax, credits and completeness

R/SGS tariff sheets say applicable Maryland sales tax is added unless exempt.
[COMAR 03.06.01.10](https://regs.maryland.gov/us/md/exec/comar/03.06.01.10)
D1 exempts filed residential/domestic-schedule electricity; ordinary SGS-S
commercial electricity and delivery are taxable. C1–C3 exclude late penalties,
county-imposed tax and environmental surcharge from taxable price.
[COMAR 03.06.01.08](https://regs.maryland.gov/us/md/exec/comar/03.06.01.08)
and Tax-General 11-101 generally include vendor-imposed taxes and address
unconditional discounts. [Tax-General 11-104(a)](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gtg&section=11-104)
uses approximately-6% **statutory brackets**, not ordinary cent-rounding of 6%:
$100.01 taxable price gives $6.01. A complete SGS-S invoice needs independently
reconciled tax base, included credits and bracket application. Initial SGS-S
subtotal explicitly excludes **unmodeled state sales tax**, not zero/exemption.

Historical 176/137, current 178/137, RRC First Revised, filed June 28, 2019,
effective usage July 1, 2019: applies R, R-TOU-ND and R-TOU-P, **not SGS-S**;
monthly dollar/customer credit, quarterly update/true-up. Exact 2025–2026 monthly
amounts were not recovered in this bounded pass. Absence from variable CSEG
rates is not zero proof. R subtotal must disclose excluded recurring RRC.

The [PSC June 27, 2025 relief announcement](https://www.psc.state.md.us/wp-content/uploads/MD-PSC-Sets-Plan-to-Distribute-Legislative-Refund-Act-Money_06272025.pdf)
applies statewide residential legislative relief in August/September 2025 and
January/February 2026. First round requires active account June 1, prior usage
through March 31, and active account in posting month. No Delmarva-specific
individual award/tier/posting evidence was recovered; exclude account-specific
legislative relief visibly. Do not substitute BGE/Pepco/Potomac Edison amounts
or derive eligibility/refund from changed simulated imports. Other discretionary
programs require enrollment/event proof and are outside ordinary account scope.

**Initial results are verified-charge subtotals, not complete bills:** R excludes
unverified RRC and legislative credits; SGS-S excludes unresolved state sales-tax
calculation. Local tax treatment remains explicit code-based scope as above.

## Billing periods, PV/storage and benchmark formulas

Historical 18/17: regular monthly meter periods are **25–35 days**; outside that
range bill prorates to 30 days using actual period. Complete 28/29/30/31-day
calendar cycles support one monthly charge; no days/30 reduction is inferred.
No general intramonth rate-change allocation rule was located in this original.
Supply research independently found transmission revision usage August 27,
2025: reject calendar August 2025 unless an allocation source resolves it.
Every other date must be the intersection of all verified components; base-rate
coverage alone does not establish executable month coverage.

Historical 165/126, current 167/126: standby Rider S normally applies parallel
own generation when standby service required, but expressly excepts self-generated
power not exceeding **60 kW** where ordinary classification would otherwise
serve needs. For an initial <=25-kW combined PV/storage hypothetical, require
approved ordinary interconnection/non-export agreement, no standby or special
facilities charges, and utility-confirmed retention of E3 for SGS-S. The exception
does not prove account approval or authorize export settlement. Historical166/127
requires protective/interconnection agreement for parallel operation; utility
technical review remains independent. Standalone storage settlement unverified.

Independent **component** benchmark: delivery's [May2025 CSEG original](https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6813cee9952c500a8dd0aae0/DPL_MD_CSEG_-_05012025.pdf?branch=prod_alias) physical
R1/SGS2 publishes January2025 variable totals R $0.21340320/kWh and SGS TypeI
$0.17833940/kWh. GRT is already embedded. For E=1,000 imported kWh:

- R raw subtotal = $9.43 + $0.32 + E×0.21340320 = **$223.1532**, before excluded
  RRC/legislative credits.
- SGS E3 raw subtotal = $26 + $1.85 + E×0.17833940 + (E/175)×$4.303679 =
  **$230.7818514286**, before excluded state sales tax.

These are independent published-component arithmetic fixtures, **not actual
customer-invoice reconciliation**. Cent rounding of individual lines and total
may differ; preserve that limitation. No seasonal/DST schedule or missing-data
fallback may be inferred; complete consecutive America/New_York intervals and
explicit supported months remain required by the shared implementation.
