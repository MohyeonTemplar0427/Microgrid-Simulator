# Pepco Maryland tax and fixed-surcharge research

Research date: 2026-10-26. Scope: ordinary Schedule R and secondary Schedule GS,
Type I SOS, complete calendar billing cycles, non-export. No production edits or
Git mutations were made by this research task. Source originals, extracted text,
URLs, byte counts and SHA-256 values are in
`.cache/pepco_md/sources/tax/sources.json`. Page references below are **physical
PDF pages**, followed by the tariff page where applicable.

## Explicit jurisdiction and account facts

The proposed hypothetical site is **unincorporated Montgomery County, Maryland**.
The weather coordinate 39.05,-77.18 is separate metadata; it does not establish
utility territory, county, municipal limits, tariff eligibility or an exemption.
Require these facts explicitly on the modeled account. Pepco Rider MCS applies
to customers located in Montgomery County. The ordinary scope has no additional
municipal tax assignment; incorporated places and special exemptions are outside
this initial scope. This is an explicit hypothetical account scope, not a claim
that the coordinate establishes its boundaries.

The county's official [FY2025 public utility fuel-energy tax return](https://www.montgomerycountymd.gov/Finance/Resources/Files/FY2025PublicUtilityReturnFillable.pdf),
physical page 1, is effective July 1, 2024 and lists underlying county electricity
tax of $0.01106/kWh residential/agricultural and $0.01978/kWh nonresidential.
These underlying taxes are **not** Pepco's billed MCS rates. Pepco's surcharge
includes recovery adjustments; do not substitute the county rate or BGE's
provider-specific surcharge.

## Original tariff provisions and USC

[February 4, 2026 full tariff book](https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blte8a580e4cc79e2c4/6984d9aaa88c126a53f51a93/2026-02-04_MASTER_MD_Pepco_Tariff_Book_.pdf?branch=prod_alias),
physical page 80, tariff page 28, Twelfth Revised, issued June 28, 2019,
effective July 1, 2019, lists R at **$0.32/month/account**. This same revision is
physical page 84 of the current supply-agent original
`.cache/pepco_md/sources/supply/book_current.pdf`.

GS uses the customer's **previous annual distribution revenue**, with assignment
updated **in the first quarter of each new year**, under the Commission order.
The tariff does not say every account changes on January 1. Consequently a
calendar-year mapping must explicitly confirm that its utility-assigned band
applies to all modeled cycles, including cycles before and after the utility's
first-quarter update. Changing bands require verified effective cycles/dates.
Never recompute this assignment from a modeled grid-only, PV or battery bill.

| Previous annual electric distribution bills | Monthly USC |
|---|---:|
| Under $175 | $0.25 |
| $175–$1,299 | $1.85 |
| $1,300–$2,599 | $6.14 |
| $2,600–$6,499 | $12.28 |
| $6,500–$12,999 | $24.56 |
| $13,000–$25,999 | $36.85 |
| $26,000–$51,999 | $49.13 |
| $52,000–$77,999 | $92.12 |
| $78,000–$103,999 | $122.82 |
| $104,000–$129,999 | $184.22 |
| $130,000–$181,999 | $276.35 |
| $182,000–$233,999 | $368.46 |
| $234,000–$259,999 | $552.69 |
| $260,000–$519,999 | $736.91 |
| $520,000–$779,999 | $982.55 |
| $780,000–$1,039,999 | $1,228.19 |
| $1,040,000–$1,299,999 | $1,473.83 |
| $1,300,000–$1,559,999 | $1,719.47 |
| $1,560,000–$1,819,999 | $1,965.10 |
| $1,820,000–$2,079,999 | $2,149.33 |
| $2,080,000–$2,339,999 | $2,333.56 |
| $2,340,000–$2,599,999 | $2,456.38 |
| $2,600,000–$3,249,999 | $2,579.20 |
| Over $3,250,000 | $2,763.43 |

Preserve the original wording of the upper bracket: the printed table leaves
$3,250,000 itself ambiguous. Initial small-GS scope needs only explicitly assigned
$175–$1,299 ($1.85) and must not infer any assignment from building demand.

