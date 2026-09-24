from copy import deepcopy

import pytest

from src.local_web.contract import DEFAULT_SITE_REQUEST, validate_request
from src.local_web.site_profile import customer_class


def test_advanced_pv_battery_connection_accepts_only_modeled_ac_path():
    request = deepcopy(DEFAULT_SITE_REQUEST)
    request["pv_battery_connection"] = "ac_coupled"
    assert validate_request(request)["pv_battery_connection"] == "ac_coupled"
    request["pv_battery_connection"] = "dc_coupled"
    with pytest.raises(ValueError, match="Only AC-coupled"):
        validate_request(request)


@pytest.mark.parametrize('profile,expected', [
    ({'site_type': 'commercial', 'subtype': None}, 'commercial'),
    ({'site_type': 'residential', 'subtype': 'house'}, 'residential'),
    ({'site_type': 'residential', 'subtype': 'apartment_unit'}, 'residential'),
    ({'site_type': 'residential', 'subtype': 'common_areas'}, 'commercial'),
])
def test_site_account_class(profile, expected):
    assert customer_class(profile) == expected


@pytest.mark.parametrize('profile', [None, {}, {'site_type': 'residential', 'subtype': None},
    {'site_type': 'industrial', 'subtype': None}, {'site_type': 'commercial', 'subtype': 'house'}])
def test_invalid_site_profile(profile):
    with pytest.raises(ValueError):
        customer_class(profile)


@pytest.mark.parametrize('utility', ['pge', 'cleanpowersf', 'peninsula', 'svce', 'sjce', 'hetch_hetchy'])
def test_residential_never_falls_back_to_commercial_or_flat_price(utility):
    request = deepcopy(DEFAULT_SITE_REQUEST)
    request['site']['utility'] = utility
    request['site_profile'] = {'site_type': 'residential', 'subtype': 'house'}
    with pytest.raises(ValueError, match='Residential billing'):
        validate_request(request)


def test_legacy_saved_request_and_explicit_commercial_profile():
    request = deepcopy(DEFAULT_SITE_REQUEST)
    assert validate_request(request) == request
    request['site']['utility'] = 'pge'
    request['site_profile'] = {'site_type': 'commercial', 'subtype': None}
    assert validate_request(request) == request
    request['load'].update(mode='synthetic', archetype='residential')
    with pytest.raises(ValueError, match='archetype'):
        validate_request(request)


def municipal_request(subtype='house'):
    from test_municipal import account
    from test_municipal_dispatch import BATTERY
    return dict(schema_version=4, name='Residential profile test', resolution_id='a'*32,
        resolution={'status':'verified','delivery_utility':'amp'}, mode='actual_service',
        arrangement=dict(delivery_utility='amp',generation_provider='amp',tariff_id='amp_d1_2026_07_01',export_program='none'),
        account=account('D-1'),start_date='2026-08-01',end_date='2026-08-31',timezone='America/Los_Angeles',
        timestep_minutes=15,battery=deepcopy(BATTERY),load={'mode':'constant','base_kw':1},degradation_cost_per_kWh=.03,
        site_profile={'site_type':'residential','subtype':subtype})


@pytest.mark.parametrize('subtype', ['house', 'apartment_unit'])
def test_supported_residential_cycle_round_trip(subtype):
    request = municipal_request(subtype)
    assert validate_request(request) == request


def test_municipal_profile_cannot_conflict_with_account_or_schedule():
    request = municipal_request()
    request['account']['customer_class'] = 'commercial'
    with pytest.raises(ValueError, match='customer class'):
        validate_request(request)
    request = municipal_request('common_areas')
    with pytest.raises(ValueError, match='customer class'):
        validate_request(request)
    request['account']['customer_class'] = 'commercial'
    with pytest.raises(ValueError):  # common areas cannot be billed on D-1
        validate_request(request)


def test_common_areas_do_not_use_whole_building_synthetic_load():
    request = deepcopy(DEFAULT_SITE_REQUEST)
    request['site']['utility'] = 'pge'
    request['site_profile'] = {'site_type':'residential','subtype':'common_areas'}
    assert validate_request(request) == request
    request['load'].update(mode='synthetic', archetype='multifamily')
    with pytest.raises(ValueError, match='archetype'):
        validate_request(request)
