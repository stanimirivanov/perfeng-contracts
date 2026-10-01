# perfeng-contracts dependency policy

## TL;DR

- Python and Node dependencies are contract-authoring and validation tools;
  consumers receive language-neutral artifacts, not these toolchains.
- `pyproject.toml`, `package.json` and their lockfiles declare and resolve the
  complete reproducible tool environment.
- `make verify` is offline after bootstrap; `make supply-chain` requires current
  registry and vulnerability data.
- Review license, maintenance, security, determinism and replacement cost
  before admitting a dependency.
- Keep dependency-only updates separate from contract semantic changes whenever
  practical.

## Dependency boundaries

Python has no product runtime dependency in this repository. Its development
group contains offline JSON Schema and OpenAPI validators plus quality tools.
The private Node package uses Effect as its contract-authoring runtime;
TypeScript, tsx and Biome remain development tools. None of these packages are a
runtime requirement for Go, Python, Rust, Java or other contract consumers.

The existing uv dependency group and npm dependency classes provide appropriate
separation. Do not introduce another language toolchain or isolated project
solely to imitate another repository's implementation.

## Admission criteria

A dependency MUST have a concrete current need, a maintained release, a license
compatible with the repository and candidate bundle, deterministic offline
behavior after bootstrap, and a proportionate replacement boundary. Prefer the
standard library for small repository policy checks when it avoids another
lasting tool dependency.

Validators and generators process untrusted repository content. Bound their
inputs and diagnostics, keep remote resolution disabled and cover important
failure semantics with fixtures.

## Locking and updates

- Change Python declarations and `uv.lock` together through `uv`.
- Change Node declarations and `pnpm-lock.yaml` together through pnpm.
- Never hand-edit a lockfile merely to obtain a preferred diff.
- Run `make bootstrap`, `make verify` and `make supply-chain` after an update.
- Keep dependency upgrades separate from compatibility changes unless they are
  inseparable for correctness or security.

Dependabot may propose grouped GitHub Actions updates. Python and pnpm 11
dependency updates remain manual, lockfile-aware workflows until hosted
updaters support the pinned toolchains reliably. Every proposal still requires
ordinary compatibility, generation and conformance review.

## Vulnerabilities and licenses

`uv audit --locked` checks the Python graph for supported Linux and Windows
targets. `pnpm audit` checks both authoring and development dependencies because
all execute in trusted CI. Findings require an explicit assessment of affected
versions, reachability, fix availability and exposure; exceptions require an
owner, rationale and review trigger.

The license sensor uses pnpm's installed dependency inventory and an explicit
SPDX allowlist for production Node dependencies. It does not claim that a
machine-readable identifier replaces legal review, and changes to the allowlist
require a focused policy review. Python license admission remains a human review
until a maintained pinned scanner with reliable metadata is selected.

## Constrained environments

Bootstrap and advisory queries may need network access. Verification uses
offline uv operation and installed pnpm dependencies after bootstrap. When
current advisory data or another required input is unavailable, report the
exact command as not run, the blocker, checks that passed and residual risk as
required by CONTRIBUTING.
