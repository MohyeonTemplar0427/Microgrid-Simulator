"""Equipment-specific PV model: named modules, named inverters, real strings.

Phase 1 (:mod:`src.profiles.pv_model`) estimates a *generic* array from a
nameplate DC rating and one aggregate loss fraction. This module models the
plant that was actually specified: a CEC module part number, a CEC inverter
part number, how many modules are in series, how many strings are in
parallel, how those strings are distributed across MPPT inputs, and how many
inverters there are.

Both phases return the same optimizer-facing quantity, ``pv_available_kw`` --
the maximum nonnegative AC real power available after inverter conversion and
equipment clipping, before operational curtailment. Phase 1 is unchanged and
remains the right choice when no part numbers are known.

Chain, in order, per subarray::

    weather (GHI/DNI/DHI, air temperature, wind)
      -> solar position at each interval's midpoint   (shared by the plant)
      -> plane-of-array irradiance (Hay-Davies transposition)
      -> angle-of-incidence modifier (physical IAM)
      -> effective irradiance = poa_direct * IAM + poa_diffuse
      -> cell temperature (SAPM, the subarray's mount type)
      -> CEC six-parameter single-diode curve -> module v_mp, i_mp, p_mp, v_oc
      -> string arrangement: v_string = v_mp * modules_per_string,
                             p_array  = p_mp * modules_per_string * strings
      -> DC system losses, applied once
      -> MPPT window: operate at the window edge when v_string falls outside

then, per inverter::

    each subarray feeds one MPPT input
      -> Sandia inverter model (multi-input form when there is more than one)
      -> clip at Paco
      -> x the number of identical instances of that inverter

**What is modelled here that Phase 1 cannot express.**

* *Angle of incidence.* Phase 1 folds reflection into its aggregate loss
  fraction. Here the physical IAM model is applied to the beam component, so
  a steeply tilted or badly oriented subarray is penalised at the times of day
  it actually is.
* *Module physics.* The single-diode curve responds to irradiance and
  temperature the way the specified module does, rather than through one
  linear temperature coefficient.
* *String voltage.* Modules in series set the operating voltage. That voltage
  is what decides whether the inverter can track the maximum power point at
  all, and the Sandia model's efficiency is voltage dependent.
* *Per-inverter clipping.* Clipping happens inside each inverter. On a plant
  whose inverters are not all identical, the plant total is strictly greater
  than clipping computed from plant totals -- see
  :func:`simulate_equipment_pv_stages`.

**Electrical control boundary: grid-following only.**

Every inverter here is grid-following. The utility grid is assumed to
establish voltage and frequency; the model answers how much real power the
array can inject into it. That assumption is what makes "maximum available AC
power" well posed -- it depends only on the sun, the equipment and the
inverter's own limits, and not on what an island happens to be demanding.

Grid-forming operation, islanding and the control behaviour they need are
future work, listed in :data:`CONTROL_BEHAVIOUR_NOT_MODELLED` and rejected by
name rather than silently ignored. Phase 2 also models *available* production
rather than dispatch: what the plant is told to produce is decided later, and
electrical feasibility on the network -- the OpenDSS layer -- is out of scope
here.

**What is deliberately not modelled.**

* *Spectral mismatch.* The available correlations need precipitable water or
  air mass coefficients that the weather schema does not carry. Omitting it is
  stated rather than hidden; it is a low-single-digit annual effect for
  crystalline silicon.
* *Inverter DC current limit.* The Sandia model defines no current limit, and
  the CEC database cannot supply one: its ``Idcmax`` column is exactly
  ``Pdco / Vdco`` for all 3,264 entries -- the DC operating current at rated
  power, not a datasheet maximum input current. Checking a string's
  short-circuit current against it would compare two different quantities and
  flag almost every correctly sized array, so no such check is made.
* *Electrical mismatch between differently-oriented strings sharing one MPPT
  input.* Combining dissimilar I-V curves is a real modelling problem with no
  default answer, so each subarray is required to have its own MPPT input.
  Identical parallel strings are not a mismatch case -- describe them as one
  subarray with more strings.
* *Night tare.* The Sandia model returns ``-Pnt`` when the array cannot start
  the inverter. That is inverter self-consumption, a site *load*, not negative
  PV availability. It is reported as
  :data:`PV_INVERTER_NIGHT_TARE_KW` and never subtracted from
  ``pv_available_kw``, which stays nonnegative by contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd
from pvlib import iam, inverter, irradiance, pvsystem, temperature

from ..timeseries.interval_table import IntervalIndex
from ..timeseries.schema import TIMESTAMP
from .pv_model import (
    ESTIMATED_CELL_TEMPERATURE_C,
    PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2,
    PV_AC_BEFORE_CLIPPING_KW,
    PV_AVAILABLE_KW,
    PV_DC_AFTER_SYSTEM_LOSSES_KW,
    PV_INVERTER_CLIPPING_KW,
    PV_MODULE_DC_POWER_KW,
    SOLAR_AZIMUTH_DEGREES,
    SOLAR_ZENITH_DEGREES,
    TRANSPOSITION_MODEL,
    solar_position_at,
)
from .weather import (
    DHI_W_PER_M2,
    DNI_W_PER_M2,
    GHI_W_PER_M2,
    TEMPERATURE_C,
    WIND_SPEED_M_PER_S,
)

#: Identifies the Phase 2 modelling chain. Bump when the physics changes.
EQUIPMENT_PV_MODEL_VERSION = "phase2-cec-singlediode-sandia-v1"

#: The only electrical control mode Phase 2 implements.
#:
#: A grid-following inverter does not establish voltage or frequency: it
#: synchronises to a grid that already has both, and injects real power. That
#: is what makes "maximum available AC real power" a well-posed question with
#: an answer that depends only on the sun, the equipment and the inverter's
#: own limits -- which is exactly what this module computes.
#:
#: Grid-forming operation is a different question. An inverter that forms the
#: grid sets the voltage and frequency itself, so its real-power output is
#: decided by what the island demands moment to moment, not by what the array
#: could produce. Answering it needs a load model, a frequency and voltage
#: regulation law, and a network solution -- none of which exist here.
GRID_FOLLOWING = "grid_following"

#: Accepted values for ``control_mode``. The tuple exists so the rejection
#: message can name what is supported, and so a later phase adds a mode by
#: adding to one list rather than by finding every place a mode is assumed.
SUPPORTED_CONTROL_MODES = (GRID_FOLLOWING,)

#: Behaviour that a grid-forming or islanded model would need and that this
#: module deliberately does not attempt. Named so the rejection message can
#: say what is missing rather than only that something is.
CONTROL_BEHAVIOUR_NOT_MODELLED = (
    "grid-forming voltage control",
    "frequency formation",
    "droop control",
    "black start",
    "island transition",
    "resynchronisation",
    "switching-level and PWM simulation",
)

#: Angle-of-incidence model. ``physical`` is pvlib's Fresnel/absorption model
#: for a glass cover; its defaults describe uncoated glass.
ANGLE_OF_INCIDENCE_MODEL = "physical"

#: Watts per kilowatt. The equipment databases are in W; this module reports
#: kW, because every other power column in the repository is kW.
WATTS_PER_KILOWATT = 1000.0


# --- Phase 2 diagnostic columns ----------------------------------------
#
# Phase 1's six power stages keep their exact meanings. These are additional
# columns for effects Phase 1 has no way to produce.

#: DC power actually presented to the inverter's MPPT inputs: DC after system
#: losses, further reduced when the string voltage falls outside the
#: inverter's MPPT window and the operating point must move off the maximum
#: power point. This reduction is caused by the *inverter*, which is why it
#: sits after :data:`PV_DC_AFTER_SYSTEM_LOSSES_KW` rather than inside it.
PV_DC_AT_INVERTER_INPUT_KW = "pv_dc_at_inverter_input_kw"

#: Inverter self-consumption while the array cannot start it (Sandia ``Pnt``).
#: A site load, reported positive, never subtracted from ``pv_available_kw``.
PV_INVERTER_NIGHT_TARE_KW = "pv_inverter_night_tare_kw"

#: Effective irradiance reaching the cells: plane-of-array beam after the
#: angle-of-incidence modifier, plus plane-of-array diffuse.
EFFECTIVE_IRRADIANCE_W_PER_M2 = "effective_irradiance_w_per_m2"

# Per-subarray diagnostic columns.
POA_DIRECT_W_PER_M2 = "poa_direct_w_per_m2"
POA_DIFFUSE_W_PER_M2 = "poa_diffuse_w_per_m2"
ANGLE_OF_INCIDENCE_DEGREES = "angle_of_incidence_degrees"
ANGLE_OF_INCIDENCE_MODIFIER = "angle_of_incidence_modifier"
MODULE_MAXIMUM_POWER_VOLTAGE_V = "module_maximum_power_voltage_v"
MODULE_MAXIMUM_POWER_CURRENT_A = "module_maximum_power_current_a"
STRING_MAXIMUM_POWER_VOLTAGE_V = "string_maximum_power_voltage_v"
STRING_OPEN_CIRCUIT_VOLTAGE_V = "string_open_circuit_voltage_v"
INVERTER_INPUT_VOLTAGE_V = "inverter_input_voltage_v"
MPPT_WINDOW_LIMITED = "mppt_window_limited"

#: Power-stage columns the plant diagnostics carry, in reporting order. The
#: first six are Phase 1's, unchanged in name and meaning.
EQUIPMENT_POWER_STAGE_COLUMNS = (
    TIMESTAMP,
    PV_MODULE_DC_POWER_KW,
    PV_DC_AFTER_SYSTEM_LOSSES_KW,
    PV_DC_AT_INVERTER_INPUT_KW,
    PV_AC_BEFORE_CLIPPING_KW,
    PV_INVERTER_CLIPPING_KW,
    PV_AVAILABLE_KW,
)

#: Everything the plant diagnostic frame carries.
EQUIPMENT_DIAGNOSTIC_COLUMNS = (
    TIMESTAMP,
    SOLAR_ZENITH_DEGREES,
    SOLAR_AZIMUTH_DEGREES,
    PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2,
    EFFECTIVE_IRRADIANCE_W_PER_M2,
    ESTIMATED_CELL_TEMPERATURE_C,
    PV_MODULE_DC_POWER_KW,
    PV_DC_AFTER_SYSTEM_LOSSES_KW,
    PV_DC_AT_INVERTER_INPUT_KW,
    PV_AC_BEFORE_CLIPPING_KW,
    PV_INVERTER_CLIPPING_KW,
    PV_AVAILABLE_KW,
    PV_INVERTER_NIGHT_TARE_KW,
)

#: Per-subarray diagnostic columns.
SUBARRAY_DIAGNOSTIC_COLUMNS = (
    TIMESTAMP,
    POA_DIRECT_W_PER_M2,
    POA_DIFFUSE_W_PER_M2,
    PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2,
    ANGLE_OF_INCIDENCE_DEGREES,
    ANGLE_OF_INCIDENCE_MODIFIER,
    EFFECTIVE_IRRADIANCE_W_PER_M2,
    ESTIMATED_CELL_TEMPERATURE_C,
    MODULE_MAXIMUM_POWER_VOLTAGE_V,
    MODULE_MAXIMUM_POWER_CURRENT_A,
    STRING_MAXIMUM_POWER_VOLTAGE_V,
    STRING_OPEN_CIRCUIT_VOLTAGE_V,
    INVERTER_INPUT_VOLTAGE_V,
    MPPT_WINDOW_LIMITED,
    PV_MODULE_DC_POWER_KW,
    PV_DC_AFTER_SYSTEM_LOSSES_KW,
    PV_DC_AT_INVERTER_INPUT_KW,
)

#: Per-inverter-unit diagnostic columns. Values are for all ``count``
#: instances of that unit together, so summing across units gives the plant.
INVERTER_DIAGNOSTIC_COLUMNS = (
    TIMESTAMP,
    PV_DC_AT_INVERTER_INPUT_KW,
    PV_AC_BEFORE_CLIPPING_KW,
    PV_INVERTER_CLIPPING_KW,
    PV_AVAILABLE_KW,
    PV_INVERTER_NIGHT_TARE_KW,
)


# --- Defaults -----------------------------------------------------------

#: SAPM thermal parameter sets, keyed by how the subarray is mounted.
MOUNT_TYPES = tuple(temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"])

#: Rack-mounted glass/glass, the usual ground-mount or ballasted-roof case.
DEFAULT_MOUNT_TYPE = "open_rack_glass_glass"

#: Ground reflectance for unspecified ground cover.
DEFAULT_GROUND_ALBEDO = 0.25

#: DC-side losses applied once, per subarray. These are the constituents of
#: NREL's PVWatts 14% default that are *not* modelled explicitly elsewhere in
#: this chain: soiling, shading, snow, mismatch, wiring, connections,
#: light-induced degradation, nameplate tolerance, age and availability.
#:
#: It excludes, because each is modelled in its own right here:
#: angle-of-incidence reflection (the IAM model), the cell-temperature
#: response (the single-diode curve), MPPT-window losses (the inverter's
#: voltage window) and inverter conversion and clipping (the Sandia model).
DEFAULT_SUBARRAY_DC_LOSSES_FRACTION = 0.14

#: Cell temperature at which the string open-circuit voltage is checked
#: against the inverter's maximum DC input voltage. Open-circuit voltage is
#: highest when the array is cold, so this is a design limit, not an
#: operating one: exceeding it is an equipment-damage condition rather than a
#: performance loss. Override it with the site's record low ambient.
DEFAULT_COLD_DESIGN_CELL_TEMPERATURE_C = -10.0

#: Irradiance at which the cold open-circuit voltage check is evaluated.
COLD_DESIGN_IRRADIANCE_W_PER_M2 = 1000.0

#: CEC bandgap defaults. :func:`pvlib.pvsystem.calcparams_cec` uses these
#: crystalline-silicon values; a thin-film module modelled with them carries a
#: warning rather than a silent approximation.
CRYSTALLINE_SILICON_TECHNOLOGIES = ("Mono-c-Si", "Multi-c-Si")

#: Module parameters the CEC six-parameter model needs.
REQUIRED_MODULE_PARAMETERS = (
    "alpha_sc",
    "a_ref",
    "I_L_ref",
    "I_o_ref",
    "R_sh_ref",
    "R_s",
    "Adjust",
)

#: Inverter parameters the Sandia model needs, plus the ratings this module
#: enforces that the Sandia model itself does not.
REQUIRED_INVERTER_PARAMETERS = (
    "Paco",
    "Pdco",
    "Vdco",
    "Pso",
    "C0",
    "C1",
    "C2",
    "C3",
    "Pnt",
    "Vdcmax",
    "Mppt_low",
    "Mppt_high",
)


class PVEquipmentError(ValueError):
    """Raised when an equipment-specific PV plant cannot be modelled.

    Its own type, next to :class:`src.profiles.weather.WeatherError`, because
    these are equipment and wiring problems -- a part number that is not in
    the database, a string too long for its inverter -- rather than profile
    problems.
    """


# --- Equipment databases ------------------------------------------------


@lru_cache(maxsize=None)
def _cec_database(name: str) -> pd.DataFrame:
    """Load and cache a bundled SAM/CEC database.

    pvlib ships these as CSV files, so nothing here touches the network. The
    module database is ~21,500 entries and costs a second or so to parse,
    hence the cache.
    """

    return pvsystem.retrieve_sam(name)


def cec_module_names() -> tuple[str, ...]:
    """Every CEC module part number available offline."""

    return tuple(_cec_database("CECMod").columns)


def cec_inverter_names() -> tuple[str, ...]:
    """Every CEC inverter part number available offline."""

    return tuple(_cec_database("CECInverter").columns)


def _lookup(database: str, name: str, label: str) -> pd.Series:
    frame = _cec_database(database)

    if name not in frame.columns:
        near = [column for column in frame.columns if name.lower() in column.lower()]
        suggestion = (
            f" Did you mean one of {near[:5]}?"
            if near
            else " Names come from the CEC database bundled with pvlib; list "
            "them with cec_module_names() or cec_inverter_names()."
        )
        raise PVEquipmentError(f"{label} {name!r} is not in the CEC database.{suggestion}")

    return frame[name]


# --- Specifications -----------------------------------------------------


@dataclass(frozen=True)
class ModuleSpecification:
    """One PV module, described by its CEC six-parameter set.

    Build it from the bundled database with :meth:`from_cec_database`, or pass
    ``parameters`` directly when modelling a module the database does not
    carry. ``rated_power_w`` is the STC nameplate, used only for reporting DC
    capacity -- no power calculation uses it, because the single-diode curve
    produces power from the parameters themselves.
    """

    name: str
    parameters: dict[str, float]
    rated_power_w: float
    technology: str = "unspecified"

    def __post_init__(self) -> None:
        missing = [
            parameter
            for parameter in REQUIRED_MODULE_PARAMETERS
            if parameter not in self.parameters
        ]

        if missing:
            raise PVEquipmentError(
                f"Module {self.name!r} is missing CEC six-parameter values "
                f"{missing}. Required: {list(REQUIRED_MODULE_PARAMETERS)}."
            )

        if self.rated_power_w <= 0:
            raise PVEquipmentError(
                f"Module {self.name!r} has a nonpositive STC rating "
                f"({self.rated_power_w} W)."
            )

    @classmethod
    def from_cec_database(cls, name: str) -> "ModuleSpecification":
        """Look a module up by CEC part number. Offline; no network access."""

        entry = _lookup("CECMod", name, "Module")

        return cls(
            name=name,
            parameters={
                parameter: float(entry[parameter])
                for parameter in REQUIRED_MODULE_PARAMETERS
            },
            rated_power_w=float(entry["STC"]),
            technology=str(entry.get("Technology", "unspecified")),
        )

    @property
    def is_crystalline_silicon(self) -> bool:
        return self.technology in CRYSTALLINE_SILICON_TECHNOLOGIES


@dataclass(frozen=True)
class InverterSpecification:
    """One inverter, described by its Sandia/CEC parameter set.

    ``mppt_input_count`` is a property of the hardware that the CEC database
    does not record, so it is declared here. It is the number of independent
    MPPT inputs, and therefore the maximum number of subarrays one instance of
    this inverter can track separately.
    """

    name: str
    parameters: dict[str, float]
    mppt_input_count: int = 1

    def __post_init__(self) -> None:
        missing = [
            parameter
            for parameter in REQUIRED_INVERTER_PARAMETERS
            if parameter not in self.parameters
        ]

        if missing:
            raise PVEquipmentError(
                f"Inverter {self.name!r} is missing Sandia parameters "
                f"{missing}. Required: {list(REQUIRED_INVERTER_PARAMETERS)}."
            )

        if self.mppt_input_count < 1:
            raise PVEquipmentError(
                f"Inverter {self.name!r} must have at least one MPPT input; "
                f"received {self.mppt_input_count}."
            )

        if self.parameters["Mppt_low"] >= self.parameters["Mppt_high"]:
            raise PVEquipmentError(
                f"Inverter {self.name!r} has an empty MPPT window: "
                f"Mppt_low {self.parameters['Mppt_low']} is not below "
                f"Mppt_high {self.parameters['Mppt_high']}."
            )

    @classmethod
    def from_cec_database(
        cls,
        name: str,
        *,
        mppt_input_count: int = 1,
    ) -> "InverterSpecification":
        """Look an inverter up by CEC part number. Offline; no network access."""

        entry = _lookup("CECInverter", name, "Inverter")

        parameters = {
            parameter: float(entry[parameter])
            for parameter in REQUIRED_INVERTER_PARAMETERS
        }

        return cls(
            name=name,
            parameters=parameters,
            mppt_input_count=mppt_input_count,
        )

    @property
    def ac_capacity_kw(self) -> float:
        """``Paco``, the AC power rating at which this inverter clips."""

        return float(self.parameters["Paco"]) / WATTS_PER_KILOWATT


# --- Plant configuration ------------------------------------------------


@dataclass(frozen=True)
class SubarrayConfiguration:
    """Modules of one type, at one orientation, wired one way.

    A subarray is the unit of electrical sameness: every string in it has the
    same modules, the same count in series, the same tilt and azimuth and the
    same mounting. That is what makes it legitimate to model the whole
    subarray as one scaled module.

    ``strings`` are in parallel, so they add current; ``modules_per_string``
    are in series, so they add voltage. Two orientations therefore cannot
    share a subarray -- and cannot share an MPPT input either, which
    :class:`InverterUnitConfiguration` enforces.

    **Azimuth convention:** 0 north, 90 east, 180 south, 270 west, matching
    pvlib's ``surface_azimuth``.
    """

    module: ModuleSpecification
    modules_per_string: int
    strings: int
    tilt_degrees: float
    azimuth_degrees: float = 180.0
    mount_type: str = DEFAULT_MOUNT_TYPE
    ground_albedo: float = DEFAULT_GROUND_ALBEDO
    dc_losses_fraction: float = DEFAULT_SUBARRAY_DC_LOSSES_FRACTION
    name: str = "subarray"

    def __post_init__(self) -> None:
        if self.modules_per_string < 1:
            raise PVEquipmentError(
                f"Subarray {self.name!r} needs at least one module per "
                f"string; received {self.modules_per_string}."
            )

        if self.strings < 1:
            raise PVEquipmentError(
                f"Subarray {self.name!r} needs at least one string; received "
                f"{self.strings}."
            )

        if not 0 <= self.tilt_degrees <= 90:
            raise PVEquipmentError(
                f"Subarray {self.name!r} tilt must be between 0 (horizontal) "
                f"and 90 (vertical); received {self.tilt_degrees}."
            )

        if not 0 <= self.azimuth_degrees < 360:
            raise PVEquipmentError(
                f"Subarray {self.name!r} azimuth must be in [0, 360): 0 "
                f"north, 90 east, 180 south, 270 west. Received "
                f"{self.azimuth_degrees}."
            )

        if self.mount_type not in MOUNT_TYPES:
            raise PVEquipmentError(
                f"Subarray {self.name!r} mount type {self.mount_type!r} is "
                f"not a SAPM thermal model. Choose one of "
                f"{list(MOUNT_TYPES)}."
            )

        if not 0 <= self.dc_losses_fraction < 1:
            raise PVEquipmentError(
                f"Subarray {self.name!r} DC losses must be a fraction in "
                f"[0, 1); received {self.dc_losses_fraction}."
            )

        if not 0 <= self.ground_albedo <= 1:
            raise PVEquipmentError(
                f"Subarray {self.name!r} ground albedo must be between 0 and "
                f"1; received {self.ground_albedo}."
            )

    @property
    def module_count(self) -> int:
        return self.modules_per_string * self.strings

    @property
    def rated_dc_capacity_kw(self) -> float:
        """STC nameplate of this subarray."""

        return (
            self.module.rated_power_w
            * self.module_count
            / WATTS_PER_KILOWATT
        )

    @property
    def thermal_parameters(self) -> dict[str, float]:
        return temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"][self.mount_type]


@dataclass(frozen=True)
class InverterUnitConfiguration:
    """One inverter model, its subarrays, and how many identical copies exist.

    Each subarray occupies one MPPT input, so ``len(subarrays)`` must not
    exceed the inverter's ``mppt_input_count``. Strings that are genuinely
    paralleled onto the same input belong in one subarray with a larger
    ``strings`` count; two *different* orientations on one input would need a
    mismatch model this module does not have, and is rejected rather than
    approximated.

    ``count`` is the number of identical instances. Everything in
    ``subarrays`` describes **one** instance, so a plant of eight identical
    inverters is ``count=8`` and not eight entries.
    """

    inverter: InverterSpecification
    subarrays: tuple[SubarrayConfiguration, ...]
    count: int = 1
    cold_design_cell_temperature_c: float = (
        DEFAULT_COLD_DESIGN_CELL_TEMPERATURE_C
    )
    name: str = "inverter"

    def __post_init__(self) -> None:
        if not self.subarrays:
            raise PVEquipmentError(
                f"Inverter unit {self.name!r} has no subarrays connected."
            )

        if self.count < 1:
            raise PVEquipmentError(
                f"Inverter unit {self.name!r} must have at least one "
                f"instance; received {self.count}."
            )

        if len(self.subarrays) > self.inverter.mppt_input_count:
            raise PVEquipmentError(
                f"Inverter unit {self.name!r} connects "
                f"{len(self.subarrays)} subarrays to an inverter with "
                f"{self.inverter.mppt_input_count} MPPT input(s). Each "
                f"subarray needs its own MPPT input: paralleling different "
                f"orientations onto one input is an electrical mismatch "
                f"problem with no default model. If the strings really are "
                f"identical, describe them as one subarray with more strings; "
                f"otherwise declare the inverter's real mppt_input_count."
            )

        names = [subarray.name for subarray in self.subarrays]

        if len(set(names)) != len(names):
            raise PVEquipmentError(
                f"Inverter unit {self.name!r} has repeated subarray names "
                f"{sorted(names)}. Names identify the diagnostic frames, so "
                f"they must be distinct."
            )

        for subarray in self.subarrays:
            _validate_string_voltage(
                subarray,
                self.inverter,
                unit_name=self.name,
                cold_design_cell_temperature_c=(
                    self.cold_design_cell_temperature_c
                ),
            )

    @property
    def rated_dc_capacity_kw(self) -> float:
        """STC nameplate behind all ``count`` instances of this unit."""

        per_instance = sum(
            subarray.rated_dc_capacity_kw for subarray in self.subarrays
        )
        return per_instance * self.count

    @property
    def ac_capacity_kw(self) -> float:
        """Clipping rating of all ``count`` instances together."""

        return self.inverter.ac_capacity_kw * self.count


def _module_open_circuit_voltage(
    module: ModuleSpecification,
    *,
    irradiance_w_per_m2: float,
    cell_temperature_c: float,
) -> float:
    """Single-diode open-circuit voltage of one module at a stated condition."""

    parameters = pvsystem.calcparams_cec(
        effective_irradiance=irradiance_w_per_m2,
        temp_cell=cell_temperature_c,
        **module.parameters,
    )

    return float(pvsystem.singlediode(*parameters)["v_oc"])


def _validate_string_voltage(
    subarray: SubarrayConfiguration,
    inverter_specification: InverterSpecification,
    *,
    unit_name: str,
    cold_design_cell_temperature_c: float,
) -> None:
    """Reject a string that would overvolt its inverter when cold.

    Open-circuit voltage rises as the array cools, so the binding case is the
    coldest morning, not the hottest afternoon. Exceeding ``Vdcmax`` damages
    the inverter rather than merely costing energy, which is why this raises
    instead of warning.
    """

    cold_voltage = (
        _module_open_circuit_voltage(
            subarray.module,
            irradiance_w_per_m2=COLD_DESIGN_IRRADIANCE_W_PER_M2,
            cell_temperature_c=cold_design_cell_temperature_c,
        )
        * subarray.modules_per_string
    )

    maximum = float(inverter_specification.parameters["Vdcmax"])

    if cold_voltage > maximum:
        largest = int(maximum / (cold_voltage / subarray.modules_per_string))
        raise PVEquipmentError(
            f"Subarray {subarray.name!r} on inverter unit {unit_name!r} puts "
            f"{subarray.modules_per_string} modules in series, reaching "
            f"{cold_voltage:,.0f} V open circuit at "
            f"{cold_design_cell_temperature_c:.0f} degC cell "
            f"temperature and {COLD_DESIGN_IRRADIANCE_W_PER_M2:,.0f} W/m^2. "
            f"That is above the inverter's {maximum:,.0f} V maximum DC input "
            f"voltage, which is an equipment-damage limit rather than a "
            f"performance one. At most {largest} modules per string fit this "
            f"inverter under that design condition."
        )


@dataclass(frozen=True)
class EquipmentSpecificPVConfiguration:
    """A whole PV plant, described by the equipment it is built from.

    One location, one or more inverter units. Nothing here is a nameplate the
    user types in: DC capacity, AC capacity and DC/AC ratio are all *derived*
    from the modules and inverters, which is the point of Phase 2. A design
    that does not add up cannot be described.

    **Azimuth convention:** 0 north, 90 east, 180 south, 270 west.
    """

    latitude: float
    longitude: float
    inverter_units: tuple[InverterUnitConfiguration, ...]
    control_mode: str = GRID_FOLLOWING
    model_version: str = EQUIPMENT_PV_MODEL_VERSION

    def __post_init__(self) -> None:
        if self.control_mode not in SUPPORTED_CONTROL_MODES:
            raise PVEquipmentError(
                f"control_mode {self.control_mode!r} is not implemented. "
                f"Phase 2 models {GRID_FOLLOWING!r} inverters only: the grid "
                f"establishes voltage and frequency, and the model answers "
                f"how much real power the array can inject into it. It does "
                f"not model "
                f"{', '.join(CONTROL_BEHAVIOUR_NOT_MODELLED)}, all of which a "
                f"grid-forming or islanded plant would need. Supported: "
                f"{list(SUPPORTED_CONTROL_MODES)}."
            )

        if not -90 <= self.latitude <= 90:
            raise PVEquipmentError(
                f"Latitude must be between -90 and 90; received "
                f"{self.latitude}."
            )

        if not -180 <= self.longitude <= 180:
            raise PVEquipmentError(
                f"Longitude must be between -180 and 180; received "
                f"{self.longitude}."
            )

        if not self.inverter_units:
            raise PVEquipmentError(
                "A plant needs at least one inverter unit. An equipment "
                "specific plant with no equipment cannot be modelled; use the "
                "Phase 1 weather-derived source with a zero capacity to model "
                "a site without PV."
            )

        names = [unit.name for unit in self.inverter_units]

        if len(set(names)) != len(names):
            raise PVEquipmentError(
                f"Inverter unit names repeat: {sorted(names)}. Names identify "
                f"the per-inverter diagnostic frames, so they must be "
                f"distinct."
            )

    @property
    def rated_dc_capacity_kw(self) -> float:
        """Plant STC DC nameplate, summed from the modules that are there."""

        return sum(unit.rated_dc_capacity_kw for unit in self.inverter_units)

    @property
    def inverter_ac_capacity_kw(self) -> float:
        """Plant AC rating, summed from the inverters that are there."""

        return sum(unit.ac_capacity_kw for unit in self.inverter_units)

    @property
    def dc_ac_ratio(self) -> float:
        capacity = self.inverter_ac_capacity_kw

        if capacity <= 0:
            return float("inf")

        return self.rated_dc_capacity_kw / capacity

    @property
    def subarrays(self) -> tuple[SubarrayConfiguration, ...]:
        return tuple(
            subarray
            for unit in self.inverter_units
            for subarray in unit.subarrays
        )

    @property
    def is_homogeneous(self) -> bool:
        """True when every inverter in the plant sees the same DC design.

        Clipping is a per-inverter event. On a homogeneous plant every
        inverter clips at the same moment and by the same amount, so plant
        clipping equals ``max(plant AC before clipping - plant AC rating, 0)``
        -- the Phase 1 identity. On a mixed plant it does not, and this flag
        is how a caller knows which is which.
        """

        return len(self.inverter_units) == 1


# --- Physics ------------------------------------------------------------


def _subarray_irradiance(
    weather_frame: pd.DataFrame,
    solar_position: pd.DataFrame,
    subarray: SubarrayConfiguration,
    dni_extra: np.ndarray,
) -> dict[str, np.ndarray]:
    """Plane-of-array irradiance and the angle-of-incidence modifier."""

    zenith = solar_position["apparent_zenith"].to_numpy()
    azimuth = solar_position["azimuth"].to_numpy()

    total = irradiance.get_total_irradiance(
        surface_tilt=subarray.tilt_degrees,
        surface_azimuth=subarray.azimuth_degrees,
        solar_zenith=zenith,
        solar_azimuth=azimuth,
        dni=weather_frame[DNI_W_PER_M2].to_numpy(dtype=float),
        ghi=weather_frame[GHI_W_PER_M2].to_numpy(dtype=float),
        dhi=weather_frame[DHI_W_PER_M2].to_numpy(dtype=float),
        dni_extra=dni_extra,
        albedo=subarray.ground_albedo,
        model=TRANSPOSITION_MODEL,
    )

    def clean(key: str) -> np.ndarray:
        values = np.asarray(total[key], dtype=float)
        return np.nan_to_num(values, nan=0.0).clip(min=0.0)

    poa_global = clean("poa_global")
    poa_direct = clean("poa_direct")
    poa_diffuse = clean("poa_diffuse")

    angle_of_incidence = np.asarray(
        irradiance.aoi(
            subarray.tilt_degrees,
            subarray.azimuth_degrees,
            zenith,
            azimuth,
        ),
        dtype=float,
    )

    # The physical IAM model is undefined beyond grazing incidence; pvlib
    # returns NaN there. Beyond 90 degrees the sun is behind the plane and
    # there is no beam component to modify anyway.
    modifier = np.nan_to_num(
        np.asarray(iam.physical(angle_of_incidence), dtype=float),
        nan=0.0,
    ).clip(min=0.0)

    return {
        POA_DIRECT_W_PER_M2: poa_direct,
        POA_DIFFUSE_W_PER_M2: poa_diffuse,
        PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2: poa_global,
        ANGLE_OF_INCIDENCE_DEGREES: np.nan_to_num(
            angle_of_incidence, nan=180.0
        ),
        ANGLE_OF_INCIDENCE_MODIFIER: modifier,
        EFFECTIVE_IRRADIANCE_W_PER_M2: poa_direct * modifier + poa_diffuse,
    }


def _single_diode_curve(
    module: ModuleSpecification,
    effective_irradiance_w_per_m2: np.ndarray,
    cell_temperature_c: np.ndarray,
) -> dict[str, np.ndarray]:
    """Module operating point from the CEC six-parameter model.

    Evaluated only where there is light. The single-diode equation has no
    solution at zero irradiance -- the solver returns NaN and emits a divide
    warning -- and a dark module produces nothing, so unlit intervals are
    filled with zeros directly rather than being cleaned up afterwards.
    """

    lit = effective_irradiance_w_per_m2 > 0
    shape = effective_irradiance_w_per_m2.shape

    curve = {
        key: np.zeros(shape, dtype=float)
        for key in ("i_sc", "v_oc", "i_mp", "v_mp", "p_mp")
    }

    if not lit.any():
        return curve

    parameters = pvsystem.calcparams_cec(
        effective_irradiance=effective_irradiance_w_per_m2[lit],
        temp_cell=cell_temperature_c[lit],
        **module.parameters,
    )

    solved = pvsystem.singlediode(*parameters)

    for key in curve:
        curve[key][lit] = np.nan_to_num(
            np.asarray(solved[key], dtype=float), nan=0.0
        )

    curve["_lit"] = lit
    curve["_parameters"] = parameters

    return curve


def _apply_mppt_window(
    subarray: SubarrayConfiguration,
    curve: dict[str, np.ndarray],
    inverter_specification: InverterSpecification,
    dc_after_losses_kw: np.ndarray,
) -> dict[str, np.ndarray]:
    """Move the operating point to the MPPT window when the string leaves it.

    A string's voltage is set by its modules, not by the inverter. When that
    voltage falls outside the inverter's tracking window the inverter cannot
    sit at the maximum power point: it operates at the nearer edge of the
    window instead, which costs power. Below the window entirely -- when even
    the open-circuit voltage is under ``Mppt_low`` -- the inverter cannot
    operate at all.

    The power at the forced voltage comes from the same I-V curve, through
    :func:`pvlib.pvsystem.i_from_v`, so the loss is the real distance along
    the curve rather than an assumed derate.
    """

    modules_per_string = subarray.modules_per_string
    string_v_mp = curve["v_mp"] * modules_per_string
    string_v_oc = curve["v_oc"] * modules_per_string

    low = float(inverter_specification.parameters["Mppt_low"])
    high = float(inverter_specification.parameters["Mppt_high"])

    lit = curve.get("_lit")

    if lit is None or not lit.any():
        zeros = np.zeros_like(string_v_mp)
        return {
            INVERTER_INPUT_VOLTAGE_V: zeros,
            MPPT_WINDOW_LIMITED: np.zeros_like(zeros, dtype=bool),
            PV_DC_AT_INVERTER_INPUT_KW: zeros,
            STRING_MAXIMUM_POWER_VOLTAGE_V: string_v_mp,
            STRING_OPEN_CIRCUIT_VOLTAGE_V: string_v_oc,
        }

    # Can the inverter run at all? Only if the string can reach the window.
    operable = lit & (string_v_oc >= low)

    operating_voltage = np.where(
        operable, np.clip(string_v_mp, low, high), 0.0
    )

    limited = operable & (
        np.abs(operating_voltage - string_v_mp) > 0.0
    )

    dc_at_input_kw = np.where(operable, dc_after_losses_kw, 0.0)

    if limited.any():
        # Re-solve the curve at the forced per-module voltage. The subset is
        # taken from the lit-only parameter arrays, so the mask has to be
        # expressed in lit-space.
        limited_within_lit = limited[lit]
        parameters = curve["_parameters"]

        forced_module_voltage = (
            operating_voltage[limited] / modules_per_string
        )

        current = np.asarray(
            pvsystem.i_from_v(
                forced_module_voltage,
                *(
                    _subset(parameter, limited_within_lit)
                    for parameter in parameters
                ),
            ),
            dtype=float,
        )

        current = np.nan_to_num(current, nan=0.0).clip(min=0.0)

        forced_power_kw = (
            operating_voltage[limited]
            * current
            * subarray.strings
            / WATTS_PER_KILOWATT
        ) * (1.0 - subarray.dc_losses_fraction)

        dc_at_input_kw[limited] = forced_power_kw

    return {
        INVERTER_INPUT_VOLTAGE_V: operating_voltage,
        MPPT_WINDOW_LIMITED: limited,
        PV_DC_AT_INVERTER_INPUT_KW: dc_at_input_kw.clip(min=0.0),
        STRING_MAXIMUM_POWER_VOLTAGE_V: string_v_mp,
        STRING_OPEN_CIRCUIT_VOLTAGE_V: string_v_oc,
    }


def _subset(parameter, mask: np.ndarray):
    """Index a single-diode parameter that may be an array or a scalar."""

    values = np.asarray(parameter, dtype=float)

    if values.ndim == 0:
        return float(values)

    return values[mask]


def simulate_subarray(
    interval_index: IntervalIndex,
    weather_frame: pd.DataFrame,
    solar_position: pd.DataFrame,
    dni_extra: np.ndarray,
    subarray: SubarrayConfiguration,
    inverter_specification: InverterSpecification,
) -> pd.DataFrame:
    """Everything one subarray does, interval by interval.

    Returns a frame carrying :data:`SUBARRAY_DIAGNOSTIC_COLUMNS`. Powers are
    for one instance of the inverter unit this subarray belongs to; the plant
    roll-up multiplies by the instance count.
    """

    fields = _subarray_irradiance(
        weather_frame, solar_position, subarray, dni_extra
    )

    cell_temperature_c = np.asarray(
        temperature.sapm_cell(
            poa_global=fields[PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2],
            temp_air=weather_frame[TEMPERATURE_C].to_numpy(dtype=float),
            wind_speed=weather_frame[WIND_SPEED_M_PER_S].to_numpy(dtype=float),
            **subarray.thermal_parameters,
        ),
        dtype=float,
    )

    curve = _single_diode_curve(
        subarray.module,
        fields[EFFECTIVE_IRRADIANCE_W_PER_M2],
        cell_temperature_c,
    )

    module_dc_kw = (
        curve["p_mp"] * subarray.module_count / WATTS_PER_KILOWATT
    ).clip(min=0.0)

    dc_after_losses_kw = module_dc_kw * (1.0 - subarray.dc_losses_fraction)

    window = _apply_mppt_window(
        subarray, curve, inverter_specification, dc_after_losses_kw
    )

    return pd.DataFrame(
        {
            TIMESTAMP: interval_index.index,
            POA_DIRECT_W_PER_M2: fields[POA_DIRECT_W_PER_M2],
            POA_DIFFUSE_W_PER_M2: fields[POA_DIFFUSE_W_PER_M2],
            PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2: fields[
                PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2
            ],
            ANGLE_OF_INCIDENCE_DEGREES: fields[ANGLE_OF_INCIDENCE_DEGREES],
            ANGLE_OF_INCIDENCE_MODIFIER: fields[ANGLE_OF_INCIDENCE_MODIFIER],
            EFFECTIVE_IRRADIANCE_W_PER_M2: fields[
                EFFECTIVE_IRRADIANCE_W_PER_M2
            ],
            ESTIMATED_CELL_TEMPERATURE_C: cell_temperature_c,
            MODULE_MAXIMUM_POWER_VOLTAGE_V: curve["v_mp"],
            MODULE_MAXIMUM_POWER_CURRENT_A: curve["i_mp"],
            STRING_MAXIMUM_POWER_VOLTAGE_V: window[
                STRING_MAXIMUM_POWER_VOLTAGE_V
            ],
            STRING_OPEN_CIRCUIT_VOLTAGE_V: window[
                STRING_OPEN_CIRCUIT_VOLTAGE_V
            ],
            INVERTER_INPUT_VOLTAGE_V: window[INVERTER_INPUT_VOLTAGE_V],
            MPPT_WINDOW_LIMITED: window[MPPT_WINDOW_LIMITED],
            PV_MODULE_DC_POWER_KW: module_dc_kw,
            PV_DC_AFTER_SYSTEM_LOSSES_KW: dc_after_losses_kw,
            PV_DC_AT_INVERTER_INPUT_KW: window[PV_DC_AT_INVERTER_INPUT_KW],
        }
    )


def _sandia_efficiency_watts(
    input_voltages_v: list[np.ndarray],
    input_powers_w: list[np.ndarray],
    inverter_specification: InverterSpecification,
) -> np.ndarray:
    """Sandia AC output **before** the ``Paco`` clip, in watts.

    :func:`pvlib.inverter.sandia` applies conversion and clipping in one call
    and exposes nothing in between, so the counterfactual "what could this DC
    have become" stage has to be reconstructed. This calls pvlib's own
    unclipped kernel and reproduces the multi-input weighting from
    :func:`pvlib.inverter.sandia_multi`, so the only thing not applied is the
    limit. A test asserts that clipping this reproduces pvlib's output bit for
    bit, which is what stops the two drifting apart.
    """

    parameters = inverter_specification.parameters
    total_dc_w = sum(input_powers_w)

    if len(input_powers_w) == 1:
        return np.asarray(
            inverter._sandia_eff(input_voltages_v[0], total_dc_w, parameters),
            dtype=float,
        )

    unclipped_w = np.zeros_like(total_dc_w, dtype=float)

    for voltage, power in zip(input_voltages_v, input_powers_w):
        share = np.zeros_like(total_dc_w, dtype=float)
        np.divide(power, total_dc_w, out=share, where=total_dc_w > 0)

        unclipped_w = unclipped_w + share * np.asarray(
            inverter._sandia_eff(voltage, total_dc_w, parameters),
            dtype=float,
        )

    return unclipped_w


def simulate_inverter_unit(
    interval_index: IntervalIndex,
    unit: InverterUnitConfiguration,
    subarray_frames: list[pd.DataFrame],
) -> pd.DataFrame:
    """AC stages for all ``count`` instances of one inverter unit.

    Each subarray occupies one MPPT input. Clipping is applied **inside** each
    instance, at ``Paco``, before the instances are added together -- which is
    where a plant of mixed inverters differs from one big equivalent inverter.

    Below the inverter's startup power ``Pso`` there is no inversion: pvlib
    returns the negative night tare there. Production is zero in those
    intervals and the tare is reported separately, because
    ``pv_available_kw`` is available *generation* and is nonnegative by
    contract, while inverter self-consumption is a site load.
    """

    parameters = unit.inverter.parameters

    input_voltages_v = [
        frame[INVERTER_INPUT_VOLTAGE_V].to_numpy(dtype=float)
        for frame in subarray_frames
    ]
    input_powers_w = [
        frame[PV_DC_AT_INVERTER_INPUT_KW].to_numpy(dtype=float)
        * WATTS_PER_KILOWATT
        for frame in subarray_frames
    ]

    total_dc_w = sum(input_powers_w)
    startup_power_w = float(parameters["Pso"])
    running = total_dc_w >= startup_power_w

    unclipped_w = _sandia_efficiency_watts(
        input_voltages_v, input_powers_w, unit.inverter
    )

    ac_before_clipping_w = np.where(running, unclipped_w, 0.0).clip(min=0.0)

    rating_w = float(parameters["Paco"])
    clipping_w = (ac_before_clipping_w - rating_w).clip(min=0.0)
    available_w = ac_before_clipping_w - clipping_w

    night_tare_w = np.where(running, 0.0, abs(float(parameters["Pnt"])))

    instances = float(unit.count)
    to_plant_kw = instances / WATTS_PER_KILOWATT

    return pd.DataFrame(
        {
            TIMESTAMP: interval_index.index,
            PV_DC_AT_INVERTER_INPUT_KW: total_dc_w * to_plant_kw,
            PV_AC_BEFORE_CLIPPING_KW: ac_before_clipping_w * to_plant_kw,
            PV_INVERTER_CLIPPING_KW: clipping_w * to_plant_kw,
            PV_AVAILABLE_KW: available_w * to_plant_kw,
            PV_INVERTER_NIGHT_TARE_KW: night_tare_w * to_plant_kw,
        }
    )


@dataclass(frozen=True)
class EquipmentPVStages:
    """Plant power stages, plus the per-subarray and per-inverter detail."""

    diagnostics: pd.DataFrame
    subarray_diagnostics: dict[str, pd.DataFrame]
    inverter_diagnostics: dict[str, pd.DataFrame]


def simulate_equipment_pv_stages(
    interval_index: IntervalIndex,
    weather_frame: pd.DataFrame,
    configuration: EquipmentSpecificPVConfiguration,
) -> EquipmentPVStages:
    """Run the equipment chain and return every power stage, aligned.

    ``weather_frame`` is read, never modified.

    Plant stage identities, which :mod:`test.test_pv_equipment` pins::

        pv_available_kw = pv_ac_before_clipping_kw - pv_inverter_clipping_kw
        pv_available_kw <= plant inverter AC rating
        every stage >= 0

    The Phase 1 form ``pv_inverter_clipping_kw = max(pv_ac_before_clipping_kw
    - rating, 0)`` holds **exactly** on a plant whose inverters are all
    identical, which is every single-unit plant however many instances it has.
    It does not hold on a mixed plant, and should not: clipping happens inside
    each inverter, so one inverter can clip while another has headroom. The
    plant total is then strictly greater than the figure plant totals would
    suggest, and :attr:`EquipmentSpecificPVConfiguration.is_homogeneous` says
    which case a caller is in.

    Operational curtailment is absent here, exactly as in Phase 1. Dispatch
    later defines ``pv_output_kw = pv_available_kw - pv_curtailed_kw``.
    """

    if len(weather_frame) != interval_index.interval_count:
        raise PVEquipmentError(
            f"Weather frame has {len(weather_frame)} rows but the interval "
            f"index has {interval_index.interval_count}. Align the weather "
            f"before simulating."
        )

    solar_position = solar_position_at(
        interval_index,
        latitude=configuration.latitude,
        longitude=configuration.longitude,
    )

    dni_extra = irradiance.get_extra_radiation(
        solar_position.index
    ).to_numpy()

    subarray_diagnostics: dict[str, pd.DataFrame] = {}
    inverter_diagnostics: dict[str, pd.DataFrame] = {}

    interval_count = interval_index.interval_count
    zeros = np.zeros(interval_count, dtype=float)

    plant = {
        PV_MODULE_DC_POWER_KW: zeros.copy(),
        PV_DC_AFTER_SYSTEM_LOSSES_KW: zeros.copy(),
        PV_DC_AT_INVERTER_INPUT_KW: zeros.copy(),
        PV_AC_BEFORE_CLIPPING_KW: zeros.copy(),
        PV_INVERTER_CLIPPING_KW: zeros.copy(),
        PV_AVAILABLE_KW: zeros.copy(),
        PV_INVERTER_NIGHT_TARE_KW: zeros.copy(),
    }

    # Plane-of-array irradiance and cell temperature differ per subarray, so
    # the plant-level figures are DC-capacity weighted means: the number a
    # reader would want if asked "what was the array seeing". Per-subarray
    # frames carry the unweighted truth.
    weighted_poa = zeros.copy()
    weighted_effective = zeros.copy()
    weighted_cell_temperature = zeros.copy()
    total_weight = 0.0

    for unit in configuration.inverter_units:
        frames: list[pd.DataFrame] = []

        for subarray in unit.subarrays:
            frame = simulate_subarray(
                interval_index,
                weather_frame,
                solar_position,
                dni_extra,
                subarray,
                unit.inverter,
            )

            frames.append(frame)

            key = f"{unit.name}/{subarray.name}"

            if key in subarray_diagnostics:
                raise PVEquipmentError(
                    f"Subarray key {key!r} appears twice. Inverter unit and "
                    f"subarray names together must identify a subarray."
                )

            subarray_diagnostics[key] = frame

            instances = float(unit.count)

            for column in (
                PV_MODULE_DC_POWER_KW,
                PV_DC_AFTER_SYSTEM_LOSSES_KW,
            ):
                plant[column] += (
                    frame[column].to_numpy(dtype=float) * instances
                )

            weight = subarray.rated_dc_capacity_kw * instances
            total_weight += weight

            weighted_poa += (
                frame[PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2].to_numpy(dtype=float)
                * weight
            )
            weighted_effective += (
                frame[EFFECTIVE_IRRADIANCE_W_PER_M2].to_numpy(dtype=float)
                * weight
            )
            weighted_cell_temperature += (
                frame[ESTIMATED_CELL_TEMPERATURE_C].to_numpy(dtype=float)
                * weight
            )

        unit_frame = simulate_inverter_unit(interval_index, unit, frames)
        inverter_diagnostics[unit.name] = unit_frame

        for column in (
            PV_DC_AT_INVERTER_INPUT_KW,
            PV_AC_BEFORE_CLIPPING_KW,
            PV_INVERTER_CLIPPING_KW,
            PV_AVAILABLE_KW,
            PV_INVERTER_NIGHT_TARE_KW,
        ):
            plant[column] += unit_frame[column].to_numpy(dtype=float)

    if total_weight > 0:
        weighted_poa /= total_weight
        weighted_effective /= total_weight
        weighted_cell_temperature /= total_weight

    diagnostics = pd.DataFrame(
        {
            TIMESTAMP: interval_index.index,
            SOLAR_ZENITH_DEGREES: solar_position["apparent_zenith"].to_numpy(),
            SOLAR_AZIMUTH_DEGREES: solar_position["azimuth"].to_numpy(),
            PLANE_OF_ARRAY_IRRADIANCE_W_PER_M2: weighted_poa,
            EFFECTIVE_IRRADIANCE_W_PER_M2: weighted_effective,
            ESTIMATED_CELL_TEMPERATURE_C: weighted_cell_temperature,
            PV_MODULE_DC_POWER_KW: plant[PV_MODULE_DC_POWER_KW],
            PV_DC_AFTER_SYSTEM_LOSSES_KW: plant[PV_DC_AFTER_SYSTEM_LOSSES_KW],
            PV_DC_AT_INVERTER_INPUT_KW: plant[PV_DC_AT_INVERTER_INPUT_KW],
            PV_AC_BEFORE_CLIPPING_KW: plant[PV_AC_BEFORE_CLIPPING_KW],
            PV_INVERTER_CLIPPING_KW: plant[PV_INVERTER_CLIPPING_KW],
            PV_AVAILABLE_KW: plant[PV_AVAILABLE_KW],
            PV_INVERTER_NIGHT_TARE_KW: plant[PV_INVERTER_NIGHT_TARE_KW],
        }
    )

    return EquipmentPVStages(
        diagnostics=diagnostics,
        subarray_diagnostics=subarray_diagnostics,
        inverter_diagnostics=inverter_diagnostics,
    )


def simulate_equipment_available_ac_kw(
    interval_index: IntervalIndex,
    weather_frame: pd.DataFrame,
    configuration: EquipmentSpecificPVConfiguration,
) -> pd.Series:
    """Return only ``pv_available_kw``, for callers that want nothing else."""

    stages = simulate_equipment_pv_stages(
        interval_index, weather_frame, configuration
    )

    return pd.Series(
        stages.diagnostics[PV_AVAILABLE_KW].to_numpy(), name=PV_AVAILABLE_KW
    )


def design_warnings(
    configuration: EquipmentSpecificPVConfiguration,
) -> tuple[str, ...]:
    """Equipment-design concerns that do not make the plant unmodellable.

    These are reported rather than raised, because each one still produces a
    number a reader can reason about -- unlike a string that would overvolt
    its inverter, which :func:`_validate_string_voltage` refuses outright.
    """

    warnings: list[str] = []

    for unit in configuration.inverter_units:
        for subarray in unit.subarrays:
            if not subarray.module.is_crystalline_silicon:
                warnings.append(
                    f"Subarray {unit.name}/{subarray.name} uses a "
                    f"{subarray.module.technology} module. The CEC "
                    f"single-diode model is evaluated with pvlib's default "
                    f"bandgap parameters, which describe crystalline silicon; "
                    f"thin-film output is approximate."
                )

    if not configuration.is_homogeneous:
        warnings.append(
            f"This plant has {len(configuration.inverter_units)} different "
            f"inverter units. Clipping is computed inside each inverter and "
            f"then summed, so plant clipping is greater than "
            f"max(plant AC before clipping - plant AC rating, 0): one "
            f"inverter can clip while another still has headroom. Compare "
            f"per-inverter diagnostics rather than plant totals when "
            f"attributing clipping."
        )

    return tuple(warnings)
