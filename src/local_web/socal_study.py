"""Schema 6: account-qualified Southern California studies in the existing queue."""
from pathlib import Path
import io
import numpy as np
import pandas as pd
from ..billing.socal import PLANS,VERSION,eligibility,bill,number
from ..dispatch.battery import Battery
from .grid_only import save_results

FIELDS={'schema_version','name','resolution_id','resolution','mode','account','tariff_id','site_profile',
        'start_date','end_date','timezone','timestep_minutes','load','solar','battery','degradation_cost_per_kWh'}


def capabilities():
 return {'schema_version':6,'tariff_data_version':VERSION,'plans':list(PLANS.values()),
 'solar_programs':[{'id':'none','label':'No solar'},{'id':'approved_non_export','label':'Approved non-export PV · self-consumption only'}],
 'unsupported':['SCE CCA generation tariffs','NEM/NBT export credits and true-up','CARE/FERA/medical or other special riders','CPP events','Reactive-power charges'],
 'baseline_regions':['5','6','8','9','10','13','14','15','16']}


def billing_account(r):
 account=dict(r['account'])
 if account.get('customer_class')=='residential':
  accommodation='multifamily' if r['site_profile']['subtype']=='apartment_unit' else 'single_family'
  if account.get('accommodation',accommodation)!=accommodation:
   raise ValueError('Accommodation must match the residential site subtype.')
  account['accommodation']=accommodation
 return account


def validate(r):
 from .site_profile import customer_class
 if not isinstance(r,dict) or set(r)!=FIELDS or r['schema_version']!=6:raise ValueError('Supply exactly the schema 6 Southern California study fields.')
 if not isinstance(r['name'],str) or not 1<=len(r['name'].strip())<=120:raise ValueError('Enter a study name.')
 if r['timezone']!='America/Los_Angeles' or r['timestep_minutes']!=15:raise ValueError('Southern California studies require local Pacific time and 15-minute intervals.')
 if r['mode'] not in ('actual_service','hypothetical_bundled'):raise ValueError('Choose actual service or an explicitly hypothetical bundled comparison.')
 p=eligibility(r['tariff_id'],billing_account(r),r['start_date'],r['end_date'])
 if r['account'].get('actual_generation_provider') not in ('bundled','cca'):raise ValueError('Confirm generation enrollment separately from delivery.')
 if r['mode']=='actual_service' and r['account']['actual_generation_provider']!='bundled':raise ValueError('Actual CCA billing is unsupported; an explicitly hypothetical bundled comparison is required.')
 if customer_class(r['site_profile'])!=p['customer_class']:raise ValueError('Location-step customer type must match the account.')
 resolution=r['resolution']
 if not isinstance(resolution,dict):raise ValueError('Saved location resolution required.')
 if r['mode']=='actual_service' and (resolution.get('status')!='verified' or resolution.get('delivery_utility')!=p['utility']):raise ValueError('Actual service requires saved bill/utility-confirmed delivery.')
 if r['mode']=='hypothetical_bundled' and p['utility'] not in [c['utility_id'] for c in resolution.get('delivery_candidates',[])]+[resolution.get('delivery_utility')]:raise ValueError('Selected comparison utility must match the resolved location or confirmed override.')
 if r['battery'] is not None:Battery(**r['battery'])
 number(r['degradation_cost_per_kWh'],'Battery degradation cost',0,10)
 solar=r['solar']
 if not isinstance(solar,dict) or set(solar)!={'capacity_kw','tilt','azimuth'}:raise ValueError('Specify PV capacity, tilt and azimuth.')
 number(solar['capacity_kw'],'PV DC kW',0,10000);number(solar['tilt'],'PV tilt',0,90);number(solar['azimuth'],'PV azimuth',0,360)
 if solar['capacity_kw']>0 and r['account']['solar_program']!='approved_non_export':raise ValueError('PV requires confirmed non-export interconnection; export settlement is unsupported.')
 # Validate complete input and account classification before durable submission.
 frame=inputs(r);test=frame.assign(grid_import_kw=frame.native_load_kw,grid_export_kw=0.)
 bill(r['tariff_id'],test,billing_account(r),r['start_date'],r['end_date'])
 return r


