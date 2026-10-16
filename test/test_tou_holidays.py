"""Holiday rates, bills and dispatch; official calendar evidence in TOU_Holiday_Rules.md."""

from dataclasses import replace
from datetime import date

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import PGE_B19_SECONDARY_MANDATORY_BUNDLED, calculate_meter_billing
from src.billing.charges import calculate_timeline_billing
from src.billing.pge_common import PGE_TOU_HOLIDAYS, pge_tou_holidays
from src.billing.pge_residential import (
    PGE_E_TOU_D_HISTORICAL_VERSIONS, PGE_E_TOU_D_PLAN_TIER3,
    PGE_E_TOU_D_RESIDENTIAL_TIER1_BUNDLED,
    PGE_E_TOU_D_RESIDENTIAL_TIER2_BUNDLED,
    PGE_E_TOU_D_RESIDENTIAL_TIER3_BUNDLED,
)
from src.billing.tariffs import (
    ALL_DAYS, WEEKDAYS, DemandChargeBasis, DemandChargeComponent,
    DemandChargeFrequency, TARIFF_REGISTRY, TOUPeriod, TariffError,
)
from src.dispatch.single_day_analysis import _build_monthly_demand_charge_cost, run_cost_optimization
from src.signal_pipeline.horizon import build_horizon
from src.signal_pipeline.price_sources import PriceScheduleError, TimeOfUsePeriod, TimeOfUseSchedule
from src.tou_calendar import HolidayCalendar, HolidayTreatment

PACIFIC = "America/Los_Angeles"
D = PGE_E_TOU_D_RESIDENTIAL_TIER3_BUNDLED
D_VERSIONS = PGE_E_TOU_D_HISTORICAL_VERSIONS + (
    PGE_E_TOU_D_RESIDENTIAL_TIER1_BUNDLED,
    PGE_E_TOU_D_RESIDENTIAL_TIER2_BUNDLED, D,
)
# Independent dates from PG&E's published TOU calendar, not the generator.
EXPECTED_DATES = {
    2024: "01-01 02-19 05-27 07-04 09-02 11-11 11-28 12-25",
    2025: "01-01 02-17 05-26 07-04 09-01 11-11 11-27 12-25",
    2026: "01-01 02-16 05-25 07-04 09-07 11-11 11-26 12-25",
}


@pytest.mark.parametrize("year", EXPECTED_DATES)
def test_pge_calendar_matches_published_dates(year):
    assert pge_tou_holidays(year) == {
        date.fromisoformat(f"{year}-{day}") for day in EXPECTED_DATES[year].split()
    }


def test_pge_observance_is_not_the_federal_or_nerc_calendar():
    assert date(2021, 7, 5) in pge_tou_holidays(2021)  # Sunday observed Monday
    assert date(2022, 12, 26) in pge_tou_holidays(2022)
    assert date(2023, 1, 2) in pge_tou_holidays(2023)
    assert date(2026, 7, 3) not in pge_tou_holidays(2026)  # no Friday substitution
    assert date(2021, 12, 31) not in pge_tou_holidays(2022)
    assert date(2023, 11, 10) not in pge_tou_holidays(2023)
    for day in ("2025-01-20", "2025-06-19", "2025-10-13", "2025-11-28"):
        assert date.fromisoformat(day) not in pge_tou_holidays(2025)


