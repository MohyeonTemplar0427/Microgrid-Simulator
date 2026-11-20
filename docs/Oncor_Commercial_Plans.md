# Oncor small-commercial retail plans

## Ambit fixed-rate contracts

Ambit Texas, LLC (PUCT certificate 10117) published two commercial contracts for Oncor on May 10, 2025. Each label gives separate examples for a 7 kW non-demand-billed account and 11 kW and 16 kW demand-billed accounts. The two delivery choices in the simulator use the same supplier price. Each contract charges $9.99 per billing cycle when metered imports are **strictly below 1,250 kWh**, and has no other recurring REP base fee. At exactly 1,250 kWh the fee is zero. Actual delivery follows Oncor's dated tariff. [12-month EFL](https://mediaserver.ambitenergy.com//media/get/TSC1YTCNG12_555_283_1) · [24-month EFL](https://mediaserver.ambitenergy.com//media/get/TSC24MTCNG24_557_283_1)

| Ambit contract and printed EFL version | Supply ¢/kWh | Published ¢/kWh at 1,500 / 2,500 / 3,500 kWh | PDF SHA-256 |
|---|---:|---|---|
| TSC – 12 month Term, `TSC1YTCNG12_555_283_1250510` | 12.90 | 18.0 / 19.0 / 18.8 | `035d9baaba6852bdfbab58f1798a5f3b1468e8a433de187acbd5f49e6231dd9c` |
| TSC – 24 month Term, `TSC24MTCNG24_557_283_1250510` | 11.50 | 16.6 / 17.6 / 17.4 | `5ab403130010afde5cbf65c1abd2f49006644bb6bb2c767af5b0d7646963bfb9` |

The eligibility evidence is the enrolled EFL version, contract service start and end dates, a confirmed nonresidential small-commercial meter, Oncor's voltage and billing class, and recorded peak demand below 50 kW during the relevant 12 months. The modeled premise is outside an aggregation program. The Ambit terms print “kWh” for the peak threshold. The PUCT definition gives the dimension as kW and excludes an aggregation whose combined peak exceeds 50 kW. No annual kWh ceiling appears in these sources. New-customer service begins on the actual meter read. For an existing customer switching products, Ambit starts the new term within 24 hours of the request. Renewal can switch the customer to a variable rate. An original signed term can therefore extend into 2026. Its dates and amendments must be confirmed from the account documents. [Ambit commercial terms, pp. 1–2, version SCTOS110724](https://mediaserver.ambitenergy.com//media/get/TSCTermsOfService/en) · [PUCT §25.471(d)(11)](https://www.puc.texas.gov/agency/rulesnlaws/subrules/electric/25.471/25.471.pdf)

For the EFL benchmark, Ambit shows $6.87/month and $0.046202/kWh for the 7 kW example. It shows $32.43/month, $0.000223/kWh and $10.878180/kW for the 11 and 16 kW examples. Decimal rebilling matches all six rounded prices at the printed comparison loads. For instance, the 24-month 2,500 kWh example gives $287.50 for supply and $152.65 for delivery ($32.43 + 2,500 × $0.000223 + 11 × $10.878180), or 17.6¢/kWh. Demand on a customer bill comes from the applicable tariff, the meter and any required history. A 30% example load factor is solely a disclosure assumption.

The modeled subtotal covers an ordinary, ongoing contract with standard metering and actual monthly billing. Both labels exclude separately charged taxes and disallow export purchases. The terms also identify potential ERCOT charges, miscellaneous fees, local undergrounding charges, and average-billing or true-up arrangements. The EFL alone cannot establish a customer's resulting tax and government-fee bill. Verification is limited to the supplier and delivery subtotal for these products.

The source PDFs and extracted text are under `.cache/oncor_tx/commercial_fixed/`. The TOS has SHA-256 `5f07a7a0f47dbe0623a0a2d1f93f875e26cfa02043a08442bc39a23e2d97a661` and the PUCT rule has `32a44e82b5483ab952bbeb8de45a2f57197d61cb1e603ac58177cc2b8f41f194`.

## NEC variable contract

