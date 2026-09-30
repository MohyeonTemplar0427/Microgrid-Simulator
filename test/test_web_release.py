"""A host release is prepared only against an idle, compatible study store."""

import fcntl
import os
import subprocess
import sys

from src.local_web.runtime import ROOT


def test_release_preparation_pins_engine_and_refuses_live_worker(tmp_path):
    directory = tmp_path / "studies"
    environment = os.environ.copy()
    for key in list(environment):
        if key.startswith("MICROGRID_OIDC_") or key in {"MICROGRID_AUTH_MODE", "MICROGRID_PUBLIC_ORIGIN"}:
            environment.pop(key)
    command = [sys.executable, "-m", "tools.prepare_web_release", "--data-dir", str(directory)]
    first = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=120)
    assert first.returncode == 0, first.stderr
    assert (directory / "engine.json").is_file()
    second = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=120)
    assert second.returncode == 0, second.stderr
    settings = tmp_path / "api.env"
    settings.write_text("MICROGRID_PUBLIC_ORIGIN=https://microgrid.example.com\n"
                        "MICROGRID_AUTH_MODE=oidc\n"
                        "MICROGRID_OIDC_ISSUER=https://accounts.example.com\n"
                        "MICROGRID_OIDC_CLIENT_ID=client\n"
                        "MICROGRID_OIDC_CLIENT_SECRET=secret\n"
                        "MICROGRID_OIDC_REDIRECT_URI=https://microgrid.example.com/auth/callback\n")
    hosted = subprocess.run([*command, "--hosted", "--env-file", str(settings)],
                            cwd=ROOT, env={**environment, "MICROGRID_PUBLIC_ORIGIN": "https://wrong.example.com"},
                            capture_output=True, text=True, timeout=120)
    assert hosted.returncode == 0, hosted.stderr
    with (directory / "worker.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        blocked = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=120)
    assert blocked.returncode != 0
    assert "Stop the simulation worker" in blocked.stderr
