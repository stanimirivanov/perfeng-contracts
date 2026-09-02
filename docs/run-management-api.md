# Run-management API (candidate)

The [OpenAPI 3.1.1 document](../api/run-management/v1/openapi.json) defines the
control-plane boundary from proposal sections 12-13. This is a specification
and conformance corpus, not a deployed service. API description version 0.1.0
ships in candidate bundle 0.5.0; neither is a stable v1 release.

## Operations

| Operation | Success | Meaning |
| --- | --- | --- |
| POST /v1/runs | 201 + Run + Location | Durably accepted, not executed |
| GET /v1/runs/{runId} | 200 + Run | Current consistent snapshot |
| POST /v1/runs/{runId}/cancel | 202 + CANCELLING Run | Cancellation requested |
| Repeat cancel after ABORTED | 200 + ABORTED Run | No mutation |

All operations require bearer authentication. The server derives a stable
principal and authorization scope from the credential, never from a body field.
TLS is required outside isolated development. Token issuance and identity-provider
selection remain deployment work. Invisible runs return 404 on read/cancel;
lacking the operation permission itself can return 403.

Only create accepts a body: application/json, at most 65,536 UTF-8 bytes.
Duplicate JSON object keys at any depth, nonfinite numbers, invalid UTF-8,
malformed JSON and unknown properties are rejected. Cancel has no body;
even an empty JSON object is a 400 error.

## Declarative create request

See the [create fixture](../api/run-management/v1/examples/create.json):

- testSuite selects an approved suite within the chosen catalogue.
- catalogue supplies an immutable ID, numeric x.y.z version and SHA-256.
- profile uses one of workload/v1's six profile names.
- candidate supplies a full lowercase Git SHA and registry-qualified image
  digest, stricter than the legacy candidate descriptor.
- environment and policy supply approved definition IDs, versions and hashes.

Hashes identify exact published bytes, not parsed/reformatted JSON. The server
resolves approved registry entries and verifies those bytes. It checks suite/profile
availability, candidate-image authorization, environment access and policy mode.
A digest identifies bytes; it does not attest source provenance or image safety.
The environment-definition registry is later work and is distinct from the
existing environment/v1 observed descriptor.

Caller-supplied commands, target URLs, workload overrides, Kubernetes manifests,
credentials and arbitrary artifact-fetch URLs are not accepted. The catalogue
resolves the selected profile to a pinned workload. The policy carries baseline
rules; the prototype's free-form release alias is not an immutable baseline.
Existing policy/v1 allows observe/inform, not blocking modes.

Fixture hashes are synthetic shape examples, not deployable registry entries.

## Idempotent creation

Idempotency-Key is required: 16-128 ASCII characters matching the document's
pattern. Generate a new high-entropy key for each intended run.

The server atomically binds (stable authenticated principal, create operation,
key) to the validated request and accepted run. Token rotation for the same
principal does not change this scope. Concurrent duplicates cannot enqueue
multiple logical runs.

Request equality compares validated JSON objects: whitespace and object-key
order do not matter; string and nested values must match exactly. This shape
has no numeric fields needing cross-language numeric canonicalization. Do not
hash raw HTTP bytes or include Authorization in the request identity.

| Retry situation | Response |
| --- | --- |
| Same key and request after acceptance | Original 201, body, Location and expiration |
| Same key with different valid request | 409 IDEMPOTENCY_CONFLICT |
| Same key/request still being accepted | Wait, or 409 REQUEST_IN_PROGRESS with Retry-After |
| Rejected before acceptance | Error; no run or retained key reservation |

The accepted snapshot is immutable for replay: CREATED, revision 1. GET returns
current state; replay never resets it. Location is /v1/runs/{id}.
Idempotency-Key-Expires-At is at least 24 hours after original acceptance and
does not change on retry. The binding survives service restart and remains valid
until expiration, including after run termination.

After expiry the same key can create another run: inspect the original Location
before retrying an uncertain old request. A connection failure, 500 or 503 can
leave acceptance uncertain; retry with the same key/body within retention.
The persistence adapter must implement atomic idempotency, not a best-effort
in-memory lookup.

## Lifecycle and cancellation

