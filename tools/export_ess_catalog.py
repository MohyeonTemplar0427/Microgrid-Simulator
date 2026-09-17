"""Export reviewed facts and explicitly requested engine mappings without network access.

By default, unresolved assumptions remain blocking. This is an interchange
artifact, not an import mechanism or a way to update a running engine pin.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.equipment.ess import resolve, search
from src.equipment.ess_catalog import REVISION, RETRIEVED


def build_export(*, accept_efficiency_approximation=False, powerwall2_capacity_basis=None):
    resolutions = []
    for record in search():
        basis = powerwall2_capacity_basis if record['id'] == 'tesla.powerwall2.1092170.na' else None
        resolutions.append(resolve(record['id'], capacity_basis=basis,
                                   efficiency_approximation=accept_efficiency_approximation))
    return {
        'schema_version': 1,
        'catalog_revision': REVISION,
        'reviewed_on': RETRIEVED,
        'scope': 'The three currently cataloged North American equipment choices; not the complete CEC list.',
        'operating_defaults': {'quantity': 1, 'initial_soc': .5, 'backup_reserve': .2},
        'usage': 'Only records with ready=true have usable engine battery parameters. Assumptions must be reviewed. Metadata such as temperature limits is not an implemented derating model.',
        'resolutions': resolutions,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--accept-efficiency-approximation', action='store_true',
                        help='Explicitly accept equal square-root splitting of AC round-trip efficiency.')
    parser.add_argument('--powerwall2-capacity-basis', choices=('ac_deliverable', 'usable_internal'),
                        help='Explicit assumption; the reviewed source does not establish this boundary.')
    args = parser.parse_args()
    payload = build_export(accept_efficiency_approximation=args.accept_efficiency_approximation,
                           powerwall2_capacity_basis=args.powerwall2_capacity_basis)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(f"Exported {len(payload['resolutions'])} equipment records to {args.output}")


if __name__ == '__main__':
    main()
