# ADR-0019: Attribute source-Run reruns and recover immutable receipts

- Status: Proposed
- Date: 2026-11-13
- Milestone: M05 — Operator Visibility and Diagnostics
- Deciders: Repository owner and control-plane/Console consumers
- Supersedes: None
- Superseded by: None

## TL;DR

- M05-PR49 / issue #115 specifies rerun POST and exact actor-scoped recovery GET.
- Preserve the original report-time selection and independently verified attribution.
- Separate acceptance evidence from execution success and durable provider qualification.

## Decision and consequences

Follow the normative [rerun contract](../run-reruns.md). Use a new operation with
a closed source-report pin and audit reason instead of overloading legacy
CreateRun or letting the browser author a new selection/identity. Reuse existing
CreateRun, VerifiedActor, ScopedIdentity and canonical generated native-binding
schemas; Run's documented hand-authored OpenAPI exception owns the HTTP envelopes.
No dependency or additional schema family is needed.

Exact GET uses the source plus originating verified actor and idempotency key.
This permits lost-response recovery without another mutation, including after
rerun permission is revoked while read permission remains. Keep original caller
attribution when a renewed delegated client reads a receipt. This first contract
does not let other engineers browse one another's audit receipts; a future
service audit-search API needs its own permission and review.

Reject retrying with a new key after a timeout, recomputing current selection,
claiming a receipt proves dispatch compliance and allowing a BFF bearer to name
a human. Retain a compact sealed key tombstone after receipt retirement: this
adds persistence/retention cost, but prevents ambiguous late retry from silently
creating a second execution. Existing CreateRun key expiry rules do not change.

Trade-offs: rerun requires a complete source comparison; a failed Run with no
retained report is not silently re-created through this operation. It returns an
explicit validation outcome. The fixed 64 KiB receipt cap and actor-only recovery
are deliberately narrow; broader recovery/audit discovery needs later contracts.
Provider issuer admission, transactions, real concurrency and execution fencing
remain PR58/50/59/51 gates. Roll out providers before consumers and disable
consumer entry points first on rollback while retaining accepted evidence.
