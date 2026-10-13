# Architecture decision records

## TL;DR

- Use an ADR for durable decisions affecting contract meaning, compatibility,
  security, ownership or cross-component behavior.
- Number ADRs sequentially and never reuse a number.
- Allocate from fresh repository state and renumber concurrent collisions.
- Accepted ADRs are historical records; supersede rather than rewrite them.
- Record alternatives, consequences, migration and validation.

## When an ADR is required

Create an ADR when a decision materially affects public contract meaning,
compatibility or generation strategy, schema/API foundations, security or trust
boundaries, repository ownership, release composition, or cross-component
behavior. Cheap local validator implementation choices do not need an ADR.

## Naming and lifecycle

Use a four-digit sequence and short kebab-case name:

```text
0001-select-contract-versioning-strategy.md
```

Statuses are Proposed, Accepted, Rejected, Deprecated or Superseded. A
superseded ADR links to its replacement. Do not rewrite an accepted decision or
its consequences to make history appear cleaner.

Add every ADR to the index. Immediately before creating one, refresh the branch
as the workflow allows and inspect this index and directory. Allocate the lowest
unused four-digit number. A filename does not reserve the number outside its
proposed change.

If concurrent work uses the same number, refresh the branch, rename the later
ADR to the next available number, and update its title, index and references.
Treat this as renumbering, not a content merge. Published ADR numbers remain
immutable.

## Template

```markdown
# ADR-NNNN: Decision title

- Status: Proposed
- Date: YYYY-MM-DD
- Milestone: MNN — Outcome
- Deciders:
- Supersedes:
- Superseded by:

## Context

What forces a decision now? Include compatibility and consumer constraints.

## Decision

State the decision and scope precisely.

## Alternatives considered

### Alternative

- Benefits:
- Costs and risks:
- Reason not selected:

## Consequences

### Positive

### Negative

### Neutral or follow-up

## Compatibility and migration

## Security and operations

## Validation

How will assumptions and consequences be verified?
```

## Index

| ADR | Status | Decision |
|:--|:--|:--|
| [0001](0001-native-windows-worker-protocol.md) | Accepted | Use a separate outbound, leased native Windows worker protocol with pre-provisioned identity and scoped direct artifact upload. |
| [0002](0002-use-effect-schema-at-contract-boundaries.md) | Accepted | Author data contracts with Effect Schema while retaining generated Draft 2020-12 JSON Schema as the language-neutral boundary. |
| [0003](0003-use-s3-presigned-put-for-native-artifacts.md) | Accepted | Use short-lived S3 SigV4 presigned PUT requests for direct native artifact upload. |
| [0004](0004-version-native-worker-execution-recipes.md) | Accepted | Version complete server-reviewed Native Worker execution recipes before enabling browser leases; coexistence superseded by 0005. |
| [0005](0005-retire-native-worker-v1.md) | Accepted | Retire the never-deployed Native Worker v1 candidate and retain v2 as the sole supported generation. |
| [0006](0006-inspect-native-attempt-without-restoring-authority.md) | Proposed | Add worker-scoped read-only attempt inspection without recovering lease authority. |
| [0007](0007-discover-native-worker-slot-without-restoring-authority.md) | Proposed | Discover the authenticated worker's current measurement slot after uncertain acquisition without restoring authority or enumerating history. |
| [0008](0008-separate-kubernetes-benchmark-evidence.md) | Proposed | Admit Kubernetes benchmarks in catalogue v2 and separate stable comparison identity from preflight and Run observation evidence. |
