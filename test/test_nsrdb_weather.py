"""Tests for the NSRDB weather adapter.

**Every test here is offline.** Network access is blocked for the whole
module by an autouse fixture, so a test that accidentally reaches for the API
fails loudly rather than silently spending quota or depending on a key nobody
else has. Responses are built as real PSM4-format CSV and parsed by pvlib's
own reader, so the conversion is exercised against genuinely pvlib-shaped
input rather than against an idea of it.
"""

import io
import socket
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pvlib.iotools import read_nsrdb_psm4

from src.profiles import (
    NSRDB_API_KEY_ENV_VAR,
    NSRDB_EMAIL_ENV_VAR,
    NSRDBError,
    NSRDBRequest,
    fetch_nsrdb_weather,
    load_weather_csv,
    prepare_weather_frame,
    save_weather_csv,
)
from src.profiles.nsrdb import (
    INTERVAL_MIDPOINT,
    horizon_years,
    year_coverage_problem,
    INTERVAL_START,
    default_fetcher,
    detect_interval_label_convention,
    to_canonical_weather_frame,
)
from src.profiles.weather import (
    DHI_W_PER_M2,
    DNI_W_PER_M2,
    GHI_W_PER_M2,
    REQUIRED_WEATHER_COLUMNS,
    TEMPERATURE_C,
    WIND_SPEED_M_PER_S,
)

PACIFIC = "America/Los_Angeles"
LATITUDE = 37.77
LONGITUDE = -122.42

#: Pacific standard time, the fixed offset NSRDB reports for this location.
STANDARD_OFFSET_HOURS = -8


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail any test in this module that tries to open a socket."""

    def refuse(*args, **kwargs):
        raise AssertionError(
            "A test attempted network access. NSRDB tests must be offline."
        )

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.fixture(autouse=True)
def no_ambient_credentials(monkeypatch):
    """Make the environment credential-free unless a test supplies one.

    Without this a developer who has a real key in ``.env`` would exercise
    different code paths than continuous integration does.

    Clearing the variables is not enough on its own. ``_credentials`` loads
    ``src/.env`` with ``override=False``, which leaves an existing variable
    alone but still *sets* a missing one -- so a deleted variable would be
    restored straight from the developer's file. Pointing ``ENV_PATH`` at a
    path that does not exist makes that load a no-op.
    """

    monkeypatch.delenv(NSRDB_API_KEY_ENV_VAR, raising=False)
    monkeypatch.delenv(NSRDB_EMAIL_ENV_VAR, raising=False)
    monkeypatch.setattr(
        "src.profiles.nsrdb.ENV_PATH",
        Path(__file__).resolve().parent / "no-such-directory" / ".env",
    )


def psm4_response(
    *,
    days: int = 1,
    time_step_minutes: int = 60,
    minute_offset: int | None = None,
    start_month: int = 6,
    start_day: int = 21,
    year: int = 2023,
    peak_ghi: float = 900.0,
    temperature_c: float = 18.0,
    wind_speed_m_per_s: float = 3.0,
) -> io.StringIO:
    """A PSM4-format CSV buffer, in the layout the NSRDB API returns.

    ``minute_offset`` defaults to half the time step, which is how NSRDB
    labels its records -- at the middle of the interval they describe.
    """

    if minute_offset is None:
        minute_offset = time_step_minutes // 2

    metadata_fields = [
        "Source", "Location ID", "City", "State", "Country", "Latitude",
        "Longitude", "Time Zone", "Elevation", "Local Time Zone", "Version",
    ]
    metadata_values = [
        "NSRDB", "149279", "San Francisco", "California", "United States",
        str(LATITUDE), str(LONGITUDE), str(STANDARD_OFFSET_HOURS), "16",
        str(STANDARD_OFFSET_HOURS), "4.0.0",
    ]
    columns = [
        "Year", "Month", "Day", "Hour", "Minute", "GHI", "DNI", "DHI",
        "Temperature", "Wind Speed",
    ]

    steps_per_day = 24 * 60 // time_step_minutes

    buffer = io.StringIO()
    buffer.write(",".join(metadata_fields) + "\n")
    buffer.write(",".join(metadata_values) + "\n")
    buffer.write(",".join(columns) + "\n")

    for day in range(days):
        date = pd.Timestamp(year=year, month=start_month, day=start_day) + (
            pd.DateOffset(days=day)
        )

        for step in range(steps_per_day):
            minutes = step * time_step_minutes + minute_offset
            hour, minute = divmod(minutes, 60)

            # A smooth daylight bump, zero at night: enough structure for a
            # shifted profile to be detectable.
            fraction = minutes / (24 * 60)
            daylight = max(np.sin(np.pi * (fraction - 0.25) / 0.5), 0.0)

            ghi = peak_ghi * daylight
            buffer.write(
                ",".join(
                    str(value)
                    for value in (
                        date.year, date.month, date.day, hour, minute,
                        round(ghi, 3), round(ghi * 0.85, 3),
                        round(ghi * 0.15, 3), temperature_c,
                        wind_speed_m_per_s,
                    )
                )
                + "\n"
            )

    buffer.seek(0)
    return buffer


def parsed_response(**kwargs):
    """A PSM4 response as pvlib's own reader returns it."""

    return read_nsrdb_psm4(psm4_response(**kwargs))


