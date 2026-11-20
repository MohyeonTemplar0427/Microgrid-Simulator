"""Choptank SOS schedule identities and gaps in complete Maryland bills."""

R = "residential_r"
C = "commercial_c"
S = "general_service_s"

PLANS = {
    R: "901 Schedule R Residential Service",
    C: "902 Schedule C Commercial Service",
    S: "903 Schedule S General Service – Small (Small Power)",
}
ELIGIBILITY = {
    R: "Primarily residential or qualifying farm load, single-phase secondary, 50 kVA or less.",
    C: "Ordinary commercial uses, single-phase secondary, 50 kVA or less.",
    S: (
        "Three-phase or qualifying larger single-phase secondary service. "
        "Check the cooperative's assignment, 12-month retention/transfer history, "
        "15-minute billing demand and any metered reactive energy. "
        "Billing demand of 100 kW or more transfers to Schedule M."
    ),
}

BOOK_2025 = (
    "https://choptankelectric.coop/sites/default/files/"
    "03.01.2025%20Choptank%20Electric%20Tariff%20and%20Terms%20and%20Conditions.pdf"
)
BOOK_2026 = "https://choptankelectric.coop/sites/default/files/Tariff%20updates%207-1-26.pdf"
PCA_POLICY = "https://choptankelectric.coop/sites/default/files/PCA-policy-0422.pdf"
RATE_PAGE = "https://choptankelectric.coop/rates"
CHOICE_PAGE = "https://www.choptankelectric.coop/customer-choice-portal"
PSC_NOTICES = "https://webpscxb.pscmaryland.com/dms/general-notices"
SOURCES = (BOOK_2025, BOOK_2026, PCA_POLICY, RATE_PAGE, CHOICE_PAGE, PSC_NOTICES)
COVERAGE = ()

BLOCKED_REASON = (
    "Choptank R/C/S complete 2025–2026 bills are unavailable. The tariff requires "
    "Maryland's utility-specific environmental surcharge. The PSC lists the FY2025, "
    "FY2026 and FY2027 assignments, but Choptank's numerical factors remain unverified. "
    "Published base rates, a residential price to compare or a known PCA cannot establish a full bill."
)
GAPS = (
    ("2025-01-01", "2025-04-30",
     "The pre-May PCA and Choptank's FY2025 environmental surcharge lack dated numerical proof."),
    ("2025-05-01", "2025-06-30",
     "Published May residential supply comparison only. FY2025 environmental surcharge and commercial PCA unresolved."),
    ("2025-07-01", "2026-04-30",
     "FY2026 environmental surcharge and a complete class-specific PCA chronology are unresolved. "
     "Residential legislative relief also requires independent bill posting and eligibility records."),
    ("2026-05-01", "2026-06-30",
     "Published non-irrigation PCA. Choptank's FY2026 environmental surcharge remains unverified."),
    ("2026-07-01", "2026-12-31",
     "Choptank's FY2027 environmental surcharge remains unverified. No future period inherits the last PCA automatically."),
)


def check_plan(plan):
    if plan not in PLANS:
        raise ValueError("Select a Choptank 901 R, 902 C or 903 S schedule.")


def rates_for_month(month, plan=R):
    check_plan(plan)
    raise ValueError(BLOCKED_REASON)


def rates_on(day, plan=R):
    return rates_for_month(str(day)[:7], plan)
