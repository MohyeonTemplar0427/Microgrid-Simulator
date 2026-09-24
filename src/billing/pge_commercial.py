"""PG&E commercial tariff definitions.

Rates below are transcribed from PG&E's published tariff book and are valid
for the stated effective date only. They are **versioned data**: when PG&E
files new rates, add a new :class:`TariffDefinition` with its own effective
window rather than editing these numbers in place, so historical analyses stay
reproducible.

The B-series: small general service through large demand-metered TOU.
Every period here applies every day, including weekends and holidays,
which is why none of them sets ``TOUPeriod.days``.
"""

from dataclasses import replace
from datetime import date

from .pge_common import PGE_SEASONS
from .tariffs import (
    CustomerClass,
    DemandChargeBasis,
    DemandChargeComponent,
    DemandChargeFrequency,
    ExportCompensationRule,
    Season,
    SeasonDefinition,
    ServiceType,
    ServiceVoltageClass,
    TOUPeriod,
    TariffDefinition,
    WEEKDAYS,
    register_tariff,
)


B10_SOURCE_URL = (
    "https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-10.pdf"
)


B1_SOURCE_URL = (
    "https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-1.pdf"
)


def _pge_b1_secondary_bundled(
    *,
    tariff_id: str,
    name: str,
    daily_customer_charge: float,
) -> TariffDefinition:
    """Build one standard B-1 phase variant from the same energy schedule."""

    return TariffDefinition(
        tariff_id=tariff_id,
        name=name,
        utility="Pacific Gas and Electric",
        effective_start=date(2026, 3, 1),
        service_voltage_class=ServiceVoltageClass.SECONDARY,
        customer_class=CustomerClass.COMMERCIAL,
        service_type=ServiceType.BUNDLED,
        season_definition=PGE_SEASONS,
        daily_customer_charge=daily_customer_charge,
        # Standard B-1 has no demand-charge component. B1-ST is a different
        # optional storage rate and is intentionally not represented here.
        demand_charges=(),
        tou_periods=(
            TOUPeriod(
                name="summer_peak",
                billing_category="summer_peak",
                rate_per_kWh=0.47087,
                start_hour=16,
                end_hour=21,
                season=Season.SUMMER,
                priority=30,
            ),
            TOUPeriod(
                name="summer_part_peak_afternoon",
                billing_category="summer_part_peak",
                rate_per_kWh=0.42164,
                start_hour=14,
                end_hour=16,
                season=Season.SUMMER,
                priority=20,
            ),
            TOUPeriod(
                name="summer_part_peak_evening",
                billing_category="summer_part_peak",
                rate_per_kWh=0.42164,
                start_hour=21,
                end_hour=23,
                season=Season.SUMMER,
                priority=20,
            ),
            TOUPeriod(
                name="summer_off_peak",
                billing_category="summer_off_peak",
                rate_per_kWh=0.40083,
                start_hour=0,
                end_hour=0,
                season=Season.SUMMER,
                priority=0,
            ),
            TOUPeriod(
                name="winter_peak",
                billing_category="winter_peak",
                rate_per_kWh=0.39545,
                start_hour=16,
                end_hour=21,
                season=Season.WINTER,
                priority=30,
            ),
            TOUPeriod(
                name="winter_super_off_peak",
                billing_category="winter_super_off_peak",
                rate_per_kWh=0.36291,
                start_hour=9,
                end_hour=14,
                season=Season.WINTER,
                months=frozenset({3, 4, 5}),
                priority=20,
            ),
            TOUPeriod(
                name="winter_off_peak",
                billing_category="winter_off_peak",
                rate_per_kWh=0.37933,
                start_hour=0,
                end_hour=0,
                season=Season.WINTER,
                priority=0,
            ),
        ),
        export_rule=ExportCompensationRule(
            name="not_modelled",
            implemented=False,
            note=(
                "B-1 export compensation is not part of the B-1 rate "
                "schedule. Configure the account's NEM or Net Billing "
                "Tariff export prices separately."
            ),
        ),
        source_url=B1_SOURCE_URL,
        version="2026-03-01",
        notes=(
            "Standard B-1, secondary voltage and bundled service. The "
            "account must not have reached 75 kW or more for three "
            "consecutive months in the latest twelve. B1-ST, PDP, CCA, "
            "Direct Access, export compensation, standby charges and "
            "power-factor adjustments are not modelled."
        ),
    )


