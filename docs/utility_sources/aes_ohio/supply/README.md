# AES Ohio supply and transmission source ledger

Researched November 2, 2026 for ordinary D17 non-heating, non-PIPP residential and D19 secondary single-phase SSO accounts. Generation supplier is AES Ohio under G10. Retail transmission is separately charged under T08. No wholesale PJM settlement, competitive supplier, community aggregation, export settlement, TCRR opt-out/NSPL opt-in, mercantile exemption, PIPP customer discount or minimum-load service agreement is included.

`rates.json` records exact tariff values as decimal strings and distinguishes service-rendered G10 from bills-rendered T08. `sources.json` pins original URLs, cache paths and SHA-256 hashes. Originals and detailed extraction/rendering evidence are private under `.cache/aes_ohio/sources/supply/`. The tariff page's pre-filing/proposed distribution bundle was not used as adopted supply evidence.

## Supply chronology

| Service dates | G10 revision | D17 non-PIPP and D19 SSO ($/kWh) | Evidence |
| --- | --- | --- | --- |
| June 1, 2024-May 31, 2025 | 25th | 0.0857985 | Adopted original PDF |
| June 1, 2025-May 31, 2026 | 26th | 0.0945004 | Official dated calculators and reproducible cached adopted-regulator page 1/page 3 text. Original PDF remains unavailable. |
| June 1, 2026-May 31, 2027 | 27th | 0.1085598 | Adopted original PDF; implementation request ends in 2026 |

The embedded alternative-energy component is already part of G10: the 25th-revision PDF prints $0.0000018/kWh, the cached 26th prints $0.0000562/kWh, and the 27th prints $0.0001986/kWh. Do not add it again. The 2024 calculator's mercantile difference implies a different embedded amount, so it must not substitute for the adopted PDF or extend this ordinary-account work to mercantile exemptions. G10 is energy-only and bypassable. It requires distribution D17-D25 as applicable and non-bypassable T08. Default service covers customers without a selected alternate supplier, including the listed aggregation opt-out/default conditions.

The G10 26th-revision gap is an original-document preservation gap, not an inferred price. The official June 2025 calculators and October/November 2026 calculators contain the exact $0.0945004/kWh rate. Reproducible search captures of the regulator's formerly published G10 page 1 and page 3 retain the 26th revision, order 25-0439-EL-RDR dated May 28, 2025, issue May 30, effective/service-rendered June 1, annual June-May term, applicability and embedded component. Direct retrieval of the same mutable regulator book now returns the 2026 27th revision. A bounded versioned-regulator archive check also returned the 27th. This evidence must remain labeled as calculator plus cached official text and never counted as an adopted original PDF. A policy requiring original PDFs for every pricing window would exclude June 2025-May 2026.

## Transmission chronology

| Bills rendered | T08 revision | D17 $/kWh | D19 $/all billing kW | D19 $/kWh | D19 low-load substitute $/kWh |
| --- | --- | --- | --- | --- | --- |
| September 1, 2024-May 31, 2025 | 24th | 0.0101098 | 2.8762278 | 0.0005432 | 0.0357205 |
| June 1-August 31, 2025 | 25th | 0.0150056 | 3.9517849 | 0.0008294 | 0.0459411 |
| September 1, 2025-May 31, 2026 | 26th | 0.0150056 | 3.9517849 | 0.0008294 | 0.0549634 |
| June 1, 2026-May 31, 2027 | 27th | 0.0179223 | 4.3554372 | 0.0007632 | 0.1200902 |

All four needed T08 revisions are preserved as original PDFs. The older June 2024 23rd revision is retained for provenance, but its commercial rates were superseded September 1, 2024 and cannot price January-May 2025. The September 2025 change matters to the low-load substitute even though ordinary transmission rates stayed unchanged.

T08 delegates demand determination to the applicable distribution sheet. All ordinary secondary billing kW are charged, including the first 5kW. From June 2025, primary-and-above customers use NSPL, while secondary customers use it only if they opt in. June 2026 T08 adds a greater-of contractual minimum-load clause for service agreements; those accounts are outside ordinary scope. The T08 substitute replaces both demand and energy when D19 low-load treatment applies. It is not independently minimized. No interim-cent rounding or strict equality tie-break is specified in the T08 tariff text.

