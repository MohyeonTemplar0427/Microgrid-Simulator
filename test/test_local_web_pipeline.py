"""Real HTTP submission and independent process execution across API restarts."""
from contextlib import contextmanager
from datetime import datetime
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


def test_local_draft_gets_name_only_when_result_is_saved(tmp_path):
    from urllib.error import HTTPError
    from src.local_web.worker import write_json

    with api_service(tmp_path) as (app, call):
        caps = call('/api/capabilities')[1]
        request = deepcopy(caps['defaults'])
        request['name'] = 'Untitled study'
        code, draft = call('/api/studies?draft=1', request, caps['token'])
        assert code == 202 and draft['saved'] == 0
        assert draft['name'] == 'Untitled study'
        write_json(app.store.directory/'runs'/draft['id']/'result.json', {'tables': []})
        app.store.finish(draft['id'])
        assert call('/api/studies/'+draft['id'])[1]['expires_at'] is not None
        with pytest.raises(HTTPError) as invalid:
            call('/api/studies/'+draft['id']+'/save', {'name': '   '}, caps['token'])
        assert invalid.value.code == 400
        assert call('/api/studies/'+draft['id'])[1]['saved'] == 0

        code, saved = call('/api/studies/'+draft['id']+'/save',
                           {'name': '  My Burbank solar comparison  '}, caps['token'])
        assert code == 200 and saved['saved'] == 1
        assert saved['name'] == 'My Burbank solar comparison'
        assert saved['expires_at'] is None
        assert saved['request']['name'] == saved['name']
        assert call('/api/studies/'+draft['id']+'/request.json')[1]['name'] == saved['name']
        assert call('/api/studies')[1][0]['name'] == saved['name']
        # The original calculation input remains immutable on disk.
        original = json.loads((app.store.directory/'runs'/draft['id']/'request.json').read_text())
        assert original['name'] == 'Untitled study'


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
            assert result['runtime_seconds'] is not None and result['runtime_seconds'] > 0
            assert datetime.fromisoformat(result['created_at']) <= datetime.fromisoformat(result['started_at']) <= datetime.fromisoformat(result['finished_at'])
            assert call('/api/studies')[1][0]['runtime_seconds'] == result['runtime_seconds']
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