def make_request(**overrides) -> NSRDBRequest:
    settings = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "year": 2023,
        "timezone": PACIFIC,
        "time_step_minutes": 60,
    }
    settings.update(overrides)
    return NSRDBRequest(**settings)


def fetcher_returning(response):
    """A stand-in for the network call, recording how it was invoked."""

    calls = []

    def fetch(request, api_key, email):
        calls.append({"request": request, "api_key": api_key, "email": email})
        return response

    fetch.calls = calls
    return fetch


## The offline guarantee ---------------------------------------------------


def test_the_network_guard_is_actually_armed():
    # If this ever stops raising, every other "offline" claim in this module
    # is unverified, so the guard is itself tested.
    with pytest.raises(AssertionError, match="offline"):
        socket.create_connection(("example.invalid", 80))


def test_the_default_fetcher_is_never_used_by_these_tests():
    response = parsed_response()
    fetch = fetcher_returning(response)

    fetch_nsrdb_weather(
        make_request(), api_key="k", email="e@example.com", fetcher=fetch
    )

    assert len(fetch.calls) == 1
    assert fetch is not default_fetcher


def test_importing_the_module_needs_no_credentials():
    # Building a request must not touch the environment; only a fetch does.
    request = make_request()

    assert request.latitude == LATITUDE


## Horizon years and coverage ---------------------------------------------


def _horizon(start, end, timezone="America/Los_Angeles"):
    from src.timeseries.interval_table import build_interval_index

    return build_interval_index(
        start_date=start, end_date=end, timezone=timezone
    )


def test_a_horizon_inside_one_year_needs_that_year():
    assert horizon_years(_horizon("2025-06-01", "2025-06-03")) == (2025,)


def test_the_inclusive_end_date_is_respected():
    # 31 December is the last billed day, so the horizon is 2025 alone even
    # though the exclusive end instant falls in 2026.
    assert horizon_years(_horizon("2025-12-30", "2025-12-31")) == (2025,)


def test_a_horizon_crossing_new_year_needs_both_years():
    assert horizon_years(_horizon("2025-12-30", "2026-01-02")) == (2025, 2026)


def test_the_matching_year_has_no_problem():
    horizon = _horizon("2025-06-01", "2025-06-03")

    assert year_coverage_problem(2025, horizon) is None


def test_a_mismatched_year_is_named_as_a_proxy():
    horizon = _horizon("2026-05-31", "2026-06-02")

    problem = year_coverage_problem(2025, horizon)

    assert problem is not None
    assert "2025" in problem
    assert "2026" in problem
    assert "proxy" in problem


def test_a_horizon_spanning_two_years_says_one_fetch_is_not_enough():
    horizon = _horizon("2025-12-30", "2026-01-02")

    problem = year_coverage_problem(2025, horizon)

    assert problem is not None
    assert "2025 and 2026" in problem
    assert "separately" in problem


def test_three_or_more_years_read_as_a_range():
    horizon = _horizon("2024-03-01", "2026-06-02")

    problem = year_coverage_problem(2024, horizon)

    assert "2024 through 2026" in problem
    assert "and 2025 and" not in problem