@pytest.mark.parametrize("tariff", D_VERSIONS, ids=lambda t: t.tariff_id)
def test_each_implemented_e_tou_d_version_rates_and_bills(tariff):
    # All local service dates in each history window, plus the current summer.
    end = pd.Timestamp(tariff.effective_end or date(2026, 9, 17)) + pd.DateOffset(days=1)
    index = pd.date_range(tariff.effective_start, end, freq="15min", inclusive="left", tz=PACIFIC)
    holiday_dates = {date.fromisoformat(f"{year}-{day}")
                     for year in set(index.year) for day in EXPECTED_DATES[year].split()}
    season = np.where(np.isin(index.month, [6, 7, 8, 9]), "summer", "winter")
    peak = ((index.weekday < 5) & (index.hour >= 17) & (index.hour < 20)
            & ~np.isin(index.date, list(holiday_dates)))
    expected_names = pd.Series(season) + np.where(peak, "_peak", "_off_peak")
    values = {p.name: p.rate_per_kWh for p in tariff.tou_periods}
    expected_rates = expected_names.map(values)
    assert tariff.energy_rates(index).tolist() == expected_rates.tolist()
    assert tariff.period_names(index).tolist() == expected_names.tolist()
    assert tariff.demand_basis_for(index).isna().all()  # residential has no demand charge

    bills = calculate_meter_billing(
        pd.DataFrame({"timestamp": index, "grid_import_kw": 1.}),
        tariff, meter_id="home", timestep_hours=.25, expect_full_periods=False,
    )
    labels = index.strftime("%Y-%m")
    for bill, label in zip(bills, pd.unique(labels)):
        mask = labels == label
        energy = float(expected_rates[mask].sum()) * .25
        days = len(set(index[mask].date))
        expected_total = max(energy + days * (tariff.daily_customer_charge or 0),
                             days * (tariff.daily_minimum_bill or 0))
        assert bill.import_energy_charge == pytest.approx(energy)
        assert bill.demand_charge == 0
        assert bill.total_utility_charge == pytest.approx(expected_total)


def test_holiday_at_a_historical_rate_change_and_season_change():
    # Sep 1 is both Labor Day and the start of the third 2025 rate version.
    index = pd.date_range("2025-08-29", "2025-10-02", freq="15min", inclusive="left", tz=PACIFIC)
    bills = calculate_timeline_billing(
        pd.DataFrame({"timestamp": index, "grid_import_kw": 1.}),
        PGE_E_TOU_D_PLAN_TIER3, meter_id="home", timestep_hours=.25,
    )
    # Manual hourly totals: Aug 29-31 has one peak weekday; September has
    # 22 weekdays minus Labor Day = 63 peak hours. Oct 1 has 3 winter peak hours.
    expected = [3 * .57149 + 69 * .43653,
                63 * .56158 + 657 * .42662,
                3 * .47198 + 21 * .43337]
    assert [b.import_energy_charge for b in bills] == pytest.approx(expected)
    assert [b.total_utility_charge for b in bills] == pytest.approx(expected)
    assert [b.segments[0].version for b in bills] == ["2025-03-01", "2025-09-01", "2025-09-01"]


@pytest.mark.parametrize("day,peak", [("2026-07-03", True), ("2026-07-04", False),
                                     ("2026-09-07", False), ("2026-09-08", True)])
def test_current_e_tou_d_local_boundaries(day, peak):
    index = pd.DatetimeIndex([f"{day} {t}" for t in ("16:45", "17:00", "19:45", "20:00")], tz=PACIFIC)
    high = .47708 if peak else .34212
    assert D.energy_rates(index).tolist() == pytest.approx([.34212, high, high, .34212])


@pytest.mark.parametrize("day,count", [("2025-03-09", 92), ("2025-11-02", 100)])
def test_holiday_aware_tariff_keeps_dst_interval_counts_and_bill(day, count):
    horizon = build_horizon(day, 1, PACIFIC)
    assert len(horizon.index) == count
    bill, = calculate_timeline_billing(
        pd.DataFrame({"timestamp": horizon.index, "grid_import_kw": 1.}),
        PGE_E_TOU_D_PLAN_TIER3, meter_id="home", timestep_hours=.25,
    )
    rate = .44328 if day.startswith("2025-03") else .43337
    assert bill.import_energy_charge == pytest.approx(count * .25 * rate)
    assert bill.billing_days == 1


