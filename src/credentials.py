"""Explicit, allowlisted provider credentials for local application entry points.

Importing this module never reads a file or changes the environment. Process
values, including intentionally empty ones, take precedence over dotenv values.
Authentication and database settings are deliberately outside these allowlists.
"""

import os
from pathlib import Path
from typing import Iterable


DEFAULT_ENV_PATH = Path(__file__).resolve().parent / ".env"
WEATHER_CREDENTIALS = ("NSRDB_API_KEY", "NSRDB_API_EMAIL")
CARBON_CREDENTIALS = ("ELECTRICITY_MAPS_API_KEY",)
MARKET_CREDENTIALS = ("PJM_API_KEY", "GRIDSTATUS_API_KEY")
LOCAL_STUDY_CREDENTIALS = WEATHER_CREDENTIALS + CARBON_CREDENTIALS
SIGNAL_CREDENTIALS = CARBON_CREDENTIALS + MARKET_CREDENTIALS
_ALLOWED_NAMES = frozenset(LOCAL_STUDY_CREDENTIALS + MARKET_CREDENTIALS)


def load_credentials(
    env_file: str | Path | None = DEFAULT_ENV_PATH,
    *,
    names: Iterable[str],
) -> None:
    """Fill only missing, explicitly selected provider variables from one file.

    ``None`` means environment-only operation. A missing file or empty file
    value leaves the variable unset; the provider retains its existing missing-
    credential error. No parent-directory dotenv discovery is performed.
    """
    selected = tuple(names)
    if not set(selected) <= _ALLOWED_NAMES:
        raise ValueError("Only supported provider credential names may be loaded.")
    missing = [name for name in selected if name not in os.environ]
    if env_file is None or not missing:
        return
    try:
        path = Path(env_file)
        if not path.is_file():
            return
        # dotenv_values uses override=True when expanding ${VARIABLE}. Use
        # the parser's override=False mode so interpolation also honors the
        # process environment, without loading unrelated file entries.
        from dotenv.main import DotEnv

        values = DotEnv(path, override=False, encoding="utf-8").dict()
    except (OSError, UnicodeError):
        raise ValueError("Could not read the provider credential file.") from None
    for name in missing:
        if values.get(name):
            os.environ.setdefault(name, values[name])
