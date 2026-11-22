# ADR-0006: Inspect a Native Worker attempt without restoring authority

- Status: Proposed
- Date: 2026-10-08
- Milestone: M03 — Native Browser Decision Loop
- Deciders: Project owner and affected consumer maintainers
- Supersedes: None
- Superseded by: None

## TL;DR

- Let an authenticated worker inspect one known Run and attempt after local interruption.
- Return a worker-scoped, read-only snapshot: ACTIVE, INACTIVE or TERMINAL.
- Do not return a lease capability or turn any response into permission to resume, delete evidence or acquire more work.
- Make unknown and foreign-owned attempts indistinguishable to the caller.
- Keep uncertain acquisition without a known attempt ID and unattended restart recovery out of scope.

## Context

The Playwright worker retains local attempt files and an owner marker after uncertain acquisition,
publication or terminal reporting. Its local verifier can establish that measurement bytes match a
runner receipt, but local files cannot reveal the control plane's accepted terminal state or
whether the lease is still current. The existing renewal and terminal operations require an
in-memory lease capability, which must not be persisted merely to make restart easier. The
user-facing Run API has a different credential audience and does not identify the worker's
attempt. Operators need a narrowly scoped server observation before deciding what to retain or
investigate further.

## Decision

Add `POST /native-worker/v2/attempts/inspect` under the worker bearer audience. The request names
one `runId` and `attemptId`, fixes `protocolVersion` at 2, and cannot select a worker. The server
uses the authenticated worker principal and observes one consistent snapshot:

- `TERMINAL` if this worker's attempt has a durably accepted first terminal report, even if its
  lease row remains. The response includes the accepted kind, resulting Run revision and time.
- `ACTIVE` if the matching v2 lease belongs to this worker and is neither released nor expired at
  `serverTime`. The response includes the lease ID, expiry and observed Run revision, but no
  capability. It may be stale immediately after delivery.
- `INACTIVE` if the matching retained v2 lease row belongs to this worker but is released or
  expired and no accepted terminal report exists. It does not explain why the attempt stopped.
- `404 ATTEMPT_NOT_FOUND` if no matching retained record is available to this worker. The same
  response covers nonexistent and foreign-owned attempts. An overwritten expired lease may also
  become unobservable and return 404.

The endpoint does not mutate worker presence, lease, Run, artifact or terminal state. The result
is evidence for operator reconciliation only. It does not restore the lease capability, permit an
old process to continue, prove that object-store bytes were registered, authorize file or marker
deletion, or authorize another acquisition. Concurrent process exclusion, retention policy and
recovery of an acquisition whose response was lost before its attempt ID became known remain
separate work.

## Alternatives considered

### Persist the lease capability locally and retry existing mutations

- Benefits: The worker could attempt a direct retry after restart.
- Costs and risks: A durable bearer capability expands theft and stale-process risk; a recovered
  token still cannot prove current authority after server-side expiry or reassignment.
- Reason not selected: A read-only observation has a smaller trust boundary.

### Use the user-facing Run Management API

- Benefits: Avoids a new worker operation.
- Costs and risks: Requires a different credential audience and does not expose worker-scoped
  attempt identity or exact terminal acceptance.
- Reason not selected: It cannot settle the question the retained spool raises.

### List all attempts for a worker

- Benefits: Could diagnose an acquisition whose response was lost before the worker learned its
  attempt ID.
- Costs and risks: Adds enumeration, pagination, retention and larger disclosure semantics.
- Reason not selected: The known retained-attempt case is bounded; unknown acquisition needs a
  separate, reviewed single-worker recovery protocol.

## Consequences

### Positive

- A worker can compare one retained Run/attempt with authoritative server records without using
  its user-facing credential or recovering a lease capability.
- Terminal precedence and indistinguishable 404 responses make the interpretation explicit.

### Negative

- The control plane needs a worker-scoped read across current leases and accepted terminal
  reports, with an internally consistent server timestamp.
- A point-in-time response is not a lock. Operators still need an explicit process and retention
  procedure before clearing local state.

### Neutral or follow-up

- `perfeng-playwright` may add a read-only transport after the control plane implements this
  operation. Unattended availability remains disabled until unknown acquisition, single-process
  exclusion and retained-evidence policy are addressed.

## Compatibility and migration

The operation is additive within Native Worker API v2, whose OpenAPI version advances to 2.1.0
in candidate bundle 0.20.0. Existing v2 operation shapes remain unchanged. Strict clients must
explicitly accept the new operation and error code. Deploy the implementing control plane before
pinning a worker to this bundle; older workers remain on their reviewed bundle and do not call it.
No persisted evidence is rewritten and no v1 Native Worker support returns.

## Security and operations

Require the worker bearer credential, bind every lookup to that worker, and use one bounded
request. Do not return capability hashes, capability plaintext, upload grants, object keys,
artifact bytes or target URLs. Redact internal existence differences from 404 messages and
telemetry. A failed or ambiguous inspection must leave retained evidence and owner markers
untouched. Rollback removes use of the new operation, not historical records.

## Validation

Offline OpenAPI, positive, rejection and HTTP fixtures cover all three response states, the
indistinguishable 404, worker-selected identity rejection, closed response shapes, identity
echoes and server-time ordering. Consumer implementations must add storage and HTTP tests for
worker scoping, terminal precedence, expiry races and no mutation.
