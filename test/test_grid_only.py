from copy import deepcopy
import json

import pandas as pd
import pytest
from src.local_web.contract import DEFAULT_SITE_REQUEST, validate_request
from src.local_web.grid_only import execute
from src.local_web.worker import write_json


def request():
    from src.local_web.grid_only import FIELDS
    base = {**deepcopy(DEFAULT_SITE_REQUEST), 'site_profile':{'site_type':'commercial','subtype':None}}
    base['site']['utility']='pge'
    return {k:5 if k=='schema_version' else base[k] for k in FIELDS}


@pytest.mark.parametrize('extra', ['battery','solar','weather_id','ess','strategies'])
def test_grid_only_rejects_hidden_equipment(extra):
    data=request();data[extra]=None
    with pytest.raises(ValueError,match='schema 5'):
        validate_request(data)


@pytest.mark.parametrize('day,count', [('2026-03-08',92),('2026-11-01',100)])
def test_grid_only_dst_and_flat_bill(tmp_path,monkeypatch,day,count):
    import pvlib.location
    def no_weather(*args,**kwargs): raise AssertionError('No PV means no weather call')
    monkeypatch.setattr(pvlib.location.Location,'get_clearsky',no_weather)
    data=request();data.update(start_date=day,end_date=day)
    validate_request(data)
    write_json(tmp_path/'engine.json',{})
    execute(tmp_path,data)
    frame=pd.read_csv(tmp_path/'inputs.csv');cost=pd.read_csv(tmp_path/'comparison.csv').iloc[0]
    assert len(frame)==count and frame.pv_available_kw.eq(0).all()
    assert frame.grid_import_kw.equals(frame.native_load_kw)
    assert cost.total_explicit_cost==pytest.approx(count*.25*60*.25)
    assert not (tmp_path/'weather.csv').exists()
    assert not (tmp_path/'dispatch-cost_optimal.csv').exists()


def test_grid_only_tariff_reconciles_and_refuses_outside_coverage(tmp_path):
    from src.billing import get_tariff
    from src.billing.charges import calculate_meter_billing
    data=request();data.update(tariff_id='hetch_hetchy_c1_standard_2026_07_01')
    # Use an identifier from the registered, verified service catalog.
    from src.local_web.worker import capabilities
    data['tariff_id']=next(t['id'] for t in capabilities()['tariffs'] if t['service']=='hetch_hetchy')
    data['site']['utility']='hetch_hetchy'
    write_json(tmp_path/'engine.json',{})
    execute(tmp_path,data)
    frame=pd.read_csv(tmp_path/'inputs.csv');frame.timestamp=pd.to_datetime(frame.timestamp,utc=True).dt.tz_convert(data['timezone'])
    bill=calculate_meter_billing(frame,get_tariff(data['tariff_id']),meter_id='site',timestep_hours=.25)
    assert pd.read_csv(tmp_path/'comparison.csv').iloc[0].total_utility_charge==pytest.approx(sum(p.total_utility_charge for p in bill))
    data.update(start_date='2028-08-01',end_date='2028-08-01')
    with pytest.raises(ValueError):execute(tmp_path,data)


def test_municipal_grid_only_never_optimizes(tmp_path,monkeypatch):
    from test_site_profile import municipal_request
    import src.local_web.municipal_study as municipal
    data=municipal_request();data.update(grid_only=True,battery=None,degradation_cost_per_kWh=0)
    def no_optimizer(*args,**kwargs):raise AssertionError('Grid-only must not optimize storage')
    monkeypatch.setattr(municipal,'optimize_storage',no_optimizer)
    validate_request(data);write_json(tmp_path/'engine.json',{})
    municipal.execute_study(tmp_path,data)
    result=json.loads((tmp_path/'result.json').read_text())
    assert set(result['bills'])=={'no_battery'}
    assert len(pd.read_csv(tmp_path/'comparison.csv'))==1
    assert not (tmp_path/'dispatch-cost_optimal.csv').exists()
    data['battery']={}
    with pytest.raises(ValueError,match='no battery'):validate_request(data)


@pytest.mark.parametrize('option', ['r','s'])
def test_grid_only_rejects_renewable_and_storage_rates(option):
    data=request();data['tariff_id']=f'pge_b19_secondary_option_{option}_bundled_2026_03_01'
    with pytest.raises(ValueError,match='incompatible'):
        validate_request(data)


def test_historical_billing_plan_preflight():
    data = request()
    data.update(start_date="2025-09-17", end_date="2025-10-17",
                tariff_id="pge_b6_secondary_polyphase_bundled_2026_03_01")
    with pytest.raises(ValueError, match="Billing Plan coverage"):
        validate_request(data)
    data["tariff_id"] = "pge_b6_secondary_polyphase_bundled_2025_09_01"
    validate_request(data)
    data["end_date"] = "2026-01-01"
    with pytest.raises(ValueError, match="Billing Plan coverage"):
        validate_request(data)
