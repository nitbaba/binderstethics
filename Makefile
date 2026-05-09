.PHONY: install install-dev run test lint format typecheck clean

PYTHON := python3
VENV   := .venv
BIN    := $(VENV)/bin

# ── Setup ──────────────────────────────────────────────────────────────────
install:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install .

install-dev:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev]"
	cp -n .env.example .env || true

# ── Run ────────────────────────────────────────────────────────────────────
run:
	$(BIN)/python -m src.main

# ── Quality ────────────────────────────────────────────────────────────────
lint:
	$(BIN)/ruff check src tests

format:
	$(BIN)/ruff format src tests

typecheck:
	$(BIN)/mypy src

test:
	$(BIN)/pytest

# ── Cleanup ────────────────────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov .coverage dist build *.egg-info
