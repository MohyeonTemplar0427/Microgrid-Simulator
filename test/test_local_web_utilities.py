from copy import deepcopy
import requests
import pytest
from src.local_web.utilities import lookup_utilities
from src.local_web.contract import DEFAULT_SITE_REQUEST, validate_request


def response(features):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"features": [{"attributes": x} for x in features]}
    return Response()


def test_overlapping_distribution_and_cca_are_choices_not_account_assignment():
    def get(url, params, timeout):
        assert params['geometry'] == '-122.4194,37.7749'
        assert params['spatialRel'] == 'esriSpatialRelIntersects'
        assert params['inSR'] == 4326 and timeout == 10
        return response([dict(OBJECTID=4, Utility='Pacific Gas & Electric Company', Acronym='PG&E', Type='IOU')]
                        if 'IOU_POU' in url else [dict(OBJECTID=12, Utility='CleanPowerSF', Acronym='CPSF', Type='CCA')])
    result = lookup_utilities(dict(latitude=37.7749, longitude=-122.4194), get=get)
    assert result['status'] == 'matched'
    assert {x['id'] for x in result['candidates']} == {'pge', 'cec:other:12'}
    assert 'selected' not in result
    assert all(x['source_url'].startswith('https://services3.arcgis.com/') for x in result['candidates'])


def test_outside_coverage_never_fabricates_a_utility():
    def get(*a, **kw): pytest.fail('Outside coverage must not call provider')
    result = lookup_utilities(dict(latitude=40, longitude=-74), get=get)
    assert result['status'] == 'outside_coverage' and result['candidates'] == []


def test_partial_lookup_is_explicit():
    def get(url, **kw):
        if 'Other' in url: raise requests.Timeout()
        return response([dict(OBJECTID=1, Utility='Municipal utility', Acronym='MU', Type='POU')])
    result = lookup_utilities(dict(latitude=38, longitude=-121), get=get)
    assert result['status'] == 'partial'
    assert result['candidates'][0]['id'] == 'cec:distribution:1'
    assert not result['candidates'][0]['bundled_tariff_supported']


def test_cca_study_saved_without_applying_pge_tariff():
    study = deepcopy(DEFAULT_SITE_REQUEST)
    study['site']['utility'] = 'cec:other:12'
    validate_request(study)
    study['tariff_id'] = 'pge_b1'
    with pytest.raises(ValueError, match='bundled'):
        validate_request(study)


@pytest.mark.parametrize('coordinates',[{'latitude':True,'longitude':-122},{'latitude':38,'longitude':float('nan')},{'latitude':91,'longitude':-122}])
def test_invalid_coordinates(coordinates):
    with pytest.raises(ValueError): lookup_utilities(coordinates)
