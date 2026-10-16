"""Provider credential boundaries, using fake files and no external services."""
import importlib
import os
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import Mock

import pytest

from src import credentials


ROOT = Path(__file__).resolve().parents[1]
PROVIDER_NAMES = credentials.LOCAL_STUDY_CREDENTIALS + credentials.MARKET_CREDENTIALS
UNRELATED_NAMES = ("MYSQL_PASSWORD", "MICROGRID_OIDC_CLIENT_SECRET", "UNRELATED_SECRET")


@pytest.fixture(autouse=True)
def isolated_credentials(monkeypatch):
    for name in PROVIDER_NAMES + UNRELATED_NAMES:
        # Record initially absent names too, so values loaded by the helper
        # cannot leak into another test when monkeypatch restores the process.
        monkeypatch.setenv(name, os.environ.get(name, ""))
        monkeypatch.delenv(name)

    def no_network(*args, **kwargs):
        raise AssertionError("Credential tests must not access the network.")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)


@pytest.fixture
def env_file(tmp_path):
    path = tmp_path / "credentials.env"
    path.write_text("\n".join(f"{name}=file-{name}" for name in PROVIDER_NAMES + UNRELATED_NAMES))
    return path


@pytest.mark.parametrize("names", [credentials.WEATHER_CREDENTIALS,
    credentials.CARBON_CREDENTIALS, credentials.LOCAL_STUDY_CREDENTIALS,
    credentials.SIGNAL_CREDENTIALS])
def test_only_selected_provider_credentials_are_loaded(env_file, names):
    credentials.load_credentials(env_file, names=names)
    for name in PROVIDER_NAMES + UNRELATED_NAMES:
        assert os.getenv(name) == (f"file-{name}" if name in names else None)


def test_environment_wins_including_empty_values_and_interpolation(monkeypatch, tmp_path):
    path = tmp_path / ".env"
    path.write_text('NSRDB_API_KEY=file-key\nNSRDB_API_EMAIL="${NSRDB_API_KEY}@example.test"\n'
                    'ELECTRICITY_MAPS_API_KEY=file-carbon\n')
    monkeypatch.setenv("NSRDB_API_KEY", "process-key")
    monkeypatch.setenv("ELECTRICITY_MAPS_API_KEY", "")
    credentials.load_credentials(path, names=credentials.LOCAL_STUDY_CREDENTIALS)
    assert os.environ["NSRDB_API_KEY"] == "process-key"
    assert os.environ["NSRDB_API_EMAIL"] == "process-key@example.test"
    assert os.environ["ELECTRICITY_MAPS_API_KEY"] == ""


@pytest.mark.parametrize("use_none", [False, True])
def test_missing_or_disabled_file_does_not_discover_parent_dotenv(tmp_path, monkeypatch, use_none):
    (tmp_path / ".env").write_text("NSRDB_API_KEY=must-not-discover")
    monkeypatch.chdir(tmp_path)
    credentials.load_credentials(None if use_none else tmp_path / "missing", names=credentials.WEATHER_CREDENTIALS)
    assert "NSRDB_API_KEY" not in os.environ


def test_empty_or_unassigned_file_values_remain_missing(tmp_path):
    path = tmp_path / ".env"
    path.write_text('NSRDB_API_KEY=\nNSRDB_API_EMAIL\nELECTRICITY_MAPS_API_KEY=""\n')
    credentials.load_credentials(path, names=credentials.LOCAL_STUDY_CREDENTIALS)
    assert not set(credentials.LOCAL_STUDY_CREDENTIALS).intersection(os.environ)


def test_configured_environment_needs_no_file_read(env_file, monkeypatch):
    for name in credentials.LOCAL_STUDY_CREDENTIALS:
        monkeypatch.setenv(name, "already-configured")
    monkeypatch.setattr("dotenv.main.DotEnv.dict", Mock(side_effect=AssertionError("Unexpected dotenv read")))
    credentials.load_credentials(env_file, names=credentials.LOCAL_STUDY_CREDENTIALS)


def test_unsupported_credential_name_rejects_before_reading(env_file, monkeypatch):
    monkeypatch.setattr("dotenv.main.DotEnv.dict", Mock(side_effect=AssertionError("Unexpected dotenv read")))
    with pytest.raises(ValueError, match="Only supported provider"):
        credentials.load_credentials(env_file, names=("MYSQL_PASSWORD",))


def test_unreadable_file_error_does_not_disclose_contents(tmp_path):
    path = tmp_path / ".env"
    path.write_bytes(b"NSRDB_API_KEY=private-test-value\xff")
    with pytest.raises(ValueError, match="Could not read the provider credential file") as error:
        credentials.load_credentials(path, names=credentials.WEATHER_CREDENTIALS)
    assert "private-test-value" not in str(error.value)


