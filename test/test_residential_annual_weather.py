"""Offline annual weather invariants: leap year, DST, gaps, and quality flags."""
import numpy as np
import pandas as pd
import pytest
from src.profiles.residential import annual_noaa_weather, ResidentialError


@pytest.fixture
def observations(tmp_path):
    index=pd.date_range('2024-01-01','2025-01-02',freq='h',inclusive='left',tz='UTC')
    frame=pd.DataFrame({'STATION':'001','DATE':index.strftime('%Y-%m-%dT%H:%M:%S'),'TMP':'+0200,1'})
    path=tmp_path/'noaa.csv'
    frame.to_csv(path,index=False)
    return path,frame


def read(path,**kwargs):
    return annual_noaa_weather([path],station='001',region='fixture',year=2024,**kwargs)


def test_local_leap_year_boundaries_and_dst(observations):
    path,_=observations
    weather,audit=read(path)
    assert len(weather.frame)==8784
    assert weather.frame.index[0]==pd.Timestamp('2024-01-01T08:00Z')
    assert weather.frame.index[-1]==pd.Timestamp('2025-01-01T07:00Z')
    assert weather.frame.index.is_unique
    local=weather.frame.tz_convert('America/Los_Angeles')
    assert len(local.loc['2024-03-10'])==23
    assert len(local.loc['2024-11-03'])==25
    assert audit.weather_quality.eq('observed').all()


def test_one_bad_quality_hour_is_interpolated_and_flagged(observations):
    path,frame=observations
    frame.loc[99,'TMP']='+0100,1';frame.loc[100,'TMP']='+0600,9';frame.loc[101,'TMP']='+0300,5'
    frame.to_csv(path,index=False)
    weather,audit=read(path)
    stamp=pd.Timestamp(frame.loc[100,'DATE'],tz='UTC')
    assert weather.frame.loc[stamp,'temperature_c']==20
    assert np.isnan(audit.loc[stamp,'temperature_observed_c'])
    assert audit.loc[stamp,'weather_quality']=='interpolated'
    assert weather.diagnostics['interpolated_hours']==1
    with pytest.raises(ResidentialError,match='gap exceeds'):
        read(path,max_gap_hours=0)


def test_long_gap_is_not_partially_filled(observations):
    path,frame=observations
    frame=frame.drop([100,101]);frame.to_csv(path,index=False)
    with pytest.raises(ResidentialError,match='gap exceeds'):
        read(path)


def test_missing_adjoining_year_is_rejected(observations):
    path,frame=observations
    frame=frame[frame.DATE<'2025'];frame.to_csv(path,index=False)
    with pytest.raises(ResidentialError,match='year-boundary'):
        read(path)


def test_missing_station_is_rejected(observations):
    path,_=observations
    with pytest.raises(ResidentialError,match='No accepted'):
        annual_noaa_weather([path],station='other',region='fixture',year=2024)


@pytest.mark.parametrize('limit',[-1,4,1.5,True])
def test_gap_limit_requires_small_integer(observations,limit):
    with pytest.raises(ResidentialError,match='integer'):
        read(observations[0],max_gap_hours=limit)


def test_county_selection_excludes_vacant_and_other_regions():
    from tools.build_county_residential_year import occupied_county
    frame=pd.DataFrame({'in.county':['G0600010','G0600010','G0600190'],
        'completed_status':['Success']*3,'in.vacancy_status':['Occupied','Vacant','Occupied']})
    assert occupied_county(frame,'G0600010').index.tolist()==[0]
