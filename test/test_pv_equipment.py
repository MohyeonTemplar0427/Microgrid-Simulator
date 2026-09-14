"""Tests for the equipment-specific PV model (Phase 2).

Everything here is offline and deterministic. Irradiance comes from pvlib's
clear-sky model and equipment from the CEC databases bundled with pvlib, so no
test touches the network or needs a secret.

The module and inverter chosen throughout are a 300 W crystalline-silicon
module and a 50 kW three-phase commercial string inverter -- a pairing a real
project would make, which is what makes the MPPT-window and clipping cases
representative rather than contrived.
"""

import numpy as np
import pandas as pd
import pytest
from pvlib import inverter as pvlib_inverter
from pvlib.location import Location

from src.profiles import (
    CONTROL_BEHAVIOUR_NOT_MODELLED,
    EQUIPMENT_DIAGNOSTIC_COLUMNS,
    EQUIPMENT_POWER_STAGE_COLUMNS,
    EQUIPMENT_PV_MODEL_VERSION,
    GRID_FOLLOWING,
    SUPPORTED_CONTROL_MODES,
    EquipmentSpecificPV,
    EquipmentSpecificPVConfiguration,
    InverterSpecification,
    InverterUnitConfiguration,
    ModuleSpecification,
    PVEquipmentError,
    SubarrayConfiguration,
    WeatherDerivedPV,
    WeatherDerivedPVConfiguration,
    cec_inverter_names,
    cec_module_names,
)
from src.profiles.pv_equipment import (
    EFFECTIVE_IRRADIANCE_W_PER_M2,
    INVERTER_INPUT_VOLTAGE_V,
    MPPT_WINDOW_LIMITED,
    PV_DC_AT_INVERTER_INPUT_KW,
    PV_INVERTER_NIGHT_TARE_KW,
    STRING_MAXIMUM_POWER_VOLTAGE_V,
    _sandia_efficiency_watts,
)
from src.profiles.pv_model import (
    PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2,
    PV_AC_BEFORE_CLIPPING_KW,
    PV_AVAILABLE_KW,
    PV_DC_AFTER_SYSTEM_LOSSES_KW,
    PV_INVERTER_CLIPPING_KW,
    PV_MODULE_DC_POWER_KW,
)
from src.profiles.weather import (
    DHI_W_PER_M2,
    DNI_W_PER_M2,
    GHI_W_PER_M2,
    TEMPERATURE_C,
    WIND_SPEED_M_PER_S,
)
from src.timeseries import build_interval_index

PACIFIC = "America/Los_Angeles"
LATITUDE = 37.77
LONGITUDE = -122.42

MODULE_NAME = "Canadian_Solar_Inc__CS6X_300M"

#: 50 kW three-phase commercial string inverter. Comfortably larger than the
#: default array here, so nothing clips unless a test asks for it.
INVERTER_NAME = "SMA_America__STP_50_US_41__480V_"

#: 12 kW inverter of the same family, used wherever a test needs clipping.
#: It is a real database entry rather than a shrunken copy of the 50 kW one:
#: ``Paco`` and ``Pdco`` both appear inside the Sandia efficiency polynomial,
#: so overriding one of them in isolation does not describe a smaller
#: inverter, it describes an inverter that converts badly.
SMALL_INVERTER_NAME = "SMA_America__STP12000TL_US_10__480V_"

#: Modules in series that fit this inverter's 800 V maximum DC input at the
#: default -10 degC cold design condition.
MODULES_PER_STRING = 15


def make_index(start="2026-06-21", end="2026-06-21", timezone=PACIFIC):
    return build_interval_index(start, end, timezone)


def clear_sky_weather(
    interval_index,
    *,
    temperature_c: float = 20.0,
    wind_speed_m_per_s: float = 2.0,
) -> pd.DataFrame:
    """Physically consistent GHI/DNI/DHI for the horizon, from pvlib."""

    location = Location(LATITUDE, LONGITUDE, tz=interval_index.timezone)
    sky = location.get_clearsky(interval_index.index, model="ineichen")

    return pd.DataFrame(
        {
            "timestamp": interval_index.index,
            GHI_W_PER_M2: sky["ghi"].to_numpy(),
            DNI_W_PER_M2: sky["dni"].to_numpy(),
            DHI_W_PER_M2: sky["dhi"].to_numpy(),
            TEMPERATURE_C: temperature_c,
            WIND_SPEED_M_PER_S: wind_speed_m_per_s,
        }
    )


def module() -> ModuleSpecification:
    return ModuleSpecification.from_cec_database(MODULE_NAME)


def inverter_specification(
    name: str = INVERTER_NAME,
    *,
    mppt_input_count: int = 2,
    **overrides,
) -> InverterSpecification:
    """A real CEC inverter, optionally with overridden voltage ratings.

    Only ``Mppt_low``, ``Mppt_high`` and ``Vdcmax`` may be overridden. None of
    them appears in the Sandia efficiency polynomial -- they are limits this
    module enforces and the Sandia model does not -- so changing one describes
    a different tracking window on the same converter. ``Paco`` and ``Pdco``
    are not overridable here for the opposite reason: both are inside the
    polynomial, so changing either alone changes the conversion efficiency
    rather than the size of the inverter. Use ``SMALL_INVERTER_NAME`` for a
    smaller inverter.
    """

    assert set(overrides) <= {"Mppt_low", "Mppt_high", "Vdcmax"}, overrides

    specification = InverterSpecification.from_cec_database(
        name, mppt_input_count=mppt_input_count
    )

    if not overrides:
        return specification

    parameters = dict(specification.parameters)
    parameters.update(overrides)

    return InverterSpecification(
        name=specification.name,
        parameters=parameters,
        mppt_input_count=mppt_input_count,
    )


