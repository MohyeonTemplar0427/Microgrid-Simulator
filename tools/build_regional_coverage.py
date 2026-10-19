"""Build a catalog/evidence coverage matrix without APIs or running studies.

Implemented catalog rows are not simulation acceptance evidence. This command
reads the optional private validation manifest and verifies retained request/result
fingerprints before attaching a completed audited case to its exact plan/supplier.
It never copies interval data, wholesale prices, credentials or requests into docs.
"""
from __future__ import annotations

import argparse
import csv
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

UTILITY_DOCS = {
    "dominion_energy_virginia": ("docs/Dominion_Virginia_General.md", "docs/utility_sources/dominion/va_general_2026/manifest.json", "test/test_dominion_va_general.py"),
    "dominion_energy_north_carolina": ("docs/Dominion_North_Carolina.md", "docs/utility_sources/dominion_nc/manifest.json", "test/test_dominion_nc.py"),
    "pseg": ("docs/PSEG_New_Jersey_Billing.md", "docs/utility_sources/pseg/manifest.json", "test/test_pseg_billing.py"),
    "firstenergy_pa_west_penn": ("docs/FirstEnergy.md", "docs/utility_sources/firstenergy/manifest.json", "test/test_firstenergy.py"),
    "firstenergy_ohio_edison": ("docs/FirstEnergy.md", "docs/utility_sources/firstenergy/manifest.json", "test/test_firstenergy.py"),
    "peco": ("docs/PECO.md", "docs/utility_sources/peco/manifest.json", "test/test_peco.py"),
}
DEFAULT_EVIDENCE = (".cache/regional_validation_release_20261015/validation.json",
                    ".cache/regional_validation_va_history_20261015/validation.json")

FIELDS = ["utility_id", "utility", "jurisdiction", "customer_class", "tariff", "label", "supply", "status",
    "eligibility", "coverage", "coverage_basis", "coverage_is_complete_bill", "coverage_scope", "coverage_excluded_components", "base_effective_start", "billing", "dispatch", "main_browser", "billing_path",
    "dispatch_path", "browser_path", "equipment_modes", "solar_modes", "electrical_replay", "unit_structure_evidence",
    "unit_test_path", "monthly_status", "monthly_studies", "monthly_engines", "monthly_evidence", "monthly_manifests", "monthly_bill_scopes",
    "annual_status", "annual_studies", "annual_engines", "annual_evidence", "annual_manifests", "annual_bill_scopes", "source_manifest", "utility_document",
    "source_pdf_pages", "source_urls", "capacity_transmission"]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def relative(path, root):
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return str(Path(path).resolve())


