"""Timestamped weather input for the weather-derived PV model.

**Timestamp convention.** Every timestamp is the *start* of its interval, the
same convention as :mod:`src.timeseries.schema`. A provider that publishes
interval-*ending* timestamps must be converted by its adapter before reaching
this module; nothing here guesses the convention, because guessing wrong
shifts a PV profile by one interval and nobody notices.

**Units.** Irradiance in W/m^2, air temperature in degrees Celsius, wind speed
in m/s at the measurement height the temperature model expects (10 m for the
SAPM open-rack coefficients used by :mod:`src.profiles.pv_model`).

Validation here is deliberately about *unit mistakes*, not about rejecting
unusual weather. Cloud-edge enhancement really does push global horizontal
irradiance above the clear-sky limit, so the bounds are wide enough to admit
genuine extremes and narrow enough to catch a frame supplied in kW/m^2,
kelvin or joules.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..timeseries.interval_table import IntervalIndex, align_to_index
from ..timeseries.schema import TIMESTAMP, MissingDataPolicy

# Canonical weather column names.
GHI_W_PER_M2 = "ghi_w_per_m2"
DNI_W_PER_M2 = "dni_w_per_m2"
DHI_W_PER_M2 = "dhi_w_per_m2"
TEMPERATURE_C = "temperature_c"
WIND_SPEED_M_PER_S = "wind_speed_m_per_s"

IRRADIANCE_COLUMNS = (GHI_W_PER_M2, DNI_W_PER_M2, DHI_W_PER_M2)

REQUIRED_WEATHER_COLUMNS = (
    TIMESTAMP,
    GHI_W_PER_M2,
    DNI_W_PER_M2,
    DHI_W_PER_M2,
    TEMPERATURE_C,
    WIND_SPEED_M_PER_S,
)

# Plausibility bounds. Chosen to catch a wrong unit, not to police weather.
#
#   irradiance : 1361 W/m^2 is the solar constant; surface values above it
#                occur briefly under cloud enhancement, so the ceiling sits
#                above it rather than at it. A frame in kW/m^2 reads ~1.0 and
#                is caught by MIN_PLAUSIBLE_DAYTIME_GHI instead.
#   temperature: the recorded terrestrial range with margin. Catches kelvin
#                (~290) and Fahrenheit in hot weather (~95).
#   wind       : above the strongest recorded surface gust.
MAX_PLAUSIBLE_IRRADIANCE_W_PER_M2 = 1600.0
MIN_PLAUSIBLE_TEMPERATURE_C = -95.0
MAX_PLAUSIBLE_TEMPERATURE_C = 65.0
MAX_PLAUSIBLE_WIND_SPEED_M_PER_S = 120.0

# If the brightest interval in a frame is below this, the values are almost
# certainly kW/m^2 rather than W/m^2.
MIN_PLAUSIBLE_PEAK_GHI_W_PER_M2 = 20.0


class WeatherError(ValueError):
    """Raised when a weather frame cannot be trusted as model input."""


@dataclass
class WeatherData:
    """A validated, timezone-aware weather frame.

    ``filled_interval_count`` records how many intervals the missing-data
    policy had to fill, so a synthesised interval is never silently presented
    as observed.
    """

    frame: pd.DataFrame
    source: str = "unspecified"
    filled_interval_count: int = field(default=0)

    def describe(self) -> str:
        return f"{self.source} ({len(self.frame)} intervals)"


def _require_columns(data: pd.DataFrame, label: str) -> None:
    missing = set(REQUIRED_WEATHER_COLUMNS) - set(data.columns)

    if missing:
        raise WeatherError(
            f"{label} is missing required columns {sorted(missing)}. "
            f"Expected {list(REQUIRED_WEATHER_COLUMNS)}; received "
            f"{sorted(data.columns)}."
        )


def _parse_timestamps(values: pd.Series) -> pd.Series:
    """Parse a timestamp column, tolerating a mix of UTC offsets.

    A local-time file that spans a daylight-saving fall-back carries two
    offsets in one column -- the repeated wall-clock hour written once at
    -07:00 and once at -08:00. That file is correct, and the offsets are
    exactly what disambiguate it. pandas nonetheless returns object dtype for
    it today, with a warning that it will raise outright in a future version.

    So: parse normally, and fall back to parsing into a single zone when the
    column turns out to be mixed. The instants are unchanged either way, and
    alignment converts to the site zone afterwards as it does for any input.
    Doing nothing here would reject a correct file with an error about the
    ``.dt`` accessor, which says nothing about what is actually wrong.
    """

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)

        try:
            timestamps = pd.to_datetime(values, errors="coerce")
        except ValueError:
            timestamps = None

    if timestamps is None or timestamps.dtype == object:
        return pd.to_datetime(values, errors="coerce", utc=True)

    return timestamps


def _coerce_timestamps(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    timestamps = _parse_timestamps(frame[TIMESTAMP])

    if timestamps.isna().any():
        raise WeatherError(
            f"{label} contains unparseable timestamps."
        )

    if timestamps.dt.tz is None:
        raise WeatherError(
            f"{label} timestamps are timezone-naive. Localize them to the "
            f"site's timezone first, so daylight-saving transitions are "
            f"unambiguous and solar position is computed at the right instant."
        )

    frame = frame.copy()
    frame[TIMESTAMP] = timestamps
    return frame


def _coerce_numeric(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    frame = frame.copy()

    for column in REQUIRED_WEATHER_COLUMNS:
        if column == TIMESTAMP:
            continue

        try:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
        except (TypeError, ValueError) as error:
            raise WeatherError(
                f"{label} column {column!r} contains nonnumeric values."
            ) from error

    return frame


def _validate_ranges(frame: pd.DataFrame, label: str) -> None:
    """Catch obvious unit mistakes without rejecting genuine extremes."""

    for column in IRRADIANCE_COLUMNS:
        values = frame[column]

        if (values < 0).any():
            first = frame.loc[values < 0, TIMESTAMP].iloc[0]
            raise WeatherError(
                f"{label} column {column!r} has negative irradiance, first at "
                f"{first}. Irradiance cannot be negative."
            )

        if (values > MAX_PLAUSIBLE_IRRADIANCE_W_PER_M2).any():
            worst = float(values.max())
            raise WeatherError(
                f"{label} column {column!r} peaks at {worst:,.0f} W/m^2, above "
                f"the {MAX_PLAUSIBLE_IRRADIANCE_W_PER_M2:,.0f} W/m^2 "
                f"plausibility ceiling. This usually means the column is an "
                f"energy accumulation (J/m^2 or Wh/m^2) rather than an "
                f"instantaneous irradiance."
            )

    peak_ghi = float(frame[GHI_W_PER_M2].max())

    if 0 < peak_ghi < MIN_PLAUSIBLE_PEAK_GHI_W_PER_M2:
        raise WeatherError(
            f"{label} peaks at only {peak_ghi:.3f} W/m^2 of global horizontal "
            f"irradiance. This usually means the column is in kW/m^2; "
            f"multiply by 1000. Supply an all-zero column deliberately if the "
            f"horizon really is dark."
        )

    temperature = frame[TEMPERATURE_C]

    if (
        (temperature < MIN_PLAUSIBLE_TEMPERATURE_C).any()
        or (temperature > MAX_PLAUSIBLE_TEMPERATURE_C).any()
    ):
        raise WeatherError(
            f"{label} air temperature spans "
            f"{float(temperature.min()):.1f} to {float(temperature.max()):.1f}, "
            f"outside the plausible range "
            f"[{MIN_PLAUSIBLE_TEMPERATURE_C:.0f}, "
            f"{MAX_PLAUSIBLE_TEMPERATURE_C:.0f}] degrees Celsius. Check for "
            f"kelvin or Fahrenheit."
        )

    wind = frame[WIND_SPEED_M_PER_S]

    if (wind < 0).any():
        raise WeatherError(
            f"{label} contains negative wind speed."
        )

    if (wind > MAX_PLAUSIBLE_WIND_SPEED_M_PER_S).any():
        raise WeatherError(
            f"{label} wind speed peaks at {float(wind.max()):.1f} m/s, above "
            f"the {MAX_PLAUSIBLE_WIND_SPEED_M_PER_S:.0f} m/s plausibility "
            f"ceiling. Check the units."
        )


def prepare_weather_frame(
    data: pd.DataFrame,
    *,
    label: str = "Weather data",
    column_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Validate a raw weather frame into the canonical column set.

    ``column_map`` renames provider columns onto the canonical names before
    validation, e.g. ``{"temp_air": "temperature_c"}``.
    """

    if data is None or len(data) == 0:
        raise WeatherError(f"{label} is empty.")

    frame = data.rename(columns=dict(column_map or {}))

    _require_columns(frame, label)

    frame = frame[list(REQUIRED_WEATHER_COLUMNS)]
    frame = _coerce_timestamps(frame, label)
    frame = _coerce_numeric(frame, label)

    if frame[TIMESTAMP].duplicated().any():
        duplicate = frame.loc[frame[TIMESTAMP].duplicated(), TIMESTAMP].iloc[0]
        raise WeatherError(
            f"{label} contains duplicate timestamps, first at {duplicate}. "
            f"A repeated timestamp is ambiguous; note that a daylight-saving "
            f"fall-back repeats local wall-clock times, which is why "
            f"timezone-aware timestamps are required."
        )

    _validate_ranges(frame, label)

    return frame.sort_values(TIMESTAMP).reset_index(drop=True)


