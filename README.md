# perfeng-contracts

## TL;DR

- This repository owns language-neutral schemas, OpenAPI descriptions,
  examples, fixtures and compatibility rules shared by `perfeng-*` components.
- Runtime behavior, persistence, analysis and deployment remain in their owning
  repositories.
- Data contracts are authored with Effect Schema and compiled to
  checked-in Draft 2020-12 JSON Schema for every consumer.
- Contract changes require positive and negative validation plus explicit
  compatibility and consumer-migration effects.
- Use `make validate` or the listed `pnpm` and `uv` commands for the complete
  offline validation suite.
- Candidate bundles are not stable releases; consumers pin reviewed immutable
  revisions.

Language-neutral performance engineering contracts, extracted from
`performance-platform`. The bundle covers execution metadata, normalized metrics,
workload definitions, test catalogues, raw/normalized result transport, and
performance policies with independent quality, SLO, and regression outcomes.

## Contents

| Contract | Schema | Purpose |
| --- | --- | --- |
| `candidate/v1` | [candidate](schemas/candidate/v1/candidate.schema.json) | Software identity |
| `environment/v1` | [environment](schemas/environment/v1/environment.schema.json) | Standalone environment descriptor |
| `run/v1` | [run metadata](schemas/run/v1/run-metadata.schema.json) | Execution identity, phases, and context |
| `result/v1` | [legacy test result](schemas/result/v1/test-result.schema.json) | Original metric record requiring a sample count |
| `result/v2` | [test result](schemas/result/v2/test-result.schema.json) | Metric record supporting unavailable sample counts |
| `artifact/v1` | [artifact reference](schemas/artifact/v1/artifact-reference.schema.json) | Stored bytes, checksum, size, format, and run identity |
| `raw-result/v1` | [raw result](schemas/raw-result/v1/raw-result.schema.json) | Raw artifact manifest with producer and measurement context |
| `raw-result/v2` | [raw result with execution provenance](schemas/raw-result/v2/raw-result.schema.json) | Raw artifact manifest supporting OCI images, native source checkouts, and verified release archives |
| `playwright-measurements/v1` | [Playwright measurements](schemas/playwright-measurements/v1/playwright-measurements.schema.json) | Original semantic browser timings with runtime and cache context |
| `playwright-measurements/v2` | [contextual Playwright measurements](schemas/playwright-measurements/v2/playwright-measurements.schema.json) | Semantic timings with page lifetime, diagnostic mode, and environment identity |
| `browser-environment/v1` | [browser environment](schemas/browser-environment/v1/browser-environment.schema.json) | Versioned host, browser, display, power, and calibration evidence |
| `browser-diagnostics/v1` | [browser diagnostics](schemas/browser-diagnostics/v1/browser-diagnostics.schema.json) | Capture status and immutable references for browser diagnostic evidence |
| `normalized-result/v1` | [normalized result](schemas/normalized-result/v1/normalized-result.schema.json) | Multi-metric envelope with raw evidence references |
| `workload/v1` | [workload](schemas/workload/v1/workload.schema.json) | Versioned profiles, configuration, phases, and dataset identity |
| `catalogue/v1` | [test catalogue](schemas/catalogue/v1/test-catalogue.schema.json) | Test ownership, pinned tools/source/images, and scheduling |
| `catalogue/v2` | [execution-aware test catalogue](schemas/catalogue/v2/test-catalogue.schema.json) | Test catalogue supporting container and native runner artifacts |
| `policy/v1` | [performance policy](schemas/policy/v1/performance-policy.schema.json) | Explicit metric thresholds and versioned baseline selection |
| `analysis/v1` | [analysis result](schemas/analysis/v1/analysis-result.schema.json) | Independent quality, SLO, and regression outcomes with evidence references |
| `baseline/v1` | [performance baseline](schemas/baseline/v1/baseline.schema.json) | Versioned normalized-result anchor, qualification, environment identity, and approval history |

[contracts.json](contracts.json) maps schemas to executable examples and records
the bundle version. The original normalized-result array remains a legacy
fixture, validated one metric at a time. New producers use the normalized-result
envelope containing `result/v2` records and references to raw evidence.

All nineteen data contracts are authored under `contracts/source` and generated
into their existing `schemas` paths. The registry in
`contracts/source/registry.ts` is the complete source-to-artifact ledger.
Generated files under `schemas` must not be edited directly. The Run Management
and Native Worker OpenAPI descriptions remain hand-authored. See
[ADR-0002](docs/decisions/0002-use-effect-schema-at-contract-boundaries.md).

