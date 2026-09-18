import json

import numpy as np
import pandas as pd
import pytest

from src.local_web.carbon import values, validate


def spec(day='2026-08-01',minutes=15):
    return dict(site={'latitude':37.7749,'longitude':-122.4194},start_date=day,end_date=day,timezone='America/Los_Angeles',timestep_minutes=minutes,
                carbon={'source':'electricity_maps','region':'caiso_np15'})


def native(request):
    start=pd.Timestamp(request['start_date'],tz=request['timezone'])
    index=pd.date_range(start,start+pd.DateOffset(days=1),freq='15min',inclusive='left')
    return pd.DataFrame({'timestamp':index,'gCO2/kWh':np.arange(len(index),dtype=float)+100})


def mocked_provider(monkeypatch,frame):
    monkeypatch.setenv('ELECTRICITY_MAPS_API_KEY','test-only')
    import src.signal_pipeline.electricity_maps_data as provider
    monkeypatch.setattr(provider,'get_multi_day_carbon_data',lambda key,zone,*a,**k: frame.copy() if zone=='US-CAL-CISO' else pytest.fail(zone))
    return provider


@pytest.mark.parametrize('day,count',[('2026-03-08',92),('2026-11-01',100)])
@pytest.mark.parametrize('minutes',[15,30,60])
def test_carbon_dst_aggregation_and_durable_reuse(tmp_path,monkeypatch,day,count,minutes):
    request=spec(day,minutes);frame=native(request);provider=mocked_provider(monkeypatch,frame)
    index=frame.timestamp.iloc[::minutes//15]
    data,meta=values(request,tmp_path,index)
    assert len(data)==count//(minutes//15)
    assert data==pytest.approx(frame['gCO2/kWh'].to_numpy().reshape(-1,minutes//15).mean(axis=1))
    assert meta['request']['zone']=='US-CAL-CISO'
    assert 'not a site measurement' in meta['warning']
    monkeypatch.setattr(provider,'get_multi_day_carbon_data',lambda *a,**k:pytest.fail('Refetched saved data'))
    assert values(request,tmp_path,index)[0]==pytest.approx(data)
    (tmp_path/'carbon.csv').write_text('modified')
    with pytest.raises(ValueError,match='checksum'):values(request,tmp_path,index)


@pytest.mark.parametrize('bad',['gap','duplicate','nan','negative'])
def test_carbon_rejects_bad_native_coverage(tmp_path,monkeypatch,bad):
    request=spec();frame=native(request);index=frame.timestamp.copy()
    if bad=='gap':frame=frame.iloc[:-1]
    if bad=='duplicate':frame=pd.concat([frame,frame.iloc[-1:]])
    if bad=='nan':frame.loc[0,'gCO2/kWh']=np.nan
    if bad=='negative':frame.loc[0,'gCO2/kWh']=-1
    mocked_provider(monkeypatch,frame)
    with pytest.raises(ValueError,match='every native'):values(request,tmp_path,index)
    assert not (tmp_path/'carbon.json').exists()


def test_missing_credentials_no_implicit_fallback(tmp_path,monkeypatch):
    monkeypatch.delenv('ELECTRICITY_MAPS_API_KEY',raising=False)
    with pytest.raises(ValueError,match='credentials'):values(spec(),tmp_path,native(spec()).timestamp)
    assumed={**spec(), 'carbon':{'source':'assumed','value':200}}
    with pytest.raises(ValueError,match='constant assumptions'):
        values(assumed,tmp_path,native(spec()).timestamp)
    with pytest.raises(ValueError,match='5-minute'):validate(spec(minutes=5))


def test_grid_only_emissions_use_interval_carbon(tmp_path,monkeypatch):
    from test_grid_only import request
    from src.local_web.grid_only import execute
    from src.local_web.worker import write_json
    r={**request(),'carbon':spec()['carbon']};frame=native(r)
    mocked_provider(monkeypatch,frame);write_json(tmp_path/'engine.json',{})
    execute(tmp_path,r)
    result=pd.read_csv(tmp_path/'comparison.csv').iloc[0]
    assert result.emissions_kgCO2==pytest.approx(float(frame['gCO2/kWh'].sum()*60*.25/1000))
    assert result.total_explicit_cost==pytest.approx(60*24*.25)
    assert json.loads((tmp_path/'result.json').read_text())['input_provenance']['carbon']['request']['zone']=='US-CAL-CISO'


def test_location_mapping_rejects_unknown_and_mismatched_regions():
    from src.local_web.carbon import region_for_location
    for lat,lon in [(37.7749,-122.4194),(37.3541,-121.9552),(37.7652,-122.2416),(38.4404,-122.7141)]:
        assert region_for_location(lat,lon)['zone']=='US-CAL-CISO'
    with pytest.raises(ValueError,match='No supported'):
        region_for_location(40.7128,-74.006)
    request=spec();request['carbon']['region']='US-TEX-ERCO'
    with pytest.raises(ValueError,match='does not match'):validate(request)
    request['carbon']['region']='from_location'
    validate(request)
    request['site']={'latitude':40.7128,'longitude':-74.006}
    with pytest.raises(ValueError,match='No supported'):validate(request)
