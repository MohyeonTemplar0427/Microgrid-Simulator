"""Interstate Power & Light Iowa retail prices and explicit component clocks.

Only intersections of recovered component windows are executable. The EAC
summary is a billed composite; its included RCE must never be charged twice.
Source extracts and retrieval limitations live in docs/utility_sources/alliant_ia.
"""
from datetime import date

PLANS = ("400", "407", "427", "600", "607")
THROUGH = "2026-10-25"
COVERAGE = (("2025-01-01", "2025-12-31"), ("2026-06-01", "2026-10-31"))
ROOT = "https://www.alliantenergy.com/-/media/alliant/documents/accountandbilling/ratesandtariffs/iowaelectricrates/"
SOURCES = [
    "https://www.alliantenergy.com/account-and-billing/understanding-bill-rates/iowa/electric",
    ROOT+"electricresidentialserviceusage.pdf",
    ROOT+"electricgeneralserviceusage.pdf",
    ROOT+"eacsummary.pdf",
    ROOT+"ridereecrenergyefficiencycostrecovery.pdf",
    ROOT+"riderdrcrdemandresponsecostrecovery.pdf",
    ROOT+"riderrtsregionaltransmissionserviceclause.pdf",
    ROOT+"ridertaxtaxadjustmentclause.pdf",
    ROOT+"ridertbrtaxbenefitrider.pdf",
    ROOT+"riderrceratecaseexpense.pdf",
    ROOT+"section2definitions.pdf",
    ROOT+"section7billingandpayingforservice.pdf",
    ROOT+"section16cogeneratorssmallpowerproducersalternateenergyproducerssmallhydroproduc.pdf",
    "https://revenue.iowa.gov/taxes/tax-guidance/sales-use-excise-tax/sales-use-tax-guide",
    "https://revenue.iowa.gov/taxes/frequently-asked-questions/local-option-sales-tax-lost",
    "https://www.linncountyiowa.gov/1593/Local-Option-Sales-Tax-Referendum",
    "https://www.alliantenergy.com/ways-to-save/time-of-day-iowa",
    ROOT+"inflowoutflowtariff.pdf",
    "https://web.archive.org/web/20250907174848id_/https://www.alliantenergy.com/account-and-billing/understanding-bill-rates/iowa/electric/rts",
    "https://www.alliantenergy.com/account-and-billing/understanding-bill-rates/iowa/outlook",
    "https://www.alliantenergy.com/-/media/alliant/documents/accountandbilling/billguides/iowaresidentialbillguide.pdf",
    "https://www.alliantenergy.com/-/media/alliant/documents/accountandbilling/billguides/iowasummersaverbillguide.pdf",
    "https://www.alliantenergy.com/-/media/alliant/documents/accountandbilling/billguides/iowanightowlbillguide.pdf",
    "https://www.alliantenergy.com/-/media/alliant/documents/accountandbilling/billguides/iowasmallbusinessbillguide.pdf",
    "https://www.boonegov.com/egov/apps/document/center.egov?id=2270&view=item",
]
# Filed October1,2024 base prices. Winter/off, summer/off, summer/on,
# winter/super-off, summer/super-off. None means the period is not offered.
BASE = {
    "400": (.09992, .13398, None, None, None),
    "407": (.09992, .11134, .22269, None, None),
    "427": (.11657, .12293, .24585, .05829, .06146),
    "600": (.12041, .16513, None, None, None),
    "607": (.12041, .14116, .28232, None, None),
}
# Actual published billing-month composite, all selected ordinary classes.
# Blank November/December2026 entries are deliberately absent.
EAC = {
    2025: (.01160, .01020, .00020, -.01100, -.01050, .00180,
           .01240, .01810, .01976, .01496, .00666, -.00034),
    2026: (.00066, .00166, .00796, -.00254, -.00994, -.00334,
           .00656, .01076, .01616, .01676),
}
RIDER_HISTORY = {
    "energy_efficiency": (
        ("2025-01-01", "2025-06-16", (.0009, .0014), "Sheet60 substitute revision29; factors applied August1,2024; successor applies June17,2025"),
        ("2025-06-17", "2025-12-31", (.0006, .0032), "Sheet60 substitute revision30; factors applied June17,2025"),
        ("2026-06-01", "2026-10-31", (.0013, .0038), "Sheet60 revision31; factors applied June1,2026"),
    ),
    "demand_response": (
        ("2025-01-01", "2025-06-16", (.0031, .0023), "Bounded2025 historical class-factor reconstruction: official400/407/427 and600 bill guides, continuous municipal600 bill evidence, and filed revision7 replacing substitute revision6 June17; original sixth-sheet start not asserted"),
        ("2025-06-17", "2025-12-31", (.0048, .0028), "Sheet60.1 substitute revision7; factors applied June17,2025"),
        ("2026-06-01", "2026-10-31", (.0042, .0023), "Sheet60.1 revision8; factors applied June1,2026"),
    ),
    "regional_transmission": (
        ("2025-01-01", "2025-08-31", (.04077, .03217), "Sheet86 substitute revision23; factors applied January1,2025; official archived utility history confirms January–August"),
        ("2025-09-01", "2025-12-31", (.04055, .03196), "Official archived utility RTS history; factors applied September1,2025, including ROE refund"),
        ("2026-02-06", "2026-07-31", (.04494, .03568), "Sheet86 third substitute revision25; factors applied February6,2026"),
        ("2026-08-01", "2026-10-31", (.04456, .03539), "Sheet86 revision26; factors applied August1,2026"),
    ),
}


