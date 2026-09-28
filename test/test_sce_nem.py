"""Filed SCE NEM/NEM-ST retail netting and interval NBC differences."""
import numpy as np
import pytest

from src.billing.socal import bill
from src.dispatch.socal import optimize
from src.local_web.socal_study import validate
from test_socal import account, frame, study_request


def nem_account(version='nem2', **updates):
    vintage = 2016 if version == 'nem1' else 2022
    a = account('sce')
    a.update(actual_generation_provider='bundled', solar_program='sce_nem',
             interconnection_confirmed=True, sce_nem_version=version,
             sce_nem_request_date=f'{vintage}-05-01', sce_nem_pto_date=f'{vintage}-06-01',
             sce_nem_relevant_period_end='2026-08-01', sce_nem_legacy_confirmed=True,
             sce_nem_billing_option='monthly', sce_nem_opening_energy_credit=0.,
             sce_nem_credit_confirmed=True, billing_month_factor=1/30)
    a.update(updates)
    return a


@pytest.mark.parametrize('version', ['nem1', 'nem2'])
def test_legacy_nem_cycle_reconciles_and_values_export_at_retail(version):
    day = '2026-07-06'
    f = frame(day, day, kw=1.).assign(grid_export_kw=0.)
    f.loc[f.timestamp.dt.hour == 10, 'grid_import_kw'] = 0.
    f.loc[f.timestamp.dt.hour == 10, 'grid_export_kw'] = 1.
    a = nem_account(version)
    result = bill('sce_tou-d-prime', f, a, day, day)
    assert result['export_kWh'] == pytest.approx(1.)
    assert result['total'] == pytest.approx(sum(result['line_items'].values()))
    assert result['credit_ledger']['protected_import_nbc'] == pytest.approx(
        0 if version == 'nem1' else 23*(.00765+.00014))
    no_export = f.assign(grid_export_kw=0.)
    no_export.loc[no_export.timestamp.dt.hour == 10, 'grid_import_kw'] = 1.
    base = bill('sce_tou-d-prime', no_export, a, day, day)
    assert result['total'] < base['total']


def test_nem1_and_nem2_charge_different_protected_import_nbc():
    day = '2026-07-06'
    f = frame(day, day, kw=1.).assign(grid_export_kw=0.)
    f.loc[f.timestamp.dt.hour == 10, 'grid_import_kw'] = 0.
    f.loc[f.timestamp.dt.hour == 10, 'grid_export_kw'] = 1.
    one = bill('sce_tou-d-prime', f, nem_account('nem1'), day, day)
    two = bill('sce_tou-d-prime', f, nem_account('nem2'), day, day)
    assert two['total'] - one['total'] == pytest.approx(.00765+.00014)


@pytest.mark.parametrize('pto', ['2021-06-01', '2022-06-01'])
def test_2021_2022_nem2_accounts_use_2025_service_rates_not_nbt_vintage(pto):
    day = '2025-06-16'
    a = nem_account(sce_nem_request_date=pto[:4]+'-05-01', sce_nem_pto_date=pto,
                    sce_nem_relevant_period_end='2025-08-01')
    f = frame(day, day, kw=1.).assign(grid_export_kw=0.)
    result = bill('sce_tou-d-prime', f, a, day, day)
    assert result['credit_ledger']['protected_import_nbc'] == pytest.approx(
        24*(.03395+.00595-.00001-.00058))
    assert result['line_items']['fixed_or_minimum_charge'] == pytest.approx(.516)
    assert result['total'] == pytest.approx(sum(result['line_items'].values()))


