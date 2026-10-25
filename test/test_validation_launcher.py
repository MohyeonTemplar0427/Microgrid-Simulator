"""Validation policy, subprocess deadlines and retained resume evidence."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from tools import validate
from tools.validation_support import output_lock, positive_seconds


def options(**changes):
    values = dict(tier="focused", area=[], test=[], include_gui=False, timeout=None,
        regional=False, inputs=None, utility=[], plan=[], period=[], start_date=None,
        end_date=None, ciep_inputs=None, include_ciep=False, include_va_history=False,
        case_timeout=2100., matrix_timeout=3600., output=None, dry_run=False, resume=False)
    return SimpleNamespace(**{**values, **changes})


def test_tiers_have_explicit_coverage_and_no_implicit_gui():
    output = validate.ROOT/".cache/fixture"
    focused = validate.build_plan(options(area=["regional"]), output)
    assert len(focused) == 1
    assert "test/test_regional_dispatch.py" in focused[0]["command"]
    release = validate.build_plan(options(tier="release"), output)
    assert "test" in release[0]["command"]
    assert all("--ignore="+p in release[0]["command"] for p in validate.GUI_TESTS)
    assert any(p["id"].startswith("node-") for p in release)
    assert all("src.simulation.graphical_interface" not in str(p["command"]) for p in release)
    assert validate.build_plan(options(tier="workflow"), output)[0]["timeout_seconds"] == 600
    assert not any(a.startswith("--ignore=") for a in
        validate.build_plan(options(tier="release", include_gui=True), output)[0]["command"])


@pytest.mark.parametrize("tier", ["workflow", "release"])
def test_full_tiers_cannot_be_silently_narrowed(tier):
    with pytest.raises(ValueError, match="cannot narrow"):
        validate.build_plan(options(tier=tier, test=["test/test_battery.py"]), validate.ROOT/".cache/x")


def test_gui_is_explicit_and_test_paths_stay_inside_repository():
    with pytest.raises(ValueError, match="GUI testing is paused"):
        validate.selected_tests("focused", tests=[validate.GUI_TESTS[0]])
    assert validate.selected_tests("focused", tests=[validate.GUI_TESTS[0]], include_gui=True)
    with pytest.raises(ValueError, match="existing paths"):
        validate.selected_tests("focused", tests=["../outside.py"])


@pytest.mark.parametrize("value", [0, -1, "nan", "inf", True])
def test_deadlines_must_be_finite_positive(value):
    with pytest.raises(ValueError):
        positive_seconds(value)


def test_same_output_cannot_be_owned_twice(tmp_path):
    with output_lock(tmp_path, "lock"):
        with pytest.raises(ValueError, match="Another validation"):
            with output_lock(tmp_path, "lock"):
                pytest.fail("Second writer acquired the lock")
    with output_lock(tmp_path, "lock"):
        pass


def test_subprocess_deadline_interrupts_instead_of_waiting_forever(tmp_path):
    log = tmp_path/"timeout.log"
    result = validate.run_process([sys.executable, "-c", "import time; time.sleep(30)"], log, .3)
    assert result["status"] == "timed_out"
    assert result["elapsed_seconds"] < 4
    assert result["returncode"] != 0


@pytest.fixture
def tiny_repo(tmp_path, monkeypatch):
    (tmp_path/"test").mkdir()
    (tmp_path/"test/test_tiny.py").write_text("def test_tiny():\n    assert 2+2 == 4\n")
    monkeypatch.setattr(validate, "ROOT", tmp_path)
    monkeypatch.setattr(validate, "fingerprints", lambda: {"engine_id": "fixture", "source": "unchanged"})
    return options(output=tmp_path/".cache/run", test=["test/test_tiny.py"])


def test_real_pytest_run_and_resume_keeps_original_results(tiny_repo, monkeypatch):
    monkeypatch.setenv("VALIDATION_PRIVATE_SECRET", "must-not-appear-in-report")
    assert validate.run(tiny_repo) == 0
    path = tiny_repo.output/"report.json"
    first = json.loads(path.read_text())
    phase = first["phases"][0]
    assert phase["pytest"]["tests"] == 1 and phase["status"] == "passed"
    assert phase["artifacts"].keys() == {"pytest-attempt-1.log", "pytest-attempt-1.xml"}
    assert "must-not-appear-in-report" not in path.read_text()
    tiny_repo.resume = True
    assert validate.run(tiny_repo) == 0
    second = json.loads(path.read_text())
    assert second["phases"] == first["phases"]
    assert second["sessions"][-1]["reused_phases"] == 1
    assert second["sessions"][-1]["executed_phases"] == 0
    # A changed saved log is not valid reuse evidence; rerun without overwriting it.
    (tiny_repo.output/phase["log"]).write_text("changed")
    assert validate.run(tiny_repo) == 0
    third = json.loads(path.read_text())
    assert third["phases"][0]["log"] == "pytest-attempt-2.log"
    assert len(third["phases"][0]["attempts"]) == 1
    assert (tiny_repo.output/"pytest-attempt-1.xml").exists()


def test_resume_rejects_changed_code_or_selection_without_rewriting_evidence(tiny_repo, monkeypatch):
    assert validate.run(tiny_repo) == 0
    path = tiny_repo.output/"report.json"; original = path.read_bytes()
    tiny_repo.resume = True
    monkeypatch.setattr(validate, "fingerprints", lambda: {"engine_id": "different"})
    with pytest.raises(ValueError, match="changed"):
        validate.run(tiny_repo)
    assert path.read_bytes() == original


def test_dry_run_has_no_output_or_subprocess(tiny_repo, monkeypatch, capsys):
    tiny_repo.dry_run = True
    monkeypatch.setattr(validate, "run_process", lambda *a: pytest.fail("Dry run executed a child"))
    assert validate.run(tiny_repo) == 0
    assert not tiny_repo.output.exists()
    assert '"browser": "not launched"' in capsys.readouterr().out


def test_timeout_is_retained_as_failure_and_never_reused(tiny_repo, monkeypatch):
    calls = []
    def timeout(command, log, limit):
        calls.append(command);log.write_text("deadline fixture")
        return dict(status="timed_out", returncode=-2, elapsed_seconds=.1)
    monkeypatch.setattr(validate, "run_process", timeout)
    assert validate.run(tiny_repo) == 1
    tiny_repo.resume = True
    assert validate.run(tiny_repo) == 1 and len(calls) == 2
    report = json.loads((tiny_repo.output/"report.json").read_text())
    assert report["status"] == "timed_out"
    assert report["phases"][0]["attempts"][0]["status"] == "timed_out"


def test_regional_phase_always_reenters_driver_even_after_pass(tiny_repo, monkeypatch):
    monkeypatch.setattr(validate, "build_plan", lambda a, p: [dict(
        id="regional", command=["fixture"], timeout_seconds=1.)])
    seen = []
    def process(command, log, limit):
        seen.append(command);log.write_text("fixture")
        folder=tiny_repo.output/"regional";folder.mkdir(exist_ok=True)
        (folder/"validation.json").write_text("{}")
        return dict(status="passed", returncode=0, elapsed_seconds=.01)
    monkeypatch.setattr(validate, "run_process", process)
    assert validate.run(tiny_repo) == 0
    tiny_repo.resume = True
    assert validate.run(tiny_repo) == 0
    assert seen == [["fixture"], ["fixture", "--resume"]]


def test_mid_run_source_change_invalidates_pass(tiny_repo, monkeypatch):
    reads=iter([{"source":"before"}, {"source":"after"}])
    monkeypatch.setattr(validate, "fingerprints", lambda: next(reads))
    def process(command, log, limit):
        log.write_text("fixture")
        xml=next(a.split("=",1)[1] for a in command if a.startswith("--junitxml="))
        Path(xml).write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"/></testsuites>')
        return dict(status="passed", returncode=0, elapsed_seconds=.01)
    monkeypatch.setattr(validate, "run_process", process)
    assert validate.run(tiny_repo) == 1
    assert json.loads((tiny_repo.output/"report.json").read_text())["status"] == "invalidated"


@pytest.mark.parametrize("tests,skipped", [(0,0),(2,2)])
def test_empty_or_entirely_skipped_run_cannot_claim_coverage(tiny_repo,monkeypatch,tests,skipped):
    def process(command,log,limit):
        log.write_text("fixture")
        xml=next(a.split("=",1)[1] for a in command if a.startswith("--junitxml="))
        Path(xml).write_text(f'<testsuites><testsuite tests="{tests}" skipped="{skipped}"/></testsuites>')
        return dict(status="passed",returncode=0,elapsed_seconds=.01)
    monkeypatch.setattr(validate,"run_process",process)
    assert validate.run(tiny_repo)==1


def test_bad_matrix_selection_fails_before_tests_or_output(tiny_repo,monkeypatch):
    from tools import run_regional_validation as driver
    monkeypatch.setattr(driver,"ROOT",validate.ROOT)
    tiny_repo.regional=True;tiny_repo.inputs=validate.ROOT/".cache/inputs"
    tiny_repo.inputs.mkdir(parents=True)
    tiny_repo.plan=["not-a-representative-plan"]
    monkeypatch.setattr(validate,"run_process",lambda *a:pytest.fail("Invalid plan ran tests"))
    with pytest.raises(ValueError,match="No selected representative"):
        validate.run(tiny_repo)
    assert not tiny_repo.output.exists()
    tiny_repo.plan=["VA-1G"];tiny_repo.utility=["dominion_energy_virginia"];tiny_repo.period=["annual"]
    with pytest.raises(ValueError,match="No executable cases"):
        validate.run(tiny_repo)
    assert not tiny_repo.output.exists()


def test_ohio_provisional_flag_is_explicit_and_forwarded(tmp_path):
    # No external data required; use a temporary private folder in a fake root.
    from unittest.mock import patch
    from tools import run_regional_validation as driver
    with patch.object(validate,"ROOT",tmp_path), patch.object(driver,"ROOT",tmp_path):
        (tmp_path/"test").mkdir();(tmp_path/"test/test_fixture.py").write_text("# fixture\n")
        inputs=tmp_path/".cache/inputs";inputs.mkdir(parents=True)
        args=options(regional=True,inputs=inputs,test=["test/test_fixture.py"],utility=["firstenergy_ohio_edison"],period=["annual"])
        ordinary=validate.build_plan(args,tmp_path/".cache/out")
        assert "--allow-ohio-provisional" not in ordinary[-1]["command"]
        args.allow_ohio_provisional=True
        opted=validate.build_plan(args,tmp_path/".cache/out")
        assert "--allow-ohio-provisional" in opted[-1]["command"]
        args.regional=False;args.inputs=None;args.utility=[];args.period=[]
        with pytest.raises(ValueError,match="require --regional"):validate.build_plan(args,tmp_path/".cache/out")


def test_we_duke_provisional_flag_is_explicit_and_forwarded(tmp_path):
    from unittest.mock import patch
    from tools import run_regional_validation as driver
    with patch.object(validate,"ROOT",tmp_path), patch.object(driver,"ROOT",tmp_path):
        (tmp_path/"test").mkdir();(tmp_path/"test/test_fixture.py").write_text("# fixture\n")
        inputs=tmp_path/".cache/inputs";inputs.mkdir(parents=True)
        args=options(regional=True,inputs=inputs,test=["test/test_fixture.py"],
                     utility=["we_energies_wisconsin","duke_energy_indiana"],period=["annual"])
        assert "--allow-we-duke-provisional" not in validate.build_plan(args,tmp_path/".cache/out")[-1]["command"]
        args.allow_we_duke_provisional=True
        assert "--allow-we-duke-provisional" in validate.build_plan(args,tmp_path/".cache/out")[-1]["command"]
        args.regional=False;args.inputs=None;args.utility=[];args.period=[]
        with pytest.raises(ValueError,match="require --regional"):
            validate.build_plan(args,tmp_path/".cache/out")
