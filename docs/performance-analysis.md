# Request-linked analysis publications

## TL;DR

- Candidate performance-analysis/v1 maps native analysis/v1 to an admitted request.
- Authenticate scope and compare retained native bindings before consuming bytes.
- Existing integration messages and APIs are unchanged; no endpoint is activated.

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
defines no HTTP operation, callback, acknowledgement or transport retry schedule;
provider implementation must review that delivery boundary separately.

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
