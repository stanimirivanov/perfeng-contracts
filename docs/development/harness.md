# perfeng-contracts coding harness

## TL;DR

- Use the [documentation map](../README.md) to load only the policy and contract
  guidance relevant to the task.
- Run `make bootstrap` once when locks change, then use `make verify` as the
  deterministic, network-independent development loop.
- Run `make validate` before handoff; it adds current vulnerability and license
  evidence to verification.
- Contract generation drift and the Python semantic validators are the
  meaningful repository boundary checks; no application architecture gate is
  invented here.
- Report unavailable checks explicitly and never claim an unexecuted check
  passed.

## Purpose

The harness combines guidance read before editing with deterministic feedback
after each change. It keeps Effect source, generated JSON Schema, OpenAPI,
examples, rejection fixtures, bundle metadata and documentation coherent while
remaining self-contained for contributors and coding agents.

This inventory does not replace the root [Makefile](../../Makefile),
[CONTRIBUTING.md](../../CONTRIBUTING.md) or the contract
[engineering standards](engineering-standards.md).

## Cost and timing tiers

| Tier | Intended timing | Characteristics |
|:--|:--|:--|
| T0 — route | Before editing | Read-only routing through `AGENTS.md`, `CONTRIBUTING.md` and the documentation map. |
| T1 — inner loop | During editing | Focused validators and `make verify`; deterministic and offline after bootstrap. |
| T2 — acceptance | Before handoff | `make validate`, including current vulnerability and license data. |
| T3 — specialized | Release or consumer integration work | Candidate-bundle assembly, publication and consumer-specific conformance. |

Cost tiers describe feedback timing, not permission to skip an applicable
check. The constrained-environment protocol in CONTRIBUTING always applies.

## Command surface

| Command | What it establishes |
|:--|:--|
| `make bootstrap` | Locked Python and Node dependencies are available. |
| `make doctor` | The effective Git, uv, Python, Node, pnpm and Make toolchain is visible. |
| `make generate-contracts` | Checked-in JSON Schema is regenerated from authoritative Effect Schema. |
| `make fmt` | Repository-owned Python and TypeScript are formatted; inspect the diff. |
| `make docs-check` | Local links, TL;DR policy, ADR bookkeeping and templates satisfy mechanical policy. |
| `make check` | Generation drift, formatting, policy, locks, types and offline validators pass. |
| `make test` | TypeScript boundary tests and Python semantic tests pass. |
| `make verify` | Checks and tests pass without network after bootstrap. |
| `make vuln` | Locked Python and Node graphs are checked against current advisory data. |
| `make license` | Production Node dependencies satisfy the reviewed SPDX allowlist. |
| `make supply-chain` | Vulnerability and license sensors pass together. |
| `make validate` | The complete non-publishing acceptance aggregate passes. |

Candidate-bundle creation stays in the stable Linux validation job until it has
a deterministic cross-platform repository builder. It is not silently treated
as a stable release.

## Contract-specific feedback

`pnpm contracts:check` proves deterministic generation and exact source/artifact
agreement. The TypeScript tests exercise strict Effect decoding. The Python
validators prove language-neutral JSON Schema, OpenAPI and cross-document
semantics. These checks complement one another; none may be removed merely
because another accepts the same positive example.

The repository contains contract authoring and validation tools, not an
application runtime. A hexagonal package dependency matrix would therefore be a
false abstraction. Boundary enforcement belongs at source authority,
generation, compatibility and offline resolution.

## Feedback design

A recurring finding SHOULD become clearer canonical guidance, an early
deterministic sensor, a focused conformance fixture, or an explicit owned
exception when automation would be misleading. Checks MUST NOT rewrite
generated artifacts during validation, weaken a rejection case, fetch remote
schemas or report unavailable advisory data as healthy.

## CI mapping

The existing Linux `validate` job remains the stable status context and retains
candidate-bundle assembly. Linux verification exercises the
generation requirement. Supply-chain feedback runs separately because current
advisory data has different availability and failure characteristics.

GitHub Action references may use reviewed release tags or commit SHAs; the
repository policy validator does not prescribe one style. Contract checksums,
pinned consumer revisions and artifact identities remain immutable values.

## Maintaining the harness

Harness changes are normal reviewed changes. Update this guide, the
documentation map, Make targets and CI together whenever command ownership or
feedback timing changes. Review false positives, runtime, repeated suppressions
and escaped compatibility defects.
