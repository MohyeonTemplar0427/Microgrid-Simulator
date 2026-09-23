"""Build occupied-home hourly load estimates for a complete local calendar year.

Pinned stock: ResStock 2025.1 AMY2018. Outputs are fixed-stock scenarios, not
empirically calibrated forecasts. Browser features are not registered/changed.
"""
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.run_fresno_residential_study import (
    ROOT, CACHE, BASE, TOTAL, SOURCE_URLS, fetch, prepare_dwelling, select_population,
    component_name, response_mapping, save_profile, sha, np, pd,
    Provenance, ResidentialProfile, TemperatureWeather, WeatherResponseModel,
    read_resstock_csv, coarsen_profile, aggregate_population, compare_profiles,
)
from src.profiles.residential import annual_noaa_weather

COUNTIES = {
    'fresno': dict(gisjoin='G0600190', name='Fresno County, CA', station='72389093193',
                   station_name='Fresno Yosemite International Airport'),
    'alameda': dict(gisjoin='G0600010', name='Alameda County, CA', station='72493023230',
                    station_name='Oakland International Airport'),
}


def occupied_county(metadata, gisjoin):
    frame=metadata.loc[(metadata['in.county']==gisjoin)&(metadata.completed_status=='Success')&
                       (metadata['in.vacancy_status']=='Occupied')].copy()
    if frame.empty:
        raise ValueError('No successful occupied models for county')
    return frame


