# perfeng-contracts documentation map

## TL;DR

- Start with [CONTRIBUTING.md](../CONTRIBUTING.md) for workflow policy, then
  use this page to load only the contract sources relevant to the task.
- Effect Schema is authoritative for data contracts; generated JSON Schema is
  the language-neutral consumer boundary. OpenAPI remains explicitly
  hand-authored.
- Compatibility, examples, rejection fixtures and consumer migration guidance
  change together.
- Update this map when a canonical source moves or a recurring task lacks a
  clear route.

## Route by task

| Task or changed area | Read before changing it | Verify or consult as needed |
|:--|:--|:--|
| Contributor workflow, issue scope or completion report | [CONTRIBUTING.md](../CONTRIBUTING.md) | [Agent entry point](../AGENTS.md) |
| Effect Schema source or generated JSON Schema | [Contract engineering standards](development/engineering-standards.md), [ADR-0002](decisions/0002-use-effect-schema-at-contract-boundaries.md) | Root [README](../README.md), `pnpm contracts:check` |
| Compatibility, generations or consumer migration | [Compatibility guide](compatibility.md), [schema versioning](architecture/schema-versioning.md) | Affected producers, consumers and ADRs |
| Run Management API | [Run Management API guide](run-management-api.md) | API fixtures and offline validator |
| Native Worker API or native artifact upload | [Native Worker API guide](native-worker-api.md), relevant [ADRs](decisions/README.md) | API fixtures, rejection cases and HTTP cases |
| Native Worker v2 baseline recipe | [Native Worker API v2 candidate](native-worker-api-v2.md), [ADR-0004](decisions/0004-version-native-worker-execution-recipes.md) | v2 OpenAPI, examples, rejection and HTTP cases |
| Workloads, catalogues or metric naming | [Workloads and catalogues](workloads-and-catalogues.md), [metric naming](architecture/metric-naming.md) | Registry, examples and semantic tests |
| Artifact, result, browser or policy contracts | [Artifact and result transport](artifact-and-result-transport.md), [browser diagnostics](browser-diagnostics.md), [Playwright measurements](playwright-measurements.md), [performance policies](performance-policies.md) | Contract-specific fixtures and tests |
| Build, CI, repository policy or developer experience | [Harness guide](development/harness.md) | [Dependency policy](development/dependency-policy.md), `make docs-check`, `make verify` |
| Dependency admission, updates, licensing or vulnerabilities | [Dependency policy](development/dependency-policy.md) | [Security policy](../SECURITY.md), `make supply-chain` |
| Durable compatibility, ownership or security decision | [ADR index](decisions/README.md) | Affected consumer migration guidance |
| Vulnerability reporting | [Security policy](../SECURITY.md) | Relevant trust-boundary documentation |

## Canonical collections

- [Development](development/) contains engineering, harness and dependency
  policy.
- [Architecture](architecture/) records contract naming and versioning rules.
- [Decisions](decisions/README.md) records durable choices and their lifecycle.
- The root [README](../README.md) inventories published contract artifacts and
  exact validation commands.
- [Security](../SECURITY.md) defines vulnerability reporting and contribution
  expectations.

## Keeping the map useful

A change MUST update this page when it adds, renames, moves or removes a
canonical source or creates a recurring task without a clear route. Keep this
page focused on routing rather than duplicating contract meaning.
`make docs-check` validates local links and documentation structure; semantic
accuracy and consumer impact still require review.
