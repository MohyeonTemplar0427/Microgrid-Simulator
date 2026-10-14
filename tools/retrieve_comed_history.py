"""Retrieve identified official evidence, verifying pinned revisions.

This research command does not register rates or infer historical coverage.
Tests and billing remain offline. A changed document requires explicit review.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-id', action='append', help='Manifest source ID; default: all identified sources')
    parser.add_argument('--output', type=Path, default=Path('.cache/comed_history/retrieved'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root/'docs/utility_sources/comed/history/manifest.json').read_text())
    sources = {s['id']: s for s in manifest['sources']}
    selected = args.source_id or list(sources)
    if set(selected)-set(sources):
        parser.error('Unknown source ID; identify and review its official URL first.')
    args.output.mkdir(parents=True, exist_ok=True)
    for ident in selected:
        source = sources[ident]; parsed = urlsplit(source['url'])
        if parsed.scheme != 'https' or parsed.hostname not in ('www.comed.com','www.icc.illinois.gov','icc.illinois.gov'):
            raise ValueError('Evidence must come from an identified official HTTPS source.')
        response = requests.get(source['url'], timeout=45)
        response.raise_for_status()
        data = response.content
        if not data.startswith(b'%PDF') or hashlib.sha256(data).hexdigest()!=source['sha256']:
            raise ValueError(ident+': downloaded revision differs from verified evidence; review before updating rates.')
        target = args.output/(ident+'.pdf')
        target.write_bytes(data)
        print(ident, source['sha256'], target)


if __name__ == '__main__':
    main()