def small_inverter(**overrides) -> InverterSpecification:
    """The 12 kW inverter: small enough that the default array clips on it."""

    return inverter_specification(SMALL_INVERTER_NAME, **overrides)


def subarray(**overrides) -> SubarrayConfiguration:
    settings = {
        "module": module(),
        "modules_per_string": MODULES_PER_STRING,
        "strings": 6,
        "tilt_degrees": 20.0,
        "azimuth_degrees": 180.0,
    }
    settings.update(overrides)
    return SubarrayConfiguration(**settings)


def unit(**overrides) -> InverterUnitConfiguration:
    settings = {
        "inverter": inverter_specification(),
        "subarrays": (subarray(),),
    }
    settings.update(overrides)
    return InverterUnitConfiguration(**settings)


def make_configuration(units=None) -> EquipmentSpecificPVConfiguration:
    return EquipmentSpecificPVConfiguration(
        latitude=LATITUDE,
        longitude=LONGITUDE,
        inverter_units=units if units is not None else (unit(),),
    )


def build_detailed(configuration, interval_index, weather=None, **kwargs):
    source = EquipmentSpecificPV(
        configuration=configuration,
        weather_data=weather
        if weather is not None
        else clear_sky_weather(interval_index),
        **kwargs,
    )
    return source.build_detailed(interval_index)


def build(configuration, interval_index, weather=None, **kwargs):
    return build_detailed(
        configuration, interval_index, weather, **kwargs
    ).pv_available_kw


def energy_kwh(series, interval_index) -> float:
    return float(np.sum(series) * interval_index.timestep_hours)


## Equipment databases ----------------------------------------------------


def test_the_cec_databases_are_available_offline():
    modules = cec_module_names()
    inverters = cec_inverter_names()

    assert MODULE_NAME in modules
    assert INVERTER_NAME in inverters
    # pvlib ships these as CSV files; nothing here reaches a network.
    assert len(modules) > 10_000
    assert len(inverters) > 1_000


def test_a_module_carries_its_six_parameter_set_and_nameplate():
    specification = module()

    assert specification.rated_power_w == pytest.approx(300.03)
    assert specification.is_crystalline_silicon

    for parameter in ("alpha_sc", "a_ref", "I_L_ref", "I_o_ref", "R_sh_ref",
                      "R_s", "Adjust"):
        assert parameter in specification.parameters


def test_an_inverter_reports_its_clipping_rating():
    specification = inverter_specification()

    assert specification.ac_capacity_kw == pytest.approx(50.01)
    assert specification.parameters["Mppt_low"] == pytest.approx(500.0)


def test_an_unknown_module_is_rejected_with_candidates():
    with pytest.raises(PVEquipmentError) as error:
        ModuleSpecification.from_cec_database("CS6X_300M")

    # A partial name is the usual mistake, so the message points at the
    # full part numbers that contain it rather than only saying "not found".
    assert "Did you mean" in str(error.value)
    assert MODULE_NAME in str(error.value)


def test_an_unknown_inverter_is_rejected():
    with pytest.raises(PVEquipmentError) as error:
        InverterSpecification.from_cec_database("no_such_inverter")

    assert "cec_inverter_names()" in str(error.value)


def test_a_module_may_be_specified_without_the_database():
    specification = ModuleSpecification(
        name="custom",
        parameters=dict(module().parameters),
        rated_power_w=300.0,
    )

    assert specification.name == "custom"
    assert not specification.is_crystalline_silicon  # technology unstated


def test_an_incomplete_module_parameter_set_is_rejected():
    parameters = dict(module().parameters)
    parameters.pop("a_ref")

    with pytest.raises(PVEquipmentError) as error:
        ModuleSpecification(
            name="custom", parameters=parameters, rated_power_w=300.0
        )

    assert "a_ref" in str(error.value)


## Plant configuration ----------------------------------------------------


def test_capacities_are_derived_from_the_equipment_not_typed_in():
    configuration = make_configuration()

    modules = MODULES_PER_STRING * 6
    assert configuration.rated_dc_capacity_kw == pytest.approx(
        modules * 300.03 / 1000.0
    )
    assert configuration.inverter_ac_capacity_kw == pytest.approx(50.01)
    assert configuration.dc_ac_ratio == pytest.approx(
        configuration.rated_dc_capacity_kw / 50.01
    )


def test_instance_count_multiplies_both_capacities():
    one = make_configuration((unit(count=1),))
    four = make_configuration((unit(count=4),))

    assert four.rated_dc_capacity_kw == pytest.approx(
        4 * one.rated_dc_capacity_kw
    )
    assert four.inverter_ac_capacity_kw == pytest.approx(
        4 * one.inverter_ac_capacity_kw
    )


def test_a_plant_with_one_unit_is_homogeneous_however_many_instances():
    assert make_configuration((unit(count=9),)).is_homogeneous
    assert not make_configuration(
        (unit(name="a"), unit(name="b"))
    ).is_homogeneous


def test_impossible_string_arrangements_are_rejected():
    with pytest.raises(PVEquipmentError):
        subarray(modules_per_string=0)

    with pytest.raises(PVEquipmentError):
        subarray(strings=0)


def test_subarray_geometry_and_losses_are_bounded():
    with pytest.raises(PVEquipmentError):
        subarray(tilt_degrees=95.0)

    with pytest.raises(PVEquipmentError):
        subarray(azimuth_degrees=360.0)

    with pytest.raises(PVEquipmentError):
        subarray(ground_albedo=1.5)

    with pytest.raises(PVEquipmentError):
        subarray(dc_losses_fraction=1.0)


