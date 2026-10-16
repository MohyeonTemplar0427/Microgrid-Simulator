"""Launch the shared desktop study interface or the legacy Tkinter workflow."""

import signal


def main() -> None:
    """Launch the shared desktop study UI, or the previous Tkinter workflow."""

    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Launch the Microgrid Simulator desktop application.")
    parser.add_argument("--legacy", action="store_true", help="Open the previous engineering-focused Tkinter GUI.")
    args = parser.parse_args()
    if not args.legacy and sys.platform == "darwin":
        from .desktop_application import run_desktop_application

        run_desktop_application()
        return

    from .application_interface import (
        create_guided_application_window,
    )

    window = create_guided_application_window()
    application = window.microgrid_application
    print("\nSimulator window is open....")

    def close_on_interrupt(_signal_number, _frame) -> None:
        application._close_application()

    previous_sigint_handler = signal.signal(
        signal.SIGINT,
        close_on_interrupt,
    )
    try:
        window.mainloop()
    finally:
        application._close_application()
        signal.signal(signal.SIGINT, previous_sigint_handler)


if __name__ == "__main__":
    main()
