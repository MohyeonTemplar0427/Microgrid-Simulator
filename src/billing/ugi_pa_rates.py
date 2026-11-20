"""UGI Utilities Electric Division, Pennsylvania P.U.C. No. 6, Rates R and GS-1."""
from calendar import monthrange
from datetime import date

PLANS = {"R": "Residential Service", "GS-1": "General Service"}
ARCHIVE = "https://ugi.outsystemsenterprise.com/UGITariff_FO/Tariffs?Division=Electric"
MARCH_BOOK = "https://www.ugi.com/wp-content/uploads/2026/03/BOOK%20IX%20(Current%20Tariffs)_ADA.pdf"
WORKPAPER = "https://www.ugi.com/wp-content/uploads/2026/03/BOOK%20IV%20(Exhibits%20A,%20B%20and%20E)_ADA.pdf"
CUSTOMER_GENERATION = "https://www.ugi.com/resources-for-customer-generation/"
EIA = "https://www.eia.gov/electricity/data/eia861/zip/f8612025.zip"
TAX = "https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/sales-use-and-hotel-occupancy-tax"
EXEMPTION = "https://www.pacodeandbulletin.gov/secure/pacode/data/061/chapter32/s32.25.html"
TAX_BASIS = "https://www.pacodeandbulletin.gov/secure/pacode/data/061/chapter33/s33.2.html"
SOURCES = [ARCHIVE, MARCH_BOOK, WORKPAPER, TAX, EXEMPTION, TAX_BASIS, CUSTOMER_GENERATION, EIA]

# Source units are cents per kWh or percentages; the last column is the filed supplement.
# GSR-1 used one price for both classes through May 2025.
GSR = (
    ("2024-12-01", 10.637, 10.637, 75),
    ("2025-06-01", 11.470, 11.005, 81),
    ("2025-12-01", 11.211, 10.758, 87),
    ("2026-06-01", 12.616, 12.093, 93),
    ("2026-12-01", 12.401, 11.886, 101),
)
USP = (
    ("2024-12-01", 2.121, 76), ("2025-06-01", 2.222, 82),
    ("2025-12-01", 1.868, 88), ("2026-06-01", 2.120, 95),
)
EEC = (
    ("2024-09-01", .151, .122, 73), ("2025-09-01", .181, .233, 84),
    ("2026-09-01", .170, .343, 98),
)
STAS = (
    ("2023-10-01", 0., 62), ("2025-01-20", .01, 78),
    ("2025-09-20", .02, 85), ("2026-01-19", .01, 90),
    ("2026-07-20", 0., 97), ("2026-10-19", -.01, 100),
)
# Rider G expressly selects bills rendered; all other dated components select service.
DSIC = (
    ("2025-01-01", .32, 77), ("2025-04-01", .74, 79),
    ("2025-07-01", 1.23, 83), ("2025-10-01", 1.41, 86),
    ("2026-01-01", 1.83, 89), ("2026-04-01", 2.28, 91),
    ("2026-07-01", 3.25, 96), ("2026-10-01", 4.46, 99),
)
COMMON_COVERAGE = (
    ("2025-02-01", "2025-08-31"), ("2025-10-01", "2025-12-31"),
    ("2026-02-01", "2026-06-30"), ("2026-08-01", "2026-09-30"),
)
COVERAGE = {
    "R": (*COMMON_COVERAGE, ("2026-11-01", "2026-11-30")),
    "GS-1": (*COMMON_COVERAGE, ("2026-11-01", "2026-12-31")),
}
TRANSITIONS = tuple(row[0][:7] for row in STAS[1:])


def _on(table, day):
    return next(row for row in reversed(table) if day >= row[0])


def rates_for_month(month, plan):
    if plan not in PLANS:
        raise ValueError("Select UGI Electric Pennsylvania R or GS-1.")
    try:
        start = date.fromisoformat(month)
    except (TypeError, ValueError):
        raise ValueError("UGI requires an ISO calendar-month start.") from None
    end = start.replace(day=monthrange(start.year, start.month)[1]).isoformat()
    if (start.day != 1 or start.isoformat() != month
            or not any(lo <= month and end <= hi for lo, hi in COVERAGE[plan])):
        raise ValueError(f"UGI {plan} complete-cycle rate coverage is unverified for {month[:7]}.")
    res = plan == "R"
    column = 1 if res else 2
    gsr, usp, eec = _on(GSR, month), _on(USP, month), _on(EEC, month)
    stas, dsic = _on(STAS, month), _on(DSIC, end)
    versions = dict(base=62, gsr=gsr[-1], eec=eec[-1], dsic=dsic[-1], stas=stas[-1])
    if res:
        versions["usp"] = usp[-1]
    timing = "completed_calendar_month"
    if month == "2026-11-01":
        timing = "in_progress_as_of_2026-11-19"
    elif month == "2026-12-01":
        timing = "published_forward_as_of_2026-11-19"
    return dict(
        customer=10.75 if res else 17., distribution=.05290 if res else .05987,
        supply=gsr[column] / 100, universal_service=usp[1] / 100 if res else 0.,
        efficiency=eec[column] / 100, dsic=dsic[1] / 100, stas=stas[1] / 100,
        sales_tax=0. if res else .06, source_versions=versions, coverage_timing=timing,
    )
