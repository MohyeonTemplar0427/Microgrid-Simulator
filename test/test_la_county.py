"""Independent LA County bills and delivery/generation role regressions."""
import numpy as np
import pandas as pd
import pytest

from src.billing.socal import bill, eligibility
from src.billing.glendale import peak_mask
from src.dispatch.socal import optimize
from test_socal import account, frame, study_request


def gwp_account(**changes):
    a = account('gwp')
    a.update(gwp_individual_meter_confirmed=True, gwp_allocation_confirmed=True,
             gwp_historical_peak_floor_kw=30., gwp_demand_history_confirmed=True,
             storage_schedule_confirmed=True)
    a.update(changes)
    return a


def test_glendale_residential_independent_three_tier_bill():
    # July: 744 kWh; 310 kWh in each of the first two tiers, then 124.
    b = bill('gwp_l-1-a', frame(), gwp_account(local_tax_percent=7), '2026-07-01', '2026-07-31')
    base = 31*.75 + 310*.3071 + 310*.3806 + 124*.4547
    assert b['total'] == pytest.approx(base*1.0285*1.07 + 744*.0003)
    assert b['line_items']['public_benefits_charge'] == pytest.approx(base*.0285)
    assert b['line_items']['ECAC'] == 0


def test_glendale_transition_and_dst():
    f = frame('2025-10-31', '2025-11-02')
    b = bill('gwp_l-1-a', f, gwp_account(), '2025-10-31', '2025-11-02')
    # October 24 kWh; November 49 kWh (fall-back day has 25 hours).
    energy = 10*.2883+10*.3549+4*.4238 + 20*.2575+20*.3189+9*.3935
    assert b['total'] == pytest.approx((energy+3*.75)*1.0285+73*.0003)
    assert len(b['rate_versions']) == 2


def test_glendale_low_season_tou_and_thanksgiving_friday():
    idx = pd.DatetimeIndex(['2025-11-26 11:45', '2025-11-26 12:00', '2025-11-26 20:45',
                            '2025-11-26 21:00', '2025-11-27 16:00', '2025-11-28 16:00'], tz='America/Los_Angeles')
    assert peak_mask(idx).tolist() == [False, True, True, False, False, False]
    b = bill('gwp_l-1-b', frame('2025-11-26','2025-11-28'), gwp_account(), '2025-11-26','2025-11-28')
    assert b['total'] == pytest.approx((63*.1901+9*.5700+3*.75)*1.0285+72*.0003)


def test_glendale_demand_floor_and_no_interval_summing():
    a = gwp_account(customer_class='commercial')
    b = bill('gwp_ld-2-a', frame(kw=20), a, '2026-07-01','2026-07-31')
    assert b['total'] == pytest.approx((31*1.6+14880*.1645+30*31*1.1)*1.0285+14880*.0003)
    a.pop('gwp_historical_peak_floor_kw')
    with pytest.raises(ValueError, match='historical'):
        bill('gwp_ld-2-a', frame(kw=20), a, '2026-07-01','2026-07-31')


@pytest.mark.parametrize('change', [dict(generation_provider='cpa'), dict(solar_program='nem'),
    dict(gwp_individual_meter_confirmed=False), dict(gwp_allocation_confirmed=False)])
def test_glendale_missing_or_unsupported_account(change):
    with pytest.raises(ValueError):
        eligibility('gwp_l-1-a', gwp_account(**change), '2026-07-01','2026-07-31')


def test_glendale_coverage_and_resolution_rejection():
    with pytest.raises(ValueError, match='coverage'):
        eligibility('gwp_l-1-a', gwp_account(), '2024-12-01', '2024-12-31')
    with pytest.raises(ValueError, match='15-minute'):
        bill('gwp_l-1-a', frame().iloc[::4], gwp_account(), '2026-07-01', '2026-07-31')


@pytest.mark.parametrize('key', ['gwp_l-1-a','gwp_l-1-b','gwp_l-2-a','gwp_l-2-b','gwp_ld-2-a'])
def test_glendale_dispatch_matches_final_bill(key):
    a = gwp_account(customer_class='residential' if key.startswith('gwp_l-1') else 'commercial')
    f = frame('2026-07-06','2026-07-07')
    f.loc[f.timestamp.dt.hour.between(16,19), ['native_load_kw','grid_import_kw']] = 3.
    r = optimize(key, f, a, '2026-07-06','2026-07-07',
        dict(capacity_kWh=10,energy_kWh=5,SOC_min=.2,SOC_max=.8,max_charge_kw=3,max_discharge_kw=3,
             charge_efficiency=.95,discharge_efficiency=.95), .01)
    assert r['objective_gap'] < .02
    assert r['bill']['total'] + r['degradation_cost'] <= r['baseline_bill']['total']+.02
    d = r['dispatch']
    assert np.allclose(d.grid_import_kw+d.battery_discharge_kw, d.native_load_kw+d.battery_charge_kw, atol=1e-5)


