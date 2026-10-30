# Request-linked analysis publications

## TL;DR

- Candidate performance-analysis/v1 maps native analysis/v1 to an admitted request.
- Authenticate scope and compare retained native bindings before consuming bytes.
- Lifecycle messages remain closed; the opt-in read contract activates no endpoint.

## Meaning and authority

`dev.perfeng.integration.analysis-published.v1` is a separate closed CloudEvents-style
family. It carries the entire original integration context, scoped admitted run,
explicit native association and immutable analysis artifact reference. The native
test ID may differ from the native workload ID and all catalog labels. Never
derive either identity from opaque request/run IDs, aliases or revision strings.

The provider must retain `native` alongside admission: native run/test IDs,
workload and policy id/version/SHA-256, and either no baseline or the exact approved
baseline identity and normalized artifact. The binding attests the provider's
reviewed resolution of every original immutable selection, including environment,
profile and candidate. Resolve it once during admission; a current registry or a
later baseline approval cannot reconstruct historical authority. A non-null
baseline must have been approved for that admitted selection. Its later retirement
does not invalidate historical evidence or approve a new execution.

An authenticated publication must match independently retained admission context,
run and native binding exactly. Source/run issuer must match the configured
provider; principal must match verified credentials. A body echo is not proof of
authentication or admission. Provider materialization and retention require a
separate reviewed implementation before consumer activation.

## Artifact and policy verification

The reference identifies `kind: analysis`, `format: analysis-result/v1`, JSON,
positive byte size at most 1 MiB and SHA-256 of exact bytes. Verify size and hash
before parsing through analysis/v1; reject duplicate members and non-finite JSON.
Never normalize bytes before hashing. URI metadata grants no network permission:
use configured authenticated storage/origin allowlists, bounded timeouts, response
limits and redirect policy. Credentials, query tokens and fragments are forbidden
in retained addresses. Do not follow candidate/baseline normalized-result URIs or
read raw k6 results to recompute statistics.

Report run ID and candidate artifact run ID must match native run ID; report test
ID and policy identity/hash must match the retained native association. Every
comparison artifact must equal the admitted baseline artifact; no baseline means
no comparison artifact. Missing reference data may remain inconclusive even when
a baseline was selected. Verify the exact reviewed policy bytes by their native
digest and validate complete rule coverage, selectors, configured sections and
policy baseline IDs/versions against the frozen approved baseline. The publication
does not carry policy bodies or replace analysis/v1 policy conformance.

Quality, SLO, regression and uncertainty remain independent. COMPLETED, SLO PASS,
observe/inform mode and a valid publication never grant an overall PASS, blocking,
baseline promotion or execution authority.

## Delivery, replay and compatibility

Publication time cannot precede admission or analysis creation; analysis creation
cannot precede admission. Deadline expiry or cancellation intent does not discard
valid late analysis. No terminal lifecycle transition is inferred from publication.
Authenticate before exposing scope-specific absence or evidence. This contract
defines the scoped HTTP read below, with no mutation, callback or acknowledgement.
Provider implementation must adopt the reviewed operation before consumption.

Retain one immutable publication association per request/attempt. Exact redelivery
is idempotent. Reusing source/event ID with different content, or publishing a
different artifact/native binding for the same request/attempt, is a conflict;
retain the contradiction and never silently replace evidence. A new execution or
corrected report requires a separately reviewed fresh request/attempt. Publication
retention must survive transport retries and native run retention.

Candidate bundle 0.25.0 adds this family without expanding performance-integration/v1
or changing analysis/v1. Old consumers stay on their pins; opted-in readers must
implement these semantic/authentication checks, not merely schema decoding. Stage
rollout as shared-contract review, durable provider binding/publication, then Argus
authenticated consumption and persistence. No release or deployment occurs here.
Revert removes the new candidate family; existing APIs and evidence are unaffected.

The offline `scripts/performance_analysis.py` checks relationships after schema
validation. `check_binding` additionally requires independently trusted inputs and
already validated analysis/policy semantics; it is conformance tooling, not an SDK.
See [ADR-0011](decisions/0011-bind-analysis-publications-to-retained-admission.md).

## Scoped HTTP reads

Candidate bundle 0.26.0 / integration API 1.1.0 defines
`GET /integration/v1/requests/{requestId}/analysis?issuer=<request-issuer>`.
Percent-encode the opaque request ID and issuer once using the existing integration
identity rules. Require one nonblank request ID and exactly one issuer query;
reject duplicate/unknown query parameters and a request body. Native Run IDs and
artifact URLs are not request identity and never select another owner's evidence.

Authenticate bearer credentials and require the existing request-read permission
before exposing absence. Derive principal namespace/ID from authentication and
provider namespace from trusted configuration. Scope lookup by principal and full
request identity. Return the original immutable performance-analysis/v1 publication
as application/json, including its stable event ID/time; do not wrap it in lifecycle
messages, re-create it on reads, return a latest report or trigger materialization.
Reading never executes, schedules, cancels, promotes a baseline or fetches artifacts.

| Status | Body / behavior |
| --- | --- |
| 200 | Separate closed AnalysisPublication component |
| 400 | Existing Error with invalid_request for malformed read identity |
| 401 | unauthenticated; required WWW-Authenticate: Bearer |
| 403 | forbidden when authenticated read permission is absent |
| 404 | unknown_request with message "Not Found" uniformly for unknown, invisible or unpublished requests |
| 429 | rate_limited; required positive Retry-After seconds |
| 503 | unavailable; required positive Retry-After seconds |

All responses require Cache-Control: no-store. Absence cases share body and headers;
never expose an owner-specific not-ready marker. A 404 may become ready later and
is not a terminal Run state; consumers use bounded polling/backoff and preserve
request identity. Honor Retry-After on 429/503; fix identity or credentials instead
of blindly retrying 400/401/403. Other methods are not defined; providers reject
them without side effects. No transport acknowledgement or artifact download is added.

After schema validation, `check_read_scope` compares independently trusted provider,
authenticated principal and parsed path/query identity. It is conformance tooling,
not an authenticator or runtime SDK. Consumers still perform retained admission,
native association, exact artifact/policy and outcome checks before decisions.
Publication, completion and SLO PASS remain separate from overall decision authority.

Old payloads and operations keep their meaning and bytes. Pin the changed API
document and confirm provider support before opting in; an old endpoint's 404 may
mean unsupported route. Roll out provider handler/authentication, then Argus polling
and persistence. No deployment or stable release occurs here. Roll back read opt-in
while preserving retained evidence. See [ADR-0012](decisions/0012-read-retained-analysis-by-request.md).
