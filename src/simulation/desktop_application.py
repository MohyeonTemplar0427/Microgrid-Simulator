"""Run the local study application in a desktop window.

The desktop and browser use the same HTTP routes, form, worker and results.
Keeping one interface avoids silently losing new billing controls in Tkinter.
"""

from __future__ import annotations

import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import threading

from ..local_web.runtime import Application, ROOT
from ..local_web.server import make_server


DESKTOP_DATA_DIR = ROOT / ".cache" / "local_web_desktop"
NATIVE_WINDOW = Path(__file__).with_name("native_webview.swift")


def load_local_credentials(env_file: Path = ROOT / "src" / ".env") -> None:
    """Read only the credentials used by the local study server."""

    if not env_file.is_file():
        return
    from dotenv import dotenv_values

    values = dotenv_values(env_file)
    for key in ("NSRDB_API_KEY", "NSRDB_API_EMAIL", "ELECTRICITY_MAPS_API_KEY"):
        if values.get(key):
            os.environ.setdefault(key, values[key])


def open_native_window(url: str) -> None:
    """Show the shared local form in a macOS WebKit window."""

    if sys.platform != "darwin":
        raise RuntimeError("The native desktop window currently requires macOS.")
    module_cache = Path(tempfile.gettempdir()) / "microgrid-swift-module-cache"
    module_cache.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["CLANG_MODULE_CACHE_PATH"] = str(module_cache)
    environment["SWIFT_MODULE_CACHE_PATH"] = str(module_cache)
    with tempfile.TemporaryDirectory(prefix="microgrid-desktop-") as temporary:
        bundle = Path(temporary) / "Microgrid Simulator.app" / "Contents"
        executable = bundle / "MacOS" / "MicrogridSimulator"
        executable.parent.mkdir(parents=True)
        (bundle / "Info.plist").write_bytes(plistlib.dumps({
            "CFBundleExecutable": executable.name,
            "CFBundleIdentifier": "org.microgrid.simulator.desktop",
            "CFBundleName": "Microgrid Simulator",
            "CFBundlePackageType": "APPL",
            "NSHighResolutionCapable": True,
        }))
        subprocess.run(["/usr/bin/swiftc", "-o", str(executable), str(NATIVE_WINDOW)],
                       check=True, env=environment)
        subprocess.run([str(executable), url], check=True, env=environment)


def run_desktop_application(
    *,
    data_dir: Path = DESKTOP_DATA_DIR,
    refresh_engine: bool = True,
    env_file: Path = ROOT / "src" / ".env",
) -> None:
    """Own the local server for exactly the lifetime of the desktop window."""

    load_local_credentials(env_file)
    application = Application(data_dir, refresh=refresh_engine, embedded_worker=True)
    try:
        server = make_server(application, port=0)
    except BaseException:
        application.close()
        raise

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    try:
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"Microgrid Simulator desktop: {url}", flush=True)
        try:
            open_native_window(url)
        except KeyboardInterrupt:
            pass
    finally:
        if thread.is_alive():
            server.shutdown()
        server.server_close()
        thread.join()
        application.close()
