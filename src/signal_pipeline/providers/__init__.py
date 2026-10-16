"""Market price provider registry.

Adding a provider means adding one adapter module and one entry here; no
conditional logic belongs in the common processing code.
"""

import inspect

from .base import (
    PRICE_COLUMNS,
    DuplicateIntervalError,
    EmptyResponseError,
    InvalidLocationError,
    MarketProvider,
    MissingCredentialsError,
    MissingIntervalError,
    RangeLimitError,
    SchemaError,
    SignalProviderError,
    TimezoneNormalizationError,
    UnitConversionError,
    UnknownRegionError,
    UnsupportedProviderError,
)
from .caiso import CAISOProvider
from .ercot import ERCOTProvider
from .gridstatus_io import GridStatusIOProvider
from .pjm import PJMProvider

PROVIDER_REGISTRY: dict[str, type[MarketProvider]] = {
    "caiso": CAISOProvider,
    "ercot": ERCOTProvider,
    "gridstatus_io": GridStatusIOProvider,
    "pjm": PJMProvider,
}


def _provider_class(provider_name: str) -> type[MarketProvider]:
    key = str(provider_name).strip().lower()
    if key not in PROVIDER_REGISTRY:
        raise UnsupportedProviderError(
            f"Unsupported market provider {provider_name!r}. "
            f"Supported providers: {sorted(PROVIDER_REGISTRY)}."
        )
    return PROVIDER_REGISTRY[key]


def provider_configuration_schema(provider_name: str) -> tuple[frozenset, frozenset]:
    """Describe non-secret configuration without constructing a client."""
    adapter = _provider_class(provider_name)
    options = frozenset(inspect.signature(adapter.__init__).parameters) - {"self", "api_key"}
    required = getattr(adapter, "required_configuration_options", frozenset())
    return options, required


def get_provider(
    provider_name: str,
    **provider_options,
) -> MarketProvider:
    """Instantiate the adapter registered under ``provider_name``.

    Options that a given adapter does not accept are dropped rather than
    raising. Construction options are provider-specific by nature -- CAISO
    throttles with ``sleep_seconds``, PJM takes an ``api_key``, ERCOT takes a
    ``location_type`` -- and callers that iterate over regions should not have
    to branch on which provider they happen to be talking to.
    """

    adapter_class = _provider_class(provider_name)

    accepted = inspect.signature(adapter_class.__init__).parameters

    supported_options = {
        name: value
        for name, value in provider_options.items()
        if name in accepted
    }

    return adapter_class(**supported_options)


def supported_providers() -> list[str]:
    return sorted(PROVIDER_REGISTRY)


__all__ = [
    "PRICE_COLUMNS",
    "PROVIDER_REGISTRY",
    "CAISOProvider",
    "DuplicateIntervalError",
    "ERCOTProvider",
    "EmptyResponseError",
    "GridStatusIOProvider",
    "InvalidLocationError",
    "MarketProvider",
    "MissingCredentialsError",
    "MissingIntervalError",
    "PJMProvider",
    "RangeLimitError",
    "SchemaError",
    "SignalProviderError",
    "TimezoneNormalizationError",
    "UnitConversionError",
    "UnknownRegionError",
    "UnsupportedProviderError",
    "get_provider",
    "provider_configuration_schema",
    "supported_providers",
]
