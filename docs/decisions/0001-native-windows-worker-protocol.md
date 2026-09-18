# ADR-0001: Use an outbound leased native Windows worker

- Status: Accepted
- Date: 2026-09-18
- Milestone: M03 — Native Browser Decision Loop
- Deciders: Repository owner
- Supersedes: None
- Superseded by: None

## TL;DR

- Define a separate Native Worker API rather than extending the user-facing Run
  Management API.
- Run Playwright through an interactive per-user Windows agent that initiates
  every connection to the control plane over HTTPS.
- Authenticate each agent with a pre-provisioned, revocable worker credential
  stored outside configuration and payloads.
- Dispatch compatible work through expiring, renewable, at-least-once leases;
  the initial browser-measurement capacity is one active lease per worker.
- Publish evidence directly to object storage with short-lived, run-scoped
  upload grants, then register verified immutable references.
- Treat capability claims as scheduling input, not proof of qualification or
  authorization.

## Context

M03 must execute existing Playwright capture and diagnostic capabilities on a
qualified Windows laptop through the control plane. A representative browser
host normally sits behind NAT and a host firewall, uses an interactive desktop
session, and must not receive Kubernetes credentials or permanent object-store
credentials. The control plane must recover from worker, process and network
failure without claiming exactly-once execution.

The existing Run Management API serves callers that create and inspect Runs.
The existing in-process reconciliation worker uses database leases to serialize
control-plane work, but that private Go interface is not a protocol for an
untrusted remote execution host. Native dispatch needs its own authentication,
capability, lease, cancellation and evidence-publication semantics.

Browser measurements are especially sensitive to host contention. Concurrent
measurement Runs on one average laptop would weaken comparability even when the
machine has spare logical CPU or memory capacity. Worker availability and host
qualification must therefore remain distinct from ordinary service health.

## Decision

### Separate Native Worker API

Create a language-neutral `native-worker/v1` API with independent versioning,
authentication policy and conformance fixtures. Do not add worker endpoints to
the Run Management API. Both APIs may be served by the control-plane process,
but they remain separate contracts and authorization audiences.

The first API generation will cover:

- authenticated worker presence and current capabilities;
- acquisition of one compatible execution lease;
- lease renewal and cancellation observation;
- bounded completion or failure reporting;
- acquisition of artifact upload grants; and
- registration of immutable artifact references after upload verification.

Specific endpoint and payload shapes belong to the subsequent contract PR.
This ADR fixes their semantics and trust boundaries.

### Outbound pull connection model

The agent initiates all control traffic over HTTPS. It advertises availability
and requests compatible work through bounded polling or long polling. The
control plane never opens a connection to the laptop, and the worker exposes no
inbound listener.

Server time is authoritative for lease issuance and expiry. The worker uses a
monotonic clock for local deadlines and must tolerate ordinary wall-clock skew.
Retry intervals are server-bounded so an unhealthy worker cannot create an
unbounded polling rate.

### Pre-provisioned worker identity

Each installation receives a distinct, revocable credential provisioned by an
operator and stored in Windows Credential Manager or an equivalent OS-protected
secret store. The credential authenticates a server-side worker principal; a
request body cannot select or replace that principal. Tokens never appear in
URLs, JSON payloads, logs, qualification evidence or repository configuration.

Native Worker API v1 has no self-service enrollment or credential-issuance
endpoint. Rotation and revocation are explicit administrative operations.
Compromise of one credential must not authorize another worker, user-facing Run
administration, Kubernetes access, or unrestricted object-store access.

### Interactive per-user agent

The Playwright agent runs in the qualified user's interactive Windows session,
normally started at login through a reviewed per-user mechanism. It is not a
Windows service and does not run in Session 0. This preserves access to the
actual desktop, display, browser profile boundary, power state and host
conditions used by browser qualification.

The agent executes only reviewed catalogue and workload selections resolved by
the control plane. It does not accept caller-supplied commands, target URLs,
repository revisions or credentials. Browser mode remains part of the reviewed
execution profile; an interactive agent does not by itself require a visible
browser window.

Native Worker API v1 permits one active browser-measurement lease per worker.
Background heartbeat and artifact transfer may overlap with local cleanup, but
two measurement Runs must not execute concurrently on the same host.

### Capability and qualification separation

The agent reports bounded facts needed for compatibility matching, including
the supported tool, operating-system and architecture family, runner contract
generation, browser family, and accepted execution-artifact kinds. These values
are untrusted claims until checked against server policy.

Scheduling additionally requires current, immutable qualification evidence
that binds the worker identity to a compatible `browser-environment/v1`
document and reviewed Playwright runner provenance. Registration or heartbeat
alone does not make a worker qualified. The server decides freshness,
compatibility and authorization; the worker cannot declare itself approved.

### Expiring at-least-once leases

The control plane grants one opaque, time-bounded lease for a compatible Run and
attempt. The lease capability is separate from the long-lived worker credential
and is valid only for its worker, Run, attempt and allowed operations. It must
not be persisted in evidence or logged.

The worker renews before expiry. Renewal can report that cancellation is
requested. On cancellation, shutdown or lease loss, the worker promptly stops
the browser process tree and must not report ordinary completion. The control
plane may lease the Run again after expiry or confirmed release; therefore
dispatch is at least once, not exactly once.

Every execution has a server-issued attempt identity. Artifact object keys,
receipts and completion reports include that identity so a late or duplicated
attempt cannot overwrite evidence from another attempt. Terminal mutation is
conditional on the current lease and expected Run revision. A stale worker can
retain bounded local diagnostics for an operator, but cannot publish them as
authoritative Run evidence without a current grant.

