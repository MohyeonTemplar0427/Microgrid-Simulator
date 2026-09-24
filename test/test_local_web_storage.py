"""CSV upload quotas count logical ownership and physical storage separately."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from types import SimpleNamespace

import pytest

from src.local_web.contract import DEFAULT_REQUEST
from src.local_web.runtime import Application, CapacityError, ROOT, Store


def samples():
    first = (ROOT / "data/default_small_business_week.csv").read_bytes()
    second = first.replace(b"12.714", b"12.715", 1)
    assert second != first
    return first, second


def test_single_upload_limit_rejects_before_writing(tmp_path, monkeypatch):
    first, _ = samples()
    monkeypatch.setenv("MICROGRID_MAX_UPLOAD_BYTES", str(len(first) - 1))
    store = Store(tmp_path)
    with pytest.raises(CapacityError, match="per-file"):
        store.add_dataset(first, "sample.csv", "alice")
    assert list((tmp_path / "datasets").iterdir()) == []


def test_owner_quota_counts_each_owned_dataset_once(tmp_path, monkeypatch):
    first, second = samples()
    monkeypatch.setenv("MICROGRID_MAX_OWNER_DATASET_BYTES", str(len(first) + len(second) - 1))
    store = Store(tmp_path)
    original = store.add_dataset(first, "first.csv", "alice")
    assert original["size_bytes"] == len(first)
    assert store.add_dataset(first, "same.csv", "alice")["id"] == original["id"]
    with pytest.raises(CapacityError, match="saved CSV upload quota"):
        store.add_dataset(second, "second.csv", "alice")
    assert len(store.datasets("alice")) == 1
    assert store.add_dataset(second, "second.csv", "bob")["size_bytes"] == len(second)


def test_global_quota_counts_shared_file_once(tmp_path, monkeypatch):
    first, second = samples()
    monkeypatch.setenv("MICROGRID_MAX_DATASET_STORE_BYTES", str(len(first) + len(second) - 1))
    store = Store(tmp_path)
    original = store.add_dataset(first, "first.csv", "alice")
    assert store.add_dataset(first, "shared.csv", "bob")["id"] == original["id"]
    with pytest.raises(CapacityError, match="server's CSV upload storage"):
        store.add_dataset(second, "second.csv", "bob")
    assert len(list((tmp_path / "datasets").glob("*.csv"))) == 1


def test_concurrent_uploads_cannot_exceed_global_quota(tmp_path, monkeypatch):
    first, second = samples()
    monkeypatch.setenv("MICROGRID_MAX_DATASET_STORE_BYTES", str(max(len(first), len(second))))
    stores = Store(tmp_path), Store(tmp_path)

    def upload(index):
        try:
            return stores[index].add_dataset((first, second)[index], "sample.csv", f"user{index}")["id"]
        except CapacityError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        accepted = [value for value in pool.map(upload, (0, 1)) if value]
    assert len(accepted) == 1
    assert sum(path.stat().st_size for path in (tmp_path / "datasets").glob("*.csv")) <= max(len(first), len(second))


def test_concurrent_uploads_cannot_exceed_owner_quota(tmp_path, monkeypatch):
    first, second = samples()
    monkeypatch.setenv("MICROGRID_MAX_OWNER_DATASET_BYTES", str(max(len(first), len(second))))
    stores = Store(tmp_path), Store(tmp_path)

    def upload(index):
        try:
            return stores[index].add_dataset((first, second)[index], "sample.csv", "alice")["id"]
        except CapacityError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        accepted = [value for value in pool.map(upload, (0, 1)) if value]
    assert len(accepted) == 1
    assert len(stores[0].datasets("alice")) == 1


def test_legacy_grants_count_by_existing_file_size(tmp_path, monkeypatch):
    first, second = samples()
    monkeypatch.setenv("MICROGRID_MAX_OWNER_DATASET_BYTES", str(len(first) + len(second) - 1))
    store = Store(tmp_path)
    old = store.add_dataset(first, "old.csv")
    store.grant("dataset", old["id"], "alice", {"name": "old.csv"})
    with pytest.raises(CapacityError, match="saved CSV upload quota"):
        store.add_dataset(second, "new.csv", "alice")


def test_run_reservations_include_queued_studies_and_release_on_finish(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGRID_MAX_RUN_BYTES", "100000")
    monkeypatch.setenv("MICROGRID_MAX_OWNER_RUN_BYTES", "250000")
    monkeypatch.setenv("MICROGRID_MAX_RUN_STORE_BYTES", "300000")
    monkeypatch.setenv("MICROGRID_MIN_FREE_BYTES", "1")
    store = Store(tmp_path)
    sample, _ = samples()
    dataset = store.add_dataset(sample, "sample.csv", "alice")
    request = deepcopy(DEFAULT_REQUEST)
    request["dataset_id"] = dataset["id"]
    first = store.submit(request, {"id": "engine"}, "alice")
    second = store.submit(request, {"id": "engine"}, "alice")
    with pytest.raises(CapacityError, match="saved study storage"):
        store.submit(request, {"id": "engine"}, "alice")
    store.finish(first["id"])
    assert store.submit(request, {"id": "engine"}, "alice")["status"] == "queued"
    assert second["status"] == "queued"


def test_run_store_reservation_is_atomic_across_connections(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGRID_MAX_RUN_BYTES", "100000")
    monkeypatch.setenv("MICROGRID_MAX_OWNER_RUN_BYTES", "100000")
    monkeypatch.setenv("MICROGRID_MAX_RUN_STORE_BYTES", "100000")
    monkeypatch.setenv("MICROGRID_MIN_FREE_BYTES", "1")
    first, second = Store(tmp_path), Store(tmp_path)
    sample, _ = samples()
    dataset = first.add_dataset(sample, "sample.csv", "alice")
    first.grant("dataset", dataset["id"], "bob", dataset)
    request = deepcopy(DEFAULT_REQUEST)
    request["dataset_id"] = dataset["id"]

    def submit(index):
        try:
            return (first, second)[index].submit(request, {"id": "engine"}, ("alice", "bob")[index])["id"]
        except CapacityError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        accepted = [value for value in pool.map(submit, (0, 1)) if value]
    assert len(accepted) == 1
    assert len(list((tmp_path / "runs").iterdir())) == 1


def test_existing_run_reservations_reduce_available_disk(tmp_path, monkeypatch):
    import src.local_web.runtime as runtime
    monkeypatch.setenv("MICROGRID_MAX_RUN_BYTES", "100000")
    monkeypatch.setenv("MICROGRID_MAX_OWNER_RUN_BYTES", "300000")
    monkeypatch.setenv("MICROGRID_MAX_RUN_STORE_BYTES", "300000")
    monkeypatch.setenv("MICROGRID_MIN_FREE_BYTES", "1")
    store = Store(tmp_path)
    sample, _ = samples()
    dataset = store.add_dataset(sample, "sample.csv", "alice")
    request = deepcopy(DEFAULT_REQUEST)
    request["dataset_id"] = dataset["id"]
    monkeypatch.setattr(runtime.shutil, "disk_usage", lambda _: SimpleNamespace(free=150000))
    assert store.submit(request, {"id": "engine"}, "alice")["status"] == "queued"
    with pytest.raises(CapacityError, match="low on disk space"):
        store.submit(request, {"id": "engine"}, "alice")


def test_csv_upload_cannot_consume_queued_study_reservation(tmp_path, monkeypatch):
    import src.local_web.runtime as runtime
    monkeypatch.setenv("MICROGRID_MAX_RUN_BYTES", "100000")
    monkeypatch.setenv("MICROGRID_MAX_OWNER_RUN_BYTES", "300000")
    monkeypatch.setenv("MICROGRID_MAX_RUN_STORE_BYTES", "300000")
    monkeypatch.setenv("MICROGRID_MIN_FREE_BYTES", "1")
    store = Store(tmp_path)
    first, second = samples()
    dataset = store.add_dataset(first, "first.csv", "alice")
    request = deepcopy(DEFAULT_REQUEST)
    request["dataset_id"] = dataset["id"]
    store.submit(request, {"id": "engine"}, "alice")
    monkeypatch.setattr(runtime.shutil, "disk_usage", lambda _: SimpleNamespace(free=50000))
    with pytest.raises(CapacityError, match="low on disk space"):
        store.add_dataset(second, "second.csv", "alice")
    assert len(store.datasets("alice")) == 1


def test_input_copy_must_fit_study_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGRID_MAX_RUN_BYTES", "100")
    monkeypatch.setenv("MICROGRID_MAX_OWNER_RUN_BYTES", "100")
    monkeypatch.setenv("MICROGRID_MAX_RUN_STORE_BYTES", "100")
    monkeypatch.setenv("MICROGRID_MIN_FREE_BYTES", "1")
    store = Store(tmp_path)
    sample, _ = samples()
    dataset = store.add_dataset(sample, "sample.csv", "alice")
    request = deepcopy(DEFAULT_REQUEST)
    request["dataset_id"] = dataset["id"]
    with pytest.raises(CapacityError, match="Saved inputs exceed"):
        store.submit(request, {"id": "engine"}, "alice")
    assert store.list("alice") == []
    assert list((tmp_path / "runs").iterdir()) == []


def test_stale_queued_temporary_study_is_removed(tmp_path):
    store = Store(tmp_path)
    sample, _ = samples()
    dataset = store.add_dataset(sample, "sample.csv", "guest:temporary")
    request = deepcopy(DEFAULT_REQUEST)
    request["dataset_id"] = dataset["id"]
    study = store.submit(request, {"id": "engine"}, "guest:temporary", temporary=True)
    with store.connect() as db:
        db.execute("UPDATE studies SET created_at='2000-01-01T00:00:00+00:00' WHERE id=?", (study["id"],))
    assert store.purge_expired_studies() == 1
    assert not (tmp_path / "runs" / study["id"]).exists()
    assert store.list("guest:temporary") == []


def test_weather_storage_counts_owned_and_orphaned_files(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGRID_MAX_WEATHER_BYTES", "100")
    monkeypatch.setenv("MICROGRID_MAX_OWNER_WEATHER_BYTES", "200")
    monkeypatch.setenv("MICROGRID_MAX_WEATHER_STORE_BYTES", "300")
    monkeypatch.setenv("MICROGRID_MIN_FREE_BYTES", "1")
    store = Store(tmp_path)
    for resource in ("a", "b"):
        store.require_weather_storage("alice", resource)
        directory = tmp_path / "weather" / resource
        directory.mkdir()
        (directory / "weather.csv").write_bytes(b"x" * 90)
        store.grant("weather", resource, "alice")
    with pytest.raises(CapacityError, match="saved weather storage"):
        store.require_weather_storage("alice", "c")
    store.require_weather_storage("bob", "c")
    orphan = tmp_path / "weather" / "orphan"
    orphan.mkdir()
    (orphan / "weather.csv").write_bytes(b"x" * 50)
    with pytest.raises(CapacityError, match="server's weather storage"):
        store.require_weather_storage("bob", "c")


@pytest.mark.parametrize("name", [
    "MICROGRID_MAX_UPLOAD_BYTES", "MICROGRID_MAX_OWNER_DATASET_BYTES",
    "MICROGRID_MAX_DATASET_STORE_BYTES",
])
def test_server_startup_requires_room_for_builtin_samples(tmp_path, monkeypatch, name):
    monkeypatch.setenv(name, "1")
    with pytest.raises(ValueError, match=name):
        Application(tmp_path, embedded_worker=False)


@pytest.mark.parametrize("name", [
    "MICROGRID_MAX_UPLOAD_BYTES", "MICROGRID_MAX_OWNER_DATASET_BYTES",
    "MICROGRID_MAX_DATASET_STORE_BYTES",
])
def test_invalid_storage_quota_fails_startup(tmp_path, monkeypatch, name):
    monkeypatch.setenv(name, "0")
    with pytest.raises(ValueError, match=name):
        Store(tmp_path)


@pytest.mark.parametrize("small,large", [
    ("MICROGRID_MAX_RUN_BYTES", "MICROGRID_MAX_OWNER_RUN_BYTES"),
    ("MICROGRID_MAX_RUN_BYTES", "MICROGRID_MAX_RUN_STORE_BYTES"),
    ("MICROGRID_MAX_WEATHER_BYTES", "MICROGRID_MAX_OWNER_WEATHER_BYTES"),
    ("MICROGRID_MAX_WEATHER_BYTES", "MICROGRID_MAX_WEATHER_STORE_BYTES"),
])
def test_storage_hierarchy_fails_startup_when_inverted(tmp_path, monkeypatch, small, large):
    monkeypatch.setenv(small, "100")
    monkeypatch.setenv(large, "99")
    with pytest.raises(ValueError, match=large):
        Store(tmp_path)