def test_holiday_support_does_not_extend_rate_coverage():
    index = build_horizon("2026-05-25", 1, PACIFIC).index
    with pytest.raises(TariffError, match="2026-05-25"):
        calculate_meter_billing(pd.DataFrame({"timestamp": index, "grid_import_kw": 1.}),
                                D, meter_id="home", timestep_hours=.25)
    with pytest.raises(ValueError, match="2026-05-25"):
        PGE_E_TOU_D_PLAN_TIER3.require_coverage(date(2026, 5, 25), date(2026, 5, 25))


def _generic_schedule():
    return TimeOfUseSchedule(
        periods=(TimeOfUsePeriod("peak", .6, 17, 20, WEEKDAYS, HolidayTreatment.EXCLUDE),),
        default_price_per_kWh=.1, holiday_calendar=PGE_TOU_HOLIDAYS,
    )


@pytest.mark.parametrize("day,peak", [("2021-07-05", False), ("2022-12-26", False),
                                     ("2023-01-02", False), ("2026-07-03", True),
                                     ("2025-01-20", True), ("2025-06-19", True)])
def test_generic_signals_use_explicit_observed_calendar(day, peak):
    prices = _generic_schedule().build_prices(build_horizon(day, 1, PACIFIC, 15))
    expected = np.where((prices.timestamp.dt.hour >= 17) & (prices.timestamp.dt.hour < 20) & peak, .6, .1)
    assert prices.price_per_kWh.tolist() == pytest.approx(expected)


def test_generic_regular_periods_do_not_get_an_implicit_holiday_override():
    schedule = TimeOfUseSchedule((TimeOfUsePeriod("peak", .6, 17, 20, WEEKDAYS),), .1)
    horizon = build_horizon("2025-07-04", 1, PACIFIC)
    for calendar in (None, PGE_TOU_HOLIDAYS):
        result = replace(schedule, holiday_calendar=calendar).build_prices(horizon)
        assert result.price_per_kWh.iloc[17 * 4] == .6


@pytest.mark.parametrize("treatment,expected", [
    (HolidayTreatment.REGULAR, [.1, .2, .1]),
    (HolidayTreatment.INCLUDE, [.2, .2, .1]),
    (HolidayTreatment.ONLY, [.2, .1, .1]),
])
def test_generic_holiday_only_or_weekend_including_holiday(treatment, expected):
    # Friday holiday, Saturday, ordinary Monday. ONLY deliberately ignores days.
    index = pd.DatetimeIndex(["2025-07-04 18:00", "2025-07-05 18:00", "2025-07-07 18:00"], tz=PACIFIC)
    period = TimeOfUsePeriod("weekend", .2, 17, 20, frozenset({5, 6}), treatment)
    mask = period.matches(pd.Series(index.hour), pd.Series(index.weekday), PGE_TOU_HOLIDAYS.mask(index))
    assert np.where(mask, .2, .1).tolist() == expected


def test_wrapped_period_holiday_is_the_local_interval_date():
    period = TimeOfUsePeriod("overnight", .2, 22, 6, ALL_DAYS, HolidayTreatment.EXCLUDE)
    schedule = TimeOfUseSchedule((period,), .1, PGE_TOU_HOLIDAYS)
    result = schedule.build_prices(build_horizon("2025-07-03", 2, PACIFIC))
    result = result.set_index("timestamp").price_per_kWh
    assert result.loc["2025-07-03 23:45"] == .2  # already July 4 in UTC
    assert result.loc["2025-07-04 00:00"] == .1
    assert result.loc["2025-07-04 22:00"] == .1


def test_generic_dst_repeated_hours_and_no_timezone_conversion():
    calendar = HolidayCalendar("synthetic DST date", lambda year: {date(year, 11, 2)})
    schedule = TimeOfUseSchedule(
        (TimeOfUsePeriod("holiday", .2, 0, 24, holiday_treatment=HolidayTreatment.ONLY),),
        .1, calendar,
    )
    result = schedule.build_prices(build_horizon("2025-11-02", 1, "America/New_York"))
    assert len(result) == 100
    assert (result.price_per_kWh == .2).all()
    assert str(result.timestamp.dt.tz) == "America/New_York"