PGE_B1_SECONDARY_SINGLE_PHASE_BUNDLED = register_tariff(
    _pge_b1_secondary_bundled(
        tariff_id="pge_b1_secondary_single_phase_bundled_2026_03_01",
        name="PG&E B-1 Small General Service (Single-Phase)",
        daily_customer_charge=0.32854,
    )
)

PGE_B1_SECONDARY_POLYPHASE_BUNDLED = register_tariff(
    _pge_b1_secondary_bundled(
        tariff_id="pge_b1_secondary_polyphase_bundled_2026_03_01",
        name="PG&E B-1 Small General Service (Polyphase)",
        daily_customer_charge=0.82136,
    )
)

PGE_B10_SECONDARY_BUNDLED = register_tariff(
    TariffDefinition(
        tariff_id="pge_b10_secondary_bundled_2026_03_01",
        name="PG&E B-10 Medium General Demand-Metered Service",
        utility="Pacific Gas and Electric",
        effective_start=date(2026, 3, 1),
        service_voltage_class=ServiceVoltageClass.SECONDARY,
        customer_class=CustomerClass.COMMERCIAL,
        service_type=ServiceType.BUNDLED,
        season_definition=PGE_SEASONS,
        # $ per meter per day.
        daily_customer_charge=11.36882,
        demand_charges=(
            DemandChargeComponent(
                name="maximum_demand",
                rate_per_kW=20.50,
                basis=DemandChargeBasis.MAXIMUM,
            ),
        ),
        tou_periods=(
            # --- Summer: June 1 - September 30 ---
            TOUPeriod(
                name="summer_peak",
                rate_per_kWh=0.33947,
                start_hour=16,
                end_hour=21,
                season=Season.SUMMER,
                priority=30,
            ),
            TOUPeriod(
                name="summer_part_peak_afternoon",
                rate_per_kWh=0.27778,
                start_hour=14,
                end_hour=16,
                season=Season.SUMMER,
                priority=20,
            ),
            TOUPeriod(
                name="summer_part_peak_evening",
                rate_per_kWh=0.27778,
                start_hour=21,
                end_hour=23,
                season=Season.SUMMER,
                priority=20,
            ),
            TOUPeriod(
                name="summer_off_peak",
                rate_per_kWh=0.24522,
                start_hour=0,
                end_hour=0,  # full day, lowest priority
                season=Season.SUMMER,
                priority=0,
            ),
            # --- Winter: October 1 - May 31 ---
            TOUPeriod(
                name="winter_peak",
                rate_per_kWh=0.26321,
                start_hour=16,
                end_hour=21,
                season=Season.WINTER,
                priority=30,
            ),
            # Super off-peak applies only in March, April and May.
            TOUPeriod(
                name="winter_super_off_peak",
                rate_per_kWh=0.19139,
                start_hour=9,
                end_hour=14,
                season=Season.WINTER,
                months=frozenset({3, 4, 5}),
                priority=20,
            ),
            TOUPeriod(
                name="winter_off_peak",
                rate_per_kWh=0.22773,
                start_hour=0,
                end_hour=0,  # full day, lowest priority
                season=Season.WINTER,
                priority=0,
            ),
        ),
        export_rule=ExportCompensationRule(
            name="not_modelled",
            implemented=False,
            note=(
                "B-10 export compensation (NEM or the Net Billing Tariff) is "
                "not modelled. Configure an explicit fixed or CSV export "
                "price in the surplus configuration instead."
            ),
        ),
        source_url=B10_SOURCE_URL,
        version="2026-03-01",
        notes=(
            "Secondary voltage means service below 2,400 V, which includes "
            "the modelled 480 V service. Rates are bundled (PG&E supplies "
            "generation); CCA and Direct Access customers pay different "
            "generation components and are not modelled."
        ),
    )
)


B19_SOURCE_URL = (
    "https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-19.pdf"
)

