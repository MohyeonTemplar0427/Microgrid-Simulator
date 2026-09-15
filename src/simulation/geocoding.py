"""Turn a typed place name into the coordinates the PV model needs.

The weather-derived PV models take a numeric latitude and longitude, and
nothing else will do: solar position is computed from them, and a degree of
error moves sunrise by minutes. Asking a user to look those up by hand is a
poor experience and an easy place to transpose a sign, so this module lets
them type "Oakland, CA" and get 37.804, -122.271 back.

**The coordinates remain the stored truth.** What is geocoded here is a
convenience that *fills in* latitude and longitude; it never replaces them,
and a failed lookup must leave whatever coordinates were already there
untouched. :func:`GeocodingError` exists so a caller can report a failure
without having anything to write.

**Requests are explicit.** Geocoding providers are shared infrastructure with
usage policies, so a lookup happens when a user asks for one -- never while
they are typing, and never as a side effect of some other field changing.
Repeated lookups of the same text are served from an in-process cache.

**No credentials.** The default provider is Nominatim, OpenStreetMap's public
geocoder, which needs no key. Its usage policy does require a descriptive
User-Agent identifying the application, which :data:`DEFAULT_USER_AGENT`
supplies. A deployment expecting real volume should move to a provider with a
contract rather than leaning on a free service; the
:class:`GeocodingProvider` abstraction is there so that is a new class rather
than a rewrite.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urlencode

#: Seconds to wait for a geocoding response before giving up. Short enough
#: that a wedged provider does not look like a frozen application.
DEFAULT_TIMEOUT_SECONDS = 10.0

#: Nominatim's usage policy requires an application to identify itself. A
#: generic agent gets rate limited or blocked outright.
DEFAULT_USER_AGENT = (
    "MicrogridSimulator/1.0 (microgrid analysis; contact via repository)"
)

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"

#: How many distinct queries to remember. Small because a session searches for
#: a handful of sites, and a stale coordinate is worse than a second request.
DEFAULT_CACHE_SIZE = 64


class GeocodingError(Exception):
    """Raised when a place name could not be turned into coordinates.

    Always safe to show to a user: the message says what failed and what to do
    about it, and never carries a URL or a credential.
    """


@dataclass(frozen=True)
class GeocodedLocation:
    """One resolved place.

    ``display_name`` is the provider's readable description of what it
    matched, which is the only way a user can tell "Springfield" in Illinois
    from "Springfield" in Missouri.
    """

    query: str
    display_name: str
    latitude: float
    longitude: float
    provider: str

    def summary(self) -> str:
        return (
            f"{self.display_name} "
            f"({self.latitude:.4f}, {self.longitude:.4f})"
        )


def _validate_coordinates(latitude: float, longitude: float, provider: str) -> None:
    if not -90 <= latitude <= 90:
        raise GeocodingError(
            f"{provider} returned latitude {latitude}, which is outside "
            f"-90 to 90."
        )

    if not -180 <= longitude <= 180:
        raise GeocodingError(
            f"{provider} returned longitude {longitude}, which is outside "
            f"-180 to 180."
        )


class GeocodingProvider(ABC):
    """One geocoding service."""

    name: str

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> GeocodedLocation:
        """Resolve ``query`` or raise :class:`GeocodingError`."""


class NominatimGeocoder(GeocodingProvider):
    """OpenStreetMap's public geocoder. No credential, but a usage policy.

    ``requests`` is imported inside :meth:`search` rather than at module
    scope, so importing this module -- which the GUI does at startup -- never
    pulls in an HTTP stack, and a test that injects a fake provider never
    touches one either.
    """

    name = "Nominatim (OpenStreetMap)"

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        url: str = NOMINATIM_SEARCH_URL,
    ) -> None:
        self.user_agent = user_agent
        self.url = url

    def search(
        self,
        query: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> GeocodedLocation:
        import requests

        parameters = {"q": query, "format": "json", "limit": 1}

        try:
            response = requests.get(
                self.url,
                params=parameters,
                headers={"User-Agent": self.user_agent},
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            matches = response.json()
        except requests.Timeout as error:
            raise GeocodingError(
                f"The location service did not respond within "
                f"{timeout_seconds:.0f} seconds. Check the network "
                f"connection, or enter latitude and longitude directly."
            ) from error
        except requests.RequestException as error:
            # A requests exception can carry the full request URL; the query
            # text is the user's, but the message is kept to the failure type
            # so nothing unexpected is echoed into the interface.
            raise GeocodingError(
                f"The location service could not be reached "
                f"({type(error).__name__}). Check the network connection, or "
                f"enter latitude and longitude directly."
            ) from error
        except (ValueError, json.JSONDecodeError) as error:
            raise GeocodingError(
                "The location service returned a response that could not be "
                "read. Try again, or enter latitude and longitude directly."
            ) from error

        if not matches:
            raise GeocodingError(
                f"No location matched {query!r}. Try adding a state or "
                f"country, or enter latitude and longitude directly."
            )

        match = matches[0]

        try:
            latitude = float(match["lat"])
            longitude = float(match["lon"])
        except (KeyError, TypeError, ValueError) as error:
            raise GeocodingError(
                f"The location service returned a match for {query!r} without "
                f"usable coordinates."
            ) from error

        _validate_coordinates(latitude, longitude, self.name)

        return GeocodedLocation(
            query=query,
            display_name=str(match.get("display_name") or query),
            latitude=latitude,
            longitude=longitude,
            provider=self.name,
        )


class LocationSearch:
    """A geocoding provider plus a small cache of what it has already said.

    The cache exists to be polite rather than to be fast: a user who searches
    the same site twice in one session should not cost the provider two
    requests. It is per process and is never written to disk, so a coordinate
    cannot go stale between runs.
    """

    def __init__(
        self,
        provider: GeocodingProvider | None = None,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        cache_size: int = DEFAULT_CACHE_SIZE,
    ) -> None:
        self.provider = provider or NominatimGeocoder()
        self.timeout_seconds = timeout_seconds
        self.cache_size = cache_size
        self._cache: dict[str, GeocodedLocation] = {}
        self.request_count = 0

    @staticmethod
    def _cache_key(query: str) -> str:
        return " ".join(query.split()).casefold()

    def search(self, query: str) -> GeocodedLocation:
        """Resolve ``query``, using the cache when it has been asked before."""

        text = query.strip()

        if not text:
            raise GeocodingError(
                "Enter a place to search for -- an address, a city, or a site "
                "name."
            )

        key = self._cache_key(text)

        if key in self._cache:
            return self._cache[key]

        location = self.provider.search(
            text, timeout_seconds=self.timeout_seconds
        )

        self.request_count += 1

        if len(self._cache) >= self.cache_size:
            # Plain FIFO eviction. A session searches a handful of sites, so
            # anything cleverer would be more code than it saves requests.
            self._cache.pop(next(iter(self._cache)))

        self._cache[key] = location

        return location

    def cached_queries(self) -> tuple[str, ...]:
        return tuple(self._cache)


def build_search_url(query: str, url: str = NOMINATIM_SEARCH_URL) -> str:
    """The request a search would make. For diagnostics and documentation."""

    return f"{url}?{urlencode({'q': query, 'format': 'json', 'limit': 1})}"
