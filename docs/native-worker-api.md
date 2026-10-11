# Native Worker API

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
- A lease includes a complete server-reviewed baseline Chromium execution
  recipe; the worker must not supply missing measurement settings from defaults.
- A read-only attempt inspection can support operator reconciliation after interruption, but
  neither local evidence nor a server snapshot restores lease authority.
- Current-slot discovery handles an unknown attempt ID without listing history;
  stop the old process and withdraw availability before manual recovery.
- Implementers must use the OpenAPI description and positive, rejection and
  HTTP fixtures under `api/native-worker/v2` as the conformance boundary.

The Native Worker API dispatches existing reviewed Playwright journeys to a
representative Windows laptop without exposing an inbound listener,
Kubernetes identity, permanent object-store credentials or caller-selected
commands. [ADR-0001](decisions/0001-native-windows-worker-protocol.md) owns the
architecture decision. This document explains the supported v2 behavior;
the self-contained OpenAPI document is authoritative for wire shape.

## API boundary

Native Worker API credentials have a different audience from user-facing Run
Management credentials. A deployment may serve both APIs from one process, but
it must authenticate and authorize them independently. The API has no enrollment,
credential issuance or rotation endpoint. Operators provision a distinct
revocable credential to each installation and the agent stores it in Windows
Credential Manager or an equivalent OS-protected store.

Every request uses the worker credential as an HTTPS bearer credential. The
authenticated principal is the worker identity. Request bodies therefore have
no `workerId`, principal, credential or token property. The narrower lease
capability is carried only in the documented header. Upload authorization is a
short-lived presigned URL plus a closed set of exact signed request headers in
the upload-grant response body. These values are delivery material only: they
do not belong in logs, evidence, diagnostics or persistent storage.

| Operation | Purpose | Success |
| --- | --- | --- |
| `reportWorkerPresence` | Report availability, bounded capabilities and immutable qualification evidence | `200` with the server interpretation |
| `acquireNativeLease` | Long-poll briefly for one compatible assignment | `200` plus `X-Perfeng-Lease`, or `204` plus `Retry-After` |
| `renewNativeLease` | Extend the lease and observe cancellation | `200` with authoritative server times |
| `releaseNativeLease` | Stop without claiming ordinary completion | idempotent `204` |
| `createNativeUploadGrant` | Request one bounded exact-object upload | `201` with a presigned `PUT` URL and exact signed headers |
| `registerNativeArtifact` | Verify uploaded bytes and register their immutable reference | `201` |
| `reportNativeTerminal` | Report completed or failed execution | `200`, including identical duplicate acknowledgement |
| `inspectNativeAttempt` | Observe one known attempt owned by the authenticated worker | `200` with ACTIVE, INACTIVE or TERMINAL, or indistinguishable `404` |
| `discoverNativeAttempt` | Observe recorded availability and this worker's single current measurement slot | `200` with NONE or FOUND, always `Cache-Control: no-store` |

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
infer one dimension from another. Native Worker v2 fixes browser measurement
capacity at exactly one so host contention does not silently weaken evidence
comparability.

The control plane may return work only when the authenticated worker is
available, authorized, currently qualified and compatible with the complete
assignment. The assigned catalogue test, workload, profile, browser,
diagnostic mode and execution artifact come from reviewed server policy. The
worker cannot substitute a repository revision, archive or arbitrary command.

Presence and acquisition require `protocolVersion: 2`; capabilities require
`runnerContract: 2`. A lease capability is valid only for this API generation.
The current contract supports the repository-owned `search` journey in
`baseline` mode, Chromium, and a source-checkout runner artifact. Trace,
memory, smoothness, branded browsers and release archives need separate
contract review before workers advertise those combinations.

## Reviewed execution recipe

The lease assignment includes the reviewed catalogue test, workload and
profile, SUT target, browser, diagnostic mode, execution artifact and artifact
plan. Its required `recipe` supplies journey ID, workload version and SHA-256,
cache and page-reuse policy, warm-up and measurement counts, qualified host
profile/version/fingerprint and evidence SHA-256, and headless/viewport/device
scale settings. Both artifact slots are required. The worker must not derive
missing fields from local defaults or accept an unsupported journey.

The projection to Playwright `RunnerConfiguration` is exact:

| Runner field | Reviewed lease source |
| --- | --- |
| `schemaVersion` | `2` |
| `runId`, `testId` | `runId`, `assignment.catalogueTestId` |
| `workload.id`, `.profile` | `assignment.workloadId`, `.profile` |
| `workload.version`, `.sha256` | `assignment.recipe.workloadVersion`, `.workloadSha256` |
| `scenario` | `assignment.recipe.scenario` |
| `diagnosticMode` | `assignment.diagnosticMode` (`baseline`) |
| `environment.profile.id`, `.version` | `assignment.recipe.environment.profileId`, `.profileVersion` |
| `environment.fingerprint` | `assignment.recipe.environment.fingerprint` |
| `target.baseUrl` | `assignment.target.baseUrl` |
| `browser` | `assignment.recipe.browserSettings` |

