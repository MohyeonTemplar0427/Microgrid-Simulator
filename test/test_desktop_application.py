"""The desktop shell must use and clean up the shared local study service."""

from unittest.mock import Mock

from src.simulation import desktop_application


def test_desktop_uses_shared_study_server_and_closes_it(monkeypatch, tmp_path):
    application = Mock()
    server = Mock(server_port=43210)
    server.serve_forever = lambda: None
    opened = []
    created = []

    monkeypatch.setattr(desktop_application, "Application", lambda *args, **kwargs: created.append((args, kwargs)) or application)
    monkeypatch.setattr(desktop_application, "make_server", lambda app, port: server if app is application and port == 0 else None)
    monkeypatch.setattr(desktop_application, "open_native_window", opened.append)
    monkeypatch.setattr(desktop_application, "load_local_credentials", lambda path: None)

    desktop_application.run_desktop_application(data_dir=tmp_path, env_file=tmp_path / "none")

    assert created == [((tmp_path,), {"refresh": True, "embedded_worker": True})]
    assert opened == ["http://127.0.0.1:43210/"]
    server.server_close.assert_called_once()
    application.close.assert_called_once()


def test_desktop_closes_service_when_window_fails(monkeypatch, tmp_path):
    application = Mock()
    server = Mock(server_port=43210)
    server.serve_forever = lambda: None
    monkeypatch.setattr(desktop_application, "Application", lambda *args, **kwargs: application)
    monkeypatch.setattr(desktop_application, "make_server", lambda *args, **kwargs: server)
    monkeypatch.setattr(desktop_application, "load_local_credentials", lambda path: None)
    monkeypatch.setattr(desktop_application, "open_native_window", lambda url: (_ for _ in ()).throw(RuntimeError("window failed")))

    import pytest
    with pytest.raises(RuntimeError, match="window failed"):
        desktop_application.run_desktop_application(data_dir=tmp_path, env_file=tmp_path / "none")

    server.server_close.assert_called_once()
    application.close.assert_called_once()


def test_desktop_only_loads_allowed_local_credentials(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("NSRDB_API_KEY=test-weather-key\nUNRELATED_SECRET=do-not-load\n")
    monkeypatch.delenv("NSRDB_API_KEY", raising=False)
    monkeypatch.delenv("UNRELATED_SECRET", raising=False)

    desktop_application.load_local_credentials(env_file)

    import os
    assert os.environ["NSRDB_API_KEY"] == "test-weather-key"
    assert "UNRELATED_SECRET" not in os.environ
