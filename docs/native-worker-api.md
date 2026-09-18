# Native Worker API v1

## TL;DR

- This API is the machine-facing boundary between the control plane and a
  qualified interactive Windows worker; it is separate from Run Management.
- The worker makes outbound authenticated HTTPS requests and never chooses its
  server-side identity, a command, a target URL, or an object-store key.
- Capability, qualification, availability and authorization are distinct;
  only their server-approved intersection can acquire work.
- Execution is at least once through expiring leases fenced by worker, lease,
  attempt and expected Run revision.
- Artifact bytes go directly to object storage through short-lived exact-key
  grants; verified references are registered before the manifest is completed.
- Implementers must use the OpenAPI description and positive, rejection and
  HTTP fixtures under `api/native-worker/v1` as the conformance boundary.

The Native Worker API dispatches existing reviewed Playwright journeys to a
representative Windows laptop without exposing an inbound listener,
Kubernetes identity, permanent object-store credentials or caller-selected
commands. [ADR-0001](decisions/0001-native-windows-worker-protocol.md) owns the
architecture decision. This document explains the interoperable v1 behavior;
the self-contained OpenAPI document is authoritative for wire shape.

## API boundary

Native Worker API credentials have a different audience from user-facing Run
Management credentials. A deployment may serve both APIs from one process, but
it must authenticate and authorize them independently. V1 has no enrollment,
credential issuance or rotation endpoint. Operators provision a distinct
revocable credential to each installation and the agent stores it in Windows
Credential Manager or an equivalent OS-protected store.

Every request uses the worker credential as an HTTPS bearer credential. The
authenticated principal is the worker identity. Request bodies therefore have
no `workerId`, principal, credential or token property. Lease and upload
capabilities are narrower authorization material and are carried only in the
documented headers. None of these values belongs in logs, evidence, URLs,
diagnostics or persisted fixture data.

| Operation | Purpose | Success |
| --- | --- | --- |
| `reportWorkerPresence` | Report availability, bounded capabilities and immutable qualification evidence | `200` with the server interpretation |
| `acquireNativeLease` | Long-poll briefly for one compatible assignment | `200` plus `X-Perfeng-Lease`, or `204` plus `Retry-After` |
| `renewNativeLease` | Extend the lease and observe cancellation | `200` with authoritative server times |
| `releaseNativeLease` | Stop without claiming ordinary completion | idempotent `204` |
| `createNativeUploadGrant` | Request one bounded exact-object upload | `201` plus `X-Perfeng-Upload-Grant` |
| `registerNativeArtifact` | Verify uploaded bytes and register their immutable reference | `201` |
| `reportNativeTerminal` | Report completed or failed execution | `200`, including identical duplicate acknowledgement |

The API is outbound-pull and POST-only. `maxWaitSeconds` is capped at 30 and
server-provided heartbeat and retry intervals are bounded. A worker should add
jitter without exceeding the server's interval and should treat server time as
authoritative for leases and grants.

## Presence, capability and qualification

Presence reports four different concepts without collapsing them:

- **Capability** is an untrusted claim about tool, Windows architecture,
  browser families, runner contract, accepted execution artifacts, evidence
  kinds and diagnostic modes.
- **Qualification evidence** identifies the immutable
  `browser-environment/v1` evidence and reviewed runner provenance claimed by
  the installation. It is input to a server decision, not a worker verdict.
- **Availability** is the worker's current operational intent: available,
  draining or unavailable.
- **Authorization** is a server policy decision for the authenticated worker.

The presence response reports the server's qualification decision and
acquisition authorization independently. A worker can be healthy but stale,
capable but unauthorized, or qualified but draining. Implementations must not
infer one dimension from another. Native Worker v1 fixes browser measurement
capacity at exactly one so host contention does not silently weaken evidence
comparability.

The control plane may return work only when the authenticated worker is
available, authorized, currently qualified and compatible with the complete
assignment. The assigned catalogue test, workload, profile, browser,
diagnostic mode and execution artifact come from reviewed server policy. The
worker cannot substitute a repository revision, archive or arbitrary command.

## Lease and attempt fencing

A lease is an opaque, expiring capability bound to one authenticated worker,
Run and attempt. The acquisition response body provides identifiers,
authoritative timestamps, renewal timing, the reviewed assignment and the
bounded artifact plan. The response header provides the separate lease
capability. The worker must keep that capability in memory only as long as
needed and send it on each lease-scoped mutation.