# Mandatory for customers whose maximum billing demand has exceeded 499 kW
# for at least three consecutive months; secondary voltage, bundled service
# only. Unlike B-10, this schedule bills three separate demand components --
# a maximum-demand charge plus time-scoped peak-period and part-peak-period
# charges -- all three applied to the same bill (Sheet 14, Section 3a).
# Winter has no part-peak-period demand component; only summer does.
PGE_B19_SECONDARY_MANDATORY_BUNDLED = register_tariff(
    TariffDefinition(
        tariff_id="pge_b19_secondary_mandatory_bundled_2026_03_01",
        name="PG&E B-19 Medium General Demand-Metered TOU Service (Mandatory)",
        utility="Pacific Gas and Electric",
        effective_start=date(2026, 3, 1),
        service_voltage_class=ServiceVoltageClass.SECONDARY,
        customer_class=CustomerClass.COMMERCIAL,
        service_type=ServiceType.BUNDLED,
        season_definition=PGE_SEASONS,
        # $ per meter per day.
        daily_customer_charge=58.62824,
        demand_charges=(
            DemandChargeComponent(
                name="maximum_demand",
                rate_per_kW=37.37,
                basis=DemandChargeBasis.MAXIMUM,
            ),
            DemandChargeComponent(
                name="peak_period_demand_summer",
                rate_per_kW=46.16,
                basis=DemandChargeBasis.PEAK_PERIOD,
                season=Season.SUMMER,
            ),
            DemandChargeComponent(
                name="part_peak_period_demand_summer",
                rate_per_kW=10.52,
                basis=DemandChargeBasis.PART_PEAK_PERIOD,
                season=Season.SUMMER,
            ),
            DemandChargeComponent(
                name="peak_period_demand_winter",
                rate_per_kW=2.31,
                basis=DemandChargeBasis.PEAK_PERIOD,
                season=Season.WINTER,
            ),
        ),
        tou_periods=(
            # --- Summer: June 1 - September 30 ---
            TOUPeriod(
                name="summer_peak",
                rate_per_kWh=0.18648,
                start_hour=16,
                end_hour=21,
                season=Season.SUMMER,
                priority=30,
                demand_basis=DemandChargeBasis.PEAK_PERIOD,
            ),
            TOUPeriod(
                name="summer_part_peak_afternoon",
                rate_per_kWh=0.14775,
                start_hour=14,
                end_hour=16,
                season=Season.SUMMER,
                priority=20,
                demand_basis=DemandChargeBasis.PART_PEAK_PERIOD,
            ),
            TOUPeriod(
                name="summer_part_peak_evening",
                rate_per_kWh=0.14775,
                start_hour=21,
                end_hour=23,
                season=Season.SUMMER,
                priority=20,
                demand_basis=DemandChargeBasis.PART_PEAK_PERIOD,
            ),
            TOUPeriod(
                name="summer_off_peak",
                rate_per_kWh=0.12037,
                start_hour=0,
                end_hour=0,  # full day, lowest priority
                season=Season.SUMMER,
                priority=0,
            ),
            # --- Winter: October 1 - May 31 ---
            TOUPeriod(
                name="winter_peak",
                rate_per_kWh=0.16188,
                start_hour=16,
                end_hour=21,
                season=Season.WINTER,
                priority=30,
                demand_basis=DemandChargeBasis.PEAK_PERIOD,
            ),
            # Super off-peak applies only in March, April and May.
            TOUPeriod(
                name="winter_super_off_peak",
                rate_per_kWh=0.06442,
                start_hour=9,
                end_hour=14,
                season=Season.WINTER,
                months=frozenset({3, 4, 5}),
                priority=20,
            ),
            TOUPeriod(
                name="winter_off_peak",
                rate_per_kWh=0.12026,
                start_hour=0,
                end_hour=0,  # full day, lowest priority
                season=Season.WINTER,
                priority=0,
            ),
        ),
        export_rule=ExportCompensationRule(
            name="not_modelled",
            implemented=False,
            note=(
                "B-19 export compensation (NEM or the Net Billing Tariff) is "
                "not modelled. Configure an explicit fixed or CSV export "
                "price in the surplus configuration instead."
            ),
        ),
        source_url=B19_SOURCE_URL,
        version="2026-03-01",
        notes=(
            "Mandatory tier, secondary voltage, bundled service only. The "
            "Voluntary tier and Options R and S are registered separately "
            "as `pge_b19_secondary_voluntary_bundled_2026_03_01`, "
            "`..._option_r_...` and `..._option_s_...`. Not modelled: "
            "Primary and Transmission voltage classes, and the "
            "power-factor adjustment. `previous_peak_kw` carryover applies only to the "
            "maximum-demand component -- the peak-period and part-peak-"
            "period components always start fresh from the supplied data, "
            "same caveat as a MAXIMUM-only tariff's first partial period."
        ),
    )
)


B6_SOURCE_URL = (
    "https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-6.pdf"
)


