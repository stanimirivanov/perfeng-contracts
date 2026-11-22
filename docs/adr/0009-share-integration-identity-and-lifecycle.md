# ADR-0009: Share integration identity and request lifecycle contracts

- Status: Proposed
- Date: 2026-10-22
- Milestone: M09 — Perfeng integration
- Deciders: Repository owner and integration consumers (review pending)
- Supersedes: None
- Superseded by: None

## TL;DR

- Define the Argus/Perfeng integration boundary in perfeng-contracts.
- Generate language-neutral schemas and OpenAPI from existing Effect tooling.
- Preserve native run semantics and separate transport completion from quality.

## Context

Argus and Perfeng use different Effect generations. Direct TypeScript imports
would couple their toolchains. Existing native run IDs and transient idempotency
do not provide durable cross-service request, attempt and provenance identity.

## Decision

Add performance-integration/v1 with issuer-scoped immutable selection references,
CloudEvents identity and complete request context echoed by replies. Preserve
distinct request, attempt, run and event identities. Define admission, retries,
monotonic lifecycle snapshots and cancellation independently of runtime storage.
Keep schema components generated; use existing offline Python tooling for
relational conformance. No broker, SDK or new dependency is necessary.

## Consequences

Candidate bundle 0.23.0 is additive. Existing native APIs and schemas remain
unchanged. Consumers pin published artifacts and implement authenticated scope,
reference resolution, durable mappings and cancellation races in later M09 PRs.
Schemas cannot establish external provenance or authorize execution. Joint
approval remains pending human review; runtime availability is not claimed.
