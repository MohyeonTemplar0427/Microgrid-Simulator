"""Versioned CEC electricity-delivery lookup, distinct from geocoding and CCA enrollment."""
from datetime import date, datetime, timezone
import hashlib
import json

import requests

from .contract import number
from .utilities import LAYERS

# Stable agency identifiers from the CEC layer, not city/county text matching.
AGENCIES = {71021:'pge',10500:'amp',80560:'svp',80522:'hetch_hetchy',
            58970:'ladwp',86250:'sce'}
NAMES = {'pge':'Pacific Gas & Electric Company','amp':'Alameda Municipal Power','svp':'Silicon Valley Power','hetch_hetchy':'Hetch Hetchy Power',
         'ladwp':'Los Angeles Department of Water & Power','sce':'Southern California Edison'}


# CCA IDs are checked against the official identity, not trusted on their own.
CCA_IDENTITIES = {
    12: ('cleanpowersf', {'CleanPowerSF (CPSF)'}),
    19: ('peninsula', {'Peninsula Clean Energy', 'WestLight Energy'}),
    27: ('sjce', {'San Jose Clean Energy (SJCE)'}),
    29: ('svce', {'Silicon Valley Clean Energy (SVCE)'}),
}


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def resolve_service(request, *, get=None):
    if not isinstance(request,dict) or set(request)-{'latitude','longitude','manual_confirmation'}:
        raise ValueError('Use coordinates and optional manual_confirmation; geocode addresses separately.')
    for field,bounds in [('latitude',(-90,90)),('longitude',(-180,180))]:
        if field not in request:
            raise ValueError('Coordinates are required; ZIP/city/county alone cannot resolve electric service.')
        number(request[field],field,*bounds)
    coordinates = {k:request[k] for k in ('latitude','longitude')}
    result = dict(interface_version=1,coordinates=coordinates,status='unsupported',delivery_utility=None,
                  delivery_candidates=[],generation_candidates=[],manual_confirmation=None,
                  retrieved_at=datetime.now(timezone.utc).isoformat(),sources=[],boundary_buffer_meters=100,
                  explanation='No supported electricity territory verified. No PG&E fallback is applied.')
    fetch = get or requests.get
    def query(url,params):
        r=fetch(url,params={'f':'json',**params},timeout=15); r.raise_for_status(); data=r.json()
        if not isinstance(data,dict) or 'error' in data or data.get('exceededTransferLimit'):
            raise ValueError('Incomplete CEC response.')
        return data
    params = dict(geometry=f"{request['longitude']},{request['latitude']}",geometryType='esriGeometryPoint',
                  inSR=4326,spatialRel='esriSpatialRelIntersects',returnGeometry='false',outFields='OBJECTID,AgencyNum,Utility,Acronym,Type',resultRecordCount=100)
    try:
        url=LAYERS['distribution']
        meta=query(url,{})
        edited=meta['editingInfo']['dataLastEditDate']
        if not isinstance(edited,(int,float)) or not meta.get('serviceItemId'):
            raise ValueError('Missing boundary version metadata.')
        exact=query(url+'/query',params)
        nearby=query(url+'/query',{**params,'distance':100,'units':'esriSRUnit_Meter'})
        def records(data):
            entries=[]
            for feature in data['features']:
                a=feature['attributes']
                if not isinstance(a.get('Utility'),str) or not isinstance(a.get('OBJECTID'),int):
                    raise ValueError('Invalid utility boundary record.')
                utility=AGENCIES.get(a.get('AgencyNum'))
                entries.append(dict(utility_id=utility or f"cec:distribution:{a['OBJECTID']}",
                                    name=NAMES.get(utility,a['Utility']),agency_number=a.get('AgencyNum'),object_id=a['OBJECTID']))
            return entries
        hits, near = records(exact),records(nearby)
        result['sources'].append(dict(url=url,item_id=meta['serviceItemId'],data_last_edit_epoch_ms=edited,
                                      response_sha256=_digest({'exact':exact,'nearby':nearby}),precision='approximate CEC service areas'))
        exact_ids={r['utility_id'] for r in hits}
        candidates={r['utility_id']:r for r in hits+near}
        result['delivery_candidates']=[{**r,'match':'point' if key in exact_ids else 'nearby_boundary'} for key,r in candidates.items()]
        ids={r['utility_id'] for r in hits}; nearby_ids={r['utility_id'] for r in near}
        if len(ids)>1 or len(nearby_ids)>1 or nearby_ids!=ids:
            result.update(status='ambiguous',explanation='Overlapping territories or a boundary within the 100 m screening buffer. Confirm the electricity provider using a bill or the utility.')
        elif len(ids)==1:
            utility=next(iter(ids))
            if utility in NAMES:
                result.update(status='approximate',delivery_utility=utility,
                              explanation='Interior CEC polygon match, not address-level account verification. Confirm actual electricity service and generation enrollment.')
    except (requests.RequestException,ValueError,KeyError,TypeError):
        result.update(status='unsupported',delivery_utility=None,explanation='Authoritative geographic data unavailable or incomplete. Manual bill/utility confirmation is available; no inferred provider.')
    try:
        other=query(LAYERS['other']+'/query',params)
        generation=[]
        for feature in other['features']:
            a=feature['attributes']
            if a.get('Type')!='CCA':
                continue  # WAPA, tribal and cooperative polygons are not CCAs.
            if type(a.get('OBJECTID')) is not int or not isinstance(a.get('Utility'),str) or not a['Utility'].strip():
                raise ValueError('Invalid CCA boundary record.')
            identity=CCA_IDENTITIES.get(a['OBJECTID'])
            service_id=identity[0] if identity and a['Utility'] in identity[1] else None
            generation.append(dict(id=f"cec:other:{a['OBJECTID']}",name=a['Utility'],service_id=service_id,type='CCA'))
        result['generation_candidates']=generation
        result['sources'].append(dict(url=LAYERS['other'],response_sha256=_digest(other),role='generation suggestions; not enrollment'))
    except (requests.RequestException,ValueError,KeyError,TypeError):
        result['generation_lookup_limitation']='Generation territory data unavailable; confirm account provider.'
    manual=request.get('manual_confirmation')
    if manual is not None:
        fields={'delivery_utility','evidence_type','reference','confirmed_on'}
        if not isinstance(manual,dict) or set(manual)!=fields or manual['delivery_utility'] not in NAMES or manual['evidence_type'] not in ('electricity_bill','utility_confirmation'):
            raise ValueError('Manual confirmation requires a supported delivery_utility, electricity_bill/utility_confirmation evidence_type, reference and confirmed_on.')
        if not isinstance(manual['reference'],str) or not manual['reference'].strip() or len(manual['reference'])>500:
            raise ValueError('Supply a short confirmation reference without account numbers.')
        confirmed=date.fromisoformat(manual['confirmed_on'])
        if confirmed>date.today():
            raise ValueError('Confirmation date cannot be in the future.')
        result.update(mapped_status=result['status'],mapped_delivery_utility=result['delivery_utility'],status='verified',
                      delivery_utility=manual['delivery_utility'],manual_confirmation=dict(manual),
                      explanation='User-confirmed electricity service from the stated bill/utility reference. This is an attestation, not independent utility authentication; original map evidence is preserved.')
    result['provenance_sha256']=_digest(result)
    return result
