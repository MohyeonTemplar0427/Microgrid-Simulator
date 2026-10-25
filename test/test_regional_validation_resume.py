"""Offline orchestration fixtures: resume never upgrades unverified evidence."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pandas as pd
import pytest

from tools import run_regional_validation as driver
from tools import regional_validation_resume as policy


@pytest.fixture
def matrix(tmp_path, monkeypatch):
    from src.local_web import runtime
    monkeypatch.setattr(driver, "ROOT", tmp_path)
    src=tmp_path/"src";src.mkdir();(src/"fixture.py").write_text("# frozen\n")
    output=tmp_path/".cache/run";inputs=tmp_path/".cache/inputs";inputs.mkdir(parents=True)
    weather=inputs/"fixture.txt";weather.write_text("original weather")
    state=SimpleNamespace(submissions=0, audits=0, closed=0, mode="completed", cancelled=[], engine="fixture")
    class App:
        def __init__(self, path):
            self.engine={"id":state.engine,"files":{"src/fixture.py":driver.digest(src/"fixture.py")}}
            self.store=SimpleNamespace(submit=self.submit,get=self.get,cancel=state.cancelled.append)
        def submit(self, request, engine):
            state.submissions+=1;identity=f"{state.submissions:032x}";folder=output/"runs"/identity
            folder.mkdir(parents=True)
            for name in ("inputs.csv", "billing-components.csv", "billing-cycles.csv", "ac-summary.csv"):
                (folder/name).write_text("fixture\n")
            for prefix in ("dispatch","ac"):
                for scenario in driver.SCENARIOS:(folder/f"{prefix}-{scenario}.csv").write_text("fixture\n")
            (folder/"request.json").write_text(json.dumps(request))
            (folder/"result.json").write_text(json.dumps({"engine_id":engine["id"]}))
            pd.DataFrame([dict(scenario="grid_only",utility_bill_usd=10.)]).to_csv(folder/"comparison.csv",index=False)
            return {"id":identity}
        def get(self, identity):
            return {"status":state.mode,"progress":"fixture", "runtime_seconds":.01}
        def close(self):state.closed+=1
    def audit(*args,**kwargs):
        state.audits+=1
        return (pd.DataFrame([dict(scenario="grid_only",is_complete_bill=True,objective_scope="complete_utility_bill",rate_evidence_status="not_recorded")]),
                pd.DataFrame([dict(scenario="grid_only",component="fixed",amount_usd=10.,
                                   rate_evidence_status="not_recorded",rate_assumption_ids="[]")]),
                [dict(scenario=s) for s in driver.SCENARIOS])
    monkeypatch.setattr(runtime,"Application",App)
    monkeypatch.setattr(driver,"case_request",lambda *args,**kwargs:{"fixture":"same account"})
    monkeypatch.setattr(driver,"attach_weather",lambda app,r,inputs:r.update(weather=weather.read_text()))
    monkeypatch.setattr(driver,"audit",audit)
    monkeypatch.setattr(driver,"summarize",lambda folder:None)
    def run(**kwargs):
        return driver.run(output,inputs,cases=[("pseg","residential","RS")],periods=("monthly",),**kwargs)
    return SimpleNamespace(run=run,state=state,output=output,weather=weather)


def test_resume_reaudits_passed_case_without_resolving(matrix):
    first=matrix.run();second=matrix.run(resume=True)
    assert matrix.state.submissions==1 and matrix.state.audits==2
    assert first["cases"][0]["study_id"]==second["cases"][0]["study_id"]
    assert second["sessions"][-1]["reused_cases"]==1
    assert second["sessions"][-1]["executed_cases"]==0
    assert second["cases"][0]["timing"]["artifact_audit_seconds"]>=0
    assert second["cases"][0]["resume_checks"][0]["timing"]["resume_audit_seconds"]>=0


@pytest.mark.parametrize("change",["changed","missing"])
def test_invalid_artifact_is_rerun_and_original_attempt_retained(matrix,change):
    first=matrix.run();sid=first["cases"][0]["study_id"]
    path=matrix.output/"runs"/sid/"inputs.csv"
    if change=="missing":path.unlink()
    else:path.write_text("changed")
    second=matrix.run(resume=True)
    assert matrix.state.submissions==2
    assert second["cases"][0]["study_id"]!=sid
    assert second["cases"][0]["attempts"][0]["study_id"]==sid
    assert (matrix.output/"runs"/sid/"request.json").exists()


def test_changed_inputs_do_not_replace_previous_evidence(matrix):
    first=matrix.run();old=deepcopy(first["cases"])
    matrix.weather.write_text("different weather")
    with pytest.raises(ValueError,match="inputs changed"):
        matrix.run(resume=True)
    assert matrix.state.submissions==1
    saved=json.loads((matrix.output/"validation.json").read_text())
    assert saved["cases"]==old
    assert saved["sessions"][-1]["status"]=="failed_or_interrupted"


def test_changed_engine_does_not_overwrite_manifest(matrix):
    matrix.run();path=matrix.output/"validation.json";before=path.read_bytes()
    matrix.state.engine="another-engine"
    with pytest.raises(ValueError,match="engine changed"):
        matrix.run(resume=True)
    assert path.read_bytes()==before


def test_changed_validator_or_selection_rejects_resume(matrix,monkeypatch):
    matrix.run();path=matrix.output/"validation.json";before=path.read_bytes()
    monkeypatch.setattr(policy,"validator_files",lambda:{"changed":"hash"})
    with pytest.raises(ValueError,match="validator changed"):
        matrix.run(resume=True)
    assert path.read_bytes()==before


def test_existing_run_requires_explicit_resume(matrix):
    matrix.run()
    with pytest.raises(ValueError,match="use --resume"):
        matrix.run()


def test_case_timeout_cancels_and_retry_keeps_failed_attempt(matrix):
    matrix.state.mode="running"
    with pytest.raises(ValueError,match="Validation failed"):
        matrix.run(case_timeout=.01)
    saved=json.loads((matrix.output/"validation.json").read_text());old=saved["cases"][0]
    assert old["status"]=="timed_out" and old["validation"]=="failed"
    assert matrix.state.cancelled==[old["study_id"]]
    matrix.state.mode="completed"
    after=matrix.run(case_timeout=.01,resume=True)
    assert after["cases"][0]["validation"]=="passed"
    assert after["cases"][0]["attempts"][0]["status"]=="timed_out"


def test_failed_independent_reaudit_cannot_reuse_a_pass(matrix,monkeypatch):
    matrix.run();real=driver.audit;seen=[]
    def audit(*args,**kwargs):
        seen.append(True)
        if len(seen)==1:raise AssertionError("Bill no longer reconciles")
        return real(*args,**kwargs)
    monkeypatch.setattr(driver,"audit",audit)
    result=matrix.run(resume=True)
    assert matrix.state.submissions==2 and len(seen)==2
    assert result["cases"][0]["validation"]=="passed"


def test_legacy_manifest_is_not_silently_upgraded(tmp_path):
    (tmp_path/"validation.json").write_text('{"engine_id":"old","cases":[]}')
    with pytest.raises(ValueError,match="Legacy evidence"):
        policy.previous_manifest(tmp_path,True,{})


def test_interrupted_case_keeps_study_id_and_can_be_retried(matrix,monkeypatch):
    real=driver.audit
    monkeypatch.setattr(driver,"audit",lambda *a,**kw:(_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):matrix.run()
    saved=json.loads((matrix.output/"validation.json").read_text())
    prior=saved["cases"][0]
    assert prior["study_id"] and prior["validation"]=="interrupted"
    assert matrix.state.closed==1
    monkeypatch.setattr(driver,"audit",real)
    result=matrix.run(resume=True)
    assert result["cases"][0]["study_id"]!=prior["study_id"]
    assert result["cases"][0]["attempts"][0]["study_id"]==prior["study_id"]