def _pge_b6_secondary_bundled(
    *,
    tariff_id: str,
    name: str,
    daily_customer_charge: float,
) -> TariffDefinition:
    """Build one B-6 phase variant from the shared energy schedule.

    Single-phase and polyphase service differ only in the daily customer
    charge; the energy schedule is identical, so both variants are built
    from this one definition.
    """

    return TariffDefinition(
        tariff_id=tariff_id,
        name=name,
        utility="Pacific Gas and Electric",
        effective_start=date(2026, 3, 1),
        service_voltage_class=ServiceVoltageClass.SECONDARY,
        customer_class=CustomerClass.COMMERCIAL,
        service_type=ServiceType.BUNDLED,
        season_definition=PGE_SEASONS,
        daily_customer_charge=daily_customer_charge,
        # B-6 bills energy only. Unlike B-10 and B-19 there is no demand
        # component anywhere in the schedule, which is the whole point of
        # the rate: the peak-to-off-peak energy spread carries all of the
        # price signal.
        demand_charges=(),
        # Every B-6 period applies "every day, including weekends and
        # holidays" (Sheet 5), so the absence of any day-of-week concept in
        # TOUPeriod represents this schedule exactly. Summer has no
        # part-peak period at all -- peak steps straight down to off-peak.
        tou_periods=(
            TOUPeriod(
                name="summer_peak",
                rate_per_kWh=0.64253,
                start_hour=16,
                end_hour=21,
                season=Season.SUMMER,
                priority=30,
            ),
            TOUPeriod(
                name="summer_off_peak",
                rate_per_kWh=0.38491,
                start_hour=0,
                end_hour=0,  # full day, lowest priority
                season=Season.SUMMER,
                priority=0,
            ),
            TOUPeriod(
                name="winter_peak",
                rate_per_kWh=0.39584,
                start_hour=16,
                end_hour=21,
                season=Season.WINTER,
                priority=30,
            ),
            TOUPeriod(
                name="winter_super_off_peak",
                rate_per_kWh=0.31617,
                start_hour=9,
                end_hour=14,
                season=Season.WINTER,
                months=frozenset({3, 4, 5}),
                priority=20,
            ),
            TOUPeriod(
                name="winter_off_peak",
                rate_per_kWh=0.35225,
                start_hour=0,
                end_hour=0,  # full day, lowest priority
                season=Season.WINTER,
                priority=0,
            ),
        ),
        export_rule=ExportCompensationRule(
            name="not_modelled",
            implemented=False,
            note=(
                "B-6 export compensation (NEM or the Net Billing Tariff) is "
                "not modelled. Configure an explicit fixed or CSV export "
                "price in the surplus configuration instead."
            ),
        ),
        source_url=B6_SOURCE_URL,
        version="2026-03-01",
        notes=(
            "Small General Time-of-Use Service, secondary voltage, bundled "
            "service. The account must not have reached 75 kW or more for "
            "three consecutive months in the latest twelve. Not modelled: "
            "Peak Day Pricing, which B-6 defaults eligible customers onto "
            "and which prices event hours at $0.60/kWh against a summer "
            "peak credit -- it needs PG&E's event calendar, which is not "
            "available here. CCA, Direct Access, standby charges and "
            "power-factor adjustments are also not modelled."
        ),
    )


PGE_B6_SECONDARY_SINGLE_PHASE_BUNDLED = register_tariff(
    _pge_b6_secondary_bundled(
        tariff_id="pge_b6_secondary_single_phase_bundled_2026_03_01",
        name="PG&E B-6 Small General Time-of-Use Service (Single-Phase)",
        daily_customer_charge=0.32854,
    )
)

PGE_B6_SECONDARY_POLYPHASE_BUNDLED = register_tariff(
    _pge_b6_secondary_bundled(
        tariff_id="pge_b6_secondary_polyphase_bundled_2026_03_01",
        name="PG&E B-6 Small General Time-of-Use Service (Polyphase)",
        daily_customer_charge=0.82136,
    )
)

B20_SOURCE_URL = (
    "https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-20.pdf"
)

