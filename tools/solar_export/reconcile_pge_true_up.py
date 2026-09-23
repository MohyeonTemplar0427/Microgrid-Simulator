"""Replay PG&E NBT annual statement aggregates from a JSON file.

Usage: /usr/local/bin/python3 -m tools.solar_export.reconcile_pge_true_up INPUT.json
This is statement reconciliation, not automatic annual interval billing.
"""
import argparse
import json
from pathlib import Path
from src.billing.export_settlement import CreditBalance
from src.billing.pge_true_up import TrueUpRates, reconcile_nbt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text())
    payload['bank'] = CreditBalance(**payload['bank'])
    if payload.get('rates') is not None:
        payload['rates'] = TrueUpRates(**payload['rates'])
    print(json.dumps(reconcile_nbt(**payload), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
