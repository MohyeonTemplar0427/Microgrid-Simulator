"""Replay twelve documented PG&E NBT monthly records and annual true-up.

Usage: /usr/local/bin/python3 -m tools.solar_export.replay_pge_annual INPUT.json
"""

import argparse
import json
from pathlib import Path

from src.billing.export_settlement import CreditBalance
from src.billing.pge_annual_replay import MonthlyNBTRecord, replay_nbt_year
from src.billing.pge_true_up import TrueUpRates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    if set(data) != {'account_confirmed', 'records', 'rates'}:
        raise ValueError('Supply account_confirmed, records and rates (null for a net consumer).')
    records = []
    for entry in data['records']:
        entry = dict(entry)
        if entry.get('stated_closing_balance') is not None:
            entry['stated_closing_balance'] = CreditBalance(**entry['stated_closing_balance'])
        records.append(MonthlyNBTRecord(**entry))
    rates = None if data['rates'] is None else TrueUpRates(**data['rates'])
    print(json.dumps(replay_nbt_year(records, account_confirmed=data['account_confirmed'], rates=rates),
                     indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