[transitions.json](../api/run-management/v1/transitions.json) is normative:
only its edges are permitted; terminal states cannot become active again.
Normal execution proceeds from CREATED through VALIDATING, PROVISIONING,
WARMING_UP, RUNNING, COLLECTING, ANALYZING and REPORTING to COMPLETED.
Zero warm-up permits PROVISIONING directly to RUNNING.

Tool failure in warm-up/running goes through COLLECTING when diagnostics can
be retained; unrecoverable infrastructure failure can terminate immediately.

- INVALID: asynchronous validation failed (VALIDATION_FAILED).
- TEST_FAILURE: tool failure or unusable capture prevents analysis (TOOL_ERROR).
  This is not an SLO or regression verdict.
- INFRASTRUCTURE_FAILURE: scheduling/storage/pipeline failure, timeout, or analysis
  service failure (INFRASTRUCTURE_ERROR, PIPELINE_TIMEOUT, ANALYSIS_ERROR).
- ABORTED: cancellation completed and active execution stopped.
- COMPLETED: collection, analysis and reporting finished, regardless of verdicts.

Every active state accepts cancellation by atomically entering CANCELLING.
Repeats in that state return 202 without incrementing revision. The worker
stops execution and retains available evidence before ABORTED. Cancellation
does not delete durable artifacts. Stop/cleanup failure can instead become
INFRASTRUCTURE_FAILURE.

Cancellation/completion races are serialized: cancellation winning prevents
normal completion from overwriting CANCELLING; another terminal transition
winning yields 409 RUN_TERMINAL. Already ABORTED remains 200. Cancel after
COMPLETED is not deletion or a rerun request.

Every persisted mutation increases revision; no-op replays do not. createdAt is
immutable and updatedAt never precedes it. Terminal snapshots require finishedAt
between those times and the matching failure object where applicable.
CREATED has revision 1, equal creation/update times and no tool result.
Retries do not introduce undocumented lifecycle back-edges.

toolExitCode is an optional observed process result, not a verdict. Populate it
only for one unambiguous process result representing the run; multi-process
details belong in execution evidence. k6 exit 99 with usable data can proceed
to COMPLETED. The completed fixture intentionally demonstrates that case.

## Errors and result boundaries

Errors have a stable code, safe message and server-generated requestId UUID.
Optional details use JSON Pointer paths and bounded messages. Never echo secrets,
connection strings, credentials or raw logs.

- 400: malformed JSON/header/path or forbidden body.
- 401/403/404: authentication, authorization or visibility failure.
- 409: idempotency conflict/in-progress acceptance or terminal cancellation.
- 413/415: oversized create body or wrong content type (BAD_REQUEST code).
- 422: invalid create shape or synchronously rejected references; no run created.
  Later dynamic validation can instead produce INVALID.
- 429/503: capacity/unavailability errors with Retry-After seconds.
- 500: unexpected error; acceptance may be uncertain.

Quality, SLO and regression outcomes belong to analysis/v1. No API field invents
a measurement window or result before one exists. Artifact/result retrieval
endpoints are outside this slice. The environment's local-capture/v1 receipt
is not automatically promoted to RawResult.

Legacy run/v1 remains unchanged: its INCONCLUSIVE state is not accepted here,
and it cannot express CANCELLING. Do not serialize API Run directly into that
schema. A future explicit adapter must preserve cancellation progress and map
measurement inconclusiveness into analysis, without dropping information.

## Validation

~~~sh
uv run --locked python scripts/validate.py
uv run --locked python scripts/validate_api.py
uv run --locked python -m unittest discover -s tests -v
~~~

The API is self-contained with static local references. Validation never fetches
schemas. CI checks OpenAPI structure, operation/authentication rules, seven body
fixtures, five HTTP cases, transition consistency and negative cases. All twelve
existing JSON schemas and their compatibility corpus remain unchanged.

These are contract tests, not proof of runtime concurrency, authorization,
restart persistence or cancellation. Those tests belong in the future Go service.
This initial corpus is not a general OpenAPI breaking-change detector; future
changes require reader/writer compatibility review.

Reference: [OpenAPI 3.1.1](https://spec.openapis.org/oas/v3.1.1.html).
