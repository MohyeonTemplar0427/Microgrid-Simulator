"""Monongahela Power WV Tariff 22 dated ordinary A/B rate stacks."""
ROOT="https://www.firstenergycorp.com/content/dam/customer/"
BOOK=ROOT+"Customer%20Choice/Files/west-virginia/tariffs/WVMPRetailTariff.pdf"
RES25=ROOT+"billinserts/2025-09%20WV%20Mon%20Power%20Electric%20Rates%20Notice%20Residential.pdf"
COM25=ROOT+"billinserts/2025-09%20WV%20Mon%20Power%20Non-residential%20Rates.pdf"
RES26=ROOT+"billinserts/2026-09%20MP%20Residential%20Rates.pdf"
COM26=ROOT+"billinserts/2026-09%20MP%20Non-Resi%20Rates.pdf"
TAX="https://code.wvlegislature.gov/11-15-8/"
DER="https://www.firstenergycorp.com/feconnect/westvirginia.html"
SOURCES=[BOOK,RES25,COM25,RES26,COM26,TAX,DER]
COVERAGE=(("2025-08-01","2025-12-31"),("2026-08-01","2026-11-30"))
GAPS=(
    ("2025-01-01","2025-07-31","Earlier rider chronology and July 15 allocation are not verified."),
    ("2026-01-01","2026-07-31","January ENEC/ELG, April 5 vegetation and July 15 ECC intersections remain unverified."),
    ("2026-12-01","2026-12-31","Later tariff intersection is not verified."),
)
RATES_25={
    "A":dict(customer=6.,energy=(.11555,),normalization=-.00022,ecc=.00320,ecc2=0.,
             vegetation=.01212,effluent=.00060,renewable=.00018),
    "B":dict(customer=10.,energy=(.12808,.11403),normalization=.00067,ecc=.00240,ecc2=0.,
             vegetation=.01157,effluent=.00044,renewable=.00007),
}
RATES_26={
    "A":dict(customer=6.,energy=(.12023,),normalization=.00040,ecc=.00269,ecc2=.00030,
             vegetation=.01189,effluent=0.,renewable=0.),
    "B":dict(customer=10.,energy=(.13100,.11637),normalization=.00003,ecc=.00220,ecc2=.00025,
             vegetation=.01079,effluent=0.,renewable=0.),
}


def rates_on(month,plan):
    if "2025-08-01"<=month<="2025-12-01":
        return RATES_25[plan],(RES25,COM25),"tariff22-jul15-2025-official-rate-notice"
    if "2026-08-01"<=month<="2026-11-01":
        return RATES_26[plan],(BOOK,RES26,COM26),"tariff22-aug1-2026"
    raise ValueError("Mon Power WV tariff components or allocation are unverified for "+month[:7]+".")