Every renewal, release, upload request, artifact registration and terminal
report repeats the server-issued attempt identity and the Run revision observed
by the worker. The control plane conditionally mutates only the current attempt
at that revision. It returns `409` for a stale revision or conflicting duplicate
and `410` when the lease expired, was released or no longer represents the
current attempt. A stale worker cannot register artifacts or terminal state.

Renew before `expiresAt` using the server-provided interval and a monotonic
local deadline. Renewal may return `cancellationRequested: true` with a bounded
`stopBy` timestamp. The agent then stops the complete browser process tree,
releases the lease with `CANCELLATION_REQUESTED`, and does not report ordinary
completion. Network uncertainty and lease expiry allow the same Run to be
leased again, so consumers must implement at-least-once execution rather than
claim exactly once.

Release is idempotent for the same attempt and reason. A worker should release
when cancellation is observed, the local lease is lost, the interactive agent
is shutting down, or preparation fails before authoritative execution. A
release does not make partial artifacts authoritative.

## Artifact publication and terminal reporting

The lease contains an artifact plan with server-selected slots, kinds, media
types, formats, maximum byte counts and required status. For a completed local
file, the worker computes exact size and SHA-256 and requests a grant for the
assigned slot. It does not send an object key. The control plane returns safe
grant metadata in JSON and the opaque upload authorization in
`X-Perfeng-Upload-Grant`.

The response includes a credential-free object-store HTTPS endpoint whose path
maps to the returned exact key:

```text
runs/{runId}/attempts/{attemptId}/{slot}
```

The grant permits only the required `PUT`, exact key, declared digest and
bounded size, expires no later than the execution lease, and grants no bucket
listing, deletion or cross-Run access. After upload, the worker registers the
grant, slot, size and digest. The server verifies the object before returning
an immutable reference. The worker cannot choose the authoritative URI.

Required evidence is registered first and the manifest is registered last.
Only then may `COMPLETED` name the registered manifest artifact. This ordering
prevents partial upload from appearing complete. `FAILED` instead carries a
bounded machine classification, human-safe message and retryability hint.
Cancellation uses release semantics rather than masquerading as failure or
completion.

An identical repeated terminal request receives `ALREADY_ACCEPTED` with the
same attempt and resulting Run revision. A different terminal claim for an
accepted attempt is a duplicate conflict. This makes uncertain HTTP responses
safe to retry without weakening attempt fencing.

## Errors, security and operational limits

All operations define structural, authentication, authorization, rate-limit,
internal and dependency errors. Lease-scoped mutations additionally expose
revision conflict and lost-lease outcomes. Error messages are bounded and must
not echo credentials, capabilities, private endpoint details, uploaded bytes or
untrusted diagnostic content.

Implementations must additionally:

- require TLS and validate the service identity;
- bind the bearer principal and lease capability before processing payloads;
- enforce request-size, collection-size, artifact-count and artifact-byte
  limits before expensive work;
- compare digests and identifiers exactly rather than normalizing evidence;
- stop execution when renewal cannot prove a current lease;
- revoke one worker without modifying its previously registered evidence; and
- emit telemetry using worker, Run, attempt and request identifiers, never
  authentication or grant material.

The checked-in fixtures use reserved `.invalid` HTTPS endpoints, explicit fake
header capabilities and synthetic identifiers. Validation is offline and
rejects remote schema references, request-selected identity, capacity above
one, invalid cancellation shapes, missing revision fences, worker-selected
locations and incomplete terminal reports.

## Consumer rollout

`perfeng-control-plane` and `perfeng-playwright` must pin the same reviewed
contract-bundle revision. The control plane implements authentication,
qualification policy, matching, leases, fencing, cancellation and object-store
verification. The Playwright repository implements the interactive per-user
agent and maps existing qualification, capture, diagnostics and provenance
receipts to the assigned attempt. `perfeng-environment` may provision local
connectivity and identity, but does not own the Windows process or commit its
credential. Analysis consumes only registered immutable evidence and remains
independent of this transport.

This additive API does not change Run Management or any existing data schema.
Strict bundle readers must recognize the second API inventory entry before
moving from bundle 0.14.0 to 0.15.0. There is no conversion of old local
captures into leased attempts; new authoritative evidence begins with a v1
lease and attempt identity.
