# SCE historical residential rates retrieved September 19, 2026

Official starting point: [SCE Historical Prices & Rates 2025](https://www.sce.com/regulatory/regulatory-information/tariff-books/historical-rates/historical-rate-schedules-for-2025).

Retrieved the official D (16 pages) and TOU-D (54 pages) annual change archives. Extracted **20 rate-table versions**: five each for D, TOU-D-4-9, TOU-D-5-8 and TOU-D-PRIME. All sixteen consecutive replacement links were checked against the tariff-sheet cancellation identifiers, not inferred from announcement dates or PDF page order. The archive pages are not sorted chronologically.

## Confirmed price changes

| Effective start | End established by next replacement | Change |
|---|---|---|
| January 1, 2025 | February 28, 2025 | Initial 2025 prices |
| March 1, 2025 | May 31, 2025 | Revised prices |
| June 1, 2025 | September 30, 2025 | Revised prices; applicable to the July validation |
| October 1, 2025 | November 14, 2025 | Revised prices |
| November 15, 2025 | December 31, 2025; January 2026 cancellation sheets independently verified | Revised prices and Base Services Charge |

A November 2025 simulation crosses a structural billing change. D and TOU-D-4-9/5-8 previously had $0.031/day single-family or $0.024/day multifamily basic charges and a $0.346/day ordinary minimum. November 15 introduced a $0.794/day BSC. PRIME previously had its own basic charge. These rules cannot be modeled by extending the 2026 rate table backward.

## Data files

- `residential_rate_changes.json`: source URLs and SHA-256 hashes; effective starts, established ends, tariff sheets and advice letters; delivery and generation prices; baseline credits, FRC, basic/BSC and minimum amounts.
- `domestic_d_changes.csv`: compact D comparison table.
- `sheet_index.json`: all 70 PDF pages indexed by effective date and tariff-sheet identifier, including changes to terms rather than prices.

Raw PDFs and extraction script are in the local generated-data folder `.cache/sce_history/`. Files were downloaded through the public anonymous archive link listed on SCE's website. No login, customer data or private account access was used. The 20 historical versions are registered in `src/billing/sce_residential_data.py`, with historical terms reconstructed from the 2024 archive and Preliminary H / Rule 9. The original extraction JSON is retained unchanged; its null final ends are bounded in runtime by the independently verified January 2026 cancellations.

## Interpretation and integration requirements

A prior-year rate can remain effective in a later year when the tariff history supports that continuity. Filing/announcement date is not the effective date: for example, the January 1, 2025 filing was submitted December 30, 2024. Here, multiple actual 2025 changes exist, so a single 2024 carry-forward or latest-rate regression would not reproduce 2025 tariffs.

Historical integration must reconstruct the unchanged historical terms and baseline allowances alongside these changed sheets. Annual change archives contain changed sheets, not necessarily complete consolidated schedules. Check the pre-BSC minimum-charge formula (D excludes WFC from its comparison), meter-read allocation at price changes, credits, taxes, and any special eligibility. MCAM is shown on the sheets but applies to designated nonbundled generation customers; do not add it to bundled bills.

Integrate with the shared stable-plan / dated-version architecture, retain per-version provenance, and use identical dated billing costs in dispatch. Missing terms must remain explicit; `effective_end: null` in this research file does not authorize unlimited future coverage. The initial retrieval did not change runtime coverage. The subsequent September 19 integration enables calendar-year 2025 only, preserving prior saved results.

## Extraction checks

Twenty expected rate tables, each with four D rows or six TOU rows, and sixteen matching cancellation chains. Representative D January/November and TOU-D June tables were rendered and visually inspected against extracted values. Monetary values are USD; energy units are kWh and daily charges are per meter. See source sheets for qualifications and footnotes; the JSON is not a complete billing specification.

## Additional evidence and bounded integration

`additional_evidence.json` records 2024 and 2026 archive hashes and Rule 9 evidence. `baseline_h.txt` contains the filed baseline allowances; `rule9_daily_billing.txt` establishes actual daily-charge counting. January 2026 sheets 90841-E, 90937-E, 90939-E and 90941-E cancel the November 2025 price sheets. This closes 2025 coverage without extrapolating into the unimplemented 2026 interval.

Across rate/season changes, baseline and minimum allocation remains an explicit day-prorated study approximation. Climate credits require a user-supplied, bill-confirmed amount; automatic award eligibility and carry-forward ledgers are not included.

The later [2026 audit](../history_2026/README.md) now establishes and integrates January 1–June 24, 2026 continuity. Earlier statements in this retrieval log describe the previous implementation state.
