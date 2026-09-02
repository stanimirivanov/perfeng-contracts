# perfeng-contracts

Language-neutral performance engineering contracts, extracted from
`performance-platform`. This first PR implements the existing-schema portion
of proposal phase 1 (sections 29-32 and 78). It does not complete phase 1.

## Contents

| Contract | Schema | Purpose |
| --- | --- | --- |
| `candidate/v1` | [candidate](schemas/candidate/v1/candidate.schema.json) | Software identity |
| `environment/v1` | [environment](schemas/environment/v1/environment.schema.json) | Standalone environment descriptor |
| `run/v1` | [run metadata](schemas/run/v1/run-metadata.schema.json) | Execution identity, phases, and context |
| `result/v1` | [test result](schemas/result/v1/test-result.schema.json) | One normalized metric record |

[contracts.json](contracts.json) maps schemas to executable examples and records
the bundle version. The normalized-result example is an array of metric
records; each element is validated separately. This PR does not define an
array envelope for transport.

## Validate

Use Python 3.12 or later for development checks. Python is test tooling only;
consumers in Go, TypeScript, and Python use the same JSON schemas.

```sh
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/validate.py
python -m unittest discover -s tests -v
```

Validation checks Draft 2020-12 schemas, declared defaults, all examples,
date-time formats, and negative regression cases. Schema IDs identify bundled
resources; validation does not fetch schemas from the internet.

CI runs these checks and uploads a `perfeng-contracts-0.1.0.tar.gz` candidate
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

Workload, catalogue, policy, raw-artifact, API, and analysis-decision contracts
are subsequent PRs. Missing statistical values mean unavailable, never zero.
Schema validation establishes structural validity, not scientific quality or
performance-gate readiness.

## Pull request handoff

The local feature branch is `codex/contracts-foundation`. The extracted history
is merged with `--no-commit`, so review and commit all changes to finish that
merge. These commands are instructions for the repository owner:

```sh
git add .
git commit -m "Extract performance contracts and add validation"
git push -u origin codex/contracts-foundation
```

Open a PR against `main` using [the issue text](docs/issues/001-contract-foundation.md).
Use GitHub's **Create a merge commit** option for this extraction PR. Squashing
would discard the imported ancestry. Do not push the temporary
`codex/contracts-source-history` branch separately.

The next steps are listed in [the implementation sequence](docs/implementation-sequence.md).
