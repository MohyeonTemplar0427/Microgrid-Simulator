"""Dated Ohio Power Company filed ordinary RS/GS-NDM components.

Dollar units only. Separate component clocks and an explicit intersection
guard prevent an available supply price from implying a complete retail bill.
Source extracts and original/download limitations accompany this module.
"""
from datetime import date

PLANS = ("RS", "GS-1")
ROOT = "https://www.aepohio.com/lib/docs/ratesandtariffs/Ohio/"
PUCO_ROOT = "https://dam.assets.ohio.gov/image/upload/puco.ohio.gov/empliibrary/files/docketing/tariffs/Electric/Ohio%20Power%20dba%20AEP%20Ohio/"
SOURCES = ["https://www.aepohio.com/company/about/rates/", ROOT+"January2025AEPOhioTariffBook.pdf",
    ROOT+"February_2025_AEP_Ohio_Tariff_Book.pdf", ROOT+"October_2025_AEP_Ohio_Tariff_Book.pdf",
    "https://qa.aepohio.com/lib/docs/ratesandtariffs/Ohio/April_2025_AEP_Ohio_Tariff_Book.pdf",
    "https://qa.aepohio.com/lib/docs/ratesandtariffs/Ohio/June_2025_AEP_Ohio_Tariff_Book.pdf",
    "https://qa.aepohio.com/lib/docs/ratesandtariffs/Ohio/July_2025_AEP_Ohio_Tariff_Book.pdf",
    ROOT+"October_2026_Ohio_Power_Tariff_Book.pdf", PUCO_ROOT+"PUCO%2021.pdf", PUCO_ROOT+"PUCO%2022.pdf",
    "https://www.aepohio.com/account/bills/view/understanding",
    "https://puco.ohio.gov/utilities/electricity/resources/historical-ptc-chart-opc",
    "https://www.legislature.ohio.gov/download?key=25768",
    ROOT+"December2024AEPOhioTariffBook.pdf", ROOT+"August_2025_AEP_Ohio_Tariff_Book.pdf",
    ROOT+"Nov_2025_AEP_Ohio_Tariff_Book.pdf", ROOT+"January_2026_AEP_Ohio_Tariff_Book.pdf",
    ROOT+"March_2026_AEP_Ohio_Tariff_Book.pdf", ROOT+"AEP_Ohio_Tariff_Bookv1.pdf",
    "https://qa.aepohio.com/lib/docs/ratesandtariffs/Ohio/July_2026_AEP_Ohio_Tariff_Book.pdf",
    "https://qa.aepohio.com/lib/docs/ratesandtariffs/Ohio/June_2026_AEP_Ohio_Tariff_Book.pdf",
    "https://qa.aepohio.com/lib/docs/ratesandtariffs/Ohio/September2024AEPOhioTariffBook.pdf"]

# Only completely recovered component intersections are executable.
COVERAGE = (("2025-01-01", "2026-03-31"), ("2026-05-01", "2026-10-31"))