# For customers whose maximum demand has exceeded 999 kW for at least three
# consecutive months in the latest twelve; secondary voltage, bundled service
# only. The TOU periods match B-10 and B-19 exactly; what distinguishes B-20
# is the size of the fixed and demand charges against a very narrow energy
# spread, so nearly all of a battery's value here is demand reduction.
#
# PG&E lists maximum demand once per season (Sheet 4: "Maximum Demand Summer"
# and "Maximum Demand Winter"), both currently $39.08. They are modelled as a
# single season-less component: billing is identical, and two seasonal
# MAXIMUM components would be summed by callers that total the maximum-demand
# rate, overstating it at $78.16/kW. Split them only if PG&E ever prices the
# seasons differently, and fix those callers at the same time.
PGE_B20_SECONDARY_BUNDLED = register_tariff(
    TariffDefinition(
        tariff_id="pge_b20_secondary_bundled_2026_03_01",
        name="PG&E B-20 Large General Demand-Metered TOU Service",
        utility="Pacific Gas and Electric",
        effective_start=date(2026, 3, 1),
        service_voltage_class=ServiceVoltageClass.SECONDARY,
        customer_class=CustomerClass.COMMERCIAL,
        service_type=ServiceType.BUNDLED,
        season_definition=PGE_SEASONS,
        # $ per meter per day.
        daily_customer_charge=107.36636,
        demand_charges=(
            DemandChargeComponent(
                name="maximum_demand",
                rate_per_kW=39.08,
                basis=DemandChargeBasis.MAXIMUM,
            ),
            DemandChargeComponent(
                name="peak_period_demand_summer",
                rate_per_kW=41.35,
                basis=DemandChargeBasis.PEAK_PERIOD,
                season=Season.SUMMER,
            ),
            DemandChargeComponent(
                name="part_peak_period_demand_summer",
                rate_per_kW=9.27,
                basis=DemandChargeBasis.PART_PEAK_PERIOD,
                season=Season.SUMMER,
            ),
            DemandChargeComponent(
                name="peak_period_demand_winter",
                rate_per_kW=2.32,
                basis=DemandChargeBasis.PEAK_PERIOD,
                season=Season.WINTER,
            ),
        ),
        tou_periods=(
            # --- Summer: June 1 - September 30 ---
            TOUPeriod(
                name="summer_peak",
                rate_per_kWh=0.17702,
                start_hour=16,
                end_hour=21,
                season=Season.SUMMER,
                priority=30,
                demand_basis=DemandChargeBasis.PEAK_PERIOD,
            ),
            TOUPeriod(
                name="summer_part_peak_afternoon",
                rate_per_kWh=0.14227,
                start_hour=14,
                end_hour=16,
                season=Season.SUMMER,
                priority=20,
                demand_basis=DemandChargeBasis.PART_PEAK_PERIOD,
            ),
            TOUPeriod(
                name="summer_part_peak_evening",
                rate_per_kWh=0.14227,
                start_hour=21,
                end_hour=23,
                season=Season.SUMMER,
                priority=20,
                demand_basis=DemandChargeBasis.PART_PEAK_PERIOD,
            ),
            TOUPeriod(
                name="summer_off_peak",
                rate_per_kWh=0.11482,
                start_hour=0,
                end_hour=0,  # full day, lowest priority
                season=Season.SUMMER,
                priority=0,
            ),
            # --- Winter: October 1 - May 31 ---
            TOUPeriod(
                name="winter_peak",
                rate_per_kWh=0.15632,
                start_hour=16,
                end_hour=21,
                season=Season.WINTER,
                priority=30,
                demand_basis=DemandChargeBasis.PEAK_PERIOD,
            ),
            # Super off-peak applies only in March, April and May.
            TOUPeriod(
                name="winter_super_off_peak",
                rate_per_kWh=0.05872,
                start_hour=9,
                end_hour=14,
                season=Season.WINTER,
                months=frozenset({3, 4, 5}),
                priority=20,
            ),
            TOUPeriod(
                name="winter_off_peak",
                rate_per_kWh=0.11460,
                start_hour=0,
                end_hour=0,  # full day, lowest priority
                season=Season.WINTER,
                priority=0,
            ),
        ),
        export_rule=ExportCompensationRule(
            name="not_modelled",
            implemented=False,
            note=(
                "B-20 export compensation (NEM or the Net Billing Tariff) is "
                "not modelled. Configure an explicit fixed or CSV export "
                "price in the surplus configuration instead."
            ),
        ),
        source_url=B20_SOURCE_URL,
        version="2026-03-01",
        notes=(
            "Secondary voltage, bundled service only. Option R and Option S "
            "are registered separately as "
            "`pge_b20_secondary_option_r_bundled_2026_03_01` and "
            "`..._option_s_...`. Not modelled: Primary and Transmission "
            "voltage classes, the power-factor adjustment "
            "($0.00005 per kWh per percent), Peak Day Pricing, Schedule SB "
            "standby charges, and the fuel-cell Generation Demand "
            "Adjustment. `previous_peak_kw` carryover applies only to the "
            "maximum-demand component -- the peak-period and part-peak-"
            "period components always start fresh from the supplied data."
        ),
    )
)

