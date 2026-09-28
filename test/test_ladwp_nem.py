"""LADWP R-1A NEM cycle netting, protected charges and dispatch."""
import json

import numpy as np
import pandas as pd
import pytest

from src.billing.socal import bill
from src.dispatch.socal import optimize
from src.local_web.socal_study import execute, validate
from test_socal import account, frame, study_request


def nem_account(**changes):
    a = account()
    a.update(solar_program='ladwp_nem', interconnection_confirmed=True,
             nem_credit_confirmed=True, nem_opening_credit=0.)
    a.update(changes)
    return a


def cycle(start='2026-07-01', end='2026-07-31', load=1., export_kwh=0.):
    f = frame(start, end, kw=load)
    f['grid_export_kw'] = 0.
    if export_kwh:
        mask = (f.timestamp.dt.hour >= 10) & (f.timestamp.dt.hour < 14)
        f.loc[mask, 'grid_import_kw'] = 0.
        f.loc[mask, 'grid_export_kw'] = export_kwh / (.25 * mask.sum())
    return f


def test_r1a_cycle_nets_meter_kwh_before_tiers_and_applies_opening_credit():
    f = cycle(export_kwh=100.)
    a = nem_account(nem_opening_credit=20.)
    b = bill('ladwp_r-1a', f, a, '2026-07-01', '2026-07-31')
    net = b['import_kWh'] - b['export_kWh']
    assert net == pytest.approx(520.)
    assert b['usage_kWh'] == pytest.approx(net)
    assert b['line_items']['energy_charge'] == pytest.approx(350*.07142 + 170*.13001)
    assert b['credit_ledger']['applied_credit'] == pytest.approx(20.)
    assert b['credit_ledger']['closing_credit'] == pytest.approx(0.)
    assert b['total'] == pytest.approx(sum(b['line_items'].values()))
    no_credit = bill('ladwp_r-1a', f, nem_account(), '2026-07-01', '2026-07-31')
    assert no_credit['total'] - b['total'] == pytest.approx(20.)


def test_minimum_tax_and_opening_bank_remain_protected_at_zero_net():
    f = cycle('2026-07-06', '2026-07-06', load=0., export_kwh=0.)
    a = nem_account(nem_opening_credit=100., billing_month_factor=1., local_tax_percent=5.)
    b = bill('ladwp_r-1a', f, a, '2026-07-06', '2026-07-06')
    assert b['total'] == pytest.approx(12.30*1.05)
    assert b['credit_ledger']['applied_credit'] == 0.
    assert b['credit_ledger']['closing_credit'] == 100.


def test_net_export_and_unconfirmed_or_wrong_plan_reject():
    f = cycle('2026-07-06', '2026-07-06', export_kwh=30.)
    with pytest.raises(ValueError, match='net-export'):
        bill('ladwp_r-1a', f, nem_account(), '2026-07-06', '2026-07-06')
    with pytest.raises(ValueError, match='R-1A'):
        bill('ladwp_r-1b', cycle('2026-07-06', '2026-07-06'), nem_account(), '2026-07-06', '2026-07-06')
    with pytest.raises(ValueError, match='opening NEM credit'):
        bill('ladwp_r-1a', cycle('2026-07-06', '2026-07-06'), nem_account(nem_credit_confirmed=False), '2026-07-06', '2026-07-06')
    bad = cycle('2026-07-06', '2026-07-06')
    bad['grid_export_kw'] = .1
    with pytest.raises(ValueError, match='simultaneously'):
        bill('ladwp_r-1a', bad, nem_account(), '2026-07-06', '2026-07-06')


def test_dst_cycle_and_idle_battery_are_bill_optimal():
    start, end = '2025-03-08', '2025-03-10'
    f = frame(start, end, kw=2.)
    f['pv_available_kw'] = np.where((f.timestamp.dt.hour >= 10) & (f.timestamp.dt.hour < 14), 2., 0.)
    a = nem_account(billing_month_factor=3/30)
    battery = dict(capacity_kWh=10, energy_kWh=5, SOC_min=.2, SOC_max=.8,
                   max_charge_kw=3, max_discharge_kw=3, charge_efficiency=.95, discharge_efficiency=.95)
    result = optimize('ladwp_r-1a', f, a, start, end, battery, .01)
    d = result['dispatch']
    assert len(d) == 3*96-4
    assert result['objective_gap'] == 0.
    assert result['bill']['total'] == result['solar_bill']['total']
    assert result['degradation_cost'] == 0.
    assert np.allclose(d.grid_import_kw + d.pv_output_kw, d.native_load_kw + d.grid_export_kw)
    assert d.battery_charge_kw.sum() == d.battery_discharge_kw.sum() == 0.


def test_web_worker_exports_nem_credit_ledger(tmp_path):
    r = study_request('ladwp')
    r['tariff_id'] = 'ladwp_r-1a'
    r['start_date'], r['end_date'] = '2026-07-06', '2026-07-07'
    r['account'] = nem_account(nem_opening_credit=5., billing_month_factor=2/30)
    r['account']['actual_generation_provider'] = 'bundled'
    r['solar'] = {'capacity_kw':2., 'tilt':20., 'azimuth':180.}
    assert validate(r) == r
    (tmp_path / 'engine.json').write_text('{}')
    execute(tmp_path, r)
    result = json.loads((tmp_path / 'result.json').read_text())
    assert result['solar_program'] == 'ladwp_nem'
    assert result['bills']['pv_only']['export_kWh'] > 0
    assert any(t['id'] == 'solar_credit_ledger' for t in result['tables'])
    ledger = pd.read_csv(tmp_path / 'solar_credit_ledger.csv')
    assert {'grid_only', 'pv_only'} <= set(ledger.scenario)
