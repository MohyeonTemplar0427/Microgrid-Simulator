"""Independent filed-rate bills, boundaries and optimizer reconciliation."""
import numpy as np
import pandas as pd
import pytest
from src.billing.socal import bill,eligibility,periods,holidays,ADJUSTMENTS
from src.dispatch.socal import optimize


def account(utility='ladwp',**kw):
 return dict(customer_class='residential',eligibility_confirmed=True,cycle_confirmed=True,
 ordinary_account_confirmed=True,reference='Synthetic account test',generation_provider=utility,
 solar_program='none',voltage='secondary',phase='single',local_tax_percent=0.,tax_confirmed=True,
 temperature_zone='1',region_confirmed=True,pac_tier=1,annual_average_kwh=500,
 baseline_region='6',baseline_type='basic',prime_qualification='battery',billing_month_factor=1,**kw)


def frame(start='2026-07-01',end='2026-07-31',kw=1.):
 idx=pd.date_range(pd.Timestamp(start,tz='America/Los_Angeles'),pd.Timestamp(end,tz='America/Los_Angeles')+pd.DateOffset(days=1),freq='15min',inclusive='left')
 return pd.DataFrame(dict(timestamp=idx,grid_import_kw=kw,native_load_kw=kw,pv_available_kw=0.))


def test_ladwp_r1a_independent_tiers_and_adjustments():
 r=bill('ladwp_r-1a',frame(),account(),'2026-07-01','2026-07-31')
 # 744 kWh, first 350 in tier 1, remainder tier 2; July official total rates.
 assert r['total']==pytest.approx(350*.26408+394*.32267+2.30+744*.0003)
 assert r['line_items']['IRCA']==pytest.approx(744*.06934)


def test_ladwp_zero_usage_minimum_separate_from_access():
 r=bill('ladwp_r-1a',frame(kw=0),account(),'2026-07-01','2026-07-31')
 assert r['total']==pytest.approx(12.30)


def test_sce_domestic_delivery_generation_and_frc_only_once():
 r=bill('sce_d',frame(),account('sce'),'2026-07-01','2026-07-31')
 baseline=31*11.4
 assert r['total']==pytest.approx(baseline*.18453+(744-baseline)*.28552+744*(.11761+.00619+.0003)+31*.794)
 assert 'MCAM' not in r['line_items']  # CCA-specific; not bundled.


def test_sce_small_commercial_hand_bill():
 a=account('sce');a.update(customer_class='commercial',non_cpp_confirmed=True)
 # July 4 is Saturday: Friday July 3 is NOT an observed tariff holiday.
 f=frame(kw=10);idx=pd.DatetimeIndex(f.timestamp)
 weekday=idx.dayofweek<5;peak=(idx.hour>=16)&(idx.hour<21)
 on=np.count_nonzero(weekday&peak)*2.5;mid=np.count_nonzero(~weekday&peak)*2.5;off=7440-on-mid
 r=bill('sce_tou-gs-1-e',f,a,'2026-07-01','2026-07-31')
 assert r['total']==pytest.approx(on*(.21937+.42432)+mid*(.21937+.11297)+off*(.16523+.08076)+7440*(.00457+.0003)+31*.468)


def test_sce_tou_boundaries_and_holiday_observance():
 idx=pd.DatetimeIndex(['2026-07-03 16:00','2026-07-04 16:00','2026-09-07 16:00','2026-09-08 15:45','2026-09-08 16:00','2026-09-08 21:00'],tz='America/Los_Angeles')
 assert list(periods(idx,'sce','TOU-D-4-9'))==['on','mid','mid','off','on','off']
 assert pd.Timestamp('2027-07-05').date() in holidays(2027)
 assert periods(idx,'ladwp','R-1B')[2]=='high'  # LADWP ordinance is weekday-based.


@pytest.mark.parametrize('changes',[{'generation_provider':'cca'},{'region_confirmed':False},{'pac_tier':None},{'annual_average_kwh':3000},{'solar_program':'nem'},{'tax_confirmed':False}])
def test_missing_eligibility_or_unsupported_fails(changes):
 a=account();a.update(changes)
 with pytest.raises(ValueError):eligibility('ladwp_r-1a',a,'2026-07-01','2026-07-31')


def test_no_historical_rate_extrapolation_or_hourly_demand():
 with pytest.raises(ValueError,match='coverage'):bill('sce_d',frame('2024-05-01','2024-05-31'),account('sce'),'2024-05-01','2024-05-31')
 with pytest.raises(ValueError,match='15-minute'):bill('sce_d',frame().iloc[::4],account('sce'),'2026-07-01','2026-07-31')
 with pytest.raises(ValueError,match='Export'):bill('sce_d',frame().assign(grid_export_kw=1),account('sce'),'2026-07-01','2026-07-31')


def test_dst_counts_actual_instants():
 f=frame('2025-11-01','2025-11-30')
 assert len(f)==30*96+4
 r=bill('ladwp_r-1b',f,account(),'2025-11-01','2025-11-30')
 assert r['usage_kWh']==721