@pytest.mark.parametrize("module", [
    "src.credentials", "src.profiles.nsrdb",
    "src.signal_pipeline.electricity_maps_data", "src.signal_pipeline.market_data_integration",
    "src.simulation.desktop_application", "src.local_web.server", "src.local_web.runner",
    "tools.run_comed_year_validation",
])
def test_imports_do_not_read_dotenv_or_capture_credentials(module):
    # Fresh interpreters catch import-time reads even when pytest has already
    # imported these modules. Block sockets and dotenv itself, not real keys.
    code = '''
import importlib, os, socket, sys
from unittest.mock import patch
def refuse(*args, **kwargs):
    raise AssertionError("Unexpected I/O during import")
before = dict(os.environ)
with patch("dotenv.main.DotEnv.dict", refuse), patch("dotenv.load_dotenv", refuse), \
     patch.object(socket.socket, "connect", refuse), patch.object(socket, "create_connection", refuse):
    module = importlib.import_module(sys.argv[1])
assert not hasattr(module, "api_key"), "Do not snapshot a provider key at import time"
for name in ("NSRDB_API_KEY", "NSRDB_API_EMAIL", "ELECTRICITY_MAPS_API_KEY", "PJM_API_KEY", "GRIDSTATUS_API_KEY"):
    assert os.environ.get(name) == before.get(name)
'''
    result = subprocess.run([sys.executable, "-c", code, module], cwd=ROOT,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_nsrdb_file_support_is_weather_only_and_explicit_arguments_win(env_file, monkeypatch):
    from src.profiles import nsrdb
    monkeypatch.setattr(nsrdb, "ENV_PATH", env_file)
    assert nsrdb._credentials("explicit-key", None) == ("explicit-key", "file-NSRDB_API_EMAIL")
    assert not set(credentials.CARBON_CREDENTIALS + credentials.MARKET_CREDENTIALS + UNRELATED_NAMES).intersection(os.environ)


def test_worker_environment_keeps_provider_keys_and_excludes_auth_database(env_file, monkeypatch):
    from src.local_web.privacy import redact, worker_environment
    credentials.load_credentials(env_file, names=credentials.LOCAL_STUDY_CREDENTIALS)
    monkeypatch.setenv("MICROGRID_OIDC_CLIENT_SECRET", "parent-auth-only")
    monkeypatch.setenv("MYSQL_PASSWORD", "parent-database-only")
    child = worker_environment()
    assert all(child[name] == f"file-{name}" for name in credentials.LOCAL_STUDY_CREDENTIALS)
    assert not any(name.startswith(("MICROGRID_OIDC_", "MYSQL_")) for name in child)
    assert os.environ["MICROGRID_OIDC_CLIENT_SECRET"] == "parent-auth-only"
    assert redact("file-NSRDB_API_KEY parent-auth-only parent-database-only") == "[redacted] [redacted] [redacted]"


class StopBeforeWork(Exception):
    pass


@pytest.mark.parametrize("module_name", ["src.signal_pipeline.market_data_integration", "src.dispatch.scenario_generation"])
def test_market_cli_reads_current_environment_at_execution(module_name, monkeypatch):
    module = importlib.import_module(module_name)
    monkeypatch.setattr(module, "load_credentials", lambda **kwargs: None)
    monkeypatch.setenv("ELECTRICITY_MAPS_API_KEY", "set-after-import")

    def intercept(config, api_key):
        assert api_key == "set-after-import"
        raise StopBeforeWork

    monkeypatch.setattr(module, "prepare_experiment_data", intercept)
    with pytest.raises(StopBeforeWork):
        module.main()


@pytest.mark.parametrize("entry_point,expected_names", [
    ("server", credentials.LOCAL_STUDY_CREDENTIALS),
    ("runner", credentials.CARBON_CREDENTIALS),
    ("desktop", credentials.LOCAL_STUDY_CREDENTIALS),
    ("comed", credentials.WEATHER_CREDENTIALS),
])
def test_launchers_use_the_shared_scopes(env_file, monkeypatch, tmp_path, entry_point, expected_names):
    def stop(*args, **kwargs):
        for name in PROVIDER_NAMES + UNRELATED_NAMES:
            assert os.getenv(name) == (f"file-{name}" if name in expected_names else None)
        raise StopBeforeWork

    argv = [entry_point, "--env-file", str(env_file)]
    if entry_point == "server":
        from src.local_web import server as module
        monkeypatch.setattr(module.OIDCConfig, "from_environment", lambda: None)
        monkeypatch.setattr("src.local_web.hosting.public_origin_from_environment", lambda *args: None)
        monkeypatch.setattr(module, "Application", stop)
    elif entry_point == "runner":
        from src.local_web import runner as module
        monkeypatch.setattr(module.signal, "signal", lambda *args: None)
        monkeypatch.setattr(module, "Store", stop)
    elif entry_point == "desktop":
        from src.simulation import desktop_application as module
        monkeypatch.setattr(module, "Application", stop)
        with pytest.raises(StopBeforeWork):
            module.run_desktop_application(data_dir=tmp_path, env_file=env_file)
        return
    else:
        from tools import run_comed_year_validation as module
        argv += ["--historical-inputs", str(tmp_path)]
        monkeypatch.setattr(module, "Application", stop)
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(StopBeforeWork):
        module.main()


def test_runner_remains_environment_only_without_env_file(monkeypatch, tmp_path):
    from src.local_web import runner
    monkeypatch.setenv("ELECTRICITY_MAPS_API_KEY", "process-carbon")
    monkeypatch.setattr(sys, "argv", ["runner", "--data-dir", str(tmp_path)])
    monkeypatch.setattr(runner.signal, "signal", lambda *args: None)
    monkeypatch.setattr("dotenv.main.DotEnv.dict", Mock(side_effect=AssertionError("Unexpected dotenv read")))
    monkeypatch.setattr(runner, "Store", Mock(side_effect=StopBeforeWork))
    with pytest.raises(StopBeforeWork):
        runner.main()
    assert os.environ["ELECTRICITY_MAPS_API_KEY"] == "process-carbon"
