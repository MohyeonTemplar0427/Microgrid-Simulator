"""NOVEC's independently sourced complete-calendar retail intersections."""
from calendar import monthrange
from datetime import date

ROOT = "https://www.novec.com/"
R1 = ROOT + "About_NOVEC/upload/NOVEC_RateRebal-010124.pdf"
SC1 = ROOT + "About_NOVEC/upload/Small-Commercial-Service-SC-1-3-22-23.pdf"
JAN25 = ROOT + "About_NOVEC/upload/2025-JanFeb-WC-nobleed-compressed.pdf"
JUL25 = ROOT + "About_NOVEC/upload/2025-July-WC_nobleed.pdf"
PCA_CURRENT = ROOT + "About_NOVEC/PCA-Power-Cost-Adjustment.cfm"
TERMS = ROOT + "About_NOVEC/upload/NOVEC-Terms-and-Conditions-101624.pdf"
TAX = "https://law.lis.virginia.gov/vacode/title58.1/chapter29/section58.1-2900/"
LEVY_AUTHORITY = "https://law.lis.virginia.gov/vacode/title58.1/chapter29/section58.1-2902/"
LEVY = "https://www.scc.virginia.gov/regulated-industries/public-taxation/taxes-and-fees/"
OLD_LEVY = "https://salemva.gov/DocumentCenter/View/2607/Special-Regulatory-Tax-State-PDF"
PWC25 = "https://www.pwcva.gov/assets/2024-07/FINAL%20Adopted%20Revenue%20FY25-FY29%20.pdf"
PWC26 = "https://www.pwcva.gov/assets/2025-06/Adopted%20Revenue%20FY26-FY30_Final%20Draft_V2_6.25.2025.pdf"
SOURCES = [R1, SC1, JAN25, JUL25, PCA_CURRENT, TERMS, TAX, LEVY_AUTHORITY, LEVY, OLD_LEVY, PWC25, PWC26]
BASE = {
    "R-1": dict(customer=21.30, delivery_energy=.01348, supply_energy=.09731),
    "SC-1": dict(customer=26.78, delivery_energy=.02064, supply_energy=.09242),
}
COVERAGE = (("2025-01-01", "2025-12-31"),)
GAPS = (
    ("2026-01-01", "2026-10-31", "Original 2026 PCA factor and its dated applicability have not been recovered from a primary source."),
    ("2026-11-01", "2026-12-31", "The November PCA notice does not supply the exact revised R-1 and SC-1 base-rate vectors."),
)


def rates_for_month(month):
    """Never turn the current PCA web page into unsupported historical rates."""
    try:
        value = date.fromisoformat(month)
    except (TypeError, ValueError):
        raise ValueError("NOVEC requires an ISO calendar-month start.") from None
    if value.day != 1 or value.year != 2025:
        raise ValueError(f"NOVEC complete component coverage is unverified for {str(month)[:7]}.")
    pca = -.008 if value.month < 7 else .002
    regulatory = (.000165, .000110, .000077) if value.month < 8 else (.000165,)*3
    return dict(pca=pca, regulatory_tax=regulatory,
                source_version=f"novec-2025-{'jan' if value.month < 7 else 'jul' if value.month < 8 else 'aug'}",
                source_grade="official_filed_tariffs_notices_and_state_county_tax_sources",
                sources=[R1, SC1, JAN25 if value.month < 7 else JUL25, TAX,
                         OLD_LEVY if value.month < 8 else LEVY, LEVY_AUTHORITY, PWC25, PWC26],
                month_end=value.replace(day=monthrange(value.year, value.month)[1]).isoformat())