def _pge_large_demand_tou(
    *,
    tariff_id: str,
    name: str,
    daily_customer_charge: float,
    maximum_demand: float,
    peak_demand_summer: float,
    part_peak_demand_summer: float,
    peak_demand_winter: float,
    summer_peak: float,
    summer_part_peak: float,
    summer_off_peak: float,
    winter_peak: float,
    winter_super_off_peak: float,
    winter_off_peak: float,
    source_url: str,
    notes: str,
    demand_charges_override: tuple[DemandChargeComponent, ...] | None = None,
) -> TariffDefinition:
    """Build one B-19/B-20 family tariff.

    Every schedule in this family shares the same TOU hours -- peak 4-9 p.m.,
    summer part-peak 2-4 p.m. and 9-11 p.m., winter super-off-peak 9 a.m.-2
    p.m. in March through May -- and differs only in its rates, so they are
    built from one definition rather than transcribed separately.

    Demand components priced at zero on a given schedule (Option R prices
    winter peak-period demand at $0.00) are omitted rather than registered as
    zero-rate components; the bill is identical either way.
    """

    demand_charges = [
        DemandChargeComponent(
            name="maximum_demand",
            rate_per_kW=maximum_demand,
            basis=DemandChargeBasis.MAXIMUM,
        ),
    ]

    for component_name, rate, basis, season in (
        (
            "peak_period_demand_summer",
            peak_demand_summer,
            DemandChargeBasis.PEAK_PERIOD,
            Season.SUMMER,
        ),
        (
            "part_peak_period_demand_summer",
            part_peak_demand_summer,
            DemandChargeBasis.PART_PEAK_PERIOD,
            Season.SUMMER,
        ),
        (
            "peak_period_demand_winter",
            peak_demand_winter,
            DemandChargeBasis.PEAK_PERIOD,
            Season.WINTER,
        ),
    ):
        if rate > 0:
            demand_charges.append(
                DemandChargeComponent(
                    name=component_name,
                    rate_per_kW=rate,
                    basis=basis,
                    season=season,
                )
            )

    return TariffDefinition(
        tariff_id=tariff_id,
        name=name,
        utility="Pacific Gas and Electric",
        effective_start=date(2026, 3, 1),
        service_voltage_class=ServiceVoltageClass.SECONDARY,
        customer_class=CustomerClass.COMMERCIAL,
        service_type=ServiceType.BUNDLED,
        season_definition=PGE_SEASONS,
        daily_customer_charge=daily_customer_charge,
        demand_charges=(
            demand_charges_override
            if demand_charges_override is not None
            else tuple(demand_charges)
        ),
        tou_periods=(
            TOUPeriod(
                name="summer_peak",
                rate_per_kWh=summer_peak,
                start_hour=16,
                end_hour=21,
                season=Season.SUMMER,
                priority=30,
                demand_basis=DemandChargeBasis.PEAK_PERIOD,
            ),
            TOUPeriod(
                name="summer_part_peak_afternoon",
                rate_per_kWh=summer_part_peak,
                start_hour=14,
                end_hour=16,
                season=Season.SUMMER,
                priority=20,
                demand_basis=DemandChargeBasis.PART_PEAK_PERIOD,
            ),
            TOUPeriod(
                name="summer_part_peak_evening",
                rate_per_kWh=summer_part_peak,
                start_hour=21,
                end_hour=23,
                season=Season.SUMMER,
                priority=20,
                demand_basis=DemandChargeBasis.PART_PEAK_PERIOD,
            ),
            TOUPeriod(
                name="summer_off_peak",
                rate_per_kWh=summer_off_peak,
                start_hour=0,
                end_hour=0,  # full day, lowest priority
                season=Season.SUMMER,
                priority=0,
            ),
            TOUPeriod(
                name="winter_peak",
                rate_per_kWh=winter_peak,
                start_hour=16,
                end_hour=21,
                season=Season.WINTER,
                priority=30,
                demand_basis=DemandChargeBasis.PEAK_PERIOD,
            ),
            TOUPeriod(
                name="winter_super_off_peak",
                rate_per_kWh=winter_super_off_peak,
                start_hour=9,
                end_hour=14,
                season=Season.WINTER,
                months=frozenset({3, 4, 5}),
                priority=20,
            ),
            TOUPeriod(
                name="winter_off_peak",
                rate_per_kWh=winter_off_peak,
                start_hour=0,
                end_hour=0,  # full day, lowest priority
                season=Season.WINTER,
                priority=0,
            ),
        ),
        export_rule=ExportCompensationRule(
            name="not_modelled",
            implemented=False,
            note=(
                "Export compensation (NEM or the Net Billing Tariff) is not "
                "modelled. Configure an explicit fixed or CSV export price "
                "in the surplus configuration instead."
            ),
        ),
        source_url=source_url,
        version="2026-03-01",
        notes=notes,
    )


