"""Local persistence, explicit engine snapshots, and a single process-isolated worker."""

import csv
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import importlib.metadata
import io
import json
import math
import os
import signal
import time
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import threading
import uuid

from .contract import validate_request
from .worker import write_json
from .privacy import redact, worker_environment

ROOT = Path(__file__).resolve().parents[2]


class CapacityError(Exception):
    """A bounded server resource is currently unavailable."""

    def __init__(self, message, retry_after=30):
        super().__init__(message)
        self.retry_after = retry_after


class StudyConflict(Exception):
    """The requested study transition is no longer available."""


class StudyCancelled(Exception):
    """The worker observed a user-requested cancellation."""


class RunStorageExceeded(Exception):
    """A worker filled its saved-result allowance or the host's free-space reserve."""


BOOTSTRAP = "import sys; sys.path.insert(0, sys.argv.pop(1)); from src.local_web.worker import main; main()"


def now():
    return datetime.now(timezone.utc).isoformat()


def is_guest(owner_id):
    return isinstance(owner_id, str) and owner_id.startswith("guest:")


def dependencies():
    return {name: importlib.metadata.version(name) for name in (
        "numpy", "pandas", "cvxpy", "OpenDSSDirect.py", "dss-python", "dss-python-backend",
        "pvlib", "scipy", "clarabel", "scs", "osqp", "gridstatus", "python-dotenv",
    )}


def snapshot(root, storage, refresh=False):
    """Pin source bytes explicitly; never import an evolving checkout in workers."""
    pointer = storage / "engine.json"
    if pointer.exists() and not refresh:
        manifest = json.loads(pointer.read_text())
        if manifest["dependencies"] != dependencies() or manifest["python"] != sys.version:
            raise ValueError("Engine dependencies changed. Restore them or explicitly refresh the development snapshot with --refresh-engine.")
        verify_snapshot(storage, manifest)
        return manifest
    files = {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted((root / "src").rglob("*.py"))}
    hashes = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
    if any((root / name).read_bytes() != content for name, content in files.items()):
        raise ValueError("Source changed while creating the engine snapshot; retry after the edit finishes.")
    identity = {"files": hashes, "dependencies": dependencies(), "python": sys.version}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    destination = storage / "engines" / digest
    destination.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    manifest = {**identity, "id": digest, "created_at": now(), "kind": "local-development-snapshot"}
    write_json(destination / "manifest.json", manifest)
    write_json(pointer, manifest)
    return manifest


def verify_snapshot(storage, manifest):
    destination = storage / "engines" / manifest["id"]
    for name, expected in manifest["files"].items():
        if hashlib.sha256((destination / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Saved engine snapshot was modified; refusing to run it.")


def command(storage, engine_id, argument):
    return [sys.executable, "-I", "-B", "-c", BOOTSTRAP,
            str(storage / "engines" / engine_id), str(argument)]


def inspect_csv(content):
    """Check uploads without importing the simulation engine in the web service."""
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)):
            raise ValueError("CSV contains duplicate column names.")
        alternatives = (("native_load_kw", "load_kw"), ("pv_available_kw", "pv_kw"),
                        ("carbon_intensity_g_per_kWh", "gCO2/kWh"), ("price_per_kWh",))
        required = []
        for choices in alternatives:
            present = [c for c in choices if c in fields]
            if not present:
                raise ValueError(f"CSV is missing {choices[0]} (accepted names: {', '.join(choices)}).")
            required.extend(present)
        previous = first = last = None
        count, step = 0, None
        for count, row in enumerate(reader, 1):
            if count > 110000:
                raise ValueError("CSV is limited to 110,000 intervals.")
            timestamp = datetime.fromisoformat(row["timestamp"])
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise ValueError("CSV timestamps must include a UTC offset, for example 2026-08-01T00:00:00-07:00.")
            instant = timestamp.astimezone(timezone.utc)
            if previous is not None:
                delta = (instant - previous).total_seconds()
                if delta <= 0:
                    raise ValueError("CSV timestamps must be unique and increasing by instant.")
                if step is None:
                    step = delta
                elif step != delta:
                    raise ValueError("CSV intervals must be evenly spaced; missing intervals are rejected.")
            for column in required:
                value = float(row[column])
                if not math.isfinite(value) or (column != "price_per_kWh" and value < 0):
                    raise ValueError(f"Invalid finite value in {column} at CSV row {count + 1}.")
            for canonical, legacy in alternatives[:3]:
                if canonical in fields and legacy in fields and float(row[canonical]) != float(row[legacy]):
                    raise ValueError(f"Conflicting {canonical} and {legacy} values at CSV row {count + 1}.")
            first = first or timestamp
            last, previous = timestamp, instant
        if count < 2:
            raise ValueError("CSV must contain at least two intervals.")
        return {"row_count": count, "start": first.isoformat(), "end": last.isoformat(),
                "timestep_minutes": step / 60}
    except (KeyError, TypeError, UnicodeError, csv.Error) as exc:
        raise ValueError("Use a UTF-8 CSV with timestamp, load, PV, price, and carbon columns.") from exc