In the same February book:

- Physical 90, tariff 36: Rider DT recovers Franchise Tax (Delivery), applicable
  R and GS; revision issued June 28, 2019, usage effective July 1, 2019. The
  current numerical factor is published separately.
- Physical 91, tariff 37: Rider MCS applies Montgomery County, recovers its
  fuel-energy tax, and normally is recomputed/revised July 1.
- Physical 92, tariff 38: Rider MES recovers the Maryland environmental
  surcharge, normally determined June 30 for the following year.

## Precisely supported numerical tax dates

[December 2024 other-surcharge original](https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blt6afbc02ddcc5eacf/674dbba2c60dc40bdfec926a/Pepco_MD_Other_Surcharges_-_122024.pdf?branch=prod_alias),
physical page 1, has columns July 2024–June 2025 but **only July–December 2024
are filled**. It identifies MES meter-read applicability July 1, 2024–June 30,
2025; MCS effective energy transmitted/distributed on/after July 1, 2024; and
DT effective billing month April 2000. Do not treat blank future columns as
observed monthly rate values or extend values across a later annual revision.

[February 2025 CSEG original](https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blt184aa0644dce17a4/67a0f1215b6934124e523dd3/Pepco_MD_CSEG_-_02012025.pdf?branch=prod_alias),
physical pages 1 (R) and 5 (GS), explicitly fills January and February 2025:

| Component | R | GS | Units |
|---|---:|---:|---|
| MCS | 0.0113205 | 0.0202459 | $/kWh |
| MES | 0.0001500 | 0.0001500 | $/kWh |
| DT | 0.0006200 | 0.0006200 | $/kWh |

[July 2026 other-surcharge original](https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blt6afbc02ddcc5eacf/6a45513583e4e82736c79df7/Pepco_MD_Other_Surcharges_-_072026_.pdf?branch=prod_alias),
physical page 1, fills **every July 2026–June 2027 column**:

| Component | R | GS | Units / effective clock |
|---|---:|---:|---|
| MCS | 0.0113242 | 0.0202525 | $/kWh; transmitted/distributed on/after July 1, 2026 |
| MES | 0.0001500 | 0.0001500 | $/kWh; meters read on/after July 1, 2026 |
| DT | 0.0006200 | 0.0006200 | $/kWh; billing month April 2000 onward |

[October 2026 CSEG original](https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blt184aa0644dce17a4/6abebe49c7c45d25867c0a5a/CSEG_MD_Pepco_-_10_2026_.pdf?branch=prod_alias),
physical pages 1 (R) and 4 (GS), recovered by delivery research, explicitly
lists May–June 2026 MCS at R $0.0113227/kWh and GS $0.0202499/kWh,
DT $0.00062/kWh, and MES **$0.000151/kWh**. July–October 2026 agrees with
the July 2026 other-surcharge original. The May–June MES value conflicts with
the simple statutory $0.00015/kWh cap described below; possible embedded
recovery/gross-up or source error remains unverified. Do not silently replace
it with $0.00015 or claim the apparent discrepancy resolved. Pending an
original PSC/Pepco explanation, reject these cycles or visibly omit the
unverified component in an explicitly incomplete subtotal.

**Gap:** exact Pepco MCS numerical original for July 2025–April 2026 was not
recovered. Likewise, this research has no complete dated monthly tax ledger
for March 2025–April 2026. Current tax sheets, BGE tables and underlying county
rates cannot fill the missing Pepco dates. Candidate coverage must be the
intersection with verified supply and delivery components; dates with a missing
required component must be rejected.

The current sheet also lists Prince George's tax $0.0164260/kWh, but that
jurisdiction is outside this selected scope. No other county tax or municipal
exemption is inferred. The sheet contains **no RGGI/RRC values**.

## GRT, PSC and charge bases

