"""Reproducible local Dominion reference case; no tariff extrapolation.

Use --fetch-weather once, then reuse the saved request and raw weather bytes.
--year only reports coverage preflight until a complete tariff year is verified.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.local_web.pjm_study import defaults, validate
from src.billing.dominion import PLAN
from src.local_web.runtime import Application, JobRunner


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--request',type=Path)
    parser.add_argument('--data-dir',type=Path,default=Path('.cache/pjm_candidate'))
    parser.add_argument('--fetch-weather',action='store_true')
    parser.add_argument('--year',type=int)
    args=parser.parse_args()
    if args.year:
        try:PLAN.require_coverage(date(args.year,1,1),date(args.year,12,31))
        except ValueError as error:
            print(json.dumps({'year':args.year,'status':'unsupported','reason':str(error),'tariff_extrapolated':False},indent=2))
            return 2
        raise ValueError('Full-year linked-cycle orchestration requires its own validated release.')
    r=json.loads(args.request.read_text()) if args.request else defaults()
    if args.fetch_weather:
        from src.profiles.era5 import fetch_era5
        r['weather']=fetch_era5(r['start_date'],r['end_date'],r['site']['latitude'],r['site']['longitude'])
    validate(r)
    app=Application(args.data_dir,embedded_worker=False)
    try:
        job=app.store.submit(r,app.engine,temporary=True)
        runner=JobRunner(app.store)
        try:
            deadline=time.monotonic()+600
            out=app.store.get(job['id'])
            while out['status'] not in ('completed','failed','cancelled'):
                if time.monotonic()>deadline:raise TimeoutError('Candidate exceeded ten minutes.')
                time.sleep(.2)
                out=app.store.get(job['id'])
        finally:runner.close()
        print(json.dumps({'id':out['id'],'status':out['status'],'engine_id':out['engine_id'],'directory':str((args.data_dir/'runs'/out['id']).resolve()),'error':out.get('error')},indent=2))
        return 0 if out['status']=='completed' else 1
    finally:
        app.close()


if __name__=='__main__':raise SystemExit(main())
