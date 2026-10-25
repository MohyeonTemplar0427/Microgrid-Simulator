"""Wisconsin Electric ordinary bundled prices, never wholesale MISO prices.

Amounts are dollars. Effective dates are service dates; taxes use bill date.
Evidence and the deliberately bounded account scope are documented alongside
selected source extracts in docs/utility_sources/we_energies_wi/.
"""
from datetime import date

PLANS = ("Rg1", "Rg2", "Cg1", "Cg6")
THROUGH = "2026-10-24"
COVERAGE = (("2025-01-01", "2025-06-30"), ("2026-01-01", "2026-09-30"))
PROVISIONAL_COVERAGE = (("2025-07-01", "2025-12-31"),)
PROVISIONAL_MODEL = "we_energies_wi_2025_provisional_v1"
SOURCES = [
    "https://www.we-energies.com/pdfs/etariffs/wisconsin/2025-rates-brochures.pdf",
    "https://www.we-energies.com/olb/25/2025-01-we-electric-rates.pdf",
    "https://www.we-energies.com/olb/26/2026-01-we-electric-rates.pdf",
    "https://www.we-energies.com/pdfs/etariffs/wisconsin/elecrateswi.pdf",
    "https://www.we-energies.com/payment-bill/wi-low-income",
    "https://www.we-energies.com/payment-bill/reading-bill",
    "https://docs.legis.wisconsin.gov/statutes/statutes/995/20",
    "https://docs.legis.wisconsin.gov/code/admin_code/tax/11/vii/57",
    "https://www.revenue.wi.gov/Pages/FAQS/pcs-taxrates.aspx",
    "https://news.we-energies.com/refunds-expected-for-we-energies-electric-customers-from-fuel-cost-adjustment/",
    "https://s22.q4cdn.com/994559668/files/doc_downloads/2025/June-2025-Monthly-Servicers-Certificate.pdf",
    "https://s22.q4cdn.com/994559668/files/doc_downloads/2025/07/May-2025-Monthly-Servicers-Certificate.pdf",
    "https://investor.wecenergygroup.com/investors/financial-info/WEPCO-Environmental-Trust-Financing/default.aspx",
    "https://www.we-energies.com/payment-bill/pdf/we-energies-sample-bill.pdf",
    "https://www.sec.gov/Archives/edgar/data/1840327/000110465921062220/tm213205-13_sf1a.htm",
]
# Flat/on-peak, off-peak. All four customer charges include one meter.
BASE = {
    2025: {"Rg1": (.18325, .18325), "Rg2": (.27006, .10387),
           "Cg1": (.16659, .16659), "Cg6": (.25388, .09765)},
    2026: {"Rg1": (.19342, .19342), "Rg2": (.30084, .10028),
           "Cg1": (.17621, .17621), "Cg6": (.29475, .09825)},
}
# Inclusive windows, residential / small secondary non-demand C&I.
ECC = (
    ("2025-01-01", "2025-05-31", (.00056, .00052), "January2025 brochure; May2025 servicer certificate"),
    # A certificate proves the billed month, not six subsequent months.
    ("2025-06-01", "2025-06-30", (.00055, .00050), "June2025 servicer certificate"),
    ("2026-01-01", "2026-05-31", (.00052, .00047), "January2026 brochure; superseded by sheet20.2 revision22 June2026"),
    ("2026-06-01", "2026-09-30", (.00054, .00048), "sheet20.2 revision22, June1,2026"),
)

# User-authorized study assumption, deliberately outside verified ECC history.
# Retain June's actual class factors for the six missing months rather than
# assert that January2026's lower factor was effective in December2025.
PROVISIONAL_ASSUMPTIONS = [dict(
    id="WE25-ECC-JUNE-CARRY-FORWARD", kind="rate", start="2025-07-01", end="2025-12-31", basis="service_date",
    components=["environmental_control", "state_low_income_assistance", "wisconsin_sales_tax"],
    assumed_values=dict(residential_usd_per_kwh=.00055, commercial_non_demand_usd_per_kwh=.00050,
        reference_service_month="2025-06", policy="carry_forward_last_verified_month"),
    explanation="Provisional study assumption: carry June2025's verified residential0.00055USD/kWh and smallC&I0.00050USD/kWh ECC through July–December2025. Actual filed factors/effective dates, including any midyear/nonroutine change, remain unverified. January2026 factors are not applied backward. Base energy, TOU, fuel and September's fuel refund retain their verified rules. State-assistance fee and sales-tax amounts depend on the assumed ECC; their rules remain verified.",
    sources=[SOURCES[10]])]


def service_rates(day, plan, *, mode="verified"):
    key = day.isoformat() if isinstance(day, date) else str(day)
    try:
        d = date.fromisoformat(key)
        if d.isoformat() != key:
            raise ValueError
    except ValueError as exc:
        raise ValueError("Use exact ISO Wisconsin service dates.") from exc
    if plan not in PLANS:
        raise ValueError("Select Wisconsin Electric Rg1/Rg2/Cg1/Cg6 ordinary service.")
    if mode not in ("verified", "provisional_2025"):
        raise ValueError("Choose verified or explicitly accepted provisional_2025 Wisconsin Electric rates.")
    verified = any(s <= key <= e for s, e in COVERAGE)
    provisional = not verified and mode == "provisional_2025" and any(s <= key <= e for s, e in PROVISIONAL_COVERAGE)
    if not verified and not provisional:
        raise ValueError("Wisconsin Electric complete-rate coverage is January–June2025 and January–September2026; July–December2025 ECC unverified, no extrapolation.")
    matches = [row for row in ECC if row[0] <= key <= row[1]]
    if provisional:
        start, end = PROVISIONAL_COVERAGE[0]
        factors = (.00055, .00050)
        reference = PROVISIONAL_ASSUMPTIONS[0]["id"]+": assumed June2025 class factors; not verified filed history"
    elif len(matches) != 1:
        raise ValueError("Wisconsin Electric requires one verified dated environmental control factor.")
    else:
        start, end, factors, reference = matches[0]
    res = plan in ("Rg1", "Rg2")
    # September's refund is verified independently; provisional ECC never
    # suppresses it or turns it into a guessed fuel/base-rate component.
    refund = (-.04054 if res else -.03620) if d.year == 2025 and d.month == 9 else 0.
    return dict(customer_daily=.49315, energy=BASE[d.year][plan],
        fuel=0. if d.year == 2025 else .00199, fuel_reconciliation=refund,
        environmental_control=factors[0 if res else 1], assistance_cap=3.15 if res else 10.66,
        base_version=f"{d.year}-01-01 (5-UR-111)",
        fuel_version="2025-01-01 brochure" if d.year == 2025 else "2026-01-01 sheet19 revision40",
        rider_version=f"environmental_control:{start}; fuel_refund:{'2025-09' if refund else 'none'}",
        rider_versions=dict(environmental_control=dict(start=start, end=end, reference=reference,
                evidence_status="provisional" if provisional else "verified"),
            fuel_reconciliation=dict(start="2025-09-01", end="2025-09-30", reference=SOURCES[9]) if refund else None),
        rate_evidence_status="provisional" if provisional else "verified")