def evidence_snapshot(manifest_path, *, root=ROOT):
    """Read one consistent manifest snapshot; unverified evidence stays explicit."""
    path = Path(manifest_path)
    metadata = {"manifest": relative(path, root), "available": False, "sha256": "", "engine_id": "",
                "current_source_matches_pin": None, "scope": "", "blocked_scope": {}}
    if not path.exists():
        return [], metadata
    raw = path.read_bytes()
    try:
        manifest = json.loads(raw)
    except (ValueError, UnicodeError):
        metadata["read_warning"] = "Manifest is unreadable or being written; no completion inferred. Regenerate after the run."
        return [], metadata
    metadata.update(available=True, sha256=hashlib.sha256(raw).hexdigest(),
        engine_id=manifest.get("engine_id", ""), scope=manifest.get("scope", ""), blocked_scope=manifest.get("blocked_scope", {}))
    engine_file = path.parent/"engine.json"
    if engine_file.exists():
        engine = read_json(engine_file)
        pinned = engine.get("files", {})
        current = {p.relative_to(root).as_posix(): sha256(p) for p in (Path(root)/"src").rglob("*.py")}
        metadata["current_source_matches_pin"] = current == pinned and engine.get("id") == metadata["engine_id"]
    results = []
    for entry in manifest.get("cases", []):
        record = {"case": entry.get("case", ""), "utility": entry.get("utility", ""), "plan": "", "supply": "",
                  "period": entry.get("period", ""), "study_id": entry.get("study_id", ""),
                  "status": entry.get("status", "pending"), "validation": entry.get("validation", "pending"),
                  "evidence_status": "pending", "engine_id": metadata["engine_id"], "dates": "", "scenarios": "",
                  "artifact": "", "reason": entry.get("error", ""), "manifest":metadata["manifest"],
                  "manifest_sha256":metadata["sha256"],"bill_is_complete":None,"objective_scope":"unrecorded",
                  "excluded_components":[],"coverage_start":"","coverage_end":""}
        if not re.fullmatch(r"[0-9a-f]{32}", record["study_id"]):
            record["evidence_status"] = "not_completed" if record["status"] != "completed" else "evidence_incomplete"
            results.append(record)
            continue
        directory = path.parent/"runs"/record["study_id"]
        request_file, result_file = directory/"request.json", directory/"result.json"
        record["artifact"] = relative(result_file if result_file.exists() else request_file, root)
        try:
            request = read_json(request_file)
            account = request["account"]
            record.update(plan=account["tariff"], supply=account.get("supply", account.get("supplier", account.get("supply_arrangement", "bundled"))),
                          dates=request["start_date"]+" → "+request["end_date"],
                          coverage_start=request["start_date"],coverage_end=request["end_date"])
            if record["utility"]=="pseg":
                bill_dates=[c["bill_date"] for c in request.get("billing_cycles",[]) if c.get("bill_date")] or [account.get("bill_date")]
                if all(isinstance(d,str) for d in bill_dates):
                    record.update(coverage_start=min(bill_dates),coverage_end=max(bill_dates))
            if request["site"]["utility"] != record["utility"]:
                raise ValueError("Manifest and request utility differ")
            if record["status"] != "completed" or record["validation"] != "passed":
                record["evidence_status"] = "failed" if record["validation"] == "failed" or record["status"] in ("failed", "cancelled") else "pending"
                results.append(record)
                continue
            artifacts = entry.get("source_artifacts", {})
            for filename in ("request.json", "result.json"):
                if artifacts.get(filename) != sha256(directory/filename):
                    raise ValueError("Retained "+filename+" fingerprint missing or changed")
            result = read_json(result_file)
            if result.get("engine_id") != record["engine_id"]:
                raise ValueError("Result engine differs from validation pin")
            scenarios = [r["scenario"] for r in entry.get("physics", [])]
            if len(scenarios) != 3 or set(scenarios) != {"grid_only", "pv_only", "pv_battery"}:
                raise ValueError("Audited three-scenario evidence missing")
            if record["period"] == "annual" and not (request["start_date"][5:] == "01-01" and request["end_date"][5:] == "12-31" and request["start_date"][:4] == request["end_date"][:4]):
                raise ValueError("Annual evidence does not cover one complete calendar year")
            bill_flags=[result.get("is_complete_bill")]
            excluded=set()
            for bills in result.get("billing",{}).values():
                for bill in bills:
                    bill_flags.append(bill.get("is_complete_bill"))
                    excluded.update(bill.get("excluded_components",[]))
            known=[v for v in bill_flags if type(v) is bool]
            complete=False if False in known else True if known and len(known)==len(bill_flags) else None
            if type(entry.get("is_complete_bill")) is bool and complete is not None and entry["is_complete_bill"]!=complete:
                raise ValueError("Manifest bill completeness contradicts retained results")
            scope=("complete_bill" if complete is True else ("verified_charges_subtotal" if excluded or entry.get("objective_scope")=="verified_charges_subtotal" else "incomplete_bill_estimate") if complete is False else "bill_completeness_unrecorded")
            record.update(evidence_status="audited_complete" if complete is True else "audited_partial_bill" if complete is False else "audited_scope_unknown",
                bill_is_complete=complete,objective_scope=scope,excluded_components=sorted(excluded),scenarios=", ".join(scenarios))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            record.update(evidence_status="evidence_incomplete", reason=str(exc))
        results.append(record)
    return results, metadata


def evidence_snapshots(paths, *, root=ROOT):
    """Combine distinct manifest snapshots without erasing their provenance."""
    records, manifests, seen=[],[],set()
    for path in paths:
        key=str(Path(path).resolve())
        if key in seen:
            continue
        seen.add(key)
        cases,meta=evidence_snapshot(path,root=root)
        records.extend(cases);manifests.append(meta)
    engines=list(dict.fromkeys(m["engine_id"] for m in manifests if m["engine_id"]))
    return records,{"manifests":manifests,"engine_ids":engines,"mixed_engine_pins":len(engines)>1}


def coverage_segments(plan):
    # Separate capability windows, rather than implying continuous coverage
    # between endpoints or complete bills for a tax-incomplete historical path.
    return plan.get("coverage") or [{"start":"","end":"","is_complete_bill":None,"scope":"Unavailable"}]


