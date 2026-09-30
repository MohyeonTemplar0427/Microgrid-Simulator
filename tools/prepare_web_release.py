"""Validate and pin a local-web release while its API and worker are stopped."""

import argparse
import os
from pathlib import Path

from src.local_web.auth import OIDCConfig
from src.local_web.hosting import public_origin_from_environment
from src.local_web.runtime import Application, worker_connected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--hosted", action="store_true", help="Validate HTTPS origin and OIDC settings.")
    parser.add_argument("--env-file", type=Path, help="Read the private hosted API settings file.")
    parser.add_argument("--refresh-engine", action="store_true", help="Explicitly adopt this release's engine after validation and backup.")
    args = parser.parse_args()
    if args.env_file is not None:
        from dotenv import dotenv_values
        if not args.env_file.is_file():
            parser.error("The API settings file does not exist.")
        values = dotenv_values(args.env_file)
        for key in ("MICROGRID_PUBLIC_ORIGIN", "MICROGRID_AUTH_MODE",
                    "MICROGRID_OIDC_ISSUER", "MICROGRID_OIDC_CLIENT_ID",
                    "MICROGRID_OIDC_CLIENT_SECRET", "MICROGRID_OIDC_REDIRECT_URI"):
            os.environ.pop(key, None)
            if values.get(key):
                os.environ[key] = values[key]
    if args.hosted:
        config = OIDCConfig.from_environment()
        public_origin_from_environment(True, config)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    if worker_connected(args.data_dir):
        parser.error("Stop the simulation worker before preparing a release.")
    application = Application(args.data_dir, refresh=args.refresh_engine, embedded_worker=False)
    try:
        print(f"Release prepared; engine snapshot {application.engine['id'][:12]}.")
    finally:
        application.close()


if __name__ == "__main__":
    main()
