# Delmarva Maryland supply research

Reviewed October 26, 2026. Maryland only; Delaware electricity/gas, wholesale
PJM prices and export settlement are separate and excluded. Supply scope is
Schedule R residential and Schedule SGS-S Type I SOS. Account classification,
jurisdiction and supplier assignment must be independently confirmed.

## Verified energy and supply administrative charges

All values below are dollars/kWh. Generation total is energy plus supply
administration; do not add admin a second time. PCA and transmission are
separate. Earlier future-period admin projections are superseded by final
filed period tables.

| Usage window | R energy | R admin | R generation total | SGS-S energy | SGS-S admin | SGS-S generation total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Jan 2025 | .095756 | .003852 | .099608 | .095756 | .004067 | .099823 |
| Feb-May 2025 | .095756 | .004813 | .100569 | .095756 | .005267 | .101023 |
| Jun-Sep 2025 | .094490 | .004834 | .099324 | .094633 | .003878 | .098511 |
| Oct 2025-Jan 2026 | .095462 | .004712 | .100174 | .093642 | .004041 | .097683 |
| Feb-May 2026 | .095462 | .004429 | .099891 | .093642 | .004719 | .098361 |
| Jun-Sep 2026 | .098203 | .004617 | .102820 | .098630 | .003944 | .102574 |
| Oct 2026 | .106302 | .004267 | .110569 | .103693 | .003784 | .107477 |

Decisive physical PDF pages:

- `book_2024_dec` R48/SGS55: January 2025 prior-period rates.
- `book_2025_feb1` R48/SGS55: supply admin changes explicitly effective
  February 1, 2025, filed January 23 with January 22 approval. Do not confuse
  a later shared-page February 3 revision with this supply effective date.
- `book_2025_jun_clean` R48/SGS55: actual May 22 clean filing, effective
  June 1 with May 21 approval. The separately recovered archive file named
  `book_2025_jun` explicitly marks these pages **Proposed** and is rejected.
- `book_2025_sep17` R48/SGS55: October 2025 final strips, with September 10
  approval. `book_2025_dec` independently retains those historical rates.
- `book_2026_jun` R48/SGS55: final February-May 2026 prior-period columns
  and June-September rates, filed May 29 with May 27 approval.
- `book_current` R48/SGS56: final October 2026 administration, filed
  September 28 with September 23 approval.

## Transmission, including SGS-S blocks

| Usage window | R energy $/kWh | SGS-S first 3,500 kWh $/kWh | SGS-S demand above 20 kW $/kW |
| --- | ---: | ---: | ---: |
| Jan 1-Aug 26, 2025 | .019456 | .019838 | 6.092451 |
| Aug 27, 2025-Aug 31, 2026 | .020699 | .018466 | 5.671116 |
| Sep 1-Oct 31, 2026 | .021361 | .018205 | 5.591050 |

SGS-S transmission has no charge for the first 20 kW, and no energy charge
above 3,500 kWh. These are transmission rules, not an assertion that SGS-S
has no delivery demand charge. SGS-S delivery demand is real and separately
verified by the delivery stream. A bounded initial study may require explicit
utility-assigned paragraph E3 estimated-demand method, monthly import no more
than 3,500 kWh and study peak below 20 kW. E3 billing demand is imported monthly
kWh divided by 175 hours; E3 is a rule identifier, not a fixed 3-kW assignment.
Never infer the utility's method assignment from optimization.

`book_2025_sep4`, physical R48/SGS55, explicitly makes the 2025 transmission
change effective **August 27**, with the corresponding Commission approval.
A flat old/new rate for the entire August calendar cycle is unsupported without
verified allocation. `book_2026_aug`, physical R48/SGS55, establishes September
1, 2026. Preserve these dates, not a neighboring utility's transmission clock.

The Delmarva CSEG originals explicitly say GRT is embedded in applicable
transmission/distribution rates. Do not copy Pepco's separate 2.0408% adder.
Tax interpretation and billing rules remain in the tax research receipt.

