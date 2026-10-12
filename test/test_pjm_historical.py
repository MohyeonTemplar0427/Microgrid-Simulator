"""Historical files, native interval resolution, revisions and Eastern DST."""
import pandas as pd
import pytest
from src.signal_pipeline.providers.pjm import PJMProvider
from src.timeseries.interval_table import build_interval_index
from src.regional.account import RegionalAccount
from src.local_web.pjm_study import defaults

LOCATION={"pnode_id":"999001","pnode_name":"TEST DOM NODE","zone":"DOM","source":"Synthetic fixture; not a real PJM node"}
METADATA={"market":"REAL_TIME_HOURLY","source_url":"https://dataminer2.pjm.com/feed/rt_hrl_lmps",
          "retrieved_at":"2026-10-11T12:00:00Z","unit":"$/MWh","usage_permission":"internal_use_only"}


def raw(index):
    return pd.DataFrame({"datetime_beginning_utc":index.tz_convert("UTC"),"pnode_id":"999001", "pnode_name":"TEST DOM NODE",
                         "zone":"DOM","total_lmp_rt":50.,"version_nbr":1,"row_is_current":True})


def test_full_2025_year_import_bypasses_186_day_limit_without_filling():
    grid=build_interval_index("2025-01-01","2025-12-31","America/New_York",60)
    frame,meta=PJMProvider.import_historical_file(raw(grid.index).to_csv(index=False),METADATA,grid.start,grid.end,LOCATION)
    assert len(frame)==8760
    assert (frame.price_per_kWh==.05).all()
    local=pd.DatetimeIndex(frame.timestamp).tz_convert("America/New_York")
    assert sum(local.date==pd.Timestamp("2025-03-09").date())==23
    assert sum(local.date==pd.Timestamp("2025-11-02").date())==25
    assert meta["revision_numbers"]==[1]
    assert meta["public_download_allowed"] is False and len(meta["raw_sha256"])==64


def test_latest_revision_is_preserved():
    idx=pd.date_range("2025-11-02",periods=25,freq="h",tz="America/New_York")
    frame=raw(idx);old=frame.iloc[[0]].copy();old.row_is_current=False;new=frame.iloc[[0]].copy();new.version_nbr=2;new.total_lmp_rt=-5
    frame=pd.concat([old,new,frame.iloc[1:]])
    result,meta=PJMProvider.import_historical_file(frame.to_csv(index=False),METADATA,idx[0],idx[-1]+pd.Timedelta(hours=1),LOCATION)
    assert result.iloc[0].price_per_kWh==-.005
    assert meta["revision_numbers"]==[1,2]


@pytest.mark.parametrize("error",["missing","wrong_node","wrong_zone","duplicate","nonfinite","stale","missing_revision"])
def test_invalid_historical_data_reject(error):
    idx=pd.date_range("2025-11-02",periods=25,freq="h",tz="America/New_York");frame=raw(idx)
    if error=="missing":frame=frame.drop(1)
    if error=="wrong_node":frame.loc[0,"pnode_id"]="51288"
    if error=="wrong_zone":frame.loc[0,"zone"]="WESTERN HUB"
    if error=="duplicate":frame=pd.concat([frame,frame.iloc[[0]]])
    if error=="nonfinite":frame.loc[0,"total_lmp_rt"]=float("inf")
    if error=="stale":frame.loc[0,"row_is_current"]=False
    if error=="missing_revision":frame=frame.drop(columns="version_nbr")
    with pytest.raises(ValueError):PJMProvider.import_historical_file(frame.to_csv(index=False),METADATA,idx[0],idx[-1]+pd.Timedelta(hours=1),LOCATION)


def test_five_minute_native_intervals_preserved():
    idx=pd.date_range("2025-01-01",periods=12,freq="5min",tz="America/New_York")
    frame,_=PJMProvider.import_historical_file(raw(idx).to_csv(index=False),{**METADATA,"market":"REAL_TIME_5_MIN"},idx[0],idx[-1]+pd.Timedelta(minutes=5),LOCATION)
    assert len(frame)==12


def test_official_display_headers_are_supported_without_guessing():
    idx=pd.date_range("2025-01-01",periods=24,freq="h",tz="America/New_York")
    frame=raw(idx).rename(columns={"datetime_beginning_utc":"Datetime Beginning UTC","pnode_id":"Pricing Node ID",
        "pnode_name":"Pricing Node Name","zone":"Transmission Zone","total_lmp_rt":"Total LMP Real Time",
        "version_nbr":"Version Number","row_is_current":"Latest Version"})
    imported,_=PJMProvider.import_historical_file(frame.to_csv(index=False),METADATA,idx[0],idx[-1]+pd.Timedelta(hours=1),LOCATION)
    assert len(imported)==24


@pytest.mark.parametrize("patch",[{"state_jurisdiction":"NC"},{"retail_supplier":"third_party"},{"utility_verification":{}},{"wholesale_pricing_location":{**LOCATION,"zone":"WESTERN HUB"}}])
def test_geography_and_node_do_not_imply_service(patch):
    with pytest.raises(ValueError):RegionalAccount(**{**defaults()["regional_account"],**patch}).validate_dominion()
