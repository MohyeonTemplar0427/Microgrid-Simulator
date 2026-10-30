# Duquesne RS / GS delivery research

Verified October 29, 2026. Owned scope is customer/distribution charges and
ordinary delivery riders; Rider 8 supply, Appendix A transmission, sales-tax
jurisdiction and Rider 10 STAS are reviewed independently by the other research
scopes. Exact decimal input data are in `rates_by_window.json`; original PDF
identities and retained page excerpts are in `sources.json`.

The source tariff is Electric PA PUC No. 25. The December 20, 2024 base-rate
settlement Supplement 85 establishes RS $13/month plus 8.2479 cents/kWh and
non-demand GS $18/month plus 8.4601 cents/kWh. Clean filed pages 38 and 46 are
PDF pages 35 and 41 in PUC document 1859015. The December replacement document
1859726 corrects headers on printed pages 72-74; it does not modify RS/GS prices.
Both current compiled tariffs 99 and 110 retain these same Supplement 85 pages.

## Rider windows

| Component | Period in study scope | RS | GS | Source |
| --- | --- | ---: | ---: | --- |
| EEC | Jan-May 2025 | 0.21 cents/kWh | 0.20 cents/kWh | Supp 76, PUC 1826568, PDF p16 / printed 118 |
| EEC | Jun 2025-May 2026 | 0.19 cents/kWh | **-0.06 cents/kWh** | Supp 93, PUC 1877398, PDF p6 / printed 118 |
| EEC | Jun-Oct 2026 | 0.17 cents/kWh | 0.09 cents/kWh | Final Supp 104, PUC 1927034, PDF p4 / printed 118 |
| USC | 2025 | 1.549 cents/kWh | Not applicable | Supp 84, PUC 1857627, PDF p14 / printed 93 |
| USC | Jan-Oct 2026 | 1.599 cents/kWh | Not applicable | Revised Supp 97, PUC 1904364, PDF p14 / printed 93 |
| Smart meter | Entire study scope | $0/meter-month | $0/meter-month | Supp 55, PUC 1768417, PDF p5 / printed 129 |
| Retail market enhancement | Entire study scope | $0/month | $0/month | Supp 40, PUC 1731394, PDF p6 / printed 88 |

USC applies to non-CAP residential delivery only and is embedded in the
distribution energy charge for presentation. EEC is added to RS distribution
energy and is a separate GS line; the underlying base energy rates above do
**not** include either rider. The explicit zero meter/RMES pages are retained;
zero is not inferred from missing data. Filed rider calculations already include
GRT recovery, which must not be added again.

Phase V rates begin **June 1, 2026**, not August 27. The final original Supp 104
PDF page 4 and current compiled tariff 110 printed page 118 both explicitly
state June 1. August 27 is the effective date of Supp 106's rider-matrix change
on printed page 87A adding the commercial-conversion pilot. That unrelated page
does not delay Phase V or alter these ordinary RS/GS EEC prices.

## DSIC clock, signs and base

DSIC applies on a **bills-rendered basis**, using otherwise-applicable total
distribution rates and charges including riders, excluding STAS. STAS applies
to DSIC. It is not applied to DSS or transmission. For the initial scope the
parent implementation uses matching complete calendar cycles and bills rendered
on the final service date, avoiding unsupported service-day allocation.

| Bill date | DSIC | Supplement | Original PUC document | Printed page revision |
| --- | ---: | ---: | ---: | --- |
| Jan-Mar 2025 | -0.10% | 87 | 1860296 | 25th revised 137 |
| Apr-Dec 2025 | 0.02% | 90 | 1871144 | 26th revised 137 |
| Jan-Mar 2026 | 0.49% | 99 | 1907919 | 27th revised 137 |
| Apr-Jun 2026 | 1.39% | 101 | 1919225 | 28th revised 137 |
| Jul-Sep 2026 | 2.17% | 107 | 1936914 | 29th revised 137 |
| Oct 2026 | 3.36% | 110 | 1950968 | 30th revised 137 |

The April-December 2025 continuation is established by the revision chain:
Supp 99 directly cancels the 26th revised page from Supp 90. It is not an
assumption that missing July/October history entries equal a zero rate. The
filed fourth-quarter 2026 DSIC continues through December, but complete future
delivery/supply coverage is not asserted beyond the parent implementation's
explicit covered window.

Minimum bills must not be reduced by reason of DSIC, and DSIC is excluded from
the rate-schedule minimum. Smart meter charges are also excluded from that
minimum. Special/low-import minimum applicability is separately constrained by
the parent adapter and rules research; no unknown minimum amount is invented.

## Retrieval and visual checks

The utility's direct PDF routes returned Incapsula HTML with HTTP 200; retired
short filenames also returned 404 to the web reader. Those responses were
retained as `.blocked.html`, not mislabeled as PDFs. Original filed PDFs were
instead retrieved successfully from the Pennsylvania PUC's public docket
attachments. Sixteen source PDFs and all retained page hashes were checked.
Rate tables for RS/GS base charges and all three EEC windows were rendered and
visually reviewed. PNGs and full originals remain under ignored
`.cache/duquesne_pa/sources/delivery/`.

There is no remaining numerical delivery-component gap for matching ordinary
RS/GS calendar cycles January 2025-October 2026. This finding does not establish
default-supply coverage, eligibility, tax jurisdiction, irregular-cycle billing,
special programs, export settlement or customer-invoice calibration.
