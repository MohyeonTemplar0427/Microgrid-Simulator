"""Offline-first validation tiers. No native GUI or browser is launched."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validation_support import (  # noqa: E402
    atomic_json, file_hash, output_lock, positive_seconds, utc_now, value_hash,
)

PYTHON = "/usr/local/bin/python3"
GUI_TESTS = ("test/test_application_interface.py", "test/test_desktop_application.py",
             "test/test_graphical_interface.py")
AREAS = {
    "validation": ("test_validation_launcher.py", "test_regional_validation_resume.py",
                   "test_regional_validation_driver.py", "test_regional_coverage.py"),
    "regional": ("test_regional*.py", "test_dominion*.py", "test_pseg_billing.py", "test_firstenergy*.py", "test_ohio_provisional.py", "test_peco*.py", "test_dte*.py"),
    "billing": ("test_billing*.py", "test_tariff*.py", "test_baseline*.py",
                "test_pge_residential.py", "test_pge_commercial.py", "test_tou_holidays.py"),
    "dispatch": ("test_battery.py", "test_*dispatch*.py", "test_regional_relaxation.py"),
    "electrical": ("test_*replay.py", "test_opendss*.py", "test_utility_electrical*.py"),
    "profiles": ("test_pv*.py", "test_timeseries_framework.py", "test_residential_*.py"),
    "web": ("test_local_web*.py", "test_*form_pipeline.py", "test_regional_study.py",
            "test_comed_simulation.py"),
}
WORKFLOW_TESTS = ("test/test_local_web.py", "test/test_local_web_pipeline.py",
    "test/test_regional_study.py", "test/test_socal_form_pipeline.py",
    "test/test_utility_electrical_workflows.py", "test/test_export_settlement.py")


def private_output(path):
    path = Path(path).resolve()
    if not path.is_relative_to((ROOT/".cache").resolve()):
        raise ValueError("Validation reports must stay under this checkout's ignored .cache directory.")
    return path


def selected_tests(tier, areas=(), tests=(), include_gui=False):
    if tier != "focused" and (areas or tests):
        raise ValueError("--area/--test are focused-tier selectors; they cannot narrow a release or workflow claim.")
    if tier == "release":
        chosen = ["test"]
    elif tier == "workflow":
        chosen = list(WORKFLOW_TESTS)
    else:
        chosen = list(tests)
        for area in areas or (() if tests else ("validation",)):
            for pattern in AREAS[area]:
                chosen.extend(p.relative_to(ROOT).as_posix() for p in sorted((ROOT/"test").glob(pattern)))
    for item in chosen:
        path = (ROOT/item.split("::", 1)[0]).resolve()
        if not path.exists() or not path.is_relative_to((ROOT/"test").resolve()):
            raise ValueError("Tests must be existing paths/nodes within test/: "+item)
        if not include_gui and path.relative_to(ROOT).as_posix() in GUI_TESTS:
            raise ValueError("Desktop GUI testing is paused; use --include-gui for an explicit compatibility run.")
    if not chosen:
        raise ValueError("No tests matched the selected area.")
    return sorted(set(chosen))


def fingerprints():
    """Hash current source/tests/tools, rather than trusting the Git commit alone."""
    from src.local_web.runtime import dependencies
    def group(folder, suffixes=None):
        return {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted((ROOT/folder).rglob("*"))
                if p.is_file() and "__pycache__" not in p.parts
                and p.name != ".DS_Store" and (suffixes is None or p.suffix in suffixes)}
    identity = {"files": group("src", {".py"}), "dependencies": dependencies(), "python": sys.version}
    return {"engine_id": value_hash(identity), "source": identity,
        "frontend": group("src/local_web/static"), "tests": group("test"),
        "tools": group("tools", {".py"}),
        "configuration": {p: file_hash(ROOT/p) for p in ("pytest.ini", "requirements.txt")}}


def build_plan(args, output):
    chosen = selected_tests(args.tier, args.area, args.test, args.include_gui)
    pytest = [PYTHON, "-m", "pytest", "-q", "--durations=20",
              "--junitxml="+str(output/"pytest.xml"), *chosen]
    if not args.include_gui:
        pytest.extend("--ignore="+p for p in GUI_TESTS)
    timeout = args.timeout or {"focused": 180., "workflow": 600., "release": 1200.}[args.tier]
    phases = [{"id": "pytest", "command": pytest, "timeout_seconds": timeout}]
    if args.tier != "focused":
        phases.extend({"id": "node-"+p.stem, "command": ["node", "--check", str(p)],
                       "timeout_seconds": 30.} for p in sorted((ROOT/"src/local_web/static").glob("*.js")))
    if args.regional:
        if args.inputs is None:
            raise ValueError("--regional requires --inputs containing already prepared historical data.")
        from tools.run_regional_validation import validation_periods, private_path, selected_cases
        periods = validation_periods(tuple(args.period or ("monthly", "annual")), args.start_date, args.end_date)
        cases = selected_cases(args.utility, args.plan, include_ciep=args.include_ciep,
                               include_va_history=args.include_va_history)
        if not any(period != "annual" or utility != "dominion_energy_virginia"
                   or (args.include_va_history and plan in ("VA-1", "VA-GS1"))
                   for utility, _, plan in cases for period in periods):
            raise ValueError("No executable cases in this selection")
        inputs = private_path(args.inputs)
        if not inputs.is_dir():
            raise ValueError("Prepared input folder does not exist; this launcher never retrieves data.")
        if args.include_ciep:
            ciep = private_path(args.ciep_inputs or ROOT/".cache/regional_historical_inputs/pseg")
            if not all((ciep/name).is_file() for name in ("metadata.json", "rt_hrl_lmps_pseg_resid_agg_2025_boundary.csv")):
                raise ValueError("Verified private CIEP prices/metadata are missing; no substitute is used.")
        command = [PYTHON, str(ROOT/"tools/run_regional_validation.py"), "--execute",
                   "--inputs", str(inputs), "--output", str(output/"regional"),
                   "--case-timeout", str(args.case_timeout)]
        for option, values in (("--utility", args.utility), ("--plan", args.plan), ("--period", args.period)):
            for value in values:
                command.extend([option, value])
        for option, value in (("--start-date", args.start_date), ("--end-date", args.end_date),
                              ("--ciep-inputs", str(private_path(args.ciep_inputs)) if args.ciep_inputs else None)):
            if value is not None:
                command.extend([option, value])
        for option, enabled in (("--include-ciep", args.include_ciep), ("--include-va-history", args.include_va_history), ("--allow-ohio-provisional", getattr(args,"allow_ohio_provisional",False))):
            if enabled:
                command.append(option)
        phases.append({"id": "regional", "command": command, "timeout_seconds": args.matrix_timeout})
    elif any((args.inputs, args.utility, args.plan, args.period, args.start_date, args.end_date,
              args.include_ciep, args.include_va_history, args.ciep_inputs, getattr(args,"allow_ohio_provisional",False))):
        raise ValueError("Regional input/selection flags require --regional.")
    return phases


def stop_process(process):
    """Interrupt first so queue owners can close and stop their isolated workers."""
    if process.poll() is not None:
        return
    for sig, grace in ((signal.SIGINT, 8.), (signal.SIGTERM, 2.), (signal.SIGKILL, 2.)):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=grace)
            return
        except subprocess.TimeoutExpired:
            continue
    raise RuntimeError("Validation child did not exit after termination.")


def run_process(command, log, timeout):
    started = time.monotonic()
    status = "failed"
    with log.open("wb") as stream:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            next_notice = started+30
            while process.poll() is None:
                now = time.monotonic()
                if now-started >= timeout:
                    status = "timed_out"
                    stop_process(process)
                    break
                if now >= next_notice:
                    print(f"Still running ({now-started:.0f}s); log: {log}", flush=True)
                    next_notice = now+30
                time.sleep(min(.1, max(.001, timeout-(now-started))))
            else:
                status = "passed" if process.returncode == 0 else "failed"
        except KeyboardInterrupt:
            status = "interrupted"
            stop_process(process)
    return {"status": status, "returncode": process.returncode,
            "elapsed_seconds": time.monotonic()-started}


def junit_summary(path):
    if not path.exists():
        return None
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    return {key: sum(float(s.get(key, 0)) for s in suites)
            for key in ("tests", "failures", "errors", "skipped", "time")}


def run(args):
    output = private_output(args.output or ROOT/".cache/validation_runs"/
        (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:8]))
    phases = build_plan(args, output)
    if args.dry_run:
        print(json.dumps({"tier": args.tier, "output": str(output), "phases": phases,
            "gui_tests_included": args.include_gui, "browser": "not launched"}, indent=2))
        return 0
    output.mkdir(parents=True, exist_ok=True)
    with output_lock(output, ".launcher.lock"):
        report_path = output/"report.json"
        current = fingerprints()
        selection = {"tier": args.tier, "phases": phases, "include_gui": args.include_gui}
        if report_path.exists():
            if not args.resume:
                raise ValueError("Report exists; use --resume or a fresh output directory.")
            report = json.loads(report_path.read_text())
            if report["fingerprints"] != current or report["selection"] != selection:
                raise ValueError("Source, tests, frontend, dependencies or selection changed; use a fresh output directory.")
        elif args.resume:
            raise ValueError("No launcher report exists to resume.")
        else:
            report = {"schema_version": 1, "fingerprints": current, "selection": selection, "phases": [],
                "sessions": [], "browser_acceptance": "not run by launcher",
                "timing_scope": "Monotonic wall time; not CPU/development time. Queue wait includes worker execution.",
                "browser_tool_wait_seconds": 0.,
                "excluded_gui_modules": [] if args.include_gui else list(GUI_TESTS)}
        started = time.monotonic()
        session = {"started_at": utc_now(), "resumed": args.resume, "executed_phases": 0,
                   "reused_phases": 0, "executed_phase_seconds": 0.}
        report["sessions"].append(session)
        report["status"] = "running"
        atomic_json(report_path, report)
        print("Validation report:", report_path, flush=True)
        try:
            for phase in phases:
                previous = next((p for p in report["phases"] if p["id"] == phase["id"]), None)
                # Regional phases always enter the driver to verify/re-audit
                # individual cases; launcher report hashes alone are insufficient.
                artifacts = previous.get("artifacts", {}) if previous else {}
                valid = previous and previous["status"] == "passed" and previous.get("returncode") == 0 and bool(artifacts)
                if valid and phase["id"] != "regional":
                    valid = all(Path(name).name == name and (output/name).is_file() and file_hash(output/name) == digest
                                for name, digest in artifacts.items())
                    if valid:
                        session["reused_phases"] += 1
                        print("Reusing verified phase:", phase["id"], flush=True)
                        continue
                attempts = previous.get("attempts", [])+[{
                    k: v for k, v in previous.items() if k != "attempts"}] if previous else []
                item = {"id": phase["id"], "status": "running", "attempts": attempts,
                        "started_at": utc_now()}
                report["phases"] = [p for p in report["phases"] if p["id"] != phase["id"]]+[item]
                session["executed_phases"] += 1
                command = list(phase["command"])
                xml_path = output/f"pytest-attempt-{len(attempts)+1}.xml"
                if phase["id"] == "pytest":
                    command = ["--junitxml="+str(xml_path) if arg.startswith("--junitxml=") else arg
                               for arg in command]
                if phase["id"] == "regional" and (output/"regional/validation.json").exists():
                    command.append("--resume")
                log = output/(phase["id"]+f"-attempt-{len(attempts)+1}.log")
                item.update(command=command, log=log.name)
                atomic_json(report_path, report)
                print("Running:", phase["id"], flush=True)
                item.update(run_process(command, log, phase["timeout_seconds"]))
                session["executed_phase_seconds"] += item["elapsed_seconds"]
                item["finished_at"] = utc_now()
                item["artifacts"] = {log.name: file_hash(log)}
                if phase["id"] == "pytest" and xml_path.exists():
                    summary = junit_summary(xml_path)
                    item.update(pytest=summary)
                    item["artifacts"][xml_path.name] = file_hash(xml_path)
                    if summary["tests"] <= summary["skipped"] or summary["failures"] or summary["errors"]:
                        item["status"] = "failed"
                elif phase["id"] == "pytest" and item["status"] == "passed":
                    item.update(status="failed", reason="Pytest returned without a JUnit test record.")
                if fingerprints() != current:
                    item["status"] = "invalidated"
                    item["reason"] = "Checkout changed during validation; no frozen-candidate pass claimed."
                atomic_json(report_path, report)
                print(phase["id"], item["status"], f"{item['elapsed_seconds']:.2f}s", flush=True)
                if item["status"] != "passed":
                    report["status"] = item["status"]
                    return 130 if item["status"] == "interrupted" else 1
            report["status"] = "passed"
            return 0
        except KeyboardInterrupt:
            report["status"] = "interrupted"
            return 130
        except (OSError, ValueError, RuntimeError) as exc:
            report.update(status="failed", error=str(exc))
            if "item" in locals() and item["status"] == "running":
                item.update(status="failed", error=str(exc), finished_at=utc_now())
            raise
        finally:
            session.update(finished_at=utc_now(), elapsed_seconds=time.monotonic()-started)
            atomic_json(report_path, report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=("focused", "workflow", "release"), default="focused")
    parser.add_argument("--area", choices=tuple(AREAS), action="append", default=[])
    parser.add_argument("--test", action="append", default=[], help="Explicit test path or node; focused tier only")
    parser.add_argument("--include-gui", action="store_true", help="Opt in to desktop compatibility tests")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=positive_seconds, help="Per pytest-phase wall-clock deadline")
    parser.add_argument("--matrix-timeout", type=positive_seconds, default=3600.)
    parser.add_argument("--case-timeout", type=positive_seconds, default=2100.)
    parser.add_argument("--regional", action="store_true", help="Also execute the existing private historical matrix")
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--ciep-inputs", type=Path)
    from src.billing.regional import UTILITIES
    parser.add_argument("--utility", choices=tuple(UTILITIES), action="append", default=[])
    parser.add_argument("--plan", action="append", default=[])
    parser.add_argument("--period", choices=("monthly", "annual", "custom"), action="append", default=[])
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--include-ciep", action="store_true")
    parser.add_argument("--allow-ohio-provisional", action="store_true")
    parser.add_argument("--include-va-history", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (ValueError, OSError, RuntimeError) as exc:
        print("Validation error:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