# Pair values are (RS, GS-1/GS-NDM); scalar values apply to both.
# An explicit None marks an unrecovered intermediate sheet, never zero.
HISTORY = {
    "transmission": [
        ("2025-01-01", (.0438371, .0234674), "21:400-1 revision4; September2024 official indexed book"),
        ("2025-04-01", (.0353171, .0197070), "21:400-1 revision5; April2025 original p152"),
        ("2025-10-01", (.0355042, .0215614), "21:400-1 revision6; October2025 official indexed book"),
        ("2026-04-01", (.0434364, .0316869), "21:400-1 revision7; regulator21 p160"),
        ("2026-10-01", (.0441180, .0320019), "22:400-1 revision1; October2026 original p155")],
    "pipp": [("2025-01-01", .0046279, "21:404-1 revision5; January2025 application"),
        ("2026-01-01", .0055215, "21:404-1 revision7; January2026 application"),
        ("2026-10-01", .0063634, "22:404-1 revision1; October2026 original p157")],
    "throughput_balancing": [("2025-01-01", 0., "21:406-1 revision8; August2024 application, both zones"),
        ("2025-02-01", 0., "21:406-1 revision9; February2025 application; Ohio Power zero, CSP residential credit handled explicitly"),
        ("2025-03-01", 0., "21:406-1 revision10; March2025 application, both zones")],
    "enhanced_service_reliability": [("2025-01-01", .0669857, "21:408-1 revision3; June2024 application"),
        ("2025-12-01", .0788222, "21:408-1 revision4; December2025 application; regulator21 p164 visually verified"),
        ("2026-04-10", .0580236, "22:408-1 original; April10,2026 application")],
    "grid_smart": [("2025-01-01", (2.08, 17.53), "21:410-1 revision13; January2025 application; official indexed February book"),
        ("2025-04-01", (2.22, 18.72), "21:410-1 revision14; April2025 application"),
        ("2025-07-01", (2.35, 19.89), "21:410-1 revision15; July2025 original p157"),
        ("2025-10-01", (2.45, 20.75), "21:410-1 revision16; October2025 application; official indexed regulator book"),
        ("2026-01-01", (2.62, 21.84), "21:410-1 revision17; January2026 application; official indexed March book"),
        ("2026-04-01", (2.80, 23.69), "21:410-1 revision18 and22:410-1 original; April2026 application"),
        ("2026-07-01", (2.65, 22.68), "22:410-1 revision1; July2026 application"),
        ("2026-10-01", (1.26, 10.76), "22:410-1 revision2; October2026 application")],
    "distribution_investment": [("2025-01-01", .2363101, "21:412-1 revision13; December2024 application; official indexed February book"),
        ("2025-03-01", .2414004, "21:412-1 revision14; March2025 application"),
        ("2025-07-01", .2337423, "21:412-1 revision15; July2025 original p158"),
        ("2025-09-01", .2451638, "21:412-1 revision16; September2025 application; official indexed November book"),
        ("2025-12-01", .2407925, "21:412-1 revision17; December2025 application; official indexed January2026 book"),
        ("2026-03-01", .2360370, "21:412-1 revision18; March2026 application"),
        ("2026-04-10", .0295915, "22:412-1 original; April10,2026 application; June2026 original p163 corroborates indexed original book"),
        ("2026-07-01", .0408549, "22:412-1 revision1; July2026 original p163"),
        ("2026-09-01", .0538996, "22:412-1 revision2; September2026 application")],
    "storm_damage": [("2025-01-01", (.97, 4.84), "21:414-1 revision4; November2024 application, expires October2025"),
        ("2025-11-01", (.20, .99), "21:414-1 revision5; November2025 application"),
        ("2026-04-10", (.19, 1.02), "22:414-1 original; April10,2026 application, expires October2026")],
    "economic_development": [("2025-01-01", .0494232, "21:420-1 revision7; October2024 application; official indexed February book"),
        ("2025-04-01", .0195121, "21:420-1 revision8; April2025 original p161"),
        ("2025-10-01", .0353443, "21:420-1 revision9; October2025 application; official indexed regulator book"),
        ("2026-04-01", .0239150, "21:420-1 revision10; April2026 application"),
        ("2026-04-10", .0180190, "22:420-1 original; regulator22 p163 overrides obsolete21 sheet retained in utility October book")],
    "energy_efficiency": [("2025-01-01", (.0008624, 0.), "21:437-1 revision1; September2024 application; official indexed September2024 book"),
        ("2025-04-01", (.0007387, 0.), "21:437-1 revision2; April2025 application"),
        ("2026-04-01", (.0004541, 0.), "21:437-1 revision3; April2026 application")],
    "generation_energy": [("2025-01-01", .0702100, "21:450-1 revision3; June2024 application; April2025 original p170"),
        ("2025-06-01", .0768800, "21:450-1 revision4; June2025 application"),
        ("2026-06-01", .0750800, "22:450-1 revision1; June2026 application")],
    "generation_capacity": [("2025-01-01", (.0032000, .0027300), "21:451-1/2 revision3; June2024 application; both zones"),
        ("2025-06-01", (.0229800, .0188500), "21:451-1/2 revision4; June2025 application; both zones"),
        ("2026-06-01", (.0265900, .0229800), "22:451-1 revision1; June2026 application")],
    "auction_reconciliation": [("2025-01-01", .0004501, "21:452-1 revision14; January2025 application; official indexed January book"),
        ("2025-04-01", -.0041073, "21:452-1 revision15; April2025 application"),
        ("2025-07-01", .0014672, "21:452-1 revision16; July2025 original p173"),
        ("2025-10-01", -.0057597, "21:452-1 revision17; October2025 application; official indexed regulator book"),
        ("2026-01-01", .0027589, "21:452-1 revision18; January2026 application; official indexed March book"),
        ("2026-04-01", -.0043956, "21:452-1 revision19; April2026 application"),
        ("2026-07-01", .0041210, "22:452-1 revision1; July2026 application"),
        ("2026-10-01", -.0037229, "22:452-1 revision2; October2026 application")],
}


