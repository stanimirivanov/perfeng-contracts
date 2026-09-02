# perfeng-contracts

Language-neutral performance engineering contracts, extracted from
`performance-platform`. The bundle covers execution metadata, normalized metrics,
workload definitions, and test catalogues from proposal phase 1. Policy and
transport contracts are still to follow.

## Contents

| Contract | Schema | Purpose |
| --- | --- | --- |
| `candidate/v1` | [candidate](schemas/candidate/v1/candidate.schema.json) | Software identity |
| `environment/v1` | [environment](schemas/environment/v1/environment.schema.json) | Standalone environment descriptor |
| `run/v1` | [run metadata](schemas/run/v1/run-metadata.schema.json) | Execution identity, phases, and context |
| `result/v1` | [test result](schemas/result/v1/test-result.schema.json) | One normalized metric record |
| `workload/v1` | [workload](schemas/workload/v1/workload.schema.json) | Versioned profiles, configuration, phases, and dataset identity |
| `catalogue/v1` | [test catalogue](schemas/catalogue/v1/test-catalogue.schema.json) | Test ownership, pinned tools/source/images, and scheduling |

[contracts.json](contracts.json) maps schemas to executable examples and records
the bundle version. The normalized-result example is an array of metric
records; each element is validated separately. This PR does not define an
array envelope for transport.

## Validate

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run
the commands below from the repository root. uv creates `.venv` and installs
the development tools from `uv.lock`. `.python-version` selects Python 3.12.
The Python project is development tooling; consumers in Go, TypeScript, and
Python use the same JSON schemas. It is not built as an installable package.

```sh
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked ty check
uv run --locked python scripts/validate.py
uv run --locked python -m unittest discover -s tests -v
```

Ruff handles Python linting and formatting; ty handles static type checking.
To apply formatting and safe lint fixes, run `uv run ruff check --fix .` and
`uv run ruff format .`. Update dependencies intentionally with `uv lock --upgrade`
and commit the resulting `uv.lock` changes with `pyproject.toml` as appropriate.

For VS Code, install the workspace's recommended extensions and select the
`.venv` interpreter after syncing. The checked-in settings enable Ruff formatting
and fixes on save, ty language services and type checking, and unittest discovery.
Prettier formats JSON/YAML/Markdown; Even Better TOML formats TOML. The existing
autosave extension remains recommended. `.vscode` configuration is shared;
IntelliJ's root `.idea` directory is ignored.

Validation checks Draft 2020-12 schemas, declared defaults, all examples,
date-time formats, catalogue consistency, and negative regression cases. Schema IDs identify bundled
resources; validation does not fetch schemas from the internet.

CI runs these checks and uploads a `perfeng-contracts-0.2.0.tar.gz` candidate
bundle. That CI artifact is not a published stable release. Until a release
exists, integrations should pin the merged commit SHA, not a floating branch.

## Compatibility and migration

Read [compatibility](docs/compatibility.md),
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
Policy, raw-artifact, API, and analysis-decision contracts are subsequent work.
Missing statistical values mean unavailable, never zero.
Schema validation establishes structural validity, not scientific quality or
performance-gate readiness.
