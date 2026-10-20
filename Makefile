.PHONY: setup test lint fmt check demo golden clean

setup:
	uv sync

test:
	uv run pytest -q --cov=dq --cov-report=term-missing

fmt:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy dq

check: lint test

demo:
	mkdir -p out
	uv run python -m dq review data/samples/sample_input.json -o out/review.json --report out/review.md
	@echo "--- out/review.md ---" && cat out/review.md

# HUMAN ONLY: regenerate golden output after reviewing the diff
golden:
	uv run python -m dq review data/samples/edge_cases.json -o tests/golden/expected_output.json
	git diff --stat tests/golden/expected_output.json

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage out
