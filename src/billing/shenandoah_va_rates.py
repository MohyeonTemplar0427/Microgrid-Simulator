"""Shenandoah Valley sources; no complete dated bill intersection verified."""

ROOT = "https://www.svec.coop/"
UPLOADS = ROOT + "wp-content/uploads/"
RATE_PAGE = ROOT + "your-account/rates/"
A15 = UPLOADS + "Residential-A-15.pdf"
B16 = UPLOADS + "General-Service-B-16.pdf"
B15 = UPLOADS + "General-Service-Schedule-B-15.pdf"
STS12 = UPLOADS + "VA-Sales-and-Use-Surcharge-2026.pdf"
PCA2 = UPLOADS + "Power-Cost-Adjustment-PCA-2-June-2022.pdf"
INTERIM_ORDER = UPLOADS + "PUR-2025-00190-Order-for-Notice-and-Comment.pdf"
TERMS = UPLOADS + "Terms-and-Conditions-2026.pdf"
BILL_EXPLANATION = UPLOADS + "residential-bill-explanation.pdf"
SCC_CASE = "https://www.scc.virginia.gov/docketsearch#caseDocs/146786"
SCC_ACCEPTED = "https://www.scc.virginia.gov/docketsearch/DOCS/8c5q01%21.PDF"
SCC_APPROVED = "https://www.scc.virginia.gov/docketsearch/DOCS/8bzn01%21.PDF"
VA_CONSUMPTION = "https://law.lis.virginia.gov/vacode/title58.1/chapter29/section58.1-2900/"
PLANS = {"A-15": "Residential Service", "B-16": "General Service"}
SOURCES = [RATE_PAGE, A15, B16, B15, STS12, PCA2, INTERIM_ORDER, TERMS, BILL_EXPLANATION,
           SCC_CASE, SCC_ACCEPTED, SCC_APPROVED, VA_CONSUMPTION]
COVERAGE = ()
BLOCKED_REASON = (
    "Shenandoah Valley A/B 2025–2026 billing is unverified: complete historical "
    "base/PCA/surcharge/tax intersections have not been established. STS-12 "
    "expressly lists A-14/B-14; its applicability to A-15, B-15 and B-16 remains "
    "unverified. The statutory cooperative federal-power tax reduction requires "
    "dated utility-period evidence, not a zero-factor confirmation. Current filed "
    "bases and published monthly PCA factors alone cannot establish a complete bill."
)
GAPS = (
    ("2025-01-01", "2025-11-30", "Historical A/B bases, monthly PCA, STS and complete tax intersections remain unverified."),
    ("2025-12-01", "2026-04-30", "Published PCA and January 2026 B-15 do not supply the missing A-14/2025 STS or establish STS-12 applicability to B-15 and complete taxes."),
    ("2026-05-01", "2026-11-30", "Filed A-15/B-16 and published PCA are known; STS-12 successor applicability and complete tax/account intersections remain unverified."),
    ("2026-12-01", "2026-12-31", "December PCA and complete surcharge/tax intersections remain unverified; November's factor is not extended."),
)

# Observations only, deliberately separated from executable rates_for_month.
PCA_OBSERVATIONS = {
    "2025-12": .02818,
    **{f"2026-{m:02}": .02299 for m in range(1, 5)},
    **{f"2026-{m:02}": .03411 for m in range(5, 12)},
}


def rates_for_month(month, plan="A-15"):
    if plan not in PLANS:
        raise ValueError("Select Shenandoah Valley A-15 residential or B-16 general service.")
    raise ValueError(BLOCKED_REASON)


def rates_on(day, plan="A-15"):
    return rates_for_month(str(day)[:7], plan)
