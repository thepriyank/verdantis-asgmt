"""Command line entry.

python -m dq review <input.json> [-o out.json] [--report out.md] [--suggest]
python -m dq apply-decisions <review.json> <decisions.json> [-o audit.json] [--decided-at TS]
python -m dq eval-suggester [--cases cases.json]
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from dq.ai.evaluate import load_cases, run_eval
from dq.ai.stub import StubSuggester
from dq.config import load_config
from dq.ingest import IngestError, load_file
from dq.pipeline import run_review
from dq.report import to_json, to_markdown
from dq.review import ReviewFileError, build_audit_log, read_json, to_json_text

EXIT_OK = 0
EXIT_GATE_FAILED = 1
EXIT_BAD_INPUT = 2
DEFAULT_EVAL_CASES = (
    Path(__file__).resolve().parent.parent / "data" / "eval" / "suggester_cases.json"
)


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
    apply = sub.add_parser("apply-decisions", help="record human decisions in an audit log")
    apply.add_argument("review", type=Path, help="review JSON produced by `dq review`")
    apply.add_argument("decisions", type=Path, help="JSON array of reviewer decisions")
    apply.add_argument(
        "-o", "--output", type=Path, help="write the audit log here (default: stdout)"
    )
    apply.add_argument("--decided-at", help="ISO timestamp for the log (default: now, UTC)")
    ev = sub.add_parser("eval-suggester", help="run the offline eval gate on the AI suggester")
    ev.add_argument("--cases", type=Path, default=DEFAULT_EVAL_CASES, help="eval cases JSON")
    return parser


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return EXIT_BAD_INPUT


def _collides(inputs: Sequence[Path], outputs: Sequence[Path | None]) -> bool:
    # Writing over an input would destroy source data; this tool never edits its inputs.
    resolved = {p.resolve() for p in inputs}
    return any(p is not None and p.resolve() in resolved for p in outputs)


def _write(path: Path | None, text: str) -> None:
    if path is None:
        sys.stdout.write(text)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_review(args: argparse.Namespace) -> int:
    cfg = load_config()
    if _collides([args.input], [args.output, args.report]):
        return _fail("output path must differ from the input file")
    try:
        ingest = load_file(args.input, cfg)
    except IngestError as exc:
        return _fail(str(exc))
    suggester = StubSuggester(cfg) if args.suggest else None
    result = run_review(ingest.records, ingest.parse_issues, cfg, suggester)
    try:
        _write(args.output, to_json(result))
        if args.report:
            _write(args.report, to_markdown(result))
    except OSError as exc:
        return _fail(f"cannot write output: {exc}")
    if not ingest.records:
        print("No records found in the input; nothing to review.", file=sys.stderr)
    return EXIT_OK


def _run_apply(args: argparse.Namespace) -> int:
    if _collides([args.review, args.decisions], [args.output]):
        return _fail("output path must differ from the input files")
    try:
        review, decisions = read_json(args.review), read_json(args.decisions)
        if not isinstance(decisions, list):
            return _fail(f"{args.decisions}: expected a JSON array of decisions")
        decided_at = args.decided_at or datetime.now(UTC).isoformat(timespec="seconds")
        log = build_audit_log(review, decisions, decided_at)
        _write(args.output, to_json_text(log))
    except ReviewFileError as exc:
        return _fail(str(exc))
    except OSError as exc:
        return _fail(f"cannot write output: {exc}")
    if log.errors:
        print(
            f"{len(log.errors)} decision(s) could not be recorded; see 'errors'.", file=sys.stderr
        )
    return EXIT_OK


def _run_eval(args: argparse.Namespace) -> int:
    cfg = load_config()
    try:
        cases = load_cases(args.cases)
    except (OSError, ValueError) as exc:
        return _fail(f"cannot use eval cases {args.cases}: {exc}")
    report = run_eval(StubSuggester(cfg), cases, cfg)
    sys.stdout.write(report.model_dump_json(indent=2) + "\n")
    return EXIT_OK if report.passed else EXIT_GATE_FAILED


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    handlers = {"review": _run_review, "apply-decisions": _run_apply, "eval-suggester": _run_eval}
    return handlers[args.command](args)