def test_a_typical_year_name_carries_no_opinion():
    # tmy is not a calendar year, so it is never called a mismatch.
    horizon = _horizon("2026-05-31", "2026-06-02")

    assert year_coverage_problem("tmy-2020", horizon) is None


def test_coverage_is_judged_in_the_site_timezone():
    # The same instants are a different calendar date in Honolulu, but the
    # horizon is stated in local dates, so the year is the local one.
    horizon = _horizon("2025-01-01", "2025-01-02", timezone="Pacific/Honolulu")

    assert horizon_years(horizon) == (2025,)


## Credentials ------------------------------------------------------------


def test_a_missing_key_and_address_are_both_named():
    with pytest.raises(NSRDBError) as error:
        fetch_nsrdb_weather(make_request(), fetcher=fetcher_returning(None))

    message = str(error.value)
    assert NSRDB_API_KEY_ENV_VAR in message
    assert NSRDB_EMAIL_ENV_VAR in message
    assert "load_weather_csv" in message


def test_a_missing_address_alone_is_named():
    with pytest.raises(NSRDBError) as error:
        fetch_nsrdb_weather(
            make_request(), api_key="k", fetcher=fetcher_returning(None)
        )

    message = str(error.value)
    assert NSRDB_EMAIL_ENV_VAR in message
    assert NSRDB_API_KEY_ENV_VAR not in message


def test_credentials_are_read_from_the_environment(monkeypatch):
    monkeypatch.setenv(NSRDB_API_KEY_ENV_VAR, "environment-key")
    monkeypatch.setenv(NSRDB_EMAIL_ENV_VAR, "environment@example.com")

    fetch = fetcher_returning(parsed_response())
    fetch_nsrdb_weather(make_request(), fetcher=fetch)

    assert fetch.calls[0]["api_key"] == "environment-key"
    assert fetch.calls[0]["email"] == "environment@example.com"


def test_explicit_credentials_win_over_the_environment(monkeypatch):
    monkeypatch.setenv(NSRDB_API_KEY_ENV_VAR, "environment-key")
    monkeypatch.setenv(NSRDB_EMAIL_ENV_VAR, "environment@example.com")

    fetch = fetcher_returning(parsed_response())
    fetch_nsrdb_weather(
        make_request(), api_key="explicit", email="x@example.com", fetcher=fetch
    )

    assert fetch.calls[0]["api_key"] == "explicit"


def test_a_failed_retrieval_does_not_echo_the_underlying_message():
    # A requests exception can carry the full URL, and the URL carries the
    # API key. The cause is named by type; its text is not interpolated.
    def failing(request, api_key, email):
        raise RuntimeError(
            f"https://example.invalid/api?api_key={api_key}&email={email}"
        )

    with pytest.raises(NSRDBError) as error:
        fetch_nsrdb_weather(
            make_request(),
            api_key="SECRET-KEY-VALUE",
            email="person@example.com",
            fetcher=failing,
        )

    message = str(error.value)
    assert "SECRET-KEY-VALUE" not in message
    assert "person@example.com" not in message
    assert "RuntimeError" in message


def test_provenance_carries_no_credential():
    result = fetch_nsrdb_weather(
        make_request(),
        api_key="SECRET-KEY-VALUE",
        email="person@example.com",
        fetcher=fetcher_returning(parsed_response()),
    )

    rendered = repr(result.provenance) + repr(result.metadata)

    assert "SECRET-KEY-VALUE" not in rendered
    assert "person@example.com" not in rendered


## Request validation -----------------------------------------------------


def test_coordinates_are_bounded():
    with pytest.raises(NSRDBError):
        make_request(latitude=91.0)

    with pytest.raises(NSRDBError):
        make_request(longitude=-181.0)


def test_an_unknown_dataset_names_the_available_ones():
    with pytest.raises(NSRDBError) as error:
        make_request(dataset="satellite")

    assert "conus" in str(error.value)


def test_an_unavailable_time_step_is_rejected():
    with pytest.raises(NSRDBError) as error:
        make_request(time_step_minutes=10)

    assert "[5, 15, 30, 60]" in str(error.value)


