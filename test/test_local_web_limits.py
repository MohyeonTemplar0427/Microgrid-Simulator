"""Bounded queue and HTTP computation slots for the single-host service."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest

from src.local_web.contract import DEFAULT_REQUEST
from src.local_web.runtime import CapacityError, ROOT, Store


def request_for(store, owner):
    sample = (ROOT / "data/default_small_business_week.csv").read_bytes()
    dataset = store.add_dataset(sample, "sample.csv", owner)
    request = deepcopy(DEFAULT_REQUEST)
    request["dataset_id"] = dataset["id"]
    return request


def test_queue_reservation_is_atomic_across_store_connections(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGRID_MAX_PENDING_STUDIES", "5")
    monkeypatch.setenv("MICROGRID_MAX_PENDING_PER_USER", "2")
    first, second = Store(tmp_path), Store(tmp_path)
    request = request_for(first, "alice")

    def submit(index):
        try:
            store = first if index % 2 else second
            return store.submit(request, {"id": "engine"}, "alice")["id"]
        except CapacityError:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(submit, range(8)))
    accepted = [study_id for study_id in outcomes if study_id]
    assert len(accepted) == 2
    assert len(list((tmp_path / "runs").iterdir())) == 2
    assert len(first.list("alice")) == 2

    running = first.claim()["id"]
    assert running in accepted  # Running jobs still consume capacity.
    with pytest.raises(CapacityError, match="active study limit"):
        second.submit(request, {"id": "engine"}, "alice")
    first.finish(running)
    assert second.submit(request, {"id": "engine"}, "alice")["status"] == "queued"


def test_server_queue_capacity_and_owner_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGRID_MAX_PENDING_STUDIES", "3")
    monkeypatch.setenv("MICROGRID_MAX_PENDING_PER_USER", "2")
    store = Store(tmp_path)
    alice = request_for(store, "alice")
    bob = request_for(store, "bob")
    charlie = request_for(store, "charlie")
    for _ in range(2):
        store.submit(alice, {"id": "engine"}, "alice")
    with pytest.raises(CapacityError, match="active study"):
        store.submit(alice, {"id": "engine"}, "alice")
    store.submit(bob, {"id": "engine"}, "bob")
    with pytest.raises(CapacityError, match="queue is full"):
        store.submit(charlie, {"id": "engine"}, "charlie")
    assert len(list((tmp_path / "runs").iterdir())) == 3
    assert len(store.list("alice")) == 2
    assert len(store.list("bob")) == 1
    assert store.list("charlie") == []


@pytest.mark.parametrize("name,value", [
    ("MICROGRID_MAX_PENDING_STUDIES", "0"),
    ("MICROGRID_MAX_PENDING_PER_USER", "bogus"),
    ("MICROGRID_MAX_PENDING_STUDIES", "1001"),
])
def test_invalid_limits_fail_at_startup(tmp_path, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=name):
        Store(tmp_path)
