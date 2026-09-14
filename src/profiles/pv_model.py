"""Simplified generic-array PV model: weather in, available AC power out.

This is a **PVWatts-style estimate for a generic fixed-tilt array**. It
deliberately does not ask for a module or inverter part number; it asks for
nameplate DC capacity, an orientation, a temperature coefficient, an inverter
size and one aggregate loss fraction. Anything needing a specific module
belongs to a later phase.

Chain, in order::

    weather (GHI/DNI/DHI, air temperature, wind)
      -> solar position at each interval's midpoint
      -> plane-of-array irradiance (Hay-Davies transposition)
      -> cell temperature (SAPM, open-rack glass/glass)
      -> DC power (PVWatts, includes the temperature derate)
      -> aggregate system losses, applied once
      -> inverter conversion and AC clipping (PVWatts inverter)
      -> pv_available_kw

**Where each loss is applied, and why only once.**

* *Temperature* is inside :func:`pvlib.pvsystem.pvwatts_dc` via
  ``gamma_pdc``. It is therefore **not** part of the aggregate loss fraction.
* *Aggregate system losses* (soiling, shading, mismatch, wiring, connections,
  light-induced degradation, nameplate tolerance, availability) are applied
  once to DC power. This follows NREL's PVWatts convention, whose 14% default
  explicitly **excludes** inverter efficiency and temperature. Angle-of-
  incidence reflection and spectral mismatch are also folded in here, which
  is why plane-of-array global irradiance is passed straight to
  ``pvwatts_dc`` as effective irradiance.
* *Inverter conversion* happens once, in :func:`pvlib.inverter.pvwatts`,
  which also performs the AC clip. Passing ``nominal_inverter_efficiency`` to
  the inverter model **and** including it in ``system_losses_fraction`` would
  double count it; the configuration validates that the loss fraction stays in
  the PVWatts range so this is hard to do by accident.

**Interval midpoints.** Timestamps are interval *starts*, but irradiance over
a 15-minute interval is an average, not an instant. Solar position is
therefore evaluated at ``start + timestep/2``. Using the start instant biases
every interval's sun position backwards by half a step, which is most visible
at sunrise and sunset.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pvlib import inverter, irradiance, pvsystem, solarposition, temperature

from ..timeseries.interval_table import IntervalIndex
from ..timeseries.schema import TIMESTAMP
from .weather import (
    DHI_W_PER_M2,
    DNI_W_PER_M2,
    GHI_W_PER_M2,
    TEMPERATURE_C,
    WIND_SPEED_M_PER_S,
)

# --- Diagnostic column names -------------------------------------------
#
# The power stages a later GUI or dispatch integration needs in order to say
# *why* a number is what it is: how much the modules made, what the system
# losses took, what the inverter could have produced, and what its AC rating
# refused. Names are fixed because downstream code and saved results depend
# on them.

#: DC power at the maximum power point, from irradiance and cell temperature,
#: before any configured system losses. Generic array, not a specific module.
PV_MODULE_DC_POWER_KW = "pv_module_dc_power_kw"

#: DC power remaining after the aggregate non-inverter system losses --
#: soiling, shading, mismatch, wiring, connections, light-induced
#: degradation, nameplate tolerance, availability, and the angle-of-incidence
#: and spectral terms folded into the same fraction. Inverter conversion loss
#: is **not** included here; it is applied in the next stage.
PV_DC_AFTER_SYSTEM_LOSSES_KW = "pv_dc_after_system_losses_kw"

#: Counterfactual AC power the inverter model would produce from that DC if
#: its AC rating did not exist. Conversion efficiency is applied; operational
#: dispatch curtailment is not.
PV_AC_BEFORE_CLIPPING_KW = "pv_ac_before_clipping_kw"

#: AC production lost to the inverter's AC rating alone.
PV_INVERTER_CLIPPING_KW = "pv_inverter_clipping_kw"

#: Canonical optimizer-facing output: maximum AC power available before
#: operational curtailment.
PV_AVAILABLE_KW = "pv_available_kw"

#: Intermediate solar and thermal quantities, kept so a surprising power
#: number can be traced to the sun position and cell temperature behind it.
SOLAR_ZENITH_DEGREES = "solar_zenith_degrees"
SOLAR_AZIMUTH_DEGREES = "solar_azimuth_degrees"
PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2 = "plane_of_array_irradiance_w_per_m2"
ESTIMATED_CELL_TEMPERATURE_C = "estimated_cell_temperature_c"

#: Required power-stage columns, in reporting order.
POWER_STAGE_COLUMNS = (
    TIMESTAMP,
    PV_MODULE_DC_POWER_KW,
    PV_DC_AFTER_SYSTEM_LOSSES_KW,
    PV_AC_BEFORE_CLIPPING_KW,
    PV_INVERTER_CLIPPING_KW,
    PV_AVAILABLE_KW,
)

#: Everything the diagnostic frame carries.
DIAGNOSTIC_COLUMNS = (
    TIMESTAMP,
    SOLAR_ZENITH_DEGREES,
    SOLAR_AZIMUTH_DEGREES,
    PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2,
    ESTIMATED_CELL_TEMPERATURE_C,
    PV_MODULE_DC_POWER_KW,
    PV_DC_AFTER_SYSTEM_LOSSES_KW,
    PV_AC_BEFORE_CLIPPING_KW,
    PV_INVERTER_CLIPPING_KW,
    PV_AVAILABLE_KW,
)

#: Identifies the modelling chain that produced a profile. Bump this whenever
#: the physics changes, so a stored result can be traced to how it was made.
PV_MODEL_VERSION = "phase1-pvwatts-haydavies-sapm-openrack-v1"

#: Sky-diffuse transposition model. Hay-Davies adds a circumsolar term that
#: isotropic omits, which matters on a tilted plane, and needs only
#: extraterrestrial irradiance as an extra input.
TRANSPOSITION_MODEL = "haydavies"

#: Thermal coefficients for an open-rack glass/glass module, the SAPM set
#: PVWatts-style estimates conventionally use for a generic rack-mounted array.
CELL_TEMPERATURE_PARAMETERS = temperature.TEMPERATURE_MODEL_PARAMETERS[
    "sapm"
]["open_rack_glass_glass"]


def interval_midpoints(interval_index: IntervalIndex) -> pd.DatetimeIndex:
    """Instants at which to evaluate solar position.

    Interval counts and spacing come from the generated index, so a
    daylight-saving day with 92 or 100 intervals is handled without any
    day-length assumption.
    """

    half_step = pd.Timedelta(minutes=interval_index.timestep_minutes) / 2
    return interval_index.index + half_step


def solar_position_at(
    interval_index: IntervalIndex,
    *,
    latitude: float,
    longitude: float,
) -> pd.DataFrame:
    """Apparent solar position at each interval midpoint.

    pvlib converts the timezone-aware index to UTC internally, so the result
    is correct across daylight-saving transitions; local wall-clock hours are
    never used.
    """

    return solarposition.get_solarposition(
        interval_midpoints(interval_index),
        latitude,
        longitude,
    )


def plane_of_array_irradiance(
    weather_frame: pd.DataFrame,
    solar_position: pd.DataFrame,
    *,
    tilt_degrees: float,
    azimuth_degrees: float,
    ground_albedo: float,
) -> pd.Series:
    """Transpose horizontal irradiance onto the fixed array plane.

    ``azimuth_degrees`` uses the repository convention -- 0 north, 90 east,
    180 south, 270 west -- which is also pvlib's ``surface_azimuth``
    convention, so no conversion is applied.
    """

    times = solar_position.index

    total = irradiance.get_total_irradiance(
        surface_tilt=tilt_degrees,
        surface_azimuth=azimuth_degrees,
        solar_zenith=solar_position["apparent_zenith"].to_numpy(),
        solar_azimuth=solar_position["azimuth"].to_numpy(),
        dni=weather_frame[DNI_W_PER_M2].to_numpy(dtype=float),
        ghi=weather_frame[GHI_W_PER_M2].to_numpy(dtype=float),
        dhi=weather_frame[DHI_W_PER_M2].to_numpy(dtype=float),
        dni_extra=irradiance.get_extra_radiation(times).to_numpy(),
        albedo=ground_albedo,
        model=TRANSPOSITION_MODEL,
    )

    poa_global = pd.Series(
        np.asarray(total["poa_global"], dtype=float),
        name=PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2,
    )

    # Hay-Davies can return a small negative or NaN when the sun is below the
    # horizon and the inputs are all zero. Those intervals contribute nothing.
    return poa_global.fillna(0.0).clip(lower=0.0)


def cell_temperature(
    poa_global_w_per_m2: pd.Series,
    weather_frame: pd.DataFrame,
) -> pd.Series:
    """Module cell temperature from irradiance, air temperature and wind."""

    values = temperature.sapm_cell(
        poa_global=poa_global_w_per_m2.to_numpy(dtype=float),
        temp_air=weather_frame[TEMPERATURE_C].to_numpy(dtype=float),
        wind_speed=weather_frame[WIND_SPEED_M_PER_S].to_numpy(dtype=float),
        **CELL_TEMPERATURE_PARAMETERS,
    )

    return pd.Series(np.asarray(values, dtype=float), name=ESTIMATED_CELL_TEMPERATURE_C)


def dc_power_kw(
    poa_global_w_per_m2: pd.Series,
    cell_temperature_c: pd.Series,
    *,
    rated_pv_capacity_kw: float,
    power_temperature_coefficient_per_c: float,
) -> pd.Series:
    """Generic-array DC power, including the cell-temperature derate."""

    values = pvsystem.pvwatts_dc(
        effective_irradiance=poa_global_w_per_m2.to_numpy(dtype=float),
        temp_cell=cell_temperature_c.to_numpy(dtype=float),
        pdc0=rated_pv_capacity_kw,
        gamma_pdc=power_temperature_coefficient_per_c,
    )

    return pd.Series(
        np.asarray(values, dtype=float), name=PV_MODULE_DC_POWER_KW
    ).fillna(0.0).clip(lower=0.0)


#: pvlib's PVWatts inverter reference efficiency. Used to reproduce pvlib's
#: efficiency curve when computing AC power *before* the AC-rating clip,
#: which :func:`pvlib.inverter.pvwatts` does not expose separately.
PVWATTS_INVERTER_REFERENCE_EFFICIENCY = 0.9637


def _pvwatts_inverter_efficiency(
    dc_kw: np.ndarray,
    dc_input_limit_kw: float,
    nominal_inverter_efficiency: float,
) -> np.ndarray:
    """Part-load efficiency of the PVWatts inverter model.

    This mirrors :func:`pvlib.inverter.pvwatts` exactly, minus its final clip
    to the AC rating. Reproducing the curve is what lets the diagnostics
    report a counterfactual "before clipping" stage; a test asserts that
    clipping this result reproduces pvlib's output bit for bit, so the two
    cannot drift apart silently.
    """

    zeta = np.zeros_like(dc_kw, dtype=float)

    if dc_input_limit_kw > 0:
        zeta = dc_kw / dc_input_limit_kw

    # Where dc is zero the reciprocal term is undefined; pvlib leaves it at
    # zero, and the efficiency is multiplied by zero power anyway.
    reciprocal_term = np.zeros_like(dc_kw, dtype=float)
    np.divide(0.0059, zeta, out=reciprocal_term, where=dc_kw != 0)

    return (
        nominal_inverter_efficiency
        / PVWATTS_INVERTER_REFERENCE_EFFICIENCY
        * (-0.0162 * zeta - reciprocal_term + 0.9858)
    )


def ac_before_clipping_kw(
    dc_after_losses_kw: pd.Series,
    *,
    inverter_ac_capacity_kw: float,
    nominal_inverter_efficiency: float,
) -> pd.Series:
    """AC power the inverter model would produce with no AC-rating limit.

    Counterfactual: it answers "how much AC could this DC have become", so
    the difference against the rated output is attributable to clipping and
    to nothing else. Conversion efficiency *is* applied here; operational
    curtailment is not, and never is in this module.
    """

    if inverter_ac_capacity_kw <= 0:
        return pd.Series(
            np.zeros(len(dc_after_losses_kw)),
            name=PV_AC_BEFORE_CLIPPING_KW,
        )

    dc_kw = dc_after_losses_kw.to_numpy(dtype=float)
    dc_input_limit_kw = inverter_ac_capacity_kw / nominal_inverter_efficiency

    efficiency = _pvwatts_inverter_efficiency(
        dc_kw,
        dc_input_limit_kw,
        nominal_inverter_efficiency,
    )

    values = np.asarray(efficiency * dc_kw, dtype=float)

    # pvlib floors its own result at zero (its GH 541); the part-load curve
    # goes negative at very small inputs. Power stages must be nonnegative.
    return pd.Series(
        np.nan_to_num(values, nan=0.0), name=PV_AC_BEFORE_CLIPPING_KW
    ).clip(lower=0.0)


def ac_power_kw(
    dc_after_losses_kw: pd.Series,
    *,
    inverter_ac_capacity_kw: float,
    nominal_inverter_efficiency: float,
) -> pd.Series:
    """Convert DC to AC and clip at the inverter's AC rating.

    Equivalent to :func:`pvlib.inverter.pvwatts` with ``pdc0`` set to the
    inverter's DC input limit, which places the clip exactly at the requested
    AC rating.
    """

    unclipped = ac_before_clipping_kw(
        dc_after_losses_kw,
        inverter_ac_capacity_kw=inverter_ac_capacity_kw,
        nominal_inverter_efficiency=nominal_inverter_efficiency,
    )

    return pd.Series(
        unclipped.to_numpy().clip(0.0, max(inverter_ac_capacity_kw, 0.0)),
        name=PV_AVAILABLE_KW,
    )


def simulate_pv_stages(
    interval_index: IntervalIndex,
    weather_frame: pd.DataFrame,
    *,
    latitude: float,
    longitude: float,
    rated_pv_capacity_kw: float,
    tilt_degrees: float,
    azimuth_degrees: float,
    inverter_ac_capacity_kw: float,
    power_temperature_coefficient_per_c: float,
    nominal_inverter_efficiency: float,
    system_losses_fraction: float,
    ground_albedo: float,
) -> pd.DataFrame:
    """Run the chain and return every power stage, timestamp-aligned.

    The returned frame carries :data:`DIAGNOSTIC_COLUMNS`: the required power
    stages plus the intermediate solar and thermal quantities that produced
    them. ``weather_frame`` is read, never modified.

    Stage identities, which :mod:`test.test_pv_model` pins::

        pv_inverter_clipping_kw = max(pv_ac_before_clipping_kw - rating, 0)
        pv_available_kw         = pv_ac_before_clipping_kw
                                  - pv_inverter_clipping_kw
                                = min(pv_ac_before_clipping_kw, rating)

    Operational curtailment is deliberately absent. Dispatch later defines
    ``pv_output_kw = pv_available_kw - pv_curtailed_kw``; keeping clipping and
    curtailment separate is what makes each attributable.
    """

    if len(weather_frame) != interval_index.interval_count:
        raise ValueError(
            f"Weather frame has {len(weather_frame)} rows but the interval "
            f"index has {interval_index.interval_count}. Align the weather "
            f"before simulating."
        )

    position = solar_position_at(
        interval_index,
        latitude=latitude,
        longitude=longitude,
    )

    poa_global = plane_of_array_irradiance(
        weather_frame,
        position,
        tilt_degrees=tilt_degrees,
        azimuth_degrees=azimuth_degrees,
        ground_albedo=ground_albedo,
    )

    temperatures = cell_temperature(poa_global, weather_frame)

    module_dc_kw = dc_power_kw(
        poa_global,
        temperatures,
        rated_pv_capacity_kw=rated_pv_capacity_kw,
        power_temperature_coefficient_per_c=(
            power_temperature_coefficient_per_c
        ),
    )

    # Aggregate non-inverter losses, applied exactly once and only to DC.
    dc_after_losses_kw = module_dc_kw * (1.0 - system_losses_fraction)

    ac_unclipped_kw = ac_before_clipping_kw(
        dc_after_losses_kw,
        inverter_ac_capacity_kw=inverter_ac_capacity_kw,
        nominal_inverter_efficiency=nominal_inverter_efficiency,
    )

    rating_kw = max(float(inverter_ac_capacity_kw), 0.0)

    clipping_kw = (ac_unclipped_kw - rating_kw).clip(lower=0.0)
    available_kw = ac_unclipped_kw - clipping_kw

    return pd.DataFrame(
        {
            TIMESTAMP: interval_index.index,
            SOLAR_ZENITH_DEGREES: position["apparent_zenith"].to_numpy(),
            SOLAR_AZIMUTH_DEGREES: position["azimuth"].to_numpy(),
            PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2: poa_global.to_numpy(),
            ESTIMATED_CELL_TEMPERATURE_C: temperatures.to_numpy(),
            PV_MODULE_DC_POWER_KW: module_dc_kw.to_numpy(),
            PV_DC_AFTER_SYSTEM_LOSSES_KW: dc_after_losses_kw.to_numpy(),
            PV_AC_BEFORE_CLIPPING_KW: ac_unclipped_kw.to_numpy(),
            PV_INVERTER_CLIPPING_KW: clipping_kw.to_numpy(),
            PV_AVAILABLE_KW: available_kw.to_numpy(),
        }
    )


def simulate_available_ac_kw(
    interval_index: IntervalIndex,
    weather_frame: pd.DataFrame,
    **configuration,
) -> pd.Series:
    """Return only ``pv_available_kw``, for callers that want nothing else."""

    stages = simulate_pv_stages(interval_index, weather_frame, **configuration)

    return pd.Series(
        stages[PV_AVAILABLE_KW].to_numpy(), name=PV_AVAILABLE_KW
    )