def test_generic_calendar_handles_observed_new_year_in_previous_year():
    calendar = HolidayCalendar("synthetic prior-day observation", lambda year: {date(year - 1, 12, 31)})
    index = pd.DatetimeIndex(["2025-12-31 18:00", "2026-01-01 18:00"], tz=PACIFIC)
    assert calendar.mask(index).tolist() == [True, False]


@pytest.mark.parametrize("kind", ["signal", "billing"])
def test_holiday_configuration_errors_fail_explicitly(kind):
    if kind == "signal":
        cls, error = TimeOfUsePeriod, PriceScheduleError
        build = lambda p, c: TimeOfUseSchedule((p,), .1, c)
    else:
        cls, error = TOUPeriod, TariffError
        build = lambda p, c: replace(D, tou_periods=(p,), holiday_calendar=c)
    with pytest.raises(error, match="Unknown holiday treatment"):
        cls("bad", .1, 17, 20, holiday_treatment="federal")
    period = cls("peak", .1, 17, 20, holiday_treatment=HolidayTreatment.EXCLUDE)
    with pytest.raises(error, match="explicit holiday_calendar"):
        build(period, None)
    with pytest.raises(error, match="explicit HolidayCalendar"):
        build(period, "pge")
    with pytest.raises(error, match="calendar mask"):
        if kind == "signal":
            period.matches(pd.Series([17]), pd.Series([0]))
        else:
            period.matches(pd.Series([17]), pd.Series([7]), pd.Series(["summer"]), pd.Series([0]))


@pytest.mark.parametrize("frequency", [DemandChargeFrequency.MONTHLY, DemandChargeFrequency.DAILY])
def test_generic_peak_and_part_peak_demand_objective_equals_holiday_bill(frequency):
    # Synthetic tariff: PG&E E-TOU-D itself has NO demand charges.
    tariff = replace(D, tariff_id="synthetic_holiday_demand", effective_start=date(2025, 1, 1),
        daily_customer_charge=0., demand_charges=(
            DemandChargeComponent("all", 2., DemandChargeBasis.MAXIMUM),
            DemandChargeComponent("peak", 10., DemandChargeBasis.PEAK_PERIOD, frequency=frequency),
            DemandChargeComponent("part", 4., DemandChargeBasis.PART_PEAK_PERIOD, frequency=frequency),
        ), tou_periods=(
            TOUPeriod("peak", .6, 17, 20, days=WEEKDAYS, priority=30,
                      demand_basis=DemandChargeBasis.PEAK_PERIOD, holiday_treatment=HolidayTreatment.EXCLUDE),
            TOUPeriod("part", .3, 15, 17, days=WEEKDAYS, priority=20,
                      demand_basis=DemandChargeBasis.PART_PEAK_PERIOD, holiday_treatment=HolidayTreatment.EXCLUDE),
            TOUPeriod("off", .1, 0, 0),
        ))
    index = pd.DatetimeIndex(["2025-07-03 16:00", "2025-07-03 18:00",
                              "2025-07-04 16:00", "2025-07-04 18:00"], tz=PACIFIC)
    imports = [7., 5., 100., 100.]
    data = pd.DataFrame({"timestamp": index, "grid_import_kw": imports})
    assert tariff.energy_rates(index).tolist() == [.3, .6, .1, .1]
    assert tariff.demand_basis_for(index).tolist() == [DemandChargeBasis.PART_PEAK_PERIOD,
                                                     DemandChargeBasis.PEAK_PERIOD, None, None]
    objective = _build_monthly_demand_charge_cost(cp.Constant(imports), data,
        demand_charge_rate_per_kw=0., previous_peak_kw=None, demand_tariff=tariff)
    bill, = calculate_meter_billing(data, tariff, meter_id="synthetic", timestep_hours=.25,
                                    expect_full_periods=False)
    assert objective.value == pytest.approx(100 * 2 + 5 * 10 + 7 * 4)
    assert bill.demand_charge == pytest.approx(objective.value)
    assert bill.total_utility_charge == pytest.approx(objective.value + (7 * .3 + 5 * .6 + 200 * .1) * .25)