def evidence_in_segment(record, segment):
    if not segment.get("start") or not record.get("coverage_start") or not record.get("coverage_end"):
        return False
    return record["coverage_start"]<=segment["end"] and record["coverage_end"]>=segment["start"]


def nc_eligibility(root):
    """Reuse the reviewed plan table where the catalog has generic eligibility."""
    path = Path(root)/UTILITY_DOCS["dominion_energy_north_carolina"][0]
    result = {}
    if path.exists():
        for line in path.read_text().splitlines():
            cells = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(cells) == 4 and cells[0] in {"1", "1P", "1T", "5", "5P", "6P", "6L"}:
                result[cells[0]] = cells[1]
    return result


def unit_scope(utility, plan, supply, enabled):
    if not enabled:
        return "No executable-plan acceptance claim; rejection/catalog coverage only"
    if utility.startswith("firstenergy_"):
        return "Independent filed-arithmetic benchmarks, demand/state/date/DST tests and main-form queued-worker reconciliation; no customer-bill calibration claim"
    if utility == "dominion_energy_virginia":
        return "Defined: every supported numeric structure and fixed-schedule MILP parity fixtures"
    if utility == "dominion_energy_north_carolina":
        return "Defined: every ordinary numeric structure; complete-2025 numeric cycles; selected MILP parity fixtures"
    if supply == "bgs_ciep":
        return ("Component fixtures only: CIEP GLP supply plus NIGHT delivery; combined CIEP NIGHT not separately parameterized" if plan == "GLP_NIGHT" else
                "Defined: exact CIEP numeric plan fixture; variable-dispatch acceptance fixture only for GLP")
    return "Defined: current/historical RSCP numeric plan fixtures; selected variable-dispatch parity fixtures"


def replay_scope(module, plan, enabled):
    if not enabled:
        return "Unavailable: plan disabled"
    account = module.defaults(plan["id"])
    voltage = plan.get("voltage", account.get("voltage", "secondary"))
    if voltage != "secondary":
        return "Unavailable: "+voltage+" service has no matching primary/HV reference circuit"
    phase = account.get("phase", "single" if plan.get("customer_class") == "residential" else "three")
    if phase == "single":
        nominal = account.get("voltage_v", account.get("delivery_voltage_kv", .24)*1000)
        description = "120/240 V split-phase reference" if plan.get("customer_class") == "residential" else "240 V single-phase commercial reference"
    else:
        nominal = account.get("voltage_v", account.get("delivery_voltage_kv", .48)*1000)
        description = "480 V three-phase reference"
    if nominal != (240 if phase == "single" else 480):
        return "Unavailable: declared nominal voltage lacks a matching reference circuit"
    return description+" only; primary/HV configurations unavailable; no site-specific claim"