## Independent calculator evidence

The [energy-supply page](https://www.aes-ohio.com/energy-supply) still linked the June 2025 calculators at retrieval. Dedicated [residential](https://www.aes-ohio.com/residential-bill-calculator) and [commercial](https://www.aes-ohio.com/commercial-bill-calculator) pages linked November 2026 residential and October 2026 commercial versions. The October 2026 residential snapshot was also preserved. Both 2025 and 2026 versions are kept, so a page update cannot silently change benchmark identity.

`calculator_evidence.json` records each original's hash, visible/hidden sheets, actual default dates, input values, component labels and cached bill outputs. `calculator_rate_vectors.json` contains exact source cell coordinates, date headers, numeric values and formulas for Residential/Secondary rate-table rows. Full expanded formula traces and raw OpenXML extraction are private. The files contain no VBA parts. Inspection never ran macros, changed inputs or saved the workbooks. Cached outputs prove the published sample, not a new recalculation or Excel-native behavior.

For an independent acceptance calculation, derive billed kWh and the tariff's billed demand independently, then use the original published rate vectors, not production billing tables. On a complete, single-rate, exactly 30-day bill, compute each component with Decimal arithmetic and separately reconcile customer, distribution, each rider, T08, excise and G10, then the delivery/supply totals. Use samples away from half-cent and low-load selector thresholds. The visible calculator rounds component amounts to cents; production raw/optimizer arithmetic should be compared with the raw independent calculation separately from cent-rounded invoice examples. Do not turn PTC into the total bill or treat a full bill total alone as component reconciliation.

The official commercial sample for October 1-31, 2026 (30 elapsed days) is 1,000kWh, billed demand 5kW, single phase, AES Ohio supply: customer $19.00, distribution $39.02, T08 $22.54, supply $108.56, delivery $109.01, total $217.57. The June 1-30, 2025 residential cached sample uses 29 elapsed days, 1,000kWh: customer $9.75, distribution $28.61, T08 $15.01, supply $94.50, delivery $76.92, total $171.42. These are cached published samples with their original date conventions; do not relabel them as recalculated calendar-month studies.

### Material calculator conventions and differences

- `Bill Calculator!L14` builds the D19+T08 normal variable-charge test, excluding customer and percentage riders. `L15` computes the combined cap times total kWh. `L16` selects low-load only when the rounded cap is strictly smaller than the rounded normal test. The tariff itself does not state this intermediate rounding/tie convention.
- D19 `I19:I21` select ordinary periods and `I22` selects substituted low-load periods. T08 `I51:I54` select ordinary and `I55` selects low-load periods. `L159`, `L161`, and `L163` apply D36/D29/D41 percentages to customer plus the selected D19 component, excluding transmission. First-5/remaining-demand rows are accounting splits, with the same current ordinary rates.
- September 2025 calculator cells retain D19 low-load $0.06464197 and total $0.11960537/kWh; the adopted D19 sheet prints $0.0646420 and $0.1196054. Preserve tariff precision in billing. The difference is $0.00000003/kWh and can affect a near-threshold comparison or cent at high usage.
- The calculator normalizer is 1 for 25-35 elapsed days and uses fixed 2,000/15,000kWh excise thresholds there. This differs from the reviewed statutory per-day thresholds for non-30-day cycles. Use exactly 30-day inputs for tax-tier calculator acceptance and apply the separately reviewed statutory rule to other cycles. Do not inherit the spreadsheet's limitation.
- Rate-table row 8 contains meter-read boundaries, sometimes the last business day before the legal effective date. Bill-rendered and service-rendered lookups use different header/formula paths. Those raw cells do not override tariff effective dates and do not establish a November 2025 mixed-cycle allocation rule. Rate-change-cycle support must be separately evidenced or rejected.
- The calculator takes billed demand as input; it does not independently prove 30-minute peak derivation, historical demand minima, timestamps/DST, dispatch/credit reconciliation or electrical replay.

## Preserved limitations

The G10 26th original PDF remains unrecovered. November 2025 mixed-cycle allocation is not established by these supply sources. The official calculator's narrow non-30-day excise behavior and September 2025 extra decimal precision are identified above. No production code, tests, simulation matrices, GUI, browser acceptance, commit, push or promotion was performed by this source-research scope.
