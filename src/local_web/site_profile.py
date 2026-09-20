"""Site classification shared by browser capabilities and request validation.

This is supported-model scope, not a determination of account eligibility.
Old saved requests without a profile retain their original explicit contract.
"""
SITE_OPTIONS = {
    'commercial': {'label': 'Commercial', 'subtypes': [],
                   'customer_class': 'commercial'},
    'residential': {'label': 'Residential', 'subtypes': [
        {'id': 'house', 'label': 'House', 'customer_class': 'residential'},
        {'id': 'apartment_unit', 'label': 'Apartment / individual unit', 'customer_class': 'residential'},
        {'id': 'common_areas', 'label': 'Multifamily common areas · separate account', 'customer_class': 'commercial'},
    ]},
}
SERVICE_CLASSES = {
    key: ['commercial'] for key in
    ('pge', 'cleanpowersf', 'hetch_hetchy', 'peninsula', 'svce', 'sjce')
}
SERVICE_CLASSES.update(amp=['commercial', 'residential'], svp=['commercial', 'residential'], ladwp=['commercial', 'residential'], sce=['commercial', 'residential'])
SERVICE_CLASSES['gwp'] = ['commercial', 'residential']


def customer_class(profile):
    if not isinstance(profile, dict) or set(profile) != {'site_type', 'subtype'}:
        raise ValueError('Supply site_type and subtype in the site profile.')
    kind, subtype = profile['site_type'], profile['subtype']
    if kind == 'commercial' and subtype is None:
        return 'commercial'
    if kind == 'residential':
        for option in SITE_OPTIONS['residential']['subtypes']:
            if subtype == option['id']:
                return option['customer_class']
    raise ValueError('Choose Commercial or Residential with a supported residential subtype.')


def validate_profile_request(request):
    if 'site_profile' not in request:
        return  # Backward compatibility; never invent a subtype for saved inputs.
    classification = customer_class(request['site_profile'])
    if request['schema_version'] == 4:
        if not isinstance(request['account'], dict) or request['account'].get('customer_class') != classification:
            raise ValueError('Account customer class must match the Step 2 site profile.')
        service = request['arrangement']['delivery_utility']
    else:
        from ..billing.services import SERVICES
        selection = request['site']['utility']
        service = next((s['id'] for s in SERVICES if selection == s['id'] or selection in s['aliases']), selection)
        # Residential tier/minimum-bill dispatch is not connected to this path.
        if classification == 'residential':
            raise ValueError('Residential billing and dispatch are currently supported only through AMP/SVP municipal studies; no commercial or flat-price fallback is applied.')
        if request['load']['mode'] == 'synthetic':
            allowed = () if request['site_profile']['subtype'] == 'common_areas' else ('office', 'retail', 'school', 'industrial')
            if request['load']['archetype'] not in allowed:
                raise ValueError('Load archetype does not match the Step 2 site profile.')
    if classification not in SERVICE_CLASSES.get(service, []):
        raise ValueError('Billing is not supported for this service and site type.')
