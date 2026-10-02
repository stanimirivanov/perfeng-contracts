UV_RUN := uv run --locked --offline

.PHONY: help bootstrap doctor generate-contracts fmt fmt-check docs-check check test verify vuln license supply-chain validate

help:
	@echo perfeng-contracts engineering command surface
	@echo "  make bootstrap  Resolve locked Python and Node dependencies"
	@echo "  make doctor     Report the effective local toolchain"
	@echo "  make generate-contracts  Generate JSON Schema from Effect Schema"
	@echo "  make fmt        Format Python and TypeScript sources"
	@echo "  make fmt-check  Verify Python and TypeScript formatting"
	@echo "  make docs-check Verify repository documentation and policy"
	@echo "  make check      Run static, policy, lock and contract checks"
	@echo "  make test       Run the unit-test suite"
	@echo "  make verify     Run the offline development feedback loop"
	@echo "  make vuln       Audit locked Python and Node dependencies"
	@echo "  make license    Enforce production Node dependency licenses"
	@echo "  make supply-chain  Run vulnerability and license checks"
	@echo "  make validate   Run all non-publishing acceptance checks"

bootstrap:
	uv sync --locked
	pnpm install --frozen-lockfile

doctor:
	@git --version
	@uv --version
	@$(UV_RUN) python --version
	@node --version
	@pnpm --version
	@$(MAKE) --version

generate-contracts:
	pnpm contracts:generate

fmt:
	$(UV_RUN) ruff format .
	pnpm format

fmt-check:
	$(UV_RUN) ruff format --check .
	pnpm format:check

docs-check:
	$(UV_RUN) python scripts/repo_check.py

check: fmt-check docs-check
	uv lock --check --offline
	pnpm contracts:check
	pnpm typecheck
	$(UV_RUN) ruff check .
	$(UV_RUN) ty check
	$(UV_RUN) python scripts/validate.py
	$(UV_RUN) python scripts/validate_api.py
	$(UV_RUN) python scripts/validate_native_worker_api.py
	$(UV_RUN) python scripts/validate_native_worker_api_v2.py

test:
	pnpm test
	$(UV_RUN) python -m unittest discover -s tests -v

verify: check test

vuln:
	uv audit --preview-features audit-command --locked --python-platform linux
	uv audit --preview-features audit-command --locked --python-platform windows
	pnpm audit --audit-level high

license:
	pnpm licenses:check

supply-chain: vuln license

validate: verify supply-chain
