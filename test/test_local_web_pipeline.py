"""Real HTTP submission and independent process execution across API restarts."""
from contextlib import contextmanager
from copy import deepcopy
import json
import subprocess
import sys
import threading
import time
from urllib.request import Request, urlopen

import pytest

from src.local_web.runtime import Application, JobRunner, ROOT, Store
from src.local_web.server import make_server


@contextmanager
def api_service(directory):
    app = Application(directory, embedded_worker=False)
    server = make_server(app, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def call(path, body=None, token=None):
        request = Request(f"http://127.0.0.1:{server.server_port}" + path,
                          data=None if body is None else json.dumps(body).encode(),
                          headers={"Content-Type": "application/json", "X-Study-Token": token or ""})
        with urlopen(request, timeout=15) as response:
            content = response.read()
            return response.status, json.loads(content) if response.headers["Content-Type"] == "application/json" else content
    try:
        yield app, call
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
        app.close()


def until(read, predicate):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        value = read()
        if predicate(value):
            return value
        time.sleep(.05)
    pytest.fail(f"Pipeline timed out: {value}")


def test_external_process_delivers_tables_after_api_restart(tmp_path):
    process = None
    try:
        with api_service(tmp_path) as (app, call):
            assert call('/api/health')[1]['worker'] == 'offline'
            caps = call('/api/capabilities')[1]
            request = deepcopy(caps['defaults'])
            request['start_date'] = request['end_date'] = '2026-08-01'
            request['strategies'] = ['no_battery', 'cost_optimal']
            code, study = call('/api/studies', request, caps['token'])
            assert code == 202 and study['status'] == 'queued'
            process = subprocess.Popen([sys.executable, '-m', 'src.local_web.runner',
                                        '--data-dir', str(tmp_path)], cwd=ROOT,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            until(lambda: call('/api/studies/' + study['id'])[1], lambda x: x['status'] == 'running')
            assert call('/api/health')[1]['worker'] == 'connected'
        # The HTTP application is fully closed. The runner remains independent.
        assert process.poll() is None
        with api_service(tmp_path) as (_, call):
            result = until(lambda: call('/api/studies/' + study['id'])[1],
                           lambda x: x['status'] in ('completed', 'failed'))
            assert result['status'] == 'completed', result.get('error')
            table_id = result['result']['tables'][0]['id']
            assert call(f"/api/studies/{study['id']}/tables/{table_id}?limit=2")[0] == 200
            assert call(f"/api/studies/{study['id']}/tables/{table_id}.csv")[1]
            assert result['request'] == request
    finally:
        if process is not None:
            process.terminate()
            process.communicate(timeout=15)
            assert process.returncode == 0


def test_only_worker_recovers_interrupted_jobs(tmp_path):
    with api_service(tmp_path) as (app, call):
        caps = call('/api/capabilities')[1]
        study = app.store.submit(caps['defaults'], app.engine)
        app.store.claim()  # Simulate an interrupted prior worker.
    with api_service(tmp_path) as (app, _):
        assert app.store.get(study['id'])['status'] == 'running'
        runner = JobRunner(app.store)
        try:
            assert app.store.get(study['id'])['status'] == 'failed'
            with pytest.raises(ValueError, match='Another simulation worker'):
                JobRunner(Store(tmp_path))
        finally:
            runner.close()
        assert app.health()['worker'] == 'offline'