The worker must compare the recipe's host profile ID and evidence SHA-256 with
its current qualification evidence, and compare the assigned execution
artifact with its qualified runner identity. The SUT target environment ID is
separate from the Windows host profile. Capabilities must cover the assigned
browser, diagnostic mode and artifact kinds before browser launch. `journeyId`
selects repository-owned code, never a caller-supplied command. See
[ADR-0004](decisions/0004-version-native-worker-execution-recipes.md) for the
recipe decision and [ADR-0005](decisions/0005-retire-native-worker-v1.md) for
the supported-generation decision.

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
types, formats, maximum byte counts and required status. A format is the exact
registered data-contract name, including its generation; Native Worker v2 uses
`playwright-measurements/v2` and `raw-result/v2`. For a completed local file,
the worker computes exact size and SHA-256 and requests a grant for the
assigned slot. It does not send an object key. The control plane returns the
server-selected key, a short-lived S3 Signature Version 4 presigned `PUT` URL
and the exact headers the worker must reproduce. The URL query is a bearer
credential. The whole grant response must therefore be handled as sensitive
delivery material even though its non-secret identity fields are later stored.

The object-store URL path ends with the returned exact key:

```text
runs/{runId}/attempts/{attemptId}/{slot}
```

The closed `uploadHeaders` object contains lowercase canonical names for the
signed `content-type` and `x-amz-checksum-sha256` values. The worker sends those
values unchanged and must not add an alternative payload checksum or content
type. The signature also binds `host`; the HTTP client derives it from the
presigned URL rather than receiving it as an explicit header value. The signed
full-object checksum fixes the exact payload bytes. The provider or ingress may
apply an additional request-size ceiling, and registration independently
verifies the declared size and checksum.

The grant permits only the required `PUT`, exact key, declared digest and exact
size, expires no later than the execution lease, and grants no bucket listing,
reading, deletion or cross-Run access. An identical upload may be retried until
expiry; this is not an exactly-once guarantee. After upload, the worker
registers the grant, slot, size and digest. The server independently verifies
the stored object before returning an immutable reference. The worker cannot
choose the authoritative URI, and object-store acceptance alone never makes
uploaded bytes evidence.

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

## Read-only attempt inspection

An interrupted worker may hold a retained attempt directory but no in-memory lease capability.
`inspectNativeAttempt` accepts one exact Run/attempt pair using the worker-audience credential;
the caller cannot choose a worker identity. The server returns a consistent observation at its
reported `serverTime` and only for a record belonging to that authenticated worker:

- `TERMINAL` means a first terminal report was durably accepted; its accepted kind and resulting
  Run revision are supplied. It takes precedence over a matching retained lease row.
- `ACTIVE` means the matching v2 lease row was not released and had not expired at `serverTime`.
  Its lease ID and expiry are non-secret identifiers, not a replacement capability.
- `INACTIVE` means that matching row remains but was released or expired without an accepted
  terminal report. It does not identify the cause or prove that partial uploads are complete.
- `404 ATTEMPT_NOT_FOUND` covers both unknown and foreign-owned attempts. A superseded expired
  lease may no longer have a retained row and can also produce 404; callers must not interpret it
  as proof that the attempt never existed.

No result authorizes resuming execution, deleting local files or owner markers, or advertising
availability. An `ACTIVE` result may become stale immediately, and inspection supplies no lease
capability. Use current-slot discovery below when an acquisition response was
lost before the attempt ID became known. Automatic restart recovery remains
out of scope. See
[ADR-0006](decisions/0006-inspect-native-attempt-without-restoring-authority.md).

## Read-only current-slot discovery

`POST /native-worker/v2/attempts/discover` accepts only `protocolVersion: 2`.
The worker bearer principal scopes the lookup; no Run, attempt, worker, request
ID, time range, history cursor or lease capability can be supplied. Acquisition
is not made idempotent by this endpoint and its existing request/response shape
is unchanged.

The response includes `serverTime`, stored `availability`, and one closed state:

- `NONE`: no unreleased v2 lease owned by this worker has `expiresAt > serverTime`.
  Expiry exactly at `serverTime` is inactive. Expired or released leases and
  historical terminal reports are not listed. This does not prove that an
  earlier request failed, that no evidence exists, or that acquisition is safe.
- `FOUND`: exactly one such lease occupies the measurement slot. `slotExpiresAt`
  is its exclusive expiry. The nested `attempt` reuses the known-attempt
  inspection shape with exactly the same observation time. `ACTIVE` includes
  non-secret Run, attempt and lease identifiers, expiry and Run revision.
  `TERMINAL` takes precedence when that worker's first terminal report was
  accepted, even though the lease still occupies capacity. In that case the
  accepted kind, time and resulting Run revision are returned. INACTIVE is not
  a discovery result; use exact inspection for a retained known attempt.

