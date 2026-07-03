.PHONY: build check compile docs format format-check lint test type-check

PYTHON_FILES = main.py src

check: lint format-check type-check compile docs build

lint:
	uv run ruff check $(PYTHON_FILES)

format:
	uv run ruff format $(PYTHON_FILES)

format-check:
	uv run ruff format --check $(PYTHON_FILES)

type-check:
	uv run mypy src

compile:
	uv run python -m compileall main.py src

test:
	uv run pytest -q

docs:
	uv run --group docs mkdocs build --strict

build:
	uv build