Pepco's R/GS schedules impose **2.0408% GRT on transmission and distribution**.
Listed transmission energy rates exclude the separately calculated GRT; this
differs from BGE's inclusive transmission presentation. Do not copy BGE tax
handling. There is no verified separate PSC adder to apply on top of Pepco's
published supply/delivery rates. The MCS recovery adjustments already differ
from the underlying county tax; adding PSC again would risk double counting.

The February 2025 CSEG original marks the following volumetric components with
footnote (1), which directs multiplication by GRT rate 2.0408%: transmission,
distribution energy, BSA, DT, MES, EmPOWER, RDM and MYP. **Administrative Credit
is unmarked**. MCS appears separately after the pre-county total and is unmarked.
Therefore apply GRT to verified taxable components, excluding MCS and avoiding
an unsupported subtraction of Administrative Credit from the GRT base. This
source establishes component classification; it does not authorize export or
community-solar settlement in the simulator.

[Customer handbook original](https://azure-na-assets.contentstack.com/v3/assets/bltbb7c204688a1a6a8/bltb614da37169223d7/676420cc48ed59e05a475e13/AYS_Pepco-MD_Customer_Handbook_12.24_ada.pdf),
physical page 7, provides a **December 1–30, 2022** 308-kWh sample, despite the
brochure being labeled 2024–2025. Distribution GRT $0.43 reconciles to rounded
customer, energy, federal-credit, DT, USC and MES/EmPOWER charges. The sample
supports fixed customer/USC inclusion but cent rounding cannot isolate every
small component. Transmission 308×$0.01296=$3.99 plus GRT $0.08 is separate.
Do not use this 2022 sample as a 2025 rate benchmark.

The independent 2025 bill-education original (supply agent's
`bill_education_2025.pdf`, physical 3) shows 987-kWh transmission at $0.01951,
$19.26 energy plus $0.39 GRT, consistent with separate 2.0408% calculation.
It is a Jan 29–Feb 25 blended bill, not a calendar-February benchmark.

## MES cap and rounding; state sales-tax limits

Maryland [Public Utilities §7-203](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gpu&section=7-203)
applies to electric companies serving retail customers and caps each account's
MES at the lesser of 0.15 mill/kWh ($0.00015/kWh) and $1,000/month.
[COMAR 20.50.01.04](https://regs.maryland.gov/us/md/exec/comar/20.50.01.04)
requires the MES charge to round to cents with half-cent upward. These statewide
rules apply to Pepco; provider-specific published factors remain separately
verified above. Existing official originals were copied from the BGE source
cache into this task's cache; the manifest labels that provenance.

[COMAR 03.06.01.10](https://regs.maryland.gov/us/md/exec/comar/03.06.01.10):
residential/domestic filed-schedule electricity is exempt (D1); ordinary
commercial electricity and delivery are taxable unless a documented production
or buyer exemption applies. Tax base excludes county-imposed tax (C2), MES (C3)
and late penalties (C1). Administrative/commercial offices and retail facilities
are not production exemptions. [COMAR 03.06.01.08](https://regs.maryland.gov/us/md/exec/comar/03.06.01.08)
generally includes vendor-imposed excise taxes in price and excludes directly
buyer-imposed consumer excises and unconditional price discounts as specified.

**Unresolved compound-base detail:** Pepco MCS includes a recovery gross-up,
while the legal exclusion describes the amount of county-imposed tax. An exact
Pepco source proving exclusion of the entire MCS line, rather than only its
underlying county-tax amount, was not located. GRT on MES and credit treatment
also need an independently reconciled ordinary GS bill or explicit computation
rule before a complete invoice claim.

**New rounding concern, recorded separately from earlier BGE evidence:**
[Tax-General §11-104(a)](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gtg&section=11-104)
and official Comptroller [Business Tax Tip 8](https://www.marylandtaxes.gov/forms/Business_Tax_Tips/bustip8.pdf)
require the approximately-6% statutory **brackets**. For example taxable $100.01
produces $6.01 under the bracket, while round-half-up of exactly 6% yields
$6.00. No Pepco-specific alternative authority was found. Ordinary cent-rounding
of 6% is not established as correct by the general 6% rate alone. This research
does not modify or relabel existing BGE implementation/evidence.

Safe initial Pepco GS scope: a **verified-charges subtotal excluding unverified
state sales tax**, explicitly flagged incomplete. Exclusion means unknown/
unmodeled, not zero tax or a claimed exemption. A complete GS bill requires
resolution of the base and rounding issues above.

## Legislative relief and other account-specific credits

The Maryland PSC's [June 27, 2025 original announcement](https://www.psc.state.md.us/wp-content/uploads/MD-PSC-Sets-Plan-to-Distribute-Legislative-Refund-Act-Money_06272025.pdf),
physical pages 1–2, establishes two rounds: August/September 2025 and
January/February 2026. First-round eligibility requires an active residential
account June 1, 2025, usage during the 12 months ending March 31, 2025, and an
active account in the credit posting month. Refund is based on historical
average usage, not a changed simulation's optimized imports.

Case 9798, Order 91749 (July 24, 2025), concerns implementation. Exact
Pepco-specific individual amounts, historical-use tiers and posting cycles for
both rounds were **not verified** in this bounded research. No BGE or Potomac
Edison amounts may be substituted. The generic PSC announcement is insufficient
to choose one posting month or compute a Pepco account credit. Require original
account eligibility/award/posting evidence; otherwise exclude with a visible
limitation and never claim the result is a complete actual residential invoice.

RRC/RGGI is a separate recurring tariff credit (owned by delivery research),
not the Legislative Energy Relief Refund. February 2026 book physical page 116
(current book physical 120), tariff page 50, First Revised, issued June 28,
2019 effective usage July 1, 2019, applies to R, R-TM and R-TOU-P, **not GS**.
It is a monthly dollar-per-customer credit, updated/trued up quarterly, beginning
billing month June 2009. Thus among the selected ordinary R/GS plans only R
requires this recurring-credit exclusion. Missing RRC history is not resolved
by excluding account-specific legislative assistance. Production/export,
community solar, municipal accounts and tax-exempt organizations remain outside
this initial ordinary account scope.

## Blocked research routes and next targeted evidence

Current other-surcharge table was recovered through Pepco's current-rate page.
Indexed older December 2024 and February 2025 CSEG originals were recovered.
Exact searches for the missing 2025 other-surcharge original did not recover it;
public archive full books do not embed its numerical table. The current
community-solar route did not yield a new historical ledger during this bounded
pass. Python's local certificate store failed for additional downloads; curl
retrieved the official originals successfully, without disabling verification.

Prior BGE research also recorded Cloudflare-blocked PSC environmental-notice
downloads (`.cache/bge_md/sources/general-notices.html` and
`psc_notice214.response`). Those unchanged failing routes were not retried.

Next targeted sources: dated Pepco July 2025–April 2026 other-surcharge/CSEG
original; complete PCA/BSA/Admin Credit monthly history (other owners); original PSC FY2026 assigned environmental surcharge notice (June 30, 2025)
and Pepco explanation of May–June MES $0.000151; exact
Pepco RRC quarterly ledger; original Pepco ordinary-GS bill with itemized sales
and GRT tax; Pepco-specific legislative refund award and posting evidence.


## Final bounded implementation intersection

The initial executable intersection is January–February 2025 and July–October
2026, subject to the other owners' complete supply/delivery ledgers. Reject
May–June 2026 pending resolution of the published MES $0.000151 discrepancy.
At an explicit maximum **7,500 imported kWh per month**, verified MES $0.00015
produces $1.125 before required cent rounding ($1.13); the $1,000 monthly cap
is certainly inactive. Keep the kWh limit explicit rather than omitting cap
logic without a supported consumption bound.

For the hypothetical small GS, require independent confirmation that the
utility-assigned $175–$1,299 USC band remains $1.85 throughout **each whole
modeled year 2025 and 2026**, before and after the utility's first-quarter
update. Same-band assignments may remain fixed across all three technology
scenarios. This does not prove an actual account's prior-year delivery bills.
