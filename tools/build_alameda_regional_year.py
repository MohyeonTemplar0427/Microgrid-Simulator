"""Alameda occupied-stock split by CEC zone with distinct 2024 weather."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse,json
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from tools.build_county_residential_year import occupied_county
from tools.run_fresno_residential_study import (ROOT,CACHE,BASE,TOTAL,SOURCE_URLS,fetch,prepare_dwelling,
    select_population,component_name,response_mapping,save_profile,sha,pd,np,Provenance,
    TemperatureWeather,WeatherResponseModel,aggregate_population,coarsen_profile,read_resstock_csv,compare_profiles)
from src.profiles.residential import annual_noaa_weather
from src.profiles.residential.regional_weather import regional_noaa_weather
from src.profiles.residential.regional_model import combine_regional_profiles

GROUPS={'3':dict(key='bay_side',name='Alameda CEC zone 3 (Bay-side)',station='72493023230'),
        '12':dict(key='inland',name='Alameda CEC zone 12 (inland)',station='72492723285')}


def partition_population(county):
    zones=county['in.cec_climate_zone'].astype(str)
    if not set(zones)<=set(GROUPS) or county.empty:
        raise ValueError('Expected nonempty Alameda occupied stock in CEC zones 3 and 12')
    if not county['in.vacancy_status'].eq('Occupied').all():
        raise ValueError('Vacant units must be excluded before partitioning')
    return {z:county.loc[zones.eq(z)].copy() for z in GROUPS if zones.eq(z).any()}


def run(output,download=False,sample_size=128,households=100):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if not np.isfinite(households) or households<=0:raise ValueError('Positive household count required')
    metadata_path=fetch(SOURCE_URLS['metadata.parquet'],CACHE/'metadata.parquet',download)
    county=occupied_county(pd.read_parquet(metadata_path),'G0600010');groups=partition_population(county)
    station_paths={}
    for station in ['72493023230','72492723285']:
        station_paths[station]=[fetch(f'https://www.ncei.noaa.gov/data/global-hourly/access/{y}/{station}.csv',
            CACHE/f'noaa_{station}_{y}.csv',download) for y in [2024,2025]]
    contributions=[];counterfactuals=[];summaries=[];audits={};gap_sensitivity=[]
    sources=dict(metadata=dict(url=SOURCE_URLS['metadata.parquet'],sha256=sha(metadata_path)),dwellings=[],weather=[])
    for station,paths in station_paths.items():
        sources['weather'] += [dict(url=f'https://www.ncei.noaa.gov/data/global-hourly/access/{y}/{station}.csv',sha256=sha(p)) for y,p in zip([2024,2025],paths)]
    for z,stock in groups.items():
        config=GROUPS[z];key=config['key'];dest=output/key;dest.mkdir(exist_ok=True)
        selected,strata=select_population(stock,sample_size)
        cols=['bldg_id','in.cec_climate_zone','in.city','in.puma','in.vacancy_status','in.hvac_cooling_type',
              'in.geometry_building_type_recs','in.weather_file_city','weight','study_weight','stratum',TOTAL]
        selected[cols].to_csv(dest/'selected_households.csv',index=False)
        pd.DataFrame(strata).to_csv(dest/'sampling_strata.csv',index=False)
        print(f'{key}: {len(selected)} of {len(stock)} occupied models',flush=True)
        with ThreadPoolExecutor(max_workers=4) as pool:
            files=list(pool.map(lambda i:prepare_dwelling(int(i),download),selected.bldg_id))
        provenance=Provenance(config['name'],'ResStock 2025.1 AMY2018; circa-2018 stock','amy2018',BASE,'America/Los_Angeles')
        profiles=[];temperature=None
        for path,evidence in files:
            raw=pd.read_csv(path);mapping={component_name(c):c for c in raw if c.startswith('out.electricity.')
                and c.endswith('..kwh') and component_name(c) not in {'total','net','pv'}}
            p=read_resstock_csv(path,provenance=replace(provenance,source=evidence['url']),end_use_columns=mapping,
                total_column=TOTAL,unit='kWh',timestamp_convention='end',source_timezone='Etc/GMT+5',
                timestep_minutes=15,rounding_tolerance_kw=(len(mapping)+1)*.000005*4+1e-6)
            profiles.append(coarsen_profile(p,60));sources['dwellings'].append(evidence)
            t=raw['out.outdoor_air_drybulb_temp..c'].to_numpy().reshape(-1,4).mean(axis=1)
            if temperature is None:temperature=t
            elif not np.allclose(t,temperature,atol=1e-5):raise ValueError('Multiple training weather series within region')
        published=aggregate_population(profiles,selected.study_weight,households=100)
        published.diagnostics.update(population_basis='occupied_housing_units',cec_zone=z)
        save_profile(published,dest,'published_100_occupied_homes_2018')
        keep=published.end_uses_kw.index>=pd.Timestamp('2018-01-01',tz='Etc/GMT+8')
        training=replace(published,end_uses_kw=published.end_uses_kw.loc[keep])
        weather=TemperatureWeather(pd.DataFrame({'temperature_c':temperature[keep]},index=training.end_uses_kw.index),
            60,config['name'],'amy2018','Embedded matched ResStock weather; county-assigned Hayward baseline')
        mapping=response_mapping(training.end_uses_kw)
        before=training.end_uses_kw.index<pd.Timestamp('2018-09-01',tz='Etc/GMT+8')
        hold=WeatherResponseModel.fit(replace(training,end_uses_kw=training.end_uses_kw.loc[before]),
            replace(weather,frame=weather.frame.loc[before]),response_by_end_use=mapping)
        pred=hold.predict(replace(weather,frame=weather.frame.loc[~before]),allow_extrapolation=True)
        ref=training.native_load_kw.loc[~before];metrics=compare_profiles(pred,ref)
        metrics.update(energy_bias_pct=100*metrics['energy_bias_kwh']/ref.sum(),normalized_rmse_pct=100*metrics['rmse_kw']/ref.mean())
        model=WeatherResponseModel.fit(training,weather,response_by_end_use=mapping)
        oakland,oak_audit=annual_noaa_weather(station_paths['72493023230'],station='72493023230',region=config['name'],year=2024)
        if z=='3':actual,audit=oakland,oak_audit
        else:actual,audit=regional_noaa_weather(station_paths['72492723285'],station_paths['72493023230'],
                station='72492723285',backup_station='72493023230',region=config['name'])
        result=model.predict(actual,allow_extrapolation=True)
        result.diagnostics.update(population_basis='occupied_housing_units',cec_zone=z,calibration_applied=False)
        save_profile(result,dest,'hourly_100_occupied_homes_2024')
        audit['temperature_extrapolated']=~audit.temperature_c.between(*model.temperature_range_c)
        audit.to_csv(dest/'weather_audit.csv');audits[key]=audit
        frame=result.frame().set_index('timestamp').join(audit[['temperature_c','weather_quality','temperature_extrapolated','timestamp_local']])
        frame.to_csv(dest/'hourly_load_with_quality.csv')
        share=float(stock.weight.sum()/county.weight.sum());scale=households*share/100
        contributions.append(replace(result,end_uses_kw=result.end_uses_kw*scale,households=households*share,
            diagnostics={**result.diagnostics,"community_scale_factor":scale,"coefficients_basis_households":100}))
        counter=model.predict(oakland,allow_extrapolation=True)
        counterfactuals.append(replace(counter,end_uses_kw=counter.end_uses_kw*scale,households=households*share,
            diagnostics={**counter.diagnostics,"community_scale_factor":scale,"coefficients_basis_households":100}))
        if z=='12':
            for direction in [-1,1]:
                altered=actual.frame.copy();mask=audit.weather_quality.ne('observed')
                altered.loc[mask,'temperature_c']+=direction*actual.diagnostics['held_out_rmse_c']
                sensitive=model.predict(replace(actual,frame=altered),allow_extrapolation=True)
                gap_sensitivity.append(dict(temperature_shift_sign=direction,
                    county_energy_change_kwh=float((sensitive.energy_kwh().sum()-result.energy_kwh().sum())*scale)))
        sample_mean=float(np.average(selected[TOTAL],weights=selected.study_weight));population_mean=float(np.average(stock[TOTAL],weights=stock.weight))
        summaries.append(dict(group=key,cec_zone=z,population_models=len(stock),sample_models=len(selected),
            county_occupied_share=share,represented_homes=households*share,
            population_cooling_installed_pct=float(np.average(stock['in.hvac_cooling_type'].ne('None'),weights=stock.weight)*100),
            sample_discrepancy_pct=100*(sample_mean/population_mean-1),annual_kwh_per_occupied_home=float(result.energy_kwh().sum()/100),
            cooling_kwh_per_occupied_home=float((result.energy_kwh().cooling+result.energy_kwh().cooling_fans_pumps)/100),
            temperature_extrapolated_hours=int(audit.temperature_extrapolated.sum()),weather_quality_counts=audit.weather_quality.value_counts().to_dict(),
            baseline_weather_cities=stock['in.weather_file_city'].value_counts().to_dict(),cities=stock['in.city'].value_counts().to_dict(),
            held_out_simulation_metrics=metrics,weather_diagnostics=actual.diagnostics))
    combined_provenance=Provenance('Alameda County, CA',contributions[0].provenance.release,'regional-noaa-2024',
        'CEC zone 3 Oakland + CEC zone 12 Livermore; separate stocks and models','America/Los_Angeles')
    combined=combine_regional_profiles(contributions,combined_provenance)
    counter=combine_regional_profiles(counterfactuals,replace(combined_provenance,weather_id='all-oakland-2024-counterfactual'))
    save_profile(combined,output,'combined_hourly_load');save_profile(counter,output,'same_stock_all_oakland')
    frame=combined.frame().set_index('timestamp');frame['timestamp_local']=frame.index.tz_convert('America/Los_Angeles').astype(str)
    for summary,p in zip(summaries,contributions):
        key=summary['group'];frame[f'{key}_contribution_kw']=p.native_load_kw
        for c in ['temperature_c','weather_quality','temperature_extrapolated']:frame[f'{key}_{c}']=audits[key][c]
    frame.to_csv(output/'combined_hourly_load_with_quality.csv')
    monthly=pd.DataFrame({s['group']:p.native_load_kw for s,p in zip(summaries,contributions)})
    monthly['combined']=combined.native_load_kw;monthly['same_stock_all_oakland']=counter.native_load_kw
    monthly=monthly.tz_convert('America/Los_Angeles').resample('MS').sum()
    monthly.to_csv(output/'monthly_energy_kwh.csv',index_label='month_start_local')
    oldpath=ROOT/'results/residential_alameda_2024_hourly/hourly_load_with_quality.csv'
    previous_comparison=None
    if oldpath.exists():
        old=pd.read_csv(oldpath);old.index=pd.to_datetime(old.timestamp,utc=True)
        if not old.index.equals(combined.end_uses_kw.index):raise ValueError('Prior baseline interval mismatch')
        old_kw=old.native_load_kw*households/100
        previous_comparison=dict(previous_annual_kwh=float(old_kw.sum()),change_pct=100*(combined.native_load_kw.sum()/old_kw.sum()-1),
            warning='Includes changed sampling and separate regional fits; not a pure weather effect',input_sha256=sha(oldpath))
    summary=dict(year=2024,households=households,hours=len(frame),population_basis='occupied_housing_units',groups=summaries,
        annual_kwh_per_occupied_home=float(combined.energy_kwh().sum()/households),
        coincident_peak_kw_per_occupied_home=float(combined.native_load_kw.max()/households),
        same_stock_all_oakland_kwh_per_home=float(counter.energy_kwh().sum()/households),
        regional_weather_change_pct=float(100*(combined.energy_kwh().sum()/counter.energy_kwh().sum()-1)),
        previous_county_comparison=previous_comparison,gap_temperature_sensitivity=gap_sensitivity,
        calibration_applied=False,empirical_accuracy_improvement_demonstrated=False)
    (output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False));(output/'sources.json').write_text(json.dumps(sources,indent=2))
    lines='\n'.join(f"| {s['group']} | {s['cec_zone']} | {s['county_occupied_share']*100:.2f}% | {s['population_cooling_installed_pct']:.1f}% | {s['annual_kwh_per_occupied_home']:.0f} | {s['sample_discrepancy_pct']:+.2f}% |" for s in summaries)
    (output/'README.md').write_text(f'''# Alameda regional occupied-home scenario, 2024

Split by ResStock CEC climate-zone metadata, not invented city boundaries.
Zone 12 metadata names Livermore, Pleasanton and Dublin; zone 3 is the Bay-side
proxy group. Hills and transition areas are not separately resolved.
128 homes per group by default are independently sampled within dwelling-type
and cooling-ownership strata. Sample proportions are NOT county proportions.
Population expansion weights set each group's contribution to {households:g} occupied homes.

| Group | CEC zone | County occupied share | Installed cooling | Annual kWh/home | Sample baseline error vs full group |
|---|---:|---:|---:|---:|---:|
{lines}

## Outputs and comparisons

combined_hourly_load_with_quality.csv contains {len(frame)} UTC hourly intervals,
local timestamps, end uses, total kW, regional contributions, temperatures and
quality/extrapolation flags. Group files each represent 100 occupied homes;
combined contributions use the county shares above. monthly_energy_kwh.csv
contains local-calendar monthly energy. Manifests and source hashes accompany data.

Combined annual estimate: {summary['annual_kwh_per_occupied_home']:.1f} kWh/home.
Compared with the SAME region-specific stock and fitted models all receiving
Oakland weather, using Livermore inland changes annual energy by
{summary['regional_weather_change_pct']:+.2f}%. The separate comparison to the old
county model also changes sampling and fitting; it is not purely a weather effect.

## Weather and validity

Bay-side uses Oakland; inland uses Livermore. Oakland has two isolated hourly
interpolations. Livermore has 66 missing hours, replaced using Oakland plus a
month/hour station-difference correction. One replacement also relies on an
interpolated Oakland hour. All replacements are flagged. Correction validation
holds days 10–11 of each month out of offset fitting; metrics are in summary.json.
These are estimated replacements, not observations. The gap sensitivity shifts
only replacement temperatures by plus/minus held-out RMSE; it is not a confidence interval.

ResStock assigned the same Hayward baseline weather to these county homes,
including inland models. Fits use their matched embedded 2018 temperatures;
we did NOT rerun inland EnergyPlus with Livermore baseline weather. Higher
inland temperatures can therefore require extrapolation, explicitly flagged.
Stock remains circa 2018. This split improves geographic detail, but increased
empirical accuracy is not established. No local calibration has been applied.

CEC climate-zone reference: https://www.energy.ca.gov/programs-and-topics/programs/building-energy-efficiency-standards/climate-zone-tool-maps-and

## Reproduce

```bash
python3 tools/build_alameda_regional_year.py --download --sample-size {sample_size} --households {households:g} --output {output}
```

Omit --download to replay cached inputs. Browser features remain unchanged.
''')
    print(json.dumps({k:v for k,v in summary.items() if k!='groups'},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--download',action='store_true')
    p.add_argument('--sample-size',type=int,default=128);p.add_argument('--households',type=float,default=100)
    p.add_argument('--output',type=Path,default=ROOT/'results/residential_alameda_regional_2024')
    a=p.parse_args();run(a.output,a.download,a.sample_size,a.households)