def build_rows(catalogs=None, *, evidence=(), root=ROOT):
    from src.billing.regional import adapter, catalog
    catalogs = catalog() if catalogs is None else deepcopy(catalogs)
    nc_notes = nc_eligibility(root)
    rows = []
    for utility, data in catalogs.items():
        module = adapter(utility)
        document, manifest, tests = UTILITY_DOCS[utility]
        for plan in data["plans"]:
            enabled = plan.get("status") == "supported"
            supplies = plan.get("supply_arrangements") or ["unavailable"]
            for supply in supplies:
                for segment in coverage_segments(plan):
                    matched = [x for x in evidence if (x["utility"], x["plan"], x["supply"]) == (utility, plan["id"], supply) and evidence_in_segment(x,segment)]
                    row = dict.fromkeys(FIELDS, "")
                    row.update(utility_id=utility, utility=data["label"], jurisdiction=data["state"],
                        customer_class=plan.get("customer_class", "special/unspecified; consult eligibility"), tariff=plan["id"], label=plan["label"],
                        supply=supply, status=plan["status"], eligibility=(nc_notes.get(plan["id"]) if utility.endswith("north_carolina") and enabled else None) or plan.get("eligibility") or plan.get("reason") or "Explicit utility account confirmation required",
                        coverage=segment["start"]+" → "+segment["end"] if segment["start"] else "Unverified / not executable",
                        coverage_is_complete_bill=segment.get("is_complete_bill",True) if enabled else None,
                        coverage_scope=segment.get("scope","Complete bill supported within validated account restrictions" if enabled else "Unavailable"),
                        coverage_excluded_components="Dated historical taxes; see historical_tax_research_status.json" if segment.get("is_complete_bill") is False else "",
                        coverage_basis="mixed service dates and bills-rendered components; see utility document" if utility.startswith("firstenergy_") else "bill date" if utility == "pseg" else "service dates",
                        base_effective_start=plan.get("base_effective_start", "See independent component timeline in utility document"),
                        billing="implemented verified-charges subtotal; incomplete taxes" if segment.get("is_complete_bill") is False else "implemented, eligibility bounded" if enabled else "disabled",
                        dispatch="implemented subtotal optimum only; complete-bill optimum unavailable" if segment.get("is_complete_bill") is False else "implemented, primary optimum required" if enabled else "disabled",
                        main_browser="implemented schema-11 path; case evidence separate" if enabled else "identified, disabled",
                        billing_path="src/billing/"+module.__name__.rsplit(".", 1)[-1]+".py::charge_lines" if enabled else "",
                        dispatch_path="src/dispatch/regional.py::optimize_cycle" if enabled else "",
                        browser_path="src/local_web/static/regional.js → src/local_web/regional_study.py → src/local_web/worker.py" if enabled else "",
                        equipment_modes=", ".join(plan.get("equipment_modes", [])) or ("Subject to explicit equipment/account validation" if enabled else "unavailable"),
                        solar_modes=", ".join(plan.get("solar_modes", [])) or ("Unavailable: ordinary parallel generation excluded" if plan.get("equipment_modes") == ["grid_only"] else "Not declared by catalog; see utility validator/document" if enabled else "unavailable"),
                        electrical_replay=replay_scope(module, plan, enabled), unit_structure_evidence=unit_scope(utility, plan["id"], supply, enabled),
                        unit_test_path=tests, source_manifest=manifest, utility_document=document,
                        source_pdf_pages=", ".join(map(str, plan.get("source_pages", []))),
                        source_urls="; ".join(dict.fromkeys(plan.get("sources", []))),
                        capacity_transmission=("Unavailable; no charge treatment inferred" if not enabled else ("Separate dated utility-assigned generation and transmission obligations; never inferred from monthly meter peak" if utility == "pseg" and plan["id"] in module.COMMERCIAL else "Included in default retail supply; no extra wholesale capacity/transmission added") if utility == "pseg" else "Bundled retail charges/riders; no extra wholesale PLC/NSPL charge added"))
                    for period in ("monthly", "annual"):
                        cases = [x for x in matched if x["period"] == period]
                        complete = [x for x in cases if x["evidence_status"] == "audited_complete" and segment.get("is_complete_bill") is not False]
                        conflicting = [x for x in cases if x["evidence_status"] == "audited_complete" and segment.get("is_complete_bill") is False]
                        partial = [x for x in cases if x["evidence_status"] == "audited_partial_bill"]
                        row[period+"_status"] = ("audited complete-bill representative case" if complete else "audited verified-charges subtotal only; missing taxes/components" if partial and all(x["objective_scope"]=="verified_charges_subtotal" for x in partial) else "audited incomplete-bill estimate; unresolved assumptions" if partial else "scope conflict: audit claims complete but catalog supports subtotal only" if conflicting else "; ".join(sorted(set(x["evidence_status"] for x in cases))) or
                            ("blocked: historical composite unavailable for this plan" if period == "annual" and utility.endswith("virginia") and enabled and not any(x.get("start","").startswith("2025") for x in plan.get("coverage",[])) else "not evidenced"))
                        row[period+"_studies"] = "; ".join(x["study_id"] for x in cases)
                        row[period+"_engines"] = "; ".join(dict.fromkeys(x["engine_id"] for x in cases))
                        row[period+"_evidence"] = "; ".join(x["artifact"] for x in cases)
                        row[period+"_manifests"] = "; ".join(dict.fromkeys(x["manifest"]+" [sha256="+x["manifest_sha256"]+"]" for x in cases))
                        row[period+"_bill_scopes"] = "; ".join(dict.fromkeys(x["objective_scope"]+("; excluded: "+", ".join(x["excluded_components"]) if x["excluded_components"] else "") for x in cases))
                    if utility=="dominion_energy_virginia" and segment.get("is_complete_bill") is False:
                        from src.billing.dominion_va_historical_data import SOURCE_DOCUMENTS,BASE_SOURCES
                        row["billing_path"]="src/billing/dominion_va_general.py → src/billing/dominion_va_historical.py::charge_lines"
                        row["source_manifest"]="docs/utility_sources/dominion/va_history_research/approved_2024_2025/manifest.json"
                        row["source_pdf_pages"]="See normalized_2025_components.csv for independent document/page references; current-book pages do not apply"
                        row["source_urls"]="; ".join(sorted({x["source_url"] for x in SOURCE_DOCUMENTS.values()}|{BASE_SOURCES[plan["id"]]["source_url"]}))
                        row["solar_modes"]="non_export only; historical NEM unavailable"
                        row["base_effective_start"]=BASE_SOURCES[plan["id"]]["effective_start"]
                    rows.append(row)
    return rows