def test_nem_opening_credit_offsets_energy_only_and_surplus_carries():
    day = '2026-07-06'
    f = frame(day, day, kw=1.).assign(grid_export_kw=0.)
    a = nem_account(sce_nem_opening_energy_credit=100.)
    result = bill('sce_tou-d-prime', f, a, day, day)
    assert result['line_items']['fixed_or_minimum_charge'] == pytest.approx(.794)
    assert result['line_items']['protected_import_nbc'] > 0
    assert result['credit_ledger']['applied_energy_credit'] > 0
    assert result['total'] >= result['line_items']['fixed_or_minimum_charge']
    f['grid_import_kw'] = 0.
    f['grid_export_kw'] = 2.
    surplus = bill('sce_tou-d-prime', f, a, day, day)
    assert surplus['credit_ledger']['earned_energy_credit'] > 0
    assert surplus['credit_ledger']['closing_energy_credit'] > 100


@pytest.mark.parametrize('start,end', [('2025-02-28', '2025-03-01'),
                                       ('2026-05-31', '2026-06-01')])
def test_legacy_nem_stays_in_one_filed_version_and_season(start, end):
    a = nem_account(sce_nem_relevant_period_end=start[:4]+'-08-01')
    f = frame(start, end, kw=1.).assign(grid_export_kw=0.)
    with pytest.raises(ValueError, match='rate version'):
        bill('sce_tou-d-prime', f, a, start, end)


def test_legacy_nem_web_validation_and_pv_allocation():
    r = study_request('sce')
    r['start_date'] = r['end_date'] = '2026-07-06'
    r['account'] = nem_account()
    r['solar'] = {'capacity_kw':5., 'tilt':20., 'azimuth':180.}
    assert validate(r) == r
    f = frame('2026-07-06', '2026-07-06', kw=1.)
    f['pv_available_kw'] = np.where((f.timestamp.dt.hour >= 10) & (f.timestamp.dt.hour < 15), 3., 0.)
    result = optimize('sce_tou-d-prime', f, r['account'], '2026-07-06', '2026-07-06', None, 0.)
    assert result['solar_bill']['total'] < result['baseline_bill']['total']
    assert result['dispatch'].grid_export_kw.sum() > 0


def test_legacy_nem_worker_exports_reconciled_credit_ledger(tmp_path):
    import json
    import pandas as pd
    from src.local_web.socal_study import execute
    r = study_request('sce')
    r['start_date'] = r['end_date'] = '2026-07-06'
    r['account'] = nem_account()
    r['solar'] = {'capacity_kw':5., 'tilt':20., 'azimuth':180.}
    (tmp_path / 'engine.json').write_text('{}')
    execute(tmp_path, r)
    result = json.loads((tmp_path / 'result.json').read_text())
    assert result['solar_program'] == 'sce_nem'
    assert any(t['id'] == 'solar_credit_ledger' for t in result['tables'])
    ledger = pd.read_csv(tmp_path / 'solar_credit_ledger.csv')
    assert {'grid_only', 'pv_only'} <= set(ledger.scenario)
    costs = pd.read_csv(tmp_path / 'costs.csv')
    comparison = pd.read_csv(tmp_path / 'comparison.csv')
    for row in comparison.itertuples():
        assert row.utility_bill == pytest.approx(costs.loc[costs.scenario == row.scenario, 'amount'].sum())


@pytest.mark.parametrize('change,pattern', [
    ({'sce_nem_version':'unknown'}, 'NEM 1.0'),
    ({'sce_nem_request_date':'2024-01-01'}, 'legacy deadline'),
    ({'sce_nem_credit_confirmed':False}, 'opening NEM'),
    ({'sce_nem_billing_option':'annual'}, 'monthly billing'),
    ({'sce_nem_request_date':'2017-05-01', 'sce_nem_pto_date':'2017-06-01'}, 'NEM-ST 2.0 PTO'),
    ({'actual_generation_provider':'cca'}, 'CCA'),
])
def test_unsupported_legacy_account_rejects(change, pattern):
    a = nem_account(**change)
    with pytest.raises(ValueError, match=pattern):
        bill('sce_tou-d-prime', frame('2026-07-06', '2026-07-06').assign(grid_export_kw=0.),
             a, '2026-07-06', '2026-07-06')
