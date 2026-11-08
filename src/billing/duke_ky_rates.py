"""Duke Kentucky RS and bounded DS: complete verified component intersections.

Rates are dollars/kWh and decimal revenue factors. Base/DSMR service clocks
and named utility billing-month FAC/ESM/PSM clocks are kept separate. Nothing
here extends the verified monthly factors into a missing period.
"""
BOOK = "https://psc.ky.gov/tariffs/electric/Duke%20Energy%20Kentucky/Tariff.pdf"
ARCHIVE = "https://psc.ky.gov/tariffs/electric/Duke%20Energy%20Kentucky/Cancelled%20Tariff%20Pages/"
FAC_2025 = "https://psc.ky.gov/PSCFAC/duke%20energy%20kentucky/2025_DEK.pdf"
FAC_2026 = "https://psc.ky.gov/PSCFAC/duke%20energy%20kentucky/2026_DEK.pdf"
ESM_ROOT = "https://psc.ky.gov/pscecf/2026-00234/charlene.barlow%40duke-energy.com/10232026023518/"
ESM_SUMMARY = ESM_ROOT + "STAFF-DR-01-001_-_Attachment_01_%28a%29%28b%29.xlsx"
SCHOOL = "https://apps.legislature.ky.gov/lrc/publications/ResearchReports/RR504.pdf"
SALES_TAX = "https://revenue.ky.gov/Business/Sales-Use-Tax/Pages/default.aspx"
DOMICILE = "https://revenue.ky.gov/Forms/51A380%20%281-3-23%29.pdf"
GROSS_RECEIPTS = "https://apps.legislature.ky.gov/law/statutes/statute.aspx?id=58185"
SCHOOL_2025 = "https://education.ky.gov/districts/SEEK/Documents/2024-2025%20Local%20District%20Tax%20Levies%205%2030%2025.xlsx"
SCHOOL_2026 = "https://education.ky.gov/districts/SEEK/Documents/Tax%20Rate%20Levied%20as%20of%20April%2030%202026.xlsx"
SCHOOL_2027 = "https://education.ky.gov/districts/SEEK/Documents/2026-2027%20Local%20District%20Tax%20Levies.xlsx"
SOURCES = [BOOK, ARCHIVE, FAC_2025, FAC_2026, ESM_SUMMARY, SCHOOL,
           SCHOOL_2025, SCHOOL_2026, SCHOOL_2027, SALES_TAX, DOMICILE, GROSS_RECEIPTS]
COVERAGE = (("2025-04-01", "2025-06-30"), ("2026-04-01", "2026-06-30"))
GAPS = (
    ("2025-01-01", "2025-03-31", "Earlier complete stacks and March DSMR transition are outside the verified implementation."),
    ("2025-07-01", "2025-10-31", "July interim-rate/refund and October base-rate transition allocations are unverified."),
    ("2025-11-01", "2026-03-31", "November/December/January base revisions and February DSMR transition stacks are not enabled."),
    ("2026-07-01", "2026-12-31", "Later ESM months, September fuel roll-in and later component intersections are not verified."),
)

# Utility billing month: FAC, residential ESM, non-residential ESM, signed PSM.
# PSM parentheses in filed sheets mean a charge; unparenthesized means credit.
# FAC and ESM expense month is TWO months before the named billing month.
MONTHLY = {
    "2025-05": (.004559, .0351, .0548, .001508),
    "2025-06": (-.006385, .0149, .0234, .000806),
    "2025-07": (.000627, .0543, .0855, .000806),
    "2026-05": (.006094, -.0039, -.0060, -.005893),
    "2026-06": (-.009567, -.0191, -.0288, -.003992),
    "2026-07": (-.001945, -.0097, -.0146, -.003992),
}
BILL_DATES = {"2025-05": "2025-05-01", "2025-06": "2025-06-02", "2025-07": "2025-07-01",
              "2026-05": "2026-05-01", "2026-06": "2026-06-01", "2026-07": "2026-07-01"}
ESM_ATTACHMENTS = {"2025-05": (13, "xlsx"), "2025-06": (14, "xlsx"), "2025-07": (15, "xlsx"),
                   "2026-05": (25, "xlsm"), "2026-06": (26, "xlsm"), "2026-07": (27, "xlsm")}


def rates_for_cycle(service_month, billing_month=None):
    if not isinstance(service_month, str) or len(service_month) != 7:
        raise ValueError("Duke Kentucky service month must be YYYY-MM.")
    try:
        year, month = map(int, service_month.split("-"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Duke Kentucky service month must be YYYY-MM.") from exc
    if not 1 <= month <= 12 or service_month != f"{year:04}-{month:02}":
        raise ValueError("Duke Kentucky service month must be YYYY-MM.")
    if not any(a[:7] <= service_month <= b[:7] for a, b in COVERAGE):
        raise ValueError(f"Duke Kentucky complete component intersection is unverified for service {service_month}.")
    following = f"{year+(month == 12):04}-{month%12+1:02}"
    billing_month = following if billing_month is None else billing_month
    if billing_month != following or billing_month not in MONTHLY:
        raise ValueError("Duke Kentucky requires an independently confirmed following utility billing month with verified factors.")
    fac, rs_es, ds_es, psm = MONTHLY[billing_month]
    new = service_month.startswith("2026-")
    attachment, extension = ESM_ATTACHMENTS[billing_month]
    esm_source = ESM_ROOT+f"STAFF-DR-01-001_-_Attachment_{attachment:02}.{extension}"
    return dict(customer=(14.75, 15.) if new else (13., 15.),
                energy=(.126104, .126995) if new else (.111639, .114788),
                dsm=(.005514, .001154) if new else (.002418, .003409),
                assistance_rs=.30, embedded_fuel=.033780, fac=fac,
                environmental=(rs_es, ds_es), profit_sharing=psm,
                school_tax=.03, sales_tax=.06, bill_date=BILL_DATES[billing_month],
                base_effective_start="2026-01-02" if new else "2024-10-01",
                dsm_effective_start="2026-04-01" if new else "2025-03-03",
                source_version=f"duke-ky-service-{service_month}-billing-{billing_month}",
                source_grade="filed_tariffs_and_official_monthly_factors",
                sources=[BOOK, ARCHIVE, FAC_2026 if new else FAC_2025, esm_source,
                         ESM_SUMMARY, SCHOOL, SCHOOL_2025, SCHOOL_2026, SCHOOL_2027,
                         SALES_TAX, DOMICILE, GROSS_RECEIPTS])


def rates_for_month(month):
    return rates_for_cycle(month)