## Verified monthly retail PCA

All values are signed dollars/kWh. The entries below are positive retail
charges; corresponding parenthesized CSEG credit entries have the opposite
sign. Text extraction reorders some first-two-month cells: read the rendered
column positions rather than assuming flat token order.

```python
# Ordered January-September 2025:
PCA_R_2025 = [.0054462, .0050416, .0046636, .0045395, .0035164,
              .0045270, .0055343, .0075546, .0084515]
PCA_SGS_I_2025 = [.0018674, .0006043, .0013890, .0018005, .0010042,
                  .0008805, .0013228, .0028163, .0037256]
# Ordered May-October 2026:
PCA_R_2026_MAY_OCT = [.0066884, .0070129, .0075479, .0094853, .0102448, .0101653]
PCA_SGS_I_2026_MAY_OCT = [.0025753, .0025516, .0028041, .0037427, .0043628, .0043337]
```

Primary dated component originals, preserved by the delivery stream:

- `cseg_may2025.pdf`: physical R1/SGS2, December 2024-May 2025 columns.
- `cseg_sep2025.pdf`: physical R1/SGS2, April-September 2025 columns.
- `cseg_oct2026.pdf`: physical R1/SGS4, May-October 2026 columns.

The standalone `pca_current.pdf` visually corroborates all June-October 2026
PCA entries. Its later November 2026-May 2027 cells are blank. A targeted
history pass also found the July 2025 standalone chart, corroborating June
and July 2025, but it cannot fill its later blank columns.

**Gap: October 2025-April 2026 monthly PCA remains unverified.** Generation
and admin strips do not fill PCA. No full-year 2025 or 2026 bill coverage is
established. Source recovery for another component cannot waive this gap.

## Service rules and executable scope boundaries

Current full tariff physical 161-162 (printed leaves 120-121), Rider SOS:
R is residential SOS; SGS-S is Type I except utility assignments to Type II.
Type II SGS-S triggers are measured demand at least 25 kW in one of twelve
billing months, more than 6,000 kWh in two consecutive winter billing months
(October-May), or more than 7,500 kWh in one summer month. SOS-type changes
occur annually with June billing. Tax research owns detailed service and
estimated-demand eligibility; no historical assignment is inferred here.

PCA is a separate monthly item on billed kWh. True-ups occur at least with
**June, October and February billing months**, distinct from Pepco's November
true-up. Supply administration typically changes February, June and October.
The final energy-strip usage windows are the explicit dates above. Complete
calendar cycles do not erase intramonth tariff changes.

The supply evidence intersects other required components only after their own
checks: July 2025 MES changes July 2, and August 2025 transmission changes
August 27, so those crossing cycles are rejected absent allocation proof.
The tax stream recovered the actual filed MES $0.000151 rate effective July 2,
2025, allowing later complete cycles including May-June 2026 while retaining
the unresolved distinction from the simple statutory assessment cap. The July
6, 2026 archived book explicitly makes $0.000150 effective July 1, resolving
July 2026's boundary. No residential RRC/refund or
ordinary GS sales-tax value is invented; incomplete subtotals must remain
visibly incomplete.

## Preserved originals and receipts

`.cache/delmarva_md/sources/supply/supply_records.json` pins 12 exact original
URLs, SHA-256s, full-text hashes, selected physical pages and excerpt hashes.
The current outlined PCA table has a hashed PNG render and labeled visual
transcription. `delivery_component_refs.json` pins the three original component
PDF hashes and pages without changing their owner files.
`history_gap_receipt.json` records the bounded index/archive and targeted-gap
pass, excluded proposed source and missing dates. A source not recovered by
these routes is not proof no such historical document exists.