def _rider(component, day, residential):
    matches = [row for row in RIDER_HISTORY[component] if row[0] <= day <= row[1]]
    if len(matches) != 1:
        raise ValueError(f"Alliant Iowa {component} needs one verified dated class factor on {day}.")
    start, end, values, source = matches[0]
    return values[not residential], dict(start=start, end=end, reference=source)


def tax_benefit(day, residential):
    """Separate TBR credit, absent from the historical EAC's dashed column C.

    Its twelve-month application ends October1,2025. This helper does not
    establish executable coverage or allocation for shifted meter cycles.
    """
    return (-.00789 if residential else -.00592) if "2024-10-01" <= day < "2025-10-01" else 0.


def service_rates(day, plan, *, billing_month=None):
    key = day.isoformat() if type(day) is date else day
    try:
        if not isinstance(key, str) or date.fromisoformat(key).isoformat() != key:
            raise ValueError
    except ValueError as exc:
        raise ValueError("Use exact ISO Alliant Iowa service dates.") from exc
    if plan not in PLANS:
        raise ValueError("Select Alliant Iowa 400/407/427 residential or 600/607 general service.")
    month = key[:7]+"-01" if billing_month is None else billing_month
    if month != key[:7]+"-01":
        raise ValueError("Alliant Iowa first scope aligns complete calendar service and designated billing month; no inferred crossing allocation.")
    if not any(start <= key <= end for start, end in COVERAGE):
        raise ValueError("Alliant Iowa complete-rate coverage is January–December2025 and June–October2026 only; January–May2026 gaps and November/December EAC are not extrapolated.")
    current = date.fromisoformat(key)
    if current.year not in EAC or current.month > len(EAC[current.year]):
        raise ValueError("The Alliant Iowa billing month's EAC factor is not published.")
    residential = plan in ("400", "407", "427")
    dated = {name: _rider(name, key, residential) for name in RIDER_HISTORY}
    return dict(customer_daily=.5096 if residential else .7562, energy=BASE[plan],
        energy_adjustment=EAC[current.year][current.month-1],
        tax_benefit=tax_benefit(key, residential),
        **{name: value for name, (value, _) in dated.items()},
        base_version="October1,2024 (RPU-2023-0002)", eac_version=month,
        eac_includes_rce=current >= date(2025, 9, 1), rce_included_usd_per_kwh=.00006 if current >= date(2025, 9, 1) else 0.,
        rider_versions={name: version for name, (_, version) in dated.items()},
        rider_version="; ".join(f"{name}:{version['start']}" for name, (_, version) in dated.items()))
