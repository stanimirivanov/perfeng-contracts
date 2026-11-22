# ADR-0018: Read authorized original Run evidence by retained identity

- Status: Proposed
- Date: 2026-11-13
- Milestone: M05 — Operator Visibility and Diagnostics
- Deciders: Repository owner and control-plane/Console consumers
- Supersedes: None
- Superseded by: None

## TL;DR

- Add exact artifact and report-used policy byte reads in M05-PR25 / issue #113.
- Preserve original bytes, current service authority and immutable historical binding.
- Keep URL proxying, general artifact downloads and provider implementation out of scope.

## Decision and consequences

Follow the normative [evidence read profile](../run-evidence-reads.md).
Use identifier-only public operations with a 1 MiB verified original-body limit,
RFC 9530 Content-Digest and explicit identity headers. Octet-stream transport
avoids accidental JSON reserialization before hashing; client byte/header adapters
need separate conformance admission. Do not infer access from a frozen comparison:
authorize the selected Run and each evidence-owning resource on every read.

Permit the exact historical baseline association for comparison display, with its
owning Run identified separately. Policy retrieval uses retained report-time proof,
not merely the requested policy or latest catalog state. Do not extend the native
Artifact kind enum to match the separate publication descriptor's analysis kind.

Reject returning signed storage URLs, automatic redirects, browser storage access,
reconstructing policy JSON and a generic proxy. They weaken scope or immutable-byte
identity. A JSON/base64 envelope adds copies and an unnecessary second wire format.
The fixed cap may reject unusually large valid reports: return explicit failure,
never truncate; a later version can review a larger bound or streaming protocol.

This is an additive candidate contract, not a live feature claim. No new dependency
or schema family is needed. Provider admission must prove current resource rights,
revocation, bounded I/O and failure mapping before consumers enable these reads.