def build(county_key, *, year=2024, sample_size=256, households=100, download=False, output=None):
    config=COUNTIES[county_key]
    if not np.isfinite(households) or households<=0:
        raise ValueError('households must be positive')
    output=Path(output or ROOT/f'results/residential_{county_key}_{year}_hourly')
    output.mkdir(parents=True,exist_ok=True)
    metadata_path=fetch(SOURCE_URLS['metadata.parquet'],CACHE/'metadata.parquet',download)
    county=occupied_county(pd.read_parquet(metadata_path),config['gisjoin'])
    selected,strata=select_population(county,sample_size)
    selected[['bldg_id','in.county','in.vacancy_status','in.cec_climate_zone','stratum','weight',
              'study_weight','inclusion_probability',TOTAL]].to_csv(output/'selected_households.csv',index=False)
    pd.DataFrame(strata).to_csv(output/'sampling_strata.csv',index=False)
    print(f'{county_key}: selected {len(selected)} occupied models of {len(county)}',flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        files=list(pool.map(lambda i:prepare_dwelling(int(i),download),selected.bldg_id))
    provenance=Provenance(config['name'],'ResStock 2025.1 AMY2018; circa-2018 stock','amy2018',BASE,'America/Los_Angeles')
    profiles=[];evidence=[];temperature=None
    for path,record in files:
        raw=pd.read_csv(path)
        mapping={component_name(c):c for c in raw if c.startswith('out.electricity.') and c.endswith('..kwh')
                 and component_name(c) not in {'total','net','pv'}}
        profile=read_resstock_csv(path,provenance=replace(provenance,source=record['url']),
            end_use_columns=mapping,total_column=TOTAL,unit='kWh',timestamp_convention='end',
            source_timezone='Etc/GMT+5',timestep_minutes=15,
            rounding_tolerance_kw=(len(mapping)+1)*.000005*4+1e-6)
        profiles.append(coarsen_profile(profile,60));evidence.append(record)
        current=raw['out.outdoor_air_drybulb_temp..c'].to_numpy().reshape(-1,4).mean(axis=1)
        if temperature is None: temperature=current
        elif not np.allclose(current,temperature,atol=1e-5):
            raise ValueError('County has multiple simulation weather series; split population before fitting')
    published=aggregate_population(profiles,selected.study_weight,households=households)
    published.diagnostics.update(population_basis='occupied_housing_units',county_gisjoin=config['gisjoin'])
    save_profile(published,output,'published_occupied_2018')
    keep=published.end_uses_kw.index>=pd.Timestamp('2018-01-01',tz='Etc/GMT+8')
    training=replace(published,end_uses_kw=published.end_uses_kw.loc[keep])
    weather=TemperatureWeather(pd.DataFrame({'temperature_c':temperature[keep]},index=training.end_uses_kw.index),
        60,config['name'],'amy2018','Matched ResStock embedded temperature; EST end converted to UTC start')
    responses=response_mapping(training.end_uses_kw.columns)
    before=training.end_uses_kw.index<pd.Timestamp('2018-09-01',tz='Etc/GMT+8')
    held_model=WeatherResponseModel.fit(replace(training,end_uses_kw=training.end_uses_kw.loc[before]),
        replace(weather,frame=weather.frame.loc[before]),response_by_end_use=responses)
    reference=replace(training,end_uses_kw=training.end_uses_kw.loc[~before])
    held=held_model.predict(replace(weather,frame=weather.frame.loc[~before]),allow_extrapolation=True)
    metrics=compare_profiles(held,reference.native_load_kw)
    metrics.update(reference='Excluded Sep–Dec ResStock simulation, not customer measurements',
        energy_bias_pct=100*metrics['energy_bias_kwh']/reference.energy_kwh().sum(),
        normalized_rmse_pct=100*metrics['rmse_kw']/reference.native_load_kw.mean())
    model=WeatherResponseModel.fit(training,weather,response_by_end_use=responses)
    paths=[];weather_sources=[]
    for y in [year,year+1]:
        station=config['station'];url=f'https://www.ncei.noaa.gov/data/global-hourly/access/{y}/{station}.csv'
        path=CACHE/f'noaa_{station}_{y}.csv'
        if county_key=='fresno' and y==2024: path=CACHE/'noaa_2024.csv'
        paths.append(fetch(url,path,download));weather_sources.append(dict(url=url,sha256=sha(path)))
    actual,audit=annual_noaa_weather(paths,station=config['station'],region=config['name'],year=year,max_gap_hours=1)
    estimated=model.predict(actual,allow_extrapolation=True)
    estimated.diagnostics.update(population_basis='occupied_housing_units',calibration_applied=False,
        fixed_stock_year=2018,weather_year=year,station_name=config['station_name'],
        county_gisjoin=config['gisjoin'],spatial_weather_basis='One airport proxy for county; no spatial microclimate weighting')
    save_profile(estimated,output,'hourly_load')
    frame=estimated.frame().set_index('timestamp')
    frame['timestamp_local']=audit.timestamp_local
    frame['temperature_c']=audit.temperature_c
    frame['weather_quality']=audit.weather_quality
    lo,hi=model.temperature_range_c
    frame['temperature_extrapolated']=~audit.temperature_c.between(lo,hi)
    frame['occupied_homes']=households
    frame.to_csv(output/'hourly_load_with_quality.csv',index=True)
    audit.to_csv(output/'weather_hourly_audit.csv')
    # UTC-indexed rows preserve both fall-back hours; monthly accounting is local.
    local=estimated.end_uses_kw.tz_convert('America/Los_Angeles')
    monthly=local.resample('MS').sum()  # hourly kW * one elapsed hour = kWh
    monthly['total_kwh']=monthly.sum(axis=1)
    monthly['hours']=local.resample('MS').size()
    monthly['average_kw']=monthly.total_kwh/monthly.hours
    monthly['kwh_per_occupied_home']=monthly.total_kwh/households
    monthly.to_csv(output/'monthly_energy.csv',index_label='month_start_local')
    sample_mean=float(np.average(selected[TOTAL],weights=selected.study_weight))
    full_mean=float(np.average(county[TOTAL],weights=county.weight))
    summary=dict(county=config['name'],county_gisjoin=config['gisjoin'],population_basis='occupied_housing_units',
        weather_year=year,fixed_stock_year=2018,sample_models=len(selected),population_models=len(county),occupied_homes=households,
        full_population_mean_kwh=full_mean,sample_mean_kwh=sample_mean,sample_discrepancy_pct=100*(sample_mean/full_mean-1),
        hours=len(frame),start_utc=frame.index[0].isoformat(),end_exclusive_utc=estimated.end.isoformat(),
        annual_kwh_per_occupied_home=float(estimated.energy_kwh().sum()/households),
        coincident_peak_kw_per_occupied_home=float(estimated.native_load_kw.max()/households),
        interpolated_weather_hours=actual.diagnostics['interpolated_hours'],
        temperature_extrapolated_hours=int(frame.temperature_extrapolated.sum()),station=config['station'],station_name=config['station_name'],
        held_out_simulation_metrics=metrics,calibration_applied=False,empirical_validation=False,
        climate_zones=county['in.cec_climate_zone'].value_counts().to_dict())
    (output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    (output/'sources.json').write_text(json.dumps(dict(metadata=dict(url=SOURCE_URLS['metadata.parquet'],sha256=sha(metadata_path)),
        dwellings=evidence,weather=weather_sources),indent=2))
    (output/'README.md').write_text(f'''# {config['name']}: {year} occupied-home hourly load

Generated {len(frame):,} consecutive hourly rows for the complete local calendar
year, representing {households:g} occupied homes. All timestamps identify interval
starts. UTC timestamps are unique; local timestamps include offsets for DST.
Loads are interval-average kW, so one hourly row contributes that many kWh.

Main deliverable: hourly_load_with_quality.csv. It includes each end use,
`native_load_kw`, temperature, weather-quality flag, extrapolation flag,
local timestamp and occupied-home count. monthly_energy.csv supplies monthly
kWh, average kW and elapsed-hour counts. hourly_load.json records fitted
coefficients and provenance; sources.json records input hashes and URLs.

## Weather and model limits

Station: {config['station_name']} ({config['station']}). {actual.diagnostics['interpolated_hours']}
interior missing hours were interpolated between accepted adjacent observations;
every replacement is flagged in weather_hourly_audit.csv. Gaps longer than one
hour and missing boundary hours are rejected. Adjoining {year+1} UTC observations
supply the end of the local year. {int(frame.temperature_extrapolated.sum())} hours
lie outside the simulation training temperature range and are explicitly flagged.

Stock and equipment remain at the ResStock circa-2018 baseline. This is a weather
scenario, not a forecast incorporating {year} adoption, efficiency or household
changes. Vacant units are excluded before sampling and weighting. The sample
contains {len(selected)} of {len(county)} occupied county models; its baseline annual
mean differs from the full occupied county model population by
{summary['sample_discrepancy_pct']:+.2f}%.

The airport is a weather proxy, not spatially weighted county weather. Alameda
in particular spans coastal Oakland and warmer inland locations; a county-wide
absolute estimate needs geographically matched stock/weather groups. The current
county model is a documented initial scenario. No local calibration is applied.

Held-out September–December simulation test: energy bias
{metrics['energy_bias_pct']:+.2f}%, hourly normalized RMSE {metrics['normalized_rmse_pct']:.2f}%.
This measures agreement with ResStock, not measured-household validation. Heating,
cooling, and hourly schedules are approximations; humidity and thermal lag are absent.

## Reproduce

```bash
python3 tools/build_county_residential_year.py --county {county_key} --year {year} --sample-size {sample_size} --households {households:g} --download --output {output}
```

Omit --download for a cache-only replay. No browser feature is changed.
''')
    print(json.dumps(summary,indent=2),flush=True)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--county',choices=COUNTIES,required=True)
    parser.add_argument('--year',type=int,default=2024)
    parser.add_argument('--sample-size',type=int,default=256)
    parser.add_argument('--households',type=float,default=100)
    parser.add_argument('--download',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    build(args.county,year=args.year,sample_size=args.sample_size,households=args.households,download=args.download,output=args.output)
