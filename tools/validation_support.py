"""Small, offline-only helpers shared by validation commands."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import uuid


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def value_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(value, indent=2, allow_nan=False, default=str) + "\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def positive_seconds(value):
    if isinstance(value, bool):
        raise ValueError("Timeout must be finite and positive.")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("Timeout must be finite and positive.")
    return number


@contextmanager
def output_lock(directory, name):
    """OS-owned locks release on interruption; never delete another run's lock."""
    import fcntl
    path = Path(directory) / name
    with path.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another validation command is using this output directory.") from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