def load_weather_csv(
    path: str | Path,
    *,
    column_map: dict[str, str] | None = None,
    label: str | None = None,
) -> pd.DataFrame:
    """Read and validate a weather CSV. Offline; no provider is contacted."""

    csv_path = Path(path)

    if not csv_path.is_file():
        raise WeatherError(f"Weather CSV was not found: {csv_path}")

    return prepare_weather_frame(
        pd.read_csv(csv_path),
        label=label or f"Weather CSV {csv_path.name}",
        column_map=column_map,
    )


def align_weather(
    frame: pd.DataFrame,
    interval_index: IntervalIndex,
    *,
    label: str = "Weather data",
    missing_data_policy: MissingDataPolicy = MissingDataPolicy.REJECT,
    source: str = "unspecified",
) -> WeatherData:
    """Clip and reindex validated weather onto the interval grid.

    Alignment is delegated to :func:`align_to_index`, so timezone conversion,
    horizon clipping, duplicate detection and the missing-data policy behave
    exactly as they do for every other profile input. Interval counts come
    from the index, never from a day-length assumption, which is what keeps
    daylight-saving days correct.
    """

    aligned, filled = align_to_index(
        frame,
        interval_index,
        label=label,
        missing_data_policy=missing_data_policy,
    )

    return WeatherData(
        frame=aligned.reset_index(drop=True),
        source=source,
        filled_interval_count=filled,
    )
