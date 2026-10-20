"""Offline eval of a Suggester: the gate to run on every prompt, model or abbreviation change."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dq.ai.evaluate import EvalCase, EvalReport, load_cases, run_eval
from dq.ai.stub import StubSuggester
from dq.ai.suggester import AllowlistedFields
from dq.cli import main
from dq.config import Config

CASES = Path(__file__).resolve().parents[2] / "data" / "eval" / "suggester_cases.json"


class Fixed:
    """A suggester that always returns the same raw response."""

    def __init__(self, response: object) -> None:
        self.response = response

    def suggest(self, fields: AllowlistedFields) -> object:
        return self.response


class Raises:
    def suggest(self, fields: AllowlistedFields) -> object:
        raise TimeoutError("provider down")


def case(expected: str | None, description: str = "BRG 6205") -> EvalCase:
    return EvalCase(id="c", item_description=description, expected=expected)


def test_bundled_cases_are_well_formed_and_include_hostile_text() -> None:
    cases = load_cases(CASES)
    assert len(cases) >= 10
    assert sum(c.adversarial for c in cases) >= 3
    assert len({c.id for c in cases}) == len(cases)


def test_stub_passes_the_gate_on_the_bundled_cases(cfg: Config) -> None:
    report = run_eval(StubSuggester(cfg), load_cases(CASES), cfg)
    assert report.passed, report.model_dump()
    assert report.accuracy == 1.0
    assert (report.wrong, report.false_suggestions, report.missed, report.errors) == (0, 0, 0, 0)
    assert report.total == report.correct


def test_wrong_text_fails_the_gate(cfg: Config) -> None:
    good = {"suggested_description": "Totally different", "explanation": "x", "confidence": 0.5}
    report = run_eval(Fixed(good), [case("Bearing 6205")], cfg)
    assert (report.wrong, report.correct, report.passed) == (1, 0, False)


def test_suggesting_when_nothing_is_expected_is_a_false_suggestion(cfg: Config) -> None:
    resp = {"suggested_description": "Invented text", "explanation": "x", "confidence": 0.5}
    report = run_eval(Fixed(resp), [case(None)], cfg)
    assert report.false_suggestions == 1
    assert report.passed is False


def test_no_suggestion_when_one_is_expected_is_missed(cfg: Config) -> None:
    report = run_eval(Fixed(None), [case("Bearing 6205")], cfg)
    assert (report.missed, report.passed) == (1, False)


def test_output_the_guardrails_reject_counts_as_rejected(cfg: Config) -> None:
    report = run_eval(Fixed({"suggested_description": "X"}), [case(None)], cfg)
    assert report.rejected_by_guardrails == 1
    assert report.correct == 1  # nothing shown to the steward, and nothing was expected


def test_provider_failure_is_an_error_not_a_crash(cfg: Config) -> None:
    report = run_eval(Raises(), [case("Bearing 6205")], cfg)
    assert report.errors == 1
    assert report.passed is False


def test_empty_case_list_does_not_pass(cfg: Config) -> None:
    report = run_eval(StubSuggester(cfg), [], cfg)
    assert report.total == 0
    assert report.passed is False


def test_report_is_deterministic(cfg: Config) -> None:
    cases = load_cases(CASES)
    a = run_eval(StubSuggester(cfg), cases, cfg)
    b = run_eval(StubSuggester(cfg), cases, cfg)
    assert a == b and isinstance(a, EvalReport)


def test_unusable_cases_file_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"not": "a list"}', encoding="utf-8")
    with pytest.raises(ValueError, match="array"):
        load_cases(bad)


def test_cli_eval_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["eval-suggester"]) == 0
    assert json.loads(capsys.readouterr().out)["passed"] is True
    failing = tmp_path / "cases.json"
    failing.write_text(
        json.dumps([{"id": "x", "item_description": "BRG 6205", "expected": "Wrong"}]),
        encoding="utf-8",
    )
    assert main(["eval-suggester", "--cases", str(failing)]) == 1
    assert main(["eval-suggester", "--cases", str(tmp_path / "none.json")]) == 2


class ByDescription:
    """Answers differently per description so one run can mix outcomes."""

    def __init__(self, answers: dict[str, object]) -> None:
        self.answers = answers

    def suggest(self, fields: AllowlistedFields) -> object:
        answer = self.answers[fields.item_description or ""]
        if isinstance(answer, Exception):
            raise answer
        return answer


def good(text: str) -> dict[str, object]:
    return {"suggested_description": text, "explanation": "x", "confidence": 0.5}


def test_each_gate_condition_fails_independently_when_accuracy_is_relaxed(cfg: Config) -> None:
    relaxed = cfg.model_copy(update={"ai_eval_min_accuracy": 0.5})
    ok = case("Bearing 6205", "a")
    false = case(None, "b")
    err = case("Bearing 6205", "c")
    sug = ByDescription({"a": good("Bearing 6205"), "b": good("Invented"), "c": TimeoutError()})

    only_false = run_eval(sug, [ok, false], relaxed)
    assert (only_false.accuracy, only_false.false_suggestions) == (0.5, 1)
    assert only_false.passed is False

    only_error = run_eval(sug, [ok, err], relaxed)
    assert (only_error.accuracy, only_error.errors) == (0.5, 1)
    assert only_error.passed is False

    assert run_eval(sug, [ok], relaxed).passed is True


def test_empty_cases_fail_even_when_accuracy_floor_is_zero(cfg: Config) -> None:
    lenient = cfg.model_copy(update={"ai_eval_min_accuracy": 0.0})
    assert run_eval(StubSuggester(lenient), [], lenient).passed is False
