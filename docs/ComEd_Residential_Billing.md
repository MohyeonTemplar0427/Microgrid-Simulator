# ComEd residential billing — initial backend, October 12, 2026

## Supported scope

`src/billing/comed_residential.py` calculates an **itemized subtotal** for
residential BES (default fixed-price supply) and BESH (Hourly Pricing), each
with standard delivery for four account classes:

- Single family without electric space heat
- Multi family without electric space heat
- Single family with electric space heat
- Multi family with electric space heat

These are account classifications to confirm from ComEd, not deductions from
building size or a heat-pump checkbox. The account must have one ordinary
residential meter, ComEd supply, standard delivery, and no special contracts,
means-tested discounts, or generation/export settlement.

Verified composite coverage is **September and October 2026 billing months**.
The first adapter accepts one complete calendar month at 15-, 30-, or 60-minute
resolution. This is suitable for calendar-month study cases; an actual meter
cycle that straddles months is **not yet supported**. Fixed charges apply once;
there is no invented daily proration or inferred billing month.

The result has `subtotal_usd`, `total_usd=None`, `is_complete_bill=False`, and
explicit exclusions: state electricity excise tax, municipal utility taxes,
and franchise costs. Illinois Electricity **Distribution** Tax is already
included and is distinct from those excluded taxes. The subtotal must not be
displayed as the complete bill or final savings after tax.

Commercial BES/BESH classes and both customer types are now available through
[the local ComEd billing browser](ComEd_Commercial_Billing.md). BEST time-of-use
supply, distribution TOU, alternative suppliers/municipal aggregation, multiple
meters, net metering/export credits and discount-program accounts remain
unsupported in the standalone billing adapter. A separate
[main-workflow simulation candidate](ComEd_Simulation_Integration.md) now uses
these same authoritative subtotals for approved/hypothetical non-export PV and
ESS operation. It does not promote the existing stable browser release.

## Usage

```python
from datetime import date
import pandas as pd
from src.billing.comed_residential import (
    ComEdResidentialAccount, ComEdHourlyPrices,
    calculate_comed_residential_bill,
)

# Explicit synthetic example, not a measured home.
index = pd.date_range("2026-09-01", "2026-10-01", freq="15min",
                      tz="America/Chicago", inclusive="left")
imports = pd.Series(1.0, index=index)  # average meter-import kW, 720 kWh
account = ComEdResidentialAccount(
    supply="BES",
    delivery_class="single_family_non_electric_heat",
    billing_month=date(2026, 9, 1),
    ordinary_import_only_confirmed=True,
)
result = calculate_comed_residential_bill(imports, account)
assert result["subtotal_usd"] == 137.45
assert result["total_usd"] is None
```

For BESH, specify `supply="BESH"`, `capacity_obligation_kw` and
`capacity_source` on the account. Use the obligation from the utility account,
or clearly label a hypothetical study assumption. It is **not** the maximum
power from this month's simulated imports. A documented zero is accepted;
a missing obligation is rejected.

Pass `hourly_prices=ComEdHourlyPrices(...)` with all of these explicit fields:

| Field | Required value/meaning |
|---|---|
| `values` | Numeric pandas Series with exactly one value per physical hour |
| `source` | Nonempty source reference identifying the dataset or synthetic assumption |
| `zone` | `COMED` |
| `price_basis` | `pjm_real_time_residual_lmp` |
| `unit` | `USD/MWh` |
| `timestamp_convention` | `interval_start` |

This expects the **PJM real-time residual LMP for the ComEd zone**, per Rate
BESH sheet 34. Do not relabel a Western Hub, day-ahead, five-minute, generic
zonal LMP, or already-adjusted retail series to satisfy this contract. The
adapter validates the declared type and interval coverage; it cannot verify
the truth of user-provided source metadata. Retrieving and verifying the
correct actual hourly market series is a separate integration step.

The meter Series and price Series require timezone-aware interval starts.
UTC input is accepted; month boundaries are America/Chicago. Missing,
duplicate, out-of-order, naive, shifted, or extra observations are rejected.
Subhourly meter energy is matched to its physical UTC hour. Negative hourly
prices are valid; negative meter imports are rejected, not silently clipped.
No data are filled and no export revenue is inferred.

## Filed arithmetic