def _component(name, day, residential):
    found = [(start, value, reference) for start, value, reference in HISTORY[name] if start <= day]
    if not found or found[-1][1] is None:
        raise ValueError(f"AEP Ohio {name} has no verified complete factor on {day}; no historical substitution.")
    start, value, reference = found[-1]
    if isinstance(value, tuple):
        value = value[0 if residential else 1]
    return value, dict(start=start, reference=reference)


def rates_on(day, plan, *, bill_date=None, zone="ohio_power"):
    try:
        if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
            raise ValueError
        if bill_date is None:
            bill_date = day
        if not isinstance(bill_date, str) or date.fromisoformat(bill_date).isoformat() != bill_date:
            raise ValueError
    except ValueError as exc:
        raise ValueError("AEP Ohio dates must be exact ISO local dates.") from exc
    if plan not in PLANS or zone not in ("ohio_power", "columbus_southern"):
        raise ValueError("Choose AEP Ohio RS/GS-1 and an independently verified legacy rate zone.")
    if not any(start <= day <= end for start, end in COVERAGE):
        raise ValueError("AEP Ohio date is outside the verified complete-rate intersections; no extrapolation or provisional mode.")
    if bill_date < day or bill_date[:7] != day[:7]:
        raise ValueError("AEP Ohio first scope aligns service month and bill date; shifted applicability is unsupported.")
    res = plan == "RS"
    current = day >= "2026-04-10"
    data = {k: _component(k, day, res) for k in HISTORY}
    legacy = (1.17 if res else .0018007) if bill_date < "2025-07-01" else (.88 if res else .0016400)
    if bill_date >= "2025-08-14":
        legacy = 0.
    result = dict(customer=13.5 if current and res else 21. if current else 10. if res else 9.4,
        distribution_energy=.0347738 if current and res else .0271520 if current else .0263125 if res else .0205802,
        filed_schedule="RS" if res else "GS-NDM" if current else "GS-1",
        base_version="PUCO22 April10,2026" if current else "PUCO21 RS January1,2022 / GS-1 December1,2024",
        base_percent={k: data[k][0] for k in ("enhanced_service_reliability", "distribution_investment", "economic_development")}
            | {"bad_debt":0.},
        monthly={"grid_smart":data["grid_smart"][0], "storm_damage":data["storm_damage"][0], "power_forward":0., "ohio_first":0.},
        energy={k: data[k][0] for k in ("transmission", "throughput_balancing", "energy_efficiency", "generation_energy", "generation_capacity", "auction_reconciliation")}
            | {"retail_reconciliation":0., "sso_credit":0., "tax_savings_credit":(-.001906 if res else -.001060) if current else 0.,
               "alternative_energy":.0038973, "energy_efficiency_peak_demand":0.},
        pipp=data["pipp"][0], legacy_generation=legacy,
        solar_generation=0. if bill_date >= "2025-08-14" else .10 if res else .0002905,
        versions={k: v[1] for k, v in data.items()})
    if zone == "columbus_southern" and res and "2025-02-01" <= day < "2025-03-01":
        result["energy"]["throughput_balancing"] = -.000182
    result["versions"].update(
        legacy_generation=dict(start="2025-08-14" if bill_date >= "2025-08-14" else "2025-07-01" if bill_date >= "2025-07-01" else "2025-01-01",
            reference="21:422-1 revisions7/8/9; bill-date application; August14 cancellation"),
        solar_generation=dict(start="2025-08-14" if bill_date >= "2025-08-14" else "2025-01-01",
            reference="21:433-1 revisions4/5; bill-date application; August14 cancellation"))
    return result
