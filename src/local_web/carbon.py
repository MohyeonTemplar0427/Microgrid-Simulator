"""Regional carbon signals for browser studies, without silent fallback."""
from datetime import date
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

REGIONAL_NOTE = ('Electricity Maps CAISO regional grid-average carbon intensity (US-CAL-CISO). '
    'This is a wider-area proxy, not a site measurement or the utility/CCA product mix. '
    'Local supply, imports and provider estimates can make actual site emissions differ. '
    'Average carbon intensity does not represent marginal emissions avoided by dispatch.')


# Explicit study-area routing, NOT a balancing-authority/service boundary.
# Other areas need their own supported mapping rather than a CAISO fallback.
REGION_MAPPINGS = [dict(region='caiso_np15', zone='US-CAL-CISO', label='CAISO regional grid average', timezone='America/Los_Angeles',
    south=36.8, north=38.9, west=-123.6, east=-121.0,
    scope='Bay Area study-area proxy; not an exact balancing-authority boundary')]


def region_for_location(latitude, longitude):
    from .contract import number
    number(latitude, 'Latitude', -90, 90)
    number(longitude, 'Longitude', -180, 180)
    for mapping in REGION_MAPPINGS:
        if mapping['south'] <= latitude <= mapping['north'] and mapping['west'] <= longitude <= mapping['east']:
            return mapping
    raise ValueError('No supported carbon-region mapping for this location. Add verified regional coverage before running.')


def request_region(request):
    site = request.get('site') or request.get('resolution', {}).get('coordinates', {})
    return region_for_location(site.get('latitude'), site.get('longitude'))


def validate(request):
    spec = request.get('carbon')
    if spec is None:
        if 'carbon' in request:
            raise ValueError('Choose a carbon data source.')
        return
    if not isinstance(spec, dict):
        raise ValueError('Choose a carbon data source.')
    if spec.get('source') != 'electricity_maps' or set(spec) != {'source', 'region'}:
        raise ValueError('Browser studies require location-mapped historical carbon; constant assumptions are not supported.')
    mapping = request_region(request)
    if spec['region'] not in ('from_location', mapping['region']):
        raise ValueError('Carbon region does not match the configured location.')
    if request['timestep_minutes'] not in (15, 30, 60):
        raise ValueError('Historical carbon requires 15, 30 or 60-minute study intervals; 5-minute data is not inferred.')
    if request['timezone'] != 'America/Los_Angeles':
        raise ValueError('CAISO carbon studies require America/Los_Angeles.')


def values(request, directory, timestamps):
    """Fetch once per durable study; save native data and verify reused copies."""
    validate(request)
    target = pd.DatetimeIndex(timestamps).tz_convert('UTC')
    spec = request.get('carbon', {'source':'assumed', 'value':request.get('carbon_intensity_g_per_kWh', 0)})
    if spec['source'] == 'assumed':
        return np.full(len(target), spec['value']), {'source':'assumed', 'value':spec['value'],
            'warning':'Grid carbon intensity is an explicit constant study assumption, not historical regional data.'}
    from ..signal_pipeline.region_config import get_region_config
    from ..signal_pipeline.electricity_maps_data import get_multi_day_carbon_data
    from .worker import write_json
    mapping = request_region(request)
    zone = get_region_config(mapping['region']).carbon_zone
    directory = Path(directory)
    path, meta_path = directory/'carbon.csv', directory/'carbon.json'
    identity = dict(zone=zone, start_date=request['start_date'], end_date=request['end_date'], timezone=request['timezone'])
    if path.exists() and meta_path.exists():
        metadata = json.loads(meta_path.read_text())
        if metadata['request'] != identity or hashlib.sha256(path.read_bytes()).hexdigest() != metadata['sha256']:
            raise ValueError('Saved carbon data does not match this study or its checksum.')
        frame = pd.read_csv(path)
    else:
        key = os.getenv('ELECTRICITY_MAPS_API_KEY')
        if not key:
            raise ValueError('Electricity Maps credentials are missing. Configure ELECTRICITY_MAPS_API_KEY. Historical carbon data is required; no constant fallback is available.')
        days = (date.fromisoformat(request['end_date']) - date.fromisoformat(request['start_date'])).days + 1
        write_json(directory/'progress.json', {'message':'Retrieving historical Electricity Maps carbon intensity for CAISO; no assumed fallback'})
        frame = get_multi_day_carbon_data(key, zone, request['start_date'], days, timezone=request['timezone'])
        metadata = None
    stamps = pd.DatetimeIndex(pd.to_datetime(frame.timestamp, utc=True))
    start = pd.Timestamp(request['start_date'], tz=request['timezone'])
    end = pd.Timestamp(request['end_date'], tz=request['timezone']) + pd.DateOffset(days=1)
    expected = pd.date_range(start, end, freq='15min', inclusive='left').tz_convert('UTC')
    signal = pd.Series(pd.to_numeric(frame['gCO2/kWh'], errors='raise').to_numpy(), index=stamps)
    if not stamps.equals(expected) or not np.isfinite(signal.to_numpy()).all() or (signal < 0).any():
        raise ValueError('Historical carbon must cover every native 15-minute interval exactly once, with finite nonnegative values. No gaps are filled.')
    if metadata is None:
        frame.to_csv(path, index=False)
        metadata = dict(source='electricity_maps', request=identity, native_interval_minutes=15,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(), warning=REGIONAL_NOTE)
        write_json(meta_path, metadata)
    aligned = signal.resample(f"{request['timestep_minutes']}min").mean()
    if not aligned.index.equals(target):
        raise ValueError('Carbon timestamps do not match the simulation horizon.')
    return aligned.to_numpy(), {**metadata, 'study_interval_minutes':request['timestep_minutes'], 'location_mapping':mapping,
        'aggregation':'Mean of complete native 15-minute intervals; no interpolation.'}
