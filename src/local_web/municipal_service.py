"""Additive v1 municipal replay interface; legacy study schemas stay unchanged."""
import pandas as pd

from ..billing.municipal import RATES, UNSUPPORTED, bill_cycle, eligibility
from ..billing.services import canonical_service, validate_service_pairing
from .utility_resolution import resolve_service


def capabilities():
    return {'interface_version':1,'optimized_studies':True,'study_schema_version':4,'tariffs':[r.metadata() for r in RATES.values()],
            'unsupported':UNSUPPORTED,'modes':['actual_service','alternative_location'],
            'operations':['utility-resolution','municipal-eligibility','municipal-bill'],
            'legacy_study_schemas':[1,2,3],
            'note':'Municipal bill replay and import-only storage optimization. Resolve location first and preserve its resolution_id.'}


def validate_arrangement(arrangement, resolution, *, comparison=False):
    if not isinstance(arrangement,dict) or set(arrangement)!={'delivery_utility','generation_provider','tariff_id','export_program'}:
        raise ValueError('Specify separate delivery_utility, generation_provider, tariff_id and export_program.')
    delivery=arrangement['delivery_utility']; generation=arrangement['generation_provider']
    if delivery not in ('amp','svp','pge'):
        raise ValueError('Unsupported delivery utility.')
    if not comparison:
        if resolution.get('status')!='verified' or resolution.get('delivery_utility')!=delivery:
            raise ValueError('Actual service requires matching bill/utility-confirmed delivery. Use alternative_location for hypothetical comparisons.')
    if arrangement['export_program']!='none':
        raise ValueError('Export/net-metering settlement is not implemented.')
    if delivery in ('amp','svp'):
        if generation!=delivery or arrangement['tariff_id'] not in RATES or RATES[arrangement['tariff_id']].utility!=delivery:
            raise ValueError('Municipal service must use its own generation and tariff; no PG&E delivery or CCA add-on.')
    else:
        service=canonical_service(generation)
        if service is None or service=='hetch_hetchy':
            raise ValueError('Unsupported PG&E generation arrangement; do not substitute bundled generation.')
        validate_service_pairing(arrangement['tariff_id'],generation)


def execute(kind, request):
    if kind=='utility-resolution':
        return resolve_service(request)
    if not isinstance(request,dict) or request.get('interface_version')!=1:
        raise ValueError('Use municipal interface_version 1.')
    allowed={'interface_version','mode','resolution','resolution_id','arrangement','account','start','end'}
    if kind=='municipal-bill':
        allowed|={'dispatch'}
    if set(request)-allowed:
        raise ValueError('Unknown municipal request fields.')
    for field in ('mode','resolution','arrangement','account','start','end'):
        if field not in request:
            raise ValueError(f'Missing {field}.')
    mode=request['mode']
    if mode not in ('actual_service','alternative_location'):
        raise ValueError('Choose actual_service or alternative_location mode.')
    validate_arrangement(request['arrangement'],request['resolution'],comparison=mode=='alternative_location')
    utility=request['arrangement']['delivery_utility']
    if utility=='pge':
        raise ValueError('PG&E/CCA billing remains in the existing versioned study API; this endpoint bills municipal service only.')
    items=eligibility(utility,request['account'],request['start'],request['end'])
    result={'interface_version':1,'mode':mode,'label':'Actual confirmed service' if mode=='actual_service' else 'Hypothetical alternative-location scenario; not service available at the original site',
            'resolution':request['resolution'],'arrangement':request['arrangement'],
            'eligibility':items,'unsupported':UNSUPPORTED}
    if kind=='municipal-eligibility':
        return result
    if kind!='municipal-bill':
        raise ValueError('Unknown municipal operation.')
    if 'dispatch' not in request or not isinstance(request['dispatch'],list) or len(request['dispatch'])>110000:
        raise ValueError('Supply at most 110000 dispatch intervals.')
    result['bill']=bill_cycle(request['arrangement']['tariff_id'],pd.DataFrame(request['dispatch']),
        cycle_start=request['start']+'T00:00:00'+_offset(request['start']),
        cycle_end=request['end']+'T00:00:00'+_offset(request['end']),account=request['account'])
    return result


def _offset(day):
    return pd.Timestamp(day,tz='America/Los_Angeles').strftime('%z')[:3]+':'+pd.Timestamp(day,tz='America/Los_Angeles').strftime('%z')[3:]