def test_e_tou_d_dispatch_uses_holiday_prices_and_reconciles_bill():
    savings = []
    for day in ("2026-09-07", "2026-09-08"):
        index = build_horizon(day, 1, PACIFIC).index
        data = pd.DataFrame({"timestamp": index, "load_kw": 1., "pv_kw": 0.,
                             "net_load_kw": 1., "gCO2/kWh": 0.,
                             "price_per_kWh": D.energy_rates(index).to_numpy()})
        battery = dict(initial_soc_kWh=0., min_soc_kWh=0., max_soc_kWh=4.,
                       max_charge_kw=2., max_discharge_kw=2.,
                       charge_efficiency=.95, discharge_efficiency=.95)
        optimized = run_cost_optimization(data.copy(), battery, demand_tariff=D)
        bill, = calculate_meter_billing(optimized, D, meter_id="home", timestep_hours=.25)
        energy = float((optimized.grid_import_kw * data.price_per_kWh).sum()) * .25
        assert bill.total_utility_charge == pytest.approx(energy + .79343)
        savings.append(float(data.price_per_kWh.sum()) * .25 - energy)
    assert savings[0] == pytest.approx(0., abs=1e-5)
    assert savings[1] > .2


def test_every_day_pge_tariffs_retain_holiday_energy_and_demand_periods():
    # Exercise every registered PG&E version and variant; adding calendar
    # support must not alter their every-day periods or tiered-only energy.
    tariffs = [t for t in TARIFF_REGISTRY.values()
               if t.tariff_id.startswith("pge_") and t not in D_VERSIONS]
    assert tariffs
    for tariff in tariffs:
        assert tariff.holiday_calendar is None
        assert all(p.holiday_treatment == HolidayTreatment.REGULAR for p in tariff.tou_periods)
        # Pick an actual holiday inside this version without extending coverage.
        choices = [date.fromisoformat(f"{year}-{day}")
                   for year in EXPECTED_DATES for day in EXPECTED_DATES[year].split()]
        day = next((d for d in choices if tariff.is_effective_on(d)), None)
        if day is None:
            continue  # Some historical windows contain no holiday.
        idx = pd.DatetimeIndex([f"{day} 15:00", f"{day} 18:00"], tz=PACIFIC)
        with_calendar = replace(tariff, holiday_calendar=PGE_TOU_HOLIDAYS)
        assert with_calendar.energy_rates(idx).equals(tariff.energy_rates(idx))
        assert with_calendar.demand_basis_for(idx).equals(tariff.demand_basis_for(idx))
        assert tariff.period_names(idx).iloc[-1] in {"summer_peak", "winter_peak", "all_usage"}


def test_b19_holiday_bill_still_charges_all_three_summer_demand_components():
    tariff = PGE_B19_SECONDARY_MANDATORY_BUNDLED
    index = pd.DatetimeIndex(["2026-07-04 15:00", "2026-07-04 18:00", "2026-07-04 23:00"], tz=PACIFIC)
    data = pd.DataFrame({"timestamp": index, "grid_import_kw": [7., 5., 100.]})
    bill, = calculate_meter_billing(data, tariff, meter_id="business", timestep_hours=.25,
                                    expect_full_periods=False)
    assert bill.demand_charge_by_component == pytest.approx({
        "maximum_demand": 37.37 * 100,
        "peak_period_demand_summer": 46.16 * 5,
        "part_peak_period_demand_summer": 10.52 * 7,
        "peak_period_demand_winter": 0.,
    })
    assert bill.import_energy_charge == pytest.approx((7 * .14775 + 5 * .18648 + 100 * .12037) * .25)
