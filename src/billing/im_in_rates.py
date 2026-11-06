"""IURC No. 20 Indiana bundled rates. Tracker values are filed cents/kWh."""
from calendar import monthrange

BOOK_ROOT = "https://www.indianamichiganpower.com/lib/docs/ratesandtariffs/Indiana/"
BOOK_JAN26 = BOOK_ROOT + "IM_IN_TB_20_01-30-2026.pdf#page=1"
BOOK_SEP26 = BOOK_ROOT + "IM_IN_TB_20_09-29-2026.pdf"
BOOK_OCT26 = BOOK_ROOT + "IM_IN_TB_20_10-28-2026.pdf"
IURC = "https://www.in.gov/iurc/files/"
DSM_2025 = IURC + "Amended-Utility-Articles-5.21.25.pdf"
PHASE_II = ("https://iurc.portal.in.gov/_entity/sharepointdocumentlocation/"
            "5c1c76f4-0ef6-ef11-be20-001dd80b8c52/bb9c6bba-fd52-45ad-8e64-a444aef13c39"
            "?file=46090_Indiana+Michigan+Power+Company_Tariff+Submission_022825.pdf")
FAC_94 = IURC + "ord_38702FAC94_043025.pdf"
FAC_95 = IURC + "ord_38702FAC95_102925.pdf"
PJM_15 = IURC + "ord_43774PJM15_061825.pdf"
RA_5 = IURC + "ord_45164RA5_072325.pdf"
SALES_TAX = "https://www.in.gov/dor/files/sib51.pdf"
DER = "https://www.indianamichiganpower.com/business/builders/CreateGreen-IN"

# Each entry covers whole calendar cycles only. Sources preserve superseded
# sheets and the distinction between service-date and billing-month clocks.
WINDOWS = (
    ("2025-06", "2025-06", (BOOK_SEP26, PHASE_II, DSM_2025, FAC_94)),
    ("2025-07", "2025-07", (BOOK_SEP26, PHASE_II, DSM_2025, FAC_94, PJM_15)),
    ("2025-08", "2025-09", (BOOK_SEP26, PHASE_II, DSM_2025, FAC_94, PJM_15, BOOK_JAN26, RA_5)),
    ("2025-11", "2025-12", (BOOK_SEP26, PHASE_II, DSM_2025, FAC_95, BOOK_JAN26, PJM_15, RA_5)),
    ("2026-01", "2026-03", (BOOK_SEP26, BOOK_JAN26, FAC_95, PJM_15, RA_5)),
    ("2026-04", "2026-04", (BOOK_SEP26, BOOK_JAN26, FAC_95, PJM_15)),
    ("2026-07", "2026-10", (BOOK_SEP26,)),
    ("2026-11", "2026-11", (BOOK_OCT26,)),
)
GAPS = (
    ("2025-01-01", "2025-04-30", "Earlier Phase II and final FAC 93 implementation sheets were not fully reconciled."),
    ("2025-05-01", "2025-05-31", "FAC changes for service rendered from May 5. Within-cycle allocation is unverified."),
    ("2025-10-01", "2025-10-31", "FAC changes for service rendered from October 31. Within-cycle allocation is unverified."),
    ("2026-05-01", "2026-06-30", "May FAC continuation is unverified and the new filed FAC starts June 8."),
    ("2026-12-01", "2026-12-31", "The next approved ECR filing's implementation date has not been verified."),
)
SOURCES = list(dict.fromkeys([*(url for _, _, sources in WINDOWS for url in sources), SALES_TAX, DER]))

# All RS tariff classes and the non-opt-out GS up-to-4,500 kWh row.
# Fuel and DSM are flat within this envelope. GS higher-energy and billed-kW
# factors are outside scope. The November 2026 FAC is class-specific.
COMMON_2025 = dict(dsm_ee=(.1935, .1576), environmental=(.1720, .1413))
COMMON_2026 = dict(dsm_ee=(.1379, .3873), environmental=(.1537, .1321))
PHASE_AND_TAX = dict(phase_in_credit=(-.2286, -.1511), tax_rider=(.3278, .2648))
TRACKERS = {
    "2025-06": dict(**COMMON_2025, fuel=(-.0450, -.0450), oss_pjm=(2.9289, 2.3571),
                    resource_adequacy=(.0400, .0325), solar_power=(.0148, .0115)),
    "2025-07": dict(**COMMON_2025, fuel=(-.0450, -.0450), oss_pjm=(2.8912, 2.3011),
                    resource_adequacy=(.0400, .0325), solar_power=(.0148, .0115)),
    "2025-08": dict(**COMMON_2025, fuel=(-.0450, -.0450), oss_pjm=(2.8912, 2.3011),
                    resource_adequacy=(.2844, .2303), solar_power=(.0148, .0115)),
    "2025-11": dict(**COMMON_2025, fuel=(-.0168, -.0168), oss_pjm=(2.8912, 2.3011),
                    resource_adequacy=(.2844, .2303), solar_power=(.0151, .0127)),
    "2026-01": dict(**COMMON_2026, fuel=(-.0168, -.0168), oss_pjm=(2.8912, 2.3011),
                    resource_adequacy=(.2844, .2303), solar_power=(.0151, .0127)),
    "2026-04": dict(**COMMON_2026, fuel=(-.0168, -.0168), oss_pjm=(2.8912, 2.3011),
                    resource_adequacy=(.0730, .0590), solar_power=(.0151, .0127)),
    "2026-07": dict(**COMMON_2026, fuel=(.1933, .2422), oss_pjm=(2.2753, 1.7635),
                    resource_adequacy=(.0730, .0590), solar_power=(.0151, .0127)),
    "2026-11": dict(**COMMON_2026, fuel=(-.0050, .0096), oss_pjm=(2.2753, 1.7635),
                    resource_adequacy=(.0730, .0590), solar_power=(.0141, .0117)),
}
# Sheet 4 (ordinary RS) and Sheet 12 (secondary GS), in dollars.
BASE = {"RS": (15., .11856, .11195), "GS": (29., .11050, None)}
SALES_TAX_RATE = .07


def month_end(month):
    year, number = map(int, month.split("-"))
    return f"{month}-{monthrange(year, number)[1]:02d}"


COVERAGE = tuple((start + "-01", month_end(end)) for start, end, _ in WINDOWS)


def rates_for_month(month):
    for start, end, sources in WINDOWS:
        if start <= month <= end:
            return start, {**TRACKERS[start], **PHASE_AND_TAX}, sources
    raise ValueError(f"I&M Indiana filed components or allocation are unverified for {month}. "
                     "Select a supported complete calendar cycle.")
