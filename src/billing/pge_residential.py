"""PG&E residential tariff definitions.

Rates below are transcribed from PG&E's published tariff book and are valid
for the stated effective date only. They are **versioned data**: when PG&E
files new rates, add a new :class:`TariffDefinition` with its own effective
window rather than editing these numbers in place, so historical analyses stay
reproducible.

Residential service differs from the B-series structurally, not just in
price: peaks are weekday-only, there is no demand charge, and the fixed
charge is income-graduated. Schedules whose energy price depends on
cumulative usage against a baseline allowance (E-1, E-TOU-C) are not
here yet -- the tariff model has no tier concept.
"""

from datetime import date

from .pge_common import PGE_SEASONS
from .baseline import BaselineAllowance, BaselineCode, BaselineTerritory
from .plans import RatePlan, RatePlanIdentity, register_plan
from .tariffs import (
    EnergyTier,
    CustomerClass,
    DemandChargeBasis,
    DemandChargeComponent,
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

E_TOU_D_SOURCE_URL = (
    "https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-TOU-D.pdf"
)

# PG&E's first residential schedule in this registry, and the first anywhere
# in it whose peak is weekday-only: 5-8 p.m. Monday through Friday, with
# "all other times including Holidays" off-peak. That is why `TOUPeriod`
# grew a `days` field -- every B-series period applies every day, so the
# commercial work never needed one.
#
# Rates are the Total Bundled Rates from Sheet 2 (Advice 7921-E, effective
# 1 June 2026). Seasons match the B-series: summer is 1 June through
# 30 September, winter 1 October through 31 May.
#
# The base services charge is income-graduated, so the schedule is one rate
# structure with three customer charges rather than three schedules. Each
# tier is registered separately, the same way B-1 registers single-phase and
# polyphase.
def _pge_e_tou_d_bundled(
    *,
    tariff_id: str,
    name: str,
    daily_customer_charge: float,
) -> TariffDefinition:
    return TariffDefinition(
        tariff_id=tariff_id,
        name=name,
        utility="Pacific Gas and Electric",
        effective_start=date(2026, 6, 1),
        service_voltage_class=ServiceVoltageClass.SECONDARY,
        customer_class=CustomerClass.RESIDENTIAL,
        service_type=ServiceType.BUNDLED,
        season_definition=PGE_SEASONS,
        # $ per customer per day, by income tier.
        daily_customer_charge=daily_customer_charge,
        # Residential service is not demand metered.
        demand_charges=(),
        tou_periods=(
            TOUPeriod(
                name="summer_peak",
                rate_per_kWh=0.47708,
                start_hour=17,
                end_hour=20,
                season=Season.SUMMER,
                days=WEEKDAYS,
                priority=30,
            ),
            TOUPeriod(
                name="summer_off_peak",
                rate_per_kWh=0.34212,
                start_hour=0,
                end_hour=0,  # full day, lowest priority
                season=Season.SUMMER,
                priority=0,
            ),
            TOUPeriod(
                name="winter_peak",
                rate_per_kWh=0.38747,
                start_hour=17,
                end_hour=20,
                season=Season.WINTER,
                days=WEEKDAYS,
                priority=30,
            ),
            TOUPeriod(
                name="winter_off_peak",
                rate_per_kWh=0.34886,
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
                "E-TOU-D export compensation (NEM or the Net Billing Tariff) "
                "is not modelled. Configure an explicit fixed or CSV export "
                "price in the surplus configuration instead."
            ),
        ),
        source_url=E_TOU_D_SOURCE_URL,
        version="2026-06-01",
        notes=(
            "Residential time-of-use, voluntary opt-in. Peak is 5-8 p.m. "
            "Monday through Friday; all other hours, weekends and holidays "
            "are off-peak. Holidays are NOT modelled -- a public holiday "
            "falling on a weekday is priced at the weekday peak rate, which "
            "overstates the bill for those few days. Also not modelled: the "
            "California Climate Credit ($36.18 per household, paid in the "
            "August and September bill cycles), CARE and FERA discounts, "
            "Standby Service under Schedule S, CCA and Direct Access."
        ),
    )


PGE_E_TOU_D_RESIDENTIAL_TIER1_BUNDLED = register_tariff(
    _pge_e_tou_d_bundled(
        tariff_id="pge_e_tou_d_residential_tier1_bundled_2026_06_01",
        name="PG&E E-TOU-D Residential TOU 5-8 p.m. (Income Tier 1)",
        daily_customer_charge=0.19713,
    )
)

PGE_E_TOU_D_RESIDENTIAL_TIER2_BUNDLED = register_tariff(
    _pge_e_tou_d_bundled(
        tariff_id="pge_e_tou_d_residential_tier2_bundled_2026_06_01",
        name="PG&E E-TOU-D Residential TOU 5-8 p.m. (Income Tier 2)",
        daily_customer_charge=0.39688,
    )
)

PGE_E_TOU_D_RESIDENTIAL_TIER3_BUNDLED = register_tariff(
    _pge_e_tou_d_bundled(
        tariff_id="pge_e_tou_d_residential_tier3_bundled_2026_06_01",
        name="PG&E E-TOU-D Residential TOU 5-8 p.m. (Income Tier 3)",
        daily_customer_charge=0.79343,
    )
)


E_1_SOURCE_URL = (
    "https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-1.pdf"
)

# PG&E's default residential schedule, and the first tiered rate in this
# registry. E-1 has no time-of-use periods at all -- no peak, no off-peak,
# nothing in the filed schedule mentions either -- so the price of a kWh
# depends only on how many kWh came before it in the billing period.
#
# That is why the single TOU period below spans the whole day at the Tier 1
# rate: `TariffDefinition` requires at least one period, but for a tiered
# schedule `charges` prices the period total through `energy_tiers` and never
# uses the per-interval rate. The period is there to satisfy the shape, and
# its rate is the tier-1 rate so any caller reading `energy_rates` directly
# sees the baseline price rather than something invented.
#
# Tier bounds are percentages of the baseline allowance (see `baseline.py`):
# 0-100%, 101-400%, and above 400%. PG&E currently prices the top two
# identically at $0.40702 -- the over-400% tier is what remains of the High
# Usage Surcharge -- but both are kept so a future filing that separates them
# is a rate change rather than a redesign.
#
# Rates are the Total Bundled Rates from Sheet 1 (Advice 7921-E, effective
# 1 June 2026); baseline quantities are Special Condition 2, Sheet 4.
E_1_TIERS = (
    EnergyTier(
        name="tier_1_baseline",
        rate_per_kWh=0.32561,
        upper_bound_fraction=1.0,
    ),
    EnergyTier(
        name="tier_2_over_baseline",
        rate_per_kWh=0.40702,
        upper_bound_fraction=4.0,
    ),
    EnergyTier(
        name="tier_2_over_400_percent",
        rate_per_kWh=0.40702,
        upper_bound_fraction=None,
    ),
)


def _pge_e1_bundled(
    *,
    tariff_id: str,
    name: str,
    daily_customer_charge: float,
    baseline: BaselineAllowance,
) -> TariffDefinition:
    return TariffDefinition(
        tariff_id=tariff_id,
        name=name,
        utility="Pacific Gas and Electric",
        effective_start=date(2026, 6, 1),
        service_voltage_class=ServiceVoltageClass.SECONDARY,
        customer_class=CustomerClass.RESIDENTIAL,
        service_type=ServiceType.BUNDLED,
        season_definition=PGE_SEASONS,
        daily_customer_charge=daily_customer_charge,
        demand_charges=(),
        energy_tiers=E_1_TIERS,
        baseline=baseline,
        tou_periods=(
            TOUPeriod(
                name="all_usage",
                rate_per_kWh=0.32561,
                start_hour=0,
                end_hour=0,  # the whole day, every day, all year
                priority=0,
            ),
        ),
        export_rule=ExportCompensationRule(
            name="not_modelled",
            implemented=False,
            note=(
                "E-1 export compensation (NEM or the Net Billing Tariff) is "
                "not modelled. Configure an explicit fixed or CSV export "
                "price in the surplus configuration instead."
            ),
        ),
        source_url=E_1_SOURCE_URL,
        version="2026-06-01",
        notes=(
            "Residential service, tiered by usage against a baseline "
            "allowance; no time-of-use periods and no demand charge. "
            f"Defaults to baseline territory {baseline.territory.value} "
            f"({baseline.code.value}) -- territory is a property of the "
            "premises, set by county and elevation, so pass an explicit "
            "BaselineAllowance when the site is elsewhere. Not modelled: the "
            "California Climate Credit ($36.18 per household, paid in the "
            "August and September bill cycles), CARE and FERA discounts, "
            "Standby Service under Schedule S, CCA and Direct Access."
        ),
    )


#: Territory T is the whole City and County of San Francisco, and the default
#: here because it is the site the repository's example runs use.
DEFAULT_BASELINE = BaselineAllowance(
    territory=BaselineTerritory.T,
    code=BaselineCode.BASIC,
)

PGE_E1_RESIDENTIAL_TIER1_BUNDLED = register_tariff(
    _pge_e1_bundled(
        tariff_id="pge_e1_residential_tier1_bundled_2026_06_01",
        name="PG&E E-1 Residential Tiered (Income Tier 1)",
        daily_customer_charge=0.19713,
        baseline=DEFAULT_BASELINE,
    )
)

PGE_E1_RESIDENTIAL_TIER2_BUNDLED = register_tariff(
    _pge_e1_bundled(
        tariff_id="pge_e1_residential_tier2_bundled_2026_06_01",
        name="PG&E E-1 Residential Tiered (Income Tier 2)",
        daily_customer_charge=0.39688,
        baseline=DEFAULT_BASELINE,
    )
)

PGE_E1_RESIDENTIAL_TIER3_BUNDLED = register_tariff(
    _pge_e1_bundled(
        tariff_id="pge_e1_residential_tier3_bundled_2026_06_01",
        name="PG&E E-1 Residential Tiered (Income Tier 3)",
        daily_customer_charge=0.79343,
        baseline=DEFAULT_BASELINE,
    )
)


E_ELEC_SOURCE_URL = (
    "https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-ELEC.pdf"
)

EV2_SOURCE_URL = (
    "https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_EV2%20(Sch).pdf"
)


def _pge_electrified_home_bundled(
    *,
    tariff_id: str,
    name: str,
    daily_customer_charge: float,
    summer_peak: float,
    summer_part_peak: float,
    summer_off_peak: float,
    winter_peak: float,
    winter_part_peak: float,
    winter_off_peak: float,
    source_url: str,
    notes: str,
) -> TariffDefinition:
    """E-ELEC and EV2 share one period structure and differ only in price.

    Both price a 4-9 p.m. peak **every day, including weekends and holidays**
    -- unlike E-TOU-D, whose peak is weekday-only -- with partial-peak
    shoulders at 3-4 p.m. and 9 p.m.-midnight. The shoulders are two blocks
    because they are two separate windows; they always share a rate, and the
    reference generator collapses them into one column on that basis.
    """

    return TariffDefinition(
        tariff_id=tariff_id,
        name=name,
        utility="Pacific Gas and Electric",
        effective_start=date(2026, 6, 1),
        service_voltage_class=ServiceVoltageClass.SECONDARY,
        customer_class=CustomerClass.RESIDENTIAL,
        service_type=ServiceType.BUNDLED,
        season_definition=PGE_SEASONS,
        daily_customer_charge=daily_customer_charge,
        demand_charges=(),
        tou_periods=(
            TOUPeriod(
                name="summer_peak",
                rate_per_kWh=summer_peak,
                start_hour=16,
                end_hour=21,
                season=Season.SUMMER,
                priority=30,
            ),
            TOUPeriod(
                name="summer_part_peak_afternoon",
                rate_per_kWh=summer_part_peak,
                start_hour=15,
                end_hour=16,
                season=Season.SUMMER,
                priority=20,
            ),
            TOUPeriod(
                name="summer_part_peak_evening",
                rate_per_kWh=summer_part_peak,
                start_hour=21,
                end_hour=24,
                season=Season.SUMMER,
                priority=20,
            ),
            TOUPeriod(
                name="summer_off_peak",
                rate_per_kWh=summer_off_peak,
                start_hour=0,
                end_hour=0,  # the rest of the day, lowest priority
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
            ),
            TOUPeriod(
                name="winter_part_peak_afternoon",
                rate_per_kWh=winter_part_peak,
                start_hour=15,
                end_hour=16,
                season=Season.WINTER,
                priority=20,
            ),
            TOUPeriod(
                name="winter_part_peak_evening",
                rate_per_kWh=winter_part_peak,
                start_hour=21,
                end_hour=24,
                season=Season.WINTER,
                priority=20,
            ),
            TOUPeriod(
                name="winter_off_peak",
                rate_per_kWh=winter_off_peak,
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
                "Export compensation (NEM or the Net Billing Tariff) is not "
                "modelled. Configure an explicit fixed or CSV export price in "
                "the surplus configuration instead."
            ),
        ),
        source_url=source_url,
        version="2026-06-01",
        notes=notes,
    )


_E_ELEC_NOTES = (
    "Residential time-of-use for an electrified home; requires a qualifying "
    "electric technology (heat pump space or water heating, or an electric "
    "vehicle). Peak is 4-9 p.m. every day, including weekends and holidays, "
    "so no day-of-week restriction applies. No baseline tiers and no demand "
    "charge. Not modelled: the qualifying-technology eligibility test itself, "
    "the California Climate Credit ($36.18 per household, paid in the August "
    "and September bill cycles), CARE and FERA discounts, Standby Service "
    "under Schedule S, CCA and Direct Access."
)

_EV2_NOTES = (
    "Residential time-of-use for a household with a plug-in electric "
    "vehicle (PG&E Schedule EV2, rate option A). Same period structure as "
    "E-ELEC -- 4-9 p.m. peak every day including weekends and holidays -- "
    "but a far cheaper off-peak, which is the whole point: it prices "
    "overnight charging at $0.22558/kWh in both seasons. No baseline tiers "
    "and no demand charge. Not modelled: the EV-ownership eligibility test, "
    "the California Climate Credit, CARE and FERA discounts, Standby Service "
    "under Schedule S, CCA and Direct Access."
)

# Rates are the Total Bundled Rates from Sheet 2 of each schedule
# (Advice 7921-E, effective 1 June 2026). The three registrations per
# schedule differ only in the income-graduated base services charge, the same
# way B-1 registers single-phase and polyphase.
PGE_E_ELEC_RESIDENTIAL_TIER1_BUNDLED = register_tariff(
    _pge_electrified_home_bundled(
        tariff_id="pge_e_elec_residential_tier1_bundled_2026_06_01",
        name="PG&E E-ELEC Residential Electric Home (Income Tier 1)",
        daily_customer_charge=0.19713,
        summer_peak=0.55214,
        summer_part_peak=0.39026,
        summer_off_peak=0.33358,
        winter_peak=0.32063,
        winter_part_peak=0.29854,
        winter_off_peak=0.28468,
        source_url=E_ELEC_SOURCE_URL,
        notes=_E_ELEC_NOTES,
    )
)

PGE_E_ELEC_RESIDENTIAL_TIER2_BUNDLED = register_tariff(
    _pge_electrified_home_bundled(
        tariff_id="pge_e_elec_residential_tier2_bundled_2026_06_01",
        name="PG&E E-ELEC Residential Electric Home (Income Tier 2)",
        daily_customer_charge=0.39688,
        summer_peak=0.55214,
        summer_part_peak=0.39026,
        summer_off_peak=0.33358,
        winter_peak=0.32063,
        winter_part_peak=0.29854,
        winter_off_peak=0.28468,
        source_url=E_ELEC_SOURCE_URL,
        notes=_E_ELEC_NOTES,
    )
)

PGE_E_ELEC_RESIDENTIAL_TIER3_BUNDLED = register_tariff(
    _pge_electrified_home_bundled(
        tariff_id="pge_e_elec_residential_tier3_bundled_2026_06_01",
        name="PG&E E-ELEC Residential Electric Home (Income Tier 3)",
        daily_customer_charge=0.79343,
        summer_peak=0.55214,
        summer_part_peak=0.39026,
        summer_off_peak=0.33358,
        winter_peak=0.32063,
        winter_part_peak=0.29854,
        winter_off_peak=0.28468,
        source_url=E_ELEC_SOURCE_URL,
        notes=_E_ELEC_NOTES,
    )
)

PGE_EV2_RESIDENTIAL_TIER1_BUNDLED = register_tariff(
    _pge_electrified_home_bundled(
        tariff_id="pge_ev2_residential_tier1_bundled_2026_06_01",
        name="PG&E EV2-A Residential Electric Vehicle (Income Tier 1)",
        daily_customer_charge=0.19713,
        summer_peak=0.53809,
        summer_part_peak=0.42760,
        summer_off_peak=0.22558,
        winter_peak=0.41099,
        winter_part_peak=0.39428,
        winter_off_peak=0.22558,
        source_url=EV2_SOURCE_URL,
        notes=_EV2_NOTES,
    )
)

PGE_EV2_RESIDENTIAL_TIER2_BUNDLED = register_tariff(
    _pge_electrified_home_bundled(
        tariff_id="pge_ev2_residential_tier2_bundled_2026_06_01",
        name="PG&E EV2-A Residential Electric Vehicle (Income Tier 2)",
        daily_customer_charge=0.39688,
        summer_peak=0.53809,
        summer_part_peak=0.42760,
        summer_off_peak=0.22558,
        winter_peak=0.41099,
        winter_part_peak=0.39428,
        winter_off_peak=0.22558,
        source_url=EV2_SOURCE_URL,
        notes=_EV2_NOTES,
    )
)

PGE_EV2_RESIDENTIAL_TIER3_BUNDLED = register_tariff(
    _pge_electrified_home_bundled(
        tariff_id="pge_ev2_residential_tier3_bundled_2026_06_01",
        name="PG&E EV2-A Residential Electric Vehicle (Income Tier 3)",
        daily_customer_charge=0.79343,
        summer_peak=0.53809,
        summer_part_peak=0.42760,
        summer_off_peak=0.22558,
        winter_peak=0.41099,
        winter_part_peak=0.39428,
        winter_off_peak=0.22558,
        source_url=EV2_SOURCE_URL,
        notes=_EV2_NOTES,
    )
)


# --- E-1 rate history ----------------------------------------------------
#
# PG&E refiled residential rates seven times during 2024 alone. Each window below
# is one filed rate document from PG&E's historical rate index; the rates are
# read from the "Res Inclu TOU" sheet of that workbook, from the row headed
# "Residential Schedules: E-1, EM, ES, ESR, ET".
#
# Two structural differences from the 2026 versions, both deliberate:
#
# * 2024 has **no Base Services Charge**. Its fixed provision is a "Delivery
#   Minimum Bill Amount" -- a floor under the bill, not an addition to it.
#   Modelling it as a customer charge would add roughly $11.65 a month that
#   PG&E did not charge, so it is carried as ``daily_minimum_bill``.
# * 2024 has **no income tiers**. The income-graduated charge arrives later,
#   which is exactly why a plan's identity and its versions are separate: an
#   income-tier-3 customer today was on E-1 in 2024, under rates that drew no
#   income distinction. All three income-tier plans therefore share these
#   2024 versions.
#
# **2026-03-01 to 2026-05-31 is deliberately not transcribed.** Two sources
# disagree about it. PG&E's rate workbook that carries the current numbers
# (0.32561 tier 1) labels its sheet `Res Inclu TOU_260301-Present`, implying
# they took effect on 1 March 2026. The filed tariff PDF for the same rates
# says Advice 7921-E, **Effective June 1, 2026**. The filed tariff is the
# authoritative document, so the current version starts 1 June; the workbook
# that would have covered March-May has been overwritten by the rolling
# `current` file, so those rates are not available. Billing a date in that
# window raises rather than picking one of the two readings.
E_1_HISTORICAL_SOURCE = (
    "https://www.pge.com/tariffs/en/rate-information/electric-rates.html"
)

_E_1_HISTORICAL_WINDOWS = (
    # (start, end, minimum bill $/day, tier 1, tier 2, tier 2 continued, file)
    (date(2024, 1, 1), date(2024, 2, 29), 0.37612, 0.42009, 0.52566, 0.52566,
     "Res_Inclu_TOU_240101-240229.xlsx"),
    (date(2024, 3, 1), date(2024, 3, 31), 0.39167, 0.42101, 0.52708, 0.52708,
     "Res_Inclu_TOU_240301-240331.xlsx"),
    (date(2024, 4, 1), date(2024, 5, 31), 0.39167, 0.42676, 0.53406, 0.53406,
     "Res_Inclu_TOU_240401-240531.xlsx"),
    (date(2024, 6, 1), date(2024, 6, 30), 0.39167, 0.42676, 0.53406, 0.53406,
     "Res_Inclu_TOU_240601-240630.xlsx"),
    (date(2024, 7, 1), date(2024, 8, 31), 0.39167, 0.38828, 0.48617, 0.48617,
     "Res_Inclu_TOU_240701-240831.xlsx"),
    (date(2024, 9, 1), date(2024, 9, 30), 0.39167, 0.39033, 0.48870, 0.48870,
     "Res_Inclu_TOU_240901-240930.xlsx"),
    (date(2024, 10, 1), date(2024, 12, 31), 0.39167, 0.40206, 0.50323, 0.50323,
     "Res_Inclu_TOU_241001-241231.xlsx"),
    (date(2025, 1, 1), date(2025, 2, 28), 0.39167, 0.40122, 0.50257, 0.50257,
     "Res_Inclu_TOU_250101-250228.xlsx"),
    (date(2025, 3, 1), date(2025, 8, 31), 0.40317, 0.40730, 0.51031, 0.51031,
     "Res_Inclu_TOU_250301-250831.xlsx"),
    (date(2025, 9, 1), date(2025, 12, 31), 0.40317, 0.39834, 0.49918, 0.49918,
     "Res_Inclu_TOU_250901-251231.xlsx"),
    (date(2026, 1, 1), date(2026, 2, 28), 0.40317, 0.37839, 0.47405, 0.47405,
     "Res_Inclu_TOU_260101-260228.xlsx"),
)


def _pge_e1_2024_version(
    *,
    effective_start: date,
    effective_end: date,
    daily_minimum_bill: float,
    tier_1: float,
    tier_2: float,
    tier_2_continued: float,
    source_sheet: str,
) -> TariffDefinition:
    stamp = effective_start.strftime("%Y_%m_%d")

    return TariffDefinition(
        tariff_id=f"pge_e1_residential_bundled_{stamp}",
        name=(
            f"PG&E E-1 Residential Tiered "
            f"({effective_start:%Y-%m-%d} to {effective_end:%Y-%m-%d})"
        ),
        utility="Pacific Gas and Electric",
        effective_start=effective_start,
        effective_end=effective_end,
        service_voltage_class=ServiceVoltageClass.SECONDARY,
        customer_class=CustomerClass.RESIDENTIAL,
        service_type=ServiceType.BUNDLED,
        season_definition=PGE_SEASONS,
        daily_minimum_bill=daily_minimum_bill,
        demand_charges=(),
        energy_tiers=(
            EnergyTier(
                name="tier_1_baseline",
                rate_per_kWh=tier_1,
                upper_bound_fraction=1.0,
            ),
            EnergyTier(
                name="tier_2_over_baseline",
                rate_per_kWh=tier_2,
                upper_bound_fraction=4.0,
            ),
            EnergyTier(
                name="tier_2_over_400_percent",
                rate_per_kWh=tier_2_continued,
                upper_bound_fraction=None,
            ),
        ),
        baseline=DEFAULT_BASELINE,
        tou_periods=(
            TOUPeriod(
                name="all_usage",
                rate_per_kWh=tier_1,
                start_hour=0,
                end_hour=0,
                priority=0,
            ),
        ),
        export_rule=ExportCompensationRule(
            name="not_modelled",
            implemented=False,
            note=(
                "E-1 export compensation (NEM or the Net Billing Tariff) is "
                "not modelled. Configure an explicit fixed or CSV export "
                "price in the surplus configuration instead."
            ),
        ),
        source_url=E_1_HISTORICAL_SOURCE,
        version=effective_start.isoformat(),
        notes=(
            f"Historical E-1, transcribed from {source_sheet} on PG&E's "
            f"historical rate index. No Base Services Charge existed on this "
            f"date; the fixed provision is a Delivery Minimum Bill of "
            f"${daily_minimum_bill:.5f} per meter per day, applied as a floor "
            f"under the bill rather than added to it. No income tiers. "
            f"Bundled service only. Not modelled: CARE and FERA discounts, "
            f"the California Climate Credit, CCA and Direct Access."
        ),
    )


PGE_E1_HISTORICAL_VERSIONS = tuple(
    register_tariff(
        _pge_e1_2024_version(
            effective_start=start,
            effective_end=end,
            daily_minimum_bill=minimum,
            tier_1=tier_1,
            tier_2=tier_2,
            tier_2_continued=tier_2_continued,
            source_sheet=sheet,
        )
    )
    for start, end, minimum, tier_1, tier_2, tier_2_continued, sheet
    in _E_1_HISTORICAL_WINDOWS
)


# --- Historical TOU versions ----------------------------------------------
#
# E-TOU-D, EV2 and E-ELEC read from the same workbooks as the E-1 history:
# the "Res Inclu TOU" sheet carries E-TOU-D, the "ElecVehicle&Tech" sheet
# carries EV2 and E-ELEC. Each schedule's block is bounded by the next
# labelled row, which matters -- EV2 and E-ELEC sit adjacent and share season
# and period labels, so an unbounded read silently mixes one into the other.
#
# Fixed provisions differ by schedule and by era, and are not interchangeable:
#
# * E-TOU-D and EV2 carried a Delivery Minimum Bill (a floor) before the
#   income-graduated Base Services Charge replaced it in 2026.
# * E-ELEC has always carried a Base Services Charge -- a flat $0.49281 per
#   day throughout 2024 and 2025 -- because the schedule was designed around
#   one. It became income-graduated with the others in 2026.
#
# 2026-03-01 to 2026-05-31 is absent here for the same reason it is absent
# from the E-1 history: the filed tariff dates the current rates from 1 June
# 2026 and no source states what applied in between.
_TOU_HISTORICAL_WINDOWS = (
    # (start, end,
    #  E-TOU-D: min bill, summer peak, summer off, winter peak, winter off,
    #  EV2: min bill, summer peak/part/off, winter peak/part/off,
    #  E-ELEC: base services charge, summer peak/part/off,
    #          winter peak/part/off,
    #  source workbook)
    (date(2024, 1, 1), date(2024, 2, 29),
     0.37612, 0.58758, 0.45262, 0.49798, 0.45937,
     0.37612, 0.65713, 0.54664, 0.34462,
     0.53002, 0.51332, 0.34462,
     0.49281, 0.6358, 0.47392, 0.41724,
     0.40429, 0.3822, 0.36834,
     "Res_Inclu_TOU_240101-240229.xlsx"),
    (date(2024, 3, 1), date(2024, 3, 31),
     0.39167, 0.58873, 0.45377, 0.49913, 0.46052,
     0.39167, 0.65828, 0.54779, 0.34578,
     0.53117, 0.51447, 0.34578,
     0.49281, 0.63702, 0.47514, 0.41846,
     0.40551, 0.38342, 0.36956,
     "Res_Inclu_TOU_240301-240331.xlsx"),
    (date(2024, 4, 1), date(2024, 5, 31),
     0.39167, 0.59505, 0.46009, 0.50545, 0.46684,
     0.39167, 0.6646, 0.55411, 0.3521,
     0.53749, 0.52079, 0.3521,
     0.49281, 0.64328, 0.4814, 0.42472,
     0.41177, 0.38968, 0.37582,
     "Res_Inclu_TOU_240401-240531.xlsx"),
    (date(2024, 6, 1), date(2024, 6, 30),
     0.39167, 0.59505, 0.46009, 0.50545, 0.46684,
     0.39167, 0.6646, 0.55411, 0.3521,
     0.53749, 0.52079, 0.3521,
     0.49281, 0.64328, 0.4814, 0.42472,
     0.41177, 0.38968, 0.37582,
     "Res_Inclu_TOU_240601-240630.xlsx"),
    (date(2024, 7, 1), date(2024, 8, 31),
     0.39167, 0.55219, 0.41723, 0.46259, 0.42398,
     0.39167, 0.62174, 0.51125, 0.30924,
     0.49463, 0.47793, 0.30924,
     0.49281, 0.60054, 0.43866, 0.38198,
     0.36902, 0.34693, 0.33307,
     "Res_Inclu_TOU_240701-240831.xlsx"),
    (date(2024, 9, 1), date(2024, 9, 30),
     0.39167, 0.55447, 0.41951, 0.46486, 0.42625,
     0.39167, 0.62402, 0.51353, 0.31151,
     0.49691, 0.48021, 0.31151,
     0.49281, 0.6028, 0.44092, 0.38424,
     0.37129, 0.3492, 0.33534,
     "Res_Inclu_TOU_240901-240930.xlsx"),
    (date(2024, 10, 1), date(2024, 12, 31),
     0.39167, 0.56749, 0.43253, 0.47789, 0.43928,
     0.39167, 0.63704, 0.52655, 0.32454,
     0.50993, 0.49323, 0.32454,
     0.49281, 0.61578, 0.4539, 0.39722,
     0.38426, 0.36217, 0.34831,
     "Res_Inclu_TOU_241001-241231.xlsx"),
    (date(2025, 1, 1), date(2025, 2, 28),
     0.39167, 0.56462, 0.42966, 0.47502, 0.43641,
     0.39167, 0.6159, 0.50541, 0.30339,
     0.48879, 0.47209, 0.30339,
     0.49281, 0.60728, 0.4454, 0.38872,
     0.37577, 0.35368, 0.33982,
     "Res_Inclu_TOU_250101-250228.xlsx"),
    (date(2025, 3, 1), date(2025, 8, 31),
     0.40317, 0.57149, 0.43653, 0.48189, 0.44328,
     0.40317, 0.62277, 0.51228, 0.31026,
     0.49566, 0.47896, 0.31027,
     0.49281, 0.61418, 0.4523, 0.39562,
     0.38266, 0.36057, 0.34671,
     "Res_Inclu_TOU_250301-250831.xlsx"),
    (date(2025, 9, 1), date(2025, 12, 31),
     0.40317, 0.56158, 0.42662, 0.47198, 0.43337,
     0.40317, 0.61286, 0.50237, 0.30036,
     0.48575, 0.46905, 0.30036,
     0.49281, 0.6043, 0.44242, 0.38574,
     0.37279, 0.3507, 0.33684,
     "Res_Inclu_TOU_250901-251231.xlsx"),
    (date(2026, 1, 1), date(2026, 2, 28),
     0.40317, 0.53623, 0.40127, 0.44662, 0.40801,
     0.40317, 0.59724, 0.48675, 0.28474,
     0.47013, 0.45343, 0.28474,
     0.49281, 0.57908, 0.4172, 0.36052,
     0.34756, 0.32547, 0.31161,
     "Res_Inclu_TOU_260101-260228.xlsx"),
)


def _historical_tou_version(
    *,
    tariff_id: str,
    name: str,
    effective_start: date,
    effective_end: date,
    daily_minimum_bill: float | None,
    daily_customer_charge: float | None,
    tou_periods: tuple[TOUPeriod, ...],
    source_sheet: str,
    schedule_note: str,
) -> TariffDefinition:
    if daily_minimum_bill is not None:
        fixed = (
            f"a Delivery Minimum Bill of ${daily_minimum_bill:.5f} per meter "
            f"per day, applied as a floor under the bill rather than added "
            f"to it"
        )
    else:
        fixed = (
            f"a flat Base Services Charge of ${daily_customer_charge:.5f} "
            f"per customer per day, not yet income-graduated"
        )

    return TariffDefinition(
        tariff_id=tariff_id,
        name=name,
        utility="Pacific Gas and Electric",
        effective_start=effective_start,
        effective_end=effective_end,
        service_voltage_class=ServiceVoltageClass.SECONDARY,
        customer_class=CustomerClass.RESIDENTIAL,
        service_type=ServiceType.BUNDLED,
        season_definition=PGE_SEASONS,
        daily_minimum_bill=daily_minimum_bill,
        daily_customer_charge=daily_customer_charge,
        demand_charges=(),
        tou_periods=tou_periods,
        export_rule=ExportCompensationRule(
            name="not_modelled",
            implemented=False,
            note=(
                "Export compensation (NEM or the Net Billing Tariff) is not "
                "modelled. Configure an explicit fixed or CSV export price in "
                "the surplus configuration instead."
            ),
        ),
        source_url=E_1_HISTORICAL_SOURCE,
        version=effective_start.isoformat(),
        notes=(
            f"{schedule_note} Transcribed from {source_sheet} on PG&E's "
            f"historical rate index. The fixed provision on this date is "
            f"{fixed}. Bundled service only. Not modelled: CARE and FERA "
            f"discounts, the California Climate Credit, CCA and Direct "
            f"Access."
        ),
    )


def _weekday_peak_periods(
    *,
    summer_peak: float,
    summer_off_peak: float,
    winter_peak: float,
    winter_off_peak: float,
) -> tuple[TOUPeriod, ...]:
    """E-TOU-D's shape: a 5-8 p.m. weekday peak, everything else off-peak."""

    return (
        TOUPeriod(name="summer_peak", rate_per_kWh=summer_peak,
                  start_hour=17, end_hour=20, season=Season.SUMMER,
                  days=WEEKDAYS, priority=30),
        TOUPeriod(name="summer_off_peak", rate_per_kWh=summer_off_peak,
                  start_hour=0, end_hour=0, season=Season.SUMMER, priority=0),
        TOUPeriod(name="winter_peak", rate_per_kWh=winter_peak,
                  start_hour=17, end_hour=20, season=Season.WINTER,
                  days=WEEKDAYS, priority=30),
        TOUPeriod(name="winter_off_peak", rate_per_kWh=winter_off_peak,
                  start_hour=0, end_hour=0, season=Season.WINTER, priority=0),
    )


def _every_day_peak_periods(
    *,
    summer_peak: float,
    summer_part_peak: float,
    summer_off_peak: float,
    winter_peak: float,
    winter_part_peak: float,
    winter_off_peak: float,
) -> tuple[TOUPeriod, ...]:
    """EV2 and E-ELEC's shape: 4-9 p.m. peak every day, with shoulders."""

    periods = []
    for season, peak, part, off in (
        (Season.SUMMER, summer_peak, summer_part_peak, summer_off_peak),
        (Season.WINTER, winter_peak, winter_part_peak, winter_off_peak),
    ):
        prefix = season.value
        periods += [
            TOUPeriod(name=f"{prefix}_peak", rate_per_kWh=peak,
                      start_hour=16, end_hour=21, season=season, priority=30),
            TOUPeriod(name=f"{prefix}_part_peak_afternoon", rate_per_kWh=part,
                      start_hour=15, end_hour=16, season=season, priority=20),
            TOUPeriod(name=f"{prefix}_part_peak_evening", rate_per_kWh=part,
                      start_hour=21, end_hour=24, season=season, priority=20),
            TOUPeriod(name=f"{prefix}_off_peak", rate_per_kWh=off,
                      start_hour=0, end_hour=0, season=season, priority=0),
        ]
    return tuple(periods)


_etou_d_history: list[TariffDefinition] = []
_ev2_history: list[TariffDefinition] = []
_e_elec_history: list[TariffDefinition] = []

for (
    _start, _end,
    _d_min, _d_sp, _d_so, _d_wp, _d_wo,
    _v_min, _v_sp, _v_spp, _v_so, _v_wp, _v_wpp, _v_wo,
    _e_bsc, _e_sp, _e_spp, _e_so, _e_wp, _e_wpp, _e_wo,
    _sheet,
) in _TOU_HISTORICAL_WINDOWS:
    _stamp = _start.strftime("%Y_%m_%d")

    _etou_d_history.append(register_tariff(_historical_tou_version(
        tariff_id=f"pge_e_tou_d_residential_bundled_{_stamp}",
        name=f"PG&E E-TOU-D Residential TOU 5-8 p.m. ({_start} to {_end})",
        effective_start=_start, effective_end=_end,
        daily_minimum_bill=_d_min, daily_customer_charge=None,
        tou_periods=_weekday_peak_periods(
            summer_peak=_d_sp, summer_off_peak=_d_so,
            winter_peak=_d_wp, winter_off_peak=_d_wo,
        ),
        source_sheet=_sheet,
        schedule_note=(
            "Historical E-TOU-D: peak 5-8 p.m. Monday through Friday, all "
            "other hours and weekends off-peak."
        ),
    )))

    _ev2_history.append(register_tariff(_historical_tou_version(
        tariff_id=f"pge_ev2_residential_bundled_{_stamp}",
        name=f"PG&E EV2-A Residential EV ({_start} to {_end})",
        effective_start=_start, effective_end=_end,
        daily_minimum_bill=_v_min, daily_customer_charge=None,
        tou_periods=_every_day_peak_periods(
            summer_peak=_v_sp, summer_part_peak=_v_spp, summer_off_peak=_v_so,
            winter_peak=_v_wp, winter_part_peak=_v_wpp, winter_off_peak=_v_wo,
        ),
        source_sheet=_sheet,
        schedule_note=(
            "Historical EV2-A: peak 4-9 p.m. every day including weekends "
            "and holidays, with 3-4 p.m. and 9 p.m.-midnight shoulders."
        ),
    )))

    _e_elec_history.append(register_tariff(_historical_tou_version(
        tariff_id=f"pge_e_elec_residential_bundled_{_stamp}",
        name=f"PG&E E-ELEC Residential Electric Home ({_start} to {_end})",
        effective_start=_start, effective_end=_end,
        daily_minimum_bill=None, daily_customer_charge=_e_bsc,
        tou_periods=_every_day_peak_periods(
            summer_peak=_e_sp, summer_part_peak=_e_spp, summer_off_peak=_e_so,
            winter_peak=_e_wp, winter_part_peak=_e_wpp, winter_off_peak=_e_wo,
        ),
        source_sheet=_sheet,
        schedule_note=(
            "Historical E-ELEC: peak 4-9 p.m. every day including weekends "
            "and holidays, with 3-4 p.m. and 9 p.m.-midnight shoulders."
        ),
    )))

PGE_E_TOU_D_HISTORICAL_VERSIONS = tuple(_etou_d_history)
PGE_EV2_HISTORICAL_VERSIONS = tuple(_ev2_history)
PGE_E_ELEC_HISTORICAL_VERSIONS = tuple(_e_elec_history)

del (
    _start, _end, _d_min, _d_sp, _d_so, _d_wp, _d_wo,
    _v_min, _v_sp, _v_spp, _v_so, _v_wp, _v_wpp, _v_wo,
    _e_bsc, _e_sp, _e_spp, _e_so, _e_wp, _e_wpp, _e_wo,
    _sheet, _stamp, _etou_d_history, _ev2_history, _e_elec_history,
)


# --- Plans -----------------------------------------------------------------
#
# One plan per schedule and income tier; its versions are every filed rate
# document for that schedule, in date order. The 2024 versions are shared by
# all three income-tier plans because the income distinction did not exist
# then -- the customer's plan continued across the change, the rate structure
# did not.


def _residential_plan(
    *,
    schedule: str,
    variant: str,
    versions: tuple[TariffDefinition, ...],
) -> RatePlan:
    return register_plan(
        RatePlan(
            identity=RatePlanIdentity(
                utility="Pacific Gas and Electric",
                schedule=schedule,
                service_type=ServiceType.BUNDLED.value,
                customer_class=CustomerClass.RESIDENTIAL.value,
                variant=variant,
            ),
            versions=versions,
        )
    )


PGE_E1_PLAN_TIER1 = _residential_plan(
    schedule="E-1",
    variant="income_tier_1",
    versions=PGE_E1_HISTORICAL_VERSIONS + (PGE_E1_RESIDENTIAL_TIER1_BUNDLED,),
)

PGE_E1_PLAN_TIER2 = _residential_plan(
    schedule="E-1",
    variant="income_tier_2",
    versions=PGE_E1_HISTORICAL_VERSIONS + (PGE_E1_RESIDENTIAL_TIER2_BUNDLED,),
)

PGE_E1_PLAN_TIER3 = _residential_plan(
    schedule="E-1",
    variant="income_tier_3",
    versions=PGE_E1_HISTORICAL_VERSIONS + (PGE_E1_RESIDENTIAL_TIER3_BUNDLED,),
)

PGE_E_TOU_D_PLAN_TIER1 = _residential_plan(
    schedule="E-TOU-D",
    variant="income_tier_1",
    versions=PGE_E_TOU_D_HISTORICAL_VERSIONS + (PGE_E_TOU_D_RESIDENTIAL_TIER1_BUNDLED,),
)

PGE_E_TOU_D_PLAN_TIER2 = _residential_plan(
    schedule="E-TOU-D",
    variant="income_tier_2",
    versions=PGE_E_TOU_D_HISTORICAL_VERSIONS + (PGE_E_TOU_D_RESIDENTIAL_TIER2_BUNDLED,),
)

PGE_E_TOU_D_PLAN_TIER3 = _residential_plan(
    schedule="E-TOU-D",
    variant="income_tier_3",
    versions=PGE_E_TOU_D_HISTORICAL_VERSIONS + (PGE_E_TOU_D_RESIDENTIAL_TIER3_BUNDLED,),
)

PGE_E_ELEC_PLAN_TIER3 = _residential_plan(
    schedule="E-ELEC",
    variant="income_tier_3",
    versions=PGE_E_ELEC_HISTORICAL_VERSIONS + (PGE_E_ELEC_RESIDENTIAL_TIER3_BUNDLED,),
)

PGE_EV2_PLAN_TIER3 = _residential_plan(
    schedule="EV2-A",
    variant="income_tier_3",
    versions=PGE_EV2_HISTORICAL_VERSIONS + (PGE_EV2_RESIDENTIAL_TIER3_BUNDLED,),
)
