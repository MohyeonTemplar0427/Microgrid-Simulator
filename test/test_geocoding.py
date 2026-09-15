"""Tests for the site-location geocoder.

Entirely offline: every test injects a provider, and an autouse fixture makes
any real socket use fail loudly. A geocoder that quietly contacted a public
service during the suite would be both rude and flaky.
"""

import socket

import pytest

from src.simulation.geocoding import (
    DEFAULT_USER_AGENT,
    GeocodedLocation,
    GeocodingError,
    GeocodingProvider,
    LocationSearch,
    NominatimGeocoder,
    build_search_url,
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError(
            "A test attempted network access. Geocoding tests must be offline."
        )

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


class RecordingProvider(GeocodingProvider):
    """A stand-in that answers from a script and counts what it was asked."""

    name = "recording"

    def __init__(self, result=None, error=None) -> None:
        self.result = result
        self.error = error
        self.queries: list[str] = []

    def search(self, query, *, timeout_seconds=10.0):
        self.queries.append(query)

        if self.error is not None:
            raise self.error

        return self.result or GeocodedLocation(
            query=query,
            display_name="Oakland, Alameda County, California",
            latitude=37.8044,
            longitude=-122.2712,
            provider=self.name,
        )


def test_the_network_guard_is_armed():
    with pytest.raises(AssertionError, match="offline"):
        socket.create_connection(("example.invalid", 80))


def test_a_search_returns_coordinates_and_a_readable_name():
    search = LocationSearch(RecordingProvider())

    location = search.search("Oakland, CA")

    assert location.latitude == pytest.approx(37.8044)
    assert location.longitude == pytest.approx(-122.2712)
    assert "Oakland" in location.summary()
    assert "37.8044" in location.summary()


def test_an_empty_query_never_reaches_the_provider():
    provider = RecordingProvider()
    search = LocationSearch(provider)

    with pytest.raises(GeocodingError) as error:
        search.search("   ")

    assert provider.queries == []
    assert "address" in str(error.value)


def test_repeating_a_query_is_served_from_the_cache():
    # Geocoding services are shared infrastructure with usage policies; asking
    # twice for the same text in one session is avoidable traffic.
    provider = RecordingProvider()
    search = LocationSearch(provider)

    first = search.search("Oakland, CA")
    second = search.search("  oakland,   ca ")

    assert first is second
    assert provider.queries == ["Oakland, CA"]
    assert search.request_count == 1


def test_the_cache_evicts_rather_than_growing_without_bound():
    provider = RecordingProvider()
    search = LocationSearch(provider, cache_size=2)

    for query in ("a", "b", "c"):
        search.search(query)

    assert len(search.cached_queries()) == 2
    assert "a" not in search.cached_queries()


def test_a_provider_failure_surfaces_as_a_geocoding_error():
    search = LocationSearch(
        RecordingProvider(error=GeocodingError("service unavailable"))
    )

    with pytest.raises(GeocodingError):
        search.search("Oakland, CA")


def test_a_failed_search_is_not_cached():
    # Otherwise a transient outage would poison the session.
    provider = RecordingProvider(error=GeocodingError("temporary"))
    search = LocationSearch(provider)

    for _ in range(2):
        with pytest.raises(GeocodingError):
            search.search("Oakland, CA")

    assert provider.queries == ["Oakland, CA", "Oakland, CA"]


def test_the_default_provider_identifies_the_application():
    # Nominatim's usage policy requires it; a generic agent gets blocked.
    geocoder = NominatimGeocoder()

    assert geocoder.user_agent == DEFAULT_USER_AGENT
    assert "MicrogridSimulator" in geocoder.user_agent


def test_no_credential_is_embedded_anywhere():
    url = build_search_url("Oakland, CA")

    assert "api_key" not in url
    assert "key=" not in url
    assert url.startswith("https://")


def test_out_of_range_coordinates_from_a_provider_are_rejected():
    class BadProvider(GeocodingProvider):
        name = "bad"

        def search(self, query, *, timeout_seconds=10.0):
            from src.simulation.geocoding import _validate_coordinates

            _validate_coordinates(100.0, 0.0, self.name)

    with pytest.raises(GeocodingError) as error:
        LocationSearch(BadProvider()).search("anywhere")

    assert "-90 to 90" in str(error.value)
