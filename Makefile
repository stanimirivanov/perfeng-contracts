UV_RUN := uv run --locked --offline

.PHONY: help bootstrap doctor generate-contracts fmt fmt-check docs-check check test verify vuln license supply-chain validate

help:
	@echo perfeng-contracts engineering command surface
	@echo "  make bootstrap  Resolve locked Python and Node dependencies"
	@echo "  make doctor     Report the effective local toolchain"
	@echo "  make generate-contracts  Generate JSON Schema from Effect Schema"
	@echo "  make distribution-check  Verify deterministic contract packaging"
	@echo "  make distribution-admission-check  Verify candidate admission boundaries"
	@echo "  make distribution-history-check  Verify local historical profiles and reference closure"
	@echo "  make registry-qualification-check  Test registry admission rules offline"
	@echo "  make registry-admission  Exercise the pinned candidate in a private network namespace"
	@echo "  make publication-check   Verify local immutable publication"
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

check: fmt-check docs-check api-review-check api-source-check
	uv lock --check --offline
	pnpm contracts:check
	pnpm typecheck
	$(UV_RUN) ruff check .
	$(UV_RUN) ty check
	$(UV_RUN) python scripts/validate.py
	$(UV_RUN) python scripts/validate_api.py
	$(UV_RUN) python scripts/validate_native_worker_api.py
	$(UV_RUN) python scripts/validate_performance_integration_api.py

test:
	pnpm test
	$(UV_RUN) python -m unittest discover -s tests -v

verify: check test

vuln:
	uv audit --preview-features audit-command --locked --python-platform linux
	pnpm audit --audit-level high

license:
	pnpm licenses:check

supply-chain: vuln license

validate: verify supply-chain

.PHONY: api-review-check
api-review-check:
	$(UV_RUN) python scripts/api_review.py > /dev/null

.PHONY: api-source-check
api-source-check:
	$(UV_RUN) python scripts/api_sources.py

.PHONY: distribution-check
distribution-check:
	$(UV_RUN) python -m unittest discover -s tests -p test_contract_pack.py -v

.PHONY: publication-check
publication-check:
	$(UV_RUN) python -m unittest discover -s tests -p test_contract_publish.py -v

.PHONY: distribution-history-check
distribution-history-check:
	$(UV_RUN) python -m scripts.contracts_history

.PHONY: distribution-admission-check
distribution-admission-check:
	$(UV_RUN) python -m unittest discover -s tests -p test_distribution_admission.py -v

.PHONY: registry-qualification-check registry-admission
registry-qualification-check:
	$(UV_RUN) python -m unittest discover -s tests -p test_registry_qualification.py -v

registry-admission:
	@unshare --user --map-root-user --net sh -c 'ip link set lo up && exec "$$@"' sh \
		$(UV_RUN) python -m scripts.registry_qualification --binary "$(REGISTRY_BINARY)"
