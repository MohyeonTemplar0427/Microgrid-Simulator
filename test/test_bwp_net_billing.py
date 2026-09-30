"""BWP sample-bill ordering, monthly balances, eligibility and dispatch."""

import numpy as np
import pandas as pd
import pytest

from src.billing.bwp_net_billing import settlement
from src.billing.socal import bill
from src.dispatch.socal import optimize


def account(**changes):
    result = dict(customer_class='residential', eligibility_confirmed=True,
                  ordinary_account_confirmed=True, cycle_confirmed=True,
                  tax_confirmed=True, bwp_ecac_confirmed=True,
                  bwp_ev_confirmed=True, reference='Synthetic BWP EV statement',
                  generation_provider='bwp', solar_program='bwp_net_billing',
                  voltage='secondary', phase='single', local_tax_percent=7.,
                  billing_month_factor=1., bwp_service_size='medium',
                  interconnection_confirmed=True, solar_capacity_kw=4.,
                  permit_issue_date='2026-02-01',
                  bwp_first_cycle_confirmed=True)
    result.update(changes)
    return result


def frame(load=1., pv=0., start='2026-07-01', end='2026-07-31'):
    index = pd.date_range(pd.Timestamp(start, tz='America/Los_Angeles'),
                          pd.Timestamp(end, tz='America/Los_Angeles') +
                          pd.DateOffset(days=1), freq='15min', inclusive='left')
    generation = np.full(len(index), pv) if np.isscalar(pv) else np.asarray(pv)
    native = np.full(len(index), load)
    return pd.DataFrame(dict(timestamp=index, native_load_kw=native,
                             pv_available_kw=generation,
                             grid_import_kw=np.maximum(native-generation, 0.),
                             grid_export_kw=np.maximum(generation-native, 0.)))


def test_published_bwp_sample_bill_order_reproduces_30_17():
    # Use the published statement's already-rounded dollar lines to isolate
    # credit/tax ordering. A synthetic July export vector yields its $104.40
    # credit; this does not extend July tariff coverage to the sample's winter.
    index = pd.date_range('2026-07-01 12:00', periods=1, freq='15min',
                          tz='America/Los_Angeles')
    credit = 104.40
    exports = np.array([credit / (.0825 * .25)])
    lines = dict(energy_charge=45.54+42.53, energy_cost_adjustment=18.70,
                 customer_charge=19.50, service_size_charge=4.45)
    total, items, ledger = settlement(lines, np.array([550/.25]), exports,
                                      index, account())
    assert round(total, 2) == 30.17
    assert items['solar_credit_applied'] == pytest.approx(-104.40)
    assert items['in_lieu_transfer'] == pytest.approx(.07*26.32)
    assert items['local_utility_tax'] == pytest.approx(.07*26.32)
    assert ledger['closing_credit'] == pytest.approx(0)


def test_net_import_net_export_and_carried_credit_are_reconciled():
    start, end = '2026-07-01', '2026-07-31'
    importer = frame(load=2., pv=1.)
    net_import = bill('bwp_ev', importer, account(), start, end)
    assert net_import['credit_ledger']['earned_export_credit'] == 0
    assert net_import['line_items']['energy_cost_adjustment'] == pytest.approx(744*.034)
    assert net_import['total'] == pytest.approx(sum(net_import['line_items'].values()))

    producer = frame(load=.1, pv=3.)
    net_export = bill('bwp_ev', producer, account(), start, end)
    ledger = net_export['credit_ledger']
    assert ledger['earned_export_credit'] > 0
    assert ledger['closing_credit'] > 0
    assert ledger['applied_to_usage'] == pytest.approx(
        net_export['line_items']['energy_charge'] +
        net_export['line_items']['energy_cost_adjustment'])
    assert net_export['total'] == pytest.approx(1.14*(19.50+4.45))

    carried = bill('bwp_ev', importer,
                   account(bwp_first_cycle_confirmed=False,
                           bwp_opening_credit=25.,
                           bwp_opening_balance_confirmed=True), start, end)
    assert carried['credit_ledger']['opening_credit'] == 25.
    assert carried['credit_ledger']['applied_to_usage'] == 25.
    assert carried['total'] == pytest.approx(net_import['total']-25*1.14)


def test_bwp_solar_rejects_wrong_schedule_dates_and_missing_credit_evidence():
    f = frame()
    with pytest.raises(ValueError, match='only for EV TOU'):
        bill('bwp_basic', f, account(), '2026-07-01', '2026-07-31')
    with pytest.raises(ValueError, match='Confirm the BWP opening'):
        bill('bwp_ev', f, account(bwp_first_cycle_confirmed=False,
                                  bwp_opening_credit=5.), '2026-07-01', '2026-07-31')
    with pytest.raises(ValueError, match='coverage'):
        bill('bwp_ev', frame(start='2026-06-01', end='2026-06-30'),
             account(), '2026-06-01', '2026-06-30')
    with pytest.raises(ValueError, match='coverage'):
        bill('bwp_ev', frame(start='2026-09-01', end='2026-09-30'),
             account(), '2026-09-01', '2026-09-30')
    with pytest.raises(ValueError, match='complete monthly'):
        bill('bwp_ev', frame(start='2026-07-01', end='2026-07-10'),
             account(), '2026-07-01', '2026-07-10')


def test_bwp_storage_dispatch_prices_exports_and_ignores_inherited_balance():
    f = frame(load=.8, start='2026-07-01', end='2026-07-25')
    hour = f.timestamp.dt.hour + f.timestamp.dt.minute/60
    f['pv_available_kw'] = np.where((hour >= 10) & (hour < 17), 3., 0.)
    battery = dict(capacity_kWh=5., energy_kWh=2.5, SOC_min=.2, SOC_max=.8,
                   max_charge_kw=2., max_discharge_kw=2.,
                   charge_efficiency=.95, discharge_efficiency=.95)
    result = optimize('bwp_ev', f, account(), '2026-07-01', '2026-07-25',
                      battery, .01)
    assert result['objective_gap'] < .02
    assert result['solar_bill']['total'] >= result['bill']['total']-.02
    dispatch = result['dispatch']
    assert np.allclose(dispatch.grid_import_kw+dispatch.pv_output_kw+
                       dispatch.battery_discharge_kw,
                       dispatch.native_load_kw+dispatch.battery_charge_kw+
                       dispatch.grid_export_kw,
                       atol=1e-5)
    assert np.allclose(dispatch.pv_available_kw,
                       dispatch.grid_export_kw+dispatch.battery_charge_kw+
                       np.minimum(dispatch.native_load_kw,
                                  dispatch.pv_available_kw), atol=1e-5)
    assert np.max(dispatch.battery_charge_kw * dispatch.grid_import_kw) < 1e-5
    assert np.max(dispatch.battery_discharge_kw * dispatch.grid_export_kw) < 1e-5
    inherited = optimize('bwp_ev', f,
                         account(bwp_first_cycle_confirmed=False,
                                 bwp_opening_credit=100.,
                                 bwp_opening_balance_confirmed=True),
                         '2026-07-01', '2026-07-25', battery, .01)
    assert np.allclose(dispatch.battery_charge_kw,
                       inherited['dispatch'].battery_charge_kw, atol=2e-4)
    assert inherited['bill']['total'] < result['bill']['total']