## Validate

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), Node.js
and pnpm, then run the commands below from the repository root. The checked-in
`.python-version`, `.node-version`, `uv.lock` and `pnpm-lock.yaml` select the
toolchains and dependencies. These projects are development tooling; consumers
in Go, TypeScript and Python use the same generated JSON schemas.

```sh
uv sync --locked
pnpm install --frozen-lockfile
pnpm contracts:check
pnpm format:check
pnpm typecheck
pnpm test
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked ty check
uv run --locked python scripts/validate.py
uv run --locked python scripts/validate_api.py
uv run --locked python scripts/validate_native_worker_api.py
uv run --locked python -m unittest discover -s tests -v
```

On systems with Make, `make validate` runs the same non-mutating checks and
tests. The individual commands remain the portable, authoritative interface.

Ruff handles Python linting and formatting; ty handles static type checking.
To regenerate migrated schemas, run `make generate-contracts`. To apply
formatting and safe lint fixes, run `make fmt` and
`uv run ruff check --fix .`. Update dependencies intentionally and commit the
corresponding lockfile changes.

For VS Code, install the workspace's recommended extensions and select the
`.venv` interpreter after syncing. The checked-in settings enable Ruff formatting
and fixes on save, ty language services and type checking, and unittest discovery.
Biome formats and lints TypeScript; Prettier formats other supported text files;
Even Better TOML formats TOML. The existing autosave extension remains
recommended. `.vscode` configuration is shared; IntelliJ's root `.idea`
directory is ignored.

Validation checks Draft 2020-12 schemas, declared defaults, all examples,
date-time formats, catalogue/transport/policy consistency, baseline lifecycle,
and negative regression cases. Schema IDs identify bundled resources; validation
does not fetch schemas or artifacts from the internet. Tests verify fixture
checksums against local bytes.

CI runs these checks and uploads a `perfeng-contracts-0.16.0.tar.gz` candidate
bundle. That CI artifact is not a published stable release. Until a release
exists, integrations should pin the merged commit SHA, not a floating branch.

## Compatibility and migration

Read [compatibility](docs/compatibility.md),
[baseline lifecycle](docs/baseline-lifecycle.md),
[source provenance](docs/migration-provenance.md), and
[metric naming](docs/architecture/metric-naming.md).

The original Python implementation continues to use the prototype schemas
until its replacement is migrated. This repository owns subsequent contract
changes. Coordinate any necessary transitional fixes explicitly.

The standalone candidate/environment descriptors are not identical to the
inline structures in run metadata. This extraction preserves those wire
shapes; do not replace the inline structures with `$ref` mechanically.

See [workload and catalogue contracts](docs/workloads-and-catalogues.md) for
field semantics, hashing inputs, and migration from the prototype k6 files.
See [artifact and result transport](docs/artifact-and-result-transport.md) for
byte-level integrity, envelope semantics, and migration from legacy arrays.
See [Playwright measurements](docs/playwright-measurements.md) for browser,
cache, repetition, timing, and native-payload semantics.
See [browser environments and diagnostics](docs/browser-diagnostics.md) for
reference-machine identity, page lifetime, capture modes, evidence, and privacy.
See [performance policies and analysis outcomes](docs/performance-policies.md)
for non-blocking policy semantics, evidence requirements, and prototype migration.
The [run-management API](docs/run-management-api.md) specifies create/get/cancel,
principal-scoped artifact listing, idempotency, run lifecycle and explicit
baseline administration. Its self-contained OpenAPI description and fixtures
are under api/run-management/v1 and included in the candidate bundle.
The [Native Worker API](docs/native-worker-api.md) defines authenticated worker
presence, qualification interpretation, leased execution, cancellation,
exact-object S3 presigned upload grants, immutable artifact registration and
terminal attempt reporting. Its self-contained OpenAPI description and
conformance fixtures are under api/native-worker/v1.
HTTP, persistence and analysis implementations live in their owning repositories;
this repository defines only their language-neutral interchange boundaries.
Missing statistical values mean unavailable, never zero.
Schema validation establishes structural validity, not scientific quality or
performance-gate readiness.

## Development and governance

Start with these repository sources of truth:

- [Repository working agreement](AGENTS.md)
- [Contributor workflow](CONTRIBUTING.md)
- [Contract engineering standards](docs/development/engineering-standards.md)
- [Architecture decisions](docs/decisions/README.md)
- [Security policy](SECURITY.md)
- [Code of conduct](CODE_OF_CONDUCT.md)
- [Cross-repository roadmap](https://github.com/stanimirivanov/perfeng-environment/blob/main/docs/roadmap/milestones.md)

Task-specific issue and pull-request handoff text is printed for the repository
owner and is not stored in repository documentation.
