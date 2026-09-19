"""Local persistence, explicit engine snapshots, and a single process-isolated worker."""

import csv
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.metadata
import io
import json
import math
import os
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

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = "import sys; sys.path.insert(0, sys.argv.pop(1)); from src.local_web.worker import main; main()"


def now():
    return datetime.now(timezone.utc).isoformat()


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
        for name in ("datasets", "runs", "engines", "weather", "locations"):
            (self.directory / name).mkdir(exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS studies (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL,
                created_at TEXT NOT NULL, finished_at TEXT, engine_id TEXT NOT NULL,
                error TEXT)""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def add_dataset(self, content, name):
        metadata = inspect_csv(content)
        digest = hashlib.sha256(content).hexdigest()
        metadata.update(id=digest, name=Path(name).name[:120])
        target = self.directory / "datasets" / digest
        if not target.with_suffix(".csv").exists():
            target.with_suffix(".csv").write_bytes(content)
            write_json(target.with_suffix(".json"), metadata)
        return json.loads(target.with_suffix(".json").read_text())

    def datasets(self):
        return [json.loads(p.read_text()) for p in sorted((self.directory / "datasets").glob("*.json"))]

    def submit(self, request, engine):
        validate_request(request)
        sources = {}
        if request["schema_version"] == 1:
            sources["input.csv"] = self.directory / "datasets" / (request["dataset_id"] + ".csv")
        elif request.get("weather_source") == "nsrdb":
            from .site_inputs import check_weather_matches
            cached = self.directory / "weather" / request["weather_id"]
            if not (cached / "weather.json").is_file():
                raise ValueError("Retrieve weather for this site before running.")
            check_weather_matches(request, json.loads((cached / "weather.json").read_text()))
            sources = {name: cached / name for name in ("weather.csv", "weather.json")}
        if any(not source.is_file() for source in sources.values()):
            raise ValueError("The selected input is missing. Retrieve or select it first.")
        study_id = uuid.uuid4().hex
        directory = self.directory / "runs" / study_id
        directory.mkdir()
        for name, source in sources.items():
            shutil.copyfile(source, directory / name)
        write_json(directory / "request.json", request)
        write_json(directory / "engine.json", engine)
        with self.connect() as db:
            db.execute("INSERT INTO studies VALUES (?, ?, 'queued', ?, NULL, ?, NULL)",
                       (study_id, request["name"].strip(), now(), engine["id"]))
        return self.get(study_id)

    def get(self, study_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM studies WHERE id = ?", (study_id,)).fetchone()
        if row is None:
            raise FileNotFoundError("Study not found.")
        result = dict(row)
        directory = self.directory / "runs" / study_id
        result["request"] = json.loads((directory / "request.json").read_text())
        progress = directory / "progress.json"
        result["progress"] = json.loads(progress.read_text())["message"] if progress.exists() else result["status"]
        if result["status"] == "completed":
            result["result"] = json.loads((directory / "result.json").read_text())
        return result

    def list(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM studies ORDER BY created_at DESC LIMIT 100")]

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM studies WHERE status = 'queued' ORDER BY created_at LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE studies SET status = 'running' WHERE id = ?", (row["id"],))
        return dict(row) if row else None

    def finish(self, study_id, error=None):
        with self.connect() as db:
            db.execute("UPDATE studies SET status = ?, error = ?, finished_at = ? WHERE id = ?",
                       ("failed" if error else "completed", error, now(), study_id))


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
            self.engine = snapshot(root, self.store.directory, refresh)
            result = subprocess.run(command(self.store.directory, self.engine["id"], "capabilities"),
                                    capture_output=True, text=True, check=True, timeout=90)
            self.capabilities = json.loads(result.stdout)
            for name in ("default_small_business_week.csv", "default_microgrid_week.csv"):
                self.store.add_dataset((root / "data" / name).read_bytes(), name)
        except BaseException:
            self.lock.close()
            raise
        self.resource_lock = threading.Lock()
        self.last_lookup = 0
        try:
            self.runner = JobRunner(self.store) if embedded_worker else None
        except BaseException:
            self.lock.close()
            raise

    def resource(self, kind, request):
        from .site_inputs import validate_weather_request
        if "site_defaults" not in self.capabilities:
            raise ValueError("Restart with --refresh-engine to enable location studies.")
        if kind == "location":
            if not isinstance(request, dict) or set(request) != {"query"} or not isinstance(request["query"], str) or not 1 <= len(request["query"].strip()) <= 300:
                raise ValueError("Enter a location of 1–300 characters.")
            request = {"query": request["query"].strip()}
        else:
            validate_weather_request(request)
        digest = hashlib.sha256(json.dumps([self.engine["id"], kind, request], sort_keys=True).encode()).hexdigest()
        directory = self.store.directory / ("locations" if kind == "location" else "weather") / digest
        with self.resource_lock:
            result_path = directory / "resource.json"
            if result_path.exists():
                result = json.loads(result_path.read_text())
                if kind == "location" or (directory / "weather.csv").exists() and hashlib.sha256((directory / "weather.csv").read_bytes()).hexdigest() == result["sha256"]:
                    return {**result, "id": digest, "cached": True}
            if kind == "weather" and not all(os.getenv(k) for k in ("NSRDB_API_KEY", "NSRDB_API_EMAIL")):
                raise ValueError("NSRDB credentials are missing. Restart with --env-file pointing to your existing src/.env.")
            directory.mkdir(parents=True, exist_ok=True)
            write_json(directory / "resource-request.json", {"kind": kind, "request": request})
            verify_snapshot(self.store.directory, self.engine)
            if kind == "location":
                time.sleep(max(0, 1.1 - (time.monotonic() - self.last_lookup)))
                self.last_lookup = time.monotonic()
            try:
                result = subprocess.run(command(self.store.directory, self.engine["id"], "resource") + [str(directory)],
                                        capture_output=True, timeout=180)
            except subprocess.TimeoutExpired:
                raise ValueError("Provider lookup timed out. Retry later; no substitute data was used.") from None
            if result.returncode or not result_path.exists():
                raise ValueError("Location/weather retrieval failed. Check provider availability, location and NSRDB credentials/coverage. No substitute data was used.")
            return {**json.loads(result_path.read_text()), "id": digest, "cached": False}

    def candidate(self, kind, request):
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
            cached = self.store.directory / "weather" / request["weather_id"]
            for name in ("weather.csv", "weather.json"):
                if not (cached / name).is_file():
                    raise ValueError("Annual weather is not cached; retrieve it first.")
                shutil.copyfile(cached / name, directory / name)
        write_json(directory / "resource-request.json", {"kind": kind, "request": request})
        verify_snapshot(self.store.directory, self.engine)
        try:
            result = subprocess.run(command(self.store.directory, self.engine["id"], "candidate") + [str(directory)], capture_output=True, timeout=1800)
        except subprocess.TimeoutExpired:
            raise ValueError("Candidate calculation exceeded the 30-minute limit.") from None
        if result.returncode:
            error_path = directory / "error.json"
            raise ValueError(json.loads(error_path.read_text())["error"] if error_path.exists() else "Candidate calculation failed.")
        output = json.loads((directory / "resource.json").read_text())
        return {**output, "resource_id": directory.name, "engine_id": self.engine["id"],
                **({"resolution_id": directory.name} if kind == "utility-resolution" else {})} if municipal else output

    def submit_socal(self, request):
        if not self.capabilities.get("socal"):
            raise ValueError("Refresh the engine after validating Southern California compatibility.")
        if not isinstance(request, dict) or request.get("schema_version") != 6 or "resolution" in request:
            raise ValueError("Supply schema 6 and saved resolution_id, not client location evidence.")
        rid = request.get("resolution_id", "")
        if not isinstance(rid, str) or len(rid) != 32 or any(c not in "0123456789abcdef" for c in rid):
            raise ValueError("Resolve electricity delivery first.")
        source = self.store.directory / "candidate" / rid
        if not (source / "resource.json").is_file() or json.loads((source / "resource-request.json").read_text())["kind"] != "utility-resolution":
            raise ValueError("Saved utility resolution not found.")
        request = {**request, "resolution": json.loads((source / "resource.json").read_text())}
        return self.store.submit(request, self.engine)

    def submit_municipal(self, request):
        if not self.capabilities.get("municipal", {}).get("optimized_studies"):
            raise ValueError("Refresh the engine to enable optimized municipal studies.")
        if not isinstance(request, dict) or "resolution" in request:
            raise ValueError("Supply resolution_id; client-supplied location evidence is not accepted.")
        rid = request.get("resolution_id", "")
        if not isinstance(rid, str) or len(rid) != 32 or any(c not in "0123456789abcdef" for c in rid):
            raise ValueError("Resolve and confirm electricity service first.")
        source = self.store.directory / "candidate" / rid
        if not (source / "resource.json").is_file() or json.loads((source / "resource-request.json").read_text())["kind"] != "utility-resolution":
            raise ValueError("Saved utility resolution not found.")
        request = {**request, "resolution": json.loads((source / "resource.json").read_text())}
        return self.store.submit(request, self.engine)

    def utilities(self, request):
        from .utilities import lookup_utilities
        # Validate before hashing, including nonfinite coordinates.
        from .contract import number
        if not isinstance(request, dict) or set(request) != {"latitude", "longitude"}:
            raise ValueError("Supply latitude and longitude for utility matching.")
        number(request["latitude"], "Latitude", -90, 90)
        number(request["longitude"], "Longitude", -180, 180)
        key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
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

    def health(self):
        with self.store.connect() as db:
            counts = {row["status"]: row["count"] for row in db.execute(
                "SELECT status, COUNT(*) AS count FROM studies GROUP BY status")}
        return {"api": "ready", "worker": "connected" if worker_connected(self.store.directory) else "offline",
                "execution_mode": "embedded" if self.runner else "external",
                "queued": counts.get("queued", 0), "running": counts.get("running", 0)}

    def close(self):
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
                db.execute("UPDATE studies SET status = 'failed', error = ?, finished_at = ? WHERE status = 'running'",
                           ("The worker or server stopped during this run. Submit the saved settings again to retry.", now()))
            self.thread = threading.Thread(target=self.work, daemon=True)
            self.thread.start()
        except BaseException:
            self.lock.close()
            raise

    def work(self):
        while not self.stop.is_set():
            study = self.store.claim()
            if study is None:
                self.stop.wait(0.3)
                continue
            directory = self.store.directory / "runs" / study["id"]
            error = None
            try:
                engine = json.loads((directory / "engine.json").read_text())
                if engine["dependencies"] != dependencies() or engine["python"] != sys.version:
                    raise ValueError("This saved study's engine dependencies no longer match the worker.")
                verify_snapshot(self.store.directory, engine)
                with (directory / "worker.log").open("w") as log:
                    process = subprocess.Popen(command(self.store.directory, study["engine_id"], directory),
                                               stdout=log, stderr=log, cwd=directory, pass_fds=(self.lock.fileno(),))
                    import time
                    deadline = time.monotonic() + 1800
                    while process.poll() is None:
                        if self.stop.wait(0.2) or time.monotonic() > deadline:
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait()
                            raise RuntimeError("Run interrupted by worker shutdown or the 30-minute run limit.")
                    if process.returncode != 0:
                        error_path = directory / "error.json"
                        error = json.loads(error_path.read_text())["error"] if error_path.exists() else f"Simulation worker exited with code {process.returncode}."
                    elif not (directory / "result.json").exists():
                        error = "Worker returned without saving results."
            except Exception as exc:
                error = str(exc)
            self.store.finish(study["id"], error)

    def close(self):
        self.stop.set()
        self.thread.join()
        self.lock.close()
