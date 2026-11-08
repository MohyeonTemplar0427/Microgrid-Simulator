"""Delaware Electric Cooperative R/GS complete-calendar rate intersections.

Rates belong to DEC, not Delaware County Electric Cooperative in New York and
not Delmarva Power. All monetary energy factors below are dollars per kWh.
"""
from calendar import monthrange
from datetime import date

ROOT = "https://www.delaware.coop/"
BOOK_2024 = ROOT + "sites/default/files/2024-11/Tariff%20-%20Revised%20November%202024.pdf"
BOOK_MAR2025 = ROOT + "sites/default/files/2025-03/Tariff%20-%20Revised%20March%202025.pdf"
BOOK_AUG2025 = ROOT + "sites/default/files/2025-08/Tariff%20-%20Revised%20August%202025.pdf"
BOOK_2026 = ROOT + "sites/default/files/2026-06/Tariff%20-%20Revised%20June%202026%20.pdf"
PCA_NOTICE = ROOT + "press-room/board-approves-pca-change"
TAX_SOURCE = "https://delcode.delaware.gov/title30/c055/"
NONEXPORT = (ROOT + "sites/default/files/2024-05/DEC%20Interconnection%20Agreement%20"
             "%28Under%20100kW%29%20April%202024%20Non-Export_1.pdf")
BATTERY = (ROOT + "sites/default/files/2023-09/DEC%20Interconnection%20Agreement%20"
           "%28Battery%20Storage%29%2C%20Updated.pdf")
SOURCES = [BOOK_2024, BOOK_MAR2025, BOOK_AUG2025, BOOK_2026, PCA_NOTICE,
           TAX_SOURCE, NONEXPORT, BATTERY]
BASE = {
    "R": dict(customer=28., distribution=.021400, supply_first=.101600, supply_over=.081600),
    "GS": dict(customer=30., distribution=.022498, supply_first=.111090, supply_over=.101090),
}
COVERAGE = (("2025-01-01", "2026-10-31"),)
GAPS = (("2026-11-01", "2026-12-31",
         "Incomplete/future cycles at the November 7 evidence cutoff are outside this accepted historical scope; no future PCA or tariff continuity is inferred."),)


def rates_for_month(month, plan):
    """Return one complete component stack; never backfill or roll rates forward."""
    if plan not in BASE:
        raise ValueError("Select Delaware Electric Cooperative ordinary R or GS.")
    try:
        value = date.fromisoformat(month)
    except (TypeError, ValueError):
        raise ValueError("Delaware Electric Cooperative requires an ISO calendar-month start.") from None
    if (value.day != 1 or value.isoformat() != month
            or not any(start <= month <= end for start, end in COVERAGE)):
        raise ValueError(f"Delaware Electric Cooperative complete component coverage is unverified for {str(month)[:7]}.")
    changed = month >= "2026-05-01"
    if changed:
        book = BOOK_2026
    elif month >= "2025-08-01":
        book = BOOK_AUG2025
    elif month >= "2025-03-01":
        book = BOOK_MAR2025
    else:
        book = BOOK_2024
    return dict(
        **BASE[plan], renewable_resource_fund=.000178,
        pca=.012161 if changed else -.001500,
        public_utility_tax=.0425 if plan == "GS" else 0.,
        source_version="dec-2026-05" if changed else "dec-2024-07",
        source_grade="official_cooperative_tariffs_notice_and_state_tax",
        sources=[book, PCA_NOTICE, TAX_SOURCE],
        month_end=value.replace(day=monthrange(value.year, value.month)[1]).isoformat(),
    )
