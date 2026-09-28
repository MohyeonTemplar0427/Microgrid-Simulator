"""Independent SCE NBT23–NBT26 price, bill and dispatch checks."""
import numpy as np
import pandas as pd
import pytest

from src.billing.sce_nbt import export_prices, delivery_nbc_rates, generation_nbc_rates, GENERATION_NBC_PER_KWH
from src.billing.socal import bill
from src.dispatch.socal import optimize
from src.local_web.socal_study import validate
from test_socal import account, frame, study_request


def nbt_account(**overrides):
    a = account('sce')
    a.update(actual_generation_provider='bundled', solar_program='sce_nbt',
             interconnection_confirmed=True, nbt_vintage='2026',
             nbt_interconnection_request_date='2026-01-10', nbt_pto_date='2026-06-15',
             nbt_first_cycle_confirmed=True, nbt_bonus_status='eligible_non_equity',
             nbt_bonus_confirmed=True)
    a.update(overrides)
    return a


def historical_nbt_account(vintage, study_year, **overrides):
    a = nbt_account(nbt_vintage=str(vintage),
                    nbt_interconnection_request_date=f'{vintage}-05-01',
                    nbt_pto_date=f'{vintage}-06-01',
                    nbt_first_cycle_confirmed=False,
                    nbt_opening_balances_confirmed=True,
                    nbt_opening_delivery_eec=1.,
                    nbt_opening_generation_eec=2.,
                    nbt_opening_acc_plus=3.,
                    nbt_relevant_period_end=f'{study_year}-08-01')
    a.update(overrides)
    return a


def test_verified_hour_and_weekend_holiday_prices():
    index = pd.DatetimeIndex(['2026-07-03 10:00', '2026-07-04 10:00',
                              '2026-09-07 16:00', '2026-09-08 16:00'], tz='America/Los_Angeles')
    delivery, generation = export_prices(index)
    assert list(delivery) == pytest.approx([.00123, .00045, .08218, .00240])
    assert list(generation) == pytest.approx([.05764, .02609, .04220, .06778])


def test_nbt26_export_prices_follow_local_month_before_and_after_june():
    index = pd.DatetimeIndex(['2026-01-20 10:00', '2026-05-29 10:00',
                              '2026-05-31 10:00', '2026-06-01 10:00'],
                             tz='America/Los_Angeles')
    delivery, generation = export_prices(index)
    assert list(delivery) == pytest.approx([.00070, .00043, .00006, .00108])
    assert list(generation) == pytest.approx([.06298, .01295, .00421, .03273])
    assert list(delivery_nbc_rates(index)) == pytest.approx([.01121, .01121, .01121, .00765])


@pytest.mark.parametrize('vintage,service_year,delivery,generation', [
    (2023, 2025, .00826, .05349),
    (2024, 2026, .00882, .05753),
    (2025, 2025, .00115, .05262),
    (2025, 2026, .00123, .05764),
])
def test_older_vintage_workbook_prices(vintage, service_year, delivery, generation):
    day = 7 if service_year == 2025 else 6
    index = pd.DatetimeIndex([f'{service_year}-07-{day:02d} 10:00'], tz='America/Los_Angeles')
    d, g = export_prices(index, vintage)
    assert (d[0], g[0]) == pytest.approx((delivery, generation))


def test_2025_protected_components_change_on_filed_dates():
    index = pd.DatetimeIndex(['2025-02-28 10:00', '2025-03-01 10:00',
                              '2025-06-01 10:00', '2025-10-01 10:00',
                              '2025-11-15 10:00', '2026-01-01 10:00'],
                             tz='America/Los_Angeles')
    assert list(delivery_nbc_rates(index)) == pytest.approx(
        [.04171, .04140, .03989, .04159, .01654, .01121])
    assert list(generation_nbc_rates(index)) == pytest.approx([-.00058]*5+[.00014])


