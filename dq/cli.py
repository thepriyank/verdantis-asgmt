"""Command line entry: python -m dq review <input.json> [-o out.json] [--report out.md]."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from dq.ai.stub import StubSuggester
from dq.config import load_config
from dq.ingest import IngestError, load_file
from dq.pipeline import run_review
from dq.report import to_json, to_markdown

EXIT_OK = 0
EXIT_BAD_INPUT = 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dq", description="Item-master data-quality review.")
    sub = parser.add_subparsers(dest="command", required=True)
    review = sub.add_parser("review", help="produce review candidates for a data steward")
    review.add_argument("input", type=Path, help="JSON file containing an array of item records")
    review.add_argument("-o", "--output", type=Path, help="write JSON here (default: stdout)")
    review.add_argument("--report", type=Path, help="also write a markdown summary here")
    review.add_argument(
        "--suggest",
        action="store_true",
        help="add AI-assisted description suggestions (offline stub; suggestions only)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    cfg = load_config()
    # Writing over the input would destroy the source records, which this tool never edits.
    inputs = args.input.resolve()
    if any(p and p.resolve() == inputs for p in (args.output, args.report)):
        print("error: output path must differ from the input file", file=sys.stderr)
        return EXIT_BAD_INPUT
    try:
        ingest = load_file(args.input, cfg)
    except IngestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT
    suggester = StubSuggester(cfg) if args.suggest else None
    result = run_review(ingest.records, ingest.parse_issues, cfg, suggester)
    payload = to_json(result)
    try:
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        else:
            sys.stdout.write(payload)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(to_markdown(result), encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot write output: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT
    if not ingest.records:
        print("No records found in the input; nothing to review.", file=sys.stderr)
    return EXIT_OK