Primary source: [ComEd's filed 2026 ratebook](https://www.comed.com/cdn/assets/v3/assets/blt3ebb3fed6084be2a/blt86ebee5fe6ed02f8/6ab16afb15d5b73190b00e59/2026_Ratebook.pdf?branch=prod_alias).
Each line includes one-based PDF page references. Rate literals live in
`src/billing/comed_rates.py`; amounts below are USD rather than cents.

| Supply component | September 2026 | October 2026 | PDF page |
|---|---:|---:|---:|
| BES energy, $/kWh | 0.08678 | 0.08413 | 782 |
| BES transmission, $/kWh | 0.01723 | 0.01690 | 783 |
| BES purchased-electricity adjustment, $/kWh | -0.00087 | -0.01551 | 784 |
| BESH capacity, $/kW-month | 10.10121 | 10.10121 | 785 |
| BESH transmission, $/kWh | 0.01073 | 0.01075 | 786 |
| BESH miscellaneous procurement, $/kWh | 0.00134 | 0.00226 | 787 |
| BESH purchased-electricity adjustment, $/kWh | 0.00385 | -0.02296 | 788 |

BESH hourly energy is the sum of meter kWh in each hour times:

`HEC = residual_LMP_USD_per_MWh / 1000 × 1.0124 × 0.9968 × (1 + 0.0406)`.

The factors are system-average supply uncollectible, incremental supply
uncollectible, and distribution loss, respectively (pages 60, 801, 802, 814).
The residential class loss factors on page 814 do **not** apply to BESH.
The filed capacity, transmission and procurement rates already include their
applicable factors; the model does not apply them twice. BES includes capacity
and miscellaneous procurement in its filed supply rate and receives neither
as a separate charge.

Miscellaneous procurement means procurement costs not already recovered by
BESH's energy, capacity and PJM services charges (sheet 35, PDF page 61). It
is a filed pass-through component, not an arbitrary simulator markup.

Delivery uses base charges on page 848, with the formulas on pages 864–865:

- Customer/meter: base × (IDUF + DRAF + EDAF + TPAF + class RBAF).
- Distribution facilities: the same factor treatment, plus DG rebate adjustment.
- Illinois distribution tax: base × (IDUF + class RBAF) only.
- Customer charge also includes $0.91 RCA: $0.05 renewable/coal assistance,
  $0.80 energy assistance and $0.06 residential real-time program recovery.
  Consolidated billing and purchase-of-receivables adjustments are zero.

As shown in the [official delivery calculation guide](https://www.comed.com/cdn/assets/v3/assets/blt3ebb3fed6084be2a/blt7904befea93c3525/695c1987487fe7e68ec05155/A_Guide_to_the_Retail_Customer_s_Billed_Delivery_Service_Charges.pdf?branch=prod_alias),
each factor's incremental contribution is rounded **before** summing: two
decimals for monthly charges and five for $/kWh charges. The guide's January
2026 factors are not reused for September. The adapter uses decimal arithmetic
and half-up cent rounding for final line amounts; exact customer-invoice
reconciliation remains unverified because no measured ComEd bill was supplied.

Other standard lines include environmental recovery, renewable portfolio
standard, zero-emission standard, energy efficiency, energy-transition
assistance, coal-to-solar, carbon-free resource adjustment, and $1.35/month
low-income discount recovery. The latter is a recovery charge, not a customer
discount. CFRA includes its monthly reconciliation once: -$0.01628/kWh in
September and -$0.00115/kWh in October (page 818). Negative credits stay negative.

## Provenance, coverage and next work

Retained evidence is in `docs/utility_sources/comed/`: a PDF containing only
the used ratebook pages, text extractions, the guide's calculation page, and
a manifest with source URLs, original-document hashes and excerpt page maps.
The full ratebook SHA256 is
`0e3f2ee2fcd2658e41312bc50afbda08a5830f8efaf761430c83e09abff65de1`.
No network access is required to calculate bills or run tests.

The ten-calendar-year research target is **2017–2026**. The initial search
located the ICC [historical PEA index](https://icc.illinois.gov/ormd/purchased-electricity-adjustment)
and [historical price-to-compare workbook](https://icc.illinois.gov/downloads/public/pluginillinois/1HistoricalPricestoCompare.xlsx).
The web reader returned 502 for the former and could not retrieve the latter;
neither is treated as verified historical rate data in this release. Price to
compare alone also omits delivery and other riders. The filed ratebook contains
some older base rates and rule revisions, but they do not establish complete
historical composite coverage.

For every one of the eight plan/class combinations:

| Billing months | Status |
|---|---|
| January 2017–August 2026 | Unsupported; full component history unverified |
| September–October 2026 | Implemented subtotal for the scope above |
| November–December 2026 | Unsupported; PEA/HPEA and CFRA reconciliation not verified |
| 2027 onward | Unsupported; some BESH charge structures change in January 2027 |

The informational sheets specify **billing-month applicability**, which can
differ from their filing/effective date in the footer. The eight `RatePlan`
objects returned by `build_comed_residential_plans()` use that confirmed
billing-month selection. They are intentionally not registered in the generic
service-date `TariffDefinition` catalog, which cannot express BESH's external
hourly series and account capacity obligation without losing information.

Next work: verified tax/franchise geography and real-cycle billing; actual
customer bill reconciliation; complete historical monthly composites; separately
verified commercial and TOU eligibility/rates; export settlement; then shared
further historical/operational modeling. The main-workflow candidate reuses the
authoritative charges for optimization; see its separate bounded scope. A frontend must preserve the
subtotal label and coverage checks rather than treating the model as complete.

## Verification

`/usr/local/bin/python3 -m pytest -q test/test_comed_residential.py`

The tests cover an independent $137.45 September benchmark, all four delivery
classes, October changes, credits, interval-weighted BESH energy and negative
prices, capacity independence from the current peak, zero-use fixed charges,
15/30/60-minute alignment, UTC/local equivalence, DST grid validation, and
rejection of invalid account, tariff-date, meter and price inputs. Test prices
and loads are synthetic and make no claim about observed customer savings.
