"""Kingsport Power, TPUC Tariff 3. FPPAR uses the rendered-bill date; TRP&MS uses service."""
from calendar import monthrange
from datetime import date

AEP = "https://www.appalachianpower.com/lib/docs/ratesandtariffs/Tennessee/"
TPUC = "https://tpucdockets.tn.gov/"
BOOK = AEP + "KGPT_Tariff-Nov_1_2026_FPPAR_Update.pdf"
HISTORICAL_BOOK = AEP + "KGPT_Tariff_3_FPPAR_November-1_2024.pdf"
FUEL = TPUC + "archive/filings/2016/1600001gc.pdf"
RELIABILITY_2025 = TPUC + "archive/filings/2025/2500022y.pdf"
RELIABILITY_2026 = TPUC + "filings/2026/2600015u.pdf"
PRIOR_RELIABILITY = TPUC + "archive/filings/2025/2500022b.pdf"
CLASSIFICATION = TPUC + "archive/filings/2016/1600001cm.pdf"
NMS = "https://www.appalachianpower.com/lib/docs/business/builders/TNNetMeteringPackage2024.pdf"
FRANCHISE = "https://www.kingsporttn.gov/wp-content/uploads/default/3_15_16_BMA_Minutes.pdf"
TAX = "https://revenue.support.tn.gov/hc/en-us/articles/360058703911-SUT-137-Utilities-Water-Natural-Gas-Propane-and-Electricity"
CALCULATORS = {"RS": AEP + "KingsportPowerCompany-ResidentialBillCalculator-Nov_1_2026.xlsx",
               "SGS": AEP + "KingsportPowerCompany-CommercialIndustrialBillCalculator-Nov_1_2026.xlsm"}
SOURCES = [BOOK, HISTORICAL_BOOK, FUEL, PRIOR_RELIABILITY, RELIABILITY_2025, RELIABILITY_2026,
           CLASSIFICATION, NMS, FRANCHISE, TAX, *CALCULATORS.values()]
COVERAGE = (("2025-01-01", "2026-10-31"),)
GAPS = (("2026-11-01", "2026-12-31", "These service months were incomplete or future at the November 19 evidence cutoff."),)
DEFAULT_SERVICE_MONTH = "2026-07-01"
CODES = {"RS": ("015",), "SGS": ("231", "232")}


def iso_date(value):
    try:
        result = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("Kingsport requires full ISO local dates.") from None
    if result.isoformat() != value:
        raise ValueError("Kingsport requires full ISO local dates.")
    return result


def rates_for_month(service_month, plan, *, bill_date=None):
    """Get a documented service month and, separately, the FPPAR for its bill date."""
    service = iso_date(service_month)
    if plan not in CODES or service.day != 1 or not COVERAGE[0][0] <= service_month <= COVERAGE[0][1]:
        raise ValueError(f"Kingsport service period or tariff is unverified: {service_month}, {plan}.")
    # Default lookup within a month is for the calendar cycle with a final-day bill.
    end = service.replace(day=monthrange(service.year, service.month)[1])
    billed = end if bill_date is None else iso_date(bill_date)
    if billed < end or (billed.year-service.year)*12+billed.month-service.month > 1 or billed > date(2026, 11, 19):
        raise ValueError("Kingsport requires a documented final-day or immediately following-month bill within verified billed dates.")
    rs = plan == "RS"
    if billed < date(2025, 11, 1):
        fuel, fuel_source = (.10219 if rs else .08279), HISTORICAL_BOOK
    elif billed < date(2026, 11, 1):
        fuel, fuel_source = (.09504 if rs else .07699), FUEL
    else:
        fuel, fuel_source = (.10617 if rs else .08601), FUEL
    if service < date(2025, 9, 1):
        reliability, reliability_source = (3.85 if rs else 6.87), PRIOR_RELIABILITY
    elif service < date(2026, 7, 1):
        reliability, reliability_source = (6.84 if rs else 12.20), RELIABILITY_2025
    else:
        reliability, reliability_source = (7.81 if rs else 13.94), RELIABILITY_2026
    return dict(customer=16.43 if rs else 22.03, first_kwh=.00325 if rs else .03225,
                additional_kwh=.00325 if rs else .02076, fuel=fuel, reliability=reliability,
                administrative=.00011, federal_tax_adjustment=0., prompt_discount=-.015,
                franchise=.05, sales_tax=0. if rs else .07,
                source_version=f"kingsport-tn-tariff3-service-{service_month}-bill-{billed.isoformat()}",
                source_grade="filed_tariff_orders_and_utility_bill_calculators",
                sources=[BOOK, fuel_source, reliability_source, CALCULATORS[plan], FRANCHISE, TAX])