### Direct, scoped artifact publication

The control plane does not proxy browser artifact bytes. For a current lease it
may issue short-lived upload grants for exact server-selected object keys and
bounded content. A grant permits only the required write operation; it grants no
bucket listing, deletion, arbitrary key choice or credential reuse across Runs.

The worker uploads exact bytes directly to the object store, records size and
SHA-256 locally, and then asks the Native Worker API to register immutable
artifact references. Registration succeeds only for the current lease and
attempt after the control plane verifies the expected object identity and
metadata. The manifest or completion receipt is registered last so partial
uploads never imply a complete capture.

## Alternatives considered

### Extend the Run Management API

- Benefits: one OpenAPI document and HTTP surface.
- Costs and risks: combines user and worker credentials, authorization,
  lifecycle and compatibility concerns; couples their versioning.
- Reason not selected: native agents form a separate trust domain and require a
  narrower machine-facing protocol.

### Push work from the control plane

- Benefits: immediate dispatch and no worker polling.
- Costs and risks: requires inbound laptop reachability, firewall exceptions,
  endpoint authentication and stable addressing.
- Reason not selected: it conflicts with representative laptop networking and
  creates an unnecessary attack surface.

### Self-service enrollment tokens

- Benefits: simpler installation at larger scale.
- Costs and risks: adds credential issuance, single-use token state, expiry,
  replay protection and an administrative enrollment workflow.
- Reason not selected: pre-provisioning is adequate for the initial controlled
  worker population and has a smaller security surface.

### Windows service

- Benefits: starts before login and is familiar to administrators.
- Costs and risks: runs in Session 0, which does not represent the user's
  desktop and complicates browser, display and profile access.
- Reason not selected: M03 explicitly targets representative end-user
  conditions.

### Exactly-once dispatch

- Benefits: apparently simpler execution accounting.
- Costs and risks: cannot be guaranteed across lease expiry, process failure,
  network partitions and uncertain completion responses.
- Reason not selected: explicit attempt identity and idempotent publication make
  realistic at-least-once execution observable and recoverable.

### Proxy artifact bytes through the control plane

- Benefits: the worker needs access to only one service endpoint.
- Costs and risks: couples the evidence data plane to API memory, bandwidth,
  timeout and scaling limits.
- Reason not selected: short-lived exact-key grants preserve least privilege
  without making the control plane an artifact transport proxy.

## Consequences

### Positive

- Workers need only outbound HTTPS access and no Kubernetes identity.
- User and worker API authorization can evolve independently.
- Interactive qualification remains tied to the desktop session being measured.
- Lease loss, duplicate attempts and uncertain responses have explicit semantics.
- Permanent object-store credentials are not placed on worker laptops.
- Artifact volume does not consume control-plane request bandwidth.

### Negative

- Operators must provision and rotate one credential per worker.
- The control plane must maintain worker presence, qualification, matching,
  attempt and lease state.
- Direct upload grants require object-store support and careful expiry handling.
- A logged-out or locked-down user session may make the worker unavailable even
  when Windows itself is healthy.
- At-least-once execution requires attempt-aware storage and completion logic.

### Neutral or follow-up

- `perfeng-contracts` will add the self-contained Native Worker API v1 and
  positive/negative fixtures.
- `perfeng-control-plane` will implement worker authentication, presence,
  compatibility matching, leases, cancellation and upload-grant issuance.
- `perfeng-playwright` will provide the interactive agent and bind existing
  qualification, capture, diagnostic and provenance receipts to one attempt.
- `perfeng-environment` will provision local worker identity and connectivity
  without managing the Windows process or storing its credential in Git.
- `perfeng-analysis` continues to consume registered immutable evidence and does
  not depend on worker transport details.
- A later production-security decision may add automated enrollment or managed
  device identity without changing the v1 execution semantics silently.

## Compatibility and migration

This decision changes no existing schema or API document. The future Native
Worker API will be an additive API inventory entry with its own version. Existing
Run Management API clients and existing browser evidence remain unchanged.

Strict bundle readers will need explicit support for the new API inventory entry
when it is added. Control-plane and agent implementations must pin the same
reviewed contract bundle. No existing local capture receipt can be treated as a
worker lease or retroactively assigned an attempt identity.

## Security and operations

- Require TLS and reject credentials in URLs or payloads.
- Scope authentication, lease capabilities and upload grants independently.
- Bind every mutation to the authenticated worker principal and current lease.
- Bound polling, heartbeat, payload, artifact count, artifact size and
  diagnostic output.
- Redact credential, lease and upload-grant material from errors and telemetry.
- Revoke a worker independently without deleting its prior immutable evidence.
- Treat host capability and qualification documents as untrusted inputs until
  structurally validated and authorized by server policy.
- Never interpret worker presence as host qualification or Run success.

## Validation

The follow-up contract change must prove:

- the Native Worker API is self-contained and validates offline;
- worker identity comes from authentication rather than request-selected
  principal fields;
- capability, qualification, availability and authorization remain distinct;
- only a compatible qualified worker can receive a Playwright lease;
- capacity greater than one is rejected for v1 browser measurement;
- renewal, cancellation, expiry, stale attempt and duplicate-report behavior is
  explicit;
- upload grants are short-lived and bound to exact Run, attempt and object keys;
- stale leases cannot register artifacts or terminal completion; and
- no fixture contains credentials, private endpoints or real worker evidence.
