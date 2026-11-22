# ADR-0008: Separate Kubernetes benchmark identity and observation evidence

- Status: Proposed
- Date: 2026-10-13
- Milestone: M04 — Kubernetes Benchmark Decision Loop
- Deciders: Repository owner
- Supersedes: None
- Superseded by: None

## TL;DR

- Admit kube-burner in catalogue v2 without broadening catalogue v1.
- Add one Effect-authored evidence contract for preflight and Run capture.
- Preserve stable environment descriptors while retaining transient observations separately.
- Unknown capture data is not zero; qualification is not execution or approval authority.

## Context

Kube-burner workload and raw-result provenance already exist, but catalogue tool
admission excludes it and the analysis reader currently accepts archives only.
The environment descriptor records comparison characteristics, not temporally
scoped node pressure or usage. Adding observations directly to it would change
historical shapes and risk making changing load part of stable baseline identity.

## Decision

Extend only catalogue v2's tool union and admit kube-burner OCI/archive execution.
Add `kubernetes-benchmark-evidence/v1` with distinct preflight/measurement scopes,
profile purpose and exact policy/environment identities, cluster incarnation,
bounded node observations and timestamped pressure/usage samples. Retain six
required PASS/FAIL/UNKNOWN checks with failure-first summary precedence.

Keep environment v1 and existing result/baseline/API shapes unchanged. Preserve
the separation of schema validation, observable evidence consistency, trusted
profile evaluation, dispatch authorization, statistical quality and explicit
baseline approval. The initial candidate is the workload's real image/configuration;
cluster upgrades are not silently exempted from compatibility checks.

## Alternatives considered

- Broaden the shared catalogue tool definition: accidentally changes v1; rejected.
- Add transient measurements to environment v1: changes a published closed
  shape and comparison identity; rejected in favor of separate evidence.
- Use untyped metadata or readiness alone: cannot distinguish missing metrics,
  Run scope or contradictory outcomes reliably; rejected.
- Add new Run/result generations: existing transport can reference raw evidence;
  unnecessary for this boundary and therefore excluded.

## Consequences

One additional data contract and strict catalogue readers require coordinated
consumer adoption. Captures are portable without a new API or runtime dependency.
The schema does not replace the producer's trusted profile evaluation or prove
host isolation, provenance or scientific quality. A local integration cohort
remains distinct from a performance-comparison cohort.

## Compatibility and migration

Candidate bundle 0.22.0 adds the contract and extends catalogue v2 only. Retain
old bundle revisions and unchanged historical schemas. Consumers explicitly
implement admission, OCI analysis and evidence verification before promoting
the new Kubernetes runtime. No payload conversion or evidence rewriting occurs.

## Security and operations

Validation is offline. Examples are synthetic and contain no credentials or
private endpoints. Evidence is never a lease, target reservation or cleanup
capability. Runtime observation, storage, publication and deployment belong to
the component repositories. Rollback repins the previous bundle and retains data.

## Validation

Strict Effect/generated-schema positive and negative cases, deterministic
generation, unchanged legacy admission, temporal/node conformance and context
binding tests run through `make verify`; `make validate` adds supply-chain gates.
