# ADR-0011: Bind analysis publications to retained admission

- Status: Proposed
- Date: 2026-10-29
- Milestone: M01 — Local Performance Decision Loop
- Deciders: Repository owner and integration consumers (review pending)
- Supersedes: None
- Superseded by: None

## TL;DR

- Add a separate request-linked immutable analysis publication family.
- Bind native identities explicitly to retained authenticated admission evidence.
- Preserve existing contracts and independent outcomes without runtime activation.

## Decision and consequences

Candidate 0.25.0 adds performance-analysis/v1 using existing Effect, CloudEvents-style
envelopes, integration context, native identities and artifact patterns. No new
dependency is introduced. A separate schema avoids widening the existing closed
integration union. Prior native/API/schema generations keep their bytes and meaning.

Provider admission must retain the native mapping and approved baseline artifact;
consumers cannot reconstruct authority from current registry entries or labels.
The publication binds exact analysis bytes, while existing analysis/v1 preserves
quality/SLO/regression distinctions. Offline conformance never grants credentials,
fetch permission or approval. No endpoints, storage or release are implemented.

This is the shared prerequisite for Argus M09-PR9d2. Provider persistence/delivery
and consumer ingestion require separate reviewed PRs and pins before activation.
Joint contract review remains pending; verify fixtures, rejection cases, generation
drift and unchanged existing schemas/APIs before adoption.
