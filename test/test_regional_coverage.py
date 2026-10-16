"""Coverage reports must not upgrade partial/mismatched runs to acceptance."""
import hashlib
import json

import pytest

from tools.build_regional_coverage import build_rows, evidence_snapshot, evidence_snapshots, generate


STUDY = "a"*32
ENGINE = "b"*64


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source(tmp_path, *, status="completed", validation="passed", year=True):
    folder = tmp_path/"private"
    run = folder/"runs"/STUDY
    run.mkdir(parents=True)
    request = {"account": {"tariff": "1T", "supplier": "bundled"},
        "site": {"utility": "dominion_energy_north_carolina"},
        "start_date": "2025-01-01", "end_date": "2025-12-31" if year else "2025-11-30"}
    (run/"request.json").write_text(json.dumps(request))
    (run/"result.json").write_text(json.dumps({"engine_id": ENGINE, "is_complete_bill": True}))
    manifest = {"engine_id": ENGINE, "cases": [{"case": "exact-case", "utility": "dominion_energy_north_carolina",
        "period": "annual", "study_id": STUDY, "status": status, "validation": validation,
        "physics": [{"scenario": x} for x in ("grid_only", "pv_only", "pv_battery")],
        "source_artifacts": {x: digest(run/x) for x in ("request.json", "result.json")}}]}
    path = folder/"validation.json"
    path.write_text(json.dumps(manifest))
    return path, run, manifest


def test_only_exact_plan_supplier_period_get_completed_representative_evidence(tmp_path):
    path, _, _ = source(tmp_path)
    evidence, metadata = evidence_snapshot(path, root=tmp_path)
    assert evidence[0]["evidence_status"] == "audited_complete"
    rows = build_rows(evidence=evidence, root=tmp_path)
    assert metadata["engine_id"] == ENGINE
    for row in rows:
        if row["utility_id"] == "dominion_energy_north_carolina" and row["tariff"] == "1T" and row["coverage"].startswith("2025-01-01"):
            assert row["annual_status"] == "audited complete-bill representative case"
            assert row["annual_studies"] == STUDY
            assert row["annual_engines"] == ENGINE
            assert row["monthly_status"] == "not evidenced"
        else:
            assert row["annual_status"] != "audited complete-bill representative case"


@pytest.mark.parametrize("status,validation,expected", [
    ("queued", "pending", "pending"), ("running", "pending", "pending"),
    ("completed", "pending", "pending"), ("completed", "failed", "failed"),
    ("failed", "failed", "failed"),
])
def test_worker_completion_and_artifacts_alone_never_imply_passed_audit(tmp_path, status, validation, expected):
    path, _, _ = source(tmp_path, status=status, validation=validation)
    evidence, _ = evidence_snapshot(path, root=tmp_path)
    assert evidence[0]["evidence_status"] == expected
    target = next(r for r in build_rows(evidence=evidence, root=tmp_path)
                  if r["utility_id"] == "dominion_energy_north_carolina" and r["tariff"] == "1T")
    assert target["annual_status"] != "audited complete-bill representative case"


@pytest.mark.parametrize("fault", ["request_hash", "result_hash", "engine", "scenario", "year"])
def test_changed_or_incomplete_evidence_is_not_labeled_accepted(tmp_path, fault):
    path, run, manifest = source(tmp_path, year=fault != "year")
    if fault == "request_hash":
        r = json.loads((run/"request.json").read_text()); r["extra"] = "changed"
        (run/"request.json").write_text(json.dumps(r))
    if fault == "result_hash":
        (run/"result.json").write_text("{}")
    if fault == "engine":
        (run/"result.json").write_text(json.dumps({"engine_id": "wrong"}))
        manifest["cases"][0]["source_artifacts"]["result.json"] = digest(run/"result.json")
    if fault == "scenario":
        manifest["cases"][0]["physics"].pop()
    path.write_text(json.dumps(manifest))
    evidence, _ = evidence_snapshot(path, root=tmp_path)
    assert evidence[0]["evidence_status"] == "evidence_incomplete"
    assert evidence[0]["reason"]


def test_missing_or_in_progress_manifest_stays_unrecorded(tmp_path):
    path = tmp_path/"validation.json"
    assert evidence_snapshot(path, root=tmp_path)[0] == []
    path.write_text('{"cases": [')
    cases, meta = evidence_snapshot(path, root=tmp_path)
    assert cases == [] and meta["available"] is False
    assert "being written" in meta["read_warning"]


