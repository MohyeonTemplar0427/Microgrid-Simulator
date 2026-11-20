# Kingsport Power Tennessee

Kingsport Power Company, doing business as AEP Appalachian Power, supplies both electricity and distribution service for these accounts in the City of Kingsport. The simulator supports ordinary **RS 015 residential** and **metered SGS 231/232 small commercial** for complete January 2025 through October 2026 calendar service cycles. PJM AEP is the transmission zone. Each study supplies its own account evidence, tax location and, when used, wholesale pricing location. [Source ledger](utility_sources/kingsport_tn/sources.json) · [FERC transmission-zone finding, paragraph 8](https://ferc.gov/sites/default/files/2023-04/E-3-EL22-34-001.pdf)

## Account and billing rules

| Schedule | Monthly distribution charge and minimum | Distribution energy | Eligibility |
|---|---:|---|---|
| RS 015 | $16.43 | $0.00325/kWh | One ordinary residential meter for domestic use, single-phase secondary, without controlled water heating, employee pricing or time-of-use service. |
| SGS 231/232 | $22.03 | $0.03225/kWh for the first 600 kWh and $0.02076/kWh above 600 | The utility confirms a normal maximum below 10 kW. Code 231 covers low-use service. Code 232 has a demand meter and is billed on kWh. Code 233 uses estimated unmetered quantities and is excluded. |

The minimum applies to base distribution. The fixed service charge meets it even at zero usage. The reliability charge and applicable taxes still apply. The study accepts one ordinary 120/240 V secondary meter, full monthly charges, actual metered usage and no special facilities or optional pricing. An independent utility demand value and classification reference are required for SGS. Study limits are 25 kW residential and 9.999 kW commercial for native load and imports. [Filed tariff 3, RS and SGS](https://www.appalachianpower.com/lib/docs/ratesandtariffs/Tennessee/KGPT_Tariff-Nov_1_2026_FPPAR_Update.pdf) · [Utility explanation of codes, CPAD 2-005](https://tpucdockets.tn.gov/archive/filings/2016/1600001cm.pdf)

| Fuel and purchased power, by bill issue date | RS $/kWh | SGS $/kWh, both blocks |
|---|---:|---:|
| November 1, 2024 through October 31, 2025 | 0.10219 | 0.08279 |
| November 1, 2025 through October 31, 2026 | 0.09504 | 0.07699 |
| November 1–19, 2026 within the reviewed billing scope | 0.10617 | 0.08601 |

| Targeted reliability and major storm charge, by service dates | RS $/month | SGS $/month |
|---|---:|---:|
| January–August 2025 | 3.85 | 6.87 |
| September 2025–June 2026 | 6.84 | 12.20 |
| July–October 2026 | 7.81 | 13.94 |

The purchased-power adjustment applies to bills rendered. The reliability rider applies to service rendered. An October 2025 service cycle issued October 31 therefore uses the earlier purchased-power rate. The same service issued November 1 uses the new purchased-power rate and keeps October’s reliability charge. The utility’s final 2026 reliability filing changed the proposed September effective date to July 1. The account must identify its actual bill date and the corresponding billing month. The study accepts a final-day bill or a documented bill in the immediately following month through November 19, 2026. The hypothetical default assumes a final-day bill. [2024 notice](https://tpucdockets.tn.gov/archive/filings/2016/1600001gb.pdf) · [Purchased-power comparison and filed sheets, pp. 18 and 59–66](https://tpucdockets.tn.gov/archive/filings/2016/1600001gc.pdf) · [2025 reliability filing](https://tpucdockets.tn.gov/archive/filings/2025/2500022y.pdf) · [Corrected 2026 reliability filing](https://tpucdockets.tn.gov/filings/2026/2600015u.pdf)

The administrative rider adds $0.00011/kWh. The federal tax adjustment on base distribution is 0%. Paying in full within 15 days earns a 1.5% discount on base charges plus riders. The account can also select the undiscounted bill. The city franchise fee is 5% on the resulting amount within the supported usage range. Tennessee exempts domestic residential electricity. Ordinary private SGS pays 7% state sales tax after the franchise fee. The state excludes electricity from local-option sales tax. This scope excludes franchise and commercial tax exemptions, manufacturing rates, delinquency charges and localities outside the city. [Utility residential calculator](https://www.appalachianpower.com/lib/docs/ratesandtariffs/Tennessee/KingsportPowerCompany-ResidentialBillCalculator-Nov_1_2026.xlsx) · [Utility commercial calculator](https://www.appalachianpower.com/lib/docs/ratesandtariffs/Tennessee/KingsportPowerCompany-CommercialIndustrialBillCalculator-Nov_1_2026.xlsm) · [City ordinance adoption](https://www.kingsporttn.gov/wp-content/uploads/default/3_15_16_BMA_Minutes.pdf) · [Tennessee tax manual](https://www.tn.gov/content/dam/tn/revenue/documents/tax_manuals/august-2026/sales-use-tax-manual.pdf)

## Solar and unsupported operation

An existing solar account must have final utility permission for the exact installation under the NMS rider, including the reviewed annual solar generation and historical annual consumption. Projected annual kWh must fit the reviewed historical consumption. This implementation covers solar-only systems up to 10 kW AC, zero power export at every interval, zero opening kWh or monetary credits, and previously paid inspection and installation charges. Under NMS the ordinary schedule supplies the monthly charges. With these zero-export and zero-bank conditions its billed energy equals imported kWh. Storage eligibility, export credit carry and year-end net metering settlement are outside the verified implementation. This scope excludes the larger residential EV allowance, special contracts, partial service cycles and November–December 2026 service. [Tennessee NMS package](https://www.appalachianpower.com/lib/docs/business/builders/TNNetMeteringPackage2024.pdf)

## Independent bill comparisons

The utility’s regulatory exhibits compare distribution, FPPAR and TRP&MS charges and omit the prompt-payment discount. Their reported figures also reconcile before the administrative rider, city franchise fee and Tennessee commercial tax. The commercial calculator rounds the 600-kWh blocks separately. This explains the fraction-of-a-cent difference in the 750 kWh comparisons. The 2026 exhibit repeats stale 2025 dates in its column headings. The final approved tariff dates govern the periods below. [2025 Exhibit 3, PDF p. 8](https://tpucdockets.tn.gov/archive/filings/2025/2500022b.pdf) · [2026 Exhibit 3, PDF p. 79](https://tpucdockets.tn.gov/filings/2026/2600015a.pdf)

| Representative final-day bill | Published RS 1,000 kWh comparison | Modeled RS city bill, prompt payment¹ | Published SGS 750 kWh comparison | Modeled SGS city bill, prompt payment¹ |
|---|---:|---:|---:|---:|
| March 2025 | $125.72 | $130.14 | $113.45 | $125.65 |
| September 2025 | $128.71 | $133.23 | $118.78 | $131.55 |
| November 2025 | $121.56 | $125.84 | $114.43 | $126.73 |
| July 2026 | $122.53 | $126.84 | $116.17 | $128.66 |

¹ Unrounded complete tariff arithmetic displayed to the nearest cent. The shared backend also preserves each component rounded half-up, its component sum and the unrounded total. The utility’s November 2026 residential examples of $131.76 at 1,000 kWh and $239.65 at 2,000 kWh both reconcile after prompt payment and before this study’s city fee. The supported October-service, November-issued case exercises that published adjustment. [Utility example bills](https://www.appalachianpower.com/company/about/rates/tn)

The focused checks cover every service month for both plans, independent Decimal rebills, between-month bill issue dates, the 600-kWh block, exact numeric and symbolic parity, both payment treatments, minimums, DST, missing and duplicate intervals, classification, solar eligibility and rejection of storage or credits. The batch report records frozen checks and electrical evidence. Source hashes, official locators and retrieval gaps are in the [source ledger](utility_sources/kingsport_tn/sources.json). The older utility book is still indexed under the official URL. Direct retrieval returned HTTP 404. The regulator’s dated exhibits corroborate the historical charges, and the raw regulator filings and current utility workbooks are archived under `.cache/pjm_fourth5/kingsport_tn/sources/`.
