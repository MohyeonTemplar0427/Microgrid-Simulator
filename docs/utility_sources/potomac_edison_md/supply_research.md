# Potomac Edison Maryland supply research

Reviewed October 26, 2026. Scope: **The Potomac Edison Company, Maryland,
Electric P.S.C. Md. No. 54, Schedule R residential SOS and Schedule G Type I
SOS**. The utility, supply class, Maryland jurisdiction, actual account
eligibility and PJM/wholesale metadata are separate facts. No West Virginia,
Ohio or Pennsylvania rates, pending grid surcharge, competitive supplier,
export or community-solar settlement is authorized by this evidence.

## Preserved originals and source scope

Official [Maryland tariff index](https://www.firstenergycorp.com/content/customer/customer_choice/maryland/maryland_tariffs.html)
links the current [retail tariff](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/maryland/tariffs/PotomacEdisonRetailTariff.pdf)
and [adjustment sheet](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/maryland/tariffs/PotomacEdisonaceca.pdf).
The index distinguishes current tariffs from pending revisions. Its disclaimer
says electronic tariffs are not the official documents; these originals are
the utility's published electronic filed/approved tariff copies, with approval
and effective-date footers preserved. Do not substitute a pending filing.

Original PDF/HTML bytes, complete extracted text, selected excerpts and rendered
receipts are in `.cache/potomac_edison_md/sources/supply/`; `records.json` pins
original URLs, byte counts and SHA256s, derivative hashes and physical pages.
`tariff_current.pdf` has 189 physical pages. `adjustments_current.pdf` is one
landscape page, visually checked against the extracted monthly rows. The
R and G rate leaves were also rendered and visually checked. Physical PDF
pages below are one-based; printed tariff page identifiers differ.

The current tariff explicitly dates generation tables for **June 2026–May
2027**, with summer June–September and non-summer October–May blocks.
Transmission has its own leaf clock: R physical62 is effective June1,2026;
G physical70 is effective September1,2026. The latter cannot establish
June–August transmission rates merely because its generation table includes
those dates. The adjustment sheet fills **January–December2026**. The
verified observed-date supply intersection is **June–October2026 for R**,
**September–October2026 for G**, and therefore **September–October2026
in common**. November–December values are published future cycles. This is
supply evidence only, not a complete bill or engine-validation claim.

## Fixture-ready supply rows

Dollar values below are literal published dollars/kWh except capacity/fixed
columns. Supply energy already includes the SOS administrative charge: R
$0.00400/kWh and G Type I $0.00550/kWh (definitions physical11/12). Do **not**
add those embedded charges again. Energy-only decomposition can subtract the
published embedded amount for display, without changing the charged total.

| Service usage | Schedule | Supply first 700 kWh | Supply over 700 kWh | Supply capacity above 7.5 kW |
|---|---|---:|---:|---:|
| Jun–Sep 2026 | R | .10824, all kWh | same | none |
| Oct 2026–May 2027 | R | .10209, all kWh | same | none |
| Jun–Sep 2026 | G Type I | .13108 | .06067 | $9.99/kW |
| Oct 2026–May 2027 | G Type I | .15064 | .06977 | $11.44/kW |

R: physical62, printed6, eleventh revision, effective June1,2026, approved
February18,2026. G: physical70, printed7-1, thirtieth revision, effective
September1,2026, approved July15,2026; the Type I table explicitly states its
June1–September30 and October1–May31 windows. Type II entries on that same
page are excluded.

R transmission is **.00396/kWh for all kWh fromJune1,2026**. G transmission
is verified **fromSeptember1,2026** and is **.00440/kWh
for the first700kWh, .00214/kWh above700kWh**; its capacity/minimum table prints
**$.34/month minimum charge, $.19/minimum kW, and $.24/kW above7.5kW**.
These G rates must not be backdated intoJune–August2026. They are distinct
demand/minimum rules, not three additive per-kWh rates.
Delivery research owns executable minimum/capacity interpretation and its
independent bill reconciliation. G is not a flat non-demand plan.

| 2026 calendar service months | R ECA | R administrative credit | G Type I ECA | G Type I administrative credit |
|---|---:|---:|---:|---:|
| Jan–May | .01480 | -.00193 | -.00118 | -.00220 |
| Jun–Sep | .01716 | -.00234 | .01841 | -.00230 |
| Oct–Dec | .01828 | -.00210 | -.00338 | -.00224 |

Source: adjustment original physical1. Parentheses in the original mean
credits; the table above uses retail charge signs. No monthly cell is blank.
`supply_components_2026.json` saves 24 labeled R/G monthly rows, separate
ECA/credit and generation/transmission verification flags. G June–August
transmission rates are omitted and flagged unverified after the leaf-clock
review; a generation date range is not a transmission effective-date proof. The administrative credit applies to
eligible customers regardless of shopping status. ECA applies only to the
utility's non-shopping SOS customers.

Both ECA and administrative credit take effect **on the first of the month,
on a service-rendered basis**. Current tariff printed5-8/5-9, physical59/60,
says reconciliations normally occur June, October and January, or more often
if necessary. ECA reconciles billed transmission/supply against utility
payments to PJM and wholesale suppliers. That explanation does not make an
account's retail price equal to a PJM wholesale series.

## Eligibility and capacity boundaries

Current physical11/12 (printed4-2/4-3) defines residential SOS and Type I SOS.
R is single-phase residential service through one meter (physical62/63).
Type I G requires the prior year to contain **no 30-minute metered billing
demand at least25kW**, no consumption **over6000kWh in two consecutive
non-summer billing months**, and no consumption **over7500kWh in one summer
billing month**. Summer billing months are June–September; other months are
non-summer. These historical/account facts cannot be inferred from one study
month, a utility name, ZIP or simulated peak.

Physical71 (printed7-2) says the utility categorizes SOS types each June;
customers cannot switch between Type I and Type II during June–May. Capacity
is the highest metered demand over30minutes and normally rounded to the
nearest half-kW. Its minimum-charge capacity uses current required capacity
but no less than half the highest required capacity in the preceding12months.
Connections without a demand meter have a separate kWh/250 rule with history.
Affirmative tariff, meter-method and retained-history confirmation is needed;
no missing history or rounding convention is silently invented here.

## Independent checks and unresolved history

The official [customer-choice page](https://www.firstenergycorp.com/customer_choice/maryland.html)
reports current R price-to-compare **12.433cents/kWh** through May31,2027.
Its stated scope is generation + transmission + ECA. Independently, the
October2026 tariff components sum exactly:
`.10209 + .00396 + .01828 = .12433 dollars/kWh`. Administrative credit,
delivery and taxes are outside that PTC benchmark. This check corroborates
supply only, not a total bill. June–September component sum is .12936/kWh;
this is a derived check, not a separately preserved historical PTC assertion.

**No full-year2025 or2026 supply coverage is established.** The initial index
pass and targeted official historical searches did not recover2025 ECA and
administrative-credit originals. A search index showed a superseded2025
residential leaf at the mutable current URL, whereas the saved live original
contains2026. A January2026 pending filing's redline repeats deleted2025
.09803/.09806 rates; neither observation supplies a preserved final historical
leaf or missing ECA/credit history. January–May2026 base rates therefore also
remain outside the executable supply intersection pending an actual final
source. Do not carry forward a neighboring period, use proposed values or
replace missing adjustments with zero.

A bounded transmission-clock follow-up found only a pending April20,2026
TypeI/II redline repeating G transmission numbers. It is excluded as an
adopted June–August transmission source; no approved June–August leaf was
recovered. The correct G common window remainsSeptember–October2026.

DMS case8908 returned403 to a direct web open; that unchanged route was
stopped. `history_gap_receipt.json` records specific queries, blocked route,
excluded leads and remaining windows. Failure to recover an original does not
prove that no historical source exists. Tax and delivery streams own RGGI,
USC, franchise/MES/local tax, delivery riders, ordinary interconnection and
account-credit exclusions; preserve their separate conclusions.
