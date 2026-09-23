"""Auditable station gap replacement for retrospective regional scenarios."""
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .core import ResidentialError
from .weather_model import TemperatureWeather


def observed_hourly(paths, station, index):
    reports=[];sources=[]
    for path in paths:
        f=pd.read_csv(path,dtype=str)
        if not {'STATION','DATE','TMP'} <= set(f):
            raise ResidentialError('Missing NOAA columns')
        f=f.loc[f.STATION.eq(str(station))]
        if f.empty: continue
        parts=f.TMP.str.split(',',expand=True)
        if parts.shape[1]!=2: raise ResidentialError('Invalid NOAA temperature format')
        t=pd.to_numeric(parts[0],errors='coerce')/10
        good=parts[1].isin(['1','5'])&t.between(-95,65)
        reports.append(pd.Series(t[good].to_numpy(),index=pd.to_datetime(f.loc[good,'DATE'],utc=True)))
        sources.append(dict(path=str(path),sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest()))
    if not reports: raise ResidentialError('No station observations')
    return pd.concat(reports).groupby(level=0).mean().resample('h').mean().reindex(index),sources


def fill_from_backup(primary, backup, *, timezone='America/Los_Angeles', min_pairs=10, backup_observed=None):
    """Correct backup by local month/hour mean station difference.

    Fixed blocked validation: days 10–11 of each month, excluded from offset
    fitting. Final offsets use all paired observations for retrospective gap
    reconstruction. This is not a causal forecast or measured replacement.
    """
    if not primary.index.equals(backup.index) or primary.index.tz is None or not primary.index.is_unique:
        raise ResidentialError('Primary and backup need identical unique timezone-aware grids')
    if not ((primary.index[1:]-primary.index[:-1])==pd.Timedelta(hours=1)).all():
        raise ResidentialError('Weather grid must be hourly')
    for series in [primary,backup]:
        valid=series.dropna()
        if not np.isfinite(valid).all() or not valid.between(-95,65).all():
            raise ResidentialError('Invalid station temperature')
    local=primary.index.tz_convert(timezone)
    buckets=pd.Series(local.month*100+local.hour,index=primary.index)
    paired=primary.notna()&backup.notna()
    if backup_observed is not None:
        if not backup_observed.index.equals(primary.index): raise ResidentialError("Backup quality grid mismatch")
        paired &= backup_observed
    test=pd.Series(local.day.isin([10,11]),index=primary.index)&paired
    train=paired&~test
    def estimates(mask):
        dif=primary[mask]-backup[mask]
        counts=dif.groupby(buckets[mask]).count()
        means=dif.groupby(buckets[mask]).mean().where(counts>=min_pairs)
        return backup+buckets.map(means)
    held=estimates(train)
    if not test.any() or held[test].isna().any():
        raise ResidentialError('Insufficient paired data for blocked backup validation')
    error=held[test]-primary[test]
    final=estimates(paired)
    missing=primary.isna()
    if final[missing].isna().any():
        raise ResidentialError('Backup unavailable or insufficient month/hour pairs for missing hours')
    filled=primary.where(~missing,final)
    if not filled.between(-95,65).all(): raise ResidentialError('Invalid filled temperature')
    diagnostics=dict(method='Backup plus mean primary-minus-backup difference by local month/hour',
        replaced_hours=int(missing.sum()),validation='Days 10–11 each month withheld from offsets',
        validation_hours=int(test.sum()),held_out_mae_c=float(error.abs().mean()),
        held_out_rmse_c=float(np.sqrt((error**2).mean())),held_out_bias_c=float(error.mean()),
        held_out_max_abs_error_c=float(error.abs().max()),min_pairs_per_month_hour=min_pairs,
        limitation='Validation measures typical withheld days, not error at unobserved outage temperatures')
    audit=pd.DataFrame(dict(temperature_observed_c=primary,backup_temperature_c=backup,
        temperature_c=filled,weather_quality=np.where(missing,'backup_bias_adjusted','observed')),index=primary.index)
    audit.index.name='timestamp'
    return filled,audit,diagnostics


def regional_noaa_weather(primary_paths, backup_paths, *, station, backup_station, region, year=2024):
    index=pd.date_range(f'{year}-01-01',f'{year+1}-01-01',freq='h',inclusive='left',tz='America/Los_Angeles').tz_convert('UTC')
    primary,sources=observed_hourly(primary_paths,station,index)
    from .annual_weather import annual_noaa_weather
    backup_weather,backup_audit=annual_noaa_weather(backup_paths,station=backup_station,region=region,year=year)
    backup=backup_weather.frame.temperature_c
    backup_sources=backup_weather.diagnostics['sources']
    filled,audit,diagnostics=fill_from_backup(primary,backup,backup_observed=backup_audit.weather_quality.eq('observed'))
    audit['backup_weather_quality']=backup_audit.weather_quality
    audit.loc[primary.isna() & backup_audit.weather_quality.eq('interpolated'),'weather_quality']='backup_bias_adjusted_interpolated'
    diagnostics['backup_gap_policy']=backup_weather.diagnostics
    audit['source_station']=np.where(primary.isna(),backup_station,station)
    audit['timestamp_local']=index.tz_convert('America/Los_Angeles').astype(str)
    diagnostics.update(station=station,backup_station=backup_station,sources=sources,backup_sources=backup_sources,
        replaced_timestamps=index[primary.isna()].astype(str).tolist(),accepted_quality=['1','5'])
    return TemperatureWeather(filled.to_frame('temperature_c'),60,region,f'noaa-{station}-{year}',
        'NOAA primary observations; flagged bias-adjusted secondary-station gap replacements',diagnostics),audit
