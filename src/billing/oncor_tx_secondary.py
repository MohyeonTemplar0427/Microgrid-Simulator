"""Oncor sheet 1.3, ordinary NCP-billed secondary premises in the ≤20 kW band."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .oncor_tx_delivery import DeliveryRates, calendar_rates, delivery_sources

_START = date(2025, 1, 1)
_NEW_BASE = date(2026, 6, 1)


@dataclass(frozen=True)
class SecondaryRates(DeliveryRates):
    per_ncp_kw: dict[str, Decimal]
    per_ratchet_kw: dict[str, Decimal]


# NCP is the maximum metered 15-minute kW during this billing month. The
# standard distribution charge in this band uses NCP. The enumerated riders
# use max(NCP, 80% of the highest NCP in the preceding 11 billing months).
_MONTHLY = {
    "customer_charge": ((_START, "11.13"), (_NEW_BASE, "24.00")),
    "metering_charge": ((_START, "21.30"), (_NEW_BASE, "20.99")),
}
_PER_KWH = {
    "energy_efficiency_cost_recovery": (
        (_START, ".000407"), (date(2025, 3, 1), ".000223"), (date(2026, 3, 1), ".000546")),
}
_PER_NCP = {
    "distribution_system_charge": ((_START, "5.121040"), (_NEW_BASE, "6.931363")),
    "transmission_cost_recovery": (
        (_START, "4.959012"), (date(2025, 3, 1), "4.675281"),
        (date(2025, 9, 1), "5.114972"), (date(2026, 8, 1), "5.022675"),
        (date(2026, 10, 4), "4.606104")),
    # Sheet 6.7 specifies distribution system billing kW. Sheet 1.3's
    # separate rider-ratchet list does not include the interim surcharge.
    "interim_surcharge": ((_START, "0"), (date(2026, 8, 1), ".997891")),
}
_PER_RATCHET = {
    "nuclear_decommissioning": ((_START, ".045"), (date(2025, 12, 15), "0")),
    "distribution_cost_recovery": (
        (_START, ".819305"), (date(2025, 5, 10), "1.036859"),
        (_NEW_BASE, "0"), (date(2026, 10, 4), "1.068522")),
    "rate_case_expense": (
        (_START, ".012192"), (date(2025, 2, 24), "0"), (_NEW_BASE, ".016827")),
    "mobile_generation": (
        (_START, "0"), (date(2025, 12, 1), ".156662"), (date(2026, 1, 1), "0")),
}


def secondary_rate_sheet(effective_on: date) -> SecondaryRates:
    """Dated delivery factors for the verified NCP subset, before allocation."""
    sources = delivery_sources(effective_on)

    def rates(table):
        return {name: Decimal(next(value for since, value in reversed(history)
                                   if since <= effective_on)) for name, history in table.items()}

    return SecondaryRates(monthly=rates(_MONTHLY), per_kwh=rates(_PER_KWH), sources=sources,
                          per_ncp_kw=rates(_PER_NCP), per_ratchet_kw=rates(_PER_RATCHET))


def secondary_rates(cycle_start: date, cycle_end: date, *, bill_date: date | None = None) -> SecondaryRates:
    """Complete calendar-month delivery rates for an independently eligible account."""
    return calendar_rates(secondary_rate_sheet, cycle_start, cycle_end, bill_date=bill_date)
