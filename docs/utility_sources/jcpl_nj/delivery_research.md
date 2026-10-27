# JCP&L New Jersey — delivery evidence, 2025–2026

Research scope: ordinary RS residential and GS secondary; filed delivery/base and non-BGS riders only. Supply/TEC, Part II cycle allocation, taxes, DER and NEM eligibility have separate reviews. This note establishes source values, not an implemented or invoice-calibrated bill model.

## Originals and component packet

The official [JCP&L tariff index](https://www.firstenergycorp.com/customer_choice/new_jersey/new_jersey_tariffs.html) links all 15 downloaded Part III versions dated January/March/May/June/July/September/September 15/October/December 2025 and February/March/June/July 15/September/October 2026. These are archived/current filed tariff books with order, issued and effective footers, rather than proposed rates. The component's own footer can predate its containing book; the packet preserves both dates.

Private evidence:

- `.cache/jcpl_new_jersey/sources/delivery/delivery_records.json`: exact URL, SHA-256, bytes, physical page count and original/text paths for each book.
- `.cache/jcpl_new_jersey/sources/delivery/delivery_snapshots.json`: 15 snapshots with literal rates, physical page, printed leaf, revision, issued/effective footer and selected excerpt hash per component. No interpolation.
- `tariff_index.html` and `archive_links.json` in the same directory preserve discovery.
- Checked-in [delivery excerpts](delivery_excerpts/) preserve selected original page text; the packet maps every excerpt to its original physical page. Duplicate formatting can yield distinct raw text hashes for numerically identical leaves.

All prices below use the **published including-SUT column**. Customer/distribution charges also include CBT. Do not add tax gross-ups again. Do not add the components of an already-included aggregate SBC or RRC.

## Ordinary base schedules

Prices remain identical throughout all 15 archived snapshots, except the explicitly separate transmission line.

| Component | RS | GS secondary |
|---|---:|---:|
| Monthly customer | $4.27 | Single phase $4.65; three phase $16.69 |
| June–September energy | First600 kWh $.020182/kWh, excess $.079810 | First1000 kWh $.075288/kWh, excess $.006021 |
| October–May energy | All kWh $.033061 | First1000 kWh $.069662/kWh, excess $.006021 |
| Seasonal demand | None | June–September $9.00/kW; October–May $8.38/kW, **excess10kW** |
| Minimum demand | None | $4.08/kW **excess10kW**, current+preceding11-month maximum, not below Contract Demand |

RS printedleaf3 (physical4 in every downloaded book) covers separately metered residential structures, incidental nonresidential use alongside the residence and auxiliary residential purposes. Ordinary GS is general service at secondary voltages not included under RS, RT, RGT or GST (printed10). Separate water-heating, traffic-signal, worship, veterans, optional day/night and unusual-facility branches are outside the proposed ordinary scope.

GS printed11 defines the demand charge as the greater of seasonal current maximum on-peak demand charge and the minimum rate applied to the highest on/off-peak demand **created in the current and preceding eleven months**, not below Contract Demand. Printed10 explicitly makes all three kW prices apply only above10kW. A prior billed minimum is not a new actual demand observation.

GS printed12 states maximum15-minute integrated demand, nearest0.1kW. Crucially, if the Company determines demand will not exceed10kW and elects not to install a demand meter, demand is considered below10kW for billing. This is a utility account assignment, not an inference from the simulated load. A bounded executable no-meter scope should require that assignment, actual15-minute peak no greater than10kW, documented Contract Demand no greater than10kW, and actual demand history over the preceding eleven months no greater than10kW. Do not reset history when adding DER or reconnecting: the same leaf expressly retains previous eleven-month minimum obligations after disconnection/reconnection within12months. General metered GS, nearest0.1 ties, day/night timing and active demand minima require their own implementation review.

Base transmission schedule literals (BGS team owns complete supply-stack reconciliation): $.012709/kWh beforeMay1,2025; $.014877 fromMay1,2025; $.017244 fromJuly15,2026. The July15 change replaces RS printed3 and GS printed10 without changing customer/distribution prices or tier thresholds.

## Delivery rider ledger

| Component | Dated including-SUT value | Primary printed leaf |
|---|---|---|
| NGC, secondary loss-adjusted | $.000234/kWh throughSeptember2026; $.000312 fromOctober1,2026 |47|
| SBC aggregate | $.007700 throughSeptember2025; $.009239 October2025–September2026; $.008476 fromOctober1,2026 |50|
| RRC aggregate | $.004729/kWh, service rendered effectiveJanuary1,2025; all15books unchanged |62–63|
| ZEC | +$.004265 throughMay2025; zero June2025–February14,2026; reserved leaf effectiveFebruary15,2026; −$.004265 fromJune1,2026 |64|
| RP / ENJ | RP zero in2025 throughSeptember2026; renamed ENJ October1,2026, RS $.000135/kWh, GS $.000148 |66|
| LRAM | RS $.000546, GS $.000494, effectiveDecember30,2024; RS $.000971, GS $.001001 fromFebruary1,2026 |67|
| CRC | Not introduced inJanuary/March2025books or their schedule references; first adoptedMay1,2025 at $.000358/kWh; unchanged thereafter includingOctober2026reissue |72|
| EGCC residential only | −$30 **per billing month** July/August2025; +$10 September2025–February2026; balance asofMarch1,2026 rolled intoNGC, not an ongoing fixed$10 |65|

NGC uses the published **secondary, loss-adjusted, including-SUT** value. Underlying composite or excluding-SUT figures are different. Its stale St. Lawrence hydro credit narrative specifies June2020–May2021 and is not an extra2025/26credit.

SBC detail (includingSUT) reconciles independently to each published aggregate:

| Window | DSF | RAC | UNC | CombinedUSF+Lifeline | Sum |
|---|---:|---:|---:|---:|---:|
| January–September2025 | .003497 | .000859 | .000375 | .002969 | .007700 |
| October2025–September2026 | .003497 | .000859 | .000375 | .004508 | .009239 |
| October2026 | .003528 | .000859 | .000504 | .003585 | .008476 |

Detail leaves51/53/54/55 are separately pinned. RRC detail sums to .004729: SREC I/II .000007 + TREC .002095 + SuSI .000271 + communitysolar0 + EE&C1 .000991 + EE&C2 .001365. Do not independently charge these alongside the aggregate.

ZEC's March2026book does not publish a numeric replacement: it explicitly reserves formerleaf64 effectiveFebruary15,2026 and revises schedule references. Treat this as an adopted deletion, with its provenance retained; do not manufacture a missing numeric rate. CRC's pre-May absence is similarly explicit in complete72-page books and schedule references, followed by the adopted introduction leaf in the May73-page book.

## Coverage proposal and limits

Delivery evidence covers the full2025/2026 target chronology throughOctober2026, with component revision chains rather than last-known-rate extrapolation. Calendar execution still depends on independently verified supply windows, season/cycle rules and transition allocation. September15,2025 changes **no delivery numeric value** in this packet; BGS/TEC must be assessed separately. July15,2026 changes only the RS/GS transmission rate; all fixed, block and demand delivery prices remain unchanged. February15,2026 removes an already-zero ZEC leaf without changing another delivery price. No cross-date or seasonal allocation is inferred here.

A conservative initial scope can use whole accepted cycles within joint unchanged regimes, then add transition cycles only after PartII and supply review establish their allocation. An absence of a separately dated January2026book does not itself prove a change: December2025 and February2026 books retain direct leaf revision chains; the February2026 LRAM replacement identifies its exact effective date. The packet preserves these leaf clocks for review, and makes no automatic full-year simulation claim.

Independent verification recovered here consists of utility-published **SBC and RRC aggregate-to-component** arithmetic, not a whole-bill invoice calibration. No official independent ordinary RS/GS whole-bill benchmark was recovered in this bounded delivery pass; supply research separately preserves official price-to-compare evidence. Tariff-derived base examples are RS1000kWh winter $37.331 or summer $48.3032, GS730kWh winter single-phase $55.50326 (customer+distribution energy only, no riders/supply and no active demand charge). These are transparent arithmetic fixtures, not published bill totals.
