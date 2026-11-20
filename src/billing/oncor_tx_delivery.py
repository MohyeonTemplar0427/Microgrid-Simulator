"""Filed Oncor standard-meter delivery charges. REP supply and taxes are separate."""
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

_ONCOR = ("https://www.oncor.com/content/dam/oncorwww/documents/about-us/regulatory/"
          "tariff-and-rate-schedules/Tariff%20for%20Retail%20Delivery%20Service")
_PUCT = "https://interchange.puc.texas.gov/Documents/"
HISTORICAL_BOOK = _ONCOR + "_.pdf.coredownload.pdf"
CURRENT_BOOK = _ONCOR + ".pdf.coredownload.pdf"
HISTORICAL_BASE = _PUCT + "54817_28_1322201.PDF"
HISTORICAL_RCE = _PUCT + "54817_28_1322202.PDF"
RCE_END = _PUCT + "57799_7_1491155.PDF"
DCRF_ORDER = _PUCT + "57707_46_1492438.PDF"
NDC_ORDER = _PUCT + "58826_12_1563610.PDF"
UTM_NOTICE = _PUCT + "59249_105_1676040.PDF"

_START = date(2025, 1, 1)
_AS_OF = date(2026, 11, 19)
_NEW_BASE = date(2026, 6, 1)
_BILL_DATE_TRANSITIONS = {date(2025, 2, 1), date(2025, 5, 1), date(2026, 10, 1)}

# Effective date, Residential Service, Secondary Service <=10 kW. All factors
# in this table are dollars per imported kWh. December MG is a single month.
_ENERGY_FACTORS = {
    "distribution_system_charge": (
        (_START, ".025344", ".021251"), (_NEW_BASE, ".036043", ".031236")),
    "nuclear_decommissioning": (
        (_START, ".000199", ".000130"), (date(2025, 12, 15), "0", "0")),
    "transmission_cost_recovery": (
        (_START, ".021800", ".018422"),
        (date(2025, 3, 1), ".018796", ".018606"),
        (date(2025, 9, 1), ".023580", ".018157"),
        (date(2026, 8, 1), ".019046", ".016974"),
        (date(2026, 10, 4), ".021669", ".013382")),
    "energy_efficiency_cost_recovery": (
        (_START, ".001024", ".000036"),
        (date(2025, 3, 1), ".001137", "-.000196"),
        (date(2026, 3, 1), ".001487", ".000055")),
    "distribution_cost_recovery": (
        (_START, ".004553", ".004811"),
        (date(2025, 5, 10), ".005772", ".006411"),
        (_NEW_BASE, "0", "0"),
        (date(2026, 10, 4), ".005755", ".006208")),
    "rate_case_expense": (
        (_START, ".000054", ".000055"),
        (date(2025, 2, 24), "0", "0"),
        (_NEW_BASE, ".000086", ".000084")),
    "mobile_generation": (
        (_START, "0", "0"), (date(2025, 12, 1), ".001027", ".000606"),
        (date(2026, 1, 1), "0", "0")),
    "interim_surcharge": (
        (_START, "0", "0"), (date(2026, 8, 1), ".003633", ".002878")),
}
_MONTHLY_FACTORS = {
    "customer_charge": ((_START, "1.43", "2.26"), (_NEW_BASE, "1.48", "2.34")),
    "metering_charge": ((_START, "2.80", "4.61"), (_NEW_BASE, "2.58", "4.36")),
}


@dataclass(frozen=True)
class DeliveryRates:
    monthly: dict[str, Decimal]
    per_kwh: dict[str, Decimal]
    sources: tuple[str, ...]


def delivery_sources(effective_on: date) -> tuple[str, ...]:
    """Identify the rate books and orders covering this date."""
    if type(effective_on) is not date or not _START <= effective_on <= _AS_OF:
        raise ValueError("Date outside verified Oncor delivery rate sheets.")
    sources = [CURRENT_BOOK]
    if effective_on < _NEW_BASE:
        sources.extend((HISTORICAL_BOOK, HISTORICAL_BASE, HISTORICAL_RCE, RCE_END))
    if date(2025, 5, 10) <= effective_on < _NEW_BASE:
        sources.append(DCRF_ORDER)
    if effective_on >= date(2025, 12, 15):
        sources.append(NDC_ORDER)
    if effective_on >= date(2026, 10, 4):
        sources.append(UTM_NOTICE)
    return tuple(sources)


def delivery_rate_sheet(schedule: str, effective_on: date) -> DeliveryRates:
    """Look up posted factors for a date. This lookup does not allocate a bill."""
    if schedule not in ("residential", "secondary_le_10_kw"):
        raise ValueError("Unverified Oncor delivery schedule.")
    sources = delivery_sources(effective_on)
    column = 1 if schedule == "residential" else 2

    def factors(ledger):
        return {name: Decimal(next(row[column] for row in reversed(history)
                                   if row[0] <= effective_on))
                for name, history in ledger.items()}

    return DeliveryRates(factors(_MONTHLY_FACTORS), factors(_ENERGY_FACTORS), sources)


def calendar_rates(rate_sheet, cycle_start: date, cycle_end: date, *, bill_date: date | None):
    """Select filed factors for one full calendar read and its delivery invoice."""
    if (type(cycle_start) is not date or type(cycle_end) is not date or cycle_start.day != 1
            or cycle_end != cycle_start.replace(day=monthrange(cycle_start.year, cycle_start.month)[1])):
        raise ValueError("Oncor delivery requires a complete calendar billing cycle.")
    if bill_date is not None and (type(bill_date) is not date or bill_date != cycle_end):
        raise ValueError("Oncor delivery requires the documented final-day bill date.")
    start = rate_sheet(cycle_start)
    end = rate_sheet(cycle_end)
    if start != end:
        if cycle_start not in _BILL_DATE_TRANSITIONS:
            raise ValueError("Allocation of the Oncor mid-cycle rate change is unverified.")
        if bill_date is None:
            raise ValueError("Oncor rate change requires the documented delivery bill date.")
    return end


def delivery_rates(schedule: str, cycle_start: date, cycle_end: date,
                   *, bill_date: date | None = None) -> DeliveryRates:
    """Standard-meter, complete calendar cycle. Dates are inclusive Texas local dates."""
    return calendar_rates(lambda on: delivery_rate_sheet(schedule, on),
                          cycle_start, cycle_end, bill_date=bill_date)
