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
