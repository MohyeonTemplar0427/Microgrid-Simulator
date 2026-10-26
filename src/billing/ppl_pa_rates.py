"""Dated PPL Pennsylvania fixed-price RS/GS-1 components, in dollars.

The filed residential distribution composites include riders. The ordinary
GS-1 base does not: its commercial riders are listed separately. GSC-1 and
TSC already contain MFC/GRT; do not add another merchant-function or PJM bill.
See docs/utility_sources/ppl_pa for original-document hashes and pages.
"""
from datetime import date

PLANS = ("RS", "GS-1")
COVERAGE = (("2025-01-01", "2026-10-31"),)
ROOT = "https://www.pplelectric.com/site/-/media/PPLElectric/At-Your-Service/Docs/Current-Electric-Tariff/"
SOURCES = [
    "https://www.pplelectric.com/site/More/About-Us/Electric-Rates-and-Rules/Current-Electric-Tariff",
    "https://www.pplelectric.com/site/Other-Parties/Electricity-Suppliers/Supplier-Reference/Price-Compare",
    "https://www.pplelectric.com/-/media/PPLElectric/At-Your-Service/Docs/Current-Electric-Tariff/master383-389.ashx",
    ROOT+"2025/Oct/master400-401-posted-2025-10-1.ashx",
    ROOT+"2026/Apr/master414-posted-2026-4-10.pdf",
    ROOT+"2026/October/402master4_posted-10-2-26.pdf",
    "https://www.pplelectric.com/-/media/PPLElectric/At-Your-Service/Docs/Business-Customers/PPL-EU-Business-Account-Price-Sheet_01-01-2026.pdf",
    "https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/sales-use-and-hotel-occupancy-tax",
    "https://www.pa.gov/agencies/revenue/resources/tax-rates",
    "https://revenue-pa.custhelp.com/app/answers/detail/a_id/3701",
]
# Inclusive starts; RS customer and energy are the complete filed composites.
RS_DISTRIBUTION = (
    ("2025-01-01", (15.62, .04990)),
    ("2025-04-01", (15.70, .04990)),
    ("2025-06-01", (15.70, .05049)),
    ("2025-07-01", (15.58, .05049)),
    ("2025-10-01", (15.52, .05049)),
    ("2026-01-01", (15.48, .04968)),
    ("2026-04-01", (15.50, .04968)),
    ("2026-06-01", (15.50, .04927)),
    ("2026-07-01", (15.00, .06157)),
    ("2026-10-01", (15.00, .06175)),
)
GS_DISTRIBUTION = (("2025-01-01", (22., 4.361)),
                   ("2026-07-01", (27.22, 5.923)))
# Published GSC/TSC pairs by class (residential, small C&I). PTC equals their
# sum at the published price precision; Part 2 STAS is applied separately.
SUPPLY = (
    ("2025-01-01", ((.07225, .03546), (.07458, .02988))),
    ("2025-06-01", ((.09166, .03324), (.08956, .03158))),
    ("2025-12-01", ((.09610, .03343), (.09379, .03302))),
    ("2026-06-01", ((.09804, .03343), (.09443, .03302))),
    ("2026-07-01", ((.09753, .03326), (.09445, .03303))),
)
COMMERCIAL_SMART_METER = (
    ("2025-01-01", 3.10), ("2025-04-01", 3.26),
    ("2025-07-01", 3.03), ("2025-10-01", 2.91),
    ("2026-01-01", 2.84), ("2026-04-01", 2.86),
    ("2026-07-01", 0.),
)
COMMERCIAL_EFFICIENCY = (("2025-01-01", .00243),
    ("2025-06-01", .00166), ("2026-06-01", .00071))
STORM = (("2025-01-01", (.00184, .00092)),
    ("2026-01-01", (.00190, .00094)),
    ("2026-07-01", (.00172, .00080)),
    ("2026-10-01", (.00190, .00094)))
DSIC = (("2025-01-01", .05), ("2025-03-13", .0743),
    ("2025-04-01", .075), ("2026-07-01", 0.))
TCJA = (("2025-01-01", -.08), ("2026-01-01", -.0375),
    ("2026-04-10", 0.))
STAS_DISTRIBUTION = (("2025-01-01", -.00280),
    ("2026-01-01", -.00311), ("2026-07-01", .00008))


def iso_day(day):
    key = day.isoformat() if type(day) is date else day
    if not isinstance(key, str):
        raise ValueError("Use exact ISO PPL service/bill dates.")
    try:
        valid = date.fromisoformat(key).isoformat() == key
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Use exact ISO PPL service/bill dates.")
    if not any(start <= key <= end for start, end in COVERAGE):
        raise ValueError("PPL verified complete-rate coverage is January2025–October2026; no missing/future rate substitution.")
    return key


def dated(day, versions):
    return next(value for start, value in reversed(versions) if start <= day)


def rates_on(day, plan="RS", *, bill_date=None):
    key = iso_day(day)
    rendered = key if bill_date is None else iso_day(bill_date)
    if plan not in PLANS:
        raise ValueError("Select PPL RS or ordinary single-phase GS-1 fixed default supply.")
    res = plan == "RS"
    customer, energy_or_demand = dated(key, RS_DISTRIBUTION if res else GS_DISTRIBUTION)
    generation, transmission = dated(key, SUPPLY)[not res]
    return dict(customer=customer,
        distribution_energy=energy_or_demand if res else 0.,
        distribution_demand=0. if res else energy_or_demand,
        generation=generation, transmission=transmission,
        # These commercial riders are already embedded in RS composites.
        smart_meter=0. if res else dated(key, COMMERCIAL_SMART_METER),
        competitive_enhancement=0. if res or key >= "2026-07-01" else -.01,
        energy_efficiency=0. if res else dated(key, COMMERCIAL_EFFICIENCY),
        storm=0. if res else dated(key, STORM)[1],
        dsic=dated(rendered, DSIC), tcja=dated(rendered, TCJA),
        stas_distribution=dated(key, STAS_DISTRIBUTION),
        stas_supply=.00001,
        # TCJA excludes automatic riders, even when bundled on RS's line.
        tcja_base_customer=14.09 if res and key < "2026-07-01" else customer,
        tcja_base_energy=(.03534 if key < "2026-07-01" else .04782) if res else 0.,
        tcja_base_demand=0. if res else energy_or_demand,
        base_version="2016 base plus dated riders" if key < "2026-07-01" else "July1,2026 base",
        supply_version=next(start for start, _ in reversed(SUPPLY) if start <= key),
        distribution_version=next(start for start, _ in reversed(RS_DISTRIBUTION if res else GS_DISTRIBUTION) if start <= key),
        bill_date=rendered)