def markdown(rows, evidence, metadata):
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    def link(label, path):
        return "["+str(label)+"](../"+path+")"
    out = ["# Regional utility coverage matrix", "",
        "Generated from the live Dominion Virginia, Dominion North Carolina and PSE&G catalogs. Each row is one plan, declared supply arrangement and verified coverage segment. Historical subtotals and current complete-bill capabilities are separate rows. Identification in a dropdown is separate from implemented billing, defined unit fixtures, and completed study evidence.", "",
        "Regenerate without API calls or running simulations:", "", "```sh",
        "/usr/local/bin/python3 tools/build_regional_coverage.py "+" ".join("--evidence "+shlex.quote(m["manifest"]) for m in metadata["manifests"]), "```", "",
        "The machine-readable [CSV](Regional_Utility_Coverage.csv) includes every eligibility statement, supported date window, official source URL, code path, study ID and engine ID. This snapshot is local candidate coverage; it does not promote an engine or establish account eligibility.", "",
        "## Evidence boundaries", "",
        "- **Implemented** means the shared main-browser/worker path calls the utility's dated authoritative billing expressions and optimizer. Account, equipment and history restrictions still apply.",
        "- **Defined fixtures** means the cited test module contains structure checks. This generator does not execute tests or infer a passing regression run. Fixed-meter and component fixtures are not full-year optimized studies.",
        "- **Audited** requires `completed` plus `validation=passed`, matching retained request/result fingerprints and engine ID, and all three scenario audit records. Complete-bill evidence additionally requires explicit complete-bill flags. A passed audit of a verified-charges subtotal remains **partial**; omitted decision-dependent taxes prevent a complete utility-bill optimum claim. Only the exact plan, supplier, period and overlapping coverage segment receive evidence.",
        "- Annual studies use rolling-cycle historical perfect foresight with continuous SOC and actual scenario histories. They are not annual optimum proofs, measured-customer validation or prospective operating strategies.",
        "- Secondary replay uses a representative 120/240 V split-phase or 480 V three-phase circuit. Primary, subtransmission, transmission, high-voltage and unmatched nominal-voltage service remain electrically unevaluated. Circuit overload is a reported result, not a reason to alter retail bills.",
        "- Export/NEM support is bounded by each utility's rules. Non-export validation cases do not validate export ledgers. Wholesale data and retail supply remain separate; private interval/price-derived artifacts are linked locally and are not copied into this document.", ""]
    out += ["## Validation provenance", "",
        "Each manifest keeps its engine, scope and fingerprint. Mixed engine pins are not combined into a new-engine acceptance claim. Mixed pins present: **"+str(metadata["mixed_engine_pins"])+"**.", ""]
    for manifest in metadata["manifests"]:
        out += ["- "+link(manifest["manifest"],manifest["manifest"])+": "+("available" if manifest["available"] else "pending/unreadable")+
            "; SHA-256 `"+manifest["sha256"]+"`; engine `"+manifest["engine_id"]+"`; current source matches pin: **"+str(manifest["current_source_matches_pin"])+"**."]
        if manifest.get("read_warning"):
            out += ["  "+manifest["read_warning"]]
    out += [""]
    for utility in dict.fromkeys(r["utility_id"] for r in rows):
        group = [r for r in rows if r["utility_id"] == utility]
        first = group[0]
        out += ["## "+first["utility"]+" · "+first["jurisdiction"], "",
            "Eligibility, dated components and assumptions: "+link("utility document", first["utility_document"])+"; "+"; ".join(link("retained source manifest",p) for p in dict.fromkeys(r["source_manifest"] for r in group))+". Unit fixtures: "+link(first["unit_test_path"], first["unit_test_path"])+".", "",
            "| Plan / customer / supply | Eligibility and verified coverage | Bill / dispatch / main browser | Representative electrical replay | Unit structure evidence | Monthly / annual studies |",
            "|---|---|---|---|---|---|"]
        for r in group:
            out.append("| "+" | ".join(map(cell, [
                r["tariff"]+" · "+r["customer_class"]+" · "+r["supply"],
                r["eligibility"]+" Coverage ("+r["coverage_basis"]+"): "+r["coverage"]+". Scope: "+r["coverage_scope"],
                r["billing"]+" / "+r["dispatch"]+" / schema 11" if r["status"] == "supported" else "disabled / disabled / identified only",
                r["electrical_replay"], r["unit_structure_evidence"],
                r["monthly_status"]+" / "+r["annual_status"]]))+" |")
        out += [""]
    out += ["## Recorded representative studies", "",
        "These are a snapshot of the private manifest at generation time. Missing later cases are not presumed complete; regenerate after the validation driver finishes. Each case retains its own source manifest; verified-charge subtotal audits are explicitly distinct from complete-bill audits.", "",
        "| Exact plan / supplier / period | Dates | Worker / audit / bill scope | Study and pinned engine | Local result and source manifest |",
        "|---|---|---|---|---|"]
    for case in evidence:
        out.append("| "+" | ".join(map(cell, [case["utility"]+" / "+(case["plan"] or "unresolved")+" / "+(case["supply"] or "unresolved")+" / "+case["period"],
            case["dates"], case["status"]+" / "+case["validation"]+" / "+case["evidence_status"]+" · "+case["objective_scope"]+("; excluded: "+", ".join(case["excluded_components"]) if case["excluded_components"] else "")+(" · "+case["reason"] if case["reason"] else ""),
            "`"+case["study_id"]+"` · `"+case["engine_id"]+"`", (link("result/request", case["artifact"]) if case["artifact"] else "pending")+"; "+link("manifest",case["manifest"])]))+" |")
    if not evidence:
        out += ["| No recorded cases | — | pending | — | — |"]
    out += ["", "## Shared implementation paths", "",
        "The main wizard uses [regional.js](../src/local_web/static/regional.js), [schema-11 study preparation](../src/local_web/regional_study.py) and the [isolated worker](../src/local_web/worker.py). [Regional billing](../src/billing/regional.py) dispatches to each utility's charge expressions; [regional optimization](../src/dispatch/regional.py) replays its schedule through the numeric bill. [Electrical replay](../src/local_web/electrical_replay.py) remains a separate post-optimization layer.", "",
        "Source URLs and filed PDF page references are retained in each CSV row and the utility manifests. Source windows describe verified model coverage, not when a utility or tariff existed. Ten-year historical targets and unverified components remain documented utility by utility.", ""]
    return "\n".join(out)