def test_a_typical_year_cannot_be_addressed_by_calendar_year():
    # A TMY is assembled from months of different real years, so asking for
    # "the TMY of 2023" is a category error rather than a lookup that fails.
    with pytest.raises(NSRDBError) as error:
        make_request(dataset="tmy", year=2023)

    assert "assembled from many years" in str(error.value)

    make_request(dataset="tmy", year="tmy")


def test_a_calendar_dataset_cannot_be_addressed_by_a_typical_year_name():
    with pytest.raises(NSRDBError) as error:
        make_request(dataset="conus", year="tmy")

    assert "calendar year as an integer" in str(error.value)


def test_a_named_site_timezone_is_required():
    with pytest.raises(NSRDBError) as error:
        make_request(timezone="")

    assert "daylight saving" in str(error.value)


## Interval label convention ----------------------------------------------


@pytest.mark.parametrize("time_step", [30, 60])
def test_midpoint_labels_are_detected_at_every_even_time_step(time_step):
    data, _ = parsed_response(time_step_minutes=time_step)

    assert (
        detect_interval_label_convention(data.index, time_step)
        == INTERVAL_MIDPOINT
    )


def test_an_odd_step_cannot_be_midpoint_labelled_on_whole_minutes():
    # A 15-minute interval's midpoint is 7.5 minutes in, which no whole-minute
    # NSRDB record can express -- so the sub-hourly products are necessarily
    # interval-start labelled. A file claiming otherwise is malformed, and the
    # detector says so rather than rounding.
    data, _ = parsed_response(time_step_minutes=15, minute_offset=7)

    with pytest.raises(NSRDBError) as error:
        detect_interval_label_convention(data.index, 15)

    assert "neither the start nor the midpoint" in str(error.value)


@pytest.mark.parametrize("time_step", [15, 30, 60])
def test_start_labels_are_detected_at_every_time_step(time_step):
    data, _ = parsed_response(time_step_minutes=time_step, minute_offset=0)

    assert (
        detect_interval_label_convention(data.index, time_step)
        == INTERVAL_START
    )


def test_a_label_that_is_neither_start_nor_midpoint_is_refused():
    # Guessing here shifts the whole profile against the sun by a fraction of
    # an interval, which no downstream check would catch.
    data, _ = parsed_response(time_step_minutes=60, minute_offset=10)

    with pytest.raises(NSRDBError) as error:
        detect_interval_label_convention(data.index, 60)

    assert "neither the start nor the midpoint" in str(error.value)


def test_an_irregular_grid_is_refused():
    index = pd.DatetimeIndex(
        ["2023-06-21 00:30", "2023-06-21 01:30", "2023-06-21 02:07"],
        tz="Etc/GMT+8",
    )

    with pytest.raises(NSRDBError) as error:
        detect_interval_label_convention(index, 60)

    assert "regular" in str(error.value)


def test_midpoint_labels_are_shifted_back_to_interval_starts():
    request = make_request(time_step_minutes=60)
    data, _ = parsed_response(time_step_minutes=60)

    frame, convention = to_canonical_weather_frame(data, request)

    assert convention == INTERVAL_MIDPOINT
    # NSRDB's 00:30 record describes the hour beginning at 00:00.
    assert frame["timestamp"].dt.minute.unique().tolist() == [0]
    assert len(frame) == len(data)


def test_start_labels_are_left_alone():
    request = make_request(time_step_minutes=60)
    data, _ = parsed_response(time_step_minutes=60, minute_offset=0)

    frame, convention = to_canonical_weather_frame(data, request)

    assert convention == INTERVAL_START
    np.testing.assert_array_equal(
        frame["timestamp"].to_numpy(),
        data.index.tz_convert(PACIFIC).to_numpy(),
    )


def test_the_shift_moves_time_and_not_the_measurements():
    request = make_request(time_step_minutes=60)
    data, _ = parsed_response(time_step_minutes=60)

    frame, _ = to_canonical_weather_frame(data, request)

    np.testing.assert_allclose(
        frame[GHI_W_PER_M2].to_numpy(), data["ghi"].to_numpy()
    )


## Timezone conversion ----------------------------------------------------


