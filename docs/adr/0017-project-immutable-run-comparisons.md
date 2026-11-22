# ADR-0017: Project immutable Run comparisons from retained evidence

- Status: Proposed
- Date: 2026-11-12
- Milestone: M05 — Operator Visibility and Diagnostics
- Deciders: Repository owner and control-plane/Console consumers
- Supersedes: None
- Superseded by: None

## TL;DR

- Add an exact authenticated read without changing existing lifecycle or verdict schemas.
- Freeze the available historical comparison and separate evidence availability.
- Reuse canonical analysis/publication schemas and independently verified bindings.

## Decision and consequences

M05-PR46 introduces Run API 0.6.0 in candidate bundle 0.29.0. Follow the normative
[comparison contract](../run-comparison.md). The immutable native request binds
candidate/suite/profile/policy selections; report-time native association binds
the exact baseline version and artifact. Reuse AnalysisV1 and optional original
PerformanceAnalysisV1 instead of designing a second evaluation/verdict model.
Generate the evidence component from Effect into the split Run source and check
its exact output alongside existing generation. The closed HTTP envelope remains
authored under the existing Run OpenAPI exception.

Directions are the minimal missing presentation field: copy them by rule ID from
verified frozen policy, with null for an unconfigured regression section. Do not
infer direction from metric names. Compare exact report/policy bytes and retained
identity relationships; semantic conformance validates but never rewrites outcomes.

Reject rebuilding from current catalog/baseline state, returning a mutable current
Run snapshot as comparison authority, and treating missing evidence as PASS/FAIL.
An original inconclusive report can be available. INCOMPLETE/INACCESSIBLE bodies
carry no evidence or verdict. Authorize Run and all evidence before disclosure;
hidden and unknown references share INACCESSIBLE, operational faults use 503.

## Compatibility and migration

Existing payloads, routes and semantic meaning are preserved. The new response
is bounded to 2 MiB with at most 1,000 rules and requires provider opt-in.
AVAILABLE has no reader/today's-approval fields: two authorized actors see the
same retained content. Optional publication correlation is frozen too; late
correlation cannot silently replace a previously available response. Availability
observations may change as access/retention changes, without rewriting evidence.

Producer rollout belongs to PR47/48, followed by consumer pins; contracts-only
verification cannot prove live authorization or historical retention. No stable
release or runtime activation occurs. Revert consumer adoption while retaining
all frozen bindings and artifacts. Fixtures and adversarial substitutions cover
request, Run, policy, baseline, artifact, values/units, direction and publication.
