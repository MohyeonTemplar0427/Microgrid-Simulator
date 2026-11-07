"""SMECO source boundaries; no complete approved 2025–2026 bill stack yet.

Published supply-only price-to-compare history and pending monthly factors are
not executable tariffs. Keep this module fail-closed until the missing filed
monthly PCA/BSA and dated tax/delivery intersections have been reconciled.
"""

ROOT = "https://www.smeco.coop/"
BOOK = ROOT + "wp-content/uploads/SMECO-Tariff-Rate-Schedules.pdf"
RATE_PAGE = ROOT + "my-account/general-information/rates-fees/"
CHOICE_PAGE = ROOT + "my-account/customer-choice/"
BSA = ROOT + "wp-content/uploads/RiderBSABillStabilizationAdjustment.pdf"
EMC = ROOT + "wp-content/uploads/RIDER-EMC.pdf"
USP = ROOT + "wp-content/uploads/RIDER-USP-1.pdf"
RELIEF = ROOT + "relief/"
PSC_BSA_CASE = "https://webpscxb.pscmaryland.com/DMS/case/9456"
PJM_REGIONS = "https://emergencyprocedures.pjm.com/ep/pages/regions.jsf"
SOURCES = [BOOK, RATE_PAGE, CHOICE_PAGE, BSA, EMC, USP, RELIEF, PSC_BSA_CASE, PJM_REGIONS]
PLANS = ("R", "GSS")
COVERAGE = ()
BLOCKED_REASON = (
    "SMECO R/GSS 2025–2026 billing is unverified: approved complete monthly "
    "PCA/BSA, dated delivery/rider/tax intersections and applicable residential "
    "credits have not been reconciled. Supply-only PTC history, current base "
    "sheets and explicitly pending monthly factors do not establish a complete bill."
)
GAPS = (("2025-01-01", "2026-12-31", BLOCKED_REASON),)


def rates_for_month(month, plan="R"):
    if plan not in PLANS:
        raise ValueError("Select SMECO R residential or GSS small general service SOS.")
    raise ValueError(BLOCKED_REASON)


def rates_on(day, plan="R"):
    return rates_for_month(str(day)[:7], plan)
