"""Replay private cached 2025 ComEd studies under a fresh immutable engine.

No credential loading or provider calls. Preserve original studies and data
permissions. Reuse the independent annual tariff/physics audit.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from src.local_web.runtime import Application
from src.local_web.site_inputs import check_weather_matches
from src.local_web.worker import write_json
from tools.run_comed_year_validation import audit,digest,require


def cached_sources(source):
    found={}
    for directory in sorted((source/"runs").iterdir()):
        if not (directory/"result.json").is_file():continue
        request=json.loads((directory/"request.json").read_text())
        if request.get("schema_version")!=10 or request.get("start_date")!="2025-01-01" or request.get("end_date")!="2025-12-31":continue
        kind=request["site_profile"]["site_type"]
        found.setdefault(kind,directory)
    require(set(found)=={"residential","commercial"},"Source must contain completed residential and commercial 2025 studies")
    return found


def reuse_weather(app,source,request):
    """Register verified local bytes as an ownerless local-only cache resource."""
    require(request["weather_source"]=="nsrdb","Cached replay requires actual-year NSRDB inputs")
    metadata=json.loads((source/"weather.json").read_text())
    check_weather_matches(request,metadata)
    require(digest(source/"weather.csv")==metadata["sha256"],"Source weather checksum changed")
    identity=[app.engine["id"],"weather",metadata["request"],None]
    resource_id=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    directory=app.store.directory/"weather"/resource_id
    directory.mkdir(exist_ok=True)
    for name in ("weather.csv","weather.json"):
        shutil.copyfile(source/name,directory/name)
    write_json(directory/"resource.json",metadata)
    app.store.grant("weather",resource_id,None)
    return resource_id


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=ROOT/".cache/comed_actual_2025_equivalent")
    parser.add_argument("--output",type=Path,default=ROOT/".cache/comed_cycling_refinement_2025")
    args=parser.parse_args()
    sources=cached_sources(args.source.resolve())
    output=args.output.resolve()
    if output.exists() and any(output.iterdir()):parser.error("Choose a new empty private output directory")
    app=Application(output)
    report=dict(scope="Private cached 2025 BESH rerun; source weather, load and prices unchanged; no live API calls",
                engine_id=app.engine["id"],driver_sha256=digest(__file__),cases=[])
    (output/"validation-driver.py").write_bytes(Path(__file__).read_bytes())
    all_months=[];all_components=[];comparisons=[];failed=False
    try:
        for kind,source in sources.items():
            old=json.loads((source/"request.json").read_text())
            r=deepcopy(old)
            r.update(name="ComEd 2025 "+kind+" · cycling refinement",weather_id=reuse_weather(app,source,r))
            job=app.store.submit(r,app.engine)
            entry=dict(case=kind,study_id=job["id"],source_study=source.name,
                       source_request_sha256=digest(source/"request.json"))
            report["cases"].append(entry)
            last=None;started=time.monotonic()
            while True:
                state=app.store.get(job["id"])
                marker=(state["status"],state["progress"])
                if marker!=last:print(kind,*marker,flush=True);last=marker
                if state["status"] in ("completed","failed","cancelled"):break
                time.sleep(1)
            entry.update(status=state["status"],elapsed_seconds=time.monotonic()-started)
            require(state["status"]=="completed",str(state.get("error")))
            directory=output/"runs"/job["id"]
            rows,lines,physics=audit(directory,r,app.engine["id"])
            pd.testing.assert_frame_equal(pd.read_csv(directory/"inputs.csv"),pd.read_csv(source/"inputs.csv"),check_exact=True)
            new=json.loads((directory/"result.json").read_text())
            old_result=json.loads((source/"result.json").read_text())
            for key in ("native_csv_sha256","price_csv_sha256"):
                require(new["input_provenance"][key]==old_result["input_provenance"][key],"Imported data hash changed")
            table=pd.read_csv(directory/"comparison.csv").set_index("scenario")
            prior=pd.read_csv(source/"comparison.csv").set_index("scenario")
            refinement=new["optimization"]["pv_battery"]["throughput_refinement"]
            require(refinement["selected_throughput_kwh"]<=refinement["primary_throughput_kwh"]+1e-6,"Refinement increased throughput")
            lower=refinement.get("global_lower_bound_kwh")
            if lower is not None:
                selected=refinement["selected_throughput_kwh"]
                require(np.isfinite(lower) and lower<=selected+refinement["proof_tolerance_kwh"],"Invalid cycling lower bound")
                require(abs(refinement["optimality_gap_kwh"]-max(0.,selected-lower))<1e-6,"Cycling gap does not reconcile")
                if refinement["minimum_throughput_proven"]:
                    require(refinement["optimality_gap_kwh"]<=refinement["proof_tolerance_kwh"],"Minimum cycling claim exceeds numerical proof tolerance")
            dt=r["timestep_minutes"]/60
            for scenario in table.index:
                old_dispatch=pd.read_csv(source/("dispatch-"+scenario+".csv"))
                old_t=float(dt*(old_dispatch.battery_charge_kw+old_dispatch.battery_discharge_kw).sum())
                table.loc[scenario,"previous_throughput_kwh"]=old_t
                table.loc[scenario,"throughput_change_vs_previous_kwh"]=table.loc[scenario,"battery_throughput_kwh"]-old_t
                delta=float(table.loc[scenario,"subtotal_usd"]-prior.loc[scenario,"subtotal_usd"])
                table.loc[scenario,"subtotal_change_vs_previous_usd"]=delta
                require(abs(delta)<=float(table.loc[scenario,"rounding_bound_usd"])+float(prior.loc[scenario,"rounding_bound_usd"]),"Bill difference exceeds independent rounding bounds")
            table.insert(0,"case",kind)
            comparisons.append(table.reset_index());all_months.append(rows);all_components.append(lines)
            entry.update(validation="passed",physics=physics,throughput_refinement=refinement,
                         input_sha256=digest(directory/"inputs.csv"),weather_sha256=digest(directory/"weather.csv"))
            print(kind,"audited; minimum throughput proven:",refinement["minimum_throughput_proven"],flush=True)
    except BaseException:
        failed=True
        raise
    finally:
        app.close()
        report["validation"]="failed" if failed else "passed"
        write_json(output/"validation.json",report)
        if comparisons:pd.concat(comparisons,ignore_index=True).to_csv(output/"comparison-to-previous.csv",index=False)
        if all_months:pd.concat(all_months,ignore_index=True).to_csv(output/"monthly-comparison.csv",index=False)
        if all_components:pd.concat(all_components,ignore_index=True).to_csv(output/"monthly-components.csv",index=False)
    print("Private validation complete:",output,flush=True)


if __name__=="__main__":main()