def test_the_fixed_offset_is_converted_not_relocalised():
    # NSRDB reports local *standard* time all year. Converting keeps the
    # instant and lets the wall clock shift in summer; re-localising would
    # move every summer interval by an hour.
    request = make_request()
    data, _ = parsed_response(start_month=6, start_day=21)

    frame, _ = to_canonical_weather_frame(data, request)

    timestamps = pd.DatetimeIndex(frame["timestamp"])

    assert str(timestamps.tz) == PACIFIC
    # June in the Pacific zone is daylight time, one hour ahead of standard.
    assert timestamps[0].utcoffset() == pd.Timedelta(hours=-7)

    # The instant itself is unchanged by the conversion.
    shifted = data.index - pd.Timedelta(minutes=30)
    assert timestamps[0] == shifted[0]


def test_a_winter_request_lands_on_standard_time():
    request = make_request()
    data, _ = parsed_response(start_month=12, start_day=21)

    frame, _ = to_canonical_weather_frame(data, request)
    timestamps = pd.DatetimeIndex(frame["timestamp"])

    assert timestamps[0].utcoffset() == pd.Timedelta(hours=-8)


def test_a_timezone_naive_response_is_refused():
    data, _ = parsed_response()
    naive = data.copy()
    naive.index = naive.index.tz_localize(None)

    with pytest.raises(NSRDBError) as error:
        to_canonical_weather_frame(naive, make_request())

    assert "timezone naive" in str(error.value)


def test_a_response_without_a_time_index_is_refused():
    data, _ = parsed_response()
    flat = data.reset_index(drop=True)

    with pytest.raises(NSRDBError) as error:
        to_canonical_weather_frame(flat, make_request())

    assert "not time indexed" in str(error.value)


def test_a_response_missing_a_field_names_it():
    data, _ = parsed_response()
    without_wind = data.drop(columns=["wind_speed"])

    with pytest.raises(NSRDBError) as error:
        to_canonical_weather_frame(without_wind, make_request())

    assert "wind_speed" in str(error.value)


def test_the_response_frame_is_never_modified():
    data, _ = parsed_response()
    untouched = data.copy(deep=True)

    to_canonical_weather_frame(data, make_request())

    pd.testing.assert_frame_equal(data, untouched)


## End to end -------------------------------------------------------------


def test_a_fetch_returns_a_frame_the_weather_layer_accepts():
    result = fetch_nsrdb_weather(
        make_request(),
        api_key="k",
        email="e@example.com",
        fetcher=fetcher_returning(parsed_response()),
    )

    assert list(result.frame.columns) == list(REQUIRED_WEATHER_COLUMNS)
    assert len(result.frame) == 24

    # Already validated, so re-preparing it is a no-op rather than a change.
    pd.testing.assert_frame_equal(
        prepare_weather_frame(result.frame), result.frame
    )


def test_the_request_reaches_the_fetcher_unchanged():
    request = make_request(time_step_minutes=30, dataset="full_disc")
    fetch = fetcher_returning(parsed_response(time_step_minutes=30))

    fetch_nsrdb_weather(
        request, api_key="k", email="e@example.com", fetcher=fetch
    )

    assert fetch.calls[0]["request"] is request


def test_provenance_records_the_conversion_that_was_applied():
    result = fetch_nsrdb_weather(
        make_request(),
        api_key="k",
        email="e@example.com",
        fetcher=fetcher_returning(parsed_response()),
    )

    provenance = result.provenance

    assert provenance["source"] == "nsrdb_psm4"
    assert provenance["dataset"] == "conus"
    assert provenance["year"] == 2023
    assert provenance["timezone"] == PACIFIC
    assert provenance["interval_label_convention"] == INTERVAL_MIDPOINT
    assert provenance["interval_count"] == 24


def test_metadata_from_the_response_is_preserved():
    result = fetch_nsrdb_weather(
        make_request(),
        api_key="k",
        email="e@example.com",
        fetcher=fetcher_returning(parsed_response()),
    )

    assert result.metadata["City"] == "San Francisco"
    assert result.metadata["latitude"] == pytest.approx(LATITUDE)


def test_hourly_data_is_flagged_as_too_coarse_for_a_fifteen_minute_grid():
    result = fetch_nsrdb_weather(
        make_request(time_step_minutes=60),
        api_key="k",
        email="e@example.com",
        fetcher=fetcher_returning(parsed_response(time_step_minutes=60)),
    )

    assert any("cloud transients" in warning for warning in result.warnings)


