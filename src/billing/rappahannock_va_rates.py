"""REC source boundaries: no complete 2025–2026 bill stack is enabled."""
ROOT = "https://myrec.coop/"
A1 = ROOT + "sites/default/files/documents/Electric%20Rates/Residential%20A-1%20Rate.pdf"
B1 = ROOT + "sites/default/files/documents/Electric%20Rates/SGS%20B-1.pdf"
PCA25 = ROOT + "sites/default/files/documents/Electric%20Rates/PCA-6-1-2025-stamped.pdf"
PCA26 = ROOT + "sites/default/files/documents/PCA-5-1-2026-stamped.pdf"
DR25 = ROOT + "sites/default/files/documents/Electric%20Rates/2025%20DR%20Rider%20Factor%20Sheet.pdf"
DR26 = ROOT + "sites/default/files/2025-12/DR-Rider-Factor-Sheet_1-1-2026_stamped.pdf"
EXHIBIT = ROOT + "sites/default/files/documents/Electric%20Rates/Exhibit%20of%20Applicable%20Riders.pdf"
TERMS = ROOT + "sites/default/files/documents/Governance%20Center/Terms%20and%20Conditions-8-27-2024.pdf"
TAX = "https://law.lis.virginia.gov/vacode/title58.1/chapter29/section58.1-2900/"
LEVY = "https://www.scc.virginia.gov/regulated-industries/public-taxation/taxes-and-fees/"
OLD_LEVY = "https://salemva.gov/DocumentCenter/View/2607/Special-Regulatory-Tax-State-PDF"
COUNTY = "https://library.municode.com/va/rockingham_county/codes/code_of_ordinances?nodeId=CH7FITA_ARTVIUTSETA"
SOURCES = [A1, B1, PCA25, PCA26, DR25, DR26, EXHIBIT, TERMS, TAX, LEVY, OLD_LEVY, COUNTY]
PLANS = ("A-1", "B-1")
COVERAGE = ()
BLOCKED_REASON = (
    "REC A-1/B-1 complete billing is unverified: the mandatory cooperative-period "
    "federal-power consumption-tax adjustment or documented nonapplicability has "
    "not been established. A no-reduction checkbox cannot set this factor to zero. "
    "Rockingham's published residential tax decimal also needs reconciliation. "
    "Known base/PCA/DR components are not an executable full bill."
)
GAPS = (("2025-01-01", "2026-12-31", BLOCKED_REASON),)


def rates_for_month(month, plan="A-1"):
    if plan not in PLANS:
        raise ValueError("Select REC A-1 residential or B-1 small general service.")
    raise ValueError(BLOCKED_REASON)


def rates_on(day, plan="A-1"):
    return rates_for_month(str(day)[:7], plan)