_FAMILY_NOT_MODELLED = (
    "Secondary voltage, bundled service only. Not modelled: Primary and "
    "Transmission voltage classes, the power-factor adjustment, Peak Day "
    "Pricing, and Schedule SB standby charges. `previous_peak_kw` carryover "
    "applies only to the all-hours monthly maximum-demand component."
)

# The Voluntary tier is the same rate schedule as Mandatory B-19 with a much
# smaller customer charge; it is open to customers below the 500 kW threshold
# that makes B-19 mandatory (Sheet 4).
PGE_B19_SECONDARY_VOLUNTARY_BUNDLED = register_tariff(
    _pge_large_demand_tou(
        tariff_id="pge_b19_secondary_voluntary_bundled_2026_03_01",
        name="PG&E B-19 Medium General Demand-Metered TOU Service (Voluntary)",
        daily_customer_charge=11.36882,
        maximum_demand=37.37,
        peak_demand_summer=46.16,
        part_peak_demand_summer=10.52,
        peak_demand_winter=2.31,
        summer_peak=0.18648,
        summer_part_peak=0.14775,
        summer_off_peak=0.12037,
        winter_peak=0.16188,
        winter_super_off_peak=0.06442,
        winter_off_peak=0.12026,
        source_url=B19_SOURCE_URL,
        notes=(
            "Voluntary tier: identical rates to Mandatory B-19 apart from the "
            "customer charge ($11.36882 rather than $58.62824 per day). "
            + _FAMILY_NOT_MODELLED
        ),
    )
)

# Option R moves cost out of demand and into energy, which suits renewable
# customers whose output cuts energy but not necessarily the monthly peak.
PGE_B19_SECONDARY_OPTION_R_BUNDLED = register_tariff(
    _pge_large_demand_tou(
        tariff_id="pge_b19_secondary_option_r_bundled_2026_03_01",
        name="PG&E B-19 Option R (Renewables), Mandatory Tier",
        daily_customer_charge=58.62824,
        maximum_demand=36.61,
        peak_demand_summer=6.50,
        part_peak_demand_summer=1.87,
        peak_demand_winter=0.00,  # Option R prices winter peak demand at zero
        summer_peak=0.43568,
        summer_part_peak=0.25184,
        summer_off_peak=0.19137,
        winter_peak=0.18276,
        winter_super_off_peak=0.10462,
        winter_off_peak=0.14044,
        source_url=B19_SOURCE_URL,
        notes=(
            "Option R, mandatory-tier customer charge. Eligibility rules for "
            "Option R enrolment are not modelled. " + _FAMILY_NOT_MODELLED
        ),
    )
)

def _option_s_demand_charges(
    *, excluded_hours_rate: float, all_hours_rate: float,
    summer_peak_rate: float, summer_part_peak_rate: float,
    winter_peak_rate: float,
) -> tuple[DemandChargeComponent, ...]:
    """Filed Option S: two distinct monthly maxima and daily TOU peaks."""
    return (
        DemandChargeComponent(
            "maximum_demand_excluding_09_to_14", excluded_hours_rate,
            excluded_local_hours=frozenset(range(9, 14)),
        ),
        DemandChargeComponent("maximum_demand_all_hours", all_hours_rate),
        DemandChargeComponent(
            "peak_period_demand_summer_daily", summer_peak_rate,
            basis=DemandChargeBasis.PEAK_PERIOD, season=Season.SUMMER,
            frequency=DemandChargeFrequency.DAILY,
        ),
        DemandChargeComponent(
            "part_peak_period_demand_summer_daily", summer_part_peak_rate,
            basis=DemandChargeBasis.PART_PEAK_PERIOD, season=Season.SUMMER,
            frequency=DemandChargeFrequency.DAILY,
        ),
        DemandChargeComponent(
            "peak_period_demand_winter_daily", winter_peak_rate,
            basis=DemandChargeBasis.PEAK_PERIOD, season=Season.WINTER,
            frequency=DemandChargeFrequency.DAILY,
        ),
    )


