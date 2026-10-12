"""Production form builder -> private queue -> pinned worker -> OpenDSS."""
import json
import subprocess
from copy import deepcopy
from urllib.error import HTTPError
import numpy as np
import pandas as pd
import pytest
from src.local_web.pjm_study import defaults, validate
from src.local_web.runtime import JobRunner
from src.profiles.era5 import parse_era5, VARIABLES
from src.timeseries.interval_table import build_interval_index
from test_local_web_pipeline import api_service, until
from test_local_web_hosting import hosted, signin


def weather_fixture():
    index=pd.date_range("2026-09-01", "2026-10-02", freq="h",inclusive="left",tz="UTC")
    h=index.hour
    raw={"latitude":37.5,"longitude":-77.5,"utc_offset_seconds":0,"timezone":"GMT",
         "hourly_units":{"time":"iso8601",**{k:v[1] for k,v in VARIABLES.items()}},
         "hourly":{"time":index.strftime("%Y-%m-%dT%H:%M").tolist(),
                   "temperature_2m":[20.]*len(index),"wind_speed_10m":[1.]*len(index),
                   "shortwave_radiation":np.where((h>=12)&(h<22),500.,0.).tolist(),
                   "direct_normal_irradiance":np.where((h>=12)&(h<22),600.,0.).tolist(),
                   "diffuse_radiation":np.where((h>=12)&(h<22),100.,0.).tolist()}}
    return {"provider":"open_meteo_era5","raw_json":json.dumps(raw),
            "request":{"latitude":37.6,"longitude":-77.5,"models":"era5","timezone":"UTC","wind_speed_unit":"ms"},
            "retrieved_at":"2026-10-11T12:00:00Z"}


def request_fixture():
    r=defaults();r["weather"]=weather_fixture();return r


def test_weather_interval_ending_conversion_and_missing_rejection():
    r=request_fixture();grid=build_interval_index(r["start_date"],r["end_date"],r["timezone"],30)
    frame,meta=parse_era5(r["weather"]["raw_json"],grid,37.6,-77.5)
    # Source noon UTC ends the 11:00 hour; local 07:00 starts it.
    assert frame.loc[frame.timestamp==pd.Timestamp("2026-09-01 07:00",tz="America/New_York"),"ghi_w_per_m2"].iloc[0]==500
    assert len(frame)==1440 and meta["native_interval_minutes"]==60
    raw=json.loads(r["weather"]["raw_json"]);raw["hourly"]["shortwave_radiation"][10]=None
    with pytest.raises(ValueError,match="Missing"):parse_era5(json.dumps(raw),grid,37.6,-77.5)


@pytest.mark.parametrize("bad",["location","timezone","weather_site","extra","dates","export","wear"])
def test_schema_rejects_unsupported_or_stale_settings(bad):
    r=request_fixture()
    if bad=="location":r["regional_account"]["utility_verification"]={}
    if bad=="timezone":r["timezone"]="America/Los_Angeles"
    if bad=="weather_site":r["weather"]["request"]["latitude"]=38
    if bad=="extra":r["unknown"]=True
    if bad=="dates":r["start_date"]="2025-09-01"
    if bad=="export":r["export_mode"]="net_metering"
    if bad=="wear":r["include_degradation_in_optimization"]="false"
    with pytest.raises(ValueError):validate(r)


def browser_request(r):
    a=r["account"];v={**r["site"],**r["solar"],**r["battery"],**r["regional_account"],
                       "start_date":r["start_date"],"end_date":r["end_date"],"load_scale":r["load"]["scale"],
                       "history_peaks":", ".join(map(str,a["history_peaks_kw"])),
                       "contract_demand_kw":a["contract_demand_kw"],"power_factor":a["power_factor"],"billing_month":a["billing_month"],
                       "account_confirmed":True,"include_wear":False,"degradation_cost_per_kWh":.03,
                       "verification_kind":"hypothetical_case","verification_reference":"Synthetic form test"}
    script="const {buildPjmRequest}=require('./src/local_web/static/pjm.js'); const fs=require('fs'); const x=JSON.parse(fs.readFileSync(0,'utf8')); process.stdout.write(JSON.stringify(buildPjmRequest(x.defaults,x.values,x.weather,null)));"
    result=subprocess.run(["node","-e",script],input=json.dumps({"defaults":defaults(),"values":v,"weather":r["weather"]}),text=True,capture_output=True,check=True)
    return json.loads(result.stdout)


def test_form_to_worker_and_old_engine_pin_remains_unchanged(tmp_path):
    with api_service(tmp_path) as (app,call):
        caps=call('/api/capabilities')[1];engine=caps['engine']['id']
        assert caps['pjm_candidate']['full_historical_year_supported'] is False
        payload=browser_request(request_fixture());assert payload['regional_account']['wholesale_pricing_location'] is None
        assert payload['battery']['max_discharge_kw']==20
        _,job=call('/api/v1/pjm/studies',payload,caps['token'])
        assert job['saved']==0
        runner=JobRunner(app.store)
        try:
            out=until(lambda:call('/api/studies/'+job['id'])[1],lambda x:x['status'] in ('completed','failed'))
        finally:runner.close()
        assert out['status']=='completed',out.get('error')
        assert out['result']['ac_validation']['all_intervals_feasible']
        _,table=call('/api/studies/'+job['id']+'/tables/comparison')
        assert len(table['data'])==3
        assert all(row[table['columns'].index('all_intervals_feasible')] is True for row in table['data'])
        assert out['result']['tables'][0]['id']=='comparison'
        _,inputs=call('/api/studies/'+job['id']+'/tables/inputs')
        assert inputs['data'][0][inputs['columns'].index('timestamp')]=='2026-09-01 04:00:00+00:00'
        assert 'private-pjm-market' not in {t['id'] for t in out['result']['tables']}
        _,ac=call('/api/studies/'+job['id']+'/tables/ac-summary')
        assert 'feeder_loss_kWh' in ac['columns'] and len(ac['data'])==3
        assert all(row[ac['columns'].index('feasible_intervals')]==1440 for row in ac['data'])
        assert app.engine['id']==engine
        assert out['result']['market_data']['used_for_retail_billing'] is False
        call('/api/studies/'+job['id']+'/save',{'name':'PJM integration fixture'},caps['token'])
        assert call('/api/studies/'+job['id'])[1]['name']=='PJM integration fixture'
        del app.capabilities['pjm_candidate']
        with pytest.raises(HTTPError) as exc:call('/api/v1/pjm/studies',payload,caps['token'])
        assert exc.value.code==400


def test_hosted_candidate_submission_and_private_inputs_are_blocked(hosted):
    app, auth, call, _ = hosted
    headers, caps = signin(call, 'pjm-reviewer')
    request = request_fixture()
    status, response, _ = call('/api/v1/pjm/studies', request, headers)
    assert status == 400 and 'local-only' in response['error']
    assert call('/api/v1/pjm/weather', {}, headers)[0] == 400
    # Even an existing privately imported candidate cannot become downloadable
    # when this storage directory is subsequently used by a hosted service.
    from src.local_web.auth import digest
    study = app.store.submit(request, app.engine, digest('pjm-reviewer'))
    for suffix in ('', '/request.json', '/result.json', '/tables/comparison.csv', '/tables.zip'):
        status, response, _ = call('/api/studies/' + study['id'] + suffix, headers=headers)
        assert status == 403 and 'local-only' in response['error']