@pytest.mark.parametrize('agency,utility', [(37452,'gwp'),(71750,'pwp'),(19201,'bwp'),(11991,'alw'),(93642,'vpu'),(32555,'ipu')])
def test_la_territory_interiors_and_boundaries(agency, utility):
    from src.local_web.utility_resolution import resolve_service
    from test_municipal import feature, geo_get
    r = resolve_service(dict(latitude=34., longitude=-118.), get=geo_get([feature(agency)]))
    assert r['status']=='approximate' and r['delivery_utility']==utility
    r = resolve_service(dict(latitude=34., longitude=-118.), get=geo_get([feature(agency)], [feature(agency),feature(86250,oid=99)]))
    assert r['status']=='ambiguous' and r['delivery_utility'] is None


def test_cerritos_is_generation_not_delivery_and_no_sce_by_exclusion():
    from src.local_web.utility_resolution import resolve_service
    from test_municipal import feature, geo_get
    ceu = feature(None, 'City of Cerritos', oid=34)
    r = resolve_service(dict(latitude=33.86,longitude=-118.08), get=geo_get([ceu]))
    assert r['status']=='unsupported' and r['delivery_utility'] is None
    assert r['generation_candidates'][0]['service_id']=='ceu'
    r = resolve_service(dict(latitude=33.86,longitude=-118.08), get=geo_get([ceu,feature(86250,oid=8)]))
    assert r['status']=='approximate' and r['delivery_utility']=='sce'
    assert r['territory_role_corrections'][0]['resolved_role']=='generation'


@pytest.mark.parametrize('oid,identity', [(11,'cpa'),(14,'epic'),(16,'lancaster'),(20,'pico_prime'),(22,'pomona')])
def test_la_generation_identity_and_version_without_enrollment(oid, identity):
    from src.local_web.utility_resolution import resolve_service, CCA_IDENTITIES
    from test_municipal import feature, geo_get, Response
    base = geo_get([feature(86250,oid=8)])
    name = next(iter(CCA_IDENTITIES[oid][1]))
    def fetch(url, params, timeout):
        if 'Other' in url and url.endswith('/query'):
            return Response({'features':[{'attributes':{'OBJECTID':oid,'Utility':name,'Type':'CCA'}}]})
        return base(url, params, timeout)
    r = resolve_service(dict(latitude=34.,longitude=-118.),get=fetch)
    assert r['delivery_utility']=='sce' and r['status']=='approximate'
    assert r['generation_candidates'][0]['service_id']==identity
    assert r['sources'][1]['data_last_edit_epoch_ms']==1788541732680
    assert r['manual_confirmation'] is None


def test_la_coverage_distinguishes_research_from_executable_billing():
    from src.local_web.socal_study import capabilities
    c = capabilities()
    assert {p['id'] for p in c['la_county_coverage']['providers']} == {
        'gwp','pwp','bwp','alw','vpu','ipu','ceu','cpa','lancaster','pico_prime','pomona','epic'}
    assert not any(p['utility'] in {'pwp','bwp','alw','vpu','ipu','ceu'} for p in c['plans'])


def test_glendale_independent_rider_percentage_is_used(monkeypatch):
    from src.billing import glendale
    # Synthetic mutation exercises the independent rider record, not a new tariff.
    begin, end, version, rates = glendale.ADJUSTMENT_VERSIONS[0]
    monkeypatch.setattr(glendale, 'ADJUSTMENT_VERSIONS', ((begin,end,version,{**rates,'public_benefits_fraction':.03}),))
    b = bill('gwp_l-1-a',frame(),gwp_account(),'2026-07-01','2026-07-31')
    assert b['line_items']['public_benefits_charge']==pytest.approx((31*.75+310*.3071+310*.3806+124*.4547)*.03)


def test_glendale_rejects_future_and_missing_rider_coverage(monkeypatch):
    from src.billing import glendale
    with pytest.raises(ValueError,match='coverage'):
        eligibility('gwp_l-1-a',gwp_account(),'2026-09-19','2026-09-20')
    monkeypatch.setattr(glendale,'ADJUSTMENT_VERSIONS',())
    with pytest.raises(ValueError,match='coverage'):
        eligibility('gwp_l-1-a',gwp_account(),'2026-07-01','2026-07-31')


def test_glendale_direct_dispatch_does_not_accept_unmodeled_pv():
    f=frame();f['pv_available_kw']=1.
    with pytest.raises(ValueError,match='does not support PV'):
        optimize('gwp_l-1-a',f,gwp_account(),'2026-07-01','2026-07-31',None,0.)
