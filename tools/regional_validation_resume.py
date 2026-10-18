"""Resume policy for the regional driver; this never certifies tariff arithmetic."""
import json
from pathlib import Path

from tools.validation_support import file_hash, value_hash


def validator_files():
    here = Path(__file__).parent
    return {name: file_hash(here/name) for name in (
        "run_regional_validation.py", "regional_validation_resume.py", "validation_support.py")}


def previous_manifest(output, resume, execution):
    path = output/"validation.json"
    if not path.exists():
        if resume:
            raise ValueError("No resumable manifest exists in this output directory.")
        if (output/"runs").exists() and any((output/"runs").iterdir()):
            raise ValueError("Unmanifested studies exist; choose a fresh output directory.")
        return None
    if not resume:
        raise ValueError("Validation output exists; use --resume or a fresh output directory.")
    old = json.loads(path.read_text())
    if (old.get("format_version") != 2 or old.get("execution") != execution
            or old.get("validator_files") != validator_files()):
        raise ValueError("Resume selection or validator changed; use a fresh output directory. Legacy evidence is not relabeled.")
    return old


def reusable(entry, request, directory, engine_id):
    """Hash checks precede the driver's mandatory independent physical/bill audit."""
    if entry.get("status") != "completed" or entry.get("validation") != "passed":
        return False
    if entry.get("request_fingerprint") != value_hash(request):
        raise ValueError("Prepared case inputs changed; use a fresh output directory.")
    hashes = entry.get("source_artifacts", {})
    required = {"request.json", "result.json", "inputs.csv", "comparison.csv",
                "billing-components.csv", "billing-cycles.csv", "ac-summary.csv"}
    required.update(f"{prefix}-{scenario}.csv" for prefix in ("dispatch", "ac")
                    for scenario in ("grid_only", "pv_only", "pv_battery"))
    if not required.issubset(hashes):
        return False
    for name, expected in hashes.items():
        if Path(name).name != name or not (directory/name).is_file() or file_hash(directory/name) != expected:
            return False
    result = json.loads((directory/"result.json").read_text())
    saved = json.loads((directory/"request.json").read_text())
    return result.get("engine_id") == engine_id and value_hash(saved) == value_hash(request)


def archived_attempt(entry):
    return {k: v for k, v in entry.items() if k != "attempts"}
