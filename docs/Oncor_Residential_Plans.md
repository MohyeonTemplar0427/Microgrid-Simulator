# Oncor residential retail plans

The catalog covers three named products for independently confirmed residential
accounts in Oncor territory. It keeps each supplier’s energy price separate
from Oncor’s delivery tariff. It covers recurring, non-export service. Each
source record in [the residential ledger](../src/billing/oncor_tx_residential.py)
contains the issuer’s document URL and SHA-256 digest. Original downloads for
this review are under `.cache/oncor_tx/residential/`.

## 4Change Energy One Rate 24

Value Based Brands LLC dba 4Change Energy (Texas REP certificate 10041)
charges $4.95 per billing cycle plus the signed version’s flat energy price.
Each version has a 24-month initial term and passes through Oncor delivery.
The study requires documented enrollment, active paperless billing with a
valid email, the ordinary 9% renewable selection, and positive monthly usage.
The terms permit a fee for zero usage, electronic-document delivery failures
and the optional renewable upgrade. Support covers standard grid-only service
and the recurring subtotal. The EFL and terms do not establish how the REP
itemizes the Texas PUC assessment for the account. [Residential terms](https://www.4changeenergy.com/docs/TOSA_4ChangeEnergy.pdf)

| EFL issue date and version | Supply (¢/kWh) | Printed averages at 500 / 1,000 / 2,000 kWh (¢/kWh) | Eligible service months for activation on the issue date |
|---|---:|---|---|
| [2024-09-01, onerta24lah_o](https://www.4changeenergy.com/docs/efl_onerta24lah_o.pdf) | 9.8273 | 16.9 / 15.9 / 15.5 | January–November 2025 and January–August 2026 |
| [2025-09-02, onerta24mac_o](https://www.4changeenergy.com/Docs2/efl_onerta24mac_o.pdf) | 10.7278 | 18.2 / 17.2 / 16.8 | October–November 2025 and January–October 2026 |

At 1,000 kWh, the September 2025 disclosure comprises $112.228 of supply
and $60.262 of Oncor delivery. The $172.49 subtotal gives the printed
17.2¢/kWh. All six examples reconcile at the published precision with the
Oncor rates at label issue. The 2024 comparison uses the September column
of Oncor’s 2024 summary ($4.23 plus $0.052000/kWh). Actual study bills
use delivery rates for the simulated cycle. [2024 Oncor residential summary](https://www.oncor.com/content/dam/oncorwww/documents/partners/rep/Oncor%20Residential%20Rates%20December%202024.pdf.coredownload.pdf) · [2025–2026 delivery source ledger](Oncor_Delivery_Sources.md)

The earlier edition is available for accounts carrying the original signed
contract into 2025. The September 2025 edition first covers a complete
calendar cycle in October. A renewal requires its own label. Neither edition
pays for exports. The modeled recurring subtotal excludes municipal charges,
taxes and optional fees. Early cancellation, default renewal and budget
billing fall outside the supported service conditions.

## Constellation NewEnergy fixed supply

The following editions of **12 Month Residential Fixed Rate** all have a zero
monthly supplier charge, zero minimum-usage fee, flat supply pricing and a
$150 early termination fee. The termination fee is outside continuing service.
The labels say the supplier does not purchase excess generation. Oncor bills
its applicable delivery charges to the REP, which passes them through.

| Label date | Supplier energy (¢/kWh) | EFL average (¢/kWh) at 500 / 1,000 / 2,000 kWh | Original label |
|---|---:|---|---|
| 2024-12-06 | 10.40 | 16.6 / 16.1 / 15.9 | [310745](https://www.constellation.com/bin/residential/GetContractVersionPDF?versionNum=310745) |
| 2025-05-01 | 11.30 | 17.2 / 16.8 / 16.5 | [381771](https://www.constellation.com/bin/residential/GetContractVersionPDF?versionNum=381771) |
| 2026-04-01 | 8.85 | 15.3 / 14.9 / 14.7 | [4930520](https://www.constellation.com/bin/residential/GetContractVersionPDF?versionNum=4930520) |

A customer must identify the version on their contract. Section 1 of
Constellation’s Texas terms starts service at the initial TDU meter read.
The contract states the term in months. An eligible study needs the actual
contract service dates, including any confirmed carry-in from 2024. A later
label has no effect on another customer's fixed contract. A renewal can carry
different prices. The EFL permits specified regulatory changes and the TOS
assigns applicable taxes and assessments to the customer. Budget billing,
municipal underground-facility charges, contract changes and account-specific
fees need separate verification. [Constellation terms, §§1 and 7](https://www.constellation.com/bin/residential/GetContractVersionPDF?versionNum=4863156)

As a reproducible disclosure check, take an eligible 1,000 kWh account with
the April 2026 label, $4.23 monthly delivery and $0.056183/kWh delivery.
The energy charge is $88.50 and delivery rounds to $60.41. With a separately
reimbursed $0.25 public utility assessment on the eligible base, the comparison
amount is $149.16, or 14.9¢/kWh at EFL precision. With that same reimbursement
treatment, all nine printed averages reconcile using the contemporaneous
delivery prices. Rounded averages do not establish a customer's actual tax
base or their enrollment. [Texas PUC price disclosures, §25.475(g)](https://www.puc.texas.gov/agency/rulesnlaws/subrules/electric/25.475/25.475.pdf) · [Texas Comptroller guidance and worked billing example](https://comptroller.texas.gov/taxes/publications/96-1309.pdf)

## NEC Co-op Energy month-to-month supply

**Residential Plan Variable Price Product** is for an NEC retail member with
residential non-demand-metered Oncor service. The REP charges $7.50 per month
and a dated flat energy price. The contract renews monthly. The provider’s
history identifies the applicable **bill issue date**. Service dates and bill
dates can differ. Monthly billing follows the meter information supplied by
Oncor. Select the dated NEC supply price and apply the independently verified
Oncor tariff for the bill. [NEC residential terms, April 18, 2024](https://neccoopenergy.com/wp-content/uploads/2024/08/NEC-Co-op-Energy-Residential-IOU-Variable-Product-TOS-ENG-rev-4-18-24-added-Lubbock74.pdf) · [NEC Oncor dated history](https://neccoopenergy.com/residential-service/residential-historic-rates/oncor-area-historic-rates/)

The $15 refundable membership fee appears on the first bill. An established
member's recurring study excludes that deposit, veteran or active-duty
discounts, security lighting, nonstandard billing, special services and
account-specific credits or charges. Capital-credit retirements and PowerPerks
refunds can appear on actual bills. Export compensation requires a separate
executed contract. [NEC terms](https://neccoopenergy.com/terms-of-service-residential/) · [Capital credits](https://neccoopenergy.com/about/capital-credits/) · [PowerPerks](https://neccoopenergy.com/about/powerperks-adjustment/)

The ledger holds 23 itemized labels spanning February 2025 through November
19, 2026, including separate prices on October 1 and 3, 2025. On the first
two October days the REP charge was 8.41¢/kWh. Beginning October 3 it was
7.81¢/kWh. January 2025 has rounded examples, but the component EFL remains
unverified. Future issue dates beyond the review date remain open.
[October 1 EFL](https://neccoopenergy.com/wp-content/uploads/2025/10/EFL-10-1-25-RESIDENTIAL-Oncor.pdf) · [October 3 EFL](https://neccoopenergy.com/wp-content/uploads/2025/10/EFL-10-3-25-RESIDENTIAL-Oncor.pdf)

Nineteen source rows reproduce all three printed averages from their own
components. The remaining four rows have the following conflicts and are
excluded from the active NEC residential supply table. A reconciled
disclosure still requires independent confirmation of delivery and tax
treatment at the requested bill date.

| Issue date from | Usage (kWh) | Printed average (¢/kWh) | Recalculated average (¢/kWh) |
|---|---:|---:|---:|
| 2025-02-01 | 1,000 | 13.4 | 13.3 |
| 2026-01-01 | 2,000 | 13.2 | 14.1 |
| 2026-09-01 | 2,000 | 16.1 | 16.0 |
| 2026-10-01 | 500 | 18.8 | 18.0 |

The NEC EFL's quoted delivery line can also differ from the actual tariff.
For example the March 2025 label prints 5.008¢/kWh for delivery and Oncor’s
March summary gives 5.0029¢/kWh. A retailer’s comparison rate must never
replace the controlling Oncor rate or be added to it. [March 2025 EFL](https://neccoopenergy.com/wp-content/uploads/2025/02/EFL-3-1-25-RESIDENTIAL-Oncor.pdf) · [Oncor residential rate summary](https://www.oncor.com/content/dam/oncorwww/documents/partners/rep/Oncor%20Residential%20Rates%20Aug%202025.pdf.coredownload.pdf)
