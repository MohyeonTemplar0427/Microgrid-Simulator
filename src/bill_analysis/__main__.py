"""Local, backend-only workflow for private customer bill PDFs.

Run from the repository root with ``/usr/local/bin/python3 -m src.bill_analysis``.
The PDF is read into memory and not copied into the project or printed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from . import analyze_bills, apply_corrections, extract_bill


def _read_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(value: dict, path: str | None) -> None:
    content = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if path:
        target = Path(path)
        if target.exists():
            raise ValueError(f"Output already exists: {target}. Choose a new path to preserve review history.")
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
    else:
        sys.stdout.write(content)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract, review and analyze measured electric bills locally.")
    commands = parser.add_subparsers(dest="command", required=True)
    extract = commands.add_parser("extract", help="Extract a reviewable draft from one PDF.")
    extract.add_argument("pdf")
    extract.add_argument("--output")
    review = commands.add_parser("review", help="Apply corrections and approve a draft.")
    review.add_argument("draft")
    review.add_argument("--corrections", help="JSON object mapping field paths to corrected values.")
    review.add_argument("--output")
    review.add_argument("--keep-draft", action="store_true", help="Apply corrections without approving yet.")
    analyze = commands.add_parser("analyze", help="Analyze one or more approved bills.")
    analyze.add_argument("bills", nargs="+")
    analyze.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        if args.command == "extract":
            result = extract_bill(Path(args.pdf).read_bytes())
        elif args.command == "review":
            changes = _read_json(args.corrections) if args.corrections else {}
            result = apply_corrections(_read_json(args.draft), changes, approve=not args.keep_draft)
        else:
            result = analyze_bills([_read_json(path) for path in args.bills])
        _write_json(result, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Bill analysis: {exc}\n")


if __name__ == "__main__":
    main()
