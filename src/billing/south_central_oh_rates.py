"""South Central Power source boundaries, without executable monthly rates.

The board-approved R/SGS distribution sheets and a dated example invoice are
not a monthly generation/transmission factor history. Keep the observations
separate from bill pricing until complete dated intersections are established.
"""

ROOT = "https://www.southcentralpower.com/"
UPLOADS = ROOT + "wp-content/uploads/"
RATE_PAGE = ROOT + "your-account/member-rates/"
DOCUMENTS = ROOT + "about-us/company-documents/"
R_2024 = UPLOADS + "Rate-Schedule-Residential-04.01.24.pdf"
SGS_2024 = UPLOADS + "Rate-Schedule-SGS-04.2024.pdf"
R_2025 = UPLOADS + "Rate-Schedule-Residential-04.01.2025.pdf"
SGS_2025 = UPLOADS + "Rate-Schedule-SGS-04.01.2025.pdf"
R_2026 = UPLOADS + "Rate-Schedule-Residential-04.01.2026-Approved-3-17-2026.pdf"
SGS_2026 = UPLOADS + "Rate-Schedule-SGS-04.01.2026-Approved-3-17-2026.pdf"
RIDER_A = UPLOADS + "Rider-A-1.pdf"
RIDER_B_2025 = UPLOADS + "Rider-B-effective-2025.pdf"
SAMPLE_BILL = UPLOADS + "Residential-Bill-Example-2026.pdf"
BILL_EXPLANATION = ROOT + "your-account/payment-billing/understanding-your-bill/"
TRANSPARENCY = ROOT + "news-releases/providing-greater-billing-transparency/"
NET_BILLING = UPLOADS + "Rate-Schedule-Net-Billing-Effective-03012022-1.pdf"
INTERCONNECTION = ROOT + "faqs/what-is-south-central-power-companys-interconnection-process/"
ENERGY_MIX = ROOT + "services/energy-mix/"
OHIO_EXCISE = "https://codes.ohio.gov/ohio-revised-code/section-5727.81"
OHIO_SALES = "https://codes.ohio.gov/ohio-revised-code/section-5739.02"
SOURCES = [RATE_PAGE, DOCUMENTS, R_2024, SGS_2024, R_2025, SGS_2025,
           R_2026, SGS_2026, RIDER_A, RIDER_B_2025, SAMPLE_BILL,
           BILL_EXPLANATION, TRANSPARENCY, NET_BILLING, INTERCONNECTION,
           ENERGY_MIX, OHIO_EXCISE, OHIO_SALES]

PLANS = {"R": "Residential Service", "SGS": "Small General Service"}
COVERAGE = ()
BLOCKED_REASON = (
    "South Central Power R/SGS 2025–2026 billing is unverified: dated monthly "
    "Rider B generation/transmission factors and their bill-cycle applicability, "
    "plus complete Rider A/locality/account intersections, have not been "
    "established. Published base sheets and the June 2, 2026 residential sample "
    "invoice do not establish prices for arbitrary cycles or SGS accounts."
)
GAPS = (("2025-01-01", "2026-12-31", BLOCKED_REASON),)

# Source observations only. No consumer/import bill can be obtained from this
# data: monthly Rider B, Rider A, and independent account facts remain missing.
BASE_SCHEDULE_OBSERVATIONS = (
    dict(effective="2024-04-01", approved="2023-12-19", distribution_per_kwh=.026,
         customer={"R": 27., "SGS": 38.}, sources=[R_2024, SGS_2024]),
    dict(effective="2025-04-01", approved="2024-12-17", distribution_per_kwh=.026,
         customer={"R": 29., "SGS": 41.}, sources=[R_2025, SGS_2025]),
    dict(effective="2026-04-01", approved="2026-03-17", distribution_per_kwh=.026,
         customer={"R": 34., "SGS": 48.}, sources=[R_2026, SGS_2026]),
)


def rates_for_month(month, plan="R"):
    """Reject missing intersections, including a fully confirmed sample month."""
    if plan not in PLANS:
        raise ValueError("Select South Central Power R residential or SGS small general service.")
    raise ValueError(BLOCKED_REASON)


def rates_on(day, plan="R"):
    return rates_for_month(str(day)[:7], plan)
