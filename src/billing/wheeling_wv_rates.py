"""Wheeling Power WV Tariff 21: joint filed RS/SGS calendar intersections."""
ROOT = "https://www.appalachianpower.com/lib/docs/ratesandtariffs/WestVirginia/"
BOOK_2025 = ROOT + "ENG_Tariff_Sheets_Eff_11-19-25.pdf#page=1"
ORIGINAL_ENG = ROOT + "2025_Base_Case_Tariff_11-17-2025.pdf"
BOOK_2026 = ROOT + "ENEC_Tariff_Sheets_Eff_9-1-26.pdf"
TAX = "https://code.wvlegislature.gov/11-15-8/"
DER = "https://www.appalachianpower.com/business/builders/generating-equipment"
SOURCES = [BOOK_2025, ORIGINAL_ENG, BOOK_2026, TAX, DER]
COVERAGE = (("2025-10-01", "2025-11-30"), ("2026-09-01", "2026-10-31"))
GAPS = (
    ("2025-01-01", "2025-09-30", "Earlier full intersections and the September 29 allocation remain unverified."),
    ("2025-12-01", "2026-08-31", "December ENG transition and intermediate ENG/RET, base and ENEC intersections remain unverified."),
    ("2026-11-01", "2026-12-31", "Later complete component intersections have not been verified."),
)
# Both companies are explicitly named on these sheets. This is Tariff 21
# evidence, not substitution of a neighboring utility's prices. CRRC applies
# only to Appalachian Power. Wheeling uses the joint filed ENEC factor without
# adding or subtracting an Appalachian CRRC. Original ENG is cents per kWh.
OLD = {
    "RS": dict(customer=13.44, energy=(.10643, .09189, .05896), enec=.05779,
               energy_efficiency=.001826, environmental=.00309, renewable_generation=.0000313),
    "SGS": dict(customer=15.83, energy=(.060437,), enec=.05346,
                energy_efficiency=.000203, environmental=.00171, renewable_generation=.0000245),
}
NEW = {
    "RS": dict(customer=14.02, energy=(.11100, .09584, .06150), enec=.05857,
               energy_efficiency=.001826, environmental=.00309, renewable_generation=.0021386),
    "SGS": dict(customer=16.51, energy=(.063040,), enec=.05294,
                energy_efficiency=.000203, environmental=.00171, renewable_generation=.00173),
}


def rates_on(month, plan):
    if "2025-10-01" <= month <= "2025-11-01":
        return OLD[plan], BOOK_2025, "tariff21-sep29-2025-cached-filed-book", "cached_filed_tariff_compilation"
    if "2026-09-01" <= month <= "2026-10-01":
        return NEW[plan], BOOK_2026, "tariff21-sep1-2026", "dated_joint_filed_tariff_book"
    raise ValueError("Wheeling Power WV tariff components are unverified for " + month[:7] + ".")
