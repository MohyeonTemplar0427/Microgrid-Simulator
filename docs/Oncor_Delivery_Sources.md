# Oncor electric delivery rates, 2025–2026

`src/billing/oncor_tx_delivery.py` returns the recurring Oncor wires charges for a
standard, individually metered premise. The REP energy contract, REP fees, taxes and
ERCOT market prices are separate. Delivery factors use imported kWh only. No export
credit, competitive-meter credit, industrial EECRF exemption, unmetered service,
discretionary work, construction charge or special facilities contract is modeled.

## Schedules and eligibility

| Filed schedule | Supported premises |
|---|---|
| 6.1.1.1.1 Residential Service | Permanent dwelling or individually metered apartment, a unique 911 address, one delivery point and a standard utility meter, without sharing or resale. |
| 6.1.1.1.2 Secondary Service Less Than or Equal to 10 kW | Ordinary metered, nonresidential secondary-voltage service, one delivery point and standard utility meter, without sharing or resale. The tariff permits single and three phase. A specific REP may be narrower. |

Current classification and recorded demand history are account facts. Before June 1,
2026, any recorded maximum demand over 10 kW moved the premise to the larger
secondary schedule in the next billing month. From June 1, a third recorded
exceedance of 10 kW in a rolling 12-month period or any recorded exceedance of
12 kW triggers the move the following billing month. Returning from the larger class
requires 12 consecutive months at or below 10 kW. A conservative scope of peaks
at or below 10 kW throughout the relevant history satisfies both upward rules. Individual
retail labels can impose a stricter threshold. Residential eligibility changed for
some accessory structures and mixed premises in June 2026. Restrict the scope to
ordinary residential service with a documented classification.
[Historical tariff, sheets 1.1–1.3](https://www.oncor.com/content/dam/oncorwww/documents/about-us/regulatory/tariff-and-rate-schedules/Tariff%20for%20Retail%20Delivery%20Service_.pdf.coredownload.pdf) · [Current Oncor tariff](https://www.oncor.com/content/dam/oncorwww/documents/about-us/regulatory/tariff-and-rate-schedules/Tariff%20for%20Retail%20Delivery%20Service.pdf.coredownload.pdf) · [Delivery charges and reclassification](https://www.oncor.com/content/oncorwww/us/en/home/about-us/regulatory/delivery-charges-101.html)

## Dated totals

Totals below are the sums of filed factors. Customer and metering charges were
$1.43 + $2.80 residential and $2.26 + $4.61 secondary through May 2026.
From June 1, 2026 they were $1.48 + $2.58 residential and $2.34 + $4.36 secondary.
The table gives posted factors in dollars per kWh. Transition rows require the
invoice rules below before they can be applied to a service cycle.

| Date in scope | Changed factor | Residential $/kWh | Secondary ≤10 kW $/kWh |
|---|---|---:|---:|
| 2025-01-01 | Opening factors carried from 2024 | .052974 | .044705 |
| 2025-02-24 | Rate case expense goes to zero | .052920 | .044650 |
| 2025-03-01 | Transmission and energy efficiency | .050029 | .044602 |
| 2025-05-10 | Distribution cost recovery | .051248 | .046202 |
| 2025-09-01 | Transmission cost recovery | .056032 | .045753 |
| 2025-12-01 | December mobile generation | .057059 | .046359 |
| 2025-12-15 | Nuclear decommissioning goes to zero | .056860 | .046229 |
| 2026-01-01 | December mobile generation ends | .055833 | .045623 |
| 2026-03-01 | Energy efficiency | .056183 | .045874 |
| 2026-06-01 | New base, zero distribution recovery, new rate-case expense | .061196 | .049532 |
| 2026-08-01 | Transmission factor and new interim surcharge | .060295 | .051227 |
| 2026-10-04 | Temporary transmission and distribution recovery factors | .068673 | .053843 |

The component ledger retains the signed commercial energy-efficiency credit in
March 2025–February 2026. Rider MG applies only in December and Rider IS starts
in August 2026, even though its recovery relates to an earlier period. Nuclear
decommissioning and mobile generation explicitly require rounding the extended
charge to the nearest cent. Sheets 2.1, 3.1 and 4.1 list TC, CTC and SBF as
inapplicable. Rider ISR was a one-billing-month refund, last dated November 27,
2023 in the historical book. State sales-tax exclusions for separately disclosed
nuclear charges are an invoice treatment. The delivery model leaves that decision
to the REP billing layer.
[PUCT historical base and NDC](https://interchange.puc.texas.gov/Documents/54817_28_1322201.PDF) · [PUCT historical RCE](https://interchange.puc.texas.gov/Documents/54817_28_1322202.PDF) · [Oncor Q2 2026 report on base-rate implementation](https://www.sec.gov/Archives/edgar/data/1193311/000119331126000019/c311-20260630x10q.htm) · [Texas Comptroller retail electricity tax guidance](https://comptroller.texas.gov/taxes/publications/96-1309.pdf)

## Cycle boundaries and source check

The historical study supports one complete calendar month per rate lookup. February
and May 2025 and October 2026 require the documented Oncor invoice date to be the
last service day. For February, the regulator confirms the last February billing-month
charges were collected by February 21 and billing stopped February 24. The DCRF order
and October 2026 temporary tariff explicitly use bills rendered on or after the
effective date. These transitions apply the new factor to the invoice's entire
monthly determinant. A different or unknown rendering date is outside this scope.
[February termination order, findings 5–7](https://interchange.puc.texas.gov/Documents/57799_7_1491155.PDF) · [May DCRF order, findings 43–44 and 53–54](https://interchange.puc.texas.gov/Documents/57707_46_1492438.PDF) · [October implementation notice and temporary sheets](https://interchange.puc.texas.gov/Documents/59249_105_1676040.PDF)

December 2025 remains blocked as a complete cycle. The PUCT order and agreed motion
set a December 15 effective date for zero NDC without establishing whether the
change applies by billing date or service allocation. Both daily posted rates
are available for inspection. November 2026 was still in progress at the November 19
evidence cutoff. Billing cycles ending later and December 2026 factors are unverified.
[NDC approval](https://interchange.puc.texas.gov/Documents/58826_12_1563610.PDF) · [NDC agreed motion](https://interchange.puc.texas.gov/Documents/58826_8_1561639.PDF)

The published 2025 Oncor monthly summary matches the January, March/April,
June–August and September/October residential rates. Use filed effective dates
for transition invoices. For small commercial the October 2025 NEC label independently
quotes $6.87 and 4.5753¢/kWh, and its November 2026 label quotes $6.70 and
5.3843¢/kWh. A 1,000 kWh September 2026 small-commercial delivery subtotal
using SFE's published $6.70 and 5.12270¢/kWh is $57.93. Issued REP labels can
contain stale or differently rounded delivery examples, including January 2026
NEC small commercial quoting the December MG amount.
[Oncor historical customer summary](https://www.oncor.com/content/dam/oncorwww/documents/partners/rep/Oncor%20Residential%20Rates.pdf.coredownload.pdf) · [NEC October 2025 label](https://neccoopenergy.com/wp-content/uploads/2025/10/EFL-10-1-25-SM-COMM-_Oncor.pdf) · [NEC November 2026 label](https://neccoopenergy.com/wp-content/uploads/2026/10/EFL-11-1-26-SM-COMM-_Oncor.pdf) · [SFE September 2026 commercial charges](https://www.sfeenergy.com/tducharges/)

Source copies are in the ignored `.cache/oncor_tx/` evidence directory. The
retrieved November 2026 248-page Oncor book (`2026.pdf`) has SHA-256
`404c87f71e57dbb4e2f88e2cc08f027270b60232f7d12aa6dfa4749c1972322e`.
The distinct February 2026 historical file (`march2026.pdf`, 247 pages) has SHA-256
`5bd13b2f275bdde44b9ac6a2945b3e624cca35931c64dd41ba818b75d2e936f7`.
The public Oncor URLs are mutable. For verification use the recorded editions
and the dated PUCT filings.

## Secondary Service Greater Than 10 kW

Sheet 1.3 (§6.1.1.1.3) serves a secondary-voltage premise with one meter and one
point of delivery. This implementation covers established single-phase premises
assigned to that schedule and billed on unadjusted 15-minute noncoincident
peak (NCP). It accepts the band with a documented maximum above 10 and at or
below 20 kW for the preceding eleven billing months and caps the study peak at
20 kW. Oncor's assignment and the historical peak need independent account
evidence. Metered kW must already reflect any meter multiplier.
[Filed rate schedule and service rules](https://www.oncor.com/content/dam/oncorwww/documents/about-us/regulatory/tariff-and-rate-schedules/Tariff%20for%20Retail%20Delivery%20Service.pdf.coredownload.pdf) · [Oncor's metering and class explanation](https://www.oncor.com/content/oncorwww/us/en/home/about-us/regulatory/delivery-charges-101.html)

Three billing determinants apply to this band. The energy-efficiency rider
uses imported kWh. The distribution charge and transmission rider use the
highest 15-minute imported kW in the current month. Riders NDC, DCRF, RCE and
MG use the larger of this NCP and 80% of the highest NCP in the eleven
preceding billing months. Rider IS names the distribution system billing kW,
which in this band is the current NCP. Class eligibility follows the documented
Oncor assignment for the billing month. The June 2026 revision explicitly
moves a customer down in the month after twelve consecutive billing months
without an exceedance of 10 kW.

The table gives dollars per billing determinant. DCRF, NDC, RCE and MG share
the rider ratchet. The customer and metering charges total $32.43 per month
through May 2026 and $44.99 per month from June 2026.

| Effective date | Base $/NCP kW | TCRF $/NCP kW | IS $/NCP kW | EECRF $/kWh | DCRF $/ratchet kW | NDC $/ratchet kW | RCE $/ratchet kW | MG $/ratchet kW |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025-01-01 opening | 5.121040 | 4.959012 | 0 | .000407 | .819305 | .045 | .012192 | 0 |
| 2025-02-24 | 5.121040 | 4.959012 | 0 | .000407 | .819305 | .045 | 0 | 0 |
| 2025-03-01 | 5.121040 | 4.675281 | 0 | .000223 | .819305 | .045 | 0 | 0 |
| 2025-05-10 | 5.121040 | 4.675281 | 0 | .000223 | 1.036859 | .045 | 0 | 0 |
| 2025-09-01 | 5.121040 | 5.114972 | 0 | .000223 | 1.036859 | .045 | 0 | 0 |
| 2025-12-01 | 5.121040 | 5.114972 | 0 | .000223 | 1.036859 | .045 | 0 | .156662 |
| 2025-12-15 | 5.121040 | 5.114972 | 0 | .000223 | 1.036859 | 0 | 0 | .156662 |
| 2026-01-01 | 5.121040 | 5.114972 | 0 | .000223 | 1.036859 | 0 | 0 | 0 |
| 2026-03-01 | 5.121040 | 5.114972 | 0 | .000546 | 1.036859 | 0 | 0 | 0 |
| 2026-06-01 | 6.931363 | 5.114972 | 0 | .000546 | 0 | 0 | .016827 | 0 |
| 2026-08-01 | 6.931363 | 5.022675 | .997891 | .000546 | 0 | 0 | .016827 | 0 |
| 2026-10-04 | 6.931363 | 4.606104 | .997891 | .000546 | 1.068522 | 0 | .016827 | 0 |

The table separates effective-date lookup from monthly settlement. The February
and May 2025 and October 2026 transitions require the final-day invoice
convention documented above. December 2025 remains blocked. The underlying
sources are sheet 1.3 (PDF pp. 72–74) in both archived Oncor books, §5.5.5
for power-factor adjustments, sheets 5.1 and 6.1–6.7 for rider factors and
the base, RCE and subsequent dated orders linked above.

For an independent check, TXU's September 19, 2025 comparison gives $32.43 per
month, $0.000223/kWh and $11.317871/kW when all demand determinants coincide.
TXU's April 11, 2026 comparison gives $32.43, $0.000546 and $11.272871.
Frontier's November 13, 2026 publication reproduces the October 4 filed
factors at $44.99, $0.000546 and $13.620707. These comparisons require equal
demand determinants. With 1,500 kWh, 12 kW this month and a 20 kW prior
maximum, the 16 kW rider determinant gives model delivery subtotals of
$172.90 for September 2025, $190.64 for June 2026, $201.50 for September
2026 and $213.60 for October 2026 after half-up cents per line.
[TXU September 2025 comparison](https://www.txu.com/-/media/Project/VistraApps/DT/Files/Content-Pages/Help-Center/20250919_-_TDU_Charges_Web_Update_COMMERCIAL_GT10KW_ENG_DETAIL.pdf) · [TXU April 2026 comparison](https://www.txu.com/-/media/Project/VistraApps/DT/Files/Content-Pages/Help-Center/20260411_-_TDU_Charges_Web_Update_COMMERCIAL_GT10KW_ENG_DETAIL.pdf) · [Frontier's November 2026 comparison](https://www.frontierutilities.com/tdsp-charges)

Outside the implemented band, sheet 1.3 has distribution price bands based
on annual load factor, with additional rules for the distribution determinant
and seasonal agriculture. Premises ever reaching 700 kW in a previous month,
or previously billed on 4CP under the tariff, may require prior-year June
through September ERCOT coincident-peak meter history. The four readings are
averaged for the subsequent calendar year's transmission billing. Separate
provisions govern unavailable 4CP history and utility-assessed adjustments
for power factor below 95% lagging. These accounts, special metering, and
initial partial reads require additional billing support.