- [book_2024_dec](https://azure-na-assets.contentstack.com/v3/assets/blt47b6e332b18fb457/blt9a557615138ff16d/677315212fdcc317970bef4b/2024-12-11_MASTER_MD_DPL_Tariff_Book.pdf); original SHA-256 `b8980e2be4af0f0a8fd169e0e9006057c73661ed6a05a723869fd5941a66c398`.
- [book_2025_feb1](https://azure-na-assets.contentstack.com/v3/assets/blt47b6e332b18fb457/blt710b9f1dbdaa74b9/67a4f005d7d66ba3bfc3bdc0/DPL_CURRENT_CLEAN_GREEN_RIDER_eff_020125.pdf); original SHA-256 `d1fecd4311a64476231935fe54a577b0705082d3f792fd945fd07382d284f705`.
- [book_2025_jun_clean](https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/bltefc1a0bec7ba2be7/6836366f66e14842151acf57/MD_SOS_Type_II_generation_rates_and_Admin_Cha_.pdf?branch=prod_alias); original SHA-256 `9aa135835eb28c37049788263ba8ba30aaa49ef3207ce96def900b0f62b18cf2`.
- [book_2025_sep4](https://azure-na-assets.contentstack.com/v3/assets/blt47b6e332b18fb457/blt5cef29ea6692979d/68cc2f0c2755d52c3548c849/2025-09-04_MASTER_MD_DPL_Tariff_Book.pdf); original SHA-256 `ef1f1d5144609796c1384d1849bc8c45e6197e25a38ed327ccbc6e35ef4c51ee`.
- [book_2025_sep17](https://azure-na-assets.contentstack.com/v3/assets/blt47b6e332b18fb457/blt99ca5e1b176e4c46/6984dd52c529c6c138cf0f12/2025-09-17_MASTER_MD_DPL_Tariff_Book.pdf); original SHA-256 `5bcad77cbbd8425750001cbe7de3d2b8ade1f967870ea810f60df649960c4e5c`.
- [book_2026_jun](https://azure-na-assets.contentstack.com/v3/assets/blt47b6e332b18fb457/blt5cf7f8ee78966506/6a551e1149eff00ac082bcc7/DPL_MD_CURRENT_CLEAN_SOS_Filing_eff_0601_.pdf); original SHA-256 `b35d95e3c9bf73eae8d33dd7ac5b805dd0c9bd3e08c42f1b8dd17ffa9da8ace8`.
- [book_2026_aug](https://azure-na-assets.contentstack.com/v3/assets/blt47b6e332b18fb457/blt3f938d0d9a94244e/6a8ddbe4c8beba22bf6a393f/2026-08-20_MASTER_DPL_MD_Tariff_Book.pdf); original SHA-256 `f7102a1f5db3951a8ae8b3acf7cb9dbb663edf3fdf67907b596dd9d24e1b980a`.
- [book_current](https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/bltefc1a0bec7ba2be7/6abbd8bb794a17e7adb9629e/9226_9056_9064_DPL_MD_CURRENT_CLEAN_Admin_Charge_RTOUND_eff_100126.pdf?branch=prod_alias); original SHA-256 `d7165fb9e1efbdd40ddd76cfbc4d6cdc5eb3653db040e27679bc88a81cde9b30`.
- [pca_current](https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt1b4ac9864f417a73/6abdb850794a17321fb97b45/DPL_MD_PCA_-_102026_.pdf?branch=prod_alias); original SHA-256 `1df4d4ad6f7897f8dd3cb8ba24e1208d2f8cedb28d8240f4407493e8f7d37d95`.

Public source discovery used Delmarva's `eudapi.delmarva.com/content-api`
endpoint `/api/content/products/other/pages`, environment `live`, verified
current page `/my-account/my-dashboard/rates-tariffs/maryland/current-tariffs`
and plural archive `/my-account/my-dashboard/rates-tariffs/maryland/tariff-archives`.
The guessed singular archive and guessed PCA path returned 404 and were stopped;
actual links were followed from the Maryland index. No proposed, Delaware,
wholesale or neighboring utility rate was substituted.
