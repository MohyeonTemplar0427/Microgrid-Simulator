"""Potomac Edison WV Tariff 3: independently transcribed R/G intersections."""
ROOT = "https://www.firstenergycorp.com/content/dam/customer/"
BOOK = ROOT + "Customer%20Choice/Files/west-virginia/tariffs/WVPERetailTariff.pdf"
RES25 = ROOT + "billinserts/2025-09%20WV%20Potomac%20Edison%20Electric%20Rates%20Notice%20Residential.pdf"
COM25 = ROOT + "billinserts/2025-09%20WV%20Potomac%20Edison%20Non-residential%20Rates.pdf"
RES26 = ROOT + "billinserts/2026-09%20PEWV%20Residential%20Rates.pdf"
COM26 = ROOT + "billinserts/2026-09%20PEWV%20Non-Res%20Rates.pdf"
TAX = "https://code.wvlegislature.gov/11-15-8/"
DER = "https://www.firstenergycorp.com/feconnect/westvirginia.html"
SOURCES = [BOOK, RES25, COM25, RES26, COM26, TAX, DER]
COVERAGE = (("2025-08-01", "2025-12-31"), ("2026-08-01", "2026-11-30"))
GAPS = (
    ("2025-01-01", "2025-07-31", "Earlier full component intersections and July 15 transition allocation are unverified."),
    ("2026-01-01", "2026-07-31", "Intermediate fuel/base, vegetation and July 15 ECC intersections are unverified."),
    ("2026-12-01", "2026-12-31", "The later full component intersection has not been verified."),
)
# Dollars per kWh except the fixed customer charge. Do not import Mon Power
# factors: aggregate example bills coincide, but its ECC/normalization differ.
RATES_25 = {
    "R": dict(customer=6., energy=(.11555,), normalization=-.00066, ecc=.00364, ecc2=0.,
              vegetation=.01212, effluent=.00060, renewable=.00018),
    "G": dict(customer=10., energy=(.12808, .11403), normalization=.00029, ecc=.00278, ecc2=0.,
              vegetation=.01157, effluent=.00044, renewable=.00007),
}
RATES_26 = {
    "R": dict(customer=6., energy=(.12023,), normalization=.00028, ecc=.00280, ecc2=.00031,
              vegetation=.01189, effluent=0., renewable=0.),
    "G": dict(customer=10., energy=(.13100, .11637), normalization=-.00006, ecc=.00229, ecc2=.00025,
              vegetation=.01079, effluent=0., renewable=0.),
}


def rates_on(month, plan):
    if "2025-08-01" <= month <= "2025-12-01":
        return RATES_25[plan], (RES25, COM25), "tariff3-jul15-2025-official-notice"
    if "2026-08-01" <= month <= "2026-11-01":
        return RATES_26[plan], (BOOK, RES26, COM26), "tariff3-aug1-2026"
    raise ValueError("Potomac Edison WV tariff components or allocation are unverified for " + month[:7] + ".")
