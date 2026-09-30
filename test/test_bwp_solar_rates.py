"""Independent adopted-rate checks for bounded BWP solar net billing."""
import pandas as pd
import pytest

from src.billing.bwp_solar_rates import export_prices, earned_export_credit, validate_net_billing_account
from src.billing.solar_programs import programs_for


def test_2026_bwp_acoe_weekday_weekend_and_holiday():
    stamps = pd.DatetimeIndex([
        '2026-07-06 17:00',  # Monday summer on-peak
        '2026-07-06 10:00',  # Monday summer mid-peak
        '2026-07-05 17:00',  # Sunday off-peak
        '2026-09-07 17:00',  # Labor Day off-peak
    ], tz='America/Los_Angeles')
    # Each isolated instant is checked separately because a billed series must
    # be ordered and contiguous; the actual rate lookup uses the same rules.
    assert [export_prices(pd.DatetimeIndex([stamp]))[0] for stamp in stamps] == pytest.approx(
        [.1186, .0825, .0702, .0702])


def test_bwp_export_credit_uses_interval_energy_and_remains_bounded():
    stamps = pd.date_range('2026-07-06 16:00', periods=4, freq='15min',
                           tz='America/Los_Angeles')
    result = earned_export_credit(stamps, [2., 2., 2., 2.])
    assert result['export_kwh'] == 2.
    assert result['earned_credit'] == pytest.approx(2 * .1186)
    assert next(p for p in programs_for('bwp', 'bwp')
                if p.id == 'bwp_net_billing').simulation_status == 'bounded_monthly'
    with pytest.raises(ValueError, match='verified only'):
        export_prices(pd.DatetimeIndex(['2026-09-21 12:00'],
                                       tz='America/Los_Angeles'))
    with pytest.raises(ValueError, match='verified only'):
        export_prices(pd.DatetimeIndex(['2026-01-06 12:00'],
                                       tz='America/Los_Angeles'))
    with pytest.raises(ValueError, match='interval-aligned'):
        earned_export_credit(stamps, [1., -1., 1., 1.])


def test_bwp_new_program_requires_dated_trigger_and_confirmed_interconnection():
    account = dict(solar_program='bwp_net_billing', solar_capacity_kw=4.,
                   interconnection_confirmed=True, permit_issue_date='2025-12-31')
    with pytest.raises(ValueError, match='on or after'):
        validate_net_billing_account(account, service_date='2026-07-01')
    account['upgrade_date'] = '2026-01-01'
    assert validate_net_billing_account(account, service_date='2026-07-01')
    account['solar_capacity_kw'] = 5000.
    assert validate_net_billing_account(account, service_date='2026-07-01')
    account['solar_capacity_kw'] = 5000.01
    with pytest.raises(ValueError, match='at most 5 MW'):
        validate_net_billing_account(account, service_date='2026-07-01')
    account['solar_capacity_kw'] = 4.
    account['interconnection_confirmed'] = False
    with pytest.raises(ValueError, match='interconnection'):
        validate_net_billing_account(account, service_date='2026-07-01')
    account = dict(solar_program='bwp_net_billing', solar_capacity_kw=4.,
                   interconnection_confirmed=True, account_transfer_date='2026-02-01')
    with pytest.raises(ValueError, match='on or after'):
        validate_net_billing_account(account, service_date='2026-07-01')
    account['transfer_to_new_customer_confirmed'] = True
    assert validate_net_billing_account(account, service_date='2026-07-01')
    with pytest.raises(ValueError, match='service date'):
        validate_net_billing_account(account, service_date='2026-01-31')
