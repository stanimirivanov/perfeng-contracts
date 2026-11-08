# ADR-0015: Distribute immutable contract artifacts

- Status: Proposed
- Date: 2026-11-08
- Milestone: M06 — Production Readiness
- Deciders: Repository owner
- Supersedes: None
- Superseded by: None

## TL;DR

- Keep Git authoritative and publish exact-byte contract selections.
- Require independently verified provenance for promotion and adoption.
- Qualify the Kubernetes evidence tracer before expanding to other consumers.

## Context

Consumers obtain and verify selected snapshots independently. Reproducing a
selection requires exact historical bytes and the files used with them.
A provider version string alone cannot identify those bytes.

## Decision

Use immutable artifacts with one provider revision per manifest. Distinguish
input selections, test candidates and promoted releases. Consumers pin and
verify the exact artifact before materializing a local projection. Adopt the
[distribution policy](../development/contract-distribution.md) for provenance,
retention, withdrawal and rollback.

## Alternatives and consequences

Manual snapshot assembly uses fewer tools but leaves recovery and transfer
procedures specific to each consumer. A live registry adds a service and must
first pass corpus and exact-byte qualification. Artifact distribution adds
publication, verification and retention work while preserving offline runtime
validation and independent consumer adoption.

## Compatibility and validation

The metadata is additive. SR-1 tests the manifest shape and defines the tracer
selection. Later tasks must verify publication, recovery and consumer parity
before changing update authority. This is preparatory release work for M06.