def test_first_cycle_separate_banks_and_protected_charges():
    f = frame('2026-07-06', '2026-07-06', kw=1.)
    a = nbt_account(billing_month_factor=1/30)
    f['grid_export_kw'] = 0.
    no_export = bill('sce_tou-d-prime', f, a, '2026-07-06', '2026-07-06')
    f.loc[f.timestamp.dt.hour == 10, 'grid_export_kw'] = 1.
    # Meter imports and exports must occupy different intervals.
    f.loc[f.timestamp.dt.hour == 10, 'grid_import_kw'] = 0.
    billed = bill('sce_tou-d-prime', f, a, '2026-07-06', '2026-07-06')
    ledger = billed['credit_ledger']
    assert billed['export_kWh'] == pytest.approx(1.)
    assert ledger['earned_delivery_eec'] == pytest.approx(.00123)
    assert ledger['earned_generation_eec'] == pytest.approx(.05764)
    assert ledger['earned_acc_plus'] == pytest.approx(.016)
    assert ledger['nonbypassable_import_charge'] == pytest.approx(23*(.00765+GENERATION_NBC_PER_KWH))
    assert billed['total'] == pytest.approx(sum(billed['line_items'].values()))
    assert billed['total'] < no_export['total']
    f['grid_import_kw'] = 0.
    f['grid_export_kw'] = 10.
    surplus = bill('sce_tou-d-prime', f, a, '2026-07-06', '2026-07-06')
    assert surplus['credit_ledger']['closing_delivery_eec'] > 0
    assert surplus['credit_ledger']['closing_generation_eec'] > 0
    assert surplus['line_items']['fixed_charge'] > 0
    assert surplus['amount_due'] == pytest.approx(0.)


@pytest.mark.parametrize('start,end,pto', [
    ('2026-05-31', '2026-06-01', '2026-05-15'),
    ('2026-07-06', '2026-07-07', '2026-06-15'),
])
def test_pv_storage_dispatch_bills_and_obeys_pv_only_charging(start, end, pto):
    f = frame(start, end, kw=1.)
    f['pv_available_kw'] = np.where((f.timestamp.dt.hour >= 10) & (f.timestamp.dt.hour < 15), 3., 0.)
    a = nbt_account(billing_month_factor=2/30, nbt_pto_date=pto)
    battery = dict(capacity_kWh=10, energy_kWh=5, SOC_min=.2, SOC_max=.8,
                   max_charge_kw=3, max_discharge_kw=3,
                   charge_efficiency=.95, discharge_efficiency=.95)
    result = optimize('sce_tou-d-prime', f, a, start, end, battery, .01)
    d = result['dispatch']
    assert result['objective_gap'] < .02
    assert result['bill']['total'] < result['solar_bill']['total']
    assert np.all(d.battery_charge_kw <= np.maximum(d.pv_available_kw - d.native_load_kw, 0) + 1e-5)
    assert np.all(d.battery_discharge_kw <= np.maximum(d.native_load_kw - d.pv_available_kw, 0) + 1e-5)
    assert np.allclose(d.grid_import_kw + d.pv_output_kw + d.battery_discharge_kw,
                       d.native_load_kw + d.battery_charge_kw + d.grid_export_kw, atol=1e-5)
    assert np.max(np.minimum(d.grid_import_kw, d.grid_export_kw)) < 1e-5


def test_cross_june_bill_uses_both_nonbypassable_import_rates():
    start, end = '2026-05-31', '2026-06-01'
    f = frame(start, end, kw=1.).assign(grid_export_kw=0.)
    a = nbt_account(nbt_pto_date='2026-05-15', billing_month_factor=2/30)
    result = bill('sce_tou-d-prime', f, a, start, end)
    ledger = result['credit_ledger']
    assert ledger['nonbypassable_delivery_charge'] == pytest.approx(24*(.01121+.00765))
    assert ledger['nonbypassable_generation_charge'] == pytest.approx(48*GENERATION_NBC_PER_KWH)
    assert ledger['nonbypassable_import_charge'] == pytest.approx(
        ledger['nonbypassable_delivery_charge'] + ledger['nonbypassable_generation_charge'])
    assert len(result['rate_versions']) == 2
    assert result['total'] == pytest.approx(sum(result['line_items'].values()))


@pytest.mark.parametrize('day,expected_delivery,expected_generation', [
    ('2026-01-20', .00070, .06298),
    ('2026-03-08', .00008, .00457),
])
def test_early_2026_cycle_credits_exports_with_its_own_hourly_prices(
        day, expected_delivery, expected_generation):
    f = frame(day, day, kw=1.).assign(grid_export_kw=0.)
    at_ten = f.timestamp.dt.hour == 10
    f.loc[at_ten, 'grid_import_kw'] = 0.
    f.loc[at_ten, 'grid_export_kw'] = 1.
    a = nbt_account(nbt_pto_date='2026-01-15', billing_month_factor=1/30)
    result = bill('sce_tou-d-prime', f, a, day, day)
    ledger = result['credit_ledger']
    assert ledger['earned_delivery_eec'] == pytest.approx(expected_delivery)
    assert ledger['earned_generation_eec'] == pytest.approx(expected_generation)
    assert ledger['nonbypassable_delivery_charge'] == pytest.approx(
        (len(f)/4 - 1) * .01121)
    assert result['total'] == pytest.approx(sum(result['line_items'].values()))


