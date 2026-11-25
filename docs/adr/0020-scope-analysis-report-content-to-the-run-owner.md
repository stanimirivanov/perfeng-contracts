# ADR-0020: Scope Analysis Report content to the Run owner

- Status: Proposed
- Date: 2026-11-25
- Milestone: M05 — Operator Visibility and Diagnostics
- Deciders: Contracts, Control Plane and Environment owners
- Supersedes: None
- Superseded by: None

## TL;DR

- An operator can request their own Run's registered report by two identifiers.
- Reuse the original-byte transport and integrity requirements of ADR-0018.
- Preserve the service-authorized artifact and historical comparison operations.

## Decision

The local operator needs the exact retained report to verify a checkout SLO
observation. The existing artifact-content operation permits normalized results
and historical baseline evidence for authorized service readers. Restricting
that operation in place would change access for existing consumers.

Give the narrower operation a separate operation ID and route. Require direct
registration on the selected Run and check the original principal on every
request. Keep storage addressing private to the provider. An operator can rotate
a credential without changing ownership. A different operator needs their own
Run even when both belong to the same service.

Adopt the 1 MiB cap and verified octet-stream response of [ADR-0018](0018-read-authorized-original-evidence.md).
A provider must finish verifying the buffered object before it commits to a
successful response. Large registered reports therefore remain an explicit
unsupported case. A later expansion of the cap requires compatibility review.
The [report read profile](../run-evidence-reads.md#run-owned-analysis-report-content)
defines admission and failure behavior.
