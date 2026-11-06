"""I&M Michigan MPSC 18/19 ordinary Standard Service, dated filed factors."""
BOOK_ROOT = "https://www.indianamichiganpower.com/lib/docs/ratesandtariffs/Michigan/"
BOOK_2025 = "https://qa.indianamichiganpower.com/lib/docs/ratesandtariffs/Michigan/IMMITBBk182025-06-30.pdf"
BOOK_2026 = BOOK_ROOT + "IM_MI_TB_Bk_19_2026_09_18.pdf"
MPSC_ROOT = ("https://www.michigan.gov/mpsc/-/media/Project/Websites/mpsc/"
             "consumer/rate-books/electric/indiana-michigan/")
REGULATOR_2026 = (MPSC_ROOT + "IM-18-current.pdf?hash=5958609692FDCE1A563587C0B12D3B13"
                  "&rev=7e1c95088a7f4809b7f2c2e61b007181")
CANCELED = (MPSC_ROOT + "IM-18-cancelled-A-B-C-D.pdf?hash=7F78A3FEA6034049BAC0BDAAD624F537"
            "&rev=a980c8a51e0e48c5bb34ec32cb378513")
ARCHIVE = ("https://www.michigan.gov/mpsc/consumer/electricity/data-price/electric-rate-books/"
           "mpsc-approved-indiana-michigan-power-company-electric-rate-books-and-cancelled-sheets")
SALES_TAX = "https://www.michigan.gov/taxes/business-taxes/sales-use-tax"
LIEAF_TAX = "https://www.michigan.gov/treasury/reference/letter/2013-letter-rulings/letter-ruling-2013-5"
DER = "https://www.indianamichiganpower.com/business/builders/CreateGreen-MI"
SOURCES = [BOOK_2025, BOOK_2026, REGULATOR_2026, CANCELED, ARCHIVE, SALES_TAX, LIEAF_TAX, DER]
COVERAGE = (
    ("2025-01-01", "2025-04-30"),
    ("2025-06-01", "2025-12-31"),
    ("2026-01-01", "2026-12-31"),
)
GAPS = (("2025-05-01", "2025-05-31",
         "Tax Rider D-123 states bills rendered but the revision footer starts service May 16. Allocation is unverified."),)
# D-2 and D-19, original sheets effective July 15, 2024. Dollar/kWh.
BASE = {
    "RS": dict(customer=7.58, supply_capacity=.03156, supply_non_capacity=.08675, delivery_energy=.04593),
    "GS": dict(customer=8.36, supply_capacity=.03047, supply_non_capacity=.07486, delivery_energy=.03262),
}
CODES = {"RS": ("015", "016"), "GS": ("215", "218")}


def rates_for_month(month):
    if not any(start[:7] <= month <= end[:7] for start, end in COVERAGE):
        raise ValueError(f"I&M Michigan rates or allocation are unverified for {month}. Select a supported complete calendar cycle.")
    if month < "2025-03":
        pscr = .00374
    elif month < "2026-01":
        pscr = .00358
    elif month < "2026-07":
        pscr = .00193
    else:
        pscr = -.01258
    if month < "2025-08":
        realignment = (.000615, .000567)
    elif month < "2026-08":
        realignment = (.000507, .000467)
    else:
        realignment = (.000388, .000358)
    if month < "2025-02":
        ewr = (.00387, 13.42)
    elif month < "2026-01":
        ewr = (.00628, 20.05)
    elif month < "2026-03":
        ewr = (.00529, 16.96)
    else:
        ewr = (.00836, 8.09)
    lieaf = .87 if month < "2025-09" else 1.25 if month < "2026-09" else 1.50
    # May is blocked. Keep the two ratemaking tax credits separate from sales tax.
    supply_tax = (-.002392, -.002421) if month < "2025-05" else (0., 0.)
    delivery_tax = (-.000570, -.000474) if month < "2025-05" else (0., 0.)
    return dict(pscr=pscr, rate_realignment=realignment, ewr=ewr, lieaf=lieaf,
                supply_tax_credit=supply_tax, delivery_tax_credit=delivery_tax,
                source_version=f"im-mi-{month}", source_grade="filed_books_and_regulator_cached_superseded_sheets",
                sources=SOURCES)