def test_independent_adjustment_version_boundary():
 f=frame('2026-06-30','2026-07-01')
 a=account();a['billing_month_factor']=2/30
 r=bill('ladwp_r-1b',f,a,'2026-06-30','2026-07-01')
 assert r['line_items']['IRCA']==pytest.approx(24*.05505+24*.06934)
 assert len(r['adjustment_versions'])==2


@pytest.mark.parametrize('key',['ladwp_r-1a','ladwp_r-1b','sce_tou-d-4-9','sce_tou-d-prime'])
def test_storage_bill_reconciliation_and_physics(key):
 f=frame('2026-07-06','2026-07-07');f['pv_available_kw']=np.where((f.timestamp.dt.hour>=10)&(f.timestamp.dt.hour<15),3.,0.)
 a=account(key.split('_')[0]);a.update(solar_program='approved_non_export',interconnection_confirmed=True,billing_month_factor=2/30)
 r=optimize(key,f,a,'2026-07-06','2026-07-07',dict(capacity_kWh=10,energy_kWh=5,SOC_min=.2,SOC_max=.8,max_charge_kw=3,max_discharge_kw=3,charge_efficiency=.95,discharge_efficiency=.95),.01)
 d=r['dispatch']
 assert r['objective_gap']<.02
 assert r['bill']['total']+r['degradation_cost']<=r['solar_bill']['total']+.02
 assert np.allclose(d.grid_import_kw+d.pv_output_kw+d.battery_discharge_kw,d.native_load_kw+d.battery_charge_kw,atol=1e-5)
 assert np.maximum(d.pv_output_kw-d.pv_available_kw,0).max()<1e-5
 assert d.grid_export_kw.sum()==0
 assert d.energy_kWh.min()>=2-1e-5 and d.energy_kWh.max()<=8+1e-5


def test_socal_bill_only_mode_reports_wear_without_pricing_it():
 f=frame('2026-07-06','2026-07-07')
 f['pv_available_kw']=np.where((f.timestamp.dt.hour>=10)&(f.timestamp.dt.hour<15),3.,0.)
 a=account('sce');a.update(solar_program='approved_non_export',interconnection_confirmed=True,billing_month_factor=2/30)
 b=dict(capacity_kWh=10,energy_kWh=5,SOC_min=.2,SOC_max=.8,max_charge_kw=3,max_discharge_kw=3,charge_efficiency=.95,discharge_efficiency=.95)
 bill_only=optimize('sce_tou-d-4-9',f,a,'2026-07-06','2026-07-07',b,10)
 wear_aware=optimize('sce_tou-d-4-9',f,a,'2026-07-06','2026-07-07',b,10,
                     include_degradation_in_optimization=True)
 assert bill_only['bill']['total'] < wear_aware['bill']['total']-1
 assert bill_only['degradation_cost'] > 0
 assert wear_aware['degradation_cost'] == pytest.approx(0,abs=1e-4)


def study_request(utility='ladwp'):
 return dict(schema_version=6,name='Synthetic SoCal verification',resolution_id='a'*32,
  resolution={'status':'approximate','delivery_utility':utility,'delivery_candidates':[{'utility_id':utility}],
   'coordinates':{'latitude':34.05,'longitude':-118.24}},mode='hypothetical_bundled',
  tariff_id='ladwp_r-1b' if utility=='ladwp' else 'sce_tou-d-prime',
  account=account(utility,actual_generation_provider='bundled'),site_profile={'site_type':'residential','subtype':'house'},
  start_date='2026-07-01',end_date='2026-07-31',timezone='America/Los_Angeles',timestep_minutes=15,
  load={'mode':'daily_peak','base_kw':1.,'peak_kw':2.,'peak_start_hour':16,'peak_end_hour':21},
  solar={'capacity_kw':0.,'tilt':20.,'azimuth':180.},battery=None,degradation_cost_per_kWh=0.)


def test_cca_cannot_be_relabelled_actual_bundled_by_api():
 from src.local_web.socal_study import validate
 r=study_request('sce');r['mode']='actual_service';r['resolution']['status']='verified'
 r['account']['actual_generation_provider']='cca'
 with pytest.raises(ValueError,match='Actual CCA'):validate(r)
 r['mode']='hypothetical_bundled';assert validate(r)==r


def test_stale_location_type_and_period_rejected():
 from src.local_web.socal_study import validate
 r=study_request();r['resolution']['delivery_candidates']=[];r['resolution']['delivery_utility']='sce'
 with pytest.raises(ValueError,match='resolved location'):validate(r)
 r=study_request();r['site_profile']={'site_type':'commercial','subtype':None}
 with pytest.raises(ValueError,match='customer type'):validate(r)
 r=study_request('sce');r['end_date']='2026-09-01'
 with pytest.raises(ValueError,match='one monthly'):validate(r)