# Option S trades lower monthly demand rates for daily peak charges and
# higher energy rates. These two monthly maxima must not be combined.
PGE_B19_SECONDARY_OPTION_S_BUNDLED = register_tariff(
    _pge_large_demand_tou(
        tariff_id="pge_b19_secondary_option_s_bundled_2026_03_01",
        name="PG&E B-19 Option S (Storage), Mandatory Tier",
        daily_customer_charge=58.62824,
        maximum_demand=6.35 + 9.13,
        peak_demand_summer=1.60,
        part_peak_demand_summer=0.08,
        peak_demand_winter=1.22,
        demand_charges_override=_option_s_demand_charges(
            excluded_hours_rate=6.35, all_hours_rate=9.13,
            summer_peak_rate=1.60, summer_part_peak_rate=0.08,
            winter_peak_rate=1.22,
        ),
        summer_peak=0.43568,
        summer_part_peak=0.25184,
        summer_off_peak=0.19137,
        winter_peak=0.18276,
        winter_super_off_peak=0.10462,
        winter_off_peak=0.14044,
        source_url=B19_SOURCE_URL,
        notes=(
            "Option S, mandatory-tier customer charge. Requires a storage "
            "system rated at least 10 percent of the account's peak demand "
            "over the previous twelve months, and is subject to an enrolment "
            "cap; neither condition is modelled. " + _FAMILY_NOT_MODELLED
        ),
    )
)

PGE_B20_SECONDARY_OPTION_R_BUNDLED = register_tariff(
    _pge_large_demand_tou(
        tariff_id="pge_b20_secondary_option_r_bundled_2026_03_01",
        name="PG&E B-20 Option R (Renewables)",
        daily_customer_charge=107.36636,
        maximum_demand=38.23,
        peak_demand_summer=5.62,
        part_peak_demand_summer=1.61,
        peak_demand_winter=0.00,  # Option R prices winter peak demand at zero
        summer_peak=0.40620,
        summer_part_peak=0.22337,
        summer_off_peak=0.16434,
        winter_peak=0.17396,
        winter_super_off_peak=0.09448,
        winter_off_peak=0.13023,
        source_url=B20_SOURCE_URL,
        notes=(
            "Option R. Eligibility rules for Option R enrolment are not "
            "modelled. " + _FAMILY_NOT_MODELLED
        ),
    )
)

PGE_B20_SECONDARY_OPTION_S_BUNDLED = register_tariff(
    _pge_large_demand_tou(
        tariff_id="pge_b20_secondary_option_s_bundled_2026_03_01",
        name="PG&E B-20 Option S (Storage)",
        daily_customer_charge=107.36636,
        maximum_demand=5.56 + 11.06,
        peak_demand_summer=1.30,
        part_peak_demand_summer=0.07,
        peak_demand_winter=1.02,
        demand_charges_override=_option_s_demand_charges(
            excluded_hours_rate=5.56, all_hours_rate=11.06,
            summer_peak_rate=1.30, summer_part_peak_rate=0.07,
            winter_peak_rate=1.02,
        ),
        summer_peak=0.40620,
        summer_part_peak=0.22337,
        summer_off_peak=0.16434,
        winter_peak=0.17396,
        winter_super_off_peak=0.09448,
        winter_off_peak=0.13023,
        source_url=B20_SOURCE_URL,
        notes=(
            "Option S. Requires a storage system rated at least 10 percent "
            "of the account's peak demand over the previous twelve months, "
            "and is subject to an enrolment cap; neither condition is "
            "modelled. " + _FAMILY_NOT_MODELLED
        ),
    )
)

def default_commercial_tariff() -> TariffDefinition:
    return PGE_B10_SECONDARY_BUNDLED


# PG&E historical Commercial (B) workbook, September–December 2025.
# First worksheet C16:C17 / J15:J19; final worksheet B-6 TOU periods.
B6_2025_SOURCE_URL = (
    "https://www.pge.com/assets/rates/tariffs/Commercial_B_Sch_250901-251231.xlsx"
)


def _historical_b6_2025(current: TariffDefinition) -> TariffDefinition:
    rates = {
        "summer_peak": 0.67220, "summer_off_peak": 0.41458,
        "winter_peak": 0.42551, "winter_off_peak": 0.38192,
        "winter_super_off_peak": 0.34584,
    }
    return register_tariff(replace(
        current,
        tariff_id=current.tariff_id.replace("2026_03_01", "2025_09_01"),
        effective_start=date(2025, 9, 1), effective_end=date(2025, 12, 31),
        version="2025-09-01", source_url=B6_2025_SOURCE_URL,
        tou_periods=tuple(replace(period, rate_per_kWh=rates[period.name])
                          for period in current.tou_periods),
    ))


PGE_B6_SECONDARY_SINGLE_PHASE_BUNDLED_2025 = _historical_b6_2025(
    PGE_B6_SECONDARY_SINGLE_PHASE_BUNDLED)
PGE_B6_SECONDARY_POLYPHASE_BUNDLED_2025 = _historical_b6_2025(
    PGE_B6_SECONDARY_POLYPHASE_BUNDLED)
