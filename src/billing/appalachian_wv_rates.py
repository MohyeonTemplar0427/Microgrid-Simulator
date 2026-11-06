"""Filed Appalachian Power WV Tariff 16 calendar intersections."""
ROOT = "https://www.appalachianpower.com/lib/docs/ratesandtariffs/WestVirginia/"
BOOK_2025 = ROOT + "ENG_Tariff_Sheets_Eff_11-19-25.pdf#page=1"
BOOK_2026 = ROOT + "ENEC_Tariff_Sheets_Eff_9-1-26.pdf"
TAX = "https://code.wvlegislature.gov/11-15-8/"
DER = "https://www.appalachianpower.com/business/builders/generating-equipment"
SOURCES = [BOOK_2025, BOOK_2026, TAX, DER]
COVERAGE = (("2025-10-01", "2025-10-31"), ("2026-09-01", "2026-10-31"))
GAPS = (
    ("2025-01-01", "2025-09-30", "Earlier tariff intersections and September 29 allocation are not fully reconciled."),
    ("2025-11-01", "2026-08-31", "The November CRRC true-up and intermediate ENG/RET, base-rate and ENEC intersections remain unverified."),
    ("2026-11-01", "2026-12-31", "The next CRRC true-up and later components have not been verified."),
)
# Prices in dollars. ENEC expressly includes CRRC. Never add CRRC a second time.
OLD = {
    "RS": dict(customer=13.44, energy=(.10643,.09189,.05896), enec=.05779,
               energy_efficiency=.001826, environmental=.00309, renewable_generation=.0000313),
    "SGS": dict(customer=15.83, energy=(.060437,), enec=.05346,
                energy_efficiency=.000203, environmental=.00171, renewable_generation=.0000245),
}
NEW = {
    "RS": dict(customer=14.02, energy=(.11100,.09584,.06150), enec=.05857,
               energy_efficiency=.001826, environmental=.00309, renewable_generation=.0021386),
    "SGS": dict(customer=16.51, energy=(.063040,), enec=.05294,
                energy_efficiency=.000203, environmental=.00171, renewable_generation=.00173),
}


def rates_on(month, plan):
    if month == "2025-10-01":
        return OLD[plan], BOOK_2025, "tariff16-sep29-2025-cached-filed-book", "cached_filed_tariff_compilation"
    if "2026-09-01" <= month <= "2026-10-01":
        return NEW[plan], BOOK_2026, "tariff16-sep1-2026", "dated_filed_tariff_book"
    raise ValueError("Appalachian Power WV tariff components are unverified for "+month[:7]+".")