def test_an_unknown_mount_type_names_the_thermal_models_available():
    with pytest.raises(PVEquipmentError) as error:
        subarray(mount_type="floating")

    assert "open_rack_glass_glass" in str(error.value)


def test_more_subarrays_than_mppt_inputs_is_rejected():
    # Two orientations on one MPPT input is an electrical mismatch problem
    # with no default model, so it is refused rather than approximated.
    with pytest.raises(PVEquipmentError) as error:
        InverterUnitConfiguration(
            inverter=inverter_specification(mppt_input_count=1),
            subarrays=(
                subarray(name="south", azimuth_degrees=180.0),
                subarray(name="west", azimuth_degrees=270.0),
            ),
        )

    assert "own MPPT input" in str(error.value)
    assert "more strings" in str(error.value)


def test_repeated_subarray_names_are_rejected():
    with pytest.raises(PVEquipmentError) as error:
        InverterUnitConfiguration(
            inverter=inverter_specification(),
            subarrays=(subarray(name="roof"), subarray(name="roof")),
        )

    assert "roof" in str(error.value)


def test_repeated_inverter_unit_names_are_rejected():
    with pytest.raises(PVEquipmentError):
        make_configuration((unit(name="same"), unit(name="same")))


def test_a_plant_needs_equipment():
    with pytest.raises(PVEquipmentError) as error:
        make_configuration(())

    assert "at least one inverter unit" in str(error.value)


def test_a_unit_needs_at_least_one_subarray():
    with pytest.raises(PVEquipmentError):
        InverterUnitConfiguration(
            inverter=inverter_specification(), subarrays=()
        )


## String voltage design limits -------------------------------------------


def test_a_string_that_would_overvolt_its_inverter_when_cold_is_rejected():
    # Open-circuit voltage rises as the array cools, so the binding case is
    # the coldest morning. Exceeding Vdcmax damages the inverter rather than
    # merely costing energy, which is why this raises rather than warns.
    with pytest.raises(PVEquipmentError) as error:
        unit(subarrays=(subarray(modules_per_string=24),))

    message = str(error.value)
    assert "maximum DC input voltage" in message
    assert "At most" in message


def test_the_rejection_names_a_string_length_that_does_fit():
    with pytest.raises(PVEquipmentError) as error:
        unit(subarrays=(subarray(modules_per_string=24),))

    largest = int(str(error.value).split("At most ")[1].split(" modules")[0])

    assert largest < 24
    # The number it suggests must itself be accepted.
    unit(subarrays=(subarray(modules_per_string=largest),))


def test_a_warmer_cold_design_temperature_admits_a_longer_string():
    # A site that never freezes can run longer strings. The design condition
    # is a site property, so it is declared rather than assumed.
    with pytest.raises(PVEquipmentError):
        unit(subarrays=(subarray(modules_per_string=17),))

    unit(
        subarrays=(subarray(modules_per_string=17),),
        cold_design_cell_temperature_c=20.0,
    )


## Diagnostics shape ------------------------------------------------------


def test_diagnostics_carry_exactly_the_documented_columns():
    index = make_index()
    result = build_detailed(make_configuration(), index)

    assert tuple(result.diagnostics.columns) == EQUIPMENT_DIAGNOSTIC_COLUMNS


def test_the_power_stage_columns_are_a_superset_of_phase_one():
    # Phase 1's six stages keep their names and meanings; Phase 2 adds the
    # inverter-input stage between them.
    assert set(EQUIPMENT_POWER_STAGE_COLUMNS) >= {
        "timestamp",
        PV_MODULE_DC_POWER_KW,
        PV_DC_AFTER_SYSTEM_LOSSES_KW,
        PV_AC_BEFORE_CLIPPING_KW,
        PV_INVERTER_CLIPPING_KW,
        PV_AVAILABLE_KW,
    }


def test_diagnostic_timestamps_match_the_interval_index_exactly():
    index = make_index("2026-06-21", "2026-06-23")
    result = build_detailed(make_configuration(), index)

    pd.testing.assert_index_equal(
        pd.DatetimeIndex(result.diagnostics["timestamp"]),
        index.index,
        check_names=False,
    )

    for frame in result.subarray_diagnostics.values():
        pd.testing.assert_index_equal(
            pd.DatetimeIndex(frame["timestamp"]), index.index, check_names=False
        )

    for frame in result.inverter_diagnostics.values():
        assert len(frame) == index.interval_count


@pytest.mark.parametrize(
    ("date", "expected"),
    [("2026-03-08", 92), ("2026-11-01", 100)],
)
def test_daylight_saving_days_keep_their_real_interval_counts(date, expected):
    index = make_index(date, date)

    assert index.interval_count == expected

    result = build_detailed(make_configuration(), index)

    assert len(result.diagnostics) == expected
    assert len(result.pv_available_kw) == expected


def test_the_available_series_matches_the_diagnostic_column():
    index = make_index()
    result = build_detailed(make_configuration(), index)

    np.testing.assert_allclose(
        result.pv_available_kw.to_numpy(),
        result.diagnostics[PV_AVAILABLE_KW].to_numpy(),
    )
    assert result.pv_available_kw.name == PV_AVAILABLE_KW


def test_subarray_and_inverter_frames_are_keyed_by_name():
    index = make_index()
    configuration = make_configuration(
        (
            unit(
                name="inv-a",
                inverter=inverter_specification(mppt_input_count=2),
                subarrays=(
                    subarray(name="south", azimuth_degrees=180.0),
                    subarray(name="west", azimuth_degrees=270.0),
                ),
            ),
        )
    )

    result = build_detailed(configuration, index)

    assert set(result.subarray_diagnostics) == {"inv-a/south", "inv-a/west"}
    assert set(result.inverter_diagnostics) == {"inv-a"}


