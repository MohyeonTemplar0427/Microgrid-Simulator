"""Keep configured server credential values out of persisted output and errors."""
import json
import os
import re
from urllib.parse import quote, quote_plus


def redact(text):
    values = [value for key, value in os.environ.items() if value and
              (re.search(r'(?:API_KEY|API_EMAIL|TOKEN|SECRET|PASSWORD|PASSWD)$', key))]
    for value in sorted(values, key=len, reverse=True):
        for encoded in {value, quote(value, safe=''), quote_plus(value), json.dumps(value)[1:-1]}:
            text = text.replace(encoded, '[redacted]')
    return text


def worker_environment():
    # Auth/session and unrelated database credentials have no role in simulations.
    return {key: value for key, value in os.environ.items()
            if not key.startswith(('MICROGRID_OIDC_', 'MYSQL_'))}
