"""Cancellation state transitions across the durable study queue."""

from copy import deepcopy

import pytest

from src.local_web.contract import DEFAULT_REQUEST
from src.local_web.runtime import CapacityError, JobRunner, ROOT, Store, StudyConflict


def new_study(store, owner="alice"):
    sample = (ROOT / "data/default_small_business_week.csv").read_bytes()
    dataset = store.add_dataset(sample, "sample.csv", owner)
    request = deepcopy(DEFAULT_REQUEST)
    request["dataset_id"] = dataset["id"]
    return store.submit(request, {"id": "engine"}, owner)


def test_queued_cancellation_releases_capacity_and_cannot_be_claimed(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGRID_MAX_PENDING_STUDIES", "3")
    monkeypatch.setenv("MICROGRID_MAX_PENDING_PER_USER", "1")
    store = Store(tmp_path)
    study = new_study(store)
    with pytest.raises(FileNotFoundError):
        store.cancel(study["id"], "bob")
    cancelled = store.cancel(study["id"], "alice")
    assert cancelled["status"] == "cancelled"
    assert cancelled["finished_at"] is not None
    assert cancelled["started_at"] is None
    assert cancelled["runtime_seconds"] is None
    assert cancelled["progress"] == "Study cancelled."
    assert store.claim() is None
    assert store.finish(study["id"]) == "cancelled"
    with pytest.raises(StudyConflict):
        store.cancel(study["id"], "alice")
    assert new_study(store)["status"] == "queued"


def test_running_cancel_wins_over_finish_and_recovery(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGRID_MAX_PENDING_STUDIES", "1")
    monkeypatch.setenv("MICROGRID_MAX_PENDING_PER_USER", "1")
    store = Store(tmp_path)
    study = new_study(store)
    assert store.claim()["id"] == study["id"]
    assert store.cancel(study["id"], "alice")["status"] == "cancelling"
    assert store.cancel(study["id"], "alice")["status"] == "cancelling"
    with pytest.raises(CapacityError, match="queue is full"):
        new_study(store, "bob")
    assert store.finish(study["id"], "simulation failed", runtime_seconds=1.25) == "cancelled"
    assert store.get(study["id"], "alice")["error"] is None
    assert store.get(study["id"], "alice")["runtime_seconds"] == 1.25

    another = new_study(store)
    assert store.claim()["id"] == another["id"]
    assert store.cancel(another["id"], "alice")["status"] == "cancelling"
    runner = JobRunner(Store(tmp_path))
    try:
        assert store.get(another["id"], "alice")["status"] == "cancelled"
    finally:
        runner.close()


def test_cancelling_keeps_per_user_slot_until_worker_finishes(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGRID_MAX_PENDING_STUDIES", "2")
    monkeypatch.setenv("MICROGRID_MAX_PENDING_PER_USER", "1")
    store = Store(tmp_path)
    alice = new_study(store)
    assert store.claim()["id"] == alice["id"]
    assert store.cancel(alice["id"], "alice")["status"] == "cancelling"
    with pytest.raises(CapacityError, match="active study limit"):
        new_study(store)
    assert new_study(store, "bob")["status"] == "queued"
    assert store.finish(alice["id"]) == "cancelled"
    assert new_study(store)["status"] == "queued"
