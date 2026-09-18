# Residential export comparison

`tools/compare_residential_exports.py` compares recorded grid energy under PG&E
bundled E-1 and E-TOU-C. It is an offline billing study, not a new browser or
battery-dispatch mode. Supply paths with `--usage`, `--bills`, `--output` and an
explicit `--territory`. Keep personal exports and generated reports in an
ignored local directory such as `.cache/`.

The adapter in `src/billing/residential_comparison.py` uses historical E-1
registry rates and verified E-TOU-C workbook rates. The March 2026 rate gap is
resolved for this bounded comparison by advice 7846-E, sheets 61096-E and
61125-E. The current workbook corroborates those energy/base rates; advice
7921-E changes climate-credit timing. This does not alter the existing
residential registry or fill its gaps for other consumers. Verified comparison
coverage is March 1, 2025 through September 17, 2026.

Account billing cycles, not calendar months, determine baseline accrual. Basic
and all-electric baseline codes are separate scenarios. Each rate-refiling
segment receives its own daily allowance and recorded energy, an explicit
approximation inherited conceptually from timeline billing. Seasonal boundaries
within a version accumulate each day's allowance in one cycle.

Reported subtotals include energy and the standard daily base charge, but
exclude taxes, climate credits, delivery minimum adjustments, export and other
account adjustments. They must not be labeled final utility bills. Discounted
accounts and subsidized-housing base-charge eligibility are not modeled.

Incomplete cycles, ambiguous/nonexistent local timestamps, and usage differences
larger than the mathematical rounding bound are excluded and listed. The
rounding bound is 0.005 kWh per hourly row plus 0.005 kWh for the bill total;
being inside the bound does not prove rounding caused the difference. The core
calculator also rejects gaps, duplicate instants, negative energy and rates
outside verified coverage. Source-estimated rows are counted in results.

Sources:

- [Historical residential workbooks](https://www.pge.com/tariffs/en/rate-information/electric-rates.html)
- [March rate filing](https://www.pge.com/tariffs/assets/pdf/adviceletter/ELEC_7846-E.pdf)
- [June climate-credit filing](https://www.pge.com/tariffs/assets/pdf/adviceletter/ELEC_7921-E.pdf)
- [Current workbook](https://www.pge.com/assets/rates/tariffs/res-inclu-tou-current.xlsx)
- [Baseline territories](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_PRELIM_A.pdf)