def test_fifteen_minute_data_raises_no_resolution_warning():
    result = fetch_nsrdb_weather(
        make_request(time_step_minutes=15),
        api_key="k",
        email="e@example.com",
        fetcher=fetcher_returning(
            parsed_response(time_step_minutes=15, minute_offset=0)
        ),
    )

    assert not any("cloud transients" in warning for warning in result.warnings)


def test_a_typical_year_says_it_is_not_a_real_year():
    result = fetch_nsrdb_weather(
        make_request(dataset="tmy", year="tmy"),
        api_key="k",
        email="e@example.com",
        fetcher=fetcher_returning(parsed_response()),
    )

    assert any("no actual year" in warning for warning in result.warnings)


def test_implausible_data_is_caught_by_the_weather_layer():
    # The adapter does not get its own plausibility rules; it hands the frame
    # to the same checks every other weather input goes through, and the
    # failure surfaces as that layer's WeatherError rather than as something
    # NSRDB-specific.
    from src.profiles import WeatherError

    data, metadata = parsed_response(peak_ghi=900_000.0)

    with pytest.raises(WeatherError) as error:
        fetch_nsrdb_weather(
            make_request(),
            api_key="k",
            email="e@example.com",
            fetcher=fetcher_returning((data, metadata)),
        )

    assert "plausibility ceiling" in str(error.value)


## Caching to CSV ---------------------------------------------------------


def test_a_fetched_year_round_trips_through_a_csv_offline(tmp_path):
    # This is what makes a fetch a one-off: saved once, read back forever
    # with no key and no network.
    result = fetch_nsrdb_weather(
        make_request(),
        api_key="k",
        email="e@example.com",
        fetcher=fetcher_returning(parsed_response(days=3)),
    )

    destination = save_weather_csv(result.frame, tmp_path / "nsrdb" / "2023.csv")

    assert destination.is_file()

    reloaded = load_weather_csv(destination)

    # Stored in UTC, so the timezone object differs by design; the instants
    # and every measurement are identical.
    np.testing.assert_array_equal(
        pd.DatetimeIndex(reloaded["timestamp"]).tz_convert(PACIFIC).to_numpy(),
        pd.DatetimeIndex(result.frame["timestamp"]).to_numpy(),
    )
    pd.testing.assert_frame_equal(
        reloaded.drop(columns=["timestamp"]),
        result.frame.drop(columns=["timestamp"]),
    )


def test_a_fall_back_day_survives_the_cache_without_ambiguity(tmp_path):
    # Daylight saving ended on 5 November 2023 in the Pacific zone, so that
    # local day repeats 01:00. NSRDB itself never sees this -- it reports
    # standard time all year -- but the converted frame does, and the two
    # 01:00 rows must stay distinguishable through the cache.
    data, metadata = parsed_response(
        year=2023, start_month=11, start_day=5, days=1, time_step_minutes=60
    )

    result = fetch_nsrdb_weather(
        make_request(),
        api_key="k",
        email="e@example.com",
        fetcher=fetcher_returning((data, metadata)),
    )

    local = pd.DatetimeIndex(result.frame["timestamp"])

    # The repeated wall-clock hour really is present, at two offsets.
    assert set(local.map(lambda stamp: stamp.utcoffset())) == {
        pd.Timedelta(hours=-7),
        pd.Timedelta(hours=-8),
    }
    assert (local.hour == 1).sum() == 2

    reloaded = load_weather_csv(save_weather_csv(result.frame, tmp_path / "w.csv"))
    timestamps = pd.DatetimeIndex(reloaded["timestamp"])

    assert not timestamps.duplicated().any()
    assert timestamps.is_monotonic_increasing
    np.testing.assert_array_equal(timestamps.to_numpy(), local.to_numpy())


