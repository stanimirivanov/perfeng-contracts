# Performance integration identity and request lifecycle v1

## TL;DR

- Candidate bundle 0.23.0 adds a shared protocol; it deploys no endpoints.
- Pin generated JSON artifacts; do not import producer TypeScript or validator internals.
- Verify credentials, immutable selections and source/deployment evidence before admission.
- Retries preserve request context; cancellation and completion are distinct outcomes.

## Identity and provenance

`performance-integration/v1` uses CloudEvents 1.0 structured JSON. Event identity
is `(source, id)`; `type` and `dataschema` identify this closed v1 generation.
Issuer URIs are opaque authorities, never URLs to fetch. Opaque IDs require URL
encoding in path parameters. Display names and trace labels confer no identity.
The producer's event source must equal the request identity issuer; consumers
configure the expected provider authority independently of reply content.

The immutable context distinguishes request and attempt identities from event
identity and the provider's run identity. Every service, capability, deployment,
environment, workload, reviewed profile, policy, baseline and evidence reference
contains issuer, ID, revision and SHA-256 of its producer-published immutable
artifact bytes. Providers must resolve and compare all four fields, including
entity kind, association and authenticated scope. Resolving one valid reference
does not prove it belongs to the selected service or deployment.

Candidate source algorithm and digest are explicit; SHA-1-only providers reject
Git SHA-256 with `unsupported_revision`. Candidate image digest must be bound to
that source and deployment by verified evidence; a Git hash cannot fabricate an
image digest. `baseline: null` explicitly means no selected approved baseline;
it never means latest. Providers reject requests requiring an unavailable or
unapproved baseline. Evidence references point to reviewed provenance; arbitrary
commands, target URLs, credentials and callbacks are not accepted fields.

`principal` identifies the expected authenticated tenant/service principal.
Providers derive actual scope from verified credentials and compare it with
this claim before resolving selections or returning request information. The
body does not authorize work. Schema validation cannot prove provenance,
association, approval or authorization; these are provider admission obligations.

## HTTP and retry semantics

The generated [OpenAPI](../api/performance-integration/v1/openapi.json) describes
three authenticated operations. POST `/integration/v1/requests` returns 202
with a durable accepted request/run mapping or 422 with a durable rejection.
GET `/integration/v1/requests/{requestId}?issuer=...` returns the current snapshot
or the retained rejection. Lookup is scoped to verified principal plus request
issuer and ID, never ID alone. Responses echo the entire immutable context.

Same request identity and identical context must return the original disposition
and run, regardless of new delivery event IDs. Conflicting context is 409 and
must not create work. A new execution attempt requires new request and attempt
IDs. Reusing an event identity with different content is also a conflict.
Request-to-run mappings and terminal tombstones must survive provider native
idempotency retention; expiry cannot silently create a second run. Unknown
lookup is 404; known retired requests are 410. Neither authorizes redispatch
under a new identity. Durable retention implementation belongs to M09-PR6.

Malformed requests use 400, authentication failures 401/403, conflicting reuse
409, unsupported content type 415, rate limiting 429, temporary failure 503.
Errors have bounded code/message; no raw diagnostics or secrets. Versions use
`unsupported_version`; unavailable/unauthorized immutable selections are not
substituted. Retry-After on 429/503 is seconds; preserve context and identities,
back off within the deadline, and reconcile uncertain acceptance by GET.
Responses never grant new authority. Network timeout is unknown acceptance.

`requestedAt` and `deadline` are immutable RFC 3339 instants with explicit
offsets; deadline must follow creation. No acceptance at or after deadline.
The deadline limits admission and triggers best-effort cancellation of accepted
work; elapsed time alone does not prove termination. Late terminal evidence is
valid. Enforcement belongs to provider/consumer runtime PRs.

## Lifecycle and cancellation

Integration states project existing native states without changing native APIs:
ACCEPTED covers CREATED through WARMING_UP, RUNNING covers RUNNING through
REPORTING, CANCELLING covers CANCELLING, COMPLETED covers COMPLETED, FAILED
covers INVALID/INFRASTRUCTURE_FAILURE/TEST_FAILURE, CANCELLED covers ABORTED.
CANCELLED means the provider confirmed termination without completion; failure
classification and quality verdicts remain separate later analysis contracts.
COMPLETED proves pipeline completion, never SLO/regression PASS.

Snapshots carry monotonic nonnegative revision per request. Unchanged snapshots
may repeat; changed snapshots require higher revision. ACCEPTED may advance to
RUNNING, CANCELLING or any terminal state; RUNNING may advance to CANCELLING or
terminal; CANCELLING may advance to terminal. Polling can skip intermediate
states. Terminal snapshots and admission disposition are immutable. A rejection
cannot become accepted; lifecycle snapshots require an accepted run identity.

POST cancellation binds the path and issuer query to the body's request context.
It is idempotent and may precede receipt of acceptance; providers must atomically prevent
unstarted work or cancel its mapped run, never create a run to cancel it. Unknown
requests return 404 and require reconciliation of the original request. A 202
snapshot confirms CANCELLING, not a stopped run; 200 returns a terminal snapshot.
Concurrent completion may win and return COMPLETED or FAILED. Cancellation
intent, a 202 acknowledgement and deadline expiry never imply CANCELLED.

## Compatibility, conformance and migration

This is an additive candidate generation. Existing schemas and native APIs keep
their bytes and meaning. No default consumer behavior changes. Provider admission
and Argus integration must pin a released bundle after joint review and check
all semantic rules above; this PR does not publish or activate the protocol.
Unsupported generations fail explicitly; there is no fallback to legacy fields.

Effect authoring generates both JSON Schema and OpenAPI components. Python
tooling checks closed message shapes and complete exchange fixtures offline,
including immutable correlation, duplicate delivery and state progression. It
is conformance tooling, not a runtime SDK or authorization engine. The default
`make validate` gate includes these checks. See proposed
[ADR-0009](decisions/0009-share-integration-identity-and-lifecycle.md).

The [CloudEvents specification](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md)
informs event identity; [AsyncAPI request/reply](https://www.asyncapi.com/docs/tutorials/getting-started/request-reply)
informs correlation. These are adapted patterns with no added dependencies.