## Power-stage identities -------------------------------------------------


def test_every_power_stage_is_nonnegative():
    index = make_index("2026-06-21", "2026-06-22")
    diagnostics = build_detailed(make_configuration(), index).diagnostics

    for column in EQUIPMENT_POWER_STAGE_COLUMNS[1:]:
        assert (diagnostics[column].to_numpy() >= 0).all(), column

    assert (diagnostics[PV_INVERTER_NIGHT_TARE_KW].to_numpy() >= 0).all()


def test_stages_are_monotonically_nonincreasing_through_the_chain():
    index = make_index()
    diagnostics = build_detailed(make_configuration(), index).diagnostics

    stages = [
        diagnostics[column].to_numpy()
        for column in (
            PV_MODULE_DC_POWER_KW,
            PV_DC_AFTER_SYSTEM_LOSSES_KW,
            PV_DC_AT_INVERTER_INPUT_KW,
            PV_AC_BEFORE_CLIPPING_KW,
            PV_AVAILABLE_KW,
        )
    ]

    for earlier, later in zip(stages, stages[1:]):
        assert (later <= earlier + 1e-9).all()


def test_the_available_identity_holds():
    index = make_index()
    diagnostics = build_detailed(make_configuration(), index).diagnostics

    np.testing.assert_allclose(
        diagnostics[PV_AVAILABLE_KW].to_numpy(),
        diagnostics[PV_AC_BEFORE_CLIPPING_KW].to_numpy()
        - diagnostics[PV_INVERTER_CLIPPING_KW].to_numpy(),
        atol=1e-12,
    )


def test_the_phase_one_clipping_identity_holds_on_a_homogeneous_plant():
    # One inverter model, any number of identical instances: every inverter
    # clips at the same moment by the same amount, so plant clipping is
    # exactly max(plant AC before clipping - plant rating, 0).
    index = make_index()
    configuration = make_configuration(
        (unit(count=3, inverter=small_inverter()),)
    )

    diagnostics = build_detailed(configuration, index).diagnostics
    rating = configuration.inverter_ac_capacity_kw

    np.testing.assert_allclose(
        diagnostics[PV_INVERTER_CLIPPING_KW].to_numpy(),
        np.clip(
            diagnostics[PV_AC_BEFORE_CLIPPING_KW].to_numpy() - rating,
            0.0,
            None,
        ),
        atol=1e-9,
    )
    assert diagnostics[PV_INVERTER_CLIPPING_KW].max() > 0


def test_clipping_on_a_mixed_plant_exceeds_the_plant_level_formula():
    # Clipping happens inside each inverter. Pairing a small inverter with a
    # large one, the small one clips while the large one still has headroom,
    # so the plant total is strictly greater than plant totals would suggest.
    index = make_index()
    configuration = make_configuration(
        (
            unit(
                name="small",
                inverter=small_inverter(),
                subarrays=(subarray(name="a"),),
            ),
            unit(
                name="large",
                inverter=inverter_specification(),
                subarrays=(subarray(name="b"),),
            ),
        )
    )

    diagnostics = build_detailed(configuration, index).diagnostics
    rating = configuration.inverter_ac_capacity_kw

    plant_level = np.clip(
        diagnostics[PV_AC_BEFORE_CLIPPING_KW].to_numpy() - rating, 0.0, None
    )
    actual = diagnostics[PV_INVERTER_CLIPPING_KW].to_numpy()

    assert (actual >= plant_level - 1e-9).all()
    assert actual.sum() > plant_level.sum()

    # The defining identity still holds, and the plant still respects its
    # total rating.
    np.testing.assert_allclose(
        diagnostics[PV_AVAILABLE_KW].to_numpy(),
        diagnostics[PV_AC_BEFORE_CLIPPING_KW].to_numpy() - actual,
        atol=1e-12,
    )
    assert diagnostics[PV_AVAILABLE_KW].max() <= rating + 1e-9


def test_available_power_never_exceeds_the_plant_ac_rating():
    index = make_index()
    configuration = make_configuration(
        (unit(inverter=small_inverter()),)
    )

    available = build(configuration, index)

    assert available.max() <= configuration.inverter_ac_capacity_kw + 1e-9


def test_an_oversized_inverter_never_clips():
    index = make_index()
    # The 50 kW inverter against a 27 kW array: it cannot reach its rating.
    configuration = make_configuration((unit(),))

    diagnostics = build_detailed(configuration, index).diagnostics

    # The array does produce; it simply never reaches the inverter's rating.
    assert diagnostics[PV_AVAILABLE_KW].max() > 0
    assert diagnostics[PV_INVERTER_CLIPPING_KW].max() == pytest.approx(0.0)
    np.testing.assert_allclose(
        diagnostics[PV_AVAILABLE_KW].to_numpy(),
        diagnostics[PV_AC_BEFORE_CLIPPING_KW].to_numpy(),
    )


def test_clipping_occurs_only_above_the_inverter_rating():
    index = make_index()
    configuration = make_configuration(
        (unit(inverter=small_inverter()),)
    )

    diagnostics = build_detailed(configuration, index).diagnostics
    rating = configuration.inverter_ac_capacity_kw

    before = diagnostics[PV_AC_BEFORE_CLIPPING_KW].to_numpy()
    clipping = diagnostics[PV_INVERTER_CLIPPING_KW].to_numpy()

    # Both sides of the rating must actually occur, or this proves nothing.
    assert (before > rating).any()
    assert (before <= rating).any()

    assert (clipping[before <= rating] == 0).all()
    assert (clipping[before > rating] > 0).all()


