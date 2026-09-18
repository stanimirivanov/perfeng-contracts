.PHONY: help generate-contracts fmt fmt-check check test validate

help:
	@echo perfeng-contracts engineering command surface
	@echo "  make generate-contracts  Generate JSON Schema from Effect Schema"
	@echo "  make fmt        Format Python and TypeScript sources"
	@echo "  make fmt-check  Verify Python and TypeScript formatting"
	@echo "  make check      Run static and contract checks"
	@echo "  make test       Run the unit-test suite"
	@echo "  make validate   Run all non-mutating checks and tests"

generate-contracts:
	pnpm contracts:generate

fmt:
	uv run --locked ruff format .
	pnpm format

fmt-check:
	uv run --locked ruff format --check .
	pnpm format:check

check: fmt-check
	pnpm contracts:check
	pnpm typecheck
	uv run --locked ruff check .
	uv run --locked ty check
	uv run --locked python scripts/validate.py
	uv run --locked python scripts/validate_api.py
	uv run --locked python scripts/validate_native_worker_api.py

test:
	pnpm test
	uv run --locked python -m unittest discover -s tests -v

validate: check test
