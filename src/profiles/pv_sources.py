"""PV-profile sources.

Every source produces ``pv_available_kw`` -- the maximum PV power available
from sunlight **before** curtailment. What the system actually delivers is
``pv_output_kw``, decided by the surplus allocation layer, and the difference
is ``pv_curtailed_kw``.

Keeping those distinct is the reason this module exists: the legacy ``pv_kw``
column conflated them, which made curtailment impossible to express.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np
import pandas as pd

from ..timeseries.interval_table import IntervalIndex, align_to_index
from ..timeseries.schema import MissingDataPolicy, PowerUnit, convert_to_kw
from .load_sources import _prepare_csv_frame
from .pv_equipment import (
    ANGLE_OF_INCIDENCE_MODEL,
    MPPT_WINDOW_LIMITED,
    PV_DC_AT_INVERTER_INPUT_KW,
    EquipmentSpecificPVConfiguration,
    design_warnings,
    simulate_equipment_pv_stages,
)
from .pv_model import (
    PV_AC_BEFORE_CLIPPING_KW,
    PV_AVAILABLE_KW,
    PV_DC_AFTER_SYSTEM_LOSSES_KW,
    PV_INVERTER_CLIPPING_KW,
    PV_MODEL_VERSION,
    TRANSPOSITION_MODEL,
    simulate_pv_stages,
)
from .weather import align_weather, prepare_weather_frame

#: Report inverter clipping once it removes more than this share of the AC
#: energy the array could otherwise have produced. Some clipping is a normal
#: consequence of a DC/AC ratio above 1; a lot of it should be deliberate.
CLIPPING_WARNING_FRACTION = 0.02

#: Report MPPT-window losses once a subarray gives up more than this
#: share of its DC energy operating off the maximum power point because
#: its string voltage leaves the inverter's tracking window. Measured in
#: energy rather than intervals: every array leaves the window at dawn
#: and dusk, when there is nothing there to lose.
MPPT_WINDOW_WARNING_FRACTION = 0.02

# Defaults for a generic fixed-tilt commercial array. Each is a convention
# rather than a measurement, so each is named and documented rather than
# buried as a literal in a signature.

#: DC nameplate divided by inverter AC rating when neither is given directly.
DEFAULT_DC_AC_RATIO = 1.20

#: Fractional power change per degree Celsius above 25 degC cell temperature.
#: Negative because module output falls as the cell warms. Representative of
#: crystalline silicon.
DEFAULT_POWER_TEMPERATURE_COEFFICIENT_PER_C = -0.004

#: Nominal inverter conversion efficiency, applied once by the inverter model.
DEFAULT_NOMINAL_INVERTER_EFFICIENCY = 0.96

#: PVWatts aggregate DC loss fraction. Excludes inverter efficiency and the
#: cell-temperature derate, both of which are modelled separately.
DEFAULT_SYSTEM_LOSSES_FRACTION = 0.14

#: Ground reflectance used by the transposition model. 0.25 is the usual
#: default for unspecified ground cover.
DEFAULT_GROUND_ALBEDO = 0.25


class PVSourceMode(StrEnum):
    SYNTHETIC = "synthetic"
    CSV_POWER = "csv_power"
    CSV_CAPACITY_FACTOR = "csv_capacity_factor"
    WEATHER = "weather"
    EQUIPMENT = "equipment"
    MEASURED_INVERTER = "measured_inverter"


class PVSourceError(ValueError):
    pass


class PVProfileSource(ABC):
    """Produces ``pv_available_kw`` over an interval index."""

    mode: PVSourceMode
    is_synthetic: bool = False

    @abstractmethod
    def build_pv_available_kw(
        self,
        interval_index: IntervalIndex,
    ) -> pd.Series:
        """Return one available-kW value per interval."""

    def describe(self) -> str:
        return self.mode.value


@dataclass
class SyntheticPV(PVProfileSource):
    """A smooth clear-sky demonstration curve.

    A half-sine between sunrise and sunset, scaled to the rated capacity. It
    models no weather, no shading and no seasonal declination -- it exists to
    demonstrate dispatch behaviour, not to estimate yield.
    """

    rated_pv_capacity_kw: float
    sunrise_hour: float = 6.0
    sunset_hour: float = 19.0
    peak_fraction_of_rating: float = 0.85

    mode = PVSourceMode.SYNTHETIC
    is_synthetic = True

    def __post_init__(self) -> None:
        if self.rated_pv_capacity_kw < 0:
            raise PVSourceError(
                f"Rated PV capacity must not be negative; received "
                f"{self.rated_pv_capacity_kw}."
            )

        if not 0 <= self.sunrise_hour < self.sunset_hour <= 24:
            raise PVSourceError(
                f"Sunrise ({self.sunrise_hour}) must be before sunset "
                f"({self.sunset_hour}), both within 0..24."
            )

        if not 0 < self.peak_fraction_of_rating <= 1:
            raise PVSourceError(
                "peak_fraction_of_rating must be between 0 and 1."
            )

    def build_pv_available_kw(
        self,
        interval_index: IntervalIndex,
    ) -> pd.Series:
        timestamps = interval_index.index

        hours = (
            timestamps.hour.to_numpy()
            + timestamps.minute.to_numpy() / 60.0
        )

        daylight_span = self.sunset_hour - self.sunrise_hour
        position = (hours - self.sunrise_hour) / daylight_span

        shape = np.where(
            (position >= 0) & (position <= 1),
            np.sin(np.pi * np.clip(position, 0, 1)),
            0.0,
        )

        values = (
            shape
            * self.rated_pv_capacity_kw
            * self.peak_fraction_of_rating
        )

        return pd.Series(values, name="pv_available_kw")

    def describe(self) -> str:
        return (
            f"Synthetic clear-sky, {self.rated_pv_capacity_kw:.2f} kW rated "
            f"- SYNTHETIC DATA"
        )


@dataclass
class CSVPowerPV(PVProfileSource):
    """Available PV power read directly from a table, in W, kW or MW."""

    data: pd.DataFrame
    timestamp_column: str = "timestamp"
    pv_column: str = "pv_kw"
    unit: PowerUnit | str = PowerUnit.KW
    rated_pv_capacity_kw: float | None = None
    missing_data_policy: MissingDataPolicy = MissingDataPolicy.REJECT
    filled_interval_count: int = field(default=0, init=False)

    mode = PVSourceMode.CSV_POWER

    def build_pv_available_kw(
        self,
        interval_index: IntervalIndex,
    ) -> pd.Series:
        frame = _prepare_csv_frame(
            self.data,
            self.timestamp_column,
            self.pv_column,
            label="PV CSV",
        )

        frame["value_kw"] = convert_to_kw(frame["value"], self.unit)

        aligned, filled = align_to_index(
            frame[["timestamp", "value_kw"]],
            interval_index,
            label="PV CSV",
            missing_data_policy=self.missing_data_policy,
        )

        self.filled_interval_count = filled

        values = aligned["value_kw"].to_numpy(dtype=float)

        if (values < 0).any():
            raise PVSourceError(
                "PV CSV contains negative values. Available PV is the power "
                "sunlight makes possible and cannot be negative."
            )

        return pd.Series(values, name="pv_available_kw")

    def describe(self) -> str:
        return f"CSV available power, column {self.pv_column!r} ({self.unit})"


@dataclass
class CSVCapacityFactorPV(PVProfileSource):
    """Capacity factors scaled by the rated capacity.

        pv_available_kw = capacity_factor * rated_pv_capacity_kw

    Factors are normally in 0..1. Values above 1 are rejected by default
    because they almost always mean the column actually holds kW.
    """

    data: pd.DataFrame
    rated_pv_capacity_kw: float
    timestamp_column: str = "timestamp"
    capacity_factor_column: str = "capacity_factor"
    maximum_capacity_factor: float = 1.0
    missing_data_policy: MissingDataPolicy = MissingDataPolicy.REJECT
    filled_interval_count: int = field(default=0, init=False)

    mode = PVSourceMode.CSV_CAPACITY_FACTOR

    def __post_init__(self) -> None:
        if self.rated_pv_capacity_kw < 0:
            raise PVSourceError(
                f"Rated PV capacity must not be negative; received "
                f"{self.rated_pv_capacity_kw}."
            )

    def build_pv_available_kw(
        self,
        interval_index: IntervalIndex,
    ) -> pd.Series:
        frame = _prepare_csv_frame(
            self.data,
            self.timestamp_column,
            self.capacity_factor_column,
            label="PV capacity-factor CSV",
        )

        aligned, filled = align_to_index(
            frame[["timestamp", "value"]],
            interval_index,
            label="PV capacity-factor CSV",
            missing_data_policy=self.missing_data_policy,
        )

        self.filled_interval_count = filled

        factors = aligned["value"].to_numpy(dtype=float)

        if (factors < 0).any():
            raise PVSourceError(
                "Capacity factors must not be negative."
            )

        if (factors > self.maximum_capacity_factor).any():
            peak = float(factors.max())
            raise PVSourceError(
                f"Capacity factor peaks at {peak:.3f}, above the maximum "
                f"{self.maximum_capacity_factor:.3f}. A capacity factor is a "
                f"fraction of rated capacity; if this column holds kW, use "
                f"the CSV available-power source instead."
            )

        return pd.Series(
            factors * self.rated_pv_capacity_kw,
            name="pv_available_kw",
        )

    def describe(self) -> str:
        return (
            f"CSV capacity factor x {self.rated_pv_capacity_kw:.2f} kW rated"
        )


@dataclass
class WeatherDerivedPVConfiguration:
    """A generic fixed-tilt array, described without naming a part number.

    **Azimuth convention:** 0 degrees north, 90 east, 180 south, 270 west.
    This matches pvlib's ``surface_azimuth``, so no conversion is applied.

    **Inverter sizing.** Give either ``inverter_ac_capacity_kw`` or
    ``dc_ac_ratio``, not both -- supplying both is rejected rather than
    silently resolved by a precedence rule nobody would remember. With
    neither, ``DEFAULT_DC_AC_RATIO`` applies. Read the resolved value from
    :attr:`resolved_inverter_ac_capacity_kw`.

    ``system_losses_fraction`` is the PVWatts aggregate: soiling, shading,
    mismatch, wiring, connections, light-induced degradation, nameplate
    tolerance and availability. It **excludes** inverter efficiency and the
    cell-temperature derate, which the model applies separately -- see
    :mod:`src.profiles.pv_model` for where each loss lands.
    """

    latitude: float
    longitude: float
    rated_pv_capacity_kw: float
    tilt_degrees: float = 20.0
    azimuth_degrees: float = 180.0
    inverter_ac_capacity_kw: float | None = None
    dc_ac_ratio: float | None = None
    power_temperature_coefficient_per_c: float = (
        DEFAULT_POWER_TEMPERATURE_COEFFICIENT_PER_C
    )
    nominal_inverter_efficiency: float = DEFAULT_NOMINAL_INVERTER_EFFICIENCY
    system_losses_fraction: float = DEFAULT_SYSTEM_LOSSES_FRACTION
    ground_albedo: float = DEFAULT_GROUND_ALBEDO
    model_version: str = PV_MODEL_VERSION

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise PVSourceError(
                f"Latitude must be between -90 and 90; received "
                f"{self.latitude}."
            )

        if not -180 <= self.longitude <= 180:
            raise PVSourceError(
                f"Longitude must be between -180 and 180; received "
                f"{self.longitude}."
            )

        if self.rated_pv_capacity_kw < 0:
            raise PVSourceError("Rated PV capacity must not be negative.")

        if not 0 <= self.tilt_degrees <= 90:
            raise PVSourceError(
                f"Tilt must be between 0 (horizontal) and 90 (vertical); "
                f"received {self.tilt_degrees}."
            )

        if not 0 <= self.azimuth_degrees < 360:
            raise PVSourceError(
                f"Azimuth must be in [0, 360): 0 north, 90 east, 180 south, "
                f"270 west. Received {self.azimuth_degrees}."
            )

        if self.inverter_ac_capacity_kw is not None and self.dc_ac_ratio is not None:
            raise PVSourceError(
                "Give either inverter_ac_capacity_kw or dc_ac_ratio, not "
                "both. They describe the same quantity, and accepting both "
                "would mean silently preferring one. Drop whichever is less "
                "natural for your input."
            )

        if self.inverter_ac_capacity_kw is not None:
            if self.inverter_ac_capacity_kw <= 0:
                raise PVSourceError(
                    "inverter_ac_capacity_kw must be positive."
                )

        if self.dc_ac_ratio is not None and self.dc_ac_ratio <= 0:
            raise PVSourceError("dc_ac_ratio must be positive.")

        if self.power_temperature_coefficient_per_c > 0:
            raise PVSourceError(
                f"power_temperature_coefficient_per_c must not be positive: "
                f"module output falls as the cell warms. Received "
                f"{self.power_temperature_coefficient_per_c}. A typical "
                f"crystalline-silicon value is "
                f"{DEFAULT_POWER_TEMPERATURE_COEFFICIENT_PER_C}/degC."
            )

        if not 0 < self.nominal_inverter_efficiency <= 1:
            raise PVSourceError(
                "nominal_inverter_efficiency must be between 0 and 1."
            )

        if not 0 <= self.system_losses_fraction < 1:
            raise PVSourceError(
                "System losses must be a fraction in [0, 1)."
            )

        if not 0 <= self.ground_albedo <= 1:
            raise PVSourceError(
                f"ground_albedo must be between 0 and 1; received "
                f"{self.ground_albedo}."
            )

    @property
    def resolved_inverter_ac_capacity_kw(self) -> float:
        """Inverter AC rating actually used, however it was specified."""

        if self.inverter_ac_capacity_kw is not None:
            return float(self.inverter_ac_capacity_kw)

        ratio = (
            self.dc_ac_ratio
            if self.dc_ac_ratio is not None
            else DEFAULT_DC_AC_RATIO
        )

        return float(self.rated_pv_capacity_kw) / float(ratio)

    @property
    def resolved_dc_ac_ratio(self) -> float:
        """DC nameplate divided by the resolved inverter AC rating."""

        capacity = self.resolved_inverter_ac_capacity_kw

        if capacity <= 0:
            return float("inf")

        return float(self.rated_pv_capacity_kw) / capacity


@dataclass(frozen=True)
class WeatherDerivedPVResult:
    """One weather-derived PV run, with the reasoning kept alongside it.

    ``pv_available_kw`` is the canonical optimizer-facing series.
    ``diagnostics`` carries every power stage that produced it, timestamp
    aligned to the same interval index, so a later GUI or dispatch
    integration can show *why* the number is what it is rather than only
    what it is.
    """

    pv_available_kw: pd.Series
    diagnostics: pd.DataFrame
    warnings: tuple[str, ...] = ()
    provenance: dict[str, object] = field(default_factory=dict)


@dataclass
class WeatherDerivedPV(PVProfileSource):
    """Available AC PV power modelled from timestamped weather.

    A simplified generic-array estimate: nameplate DC capacity, orientation,
    a temperature coefficient, an inverter size and one aggregate loss
    fraction. No module or inverter part number is required.

    ``weather_data`` is a frame carrying the canonical columns documented in
    :mod:`src.profiles.weather`, with timezone-aware **interval-start**
    timestamps. It is validated and aligned onto the interval index, so it may
    cover a longer horizon or a different timezone than the analysis. The
    supplied frame is read, never modified.

    :meth:`build_pv_available_kw` returns only the series, so existing callers
    are unaffected. :meth:`build_detailed` returns the same series plus the
    power-stage diagnostics; the most recent result is also kept on
    :attr:`last_result` for callers that take the simple path and want the
    detail afterwards.

    The result is ``pv_available_kw`` -- the maximum AC power sunlight makes
    possible before **operational curtailment**. Inverter clipping is already
    subtracted and is reported separately; curtailment is a dispatch decision
    and is never applied here.
    """

    configuration: WeatherDerivedPVConfiguration
    weather_data: pd.DataFrame
    column_map: dict[str, str] | None = None
    weather_source: str = "supplied frame"
    missing_data_policy: MissingDataPolicy = MissingDataPolicy.REJECT
    filled_interval_count: int = field(default=0, init=False)
    last_result: WeatherDerivedPVResult | None = field(
        default=None, init=False, repr=False
    )

    mode = PVSourceMode.WEATHER

    def build_detailed(
        self,
        interval_index: IntervalIndex,
    ) -> WeatherDerivedPVResult:
        """Run the model and return the series, the stages and provenance."""

        prepared = prepare_weather_frame(
            self.weather_data,
            label="Weather data",
            column_map=self.column_map,
        )

        aligned = align_weather(
            prepared,
            interval_index,
            label="Weather data",
            missing_data_policy=self.missing_data_policy,
            source=self.weather_source,
        )

        object.__setattr__(
            self, "filled_interval_count", aligned.filled_interval_count
        )

        configuration = self.configuration
        inverter_ac_capacity_kw = (
            configuration.resolved_inverter_ac_capacity_kw
        )

        diagnostics = simulate_pv_stages(
            interval_index,
            aligned.frame,
            latitude=configuration.latitude,
            longitude=configuration.longitude,
            rated_pv_capacity_kw=configuration.rated_pv_capacity_kw,
            tilt_degrees=configuration.tilt_degrees,
            azimuth_degrees=configuration.azimuth_degrees,
            inverter_ac_capacity_kw=inverter_ac_capacity_kw,
            power_temperature_coefficient_per_c=(
                configuration.power_temperature_coefficient_per_c
            ),
            nominal_inverter_efficiency=(
                configuration.nominal_inverter_efficiency
            ),
            system_losses_fraction=configuration.system_losses_fraction,
            ground_albedo=configuration.ground_albedo,
        )

        available = pd.Series(
            diagnostics[PV_AVAILABLE_KW].to_numpy(), name=PV_AVAILABLE_KW
        )

        result = WeatherDerivedPVResult(
            pv_available_kw=available,
            diagnostics=diagnostics,
            warnings=self._build_warnings(
                diagnostics,
                interval_index,
                aligned.filled_interval_count,
                inverter_ac_capacity_kw,
            ),
            provenance=self._build_provenance(
                interval_index,
                aligned,
                inverter_ac_capacity_kw,
            ),
        )

        object.__setattr__(self, "last_result", result)

        return result

    def build_pv_available_kw(
        self,
        interval_index: IntervalIndex,
    ) -> pd.Series:
        """Return ``pv_available_kw`` only, for the existing source contract."""

        return self.build_detailed(interval_index).pv_available_kw

    def _build_warnings(
        self,
        diagnostics: pd.DataFrame,
        interval_index: IntervalIndex,
        filled_interval_count: int,
        inverter_ac_capacity_kw: float,
    ) -> tuple[str, ...]:
        warnings: list[str] = []

        if filled_interval_count:
            warnings.append(
                f"{filled_interval_count} of "
                f"{interval_index.interval_count} weather intervals were "
                f"filled by the {self.missing_data_policy.value} policy. "
                f"Those intervals are modelled, not observed."
            )

        if self.configuration.rated_pv_capacity_kw == 0:
            warnings.append(
                "Rated PV capacity is zero, so this source produces no power. "
                "That is a valid way to model a site without PV."
            )

        timestep_hours = interval_index.timestep_hours
        clipped_kWh = float(
            diagnostics[PV_INVERTER_CLIPPING_KW].sum() * timestep_hours
        )
        unclipped_kWh = float(
            diagnostics[PV_AC_BEFORE_CLIPPING_KW].sum() * timestep_hours
        )

        if unclipped_kWh > 0:
            clipped_fraction = clipped_kWh / unclipped_kWh

            if clipped_fraction > CLIPPING_WARNING_FRACTION:
                warnings.append(
                    f"Inverter clipping removes {clipped_fraction:.1%} of the "
                    f"AC energy this array could otherwise produce "
                    f"({clipped_kWh:,.0f} kWh over the horizon), at a DC/AC "
                    f"ratio of "
                    f"{self.configuration.resolved_dc_ac_ratio:.2f}. That may "
                    f"be a deliberate design choice; it is reported so it is "
                    f"not an accident."
                )

        return tuple(warnings)

    def _build_provenance(
        self,
        interval_index: IntervalIndex,
        aligned,
        inverter_ac_capacity_kw: float,
    ) -> dict[str, object]:
        configuration = self.configuration

        return {
            "model_version": configuration.model_version,
            "transposition_model": TRANSPOSITION_MODEL,
            "cell_temperature_model": "sapm/open_rack_glass_glass",
            "inverter_model": "pvwatts",
            "weather_source": aligned.source,
            "filled_interval_count": aligned.filled_interval_count,
            "missing_data_policy": self.missing_data_policy.value,
            "timezone": interval_index.timezone,
            "timestep_minutes": interval_index.timestep_minutes,
            "interval_count": interval_index.interval_count,
            "latitude": configuration.latitude,
            "longitude": configuration.longitude,
            "rated_pv_capacity_kw": configuration.rated_pv_capacity_kw,
            "tilt_degrees": configuration.tilt_degrees,
            "azimuth_degrees": configuration.azimuth_degrees,
            "inverter_ac_capacity_kw": inverter_ac_capacity_kw,
            "dc_ac_ratio": configuration.resolved_dc_ac_ratio,
            "system_losses_fraction": configuration.system_losses_fraction,
            "nominal_inverter_efficiency": (
                configuration.nominal_inverter_efficiency
            ),
            "power_temperature_coefficient_per_c": (
                configuration.power_temperature_coefficient_per_c
            ),
            "ground_albedo": configuration.ground_albedo,
        }

    def describe(self) -> str:
        configuration = self.configuration
        return (
            f"Weather-derived PV at ({configuration.latitude:.4f}, "
            f"{configuration.longitude:.4f}), "
            f"{configuration.rated_pv_capacity_kw:.2f} kW DC, tilt "
            f"{configuration.tilt_degrees:.0f}deg, azimuth "
            f"{configuration.azimuth_degrees:.0f}deg, inverter "
            f"{configuration.resolved_inverter_ac_capacity_kw:.2f} kW AC "
            f"(DC/AC {configuration.resolved_dc_ac_ratio:.2f}), model "
            f"{configuration.model_version}"
        )


@dataclass(frozen=True)
class EquipmentSpecificPVResult:
    """One equipment-specific PV run, with the reasoning kept alongside it.

    ``pv_available_kw`` is the canonical optimizer-facing series, identical in
    meaning to the Phase 1 :class:`WeatherDerivedPVResult` field of the same
    name: maximum nonnegative AC real power after inverter conversion and
    equipment clipping, before operational curtailment.

    ``diagnostics`` carries the plant power stages. ``subarray_diagnostics``
    is keyed ``"<inverter unit>/<subarray>"`` and carries the irradiance,
    temperature and I-V detail behind each subarray;
    ``inverter_diagnostics`` is keyed by inverter unit name and carries the
    AC stages for all instances of that unit, which is where clipping is
    actually attributable.
    """

    pv_available_kw: pd.Series
    diagnostics: pd.DataFrame
    subarray_diagnostics: dict[str, pd.DataFrame] = field(default_factory=dict)
    inverter_diagnostics: dict[str, pd.DataFrame] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    provenance: dict[str, object] = field(default_factory=dict)


@dataclass
class EquipmentSpecificPV(PVProfileSource):
    """Available AC PV power modelled from named equipment and real strings.

    Phase 2 of the weather-derived model. Where :class:`WeatherDerivedPV`
    takes a nameplate DC rating and one aggregate loss fraction, this takes
    CEC module and inverter part numbers, how the modules are wired into
    strings, which subarray feeds which MPPT input, and how many inverters
    there are. See :mod:`src.profiles.pv_equipment` for what that buys and
    what it still does not model.

    Both sources return the same quantity and honour the same contract, so a
    caller can swap one for the other without changing what
    ``pv_available_kw`` means. Phase 1 stays available and numerically
    unchanged; it remains the right choice when no part numbers are known.

    ``weather_data`` is a frame carrying the canonical columns documented in
    :mod:`src.profiles.weather`, with timezone-aware **interval-start**
    timestamps. It is validated and aligned onto the interval index, so it may
    cover a longer horizon or a different timezone than the analysis. The
    supplied frame is read, never modified.

    :meth:`build_pv_available_kw` returns only the series, so any caller
    written against :class:`PVProfileSource` works unchanged.
    :meth:`build_detailed` returns the same series plus every diagnostic; the
    most recent result is also kept on :attr:`last_result`.
    """

    configuration: EquipmentSpecificPVConfiguration
    weather_data: pd.DataFrame
    column_map: dict[str, str] | None = None
    weather_source: str = "supplied frame"
    missing_data_policy: MissingDataPolicy = MissingDataPolicy.REJECT
    filled_interval_count: int = field(default=0, init=False)
    last_result: EquipmentSpecificPVResult | None = field(
        default=None, init=False, repr=False
    )

    mode = PVSourceMode.EQUIPMENT

    def build_detailed(
        self,
        interval_index: IntervalIndex,
    ) -> EquipmentSpecificPVResult:
        """Run the model and return the series, the stages and provenance."""

        prepared = prepare_weather_frame(
            self.weather_data,
            label="Weather data",
            column_map=self.column_map,
        )

        aligned = align_weather(
            prepared,
            interval_index,
            label="Weather data",
            missing_data_policy=self.missing_data_policy,
            source=self.weather_source,
        )

        self.filled_interval_count = aligned.filled_interval_count

        stages = simulate_equipment_pv_stages(
            interval_index,
            aligned.frame,
            self.configuration,
        )

        available = pd.Series(
            stages.diagnostics[PV_AVAILABLE_KW].to_numpy(),
            name=PV_AVAILABLE_KW,
        )

        result = EquipmentSpecificPVResult(
            pv_available_kw=available,
            diagnostics=stages.diagnostics,
            subarray_diagnostics=stages.subarray_diagnostics,
            inverter_diagnostics=stages.inverter_diagnostics,
            warnings=self._build_warnings(stages, interval_index, aligned),
            provenance=self._build_provenance(interval_index, aligned),
        )

        self.last_result = result

        return result

    def build_pv_available_kw(
        self,
        interval_index: IntervalIndex,
    ) -> pd.Series:
        """Return ``pv_available_kw`` only, for the existing source contract."""

        return self.build_detailed(interval_index).pv_available_kw

    def _build_warnings(
        self,
        stages,
        interval_index: IntervalIndex,
        aligned,
    ) -> tuple[str, ...]:
        warnings: list[str] = list(design_warnings(self.configuration))

        if aligned.filled_interval_count:
            warnings.append(
                f"{aligned.filled_interval_count} of "
                f"{interval_index.interval_count} weather intervals were "
                f"filled by the {self.missing_data_policy.value} policy. "
                f"Those intervals are modelled, not observed."
            )

        diagnostics = stages.diagnostics
        timestep_hours = interval_index.timestep_hours

        clipped_kWh = float(
            diagnostics[PV_INVERTER_CLIPPING_KW].sum() * timestep_hours
        )
        unclipped_kWh = float(
            diagnostics[PV_AC_BEFORE_CLIPPING_KW].sum() * timestep_hours
        )

        if unclipped_kWh > 0:
            clipped_fraction = clipped_kWh / unclipped_kWh

            if clipped_fraction > CLIPPING_WARNING_FRACTION:
                warnings.append(
                    f"Inverter clipping removes {clipped_fraction:.1%} of the "
                    f"AC energy this plant could otherwise produce "
                    f"({clipped_kWh:,.0f} kWh over the horizon), at a DC/AC "
                    f"ratio of {self.configuration.dc_ac_ratio:.2f}. That may "
                    f"be a deliberate design choice; it is reported so it is "
                    f"not an accident."
                )

        # Losing power to the MPPT window is a wiring decision, not weather:
        # the strings are the wrong length for the inverter at the cell
        # temperatures this site actually reaches. The test is energy, not
        # interval count -- every array leaves the window at dawn and dusk,
        # when it is producing almost nothing and it does not matter.
        for key, frame in stages.subarray_diagnostics.items():
            available_kWh = float(
                frame[PV_DC_AFTER_SYSTEM_LOSSES_KW].sum() * timestep_hours
            )

            if available_kWh <= 0:
                continue

            lost_kWh = available_kWh - float(
                frame[PV_DC_AT_INVERTER_INPUT_KW].sum() * timestep_hours
            )
            lost_fraction = lost_kWh / available_kWh

            if lost_fraction > MPPT_WINDOW_WARNING_FRACTION:
                limited_intervals = int(
                    frame[MPPT_WINDOW_LIMITED].to_numpy().sum()
                )
                warnings.append(
                    f"Subarray {key} loses {lost_fraction:.1%} of its DC "
                    f"energy ({lost_kWh:,.0f} kWh) operating outside its "
                    f"inverter's MPPT voltage window, in {limited_intervals} "
                    f"intervals. The string voltage leaves the window because "
                    f"of how many modules are in series; changing that count "
                    f"moves the array back into it."
                )

        return tuple(warnings)

    def _build_provenance(
        self,
        interval_index: IntervalIndex,
        aligned,
    ) -> dict[str, object]:
        configuration = self.configuration

        return {
            "model_version": configuration.model_version,
            "control_mode": configuration.control_mode,
            "transposition_model": TRANSPOSITION_MODEL,
            "angle_of_incidence_model": ANGLE_OF_INCIDENCE_MODEL,
            "module_model": "cec_single_diode",
            "cell_temperature_model": "sapm",
            "inverter_model": "sandia",
            "spectral_model": "not modelled",
            "weather_source": aligned.source,
            "filled_interval_count": aligned.filled_interval_count,
            "missing_data_policy": self.missing_data_policy.value,
            "timezone": interval_index.timezone,
            "timestep_minutes": interval_index.timestep_minutes,
            "interval_count": interval_index.interval_count,
            "latitude": configuration.latitude,
            "longitude": configuration.longitude,
            "rated_dc_capacity_kw": configuration.rated_dc_capacity_kw,
            "inverter_ac_capacity_kw": (
                configuration.inverter_ac_capacity_kw
            ),
            "dc_ac_ratio": configuration.dc_ac_ratio,
            "is_homogeneous": configuration.is_homogeneous,
            "inverter_units": tuple(
                {
                    "name": unit.name,
                    "inverter": unit.inverter.name,
                    "count": unit.count,
                    "mppt_inputs_used": len(unit.subarrays),
                    "mppt_input_count": unit.inverter.mppt_input_count,
                    "subarrays": tuple(
                        {
                            "name": subarray.name,
                            "module": subarray.module.name,
                            "modules_per_string": subarray.modules_per_string,
                            "strings": subarray.strings,
                            "tilt_degrees": subarray.tilt_degrees,
                            "azimuth_degrees": subarray.azimuth_degrees,
                            "mount_type": subarray.mount_type,
                            "ground_albedo": subarray.ground_albedo,
                            "dc_losses_fraction": (
                                subarray.dc_losses_fraction
                            ),
                            "rated_dc_capacity_kw": (
                                subarray.rated_dc_capacity_kw
                            ),
                        }
                        for subarray in unit.subarrays
                    ),
                }
                for unit in configuration.inverter_units
            ),
        }

    def describe(self) -> str:
        configuration = self.configuration

        modules = sorted(
            {
                subarray.module.name
                for subarray in configuration.subarrays
            }
        )
        inverters = sorted(
            {unit.inverter.name for unit in configuration.inverter_units}
        )
        inverter_instances = sum(
            unit.count for unit in configuration.inverter_units
        )
        module_count = sum(
            subarray.module_count * unit.count
            for unit in configuration.inverter_units
            for subarray in unit.subarrays
        )

        return (
            f"Equipment-specific PV at ({configuration.latitude:.4f}, "
            f"{configuration.longitude:.4f}), "
            f"{configuration.rated_dc_capacity_kw:.2f} kW DC from "
            f"{module_count} x {', '.join(modules)}, "
            f"{configuration.inverter_ac_capacity_kw:.2f} kW AC from "
            f"{inverter_instances} x {', '.join(inverters)} "
            f"(DC/AC {configuration.dc_ac_ratio:.2f}), model "
            f"{configuration.model_version}"
        )


class MeasuredInverterPV(PVProfileSource):
    """Extension point for live inverter telemetry.

    **Not implemented.** Measured inverter output is delivered power, which is
    already post-curtailment; deriving *available* PV from it needs either a
    curtailment signal from the inverter or a clear-sky reference model. That
    modelling decision is unresolved, so this raises instead of guessing.
    """

    mode = PVSourceMode.MEASURED_INVERTER

    SUPPORTED_PROTOCOLS = ("sunspec", "modbus", "mqtt")

    def __init__(self, protocol: str = "sunspec") -> None:
        self.protocol = protocol

    def build_pv_available_kw(
        self,
        interval_index: IntervalIndex,
    ) -> pd.Series:
        raise NotImplementedError(
            f"Measured inverter PV via {self.protocol!r} is not implemented. "
            f"Inverter telemetry reports delivered power; recovering "
            f"available power additionally requires a curtailment signal or a "
            f"clear-sky reference, which is not yet modelled."
        )

    def describe(self) -> str:
        return f"Measured inverter {self.protocol} (not implemented)"
