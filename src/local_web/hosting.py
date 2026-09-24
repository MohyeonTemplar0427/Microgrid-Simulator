"""Fail-closed configuration for a single-host HTTPS reverse proxy."""
import os
import re
from urllib.parse import urlsplit


def validate_public_origin(value):
    url = urlsplit(value)
    try:
        port = url.port
    except ValueError:
        raise ValueError('Invalid public origin port.') from None
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.path or url.query or url.fragment or value != value.strip()
            or not re.fullmatch(r'https://[a-z0-9.-]+(?::[0-9]+)?', value)
            or (port is not None and not 1 <= port <= 65535)):
        raise ValueError('MICROGRID_PUBLIC_ORIGIN must be an exact HTTPS origin, without a path, credentials, query, or trailing slash.')
    return value


def public_origin_from_environment(hosted, config):
    value = os.getenv('MICROGRID_PUBLIC_ORIGIN', '')
    if not hosted:
        if value or (config and urlsplit(config.redirect_uri).scheme == 'https'):
            raise ValueError('Public origin/HTTPS sign-in requires explicit --hosted mode.')
        return None
    validate_public_origin(value)
    if config is None or config.redirect_uri != value + '/auth/callback':
        raise ValueError('Hosted mode requires OIDC and an exact public-origin callback match.')
    return value