def test_all_stages_are_zero_at_night():
    index = make_index()
    result = build_detailed(make_configuration(), index)
    diagnostics = result.diagnostics

    dark = diagnostics[PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2].to_numpy() == 0

    assert dark.any()

    for column in EQUIPMENT_POWER_STAGE_COLUMNS[1:]:
        assert diagnostics.loc[dark, column].to_numpy() == pytest.approx(0.0)


def test_the_night_tare_is_reported_but_never_subtracted():
    # The Sandia model returns -Pnt when the array cannot start the inverter.
    # That is inverter self-consumption -- a site load -- so it is reported
    # separately and pv_available_kw stays nonnegative.
    index = make_index()
    diagnostics = build_detailed(make_configuration(), index).diagnostics

    dark = diagnostics[PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2].to_numpy() == 0

    assert (diagnostics.loc[dark, PV_INVERTER_NIGHT_TARE_KW] > 0).all()
    assert (diagnostics[PV_AVAILABLE_KW] >= 0).all()


## Agreement with pvlib ---------------------------------------------------


def test_the_unclipped_inverter_stage_reproduces_pvlib_exactly():
    # pvlib's sandia() applies conversion and clipping in one call, so the
    # "before clipping" stage has to be reconstructed. Clipping the
    # reconstruction must reproduce pvlib bit for bit, or the two have drifted.
    specification = inverter_specification()
    parameters = specification.parameters

    voltage = np.linspace(500.0, 800.0, 2001)
    power_w = np.linspace(0.0, 90_000.0, 2001)

    reference = np.asarray(
        pvlib_inverter.sandia(voltage, power_w, parameters), dtype=float
    )

    unclipped = _sandia_efficiency_watts([voltage], [power_w], specification)
    running = power_w >= parameters["Pso"]
    mine = np.where(running, unclipped, 0.0).clip(min=0.0)
    mine = np.minimum(mine, parameters["Paco"])

    assert np.abs(mine - np.maximum(reference, 0.0)).max() == 0.0


def test_the_multi_input_inverter_stage_reproduces_pvlib_exactly():
    specification = inverter_specification(mppt_input_count=2)
    parameters = specification.parameters

    generator = np.random.default_rng(20260914)
    size = 5000

    voltages = [
        generator.uniform(500.0, 800.0, size),
        generator.uniform(500.0, 800.0, size),
    ]
    powers = [
        generator.uniform(0.0, 40_000.0, size),
        generator.uniform(0.0, 40_000.0, size),
    ]

    reference = np.asarray(
        pvlib_inverter.sandia_multi(
            tuple(voltages), tuple(powers), parameters
        ),
        dtype=float,
    )

    unclipped = _sandia_efficiency_watts(voltages, powers, specification)
    running = sum(powers) >= parameters["Pso"]
    mine = np.where(running, unclipped, 0.0).clip(min=0.0)
    mine = np.minimum(mine, parameters["Paco"])

    assert np.abs(mine - np.maximum(reference, 0.0)).max() == 0.0


## Loss accounting --------------------------------------------------------


def test_dc_losses_apply_to_dc_only_and_exactly_once():
    index = make_index()

    for fraction in (0.0, 0.14, 0.30):
        configuration = make_configuration(
            (unit(subarrays=(subarray(dc_losses_fraction=fraction),)),)
        )
        diagnostics = build_detailed(configuration, index).diagnostics

        np.testing.assert_allclose(
            diagnostics[PV_DC_AFTER_SYSTEM_LOSSES_KW].to_numpy(),
            diagnostics[PV_MODULE_DC_POWER_KW].to_numpy() * (1.0 - fraction),
            rtol=1e-12,
        )


def test_inverter_conversion_is_not_also_in_the_dc_loss_fraction():
    # If inverter efficiency had leaked into the DC loss fraction, the AC
    # stage would sit far below a plausible conversion efficiency of the DC
    # actually presented to the inverter.
    index = make_index()
    configuration = make_configuration(
        (unit(subarrays=(subarray(dc_losses_fraction=0.0),)),)
    )

    diagnostics = build_detailed(configuration, index).diagnostics

    producing = diagnostics[PV_DC_AT_INVERTER_INPUT_KW].to_numpy() > 1.0
    efficiency = (
        diagnostics.loc[producing, PV_AC_BEFORE_CLIPPING_KW].to_numpy()
        / diagnostics.loc[producing, PV_DC_AT_INVERTER_INPUT_KW].to_numpy()
    )

    assert efficiency.max() <= 1.0
    assert efficiency.max() > 0.95


def test_the_angle_of_incidence_modifier_reduces_effective_irradiance():
    # Phase 1 folds reflection into an aggregate fraction. Here it is a real
    # function of the sun's position, so effective irradiance is below
    # plane-of-array global whenever there is a beam component.
    index = make_index()
    diagnostics = build_detailed(make_configuration(), index).diagnostics

    poa = diagnostics[PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2].to_numpy()
    effective = diagnostics[EFFECTIVE_IRRADIANCE_W_PER_M2].to_numpy()

    lit = poa > 0

    assert (effective[lit] <= poa[lit] + 1e-9).all()
    assert (effective[lit] < poa[lit]).any()


## MPPT voltage window ----------------------------------------------------


