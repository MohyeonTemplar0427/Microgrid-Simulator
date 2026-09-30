"""Offline study storage snapshots must be private, complete, and restorable."""

import fcntl
from pathlib import Path
import sqlite3

import pytest

from tools.web_storage import backup, restore, verify


def studies(directory):
    directory.mkdir()
    with sqlite3.connect(directory / "studies.sqlite3") as db:
        db.execute("CREATE TABLE studies (id TEXT PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO studies VALUES ('one', 'private study')")
    run = directory / "runs" / "one"
    run.mkdir(parents=True)
    (run / "dispatch.csv").write_text("hour,power\n1,2\n")
    (directory / "server.lock").touch()
    (directory / "worker.lock").touch()
    return directory


def test_backup_verify_and_restore_into_new_directory(tmp_path):
    source = studies(tmp_path / "source?#")
    target = tmp_path / "backup"
    assert backup(source, target) == target
    manifest = verify(target)
    assert set(manifest["files"]) == {"studies.sqlite3", "runs/one/dispatch.csv"}
    assert not (target / "data" / "server.lock").exists()
    assert target.stat().st_mode & 0o077 == 0
    restored = tmp_path / "restored"
    assert restore(target, restored) == restored
    assert (restored / "runs" / "one" / "dispatch.csv").read_text() == "hour,power\n1,2\n"
    with sqlite3.connect(restored / "studies.sqlite3") as db:
        assert db.execute("SELECT name FROM studies WHERE id='one'").fetchone() == ("private study",)
    with pytest.raises(ValueError, match="must not exist"):
        restore(target, restored)


def test_backup_refuses_active_api_or_worker(tmp_path):
    source = studies(tmp_path / "source")
    for name in ("server.lock", "worker.lock"):
        with (source / name).open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with pytest.raises(ValueError, match="Stop both"):
                backup(source, tmp_path / "backup")
            fcntl.flock(lock, fcntl.LOCK_UN)
        assert not (tmp_path / "backup").exists()


def test_backup_rejects_symlinks_and_nested_destination(tmp_path):
    source = studies(tmp_path / "source")
    with pytest.raises(ValueError, match="outside"):
        backup(source, source / "copy")
    link = source / "runs" / "one" / "elsewhere"
    link.symlink_to(Path("/etc/passwd"))
    with pytest.raises(ValueError, match="symlink"):
        backup(source, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_verification_detects_file_changes_and_refuses_restore(tmp_path):
    source = studies(tmp_path / "source")
    target = backup(source, tmp_path / "backup")
    (target / "data" / "runs" / "one" / "dispatch.csv").write_text("tampered")
    with pytest.raises(ValueError, match="checksum"):
        verify(target)
    with pytest.raises(ValueError, match="checksum"):
        restore(target, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_prune_removes_only_managed_backups_after_seven_days(tmp_path):
    from datetime import datetime, timedelta, timezone
    import json
    from tools.web_storage import prune

    source = studies(tmp_path / "source")
    old = backup(source, tmp_path / "microgrid-old")
    recent = backup(source, tmp_path / "microgrid-recent")
    other = backup(source, tmp_path / "unmanaged-old")
    clock = datetime(2026, 9, 27, tzinfo=timezone.utc)
    for path in (old, recent, other):
        manifest_path = path / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["created_at"] = (clock - timedelta(days=8 if path != recent else 1)).isoformat()
        manifest_path.write_text(json.dumps(manifest))
    assert prune(tmp_path, 7, current_time=clock) == ["microgrid-old"]
    assert not old.exists() and recent.exists() and other.exists()