Reviewed November 19, 2026. These records cover an existing NEC Co-op Energy member on its month-to-month Small Commercial Service in Oncor territory. NEC is the retail supplier (PUCT certificate 10166X). The separate Oncor delivery schedule is Secondary Service at Less Than or Equal to 10 kW. The EFL heading specifies single-phase service below 10 kW while its next line allows exactly 10 kW. Restrict NEC eligibility to single-phase secondary accounts below 10 kW with confirmed Oncor classification. Negotiated addenda, three-phase service, exactly 10 kW, demand billing and export settlement require additional evidence. [Supplier commercial enrollment documents](https://neccoopenergy.com/commercial-service/commercial-prices/)

## Billing dates and amounts

The NEC archive identifies prices by **billing date**. The terms require the most recent applicable EFL, allow a new price each month and provide for bills issued after receipt of meter data. For a service cycle ending October 1, 2025, a bill issued October 2 and a bill issued October 3 can have different REP supply charges. A meter-read date, service month or contract enrollment date alone cannot determine the price. Limit November 2026 bill dates to the November 19 review date. [Historical prices](https://neccoopenergy.com/commercial-service/commercial-historic-rates/oncor-area-historic-rates/) · [NEC terms, pp. 1–2](https://neccoopenergy.com/wp-content/uploads/2024/08/NEC-Co-op-Energy-COM-IOU-Variable-Product-TOS-ENG-SPN-rev-4-18-24-added-Lubbock.pdf)

The modeled EFL subtotal adds NEC's $7.50 monthly charge, NEC's energy charge, the disclosed Oncor monthly charge, and the disclosed Oncor energy charge on imported kWh. NEC passes through actual TDU charges, which can change after an EFL is issued. A delivery figure in a label substantiates the published offer; actual metered service crossing a tariff boundary requires the utility tariff and allocation rule. A member may also have capital credits, a PowerPerks adjustment, special services, deferred amounts or an initial refundable $15 membership fee. Price comparisons here cover standard recurring charges before applicable sales tax and miscellaneous gross receipts tax reimbursement. [Commercial terms](https://neccoopenergy.com/wp-content/uploads/2024/08/NEC-Co-op-Energy-COM-IOU-Variable-Product-TOS-ENG-SPN-rev-4-18-24-added-Lubbock.pdf) · [PowerPerks](https://neccoopenergy.com/about/powerperks-adjustment/) · [PUCT §25.475](https://www.puc.texas.gov/agency/rulesnlaws/subrules/electric/25.475/25.475.pdf)

Taxable commercial electricity generally incurs Texas state sales tax of 6.25% plus local taxes appropriate to the service address. Statutory exemptions are account-specific. A cooperative participating in the competitive market owes the miscellaneous gross receipts tax when the location qualifies. Customer reimbursement depends on the REP's billing practice. All electric cooperatives owe the public utility gross receipts assessment. Applying a second assessment on top of the published EFL recurring charges needs customer-billing evidence. [Texas Comptroller electricity tax guide](https://comptroller.texas.gov/taxes/publications/96-1309.pdf) · [Comptroller gross receipts FAQ](https://comptroller.texas.gov/taxes/misc-gross-receipts/faq.php)

## Source ledger

Each row links the original English EFL. Dollar amounts in the implementation are exact conversions of its printed rates. Displayed average prices are supplier benchmarks in cents per kWh for 1,500, 2,500 and 3,500 kWh, respectively. All available 2025–October 2026 rows were also compared against the provider's separately displayed bill-date history. The November 2026 label was linked as current on the provider's plan page. January 2025 has only historical rounded comparison prices in the source set and stays blocked. December 2026 is unverified.

| Bill date | NEC ¢/kWh | Oncor $/month | Oncor ¢/kWh | Published comparison prices | EFL check |
|---|---:|---:|---:|---|---|
| [2025-02-01](https://neccoopenergy.com/wp-content/uploads/2025/01/EFL-2-1-25-SM-COMM-_Oncor.pdf) | 6.88 | 6.87 | 4.47 | 12.3 / 11.9 / 11.8 | Pass |
| [2025-03-01](https://neccoopenergy.com/wp-content/uploads/2025/02/EFL-3-1-25-SM-COMM-_Oncor.pdf) | 8.53 | 6.87 | 4.446 | 14 / 13.6 / 13.4 | Blocked. 1,500 kWh recomputes to 13.9¢, published 14.0¢. |
| [2025-04-01](https://neccoopenergy.com/wp-content/uploads/2025/03/EFL-4-1-25-SM-COMM-_Oncor.pdf) | 9.23 | 6.87 | 4.446 | 14.7 / 14.3 / 14.1 | Blocked. 1,500 kWh recomputes to 14.6¢, published 14.7¢. |
| [2025-05-01](https://neccoopenergy.com/wp-content/uploads/2025/04/EFL-5-1-25-SM-COMM-_Oncor.pdf) | 9.63 | 6.87 | 4.6202 | 15.2 / 14.8 / 14.7 | Pass |
| [2025-06-01](https://neccoopenergy.com/wp-content/uploads/2025/05/EFL-6-1-25-SM-COMM-_Oncor.pdf) | 10.22 | 6.87 | 4.6202 | 15.8 / 15.4 / 15.2 | Blocked. 3,500 kWh recomputes to 15.3¢, published 15.2¢. |
| [2025-07-01](https://neccoopenergy.com/wp-content/uploads/2025/06/EFL-7-1-25-SM-COMM-_Oncor.pdf) | 10.32 | 6.87 | 4.6202 | 15.9 / 15.5 / 15.3 | Blocked. 3,500 kWh recomputes to 15.4¢, published 15.3¢. |
| [2025-08-01](https://neccoopenergy.com/wp-content/uploads/2025/07/EFL-8-1-25-SM-COMM-_Oncor.pdf) | 10.2 | 6.87 | 4.6202 | 15.8 / 15.4 / 15.2 | Blocked. At 1,500 kWh the EFL and arithmetic give 15.8¢, the supplier history gives 15.5¢. |
| [2025-09-01](https://neccoopenergy.com/wp-content/uploads/2025/08/EFL-9-1-25-SM-COMM-_Oncor.pdf) | 9.83 | 6.87 | 4.5753 | 15.4 / 15 / 14.8 | Pass |
| [2025-10-01](https://neccoopenergy.com/wp-content/uploads/2025/10/EFL-10-1-25-SM-COMM-_Oncor.pdf) | 8.41 | 6.87 | 4.5753 | 13.9 / 13.6 / 13.4 | Pass |
| [2025-10-03](https://neccoopenergy.com/wp-content/uploads/2025/10/EFL-10-3-25-SM-COMM-_Oncor.pdf) | 7.81 | 6.87 | 4.5753 | 13.3 / 13 / 12.8 | Pass |
| [2025-11-01](https://neccoopenergy.com/wp-content/uploads/2025/10/EFL-11-1-25-SM-COMM-_Oncor.pdf) | 7.41 | 6.87 | 4.5753 | 12.9 / 12.6 / 12.4 | Pass |
| [2025-12-01](https://neccoopenergy.com/wp-content/uploads/2025/12/EFL-12-1-25-SM-COMM-_Oncor.pdf) | 6.91 | 6.87 | 4.6229 | 12.5 / 12.1 / 11.9 | Pass |
| [2026-01-01](https://neccoopenergy.com/wp-content/uploads/2025/12/EFL-1-1-26-SM-COMM-_Oncor.pdf) | 7.81 | 6.87 | 4.6229 | 13.4 / 13 / 12.8 | Pass |
| [2026-02-01](https://neccoopenergy.com/wp-content/uploads/2026/01/EFL-2-1-26-SM-COMM-_Oncor.pdf) | 7.99 | 6.87 | 4.5623 | 13.5 / 13.1 / 13 | Pass |
| [2026-03-01](https://neccoopenergy.com/wp-content/uploads/2026/02/EFL-3-1-26-SM-COMM-_Oncor.pdf) | 8.69 | 6.87 | 4.5874 | 14.2 / 13.9 / 13.7 | Pass |
| [2026-04-01](https://neccoopenergy.com/wp-content/uploads/2026/03/EFL-4-1-26-SM-COMM-_Oncor.pdf) | 8.77 | 6.87 | 4.5874 | 14.3 / 13.9 / 13.8 | Pass |
| [2026-05-01](https://neccoopenergy.com/wp-content/uploads/2026/04/EFL-5-1-26-SM-COMM-_Oncor.pdf) | 9.44 | 6.87 | 4.5874 | 15 / 14.6 / 14.4 | Pass |
| [2026-06-01](https://neccoopenergy.com/wp-content/uploads/2026/05/EFL-6-1-26-SM-COMM-_Oncor.pdf) | 9.74 | 6.70 | 4.9532 | 15.6 / 15.3 / 15.1 | Pass |
| [2026-07-01](https://neccoopenergy.com/wp-content/uploads/2026/06/EFL-7-1-26-SM-COMM-_Oncor.pdf) | 9.94 | 6.70 | 4.9532 | 15.8 / 15.5 / 15.3 | Pass |
| [2026-08-01](https://neccoopenergy.com/wp-content/uploads/2026/07/EFL-8-1-26-SM-COMM-_Oncor.pdf) | 10.08 | 6.70 | 5.1227 | 16.2 / 15.8 / 15.6 | Blocked. 1,500 kWh recomputes to 16.1¢, published 16.2¢. |
| [2026-09-01](https://neccoopenergy.com/wp-content/uploads/2026/08/EFL-9-1-26-SM-COMM-_Oncor.pdf) | 9.44 | 6.70 | 5.1227 | 15.5 / 15.1 / 15 | Pass |
| [2026-10-01](https://neccoopenergy.com/wp-content/uploads/2026/09/EFL-10-1-26-SM-COMM-_Oncor.pdf) | 8.78 | 6.70 | 5.3843 | 15.1 / 14.7 / 14.6 | Pass |
| [2026-11-01](https://neccoopenergy.com/wp-content/uploads/2026/10/EFL-11-1-26-SM-COMM-_Oncor.pdf) | 7.78 | 6.70 | 5.3843 | 14.1 / 13.7 / 13.6 | Pass |

Published precision affects the comparison near a rounding boundary. The six blocked EFLs retain their original component values here for review. No undisclosed supplier price was fitted to the rounded examples.

Two cents-rounded checks on 2,500 kWh give $339.00 on October 2, 2025 ($7.50 + $6.87 + 2,500 × ($0.0841 + $0.045753)) and $324.00 on October 3 ($7.50 + $6.87 + 2,500 × ($0.0781 + $0.045753)). These are recurring subtotals before account-specific items. Independent test calculations compare all enabled labels with all three published examples.

## Other commercial products reviewed

| Plan | Billing treatment |
|---|---|
| ENGIE Resources Fixed Price Product – Small Commercial, January 2026 | Blocked. Its stated $6.87/month and 15.6¢/kWh produce 16.1¢/kWh at 1,500 kWh when rounded. The label prints 16.5¢, references other recurring charges and excludes utility-related charges from the contract price. The missing component requires a verified contract. [ENGIE EFL](https://www.engieresources.com/wp-content/uploads/2025/10/Oncor-EFL-Fixed-Small-Comm-1.pdf) |
| Champion Energy Business Savings Champ – 24, November 2026 | The label states 9.8¢/kWh plus TDU pass-through. Its comparison prices assume a demand meter and a 30% load factor. Eligibility and independent pricing for this specific below-10-kW scope remain open. [Champion EFL](https://docs.championenergyservices.com/ExternalDocs?language=en&planName=27%7C2%7CLO%7C0%7C0.098000%7C24%7CBusiness+Savings+Champ+-+24&state=TX) |
| TXU Energy Small Non-Residential Provider of Last Resort | A separate emergency-service contract uses a formula with nonbypassable charges, an LSP customer charge and a market-linked energy charge. It applies to designated POLR customers. [PUCT filing](https://interchange.puc.texas.gov/Documents/56035_164_1476099.PDF) |
| XOOM BizLock 36 and BizSimpleClean 12 | The provider's public PDF addresses returned October 4, 2026 editions when downloaded, although indexed versions at the same addresses showed September 1 and December 15, 2025. The retained October labels postdate the start of the last completed calendar month in this review. Neither a historical contract version nor an earlier effective date can be assigned from the URL. [BizLock PDF](https://texas.xoomenergy.com/defl/X2F00131268933A.pdf) · [BizSimpleClean PDF](https://texas.xoomenergy.com/defl/X2F00122786745B.pdf) |

Raw PDF bytes and the retrieved historic-price HTML are kept in the ignored `.cache/oncor_tx/commercial/` evidence directory. The following SHA-256 fingerprints are for the source PDFs.

| Bill date | SHA-256 |
|---|---|
| 2025-02-01 | `b9fa282c0e1b8fcec45f2abf08c9d3626f7c01f63760a47d6889d15e53f3431a` |
| 2025-03-01 | `c32f51664ec1c68b15ac7aed2e881761067df510c5b9b6789e1bb62ac30b558e` |
| 2025-04-01 | `a0e01087f9a5edc21829dc42ef460447cff5f3c8619e12a140baec82d5d812bf` |
| 2025-05-01 | `9e51d0cb20c302d92a2e2c4ed9cb407f1809ddf3022f6b79daee0d143fbc7254` |
| 2025-06-01 | `f41f40de2162057835642708b97a809cfbdf93dc11b3142380f5d2cda84e0bdd` |
| 2025-07-01 | `2d296c3ac2112de98f3e9e4e73e163ca65ab444efb4252ef0431235d92bacfde` |
| 2025-08-01 | `0bbf1838f7a53ec1970c7fe4efbfcdd1a99f4b39b8d293f7e9e6703045009399` |
| 2025-09-01 | `e8ce66756585aa3acc35ccd77b7a2312435e560051b31c5aa760ae41d8b159df` |
| 2025-10-01 | `b43aeeb4705c13d0f20eb38e37cdf9fb770c6fababa6af9479d09dfb5f2189ee` |
| 2025-10-03 | `9066be457c2352e4fe27a83066db28b47d0a2f9e52dad830fb540e601e782990` |
| 2025-11-01 | `5a4c7ceaa1072bee0c836a10ad0b81f4f6dfedd21f61a8c635b45bb7b3e42ecd` |
| 2025-12-01 | `d84a6d0861c00a015142d78f1cda4948ed693ecb8a7b08a74a512dbab893b1ed` |
| 2026-01-01 | `15428f48302b9f5bdbfacb73f601ef211b11e454fe2e265bad02c2970cb3f91f` |
| 2026-02-01 | `e6fce3bd25c84d22c286d90c970682a66c9ed9edb48f9719b71fe5510c86207a` |
| 2026-03-01 | `e0b8d9f456195555a49cee2934c7ba9fcfe8c147ebfe26b6cdeba8d9800b5f4c` |
| 2026-04-01 | `83e4cc3a5bde8a6de550bdc7bfe00fe8d0478317565348801dd301ede1b92cef` |
| 2026-05-01 | `5a6732c570e9ffb2e41d733f53a0e12461b51ccc260f5f50233ff94b8d68f618` |
| 2026-06-01 | `844ece44c35b941e058684c0f2eb6593b2eb5ebe132a89e3ec92ee7a32d21ef7` |
| 2026-07-01 | `28d6322b0af08eb28ced8473ede9d58316e33367621ffbe002e4214ee671caba` |
| 2026-08-01 | `3255903db5a20664cb51f11e22195ab96bff2c378abfd46acc8bea4a79d32fc8` |
| 2026-09-01 | `68d663f3c61d5ba919136d3e6bde33463905b3af4e6c92308a2fc3e95bbc7534` |
| 2026-10-01 | `40b43face6fe5ac981af9852d4000bd1f3c8bcf46bb54ca4c2f00955c1fdcdd5` |
| 2026-11-01 | `1c0d0e5c56f91a6a9f475d529736272ac4d33169e46b4f5854581ff95e10e99c` |
