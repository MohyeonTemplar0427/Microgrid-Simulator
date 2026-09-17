from copy import deepcopy
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from src.local_web.contract import DEFAULT_SITE_REQUEST
from src.local_web.site_inputs import build_site_inputs
from src.local_web.solar_orientation import energies, optimize
from src.profiles import WeatherDerivedPVConfiguration, WeatherDerivedPV
from src.timeseries import build_interval_index


def test_batched_energy_matches_existing_model_with_clipping(tmp_path):
    request=deepcopy(DEFAULT_SITE_REQUEST)
    request['pv_capacity_kw']=10
    _,_,tables,_=build_site_inputs(request,tmp_path)
    grid=build_interval_index(request['start_date'],request['end_date'],request['timezone'],15)
    angles=[(0,0),(23,175),(60,90),(90,270)]
    config=WeatherDerivedPVConfiguration(latitude=37.7749,longitude=-122.4194,rated_pv_capacity_kw=60,inverter_ac_capacity_kw=10)
    actual=energies(tables['weather'],grid,config,angles)
    from dataclasses import replace
    expected=[WeatherDerivedPV(replace(config,tilt_degrees=t,azimuth_degrees=a),weather_data=tables['weather']).build_detailed(grid).pv_available_kw.sum()*.25 for t,a in angles]
    np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-9)


def annual_fixture(tmp_path):
    from src.profiles.nsrdb import save_weather_csv
    request=deepcopy(DEFAULT_SITE_REQUEST)
    request.update(start_date='2025-01-01',end_date='2025-12-31',timestep_minutes=60)
    _,_,tables,_=build_site_inputs(request,tmp_path)
    save_weather_csv(tables['weather'],tmp_path/'weather.csv')
    metadata=dict(request=dict(latitude=37.7749,longitude=-122.4194,year=2025,timezone=request['timezone'],timestep_minutes=60),sha256=hashlib.sha256((tmp_path/'weather.csv').read_bytes()).hexdigest(),provenance={'source':'nsrdb_psm4','test_fixture':'synthetic clear sky; no live service'})
    (tmp_path/'weather.json').write_text(json.dumps(metadata))
    return request


def test_full_year_integer_search_and_tie_order(tmp_path,monkeypatch):
    import src.local_web.solar_orientation as module
    request=annual_fixture(tmp_path)
    observed=[]
    def scores(weather,grid,config,angles):
        observed.append((len(weather),len(grid.index),len(angles)))
        return [100 if (t,a) in ((25,175),(26,175)) else 10 for t,a in angles]
    monkeypatch.setattr(module,'energies',scores)
    result=optimize(tmp_path,request)
    assert observed==[(8760,8760,32761)]
    assert (result['tilt_degrees'],result['azimuth_degrees'])==(25,175)
    assert result['scope']=='full_historical_calendar_year'
    assert result['energy_kwh']>=result['original_energy_kwh']
    request['site']['latitude']=40
    with pytest.raises(ValueError,match='location'): optimize(tmp_path,request)


def test_reject_partial_year_and_wrong_provenance(tmp_path):
    request=annual_fixture(tmp_path)
    path=tmp_path/'weather.csv'
    frame=pd.read_csv(path);frame.iloc[:-1].to_csv(path,index=False)
    metadata=json.loads((tmp_path/'weather.json').read_text());metadata['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    (tmp_path/'weather.json').write_text(json.dumps(metadata))
    with pytest.raises(ValueError): optimize(tmp_path,request)
    metadata['provenance']['source']='clear_sky'
    (tmp_path/'weather.json').write_text(json.dumps(metadata))
    with pytest.raises(ValueError,match='historical'): optimize(tmp_path,request)