@pytest.mark.parametrize('agency,utility',[(58970,'ladwp'),(86250,'sce')])
def test_socal_geographic_identity_boundary_and_manual_override(agency,utility):
 from src.local_web.utility_resolution import resolve_service
 from test_municipal import feature,geo_get
 coords={'latitude':34.05,'longitude':-118.24}
 result=resolve_service(coords,get=geo_get([feature(agency,'Misleading city name')]))
 assert result['delivery_utility']==utility and result['status']=='approximate'
 assert result['sources'][0]['response_sha256']
 result=resolve_service(coords,get=geo_get([feature(agency)], [feature(agency),feature(999,oid=2)]))
 assert result['status']=='ambiguous'
 result=resolve_service(coords,get=geo_get([feature(999,'Los Angeles')]))
 assert result['status']=='unsupported' and result['delivery_utility'] is None
 manual=dict(delivery_utility=utility,evidence_type='utility_confirmation',reference='Synthetic test evidence',confirmed_on='2026-07-01')
 result=resolve_service({**coords,'manual_confirmation':manual},get=geo_get([feature(999)]))
 assert result['status']=='verified' and result['mapped_status']=='unsupported'
 assert result['manual_confirmation']==manual


def test_ladwp_commercial_ratchet_hand_bill():
 a=account();a.update(customer_class='commercial',previous_11_month_peaks_kw=[20.]*11)
 r=bill('ladwp_a-1a',frame(kw=10),a,'2026-07-01','2026-07-31')
 assert r['total']==pytest.approx(7+20*(5.36+.46+.96+3.08)+7440*(.08188+.05690+.06302+.01071+.01817+.03307+.0003))
 a['previous_11_month_peaks_kw']=[]
 with pytest.raises(ValueError,match='11 preceding'):bill('ladwp_a-1a',frame(kw=10),a,'2026-07-01','2026-07-31')


def test_sce_demand_rounding_peak_windows_and_optimizer():
 a=account('sce');a.update(customer_class='commercial',non_cpp_confirmed=True)
 f=frame('2026-07-06','2026-07-06',kw=10.4)
 f.loc[f.timestamp.dt.hour==17,['native_load_kw','grid_import_kw']]=10.5
 r=bill('sce_tou-gs-1-d',f,a,'2026-07-06','2026-07-06')
 assert r['line_items']['facilities_demand']==pytest.approx(11*22.61)
 assert r['line_items']['tou_demand']==pytest.approx(11*21.38)
 result=optimize('sce_tou-gs-1-d',f,a,'2026-07-06','2026-07-06',dict(capacity_kWh=10,energy_kWh=5,SOC_min=.2,SOC_max=.8,max_charge_kw=3,max_discharge_kw=3,charge_efficiency=.95,discharge_efficiency=.95),.01)
 assert result['objective_gap']<.02
 assert result['bill']['total']+result['degradation_cost']<r['total']


def test_socal_durable_api_worker_and_saved_results(tmp_path):
 import json
 from urllib.error import HTTPError
 from test_local_web_pipeline import api_service,until
 from src.local_web.runtime import JobRunner
 r=study_request();rid=r.pop('resolution_id');resolution=r.pop('resolution')
 with api_service(tmp_path) as (app,call):
  source=tmp_path/'candidate'/rid;source.mkdir(parents=True)
  (source/'resource-request.json').write_text(json.dumps({'kind':'utility-resolution'}))
  (source/'resource.json').write_text(json.dumps(resolution))
  token=call('/api/capabilities')[1]['token']
  r['resolution_id']=rid
  with pytest.raises(HTTPError) as exc:call('/api/v1/socal/studies',{**r,'resolution':resolution},token)
  assert exc.value.code==400
  code,job=call('/api/v1/socal/studies',r,token);assert code==202
  runner=JobRunner(app.store)
  try:
   result=until(lambda:call('/api/studies/'+job['id'])[1],lambda x:x['status'] in ('completed','failed'))
   assert result['status']=='completed',result.get('error')
   assert result['engine_id']==app.engine['id']
   assert result['request']['account']==r['account']
   assert result['result']['tariff_data_version'].startswith('socal-')
   table=call('/api/studies/'+job['id']+'/tables/comparison')[1]
   totals=[row[table['columns'].index('utility_bill')] for row in table['data']]
   assert len(totals)==1 and totals[0]>0
   assert b'energy_charge' in call('/api/studies/'+job['id']+'/tables/costs.csv')[1]
  finally:runner.close()


def test_naive_instants_and_unknown_exports_rejected():
 f=frame();f['timestamp']=pd.DatetimeIndex(f.timestamp).tz_convert('UTC').tz_localize(None)
 with pytest.raises(ValueError,match='UTC offset'):bill('ladwp_r-1b',f,account(),'2026-07-01','2026-07-31')
 with pytest.raises(ValueError,match='Export'):bill('ladwp_r-1b',frame().assign(grid_export_kw=float('nan')),account(),'2026-07-01','2026-07-31')
