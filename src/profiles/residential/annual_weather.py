"""Complete local-calendar NOAA weather with explicit bounded gap handling."""
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd
from .core import ResidentialError
from .weather_model import TemperatureWeather


def annual_noaa_weather(paths, *, station, region, year, timezone='America/Los_Angeles', max_gap_hours=1):
    """Return weather and per-hour audit; never extrapolate or fill long gaps.

    Hourly values are means of accepted reports (TMP QC 1/5), after averaging
    duplicate timestamps. Only interior runs up to max_gap_hours are linearly
    interpolated in elapsed time. Both local-year boundaries require data.
    """
    if isinstance(max_gap_hours, bool) or not isinstance(max_gap_hours, int) or not 0 <= max_gap_hours <= 3:
        raise ResidentialError('max_gap_hours must be an integer from 0 to 3')
    start = pd.Timestamp(f'{year}-01-01', tz=timezone).tz_convert('UTC')
    end = pd.Timestamp(f'{year+1}-01-01', tz=timezone).tz_convert('UTC')
    index = pd.date_range(start, end, freq='h', inclusive='left')
    observations, sources = [], []
    for path in paths:
        raw = pd.read_csv(path, dtype=str)
        if not {'STATION','DATE','TMP'} <= set(raw):
            raise ResidentialError('NOAA input needs STATION, DATE and TMP')
        raw = raw.loc[raw.STATION == str(station)]
        if raw.empty:
            continue
        timestamps = pd.to_datetime(raw.DATE, utc=True, errors='raise')
        parts = raw.TMP.str.split(',', expand=True)
        if parts.shape[1] != 2:
            raise ResidentialError('NOAA TMP must contain value,quality')
        temperature = pd.to_numeric(parts[0], errors='coerce')/10
        good = parts[1].isin(['1','5']) & temperature.between(-95,65)
        observations.append(pd.Series(temperature[good].to_numpy(), index=pd.DatetimeIndex(timestamps[good])))
        sources.append(dict(path=str(path), sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest()))
    if not observations or all(s.empty for s in observations):
        raise ResidentialError('No accepted observations for selected station')
    hourly = pd.concat(observations).groupby(level=0).mean().resample('h').mean().reindex(index)
    missing = hourly.isna()
    if missing.iloc[0] or missing.iloc[-1]:
        raise ResidentialError('Missing year-boundary weather; supply adjoining UTC-year observations')
    groups = missing.ne(missing.shift()).cumsum()
    lengths = missing.groupby(groups).transform('size')
    if (missing & (lengths > max_gap_hours)).any():
        raise ResidentialError('Weather gap exceeds explicit interpolation limit; use a checked secondary source')
    filled = hourly.interpolate(method='time', limit_area='inside')
    if not np.isfinite(filled).all():
        raise ResidentialError('Unresolved weather gaps')
    audit = pd.DataFrame({'temperature_observed_c': hourly, 'temperature_c': filled,
        'weather_quality': np.where(missing, 'interpolated', 'observed'),
        'station': str(station), 'timestamp_local': index.tz_convert(timezone).astype(str)}, index=index)
    audit.index.name = 'timestamp'
    diagnostics = dict(station=str(station), sources=sources, accepted_quality=['1','5'],
        interpolated_hours=int(missing.sum()), interpolation_limit_hours=max_gap_hours,
        interpolated_timestamps=index[missing].astype(str).tolist(),
        gap_policy='Linear elapsed-time interpolation for bounded interior gaps only; no edge filling',
        calendar_timezone=timezone, year=year,
        aggregation='Mean of accepted reports per UTC hour; not a time-weighted temperature integral')
    weather = TemperatureWeather(filled.to_frame('temperature_c'),60,region,f'noaa-{station}-{year}',
        'NOAA Global Hourly; explicitly flagged short-gap interpolation',diagnostics)
    return weather,audit