`availability` reports the stored AVAILABLE, DRAINING or UNAVAILABLE intent,
not presence freshness, qualification, acquisition authorization or permission.
UNREPORTED means no presence record exists and is valid only with NONE. A
missing presence record alongside a current slot, multiple occupying slots or
inconsistent stored identities is a server integrity failure: fail closed with
500/503, not a truncated result or fabricated NONE. Do not leak foreign worker
existence through response bodies or error text. Every successful response has
`Cache-Control: no-store` and no lease-capability response header.

### Consistency and late acquisition

Discovery must serialize its observation with this worker's acquisition and
presence replacement. Read `serverTime` after any serialization wait, then
observe availability, occupying lease, Run revision and terminal acceptance
consistently. A stale pre-wait snapshot cannot prove NONE. Acquisitions must
recheck current availability before committing; one that observed AVAILABLE
earlier cannot commit from that stale observation after withdrawal. These are
consumer obligations, not properties that JSON Schema alone can verify.

For manual recovery, stop the old agent and its browser process tree, exclude
any other process using this worker identity, then report UNAVAILABLE through
the existing presence operation and obtain acknowledgement before discovery.
Do not rely on local wall-clock time or sleeping for `maxWaitSeconds` to prove
that a lost HTTP request can no longer commit. A prior acquisition that commits
before withdrawal is discoverable until release or expiry; an earlier request
that has not committed must not acquire after the acknowledged withdrawal.
Concurrent new AVAILABLE reports can invalidate this observation immediately.

If discovery finds ACTIVE, retain the owner marker/evidence and wait for the
server to observe expiry; do not renew, release, publish, complete or execute
without the original in-memory capability. If it finds TERMINAL, retain the
files and compare any known local attempt identity with exact inspection; the
slot may still occupy capacity. NONE after withdrawal only settles current
capacity. It never settles unknown historical acceptance or byte integrity.
Clearing an owner marker, archiving evidence and explicitly starting another
run require the separately implemented manual recovery procedure; no discovery
response is itself cleanup or acquisition permission. Unreported identity,
errors, mismatches or uncertain withdrawal fail closed and retain local state.

See [ADR-0007](decisions/0007-discover-native-worker-slot-without-restoring-authority.md).

## Errors, security and operational limits

All operations define structural, authentication, authorization, rate-limit,
internal and dependency errors. Lease-scoped mutations additionally expose
revision conflict and lost-lease outcomes. Error messages are bounded and must
not echo credentials, capabilities, private endpoint details, uploaded bytes or
untrusted diagnostic content.

Implementations must additionally:

- require TLS and validate the service identity;
- bind the bearer principal and lease capability before processing payloads;
- redact complete presigned URLs, query strings and signed upload headers from
  logs, traces, metrics, errors and crash reports;
- enforce request-size, collection-size, artifact-count and artifact-byte
  limits before expensive work;
- compare digests and identifiers exactly rather than normalizing evidence;
- stop execution when renewal cannot prove a current lease;
- revoke one worker without modifying its previously registered evidence; and
- emit telemetry using worker, Run, attempt and request identifiers, never
  authentication or grant material.

Checked-in valid payloads live under `api/native-worker/v2/examples`, matching
the Run Management API layout. Deliberately invalid payloads are isolated under
`api/native-worker/v2/rejections`, while `http-cases.json` composes the examples
into request and response exchanges. The fixtures use reserved `.invalid`
HTTPS endpoints, explicit fake lease capabilities, non-secret presigning
placeholders and synthetic identifiers. Validation is offline and rejects
remote schema references, request-selected identity, capacity above one,
invalid cancellation shapes, missing revision fences, worker-selected
locations, mismatched presigned upload material and incomplete terminal
reports.

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

Candidate bundle `0.21.0` retains only this v2 Native Worker API and adds
read-only current-slot discovery to OpenAPI `2.2.0`. Deploy the implementing
control plane before enabling discovery in the worker. Existing acquisition,
inspection and lease mutation payloads do not change, and discovery requires
no new data schema or evidence conversion. The control-plane batch must prove
worker isolation, withdrawal versus late acquisition, exclusive expiry,
terminal precedence, integrity failure and no mutation with live PostgreSQL
tests. The Playwright batch must prove process exclusion and conservative
manual reconciliation of retained files. Consumers
must move to one reviewed bundle revision and remove v1 routes and payload
handling in coordinated control-plane and Playwright changes. Do not deploy a
v2-only worker against a v1-only control plane or enable acquisition during a
mixed rollout. Native Worker v1 was never deployed, so there is no production
wire traffic or authoritative evidence to convert. Review dormant local v1
assignments before enabling execution; recreate them under the v2 recipe
rather than translating incomplete assignments. Run Management and the data
schema inventory are unchanged. See the [compatibility ledger](compatibility.md)
for historical candidate changes.
