"""Daily submission limits and measured runtime for signed-in users."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest

from src.local_web.contract import DEFAULT_REQUEST
from src.local_web.runtime import CapacityError, ROOT, Store


def prepare(store, owner):
    content = (ROOT / "data/default_small_business_week.csv").read_bytes()
    dataset = store.add_dataset(content, "sample.csv", owner)
    request = deepcopy(DEFAULT_REQUEST)
    request["dataset_id"] = dataset["id"]
    return request


def test_default_daily_limit_is_200_studies(tmp_path):
    store = Store(tmp_path)
    usage = store.daily_usage("alice")
    assert usage["study_limit"] == 200
    assert usage["remaining_studies"] == 200
    assert "compute_limit_seconds" not in usage
    assert "remaining_seconds" not in usage


def test_daily_study_limit_is_atomic_across_api_connections(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGRID_DAILY_STUDY_LIMIT", "2")
    first, second = Store(tmp_path), Store(tmp_path)
    request = prepare(first, "alice")

    def submit(index):
        try:
            store = first if index % 2 else second
            return store.submit(request, {"id": "engine"}, "alice")["id"]
        except CapacityError:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        accepted = [study for study in pool.map(submit, range(8)) if study]
    assert len(accepted) == 2
    assert first.daily_usage("alice")["submitted_studies"] == 2
    assert len(list((tmp_path / "runs").iterdir())) == 2
    assert first.daily_usage("bob")["submitted_studies"] == 0
    assert first.submit(prepare(first, "bob"), {"id": "engine"}, "bob")["status"] == "queued"


def test_runtime_and_orientation_are_measured_but_do_not_limit_studies(tmp_path):
    store = Store(tmp_path)
    request = prepare(store, "alice")
    first = store.submit(request, {"id": "engine"}, "alice")
    assert store.claim()["id"] == first["id"]
    store.finish(first["id"], runtime_seconds=1.25)
    assert store.daily_usage("alice")["used_seconds"] == 1.25
    event = store.start_orientation("alice")
    store.finish_orientation(event, 0.85)
    usage = store.daily_usage("alice")
    assert usage["used_seconds"] == 2.1
    assert store.submit(request, {"id": "engine"}, "alice")["status"] == "queued"
    assert store.start_orientation("alice") is not None
    assert store.daily_usage("bob")["used_seconds"] == 0
    assert store.submit(prepare(store, "bob"), {"id": "engine"}, "bob")["status"] == "queued"


def test_cancelled_queue_counts_as_submission_without_compute_time(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGRID_DAILY_STUDY_LIMIT", "1")
    store = Store(tmp_path)
    request = prepare(store, "alice")
    study = store.submit(request, {"id": "engine"}, "alice")
    assert store.cancel(study["id"], "alice")["status"] == "cancelled"
    usage = store.daily_usage("alice")
    assert usage["submitted_studies"] == 1
    assert usage["used_seconds"] == 0
    with pytest.raises(CapacityError, match="study limit"):
        store.submit(request, {"id": "engine"}, "alice")


def test_usage_resets_at_utc_midnight(tmp_path, monkeypatch):
    import src.local_web.runtime as runtime
    monkeypatch.setenv("MICROGRID_DAILY_STUDY_LIMIT", "1")
    current = ["2026-09-23T23:59:00+00:00"]
    monkeypatch.setattr(runtime, "now", lambda: current[0])
    store = Store(tmp_path)
    request = prepare(store, "alice")
    study = store.submit(request, {"id": "engine"}, "alice")
    assert store.claim()["id"] == study["id"]
    store.finish(study["id"], runtime_seconds=2)
    assert store.daily_usage("alice")["remaining_studies"] == 0
    current[0] = "2026-09-24T00:01:00+00:00"
    assert store.daily_usage("alice")["submitted_studies"] == 0
    assert store.daily_usage("alice")["used_seconds"] == 0
    assert store.submit(request, {"id": "engine"}, "alice")["status"] == "queued"


@pytest.mark.parametrize("name,value", [
    ("MICROGRID_DAILY_STUDY_LIMIT", "0"),
    ("MICROGRID_DAILY_STUDY_LIMIT", "1001"),
])
def test_bad_daily_limits_fail_startup(tmp_path, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=name):
        Store(tmp_path)


def test_active_run_is_measured_before_it_finishes(tmp_path, monkeypatch):
    import src.local_web.runtime as runtime
    current = ["2026-09-23T12:00:00+00:00"]
    monkeypatch.setattr(runtime, "now", lambda: current[0])
    store = Store(tmp_path)
    request = prepare(store, "alice")
    first = store.submit(request, {"id": "engine"}, "alice")
    assert store.claim()["id"] == first["id"]
    current[0] = "2026-09-23T12:00:02+00:00"
    assert store.daily_usage("alice")["used_seconds"] == 2
    assert store.submit(request, {"id": "engine"}, "alice")["status"] == "queued"


def test_open_orientation_is_measured_conservatively_after_restart(tmp_path, monkeypatch):
    import src.local_web.runtime as runtime
    current = ["2026-09-23T12:00:00+00:00"]
    monkeypatch.setattr(runtime, "now", lambda: current[0])
    store = Store(tmp_path)
    event = store.start_orientation("alice")
    current[0] = "2026-09-23T12:31:00+00:00"
    restarted = Store(tmp_path)
    assert restarted.daily_usage("alice")["used_seconds"] == 1800
    assert restarted.start_orientation("alice") is not None
    restarted.finish_orientation(event, 60)
    assert restarted.daily_usage("alice")["used_seconds"] == 60


def test_trusted_local_mode_has_no_per_user_daily_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGRID_DAILY_STUDY_LIMIT", "1")
    store = Store(tmp_path)
    request = prepare(store, None)
    assert store.daily_usage(None) == {"enabled": False}
    assert store.submit(request, {"id": "engine"})["status"] == "queued"
    assert store.submit(request, {"id": "engine"})["status"] == "queued"
