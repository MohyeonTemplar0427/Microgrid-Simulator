"""Offline backup, verification, and non-destructive restore of local-web storage.

Stop the API and worker first. Their advisory locks are also acquired here, so
neither service can start while a backup is being copied.
"""

import argparse
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile


FORMAT_VERSION = 1
SKIP = {"studies.sqlite3", "studies.sqlite3-journal", "studies.sqlite3-wal",
        "studies.sqlite3-shm", "server.lock", "worker.lock"}


def _inside(path, parent):
    return path == parent or parent in path.parents


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _files(root):
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Storage must be a real directory.")
    found = {}
    for base, directories, filenames in os.walk(root, followlinks=False):
        for name in directories + filenames:
            path = Path(base) / name
            if path.is_symlink():
                raise ValueError("Storage contains a symlink; inspect it before backup or restore.")
        for name in filenames:
            path = Path(base) / name
            if not path.is_file():
                raise ValueError("Storage contains a non-regular file.")
            found[path.relative_to(root).as_posix()] = path
    return found


def _db_integrity(path):
    if not path.is_file():
        raise ValueError("The study database is missing.")
    uri = path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        result = db.execute("PRAGMA integrity_check").fetchone()
    if result != ("ok",):
        raise ValueError("The study database failed its integrity check.")


@contextmanager
def _stopped_services(directory):
    with ExitStack() as stack:
        for name in ("server.lock", "worker.lock"):
            lock = stack.enter_context((directory / name).open("a+"))
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("Stop both the API and simulation worker before backing up.") from None
        yield


def _write_manifest(destination, files):
    manifest = {"format_version": FORMAT_VERSION,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "files": {name: _sha256(path) for name, path in sorted(files.items())}}
    (destination / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")


def _verify_payload(directory, expected):
    actual = _files(directory)
    if set(actual) != set(expected):
        raise ValueError("Backup files differ from the manifest.")
    for name, path in actual.items():
        if _sha256(path) != expected[name]:
            raise ValueError(f"Backup checksum failed for {name}.")
    _db_integrity(directory / "studies.sqlite3")


def verify(backup):
    backup = Path(backup)
    if backup.is_symlink() or not backup.is_dir():
        raise ValueError("Backup directory is missing or is a symlink.")
    manifest = json.loads((backup / "manifest.json").read_text())
    if manifest.get("format_version") != FORMAT_VERSION or not isinstance(manifest.get("files"), dict):
        raise ValueError("Unsupported backup manifest.")
    payload = backup / "data"
    _verify_payload(payload, manifest["files"])
    return manifest


def backup(directory, destination):
    directory = Path(directory).resolve(strict=True)
    requested = Path(destination).absolute()
    destination = requested.parent.resolve(strict=True) / requested.name
    if destination.exists() or destination.is_symlink():
        raise ValueError("Backup destination already exists.")
    if not destination.parent.is_dir() or _inside(destination, directory) or _inside(directory, destination):
        raise ValueError("Backup destination must be outside the study directory with an existing parent.")
    previous_umask = os.umask(0o077)
    try:
        with _stopped_services(directory):
            source = _files(directory)
            _db_integrity(directory / "studies.sqlite3")
            staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
            try:
                payload = staging / "data"
                payload.mkdir(mode=0o700)
                for name, path in source.items():
                    if name in SKIP:
                        continue
                    target = payload / name
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    shutil.copyfile(path, target)
                with sqlite3.connect(directory / "studies.sqlite3") as original:
                    with sqlite3.connect(payload / "studies.sqlite3") as copied:
                        original.backup(copied)
                files = _files(payload)
                _write_manifest(staging, files)
                verify(staging)
                staging.rename(destination)
            except BaseException:
                shutil.rmtree(staging)
                raise
    finally:
        os.umask(previous_umask)
    return destination


def restore(backup_directory, destination):
    backup_directory = Path(backup_directory).resolve(strict=True)
    requested = Path(destination).absolute()
    destination = requested.parent.resolve(strict=True) / requested.name
    manifest = verify(backup_directory)
    if destination.exists() or destination.is_symlink():
        raise ValueError("Restore destination must not exist; never overwrite live studies.")
    if not destination.parent.is_dir() or _inside(destination, backup_directory) or _inside(backup_directory, destination):
        raise ValueError("Restore destination must be outside the backup with an existing parent.")
    previous_umask = os.umask(0o077)
    try:
        staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
        try:
            for name in manifest["files"]:
                source = backup_directory / "data" / name
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                shutil.copyfile(source, target)
            _verify_payload(staging, manifest["files"])
            staging.rename(destination)
        except BaseException:
            shutil.rmtree(staging)
            raise
    finally:
        os.umask(previous_umask)
    return destination


def prune(backup_root, keep_days=7, *, current_time=None):
    """Remove tool-created snapshots older than the selected retention window."""
    if type(keep_days) is not int or not 1 <= keep_days <= 365:
        raise ValueError("Backup retention must be 1–365 days.")
    backup_root = Path(backup_root).resolve(strict=True)
    if not backup_root.is_dir():
        raise ValueError("Backup root must be a directory.")
    cutoff = (current_time or datetime.now(timezone.utc)) - timedelta(days=keep_days)
    removed = []
    for entry in backup_root.iterdir():
        if not entry.name.startswith("microgrid-"):
            continue
        if entry.is_symlink():
            raise ValueError("Backup root contains a symlink with a managed name.")
        if not entry.is_dir():
            continue
        manifest_path = entry / "manifest.json"
        if not manifest_path.is_file():
            raise ValueError(f"Managed backup {entry.name} has no manifest; inspect it manually.")
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("format_version") != FORMAT_VERSION:
            raise ValueError(f"Managed backup {entry.name} has an unknown format.")
        try:
            created = datetime.fromisoformat(manifest["created_at"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Managed backup {entry.name} has an invalid creation time.") from exc
        if created.tzinfo is None:
            raise ValueError(f"Managed backup {entry.name} has no timezone.")
        if created <= cutoff:
            shutil.rmtree(entry)
            removed.append(entry.name)
    return removed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    create = commands.add_parser("backup", help="Back up a stopped API and worker.")
    create.add_argument("--data-dir", required=True, type=Path)
    create.add_argument("--output", required=True, type=Path)
    check = commands.add_parser("verify", help="Verify every file and the SQLite database.")
    check.add_argument("--backup", required=True, type=Path)
    recover = commands.add_parser("restore", help="Restore into a new, absent directory.")
    recover.add_argument("--backup", required=True, type=Path)
    recover.add_argument("--data-dir", required=True, type=Path)
    removal = commands.add_parser("prune", help="Remove managed snapshots older than retention.")
    removal.add_argument("--backup-root", required=True, type=Path)
    removal.add_argument("--keep-days", type=int, default=7)
    args = parser.parse_args()
    try:
        if args.action == "backup":
            backup(args.data_dir, args.output)
        elif args.action == "verify":
            verify(args.backup)
        elif args.action == "restore":
            restore(args.backup, args.data_dir)
        else:
            prune(args.backup_root, args.keep_days)
    except (OSError, ValueError, sqlite3.DatabaseError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Storage {args.action} failed: {exc}\n")
    print(f"Storage {args.action} completed.")


if __name__ == "__main__":
    main()
