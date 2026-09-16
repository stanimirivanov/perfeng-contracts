.PHONY: help fmt fmt-check check test validate

help:
	@echo perfeng-contracts engineering command surface
	@echo "  make fmt        Format Python sources"
	@echo "  make fmt-check  Verify Python formatting without changes"
	@echo "  make check      Run static and contract checks"
	@echo "  make test       Run the unit-test suite"
	@echo "  make validate   Run all non-mutating checks and tests"

fmt:
	uv run --locked ruff format .

fmt-check:
	uv run --locked ruff format --check .

check: fmt-check
	uv run --locked ruff check .
	uv run --locked ty check
	uv run --locked python scripts/validate.py
	uv run --locked python scripts/validate_api.py

test:
	uv run --locked python -m unittest discover -s tests -v

validate: check test