@pytest.mark.parametrize('vintage,year,bonus_rate', [
    (2023, 2025, .040), (2024, 2025, .032), (2025, 2026, .024),
])
def test_older_vintage_cycle_applies_opening_banks_and_its_bonus(vintage, year, bonus_rate):
    day = f'{year}-07-06'
    f = frame(day, day, kw=1.).assign(grid_export_kw=0.)
    f.loc[f.timestamp.dt.hour == 10, 'grid_import_kw'] = 0.
    f.loc[f.timestamp.dt.hour == 10, 'grid_export_kw'] = 1.
    a = historical_nbt_account(vintage, year, billing_month_factor=1/30)
    result = bill('sce_tou-d-prime', f, a, day, day)
    ledger = result['credit_ledger']
    assert ledger['opening_delivery_eec'] == pytest.approx(1.)
    assert ledger['opening_generation_eec'] == pytest.approx(2.)
    assert ledger['opening_acc_plus'] == pytest.approx(3.)
    assert ledger['earned_acc_plus'] == pytest.approx(bonus_rate)
    assert ledger['nonbypassable_generation_charge'] == pytest.approx(
        23 * (-.00058 if year == 2025 else .00014))
    assert result['total'] == pytest.approx(sum(result['line_items'].values()))


@pytest.mark.parametrize('change,pattern', [
    ({'actual_generation_provider':'cca'}, 'CCA'),
    ({'nbt_vintage':'2025'}, 'vintage must match'),
    ({'nbt_first_cycle_confirmed':False}, 'opening delivery'),
    ({'nbt_bonus_confirmed':False}, 'ACC Plus'),
    ({'nbt_pto_date':'2026-07-10'}, 'before the study cycle'),
])
def test_unverified_account_combinations_reject(change, pattern):
    a = nbt_account(**change)
    with pytest.raises(ValueError, match=pattern):
        bill('sce_tou-d-prime', frame('2026-07-06', '2026-07-06').assign(grid_export_kw=0.),
             a, '2026-07-06', '2026-07-06')


def test_date_and_plan_bounds_and_web_validation():
    a = nbt_account()
    with pytest.raises(ValueError, match='TOU-D-PRIME'):
        bill('sce_tou-d-4-9', frame('2026-07-06', '2026-07-06').assign(grid_export_kw=0.),
             a, '2026-07-06', '2026-07-06')
    with pytest.raises(ValueError, match='vintage'):
        bill('sce_tou-d-prime', frame('2025-12-31', '2025-12-31').assign(grid_export_kw=0.),
             a, '2025-12-31', '2025-12-31')
    with pytest.raises(ValueError, match='before the study cycle'):
        bill('sce_tou-d-prime', frame('2026-05-31', '2026-05-31').assign(grid_export_kw=0.),
             a, '2026-05-31', '2026-05-31')
    r = study_request('sce')
    r['account'] = a
    r['solar'] = {'capacity_kw':5., 'tilt':20., 'azimuth':180.}
    assert validate(r) == r
    r['start_date'] = r['end_date'] = '2026-01-20'
    r['account']['nbt_pto_date'] = '2026-01-15'
    assert validate(r) == r
    r['account']['actual_generation_provider'] = 'cca'
    with pytest.raises(ValueError, match='CCA'):
        validate(r)


@pytest.mark.parametrize('start,end,older', [('2026-07-06','2026-07-07',False),
                                             ('2025-07-07','2025-07-08',True)])
def test_local_browser_worker_exports_credit_ledger(tmp_path,start,end,older):
    import json
    from src.local_web.socal_study import execute
    r = study_request('sce')
    r['start_date'], r['end_date'] = start,end
    r['account'] = (historical_nbt_account(2023,2025,billing_month_factor=2/30) if older
                    else nbt_account(billing_month_factor=2/30))
    r['solar'] = {'capacity_kw':5., 'tilt':20., 'azimuth':180.}
    (tmp_path / 'engine.json').write_text('{}')
    execute(tmp_path, r)
    result = json.loads((tmp_path / 'result.json').read_text())
    assert result['solar_program'] == 'sce_nbt'
    assert any(t['id'] == 'solar_credit_ledger' for t in result['tables'])
    ledger = pd.read_csv(tmp_path / 'solar_credit_ledger.csv')
    assert {'grid_only', 'pv_only'} <= set(ledger.scenario)
    assert ledger.loc[(ledger.scenario == 'pv_only') & (ledger.component == 'earned_generation_eec'), 'amount'].iloc[0] > 0