def test_primary_and_high_voltage_billing_are_separate_from_replay_coverage():
    rows = build_rows()
    for row in rows:
        if row["tariff"] in {"VA-GS4-primary", "VA-GS4-transmission", "VA-10-primary", "VA-10-transmission", "LPL_P", "HTS_SUB", "HTS_HV"}:
            assert row["billing"].startswith("implemented")
            assert row["electrical_replay"].startswith("Unavailable")
    assert any("combined CIEP NIGHT not separately parameterized" in r["unit_structure_evidence"] for r in rows)


def test_regeneration_is_deterministic_and_preserves_input_artifacts(tmp_path):
    path, run, _ = source(tmp_path)
    before = {p.name: p.read_bytes() for p in run.iterdir()}
    md, csv = tmp_path/"coverage.md", tmp_path/"coverage.csv"
    kwargs = dict(evidence_path=path, markdown_path=md, csv_path=csv)
    generate(**kwargs)
    first = md.read_bytes(), csv.read_bytes()
    generate(**kwargs)
    assert (md.read_bytes(), csv.read_bytes()) == first
    assert {p.name: p.read_bytes() for p in run.iterdir()} == before
    assert "Defined fixtures" in md.read_text()


def revise_source(path, run, manifest, *, utility, plan, start, end, complete, period):
    request=json.loads((run/"request.json").read_text())
    request.update(site={"utility":utility},account={"tariff":plan,"supply_arrangement":"bundled"},start_date=start,end_date=end)
    (run/"request.json").write_text(json.dumps(request))
    result={"engine_id":manifest["engine_id"],"is_complete_bill":complete,
        "billing":{"grid_only":[{"is_complete_bill":complete,"excluded_components":[] if complete else ["sales_use_tax_surcharge","local_utility_consumer_tax"]}]}}
    (run/"result.json").write_text(json.dumps(result))
    entry=manifest["cases"][0]
    entry.update(utility=utility,period=period,is_complete_bill=complete,
        source_artifacts={name:digest(run/name) for name in ("request.json","result.json")})
    path.write_text(json.dumps(manifest))


def test_merge_keeps_historical_subtotal_and_current_complete_bill_distinct(tmp_path):
    h,hr,hm=source(tmp_path/"history")
    c,cr,cm=source(tmp_path/"current")
    revise_source(h,hr,hm,utility="dominion_energy_virginia",plan="VA-1",start="2025-01-01",end="2025-12-31",complete=False,period="annual")
    revise_source(c,cr,cm,utility="dominion_energy_virginia",plan="VA-1",start="2026-09-01",end="2026-09-30",complete=True,period="monthly")
    cases,metadata=evidence_snapshots([h,c,h])
    assert len(cases)==2 and len(metadata["manifests"])==2
    assert metadata["engine_ids"]==[ENGINE] and metadata["mixed_engine_pins"] is False
    assert cases[0]["evidence_status"]=="audited_partial_bill"
    assert cases[0]["objective_scope"]=="verified_charges_subtotal"
    assert cases[0]["excluded_components"]==["local_utility_consumer_tax","sales_use_tax_surcharge"]
    assert cases[0]["manifest"]!=cases[1]["manifest"]
    assert cases[0]["manifest_sha256"]==digest(h) and cases[1]["manifest_sha256"]==digest(c)
    rows=[r for r in build_rows(evidence=cases) if r["utility_id"]=="dominion_energy_virginia" and r["tariff"]=="VA-1"]
    historical=next(r for r in rows if r["coverage"].startswith("2025"))
    current=next(r for r in rows if r["coverage"].startswith("2026"))
    assert historical["coverage_is_complete_bill"] is False
    assert "subtotal only" in historical["annual_status"]
    assert "complete-bill representative" not in historical["annual_status"]
    assert historical["monthly_status"]=="not evidenced"
    assert "subtotal optimum only" in historical["dispatch"]
    assert "historical.py" in historical["billing_path"]
    assert current["coverage_is_complete_bill"] is True
    assert current["monthly_status"]=="audited complete-bill representative case"
    assert current["annual_status"]=="not evidenced"
    assert "history" in historical["annual_manifests"] and "current" in current["monthly_manifests"]