def test_a_local_time_csv_spanning_a_fall_back_is_readable(tmp_path):
    # Not an NSRDB file: a hand-written local-time one, where the repeated
    # hour carries two different UTC offsets in the same column. That file is
    # correct, and it must not be refused.
    local = pd.date_range(
        "2023-11-05 00:00", periods=6, freq="h", tz=PACIFIC
    )
    path = tmp_path / "local.csv"
    pd.DataFrame(
        {
            "timestamp": local.astype(str),
            GHI_W_PER_M2: 500.0,
            DNI_W_PER_M2: 400.0,
            DHI_W_PER_M2: 100.0,
            TEMPERATURE_C: 15.0,
            WIND_SPEED_M_PER_S: 2.0,
        }
    ).to_csv(path, index=False)

    reloaded = load_weather_csv(path)
    timestamps = pd.DatetimeIndex(reloaded["timestamp"])

    assert len(reloaded) == 6
    np.testing.assert_array_equal(timestamps.to_numpy(), local.to_numpy())


def test_saving_a_frame_missing_a_column_is_refused(tmp_path):
    result = fetch_nsrdb_weather(
        make_request(),
        api_key="k",
        email="e@example.com",
        fetcher=fetcher_returning(parsed_response()),
    )

    with pytest.raises(NSRDBError) as error:
        save_weather_csv(
            result.frame.drop(columns=[WIND_SPEED_M_PER_S]), tmp_path / "w.csv"
        )

    assert WIND_SPEED_M_PER_S in str(error.value)


## Feeding the PV model ---------------------------------------------------


def test_nsrdb_weather_drives_both_pv_phases(tmp_path):
    from src.profiles import (
        EquipmentSpecificPV,
        EquipmentSpecificPVConfiguration,
        InverterSpecification,
        InverterUnitConfiguration,
        ModuleSpecification,
        SubarrayConfiguration,
        WeatherDerivedPV,
        WeatherDerivedPVConfiguration,
    )
    from src.timeseries import build_interval_index
    from src.timeseries.schema import MissingDataPolicy

    result = fetch_nsrdb_weather(
        make_request(),
        api_key="k",
        email="e@example.com",
        fetcher=fetcher_returning(parsed_response(days=1)),
    )

    index = build_interval_index("2023-06-21", "2023-06-21", PACIFIC)

    # Hourly NSRDB data onto a 15-minute grid needs an explicit policy, which
    # is exactly what the resolution warning is about.
    generic = WeatherDerivedPV(
        configuration=WeatherDerivedPVConfiguration(
            latitude=LATITUDE,
            longitude=LONGITUDE,
            rated_pv_capacity_kw=50.0,
        ),
        weather_data=result.frame,
        missing_data_policy=MissingDataPolicy.INTERPOLATE,
    ).build_pv_available_kw(index)

    module = ModuleSpecification.from_cec_database(
        "Canadian_Solar_Inc__CS6X_300M"
    )
    equipment = EquipmentSpecificPV(
        configuration=EquipmentSpecificPVConfiguration(
            latitude=LATITUDE,
            longitude=LONGITUDE,
            inverter_units=(
                InverterUnitConfiguration(
                    inverter=InverterSpecification.from_cec_database(
                        "SMA_America__STP_50_US_41__480V_"
                    ),
                    subarrays=(
                        SubarrayConfiguration(
                            module=module,
                            modules_per_string=15,
                            strings=6,
                            tilt_degrees=20.0,
                        ),
                    ),
                ),
            ),
        ),
        weather_data=result.frame,
        missing_data_policy=MissingDataPolicy.INTERPOLATE,
    ).build_pv_available_kw(index)

    for series in (generic, equipment):
        assert len(series) == index.interval_count
        assert (series.to_numpy() >= 0).all()
        assert series.max() > 0


def test_offline_csv_weather_still_works_without_any_nsrdb_involvement(tmp_path):
    # The addendum's guarantee: the supplied-frame and CSV paths remain
    # available with no key, no network and no NSRDB code in the way.
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2026-06-21", periods=24, freq="h", tz=PACIFIC
            ),
            GHI_W_PER_M2: np.linspace(0, 800, 24),
            DNI_W_PER_M2: np.linspace(0, 700, 24),
            DHI_W_PER_M2: np.linspace(0, 120, 24),
            TEMPERATURE_C: 20.0,
            WIND_SPEED_M_PER_S: 2.0,
        }
    )

    path = tmp_path / "hand_written.csv"
    frame.to_csv(path, index=False)

    reloaded = load_weather_csv(path)

    assert list(reloaded.columns) == list(REQUIRED_WEATHER_COLUMNS)
    assert len(reloaded) == 24
