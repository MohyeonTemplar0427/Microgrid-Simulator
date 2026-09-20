# SCE residential January–June 2026 coverage audit

Retrieved and verified September 19, 2026 from [SCE's official 2026 archive](https://www.sce.com/regulatory/regulatory-information/tariff-books/historical-rates/historical-rate-schedules-for-2026) and its current residential tariff folder. `rates.json` records direct URLs, PDF hashes, source pages, eight runtime versions and their cancellation links. Extracted full texts are retained here; original PDFs and rendered price-table checks are in `.cache/sce_history/`.

## Price continuity established by explicit replacements

| Supported plan | Jan 1, 2026 sheet (AL 5725-E) | June 1, 2026 replacement (AL 5829-E) |
|---|---|---|
| D | 90841-E | 91130-E cancels 90841-E |
| TOU-D-4-9 | 90937-E | 91196-E cancels 90937-E |
| TOU-D-5-8 | 90939-E | 91198-E cancels 90939-E |
| TOU-D-PRIME | 90941-E | 91200-E cancels 90941-E |

January sheets were submitted December 30, 2025 but **effective January 1, 2026**. Their energy prices remain applicable through May 31 because June sheets explicitly cancel them. The four January delivery component sheets are also explicitly cancelled by June replacements. This is filed continuity, not interpolation or carrying a newer rate backward. The June versions end at the existing verified study boundary, September 17, 2026; no later coverage is claimed.

All eight full price pages were extracted with pdfplumber and visually inspected. January D delivery is $0.18482 baseline / $0.28590 above baseline per kWh; generation $0.11761/kWh. June delivery becomes $0.18453 / $0.28552; generation stays $0.11761. Both periods have $0.794/day ordinary BSC and $0.00619/kWh FRC. TOU baseline credit changes from $0.10108 to $0.10099/kWh (4–9/5–8 only). The JSON includes every TOU delivery/generation row. MCAM is not charged to bundled customers; it is not added to the model.

## Billing-rule review

- **Inherited rules:** D applicability and ordinary BSC billing sheets effective November 15, 2025 remain operative unless explicitly replaced. TOU-D applicability sheet 88510-E (August 15, 2024) continues until June 25, 2026. Supported 4–9/5–8/PRIME options exist before that date; they are not introduced by the June filing. Ordinary household eligibility, time periods/holidays, Preliminary H baseline quantities, and Rule 9 daily-charge counting retain the established model behavior. Sources for inherited terms are recorded in `../history_2025/` and the parent source directory.
- **January 1:** AL 5725-E updates prices and discount components. The ordinary BSC remains $0.794/day; no pre-BSC minimum returns. CARE/FERA/medical/deed-restricted discount accounts remain outside supported scope.
- **March 20:** AL 5771-E / D.26-03-013 revises D sheet 7 (91033-E replacing 90843-E) and TOU-D sheet 21 (91040-E replacing 88512-E). The climate-credit condition removes the fixed April/October semiannual wording. Tax ordering and carry-forward language remain. This does not change the supported ordinary recurring energy prices. The application continues to accept only a bill-confirmed credit amount, not automatically assume an April award. A multi-cycle credit ledger and jurisdiction-specific franchise fees remain unimplemented.
- **June 1:** AL 5829-E replaces the January price sheets and changes discount/BSC component amounts. Ordinary total BSC remains unchanged. D sheet 6 replaces 90638-E; TOU-D sheet 20 replaces 90676-E. Discounted accounts remain excluded.
- **June 25:** AL 5837-E revises TOU-D applicability and renumbers/revises conditions, removing discontinued A/B options. The supported price sheets 91196-E, 91198-E and 91200-E remain effective June 1. PRIME component sheet 91355-E cancels 91201-E but retains the same ordinary total prices. No artificial June 25 energy-price or baseline-accumulation boundary is created.

This fills **residential** coverage only. SCE commercial still starts June 25, 2026. Existing account confirmation, import-only/export rejection, unsupported riders, and cross-rate/season allocation approximations remain unchanged. No CCA or new provider is enabled.

## Runtime and validation

`src/billing/sce_residential_2026_data.py` carries the verified values inside immutable worker snapshots. The shared `RatePlan` timeline and numerical/convex charge functions use these versions for billing and dispatch. The browser obtains coverage from the same registry. Regression cases cover January, March DST, May, January 1 and June 1 transitions, June 24/25 continuity, all four plans, battery cost reconciliation and rejection beyond verified dates.

Validation completed: **1,128 tests passed**, including 22 new early-2026 checks. Sixteen independent-worker API cases completed; results are in `../../../validation/sce_2026_gap_fill.csv`. The main preview January D bill is $295.18572 for the explicit constant-1-kW test load.
