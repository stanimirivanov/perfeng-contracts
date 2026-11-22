# ADR-0010: Project safe performance catalog snapshots

- Status: Proposed
- Date: 2026-10-22
- Milestone: M09 — Perfeng integration
- Deciders: Repository owner and integration consumers (review pending)
- Supersedes: None
- Superseded by: None

## TL;DR

- Share authorized metadata, immutable references and exact supported selections.
- Require complete fresh snapshots before replacing consumer eligibility views.
- Preserve Perfeng admission authority and exclude executable/private configuration.

## Decision

Add performance-catalog/v1 using integration identities, explicit profile bindings
and baseline lifecycle. Publish one current revision per kind/issuer/ID so old
approved revisions cannot conceal retirement. Bind pages to one principal-scoped
snapshot with opaque cursors, counts and a canonical resource-array digest.
Use existing Effect generation and offline conformance tooling, with no dependency
addition. Consumers resolve no authority from labels or arbitrary URLs.

## Consequences

Candidate 0.24.0 is additive; existing contracts retain exact bytes and meaning.
Provider snapshot materialization and Argus atomic replacement remain M09-PR3/PR4.
Failed/incomplete refreshes cannot grant new execution eligibility. Historical
snapshots remain evidence, not current approval. Joint review is pending; this
contract change deploys no endpoints and publishes no release.
