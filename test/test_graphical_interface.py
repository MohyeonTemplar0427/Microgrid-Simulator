"""The desktop entry point must preserve native and legacy launch behavior."""

import signal
import sys
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from src.simulation import graphical_interface


@pytest.fixture
def legacy_window(monkeypatch):
    window = Mock()
    create_window = Mock(return_value=window)
    monkeypatch.setitem(
        sys.modules,
        "src.simulation.application_interface",
        SimpleNamespace(create_guided_application_window=create_window),
    )
    previous_handler = object()
    install_handler = Mock(return_value=previous_handler)
    monkeypatch.setattr(graphical_interface.signal, "signal", install_handler)
    return window, create_window, install_handler, previous_handler


def test_macos_default_opens_shared_desktop_without_legacy_window(monkeypatch, legacy_window):
    run_desktop = Mock()
    monkeypatch.setitem(
        sys.modules,
        "src.simulation.desktop_application",
        SimpleNamespace(run_desktop_application=run_desktop),
    )
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "argv", ["microgrid"])

    graphical_interface.main()

    run_desktop.assert_called_once_with()
    legacy_window[1].assert_not_called()
    legacy_window[2].assert_not_called()


@pytest.mark.parametrize(
    ("platform", "arguments"),
    [("darwin", ["--legacy"]), ("linux", []), ("linux", ["--legacy"])],
)
def test_legacy_or_non_macos_launch_restores_interrupt_handler(
    monkeypatch, legacy_window, platform, arguments,
):
    window, create_window, install_handler, previous_handler = legacy_window
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(sys, "argv", ["microgrid", *arguments])

    graphical_interface.main()

    create_window.assert_called_once_with()
    window.mainloop.assert_called_once_with()
    window.microgrid_application._close_application.assert_called_once_with()
    assert install_handler.call_count == 2
    assert install_handler.call_args_list[0].args[0] == signal.SIGINT
    assert callable(install_handler.call_args_list[0].args[1])
    assert install_handler.call_args_list[1] == call(signal.SIGINT, previous_handler)


def test_legacy_window_failure_still_closes_application_and_restores_handler(
    monkeypatch, legacy_window,
):
    window, _, install_handler, previous_handler = legacy_window
    window.mainloop.side_effect = RuntimeError("window failed")
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "argv", ["microgrid", "--legacy"])

    with pytest.raises(RuntimeError, match="window failed"):
        graphical_interface.main()

    window.microgrid_application._close_application.assert_called_once_with()
    assert install_handler.call_args == call(signal.SIGINT, previous_handler)
