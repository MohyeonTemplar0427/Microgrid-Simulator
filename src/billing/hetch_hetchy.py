"""SFPUC FY2026-27 retail C-1/C-2 (not municipal or Enterprise rates)."""
from dataclasses import replace
from datetime import date
from .tariffs import (CustomerClass, ServiceType, ServiceVoltageClass, Season,
                      SeasonDefinition, TOUPeriod, TariffDefinition, register_tariff,
                      DemandChargeComponent)

SOURCE = "https://www.sfpuc.gov/sites/default/files/accounts-and-services/Rates_Schedule_HHP_CleanPowerSF_2026-7.pdf"


def build_c1(*, premium=False):
    if type(premium) is not bool:
        raise ValueError("Premium enrollment must be an explicit boolean.")
    base_rates = (.39660, .31872)  # Printed page 12 / PDF page 27.
    surcharge = .00950 if premium else 0.0  # Printed page 32 / PDF page 47.
    return TariffDefinition(
        tariff_id=f"hetch_hetchy_c1_{'premium' if premium else 'standard'}_2026_07_01",
        name=f"Hetch Hetchy Power C-1 Small Commercial ({'Premium enrolled' if premium else 'Standard'})",
        utility="SFPUC Hetch Hetchy Power", customer_class=CustomerClass.COMMERCIAL,
        service_type=ServiceType.BUNDLED, service_voltage_class=ServiceVoltageClass.SECONDARY,
        effective_start=date(2026, 7, 1), effective_end=date(2027, 6, 30),
        version="FY2026-27", source_url=SOURCE,
        monthly_customer_charge=19.63, calendar_month_customer_charge=True,
        season_definition=SeasonDefinition(frozenset(range(5,11))),
        tou_periods=tuple(TOUPeriod(name=f"hhp_{season.value}",
            rate_per_kWh=rate+surcharge, start_hour=0, end_hour=0, season=season)
            for season, rate in zip((Season.SUMMER, Season.WINTER), base_rates)),
        energy_components=(("hetch_hetchy_energy", base_rates),
                           ("hetch_hetchy_premium", (surcharge, surcharge))),
        notes=("Hetch Hetchy retail C-1: confirm an eligible SFPUC small-commercial account "
               "with maximum demand below 75 kW. Location alone does not establish eligibility. "
               "Summer is May–October; winter is November–April. Energy includes generation "
               "and delivery; no PG&E PCIA or franchise surcharge is added. "
               "Premium requires confirmed enrollment. Customer charge is $19.63 per month. "
               "Calendar months are used as billing cycles; partial-month customer charges "
               "are allocated by calendar service days as a study approximation, not a filed "
               "proration rule. Rates apply to FY2026-27; actual meter-read transition billing "
               "is not modeled. Excludes taxes, discounts, special contracts and NEM/export "
               "settlements. Municipal/Enterprise schedules and other customer classes are "
               f"not represented by C-1. Source: {SOURCE}"))


def build_c2(*, voltage="secondary", premium=False):
    """Printed page 13; voltage definitions v–vi, monthly demand iv."""
    if voltage not in ("secondary", "primary"):
        raise ValueError("C-2 voltage must be secondary or primary.")
    base = build_c1(premium=premium)
    primary = voltage == "primary"
    schedule = "C-2P" if primary else "C-2S"
    rates = (.22247, .17798) if primary else (.24654, .19723)
    demand_rate = 23.94 if primary else 28.50
    surcharge = .00950 if premium else 0.0
    return replace(
        base,
        tariff_id=f"hetch_hetchy_{schedule.lower().replace('-', '')}_{'premium' if premium else 'standard'}_2026_07_01",
        name=f"Hetch Hetchy Power {schedule} Medium Commercial {voltage.title()} ({'Premium enrolled' if premium else 'Standard'})",
        service_voltage_class=ServiceVoltageClass(voltage),
        monthly_customer_charge=350.00,
        demand_charges=(DemandChargeComponent("maximum", demand_rate),),
        demand_interval_minutes=15,
        tou_periods=tuple(replace(period, rate_per_kWh=rate + surcharge)
                          for period, rate in zip(base.tou_periods, rates)),
        energy_components=(("hetch_hetchy_energy", rates),
                           ("hetch_hetchy_premium", (surcharge, surcharge))),
        notes=(f"Hetch Hetchy retail {schedule}: confirm medium-commercial account eligibility "
               "(75–500 kW) and actual service voltage with SFPUC. Primary means service "
               "from a single customer substation or without transformation at standard "
               "primary voltage; secondary is below 2,400 V or where primary/transmission "
               "definitions do not apply. Location and the representative 480 V study "
               "network do not validate the account's voltage class. "
               "Classification uses prior twelve-month demand history; exceeding the "
               "assigned maximum for more than three months triggers subsequent transfer. "
               "Simulation does not reassign an account. "
               f"Demand is ${demand_rate:.2f}/kW of the monthly maximum 15-minute import; "
               "Select 15-minute study intervals. Partial studies retain the full demand rate and may miss the month's peak. "
               "Customer charge is $350/month. Summer is May–October. Energy includes "
               "generation and delivery; no PG&E adjustments. Premium requires enrollment. "
               + base.notes[base.notes.index("Calendar months"):].replace(
                   "not represented by C-1", f"not represented by {schedule}")))


HETCH_HETCHY_TARIFFS = tuple(register_tariff(t) for t in (
    *(build_c1(premium=p) for p in (False, True)),
    *(build_c2(voltage=v, premium=p) for v in ("secondary", "primary") for p in (False, True)),
))