class Store:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.database = self.directory / "studies.sqlite3"
        self.max_pending = self._limit("MICROGRID_MAX_PENDING_STUDIES", 20)
        self.max_per_user = self._limit("MICROGRID_MAX_PENDING_PER_USER", 3)
        self.daily_study_limit = self._limit("MICROGRID_DAILY_STUDY_LIMIT", 200)
        self.guest_daily_limit = self._limit("MICROGRID_GUEST_DAILY_STUDY_LIMIT", 2)
        self.guest_global_daily_limit = self._limit("MICROGRID_GUEST_GLOBAL_DAILY_LIMIT", 20)
        self.guest_session_limit = self._limit("MICROGRID_GUEST_DAILY_SESSION_LIMIT", 100)
        self.guest_interaction_limit = self._limit("MICROGRID_GUEST_DAILY_INTERACTION_LIMIT", 20)
        self.guest_global_interaction_limit = self._limit("MICROGRID_GUEST_GLOBAL_DAILY_INTERACTION_LIMIT", 100)
        self.temp_result_hours = self._limit("MICROGRID_TEMP_RESULT_HOURS", 24, 168)
        self.max_upload_bytes = self._limit("MICROGRID_MAX_UPLOAD_BYTES", 16 * 1024 * 1024, 1 << 40)
        self.max_owner_dataset_bytes = self._limit("MICROGRID_MAX_OWNER_DATASET_BYTES", 100 * 1024 * 1024, 1 << 40)
        self.max_dataset_store_bytes = self._limit("MICROGRID_MAX_DATASET_STORE_BYTES", 1024 * 1024 * 1024, 1 << 40)
        self.max_run_bytes = self._limit("MICROGRID_MAX_RUN_BYTES", 2 * (1 << 30), 1 << 40)
        self.max_owner_run_bytes = self._limit("MICROGRID_MAX_OWNER_RUN_BYTES", 8 * (1 << 30), 1 << 40)
        self.max_run_store_bytes = self._limit("MICROGRID_MAX_RUN_STORE_BYTES", 32 * (1 << 30), 1 << 40)
        self.max_weather_bytes = self._limit("MICROGRID_MAX_WEATHER_BYTES", 64 * (1 << 20), 1 << 40)
        self.max_owner_weather_bytes = self._limit("MICROGRID_MAX_OWNER_WEATHER_BYTES", 256 * (1 << 20), 1 << 40)
        self.max_weather_store_bytes = self._limit("MICROGRID_MAX_WEATHER_STORE_BYTES", 2 * (1 << 30), 1 << 40)
        self.min_free_bytes = self._limit("MICROGRID_MIN_FREE_BYTES", 2 * (1 << 30), 1 << 40)
        if self.max_per_user > self.max_pending:
            raise ValueError("Per-user pending limit cannot exceed the server pending limit.")
        if self.max_owner_run_bytes < self.max_run_bytes:
            raise ValueError("MICROGRID_MAX_OWNER_RUN_BYTES must be at least MICROGRID_MAX_RUN_BYTES.")
        if self.max_run_store_bytes < self.max_run_bytes:
            raise ValueError("MICROGRID_MAX_RUN_STORE_BYTES must be at least MICROGRID_MAX_RUN_BYTES.")
        if self.max_owner_weather_bytes < self.max_weather_bytes:
            raise ValueError("MICROGRID_MAX_OWNER_WEATHER_BYTES must be at least MICROGRID_MAX_WEATHER_BYTES.")
        if self.max_weather_store_bytes < self.max_weather_bytes:
            raise ValueError("MICROGRID_MAX_WEATHER_STORE_BYTES must be at least MICROGRID_MAX_WEATHER_BYTES.")
        for name in ("datasets", "runs", "engines", "weather", "locations"):
            (self.directory / name).mkdir(exist_ok=True)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""CREATE TABLE IF NOT EXISTS studies (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL,
                created_at TEXT NOT NULL, finished_at TEXT, engine_id TEXT NOT NULL,
                error TEXT, started_at TEXT, runtime_seconds REAL)""")
            columns = {r[1] for r in db.execute("PRAGMA table_info(studies)")}
            if "owner_id" not in columns:
                db.execute("ALTER TABLE studies ADD COLUMN owner_id TEXT")
            if "started_at" not in columns:
                db.execute("ALTER TABLE studies ADD COLUMN started_at TEXT")
            if "runtime_seconds" not in columns:
                db.execute("ALTER TABLE studies ADD COLUMN runtime_seconds REAL")
            if "saved" not in columns:
                db.execute("ALTER TABLE studies ADD COLUMN saved INTEGER NOT NULL DEFAULT 1")
            if "expires_at" not in columns:
                db.execute("ALTER TABLE studies ADD COLUMN expires_at TEXT")
            if "guest_origin_owner" not in columns:
                db.execute("ALTER TABLE studies ADD COLUMN guest_origin_owner TEXT")
            if "deleted_at" not in columns:
                db.execute("ALTER TABLE studies ADD COLUMN deleted_at TEXT")
            db.execute("CREATE INDEX IF NOT EXISTS studies_owner ON studies(owner_id, created_at)")
            db.execute("""CREATE TABLE IF NOT EXISTS resource_owners (
                kind TEXT NOT NULL, id TEXT NOT NULL, owner_id TEXT NOT NULL, metadata TEXT,
                PRIMARY KEY(kind, id, owner_id))""")
            db.execute("CREATE TABLE IF NOT EXISTS guest_created_datasets (id TEXT PRIMARY KEY)")
            db.execute("""CREATE TABLE IF NOT EXISTS guest_interactions (
                id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, created_at TEXT NOT NULL)""")
            db.execute("CREATE INDEX IF NOT EXISTS guest_interactions_day ON guest_interactions(created_at)")
            db.execute("""CREATE TABLE IF NOT EXISTS orientation_usage (
                id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, started_at TEXT NOT NULL,
                duration_seconds REAL)""")
            db.execute("CREATE INDEX IF NOT EXISTS orientation_usage_owner ON orientation_usage(owner_id, started_at)")

    @staticmethod
    def _limit(name, default, maximum=1000):
        try:
            value = int(os.environ.get(name, str(default)))
        except ValueError:
            raise ValueError(f"{name} must be an integer from 1 to {maximum}.") from None
        if not 1 <= value <= maximum:
            raise ValueError(f"{name} must be an integer from 1 to {maximum}.")
        return value

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def grant(self, kind, resource_id, owner_id, metadata=None):
        if owner_id is not None:
            with self.connect() as db:
                db.execute("INSERT OR REPLACE INTO resource_owners VALUES (?, ?, ?, ?)",
                           (kind, resource_id, owner_id, json.dumps(metadata)))

    def require_resource(self, kind, resource_id, owner_id):
        # None is reserved for trusted local/worker calls, never an authenticated user.
        if owner_id is not None:
            with self.connect() as db:
                found = db.execute("SELECT 1 FROM resource_owners WHERE kind=? AND id=? AND owner_id=?",
                                   (kind, resource_id, owner_id)).fetchone()
            if found is None:
                raise FileNotFoundError("Resource not found.")

    def add_dataset(self, content, name, owner_id=None):
        if len(content) > self.max_upload_bytes:
            raise CapacityError("CSV upload exceeds the per-file size limit. Choose a smaller file.", None)
        metadata = inspect_csv(content)
        digest = hashlib.sha256(content).hexdigest()
        metadata.update(id=digest, name=Path(name).name[:120], size_bytes=len(content))
        target = self.directory / "datasets" / digest
        csv_path = target.with_suffix(".csv")
        metadata_path = target.with_suffix(".json")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if owner_id is not None:
                owned = {row[0] for row in db.execute(
                    "SELECT id FROM resource_owners WHERE kind='dataset' AND owner_id=?", (owner_id,))}
                if digest not in owned:
                    total = sum((self.directory / "datasets" / f"{key}.csv").stat().st_size
                                for key in owned if (self.directory / "datasets" / f"{key}.csv").is_file())
                    if total + len(content) > self.max_owner_dataset_bytes:
                        raise CapacityError("Your saved CSV upload quota is full. Contact the site administrator.", None)
            if not csv_path.is_file():
                total = sum(path.stat().st_size for path in (self.directory / "datasets").glob("*.csv"))
                if total + len(content) > self.max_dataset_store_bytes:
                    raise CapacityError("The server's CSV upload storage is full. Contact the site administrator.", None)
                self._require_free_space(len(content) + self._active_run_headroom(db))
                temporary = self.directory / "datasets" / f".{digest}.{uuid.uuid4().hex}.tmp"
                try:
                    temporary.write_bytes(content)
                    temporary.replace(csv_path)
                finally:
                    temporary.unlink(missing_ok=True)
                if is_guest(owner_id):
                    db.execute("INSERT OR IGNORE INTO guest_created_datasets VALUES (?)", (digest,))
            if not metadata_path.is_file():
                write_json(metadata_path, metadata)
            if owner_id is not None:
                db.execute("INSERT OR REPLACE INTO resource_owners VALUES (?, ?, ?, ?)",
                           ("dataset", digest, owner_id, json.dumps(metadata)))
        return metadata if owner_id is not None else json.loads(metadata_path.read_text())

    def datasets(self, owner_id=None):
        if owner_id is not None:
            with self.connect() as db:
                return [json.loads(r[0]) for r in db.execute(
                    "SELECT metadata FROM resource_owners WHERE kind='dataset' AND owner_id=? ORDER BY id", (owner_id,))]
        return [json.loads(p.read_text()) for p in sorted((self.directory / "datasets").glob("*.json"))]

    @staticmethod
    def directory_bytes(directory):
        total = 0
        for root, dirs, files in os.walk(directory, followlinks=False):
            dirs[:] = [name for name in dirs if not (Path(root) / name).is_symlink()]
            for name in files:
                path = Path(root) / name
                try:
                    if not path.is_symlink():
                        total += path.stat().st_size
                except FileNotFoundError:
                    pass  # A finished temp file may disappear during an admission scan.
        return total

    def _require_free_space(self, reserve):
        if shutil.disk_usage(self.directory).free < reserve + self.min_free_bytes:
            raise CapacityError("The study server is low on disk space. Contact the site administrator.", None)

    def _require_run_storage(self, db, owner_id):
        active = {"queued", "running", "cancelling"}
        known, owner_total, server_total, future_bytes = set(), 0, 0, 0
        for row in db.execute("SELECT id, owner_id, status FROM studies"):
            known.add(row["id"])
            actual = self.directory_bytes(self.directory / "runs" / row["id"])
            size = max(self.max_run_bytes, actual) if row["status"] in active else actual
            if row["status"] in active:
                future_bytes += max(0, self.max_run_bytes - actual)
            server_total += size
            if owner_id is not None and row["owner_id"] == owner_id:
                owner_total += size
        for path in (self.directory / "runs").iterdir():
            if path.is_dir() and not path.is_symlink() and path.name not in known:
                server_total += self.directory_bytes(path)
        if owner_id is not None and owner_total + self.max_run_bytes > self.max_owner_run_bytes:
            raise CapacityError("Your saved study storage is full. Contact the site administrator.", None)
        if server_total + self.max_run_bytes > self.max_run_store_bytes:
            raise CapacityError("The server's saved study storage is full. Contact the site administrator.", None)
        self._require_free_space(self.max_run_bytes + future_bytes)

    def _active_run_headroom(self, db):
        return sum(max(0, self.max_run_bytes - self.directory_bytes(self.directory / "runs" / row[0]))
                   for row in db.execute("SELECT id FROM studies WHERE status IN ('queued','running','cancelling')"))

    def require_weather_storage(self, owner_id, resource_id):
        directory = self.directory / "weather"
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            others = [path for path in directory.iterdir() if path.is_dir() and not path.is_symlink() and path.name != resource_id]
            server_total = sum(self.directory_bytes(path) for path in others)
            if server_total + self.max_weather_bytes > self.max_weather_store_bytes:
                raise CapacityError("The server's weather storage is full. Contact the site administrator.", None)
            if owner_id is not None:
                owned = {row[0] for row in db.execute(
                    "SELECT id FROM resource_owners WHERE kind='weather' AND owner_id=?", (owner_id,))}
                owner_total = sum(self.directory_bytes(directory / key) for key in owned if key != resource_id)
                if owner_total + self.max_weather_bytes > self.max_owner_weather_bytes:
                    raise CapacityError("Your saved weather storage is full. Contact the site administrator.", None)
            self._require_free_space(self.max_weather_bytes + self._active_run_headroom(db))

    def _daily_usage(self, db, owner_id, instant):
        day = instant.date().isoformat()
        reset = datetime.combine(instant.date() + timedelta(days=1), datetime.min.time(), timezone.utc)
        submitted = db.execute(
            "SELECT COUNT(*) FROM studies WHERE " +
            ("guest_origin_owner=?" if is_guest(owner_id) else "owner_id=?") +
            " AND substr(created_at,1,10)=?", (owner_id, day)).fetchone()[0]
        used = 0.0
        for table, duration_name, status_name in (
                ("studies", "runtime_seconds", "status"),
                ("orientation_usage", "duration_seconds", None)):
            columns = f"started_at, {duration_name}" + (f", {status_name}" if status_name else "")
            ownership = "guest_origin_owner" if table == "studies" and is_guest(owner_id) else "owner_id"
            rows = db.execute(
                f"SELECT {columns} FROM {table} WHERE {ownership}=? AND substr(started_at,1,10)=?",
                (owner_id, day))
            for row in rows:
                if row[duration_name] is not None:
                    used += row[duration_name]
                elif status_name is None or row[status_name] in ("running", "cancelling"):
                    # An open orientation row is charged conservatively after an API crash.
                    started = datetime.fromisoformat(row["started_at"])
                    used += min(1800.0, max(0.0, (instant - started).total_seconds()))
        return {
            "day_utc": day, "submitted_studies": submitted,
            "study_limit": self.guest_daily_limit if is_guest(owner_id) else self.daily_study_limit,
            "used_seconds": round(used, 3),
            "remaining_studies": max(0, (self.guest_daily_limit if is_guest(owner_id) else self.daily_study_limit) - submitted),
            "resets_at": reset.isoformat(),
        }

    def daily_usage(self, owner_id):
        if owner_id is None:
            return {"enabled": False}
        instant = datetime.fromisoformat(now())
        with self.connect() as db:
            return {"enabled": True, **self._daily_usage(db, owner_id, instant)}

    def _require_daily_capacity(self, db, owner_id, instant):
        if owner_id is None:
            return
        submitted = db.execute(
            "SELECT COUNT(*) FROM studies WHERE " +
            ("guest_origin_owner=?" if is_guest(owner_id) else "owner_id=?") +
            " AND substr(created_at,1,10)=?",
            (owner_id, instant.date().isoformat())).fetchone()[0]
        limit = self.guest_daily_limit if is_guest(owner_id) else self.daily_study_limit
        if is_guest(owner_id):
            global_count = db.execute(
                "SELECT COUNT(*) FROM studies WHERE guest_origin_owner IS NOT NULL AND substr(created_at,1,10)=?",
                (instant.date().isoformat(),)).fetchone()[0]
            if global_count >= self.guest_global_daily_limit:
                raise CapacityError("The temporary-study capacity is full today. Try again after 00:00 UTC.", None)
        if submitted >= limit:
            reset = datetime.combine(instant.date() + timedelta(days=1), datetime.min.time(), timezone.utc)
            wait = max(1, math.ceil((reset - instant).total_seconds()))
            raise CapacityError("Today's study limit is reached. You can submit again after 00:00 UTC.", wait)

    def admit_guest_interaction(self, owner_id):
        if not is_guest(owner_id):
            return
        day = datetime.now(timezone.utc).date().isoformat()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            own = db.execute("SELECT COUNT(*) FROM guest_interactions WHERE owner_id=? AND substr(created_at,1,10)=?",
                             (owner_id, day)).fetchone()[0]
            total = db.execute("SELECT COUNT(*) FROM guest_interactions WHERE substr(created_at,1,10)=?",
                               (day,)).fetchone()[0]
            if own >= self.guest_interaction_limit or total >= self.guest_global_interaction_limit:
                raise CapacityError("The temporary setup lookup limit is reached today. Try again after 00:00 UTC.", None)
            db.execute("INSERT INTO guest_interactions VALUES (?,?,?)", (uuid.uuid4().hex, owner_id, now()))

    def start_orientation(self, owner_id):
        if owner_id is None:
            return None
        event_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            instant = datetime.fromisoformat(now())
            db.execute("INSERT INTO orientation_usage (id,owner_id,started_at) VALUES (?,?,?)",
                       (event_id, owner_id, instant.isoformat()))
        return event_id

    def finish_orientation(self, event_id, duration_seconds):
        if event_id is None:
            return
        if not isinstance(duration_seconds, (int, float)) or not math.isfinite(duration_seconds) or duration_seconds < 0:
            raise ValueError("Orientation duration must be a nonnegative finite number of seconds.")
        with self.connect() as db:
            db.execute("UPDATE orientation_usage SET duration_seconds=? WHERE id=? AND duration_seconds IS NULL",
                       (duration_seconds, event_id))

    def submit(self, request, engine, owner_id=None, *, temporary=False):
        if isinstance(request, dict) and request.get("schema_version") == 7:
            from .pge_annual_study import validate_request as validate_annual
            validate_annual(request)
        else:
            validate_request(request)
        sources = {}
        if request["schema_version"] == 1:
            self.require_resource("dataset", request["dataset_id"], owner_id)
            sources["input.csv"] = self.directory / "datasets" / (request["dataset_id"] + ".csv")
        elif request.get("weather_source") == "nsrdb":
            from .site_inputs import check_weather_matches
            self.require_resource("weather", request["weather_id"], owner_id)
            cached = self.directory / "weather" / request["weather_id"]
            if not (cached / "weather.json").is_file():
                raise ValueError("Retrieve weather for this site before running.")
            check_weather_matches(request, json.loads((cached / "weather.json").read_text()))
            sources = {name: cached / name for name in ("weather.csv", "weather.json")}
        if any(not source.is_file() for source in sources.values()):
            raise ValueError("The selected input is missing. Retrieve or select it first.")
        study_id = uuid.uuid4().hex
        directory = self.directory / "runs" / study_id
        created = False
        try:
            with self.connect() as db:
                # Reserve capacity and publish the queued row in one transaction.
                # The worker cannot claim it until all input files are ready.
                db.execute("BEGIN IMMEDIATE")
                accepted_at = now()
                self._require_daily_capacity(db, owner_id, datetime.fromisoformat(accepted_at))
                pending = db.execute(
                    "SELECT COUNT(*) FROM studies WHERE status IN ('queued', 'running', 'cancelling')").fetchone()[0]
                if pending >= self.max_pending:
                    raise CapacityError("The simulation queue is full. Try again after a study finishes.")
                if owner_id is not None:
                    own = db.execute(
                        "SELECT COUNT(*) FROM studies WHERE owner_id=? AND status IN ('queued', 'running', 'cancelling')",
                        (owner_id,)).fetchone()[0]
                    if own >= self.max_per_user:
                        raise CapacityError("You have reached your active study limit. Try again after a study finishes.")
                self._require_run_storage(db, owner_id)
                directory.mkdir()
                created = True
                for name, source in sources.items():
                    shutil.copyfile(source, directory / name)
                write_json(directory / "request.json", request)
                write_json(directory / "engine.json", engine)
                if self.directory_bytes(directory) > self.max_run_bytes:
                    raise CapacityError("Saved inputs exceed the per-study storage limit. Choose smaller inputs or contact the site administrator.", None)
                db.execute("INSERT INTO studies (id,name,status,created_at,engine_id,owner_id,saved,guest_origin_owner) VALUES (?, ?, 'queued', ?, ?, ?, ?, ?)",
                           (study_id, request["name"].strip(), accepted_at, engine["id"], owner_id,
                            int(not (temporary or is_guest(owner_id))), owner_id if is_guest(owner_id) else None))
        except BaseException:
            if created:
                shutil.rmtree(directory)
            raise
        return self.get(study_id, owner_id)

    def get(self, study_id, owner_id=None):
        with self.connect() as db:
            row = db.execute("SELECT * FROM studies WHERE id = ?", (study_id,)).fetchone()
        if (row is None or row["status"] == "deleted"
                or (owner_id is not None and row["owner_id"] != owner_id)
                or (row is not None and row["expires_at"] is not None and row["expires_at"] <= now())):
            raise FileNotFoundError("Study not found.")
        result = dict(row)
        directory = self.directory / "runs" / study_id
        result["request"] = json.loads((directory / "request.json").read_text())
        progress = directory / "progress.json"
        result["progress"] = (
            "Stopping the simulation…" if result["status"] == "cancelling" else
            "Study cancelled." if result["status"] == "cancelled" else
            json.loads(progress.read_text())["message"] if progress.exists() else result["status"])
        if result["status"] == "completed":
            result["result"] = json.loads((directory / "result.json").read_text())
        return result

    def list(self, owner_id=None):
        with self.connect() as db:
            if owner_id is not None:
                return [dict(row) for row in db.execute("SELECT * FROM studies WHERE owner_id=? AND status!='deleted' AND (expires_at IS NULL OR expires_at>?) ORDER BY created_at DESC LIMIT 100", (owner_id, now()))]
            return [dict(row) for row in db.execute("SELECT * FROM studies WHERE status!='deleted' ORDER BY created_at DESC LIMIT 100")]

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM studies WHERE status = 'queued' ORDER BY created_at LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE studies SET status = 'running', started_at = ? WHERE id = ?",
                           (now(), row["id"]))
        return dict(row) if row else None

    def cancel(self, study_id, owner_id=None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status, owner_id, saved FROM studies WHERE id=?", (study_id,)).fetchone()
            if row is None or row["status"] == "deleted" or (owner_id is not None and row["owner_id"] != owner_id):
                raise FileNotFoundError("Study not found.")
            if row["status"] == "queued":
                finished = datetime.now(timezone.utc)
                expiry = (finished + timedelta(hours=self.temp_result_hours)).isoformat() if not row["saved"] else None
                db.execute("UPDATE studies SET status='cancelled', finished_at=?, expires_at=? WHERE id=?",
                           (finished.isoformat(), expiry, study_id))
            elif row["status"] == "running":
                db.execute("UPDATE studies SET status='cancelling' WHERE id=?", (study_id,))
            elif row["status"] != "cancelling":
                raise StudyConflict("This study has already finished.")
        return self.get(study_id, owner_id)

    def delete_study(self, study_id, owner_id=None):
        """Hide a finished study, then remove its files; retain only short-lived quota accounting."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status, owner_id FROM studies WHERE id=?", (study_id,)).fetchone()
            if row is None or row["status"] == "deleted" or (owner_id is not None and row["owner_id"] != owner_id):
                raise FileNotFoundError("Study not found.")
            if row["status"] in {"queued", "running", "cancelling"}:
                raise StudyConflict("Cancel the study and wait for it to stop before deleting it.")
            db.execute("""UPDATE studies SET name='Deleted study', status='deleted', error=NULL,
                          saved=0, expires_at=NULL, deleted_at=? WHERE id=?""", (now(), study_id))
        directory = self.directory / "runs" / study_id
        try:
            if directory.is_symlink():
                directory.unlink()
            elif directory.exists():
                shutil.rmtree(directory)
        except OSError:
            # The study is already inaccessible. The janitor retries file removal.
            return {"deleted": True, "storage_cleanup_pending": True}
        return {"deleted": True, "storage_cleanup_pending": False}

    def cancellation_requested(self, study_id):
        with self.connect() as db:
            row = db.execute("SELECT status FROM studies WHERE id=?", (study_id,)).fetchone()
        return row is not None and row["status"] == "cancelling"

    def finish(self, study_id, error=None, runtime_seconds=None):
        if runtime_seconds is not None and (
                isinstance(runtime_seconds, bool) or not isinstance(runtime_seconds, (int, float))
                or not math.isfinite(runtime_seconds) or runtime_seconds < 0):
            raise ValueError("Runtime must be a nonnegative finite number of seconds.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status, owner_id, saved FROM studies WHERE id=?", (study_id,)).fetchone()
            if row is None:
                raise FileNotFoundError("Study not found.")
            if row["status"] == "cancelling":
                status, error = "cancelled", None
            elif row["status"] in ("queued", "running"):
                status = "failed" if error else "completed"
            else:
                return row["status"]
            finished = datetime.now(timezone.utc)
            expiry = (finished + timedelta(hours=self.temp_result_hours)).isoformat() if not row["saved"] else None
            db.execute("UPDATE studies SET status=?, error=?, finished_at=?, runtime_seconds=?, expires_at=? WHERE id=?",
                       (status, error, finished.isoformat(), runtime_seconds, expiry, study_id))
            return status

    def save_guest_study(self, study_id, guest_owner, member_owner):
        if not is_guest(guest_owner) or is_guest(member_owner) or member_owner is None:
            raise FileNotFoundError("Study not found.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM studies WHERE id=? AND owner_id=?", (study_id, guest_owner)).fetchone()
            if (row is None or row["status"] != "completed" or row["expires_at"] is None
                    or row["expires_at"] <= now()):
                raise FileNotFoundError("Temporary study not found or no longer available.")
            own = sum(
                max(self.max_run_bytes, self.directory_bytes(self.directory / "runs" / item["id"]))
                if item["status"] in {"queued", "running", "cancelling"}
                else self.directory_bytes(self.directory / "runs" / item["id"])
                for item in db.execute("SELECT id,status FROM studies WHERE owner_id=?", (member_owner,)))
            size = self.directory_bytes(self.directory / "runs" / study_id)
            if own + size > self.max_owner_run_bytes:
                raise CapacityError("Your saved study storage is full. Contact the site administrator.", None)
            request = json.loads((self.directory / "runs" / study_id / "request.json").read_text())
            def ids(value):
                if isinstance(value, dict):
                    for key, child in value.items():
                        if key.endswith("_id") and isinstance(child, str):
                            yield child
                        else:
                            yield from ids(child)
                elif isinstance(value, list):
                    for child in value:
                        yield from ids(child)
            referenced = set(ids(request))
            grants = [resource for resource in db.execute(
                "SELECT kind,id,metadata FROM resource_owners WHERE owner_id=?", (guest_owner,))
                if resource["id"] in referenced]
            already = {(resource["kind"], resource["id"]) for resource in db.execute(
                "SELECT kind,id FROM resource_owners WHERE owner_id=?", (member_owner,))}
            for kind, cap, path_for in (
                    ("dataset", self.max_owner_dataset_bytes,
                     lambda key: self.directory / "datasets" / (key + ".csv")),
                    ("weather", self.max_owner_weather_bytes,
                     lambda key: self.directory / "weather" / key)):
                existing = sum(
                    self.directory_bytes(path_for(key)) if kind == "weather" else path_for(key).stat().st_size
                    for owned_kind, key in already if owned_kind == kind and path_for(key).exists())
                added = sum(
                    self.directory_bytes(path_for(resource["id"])) if kind == "weather" else path_for(resource["id"]).stat().st_size
                    for resource in grants if resource["kind"] == kind
                    and (kind, resource["id"]) not in already and path_for(resource["id"]).exists())
                if existing + added > cap:
                    raise CapacityError("Your profile storage is full. Contact the site administrator.", None)
            db.execute("UPDATE studies SET owner_id=?, saved=1, expires_at=NULL WHERE id=?",
                       (member_owner, study_id))
            for resource in grants:
                db.execute("INSERT OR IGNORE INTO resource_owners VALUES (?,?,?,?)",
                           (resource["kind"], resource["id"], member_owner, resource["metadata"]))
        return self.get(study_id, member_owner)

    def save_member_study(self, study_id, member_owner):
        if member_owner is None or is_guest(member_owner):
            raise FileNotFoundError("Temporary study not found.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status,saved,expires_at FROM studies WHERE id=? AND owner_id=?",
                             (study_id, member_owner)).fetchone()
            if row is None or row["status"] != "completed" or (not row["saved"] and row["expires_at"] <= now()):
                raise FileNotFoundError("Temporary study not found or no longer available.")
            db.execute("UPDATE studies SET saved=1, expires_at=NULL WHERE id=?", (study_id,))
        return self.get(study_id, member_owner)

    def purge_expired_studies(self):
        """Remove deleted/expired studies and abandoned guest resources."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            deleted = list(db.execute("SELECT id,deleted_at FROM studies WHERE status='deleted'"))
            for row in deleted:
                run_directory = self.directory / "runs" / row["id"]
                if run_directory.is_symlink():
                    run_directory.unlink()
                elif run_directory.exists():
                    shutil.rmtree(run_directory)
                if row["deleted_at"] <= (datetime.now(timezone.utc) - timedelta(days=2)).isoformat():
                    db.execute("DELETE FROM studies WHERE id=?", (row["id"],))
            db.execute("DELETE FROM guest_interactions WHERE created_at<?",
                       ((datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),))
            expired = [row[0] for row in db.execute(
                """SELECT id FROM studies WHERE saved=0 AND
                   ((expires_at IS NOT NULL AND expires_at<=?) OR
                    (status='queued' AND created_at<=?))""",
                (now(), (datetime.now(timezone.utc) - timedelta(hours=self.temp_result_hours)).isoformat()))]
            for study_id in expired:
                run_directory = self.directory / "runs" / study_id
                if run_directory.exists():
                    shutil.rmtree(run_directory)
                db.execute("DELETE FROM studies WHERE id=?", (study_id,))
            has_sessions = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='auth_guests'").fetchone()
            if has_sessions:
                expired_owners = [row["owner_id"] for row in db.execute(
                    "SELECT owner_id FROM auth_guests WHERE created<=?", (time.time() - 48 * 3600,))]
                for owner in expired_owners:
                    if db.execute("SELECT 1 FROM studies WHERE owner_id=?", (owner,)).fetchone():
                        continue
                    resources = [(row["kind"], row["id"]) for row in db.execute(
                        "SELECT kind,id FROM resource_owners WHERE owner_id=?", (owner,))]
                    db.execute("DELETE FROM resource_owners WHERE owner_id=?", (owner,))
                    db.execute("DELETE FROM orientation_usage WHERE owner_id=?", (owner,))
                    db.execute("DELETE FROM auth_guests WHERE owner_id=?", (owner,))
                    for kind, resource_id in resources:
                        if db.execute("SELECT 1 FROM resource_owners WHERE kind=? AND id=?",
                                      (kind, resource_id)).fetchone():
                            continue
                        if kind == "dataset" and db.execute(
                                "SELECT 1 FROM guest_created_datasets WHERE id=?", (resource_id,)).fetchone():
                            for suffix in (".csv", ".json"):
                                (self.directory / "datasets" / (resource_id + suffix)).unlink(missing_ok=True)
                            db.execute("DELETE FROM guest_created_datasets WHERE id=?", (resource_id,))
                        elif kind in {"weather", "location", "resolution", "candidate"}:
                            folder = "locations" if kind == "location" else "candidate" if kind in {"resolution", "candidate"} else "weather"
                            resource_directory = self.directory / folder / resource_id
                            if resource_directory.exists():
                                shutil.rmtree(resource_directory)
            utilities = self.directory / "utilities"
            if utilities.exists():
                for cache in utilities.glob("*.json"):
                    if cache.stat().st_mtime < time.time() - 86400:
                        cache.unlink(missing_ok=True)
        return len(expired)


class Application:
    def __init__(self, directory, refresh=False, root=ROOT, *, embedded_worker=True):
        self.store = Store(directory)
        self.lock = (self.store.directory / "server.lock").open("a+")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise ValueError("Another local server is using this study directory.") from None
        try:
            sample_sizes = [(root / "data" / name).stat().st_size for name in (
                "default_small_business_week.csv", "default_microgrid_week.csv")]
            sample_bytes = sum(sample_sizes)
            if self.store.max_upload_bytes < max(sample_sizes):
                raise ValueError("MICROGRID_MAX_UPLOAD_BYTES must fit each built-in sample dataset.")
            if self.store.max_owner_dataset_bytes < sample_bytes:
                raise ValueError("MICROGRID_MAX_OWNER_DATASET_BYTES must fit both built-in sample datasets.")
            if self.store.max_dataset_store_bytes < sample_bytes:
                raise ValueError("MICROGRID_MAX_DATASET_STORE_BYTES must fit both built-in sample datasets.")
            self.engine = snapshot(root, self.store.directory, refresh)
            result = subprocess.run(command(self.store.directory, self.engine["id"], "capabilities"),
                                    capture_output=True, text=True, check=True, timeout=90, env=worker_environment())
            self.capabilities = json.loads(result.stdout)
            self.samples = []
            for name in ("default_small_business_week.csv", "default_microgrid_week.csv"):
                content = (root / "data" / name).read_bytes()
                self.samples.append((content, name))
                self.store.add_dataset(content, name)
        except BaseException:
            self.lock.close()
            raise
        self.resource_lock = threading.Lock()
        self.interactive_slot = threading.BoundedSemaphore(1)
        self.bundle_slot = threading.BoundedSemaphore(1)
        self.last_lookup = 0
        try:
            self.runner = JobRunner(self.store) if embedded_worker else None
            self.store.purge_expired_studies()
            self.janitor_stop = threading.Event()
            self.janitor = threading.Thread(target=self._purge_expired_loop, daemon=True)
            self.janitor.start()
        except BaseException:
            if getattr(self, "runner", None):
                self.runner.close()
            self.lock.close()
            raise

    def _purge_expired_loop(self):
        while not self.janitor_stop.wait(60):
            try:
                self.store.purge_expired_studies()
            except OSError:
                # The next pass retries a transient filesystem error.
                pass

    def interactive(self, callback, *args):
        """Keep slow HTTP lookups and candidate calculations to one at a time."""
        if not self.interactive_slot.acquire(blocking=False):
            raise CapacityError("Another site calculation is in progress. Try again shortly.")
        try:
            return callback(*args)
        finally:
            self.interactive_slot.release()

    def provision_samples(self, owner_id):
        if owner_id is not None:
            for content, name in self.samples:
                self.store.add_dataset(content, name, owner_id)

    def resource(self, kind, request, owner_id=None):
        from .site_inputs import validate_weather_request
        if "site_defaults" not in self.capabilities:
            raise ValueError("Restart with --refresh-engine to enable location studies.")
        if kind == "location":
            if not isinstance(request, dict) or set(request) != {"query"} or not isinstance(request["query"], str) or not 1 <= len(request["query"].strip()) <= 300:
                raise ValueError("Enter a location of 1–300 characters.")
            request = {"query": request["query"].strip()}
        else:
            validate_weather_request(request)
        digest = hashlib.sha256(json.dumps([self.engine["id"], kind, request, owner_id], sort_keys=True).encode()).hexdigest()
        directory = self.store.directory / ("locations" if kind == "location" else "weather") / digest
        with self.resource_lock:
            result_path = directory / "resource.json"
            if result_path.exists():
                result = json.loads(result_path.read_text())
                if kind == "location" or (directory / "weather.csv").exists() and hashlib.sha256((directory / "weather.csv").read_bytes()).hexdigest() == result["sha256"]:
                    self.store.grant(kind, digest, owner_id)
                    return {**result, "id": digest, "cached": True}
            if kind == "weather" and not all(os.getenv(k) for k in ("NSRDB_API_KEY", "NSRDB_API_EMAIL")):
                raise ValueError("NSRDB credentials are missing. Restart with --env-file pointing to your existing src/.env.")
            if kind == "weather":
                self.store.require_weather_storage(owner_id, digest)
            directory.mkdir(parents=True, exist_ok=True)
            write_json(directory / "resource-request.json", {"kind": kind, "request": request})
            verify_snapshot(self.store.directory, self.engine)
            if kind == "location":
                time.sleep(max(0, 1.1 - (time.monotonic() - self.last_lookup)))
                self.last_lookup = time.monotonic()
            try:
                result = subprocess.run(command(self.store.directory, self.engine["id"], "resource") + [str(directory)],
                                        capture_output=True, timeout=180, env=worker_environment())
            except subprocess.TimeoutExpired:
                if kind == "weather":
                    shutil.rmtree(directory)
                raise ValueError("Provider lookup timed out. Retry later; no substitute data was used.") from None
            if result.returncode or not result_path.exists():
                if kind == "weather":
                    shutil.rmtree(directory)
                raise ValueError("Location/weather retrieval failed. Check provider availability, location and NSRDB credentials/coverage. No substitute data was used.")
            if kind == "weather" and self.store.directory_bytes(directory) > self.store.max_weather_bytes:
                shutil.rmtree(directory)
                raise CapacityError("Retrieved weather exceeds the per-resource storage limit. Contact the site administrator.", None)
            self.store.grant(kind, digest, owner_id)
            return {**json.loads(result_path.read_text()), "id": digest, "cached": False}

    def candidate(self, kind, request, owner_id=None):
        if kind != "orientation" or owner_id is None:
            return self._candidate(kind, request, owner_id)
        if "candidate_defaults" not in self.capabilities:
            raise ValueError("This pinned engine does not support the candidate equipment/orientation contract.")
        event_id = self.store.start_orientation(owner_id)
        started = time.monotonic()
        try:
            return self._candidate(kind, request, owner_id)
        finally:
            self.store.finish_orientation(event_id, time.monotonic() - started)

    def _candidate(self, kind, request, owner_id=None):
        from .contract import identifier
        if "candidate_defaults" not in self.capabilities:
            raise ValueError("This pinned engine does not support the candidate equipment/orientation contract.")
        if not isinstance(request, dict):
            raise ValueError("Supply a configuration object.")
        municipal = kind in ("utility-resolution", "municipal-eligibility", "municipal-bill")
        if municipal and "municipal" not in self.capabilities:
            raise ValueError("Refresh the pinned engine to enable municipal bill replay.")
        if municipal and kind != "utility-resolution":
            resolution_id = request.get("resolution_id", "")
            if not isinstance(resolution_id, str) or len(resolution_id) != 32 or any(c not in "0123456789abcdef" for c in resolution_id):
                raise ValueError("Resolve utility service first and supply resolution_id.")
            self.store.require_resource("resolution", resolution_id, owner_id)
            source = self.store.directory / "candidate" / resolution_id
            if "resolution" in request or not (source / "resource.json").is_file():
                raise ValueError("Use a saved utility resolution; client-supplied resolution evidence is not accepted.")
            original = json.loads((source / "resource-request.json").read_text())
            if original["kind"] != "utility-resolution":
                raise ValueError("The referenced result is not a utility resolution.")
            request = {**request, "resolution": json.loads((source / "resource.json").read_text())}
        if kind == "ess" and "record" in request:
            raise ValueError("Select equipment from this engine's catalog.")
        directory = self.store.directory / "candidate" / uuid.uuid4().hex
        directory.mkdir(parents=True)
        if kind == "orientation":
            if set(request) != {"study", "weather_id"} or not identifier(request["weather_id"]):
                raise ValueError("Retrieve annual historical weather before optimizing.")
            self.store.require_resource("weather", request["weather_id"], owner_id)
            cached = self.store.directory / "weather" / request["weather_id"]
            for name in ("weather.csv", "weather.json"):
                if not (cached / name).is_file():
                    raise ValueError("Annual weather is not cached; retrieve it first.")
                shutil.copyfile(cached / name, directory / name)
        write_json(directory / "resource-request.json", {"kind": kind, "request": request})
        verify_snapshot(self.store.directory, self.engine)
        try:
            result = subprocess.run(command(self.store.directory, self.engine["id"], "candidate") + [str(directory)], capture_output=True, timeout=1800, env=worker_environment())
        except subprocess.TimeoutExpired:
            raise ValueError("Candidate calculation exceeded the 30-minute limit.") from None
        if result.returncode:
            error_path = directory / "error.json"
            raise ValueError(json.loads(error_path.read_text())["error"] if error_path.exists() else "Candidate calculation failed.")
        output = json.loads((directory / "resource.json").read_text())
        self.store.grant("resolution" if kind == "utility-resolution" else "candidate", directory.name, owner_id)
        return {**output, "resource_id": directory.name, "engine_id": self.engine["id"],
                **({"resolution_id": directory.name} if kind == "utility-resolution" else {})} if municipal else output

    def submit_socal(self, request, owner_id=None, *, temporary=False):
        if not self.capabilities.get("socal"):
            raise ValueError("Refresh the engine after validating Southern California compatibility.")
        if not isinstance(request, dict) or request.get("schema_version") != 6 or "resolution" in request:
            raise ValueError("Supply schema 6 and saved resolution_id, not client location evidence.")
        rid = request.get("resolution_id", "")
        if not isinstance(rid, str) or len(rid) != 32 or any(c not in "0123456789abcdef" for c in rid):
            raise ValueError("Resolve electricity delivery first.")
        self.store.require_resource("resolution", rid, owner_id)
        source = self.store.directory / "candidate" / rid
        if not (source / "resource.json").is_file() or json.loads((source / "resource-request.json").read_text())["kind"] != "utility-resolution":
            raise ValueError("Saved utility resolution not found.")
        request = {**request, "resolution": json.loads((source / "resource.json").read_text())}
        return self.store.submit(request, self.engine, owner_id, temporary=temporary)

    def submit_municipal(self, request, owner_id=None, *, temporary=False):
        if not self.capabilities.get("municipal", {}).get("optimized_studies"):
            raise ValueError("Refresh the engine to enable optimized municipal studies.")
        if not isinstance(request, dict) or "resolution" in request:
            raise ValueError("Supply resolution_id; client-supplied location evidence is not accepted.")
        rid = request.get("resolution_id", "")
        if not isinstance(rid, str) or len(rid) != 32 or any(c not in "0123456789abcdef" for c in rid):
            raise ValueError("Resolve and confirm electricity service first.")
        self.store.require_resource("resolution", rid, owner_id)
        source = self.store.directory / "candidate" / rid
        if not (source / "resource.json").is_file() or json.loads((source / "resource-request.json").read_text())["kind"] != "utility-resolution":
            raise ValueError("Saved utility resolution not found.")
        request = {**request, "resolution": json.loads((source / "resource.json").read_text())}
        return self.store.submit(request, self.engine, owner_id, temporary=temporary)

    def submit_pge_annual(self, request, owner_id=None, *, temporary=False):
        if not self.capabilities.get("pge_annual_replay"):
            raise ValueError("Refresh the engine to enable PG&E annual statement replay.")
        return self.store.submit(request, self.engine, owner_id, temporary=temporary)

    def utilities(self, request, owner_id=None):
        from .utilities import lookup_utilities
        # Validate before hashing, including nonfinite coordinates.
        from .contract import number
        if not isinstance(request, dict) or set(request) != {"latitude", "longitude"}:
            raise ValueError("Supply latitude and longitude for utility matching.")
        number(request["latitude"], "Latitude", -90, 90)
        number(request["longitude"], "Longitude", -180, 180)
        key = hashlib.sha256(json.dumps([request, owner_id], sort_keys=True).encode()).hexdigest()
        directory = self.store.directory / "utilities"
        directory.mkdir(exist_ok=True)
        path = directory / (key + ".json")
        with self.resource_lock:
            if path.exists() and time.time() - path.stat().st_mtime < 86400:
                return {**json.loads(path.read_text()), "cached": True}
            result = lookup_utilities(request)
            if result["status"] not in ("unavailable", "partial"):
                write_json(path, result)
            return {**result, "cached": False}

    def health(self, owner_id=None):
        with self.store.connect() as db:
            counts = {row["status"]: row["count"] for row in db.execute(
                "SELECT status, COUNT(*) AS count FROM studies WHERE (? IS NULL OR owner_id=?) GROUP BY status", (owner_id, owner_id))}
        return {"api": "ready", "worker": "connected" if worker_connected(self.store.directory) else "offline",
                "execution_mode": "embedded" if self.runner else "external",
                "queued": counts.get("queued", 0), "running": counts.get("running", 0),
                "cancelling": counts.get("cancelling", 0)}

    def close(self):
        self.janitor_stop.set()
        self.janitor.join()
        if self.runner:
            self.runner.close()
        self.lock.close()


def worker_connected(directory):
    """Probe the exclusive worker lease, including an orphaned active child."""
    with (Path(directory) / "worker.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        return False


class JobRunner:
    """Single durable-queue consumer, independent of the HTTP application."""
    def __init__(self, store):
        self.store = store
        self.lock = (store.directory / "worker.lock").open("a+")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise ValueError("Another simulation worker is using this study directory.") from None
        self.stop = threading.Event()
        try:
            with store.connect() as db:
                db.execute("UPDATE studies SET status = 'cancelled', finished_at = ? WHERE status = 'cancelling'", (now(),))
                db.execute("UPDATE studies SET status = 'failed', error = ?, finished_at = ? WHERE status = 'running'",
                           ("The worker or server stopped during this run. Submit the saved settings again to retry.", now()))
            self.thread = threading.Thread(target=self.work, daemon=True)
            self.thread.start()
        except BaseException:
            self.lock.close()
            raise

    @staticmethod
    def stop_process(process):
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()

    @staticmethod
    def discard_generated_files(directory):
        retained = {"request.json", "engine.json", "input.csv", "weather.csv", "weather.json"}
        for path in directory.iterdir():
            if path.name in retained:
                continue
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)

    def work(self):
        while not self.stop.is_set():
            study = self.store.claim()
            if study is None:
                self.stop.wait(0.3)
                continue
            started = time.monotonic()
            directory = self.store.directory / "runs" / study["id"]
            error = None
            try:
                if self.store.cancellation_requested(study["id"]):
                    raise StudyCancelled()
                engine = json.loads((directory / "engine.json").read_text())
                if engine["dependencies"] != dependencies() or engine["python"] != sys.version:
                    raise ValueError("This saved study's engine dependencies no longer match the worker.")
                verify_snapshot(self.store.directory, engine)
                if self.store.cancellation_requested(study["id"]):
                    raise StudyCancelled()
                process = subprocess.Popen(command(self.store.directory, study["engine_id"], directory),
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=directory,
                                           env=worker_environment(), pass_fds=(self.lock.fileno(),),
                                           start_new_session=True)
                deadline = time.monotonic() + 1800
                while process.poll() is None:
                    self.stop.wait(0.2)
                    if self.store.cancellation_requested(study["id"]):
                        self.stop_process(process)
                        raise StudyCancelled()
                    if self.stop.is_set() or time.monotonic() > deadline:
                        self.stop_process(process)
                        raise RuntimeError("Run interrupted by worker shutdown or the 30-minute run limit.")
                    if (self.store.directory_bytes(directory) > self.store.max_run_bytes
                            or shutil.disk_usage(self.store.directory).free < self.store.min_free_bytes):
                        self.stop_process(process)
                        raise RunStorageExceeded("Study exceeded its result storage limit or the server's free-space reserve.")
                if self.store.directory_bytes(directory) > self.store.max_run_bytes:
                    raise RunStorageExceeded("Study exceeded its result storage limit.")
                if process.returncode != 0:
                    error_path = directory / "error.json"
                    error = json.loads(error_path.read_text())["error"] if error_path.exists() else f"Simulation worker exited with code {process.returncode}."
                elif not (directory / "result.json").exists():
                    error = "Worker returned without saving results."
            except StudyCancelled:
                pass
            except RunStorageExceeded as exc:
                self.discard_generated_files(directory)
                error = str(exc)
            except Exception as exc:
                error = str(exc)
            error = redact(error) if error else None
            if error and (directory / "error.json").exists():
                write_json(directory / "error.json", {"error": error})
            final = self.store.finish(study["id"], error, runtime_seconds=time.monotonic() - started)
            (directory / "worker.log").write_text(
                "Study cancelled.\n" if final == "cancelled" else
                error or "Simulation completed.\n")

    def close(self):
        self.stop.set()
        self.thread.join()
        self.lock.close()
