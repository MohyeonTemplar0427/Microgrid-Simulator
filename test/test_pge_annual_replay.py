"""Cross-cycle PG&E NBT credit and true-up reconciliation."""

from calendar import monthrange
from dataclasses import asdict
import json
import subprocess

import pytest

from src.billing.pge_annual_replay import MonthlyNBTRecord, replay_nbt_year
from src.billing.pge_true_up import TrueUpRates


def records():
    months = [(2024, month) for month in range(2, 13)] + [(2025, 1)]
    result = []
    for number, (year, month) in enumerate(months):
        # Early import bills were paid; late exports create a restricted bank.
        charges = {'generation': 4. if number == 0 else 0.,
                   'delivery': 500. if number == 0 else 0.,
                   'protected': 20. if number == 0 else 0.}
        earned = {'generation': 136.94 if number == 11 else 0.,
                  'delivery': 22. if number == 11 else 0.,
                  'bonus': 1.05 if number == 11 else 0.}
        result.append(MonthlyNBTRecord(
            f'{year}-{month:02d}-01', f'{year}-{month:02d}-{monthrange(year, month)[1]:02d}',
            3000. if number == 0 else 0., 5000. if number == 11 else 0.,
            charges, earned, {'generation': 4. if number == 0 else 0.,
                              'delivery': 500. if number == 0 else 0.},
            f'Hypothetical cycle {number + 1}', 'hypothetical'))
    return result


def factors():
    return TrueUpRates('2025-01', .04, .01, .02965,
                       'PG&E guide illustrative factors', 'hypothetical')


def test_twelve_cycle_replay_reproduces_published_true_up_arithmetic():
    result = replay_nbt_year(records(), account_confirmed=True, rates=factors())
    assert result['annual_import_kwh'] == 3000
    assert result['annual_export_kwh'] == 5000
    assert result['monthly_amount_due_sum'] == pytest.approx(524)
    assert result['pre_true_up_balance'] == pytest.approx(dict(generation=136.94, delivery=22, bonus=1.05))
    assert result['true_up']['adjustment_before_bonus'] == pytest.approx(-65.30)
    assert result['true_up']['adjustment_if_all_bonus_applied'] == pytest.approx(-66.35)
    assert result['next_period_balance_before_bonus_application'] == pytest.approx(dict(generation=52.94, delivery=0, bonus=1.05))


def test_credit_carryover_can_offset_next_month_but_not_protected_charge():
    months = records()
    first, second = months[0], months[1]
    months[0] = MonthlyNBTRecord(first.period_start, first.period_end, 0, 0,
                                  {'generation': 0, 'delivery': 0, 'protected': 10},
                                  {'generation': 8, 'delivery': 0, 'bonus': 0},
                                  {'generation': 0, 'delivery': 0}, first.source_reference, 'hypothetical')
    months[1] = MonthlyNBTRecord(second.period_start, second.period_end, 0, 0,
                                  {'generation': 6, 'delivery': 0, 'protected': 2},
                                  {'generation': 0, 'delivery': 0, 'bonus': 0},
                                  {'generation': 0, 'delivery': 0}, second.source_reference, 'hypothetical')
    result = replay_nbt_year(months, account_confirmed=True, rates=factors())
    assert result['monthly'][0]['amount_due'] == 10
    assert result['monthly'][1]['amount_due'] == 2
    assert result['monthly'][1]['credits_used']['generation'] == 6
    assert result['monthly'][1]['closing_balance']['generation'] == 2


def test_json_replay_command_emits_derived_true_up(tmp_path):
    payload = {'account_confirmed': True, 'records': [asdict(item) for item in records()],
               'rates': asdict(factors())}
    path = tmp_path / 'hypothetical-year.json'
    path.write_text(json.dumps(payload))
    completed = subprocess.run(['/usr/local/bin/python3', '-m', 'tools.solar_export.replay_pge_annual', str(path)],
                               capture_output=True, text=True, check=True)
    assert json.loads(completed.stdout)['true_up']['adjustment_if_all_bonus_applied'] == pytest.approx(-66.35)


@pytest.mark.parametrize('change', ['missing_month', 'gap', 'overpaid', 'mixed_evidence', 'wrong_rate_month', 'negative_energy', 'wrong_stated_bill', 'wrong_stated_bank'])
def test_unverified_or_incomplete_history_rejected(change):
    months = records()
    rates = factors()
    if change == 'missing_month':
        months.pop(4)
    elif change == 'gap':
        item = months[1]
        months[1] = MonthlyNBTRecord('2024-03-02', item.period_end, item.import_kwh,
                                     item.export_kwh, item.charges, item.credits_earned,
                                     item.offsettable_paid, item.source_reference, item.evidence_kind)
    elif change == 'overpaid':
        item = months[0]
        months[0] = MonthlyNBTRecord(item.period_start, item.period_end, item.import_kwh,
                                     item.export_kwh, item.charges, item.credits_earned,
                                     {'generation': 4, 'delivery': 521}, item.source_reference, item.evidence_kind)
    elif change == 'mixed_evidence':
        item = months[1]
        months[1] = MonthlyNBTRecord(item.period_start, item.period_end, item.import_kwh,
                                     item.export_kwh, item.charges, item.credits_earned,
                                     item.offsettable_paid, item.source_reference, 'statement_transcription')
    elif change == 'wrong_rate_month':
        rates = TrueUpRates('2025-02', .04, .01, .02965, 'Wrong month', 'hypothetical')
    elif change == 'negative_energy':
        item = months[0]
        months[0] = MonthlyNBTRecord(item.period_start, item.period_end, -1,
                                     item.export_kwh, item.charges, item.credits_earned,
                                     item.offsettable_paid, item.source_reference, item.evidence_kind)
    elif change == 'wrong_stated_bill':
        item = months[0]
        months[0] = MonthlyNBTRecord(item.period_start, item.period_end, item.import_kwh,
                                     item.export_kwh, item.charges, item.credits_earned,
                                     item.offsettable_paid, item.source_reference, item.evidence_kind,
                                     stated_amount_due=100)
    elif change == 'wrong_stated_bank':
        from src.billing.export_settlement import CreditBalance
        item = months[0]
        months[0] = MonthlyNBTRecord(item.period_start, item.period_end, item.import_kwh,
                                     item.export_kwh, item.charges, item.credits_earned,
                                     item.offsettable_paid, item.source_reference, item.evidence_kind,
                                     stated_closing_balance=CreditBalance(generation=5))
    with pytest.raises(ValueError):
        replay_nbt_year(months, account_confirmed=True, rates=rates)