def inputs(r):
 start=pd.Timestamp(r['start_date'],tz='America/Los_Angeles');end=pd.Timestamp(r['end_date'],tz='America/Los_Angeles')+pd.DateOffset(days=1)
 if not 1<=(end.date()-start.date()).days<=93:raise ValueError('Choose one billing cycle of 1–93 days; confirm its billed month factor.')
 idx=pd.date_range(start,end,freq='15min',inclusive='left');load=r['load']
 if load.get('mode')=='csv':
  frame=pd.read_csv(io.StringIO(load['csv']))
  if set(frame.columns)!={'timestamp','native_load_kw'}:raise ValueError('Load CSV requires timestamp,native_load_kw only.')
  from ..billing.socal import interval_index
  interval_index(frame,r['start_date'],r['end_date']);power=frame.native_load_kw.to_numpy(dtype=float)
 elif load.get('mode')=='daily_peak':
  base=number(load.get('base_kw'),'Base load',0,100000);peak=number(load.get('peak_kw'),'Peak load',base,100000)
  begin=number(load.get('peak_start_hour'),'Peak start',0,23);finish=number(load.get('peak_end_hour'),'Peak end',1,24)
  if begin>=finish:raise ValueError('Daily load peak must end after it starts.')
  power=np.where((idx.hour+idx.minute/60>=begin)&(idx.hour+idx.minute/60<finish),peak,base)
 else:raise ValueError('Choose a daily load assumption or measured CSV.')
 if not np.isfinite(power).all() or (power<0).any():raise ValueError('Load must be finite nonnegative kW.')
 return pd.DataFrame({'timestamp':idx,'native_load_kw':power,'pv_available_kw':np.zeros(len(idx))})


def execute(directory,r):
 from ..dispatch.socal import optimize
 import pvlib
 validate(r);frame=inputs(r);solar=r['solar']
 if solar['capacity_kw']:
  from ..timeseries import build_interval_index_from_days
  from ..profiles import WeatherDerivedPV, WeatherDerivedPVConfiguration
  c=r['resolution']['coordinates'];days=(pd.Timestamp(r['end_date'])-pd.Timestamp(r['start_date'])).days+1
  grid=build_interval_index_from_days(r['start_date'],days,r['timezone'],15)
  location=pvlib.location.Location(c['latitude'],c['longitude'],tz=r['timezone'])
  sky=location.get_clearsky(grid.index+pd.Timedelta(minutes=7.5),model='ineichen')
  weather=pd.DataFrame({'timestamp':grid.index,'ghi_w_per_m2':sky.ghi.to_numpy(),
   'dni_w_per_m2':sky.dni.to_numpy(),'dhi_w_per_m2':sky.dhi.to_numpy(),
   'temperature_c':20.,'wind_speed_m_per_s':1.})
  pv=WeatherDerivedPV(WeatherDerivedPVConfiguration(latitude=c['latitude'],longitude=c['longitude'],
   rated_pv_capacity_kw=solar['capacity_kw'],tilt_degrees=solar['tilt'],azimuth_degrees=solar['azimuth'],
   dc_ac_ratio=1.2,system_losses_fraction=.14,nominal_inverter_efficiency=.96),weather,
   weather_source='Explicit clear-sky study assumption').build_detailed(grid)
  frame['pv_available_kw']=pv.pv_available_kw.to_numpy()
 result=optimize(r['tariff_id'],frame,billing_account(r),r['start_date'],r['end_date'],r['battery'],r['degradation_cost_per_kWh'])
 tables=[];rows=[];costs=[];bills={};versions=[]
 if solar['capacity_kw']:tables=[('weather','Clear-sky study weather',weather),('pv','PV model diagnostics',pv.diagnostics)]
 scenarios=[('grid_only','baseline_bill')]
 if solar['capacity_kw']:scenarios.append(('pv_only','solar_bill'))
 if r['battery']:scenarios.append(('pv_storage' if solar['capacity_kw'] else 'battery_storage','bill'))
 for name,key in scenarios:
  b=result[key];wear=result['degradation_cost'] if key=='bill' else 0
  rows.append({'scenario':name,'utility_bill':b['total'],'degradation_cost':wear,'total_explicit_operating_cost':b['total']+wear,'savings_vs_grid':result['baseline_bill']['total']-b['total']-wear})
  versions.extend({'scenario':name,**v} for v in b.get('rate_versions',[]))
  costs.extend({'scenario':name,'component':k,'amount':v} for k,v in b['line_items'].items());bills[name]=b
 warnings=result['bill']['warnings']+['PV uses the existing PVWatts/temperature/inverter model with clear-sky irradiance, 20 °C air, 1 m/s wind, 14% system losses, 96% inverter efficiency and 1.2 DC/AC ratio; not measured weather.','Savings are operating costs only, excluding capital cost, incentives and lifecycle payback.']
 if not solar['capacity_kw']:warnings=[w for w in warnings if not w.startswith('PV uses')]
 if r['mode']=='hypothetical_bundled':warnings.insert(0,'HYPOTHETICAL bundled generation comparison — not the actual CCA customer bill.')
 if versions:tables.append(('rate_versions','Applied rate versions',pd.DataFrame(versions)))
 save_results(directory,r,[('comparison','Scenario operating costs',pd.DataFrame(rows)),('costs','Itemized bills',pd.DataFrame(costs)),('dispatch','15-minute dispatch',result['dispatch'])]+tables,warnings,bills=bills,tariff_data_version=VERSION,objective_reconciliation_error=result['objective_gap'],solar_program=r['account']['solar_program'])