def test_a_string_below_the_mppt_window_is_dragged_to_the_window_edge():
    # The array's own maximum power point sits below what the inverter can
    # track, so the inverter operates at the window's lower edge instead --
    # off the maximum power point, and producing less.
    index = make_index()

    tracked = make_configuration(
        (unit(inverter=inverter_specification(Mppt_low=300.0)),)
    )
    constrained = make_configuration(
        (unit(inverter=inverter_specification(Mppt_low=560.0)),)
    )

    free = build_detailed(tracked, index).diagnostics
    limited = build_detailed(constrained, index).diagnostics

    subarray_frame = build_detailed(
        constrained, index
    ).subarray_diagnostics["inverter/subarray"]

    producing = subarray_frame[PV_DC_AFTER_SYSTEM_LOSSES_KW].to_numpy() > 0
    flagged = subarray_frame[MPPT_WINDOW_LIMITED].to_numpy()

    assert (flagged & producing).any()

    # Where the window binds, the inverter sits exactly at its lower edge.
    bound = flagged & producing
    np.testing.assert_allclose(
        subarray_frame.loc[bound, INVERTER_INPUT_VOLTAGE_V].to_numpy(),
        560.0,
    )

    # Same modules, same weather: only the tracking window differs, and it
    # costs real DC energy.
    assert energy_kwh(
        limited[PV_DC_AT_INVERTER_INPUT_KW], index
    ) < energy_kwh(free[PV_DC_AT_INVERTER_INPUT_KW], index)

    # The stage before the window is untouched, because the window is an
    # inverter limitation and not a system loss.
    np.testing.assert_allclose(
        limited[PV_DC_AFTER_SYSTEM_LOSSES_KW].to_numpy(),
        free[PV_DC_AFTER_SYSTEM_LOSSES_KW].to_numpy(),
    )


def test_a_string_that_never_reaches_the_window_produces_nothing():
    # If even the open-circuit voltage stays under Mppt_low the inverter
    # cannot operate at all -- the modules are making power the inverter has
    # no way to take.
    index = make_index()
    configuration = make_configuration(
        (
            unit(
                inverter=inverter_specification(
                    Mppt_low=5_000.0, Mppt_high=6_000.0, Vdcmax=6_000.0
                )
            ),
        )
    )

    result = build_detailed(configuration, index)
    diagnostics = result.diagnostics

    assert diagnostics[PV_MODULE_DC_POWER_KW].max() > 0
    assert diagnostics[PV_DC_AT_INVERTER_INPUT_KW].max() == pytest.approx(0.0)
    assert diagnostics[PV_AVAILABLE_KW].max() == pytest.approx(0.0)
    assert (diagnostics[PV_INVERTER_NIGHT_TARE_KW] > 0).all()


def test_the_string_voltage_follows_the_module_count():
    index = make_index()

    short = build_detailed(
        make_configuration(
            (unit(subarrays=(subarray(modules_per_string=10, strings=9),)),)
        ),
        index,
    ).subarray_diagnostics["inverter/subarray"]

    long = build_detailed(
        make_configuration(
            (unit(subarrays=(subarray(modules_per_string=15, strings=6),)),)
        ),
        index,
    ).subarray_diagnostics["inverter/subarray"]

    lit = short[STRING_MAXIMUM_POWER_VOLTAGE_V].to_numpy() > 0

    ratio = (
        long.loc[lit, STRING_MAXIMUM_POWER_VOLTAGE_V].to_numpy()
        / short.loc[lit, STRING_MAXIMUM_POWER_VOLTAGE_V].to_numpy()
    )

    np.testing.assert_allclose(ratio, 15.0 / 10.0, rtol=1e-9)


## Plant arrangement ------------------------------------------------------


def test_identical_inverter_instances_scale_the_plant_linearly():
    index = make_index()

    one = build(make_configuration((unit(count=1),)), index)
    five = build(make_configuration((unit(count=5),)), index)

    np.testing.assert_allclose(five.to_numpy(), 5.0 * one.to_numpy())


def test_two_mppt_inputs_differ_from_one_input_carrying_both_subarrays():
    # Two orientations tracked separately beat the same modules averaged onto
    # one input: the point of independent MPPT inputs.
    index = make_index()

    split = make_configuration(
        (
            unit(
                inverter=inverter_specification(mppt_input_count=2),
                subarrays=(
                    subarray(name="south", azimuth_degrees=180.0, strings=3),
                    subarray(name="east", azimuth_degrees=90.0, strings=3),
                ),
            ),
        )
    )

    result = build_detailed(split, index)

    assert len(result.subarray_diagnostics) == 2
    assert energy_kwh(result.pv_available_kw, index) > 0

    # Each input is tracked at its own voltage, so the two subarrays sit at
    # different operating points during the day.
    south = result.subarray_diagnostics["inverter/south"]
    east = result.subarray_diagnostics["inverter/east"]

    assert not np.allclose(
        south[PV_MODULE_DC_POWER_KW].to_numpy(),
        east[PV_MODULE_DC_POWER_KW].to_numpy(),
    )


def test_subarray_frames_sum_to_the_plant_dc_stages():
    index = make_index()
    configuration = make_configuration(
        (
            unit(
                name="a",
                count=2,
                inverter=inverter_specification(mppt_input_count=2),
                subarrays=(
                    subarray(name="south", azimuth_degrees=180.0),
                    subarray(name="west", azimuth_degrees=270.0),
                ),
            ),
        )
    )

    result = build_detailed(configuration, index)

    total = sum(
        frame[PV_MODULE_DC_POWER_KW].to_numpy() * 2
        for frame in result.subarray_diagnostics.values()
    )

    np.testing.assert_allclose(
        result.diagnostics[PV_MODULE_DC_POWER_KW].to_numpy(), total
    )


