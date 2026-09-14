"""NSRDB weather adapter: satellite-derived irradiance for a real location.

Fetches NSRDB PSM4 data through pvlib's readers and converts it into the
canonical weather frame that :mod:`src.profiles.weather` defines, ready to
hand to either PV phase as ``weather_data``.

**Nothing here is required.** The supplied-frame and CSV weather workflows are
unchanged and stay fully offline; this is an additional way to obtain a frame,
not a new dependency of the model. A fetched year is normally saved once with
:func:`save_weather_csv` and read back with
:func:`src.profiles.weather.load_weather_csv` forever after, so a repeated
study costs no API quota.

**Credentials.** ``NSRDB_API_KEY`` and ``NSRDB_API_EMAIL`` in the environment
or ``.env``. The NSRDB API requires both -- the address is where it sends
notices about a request. A key is free from the developer portal pvlib's
documentation links. Nothing in this module reads a key unless a fetch is
actually requested, and no test ever performs one.

Two conversions happen here, and both are the kind of thing that silently
shifts a PV profile by an interval if assumed rather than checked.

**Timezone.** pvlib localises PSM4 data to a *fixed offset* built from the
file's own metadata (``Etc/GMT+8`` for the US Pacific coast), which is local
**standard** time and never observes daylight saving. Converting that to a
named zone with ``tz_convert`` keeps the instants and lets the wall clock
shift correctly in summer. Re-localising it instead -- treating 13:00 standard
as 13:00 local -- would move every summer interval by an hour. This module
converts, never re-localises, and refuses a frame that is not already
timezone aware.

**Interval labels.** NSRDB labels an hourly record at the middle of its hour
(minute 30), while every timestamp in this repository is the **start** of its
interval. The offset is detected from the data rather than assumed: labels
that sit on the step grid are interval starts, labels that sit exactly half a
step off it are midpoints and are shifted back. Anything else is refused,
because a convention that is neither is one nobody has checked.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .weather import (
    DHI_W_PER_M2,
    DNI_W_PER_M2,
    GHI_W_PER_M2,
    REQUIRED_WEATHER_COLUMNS,
    TEMPERATURE_C,
    WIND_SPEED_M_PER_S,
    WeatherError,
    prepare_weather_frame,
)
from ..timeseries.schema import TIMESTAMP

#: Environment variables holding the NSRDB credentials. Never logged, never
#: written into a cached file, never included in provenance.
NSRDB_API_KEY_ENV_VAR = "NSRDB_API_KEY"
NSRDB_EMAIL_ENV_VAR = "NSRDB_API_EMAIL"

#: pvlib's names for the fields this repository needs, after
#: ``map_variables=True``.
PVLIB_TO_CANONICAL = {
    "ghi": GHI_W_PER_M2,
    "dni": DNI_W_PER_M2,
    "dhi": DHI_W_PER_M2,
    "temp_air": TEMPERATURE_C,
    "wind_speed": WIND_SPEED_M_PER_S,
}

#: What to ask NSRDB for. Requesting only these keeps the response small and
#: makes a missing field an explicit failure rather than a silent NaN column.
NSRDB_PARAMETERS = ("air_temperature", "dhi", "dni", "ghi", "wind_speed")

#: NSRDB PSM4 products. Each is a different spatial domain or temporal
#: treatment, and each is a different pvlib function.
NSRDB_DATASETS = ("conus", "full_disc", "aggregated", "tmy")

#: Time steps the NSRDB API accepts, in minutes. Availability varies by
#: product and year; the API rejects a combination it does not have.
NSRDB_TIME_STEPS = (5, 15, 30, 60)

#: How a record's timestamp relates to the interval it describes.
INTERVAL_START = "interval_start"
INTERVAL_MIDPOINT = "interval_midpoint"


class NSRDBError(WeatherError):
    """Raised when NSRDB data cannot be turned into trustworthy weather.

    A :class:`~src.profiles.weather.WeatherError`, because by the time it is
    raised the question is always "can this be used as model input".
    """


@dataclass(frozen=True)
class NSRDBRequest:
    """One NSRDB retrieval, described without any credential in it.

    ``timezone`` is the named zone the site is operated in -- the same one the
    interval index uses. NSRDB does not know about it: the response arrives at
    a fixed offset and is converted, which is the whole point of naming it
    here rather than inferring it from the coordinates.
    """

    latitude: float
    longitude: float
    year: int | str
    timezone: str
    time_step_minutes: int = 60
    dataset: str = "conus"
    leap_day: bool = True

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise NSRDBError(
                f"Latitude must be between -90 and 90; received "
                f"{self.latitude}."
            )

        if not -180 <= self.longitude <= 180:
            raise NSRDBError(
                f"Longitude must be between -180 and 180; received "
                f"{self.longitude}."
            )

        if self.dataset not in NSRDB_DATASETS:
            raise NSRDBError(
                f"Unknown NSRDB dataset {self.dataset!r}. Available: "
                f"{list(NSRDB_DATASETS)}."
            )

        if self.time_step_minutes not in NSRDB_TIME_STEPS:
            raise NSRDBError(
                f"NSRDB does not offer a {self.time_step_minutes}-minute time "
                f"step. Available: {list(NSRDB_TIME_STEPS)}."
            )

        if self.dataset == "tmy":
            if not str(self.year).startswith("tmy"):
                raise NSRDBError(
                    f"The tmy dataset is addressed by a typical-year name "
                    f"such as 'tmy' or 'tmy-2023', not by the calendar year "
                    f"{self.year!r}. A typical meteorological year is "
                    f"assembled from many years and is not any one of them."
                )
        elif not isinstance(self.year, int):
            raise NSRDBError(
                f"Dataset {self.dataset!r} is addressed by a calendar year as "
                f"an integer; received {self.year!r}. Use dataset='tmy' for a "
                f"typical meteorological year."
            )

        if not self.timezone:
            raise NSRDBError(
                "A named site timezone is required. NSRDB returns data at a "
                "fixed UTC offset that never observes daylight saving, so the "
                "zone the site is operated in has to be stated to convert it."
            )

    @property
    def is_typical_year(self) -> bool:
        return self.dataset == "tmy"


@dataclass(frozen=True)
class NSRDBWeather:
    """A canonical weather frame with the NSRDB record it came from."""

    frame: pd.DataFrame
    metadata: dict[str, object] = field(default_factory=dict)
    provenance: dict[str, object] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def describe(self) -> str:
        source = self.provenance.get("dataset", "nsrdb")
        year = self.provenance.get("year", "unknown year")
        return f"NSRDB {source} {year} ({len(self.frame)} intervals)"


def _credentials(
    api_key: str | None,
    email: str | None,
) -> tuple[str, str]:
    """Resolve credentials, preferring explicit arguments over the environment.

    Read only when a fetch is actually about to happen, so importing this
    module or building a request needs no credential at all.
    """

    resolved_key = api_key or os.getenv(NSRDB_API_KEY_ENV_VAR)
    resolved_email = email or os.getenv(NSRDB_EMAIL_ENV_VAR)

    missing = []

    if not resolved_key:
        missing.append(NSRDB_API_KEY_ENV_VAR)

    if not resolved_email:
        missing.append(NSRDB_EMAIL_ENV_VAR)

    if missing:
        raise NSRDBError(
            f"NSRDB retrieval needs {' and '.join(missing)}. Set them in your "
            f"environment or .env file. The API requires both a developer key "
            f"and the address it was registered to; it uses the address to "
            f"send notices about a request. Supply a CSV through "
            f"load_weather_csv instead to work entirely offline."
        )

    return resolved_key, resolved_email


def default_fetcher(request: NSRDBRequest, api_key: str, email: str):
    """Call pvlib's NSRDB reader for the requested product.

    The only function in this module that performs network access, and it is
    injectable everywhere it is used, which is how the tests stay offline.
    """

    from pvlib import iotools

    readers = {
        "conus": iotools.get_nsrdb_psm4_conus,
        "full_disc": iotools.get_nsrdb_psm4_full_disc,
        "aggregated": iotools.get_nsrdb_psm4_aggregated,
        "tmy": iotools.get_nsrdb_psm4_tmy,
    }

    return readers[request.dataset](
        latitude=request.latitude,
        longitude=request.longitude,
        api_key=api_key,
        email=email,
        year=request.year,
        time_step=request.time_step_minutes,
        parameters=list(NSRDB_PARAMETERS),
        leap_day=request.leap_day,
        map_variables=True,
    )


def detect_interval_label_convention(
    index: pd.DatetimeIndex,
    time_step_minutes: int,
) -> str:
    """Decide whether timestamps label interval starts or interval midpoints.

    NSRDB labels an hourly record at minute 30 -- the middle of the hour it
    describes -- while every timestamp in this repository is an interval
    start. Rather than hard-coding "subtract 30 minutes for hourly data",
    which is wrong for the sub-hourly products, the offset is measured:

    * every label on the step grid (minute 0 for hourly, 0/30 for half-hourly)
      is an interval start;
    * every label exactly half a step off the grid is a midpoint;
    * anything else is refused.

    Refusing the third case is deliberate. A frame whose labels are neither is
    one whose convention nobody has established, and guessing shifts the
    profile against the sun by a fraction of an interval that no downstream
    check would catch.
    """

    if len(index) == 0:
        raise NSRDBError("NSRDB returned no intervals.")

    step = pd.Timedelta(minutes=time_step_minutes)

    # Offsets of each label from midnight, in whole minutes.
    minutes_from_midnight = (
        index.hour * 60 + index.minute + index.second / 60.0
    )
    offsets = pd.Series(minutes_from_midnight % time_step_minutes).unique()

    if len(offsets) != 1:
        raise NSRDBError(
            f"NSRDB timestamps are not on a regular "
            f"{time_step_minutes}-minute grid: labels sit at "
            f"{sorted(float(offset) for offset in offsets)} minutes past each "
            f"step. A mixed convention cannot be converted to interval starts."
        )

    offset_minutes = float(offsets[0])

    if offset_minutes == 0.0:
        return INTERVAL_START

    if offset_minutes * 2 == time_step_minutes:
        return INTERVAL_MIDPOINT

    raise NSRDBError(
        f"NSRDB timestamps sit {offset_minutes:g} minutes into each "
        f"{time_step_minutes}-minute interval, which is neither the start nor "
        f"the midpoint. This repository's timestamps are interval starts, and "
        f"a convention that is neither has to be established rather than "
        f"assumed: assuming wrong shifts the whole profile against the sun. "
        f"Time step in the response: {step}."
    )


def to_canonical_weather_frame(
    data: pd.DataFrame,
    request: NSRDBRequest,
) -> tuple[pd.DataFrame, str]:
    """Convert a pvlib PSM4 frame into the canonical weather columns.

    Returns the frame and the label convention that was detected, so a caller
    can record which conversion was applied rather than trusting that one was.

    ``data`` is read, never modified.
    """

    if not isinstance(data.index, pd.DatetimeIndex):
        raise NSRDBError(
            f"NSRDB response is not time indexed; its index is a "
            f"{type(data.index).__name__}."
        )

    if data.index.tz is None:
        raise NSRDBError(
            "NSRDB response timestamps are timezone naive. pvlib localises "
            "PSM4 data to the fixed offset in the file's own metadata, so a "
            "naive index means the response was not read by pvlib's reader. "
            "Localising it here would be a guess about which offset the file "
            "was written in."
        )

    missing = sorted(set(PVLIB_TO_CANONICAL) - set(data.columns))

    if missing:
        raise NSRDBError(
            f"NSRDB response is missing {missing}. Expected pvlib's mapped "
            f"names {sorted(PVLIB_TO_CANONICAL)}; received "
            f"{sorted(data.columns)}. Request these fields with "
            f"map_variables=True."
        )

    convention = detect_interval_label_convention(
        data.index, request.time_step_minutes
    )

    timestamps = data.index

    if convention == INTERVAL_MIDPOINT:
        timestamps = timestamps - pd.Timedelta(
            minutes=request.time_step_minutes
        ) / 2

    # Convert, never re-localise: the instants are already correct at a fixed
    # offset, and the named zone is what makes the wall clock right in summer.
    timestamps = timestamps.tz_convert(request.timezone)

    frame = pd.DataFrame(
        {
            TIMESTAMP: timestamps,
            **{
                canonical: data[pvlib_name].to_numpy(dtype=float)
                for pvlib_name, canonical in PVLIB_TO_CANONICAL.items()
            },
        }
    )

    return frame[list(REQUIRED_WEATHER_COLUMNS)], convention


def _build_warnings(request: NSRDBRequest) -> tuple[str, ...]:
    warnings: list[str] = []

    if request.is_typical_year:
        warnings.append(
            "This is a typical meteorological year, assembled from months of "
            "different real years. It represents a long-run average and no "
            "actual year, so it is the right input for expected yield and the "
            "wrong one for reconciling against a real bill or a real day."
        )

    if request.time_step_minutes > 15:
        warnings.append(
            f"NSRDB supplied {request.time_step_minutes}-minute data. Putting "
            f"it on a finer interval grid needs a missing-data policy, and "
            f"interpolating irradiance across an hour smooths away the "
            f"cloud transients that drive short-interval peaks and inverter "
            f"clipping. Request a 5- or 15-minute time step where the product "
            f"offers one."
        )

    return tuple(warnings)


def fetch_nsrdb_weather(
    request: NSRDBRequest,
    *,
    api_key: str | None = None,
    email: str | None = None,
    fetcher=None,
) -> NSRDBWeather:
    """Retrieve NSRDB weather and return it in the canonical columns.

    **Performs network access** through ``fetcher``, which defaults to
    :func:`default_fetcher`. Pass a callable taking ``(request, api_key,
    email)`` and returning pvlib's ``(data, metadata)`` pair to substitute a
    saved response -- which is how the tests exercise every line of this
    module without contacting anything.

    The returned frame has already been through
    :func:`~src.profiles.weather.prepare_weather_frame`, so it carries the
    canonical columns, has timezone-aware interval-start timestamps, and has
    passed the same unit-plausibility checks as any other weather input.
    """

    resolved_key, resolved_email = _credentials(api_key, email)
    fetch = fetcher or default_fetcher

    try:
        data, metadata = fetch(request, resolved_key, resolved_email)
    except NSRDBError:
        raise
    except Exception as error:
        # Credentials can appear in a URL inside a requests exception, so the
        # original message is deliberately not interpolated into this one.
        raise NSRDBError(
            f"NSRDB retrieval failed for dataset {request.dataset!r}, year "
            f"{request.year!r}, at ({request.latitude}, {request.longitude}). "
            f"Cause: {type(error).__name__}. Check the key, the year, and "
            f"that the coordinates fall inside the product's domain."
        ) from error

    frame, convention = to_canonical_weather_frame(data, request)

    prepared = prepare_weather_frame(
        frame, label=f"NSRDB {request.dataset} {request.year}"
    )

    return NSRDBWeather(
        frame=prepared,
        metadata=dict(metadata or {}),
        provenance={
            "source": "nsrdb_psm4",
            "dataset": request.dataset,
            "year": request.year,
            "latitude": request.latitude,
            "longitude": request.longitude,
            "timezone": request.timezone,
            "time_step_minutes": request.time_step_minutes,
            "interval_label_convention": convention,
            "leap_day": request.leap_day,
            "interval_count": len(prepared),
            "parameters": list(NSRDB_PARAMETERS),
        },
        warnings=_build_warnings(request),
    )


def save_weather_csv(frame: pd.DataFrame, path: str | Path) -> Path:
    """Write a canonical weather frame where ``load_weather_csv`` can read it.

    This is what makes a fetch a one-off. A saved year is read back offline
    forever, costs no API quota, and makes a study reproducible by someone
    without a key -- so fetch once, save, and point the analysis at the file.

    Timestamps are written in **UTC**, not in site local time. A local-time
    file that spans a daylight-saving fall-back carries two different offsets
    in one column -- correct and unambiguous, but pandas parses it to object
    dtype and will refuse it outright in a future version. UTC has one offset
    all year, names the same instants, and is converted back to the site zone
    by the interval index like any other input.
    """

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    missing = sorted(set(REQUIRED_WEATHER_COLUMNS) - set(frame.columns))

    if missing:
        raise NSRDBError(
            f"Cannot save a weather CSV missing {missing}. Expected "
            f"{list(REQUIRED_WEATHER_COLUMNS)}."
        )

    saved = frame[list(REQUIRED_WEATHER_COLUMNS)].copy()
    saved[TIMESTAMP] = pd.to_datetime(saved[TIMESTAMP]).dt.tz_convert("UTC")
    saved.to_csv(destination, index=False)

    return destination