def generate(*, root=ROOT, evidence_path=None, evidence_paths=None, markdown_path=None, csv_path=None):
    root = Path(root)
    if evidence_path is not None and evidence_paths is not None:
        raise ValueError("Supply either one evidence_path or multiple evidence_paths.")
    paths=list(evidence_paths) if evidence_paths is not None else [evidence_path] if evidence_path is not None else [root/p for p in DEFAULT_EVIDENCE]
    evidence, metadata = evidence_snapshots(paths, root=root)
    rows = build_rows(evidence=evidence, root=root)
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    markdown_path = Path(markdown_path) if markdown_path else root/"docs/Regional_Utility_Coverage.md"
    csv_path = Path(csv_path) if csv_path else root/"docs/Regional_Utility_Coverage.csv"
    markdown_path.write_text(markdown(rows, evidence, metadata))
    csv_path.write_text(csv_buffer.getvalue())
    return rows, evidence, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, action="append", help="Repeat for distinct manifests; default is the final release and VA historical-subtotal manifests.")
    parser.add_argument("--markdown", type=Path, default=ROOT/"docs/Regional_Utility_Coverage.md")
    parser.add_argument("--csv", type=Path, default=ROOT/"docs/Regional_Utility_Coverage.csv")
    args = parser.parse_args()
    rows, evidence, _ = generate(evidence_paths=args.evidence, markdown_path=args.markdown, csv_path=args.csv)
    print(f"Generated {len(rows)} plan/supplier/coverage rows; {sum(c['evidence_status']=='audited_complete' for c in evidence)} audited complete-bill cases; {sum(c['evidence_status']=='audited_partial_bill' for c in evidence)} audited subtotal cases. No tests or studies were executed.")


if __name__ == "__main__":
    main()