def test_inverter_frames_sum_to_the_plant_ac_stages():
    index = make_index()
    configuration = make_configuration(
        (
            unit(name="a", inverter=small_inverter()),
            unit(name="b", inverter=inverter_specification()),
        )
    )

    result = build_detailed(configuration, index)

    for column in (
        PV_AC_BEFORE_CLIPPING_KW,
        PV_INVERTER_CLIPPING_KW,
        PV_AVAILABLE_KW,
    ):
        total = sum(
            frame[column].to_numpy()
            for frame in result.inverter_diagnostics.values()
        )
        np.testing.assert_allclose(
            result.diagnostics[column].to_numpy(), total
        )


## Physical behaviour -----------------------------------------------------


def test_a_south_facing_array_beats_north_in_the_northern_hemisphere():
    index = make_index()

    south = build(
        make_configuration(
            (unit(subarrays=(subarray(azimuth_degrees=180.0),)),)
        ),
        index,
    )
    north = build(
        make_configuration(
            (unit(subarrays=(subarray(azimuth_degrees=0.0),)),)
        ),
        index,
    )

    assert energy_kwh(south, index) > energy_kwh(north, index)


def test_summer_produces_more_energy_than_winter():
    summer = make_index("2026-06-21", "2026-06-21")
    winter = make_index("2026-12-21", "2026-12-21")

    configuration = make_configuration()

    assert energy_kwh(build(configuration, summer), summer) > energy_kwh(
        build(configuration, winter), winter
    )


def test_hotter_air_reduces_output_through_the_module_physics():
    index = make_index()
    configuration = make_configuration()

    cool = build(configuration, index, clear_sky_weather(index, temperature_c=10.0))
    hot = build(configuration, index, clear_sky_weather(index, temperature_c=40.0))

    assert energy_kwh(hot, index) < energy_kwh(cool, index)


def test_a_dark_horizon_produces_nothing():
    index = make_index()
    weather = clear_sky_weather(index)
    weather[[GHI_W_PER_M2, DNI_W_PER_M2, DHI_W_PER_M2]] = 0.0

    available = build(make_configuration(), index, weather)

    assert available.to_numpy() == pytest.approx(0.0)


## Source contract --------------------------------------------------------


def test_build_pv_available_kw_returns_only_the_series():
    index = make_index()
    source = EquipmentSpecificPV(
        configuration=make_configuration(),
        weather_data=clear_sky_weather(index),
    )

    available = source.build_pv_available_kw(index)

    assert isinstance(available, pd.Series)
    assert len(available) == index.interval_count
    assert available.name == PV_AVAILABLE_KW


def test_the_simple_path_still_records_the_detailed_result():
    index = make_index()
    source = EquipmentSpecificPV(
        configuration=make_configuration(),
        weather_data=clear_sky_weather(index),
    )

    assert source.last_result is None

    available = source.build_pv_available_kw(index)

    assert source.last_result is not None
    np.testing.assert_allclose(
        source.last_result.pv_available_kw.to_numpy(), available.to_numpy()
    )
    assert source.last_result.subarray_diagnostics


def test_the_supplied_weather_frame_is_never_modified():
    index = make_index()
    weather = clear_sky_weather(index)
    untouched = weather.copy(deep=True)

    build(make_configuration(), index, weather)

    pd.testing.assert_frame_equal(weather, untouched)


def test_weather_may_cover_a_longer_horizon_than_the_analysis():
    long_index = make_index("2026-06-20", "2026-06-24")
    short_index = make_index("2026-06-21", "2026-06-22")

    available = build(
        make_configuration(), short_index, clear_sky_weather(long_index)
    )

    assert len(available) == short_index.interval_count


def test_provenance_records_the_equipment_it_was_built_from():
    index = make_index()
    result = build_detailed(make_configuration(), index)
    provenance = result.provenance

    assert provenance["model_version"] == EQUIPMENT_PV_MODEL_VERSION
    assert provenance["module_model"] == "cec_single_diode"
    assert provenance["inverter_model"] == "sandia"
    assert provenance["spectral_model"] == "not modelled"
    assert provenance["is_homogeneous"] is True

    unit_record = provenance["inverter_units"][0]

    assert unit_record["inverter"] == INVERTER_NAME
    assert unit_record["subarrays"][0]["module"] == MODULE_NAME
    assert unit_record["subarrays"][0]["modules_per_string"] == (
        MODULES_PER_STRING
    )


def test_describe_names_the_equipment_and_the_model_version():
    source = EquipmentSpecificPV(
        configuration=make_configuration(),
        weather_data=clear_sky_weather(make_index()),
    )

    description = source.describe()

    assert MODULE_NAME in description
    assert INVERTER_NAME in description
    assert EQUIPMENT_PV_MODEL_VERSION in description


## Warnings ---------------------------------------------------------------


def test_heavy_clipping_is_reported_as_a_warning():
    index = make_index()
    configuration = make_configuration(
        (unit(inverter=small_inverter()),)
    )

    warnings = build_detailed(configuration, index).warnings

    assert any("clipping removes" in warning for warning in warnings)


def test_a_well_matched_inverter_raises_no_clipping_warning():
    index = make_index()

    warnings = build_detailed(make_configuration(), index).warnings

    assert not any("clipping removes" in warning for warning in warnings)


def test_a_mixed_plant_warns_that_clipping_is_per_inverter():
    index = make_index()
    configuration = make_configuration(
        (
            unit(name="a", inverter=small_inverter()),
            unit(name="b", inverter=inverter_specification()),
        )
    )

    warnings = build_detailed(configuration, index).warnings

    assert any("per-inverter diagnostics" in warning for warning in warnings)