def test_distinct_engine_provenance_is_not_upgraded_to_same_engine_validation(tmp_path):
    a,_,_=source(tmp_path/"one")
    b,br,bm=source(tmp_path/"two")
    other="c"*64
    bm["engine_id"]=other
    (br/"result.json").write_text(json.dumps({"engine_id":other,"is_complete_bill":True}))
    bm["cases"][0]["source_artifacts"]["result.json"]=digest(br/"result.json")
    b.write_text(json.dumps(bm))
    cases,metadata=evidence_snapshots([a,b])
    assert metadata["mixed_engine_pins"] is True
    assert metadata["engine_ids"]==[ENGINE,other]
    assert [r["engine_id"] for r in cases]==[ENGINE,other]
    target=next(r for r in build_rows(evidence=cases) if r["utility_id"]=="dominion_energy_north_carolina" and r["tariff"]=="1T")
    assert target["annual_engines"]==ENGINE+"; "+other
    assert "one" in target["annual_manifests"] and "two" in target["annual_manifests"]


def test_audit_without_bill_completeness_never_implies_complete_bill(tmp_path):
    p,run,manifest=source(tmp_path)
    (run/"result.json").write_text(json.dumps({"engine_id":ENGINE}))
    manifest["cases"][0]["source_artifacts"]["result.json"]=digest(run/"result.json")
    p.write_text(json.dumps(manifest))
    cases,_=evidence_snapshot(p)
    assert cases[0]["evidence_status"]=="audited_scope_unknown"
    assert cases[0]["bill_is_complete"] is None
    target=next(r for r in build_rows(evidence=cases) if r["utility_id"]=="dominion_energy_north_carolina" and r["tariff"]=="1T")
    assert target["annual_status"]=="audited_scope_unknown"


def test_manifest_cannot_overrule_a_retained_incomplete_bill(tmp_path):
    p,run,manifest=source(tmp_path)
    (run/"result.json").write_text(json.dumps({"engine_id":ENGINE,"is_complete_bill":False}))
    manifest["cases"][0].update(is_complete_bill=True)
    manifest["cases"][0]["source_artifacts"]["result.json"]=digest(run/"result.json")
    p.write_text(json.dumps(manifest))
    cases,_=evidence_snapshot(p)
    assert cases[0]["evidence_status"]=="evidence_incomplete"
    assert "contradicts" in cases[0]["reason"]


def test_multiple_evidence_regeneration_records_both_paths_and_pending_manifest(tmp_path):
    first,_,_=source(tmp_path/"one")
    pending=tmp_path/"pending/validation.json"
    md,table=tmp_path/"matrix.md",tmp_path/"matrix.csv"
    _,cases,metadata=generate(evidence_paths=[first,pending],markdown_path=md,csv_path=table)
    text=md.read_text()
    assert text.count("--evidence ")==2
    assert str(first) in text and str(pending) in text
    assert "pending/unreadable" in text
    assert len(cases)==1 and len(metadata["manifests"])==2


def test_incomplete_estimate_without_explicit_omissions_is_not_verified_subtotal(tmp_path):
    p,run,manifest=source(tmp_path)
    (run/"result.json").write_text(json.dumps({"engine_id":ENGINE,"is_complete_bill":False}))
    manifest["cases"][0]["source_artifacts"]["result.json"]=digest(run/"result.json")
    p.write_text(json.dumps(manifest))
    cases,_=evidence_snapshot(p)
    assert cases[0]["evidence_status"]=="audited_partial_bill"
    assert cases[0]["objective_scope"]=="incomplete_bill_estimate"
    target=next(r for r in build_rows(evidence=cases) if r["utility_id"]=="dominion_energy_north_carolina" and r["tariff"]=="1T")
    assert "incomplete-bill estimate" in target["annual_status"]


def test_current_subtotal_capability_cannot_inherit_full_bill_claim(tmp_path):
    p,run,manifest=source(tmp_path)
    revise_source(p,run,manifest,utility="dominion_energy_virginia",plan="VA-1",start="2025-01-01",end="2025-12-31",complete=True,period="annual")
    cases,_=evidence_snapshot(p)
    target=next(r for r in build_rows(evidence=cases) if r["utility_id"]=="dominion_energy_virginia" and r["tariff"]=="VA-1" and r["coverage"].startswith("2025"))
    assert target["coverage_is_complete_bill"] is False
    assert target["annual_status"].startswith("scope conflict")
    assert "audited complete-bill representative case" not in target["annual_status"]
