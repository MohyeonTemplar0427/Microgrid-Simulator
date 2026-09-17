"""Run the simulation queue independently of the local web/API server."""
import argparse
from pathlib import Path
import signal
import threading

from .runtime import JobRunner, ROOT, Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "local_web")
    args = parser.parse_args()
    stopped = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stopped.set())
    runner = JobRunner(Store(args.data_dir))
    print(f"Simulation worker connected: {runner.store.directory}", flush=True)
    try:
        while not stopped.wait(.5):
            if not runner.thread.is_alive():
                raise RuntimeError("Simulation queue consumer stopped unexpectedly.")
    finally:
        runner.close()


if __name__ == "__main__":
    main()