def test_losing_dc_energy_to_the_mppt_window_is_reported():
    index = make_index()
    configuration = make_configuration(
        (unit(inverter=inverter_specification(Mppt_low=620.0)),)
    )

    warnings = build_detailed(configuration, index).warnings

    assert any("MPPT voltage window" in warning for warning in warnings)


def test_filled_weather_intervals_are_reported_as_a_warning():
    from src.timeseries.schema import MissingDataPolicy

    index = make_index()
    weather = clear_sky_weather(index).iloc[:-4]

    result = build_detailed(
        make_configuration(),
        index,
        weather,
        missing_data_policy=MissingDataPolicy.FORWARD_FILL,
    )

    assert any("modelled, not observed" in warning for warning in result.warnings)


def test_a_thin_film_module_is_flagged_as_approximate():
    # pvlib's CEC defaults describe crystalline silicon; a CdTe module
    # modelled with them gets a caveat rather than a silent approximation.
    thin_film = next(
        name
        for name in cec_module_names()
        if name.startswith("First_Solar")
    )

    specification = ModuleSpecification.from_cec_database(thin_film)

    assert not specification.is_crystalline_silicon

    index = make_index()
    configuration = make_configuration(
        (
            unit(
                inverter=inverter_specification(Vdcmax=2_000.0),
                subarrays=(
                    subarray(module=specification, modules_per_string=8),
                ),
            ),
        )
    )

    warnings = build_detailed(configuration, index).warnings

    assert any("thin-film output is approximate" in w for w in warnings)


## Phase 1 and Phase 2 side by side ---------------------------------------


def test_phase_one_remains_available_and_agrees_within_model_spread():
    # The two phases must answer the same question. They are different models,
    # so they will not agree exactly -- but a PVWatts estimate and a CEC
    # single-diode model of the same plant on the same day should not be far
    # apart, and a large gap would mean one of them is wrong.
    index = make_index()
    weather = clear_sky_weather(index)

    equipment = make_configuration()
    generic = WeatherDerivedPVConfiguration(
        latitude=LATITUDE,
        longitude=LONGITUDE,
        rated_pv_capacity_kw=equipment.rated_dc_capacity_kw,
        tilt_degrees=20.0,
        azimuth_degrees=180.0,
        inverter_ac_capacity_kw=equipment.inverter_ac_capacity_kw,
    )

    phase_two = build(equipment, index, weather)
    phase_one = WeatherDerivedPV(
        configuration=generic, weather_data=weather
    ).build_pv_available_kw(index)

    assert len(phase_one) == len(phase_two) == index.interval_count

    one = energy_kwh(phase_one, index)
    two = energy_kwh(phase_two, index)

    assert one > 0 and two > 0
    # Observed difference on this plant and day: -1.3%. The bound is loose
    # enough that ordinary pvlib movement will not trip it, and tight enough
    # that a genuine chain error in either phase will.
    assert abs(two - one) / one < 0.10


def test_both_phases_honour_the_same_contract():
    index = make_index()
    weather = clear_sky_weather(index)

    equipment = make_configuration()
    generic = WeatherDerivedPVConfiguration(
        latitude=LATITUDE,
        longitude=LONGITUDE,
        rated_pv_capacity_kw=equipment.rated_dc_capacity_kw,
        inverter_ac_capacity_kw=equipment.inverter_ac_capacity_kw,
    )

    for series, rating in (
        (build(equipment, index, weather), equipment.inverter_ac_capacity_kw),
        (
            WeatherDerivedPV(
                configuration=generic, weather_data=weather
            ).build_pv_available_kw(index),
            generic.resolved_inverter_ac_capacity_kw,
        ),
    ):
        assert series.name == PV_AVAILABLE_KW
        assert len(series) == index.interval_count
        assert (series.to_numpy() >= 0).all()
        assert series.max() <= rating + 1e-9


## Electrical control boundary --------------------------------------------


def test_the_default_control_mode_is_grid_following():
    # A grid-following inverter synchronises to a grid that already has
    # voltage and frequency, which is what makes "maximum available AC power"
    # a question about the sun and the equipment alone.
    assert make_configuration().control_mode == GRID_FOLLOWING
    assert SUPPORTED_CONTROL_MODES == (GRID_FOLLOWING,)


def test_the_control_mode_is_recorded_in_provenance():
    index = make_index()
    result = build_detailed(make_configuration(), index)

    assert result.provenance["control_mode"] == GRID_FOLLOWING


@pytest.mark.parametrize(
    "mode", ["grid_forming", "islanded", "droop", "GRID_FOLLOWING", ""]
)
def test_any_other_control_mode_is_rejected_by_name(mode):
    with pytest.raises(PVEquipmentError) as error:
        EquipmentSpecificPVConfiguration(
            latitude=LATITUDE,
            longitude=LONGITUDE,
            inverter_units=(unit(),),
            control_mode=mode,
        )

    message = str(error.value)
    assert GRID_FOLLOWING in message
    # The message says what is missing, not merely that something is.
    assert "grid-forming voltage control" in message
    assert "frequency formation" in message


def test_the_rejection_lists_the_behaviour_a_forming_plant_would_need():
    for behaviour in CONTROL_BEHAVIOUR_NOT_MODELLED:
        assert behaviour

    with pytest.raises(PVEquipmentError) as error:
        EquipmentSpecificPVConfiguration(
            latitude=LATITUDE,
            longitude=LONGITUDE,
            inverter_units=(unit(),),
            control_mode="grid_forming",
        )

    message = str(error.value)

    for behaviour in CONTROL_BEHAVIOUR_NOT_MODELLED:
        assert behaviour in message
