# ADR-0014: Split API authoring and review semantic changes

- Status: Proposed
- Date: 2026-11-07
- Milestone: M05 — Operator Visibility and Diagnostics
- Deciders: Repository owner
- Supersedes: OpenAPI authoring organization in ADR-0002 for Run and Native APIs
- Superseded by:

## TL;DR

- Author Run and Native APIs as separately owned path/component fragments.
- Retain Effect-authoritative Integration data definitions and generate its fragments.
- Continue publishing language-neutral bundled OpenAPI at its existing paths.
- Review semantic receipts and conformance evidence alongside source diffs.
- Qualify split/bundle tooling before moving existing source ownership.

## Context

Large generated artifacts hide small API changes and concentrate merge conflicts.
The same distribution format does not require one authored file. The Go provider
also relies on component names and reference locations; wire-language equivalence
alone cannot prove loader compatibility.

## Decision

Introduce an offline API review receipt. It records operation identities, schema
keywords, changed JSON pointers, prior/candidate canonical hashes and affected
request/response directions. A required request field or removed response field
is breaking. Removing a request enum value or adding a response enum value is
breaking for callers with closed assumptions. Other schema changes require review.
Descriptions may be reported as documentation changes. This conservative classifier
supplements fixtures and cannot prove arbitrary schema equivalence.

Run Management and Native Worker will use reviewed root/path/component sources.
Integration schemas remain authored in Effect under contracts/source; endpoint
metadata may be organized into coherent resource groups. Generated fragments never
become a second independently authored schema source.

A future exact Redocly pin must prove deterministic offline behavior, local input
closure and explicit configuration. Reject symlinks, escaping/remote references,
component collisions and implicit decorators or overlays. Preserve the existing
published OpenAPI locations and Go loader root/reference identities. Release
archive inventory changes require explicit review because the existing workflow
archives the entire api tree.

Two disjoint operation edits and a shared-component edit must be merged in both
orders and regenerated against a clean combined source. A compact receipt must
identify the affected operations; generated-diff hiding cannot replace that gate.
Provider and consumer pin adoption remain independent reviewed changes.

## Alternatives and consequences

Keeping authored monoliths leaves shared-file contention. Independently editing
generated Integration YAML would duplicate Effect schema ownership. Switching the
Go provider to a generated TypeScript server changes runtime architecture and is
outside this authoring migration.

Split source introduces more files and a bundling dependency. Admission, fixtures,
source provenance and deterministic output checks must justify that cost. This ADR
does not approve an Effect4 consumer replacement or a new runtime validator.

## References

- [ADR-0002](0002-use-effect-schema-at-contract-boundaries.md)
- [Compatibility](../compatibility.md)
- [Redocly split](https://redocly.com/docs/cli/commands/split)
- [Redocly bundle](https://redocly.com/docs/cli/commands/bundle)
