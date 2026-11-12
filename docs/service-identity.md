# Service identity and exact CI Run discovery

## TL;DR

- Run API 0.5.0 adds authenticated exact resolution and access observations.
- Service ownership, verified actor, calling client and creator are separate.
- Current service grants authorize operations; responses and links grant nothing.
- This candidate specifies provider behavior; it does not activate that behavior.

## Identity and authority

A service-enabled provider MUST bind a Run to the stable `issuer`/`id` of the
service in its retained, authenticated admission. Revisions and content digests
remain evidence identities, not membership grants. It MUST NOT infer ownership
from a name, Run ID, URL, body, header or response supplied by the client.

`VerifiedActor` identifies the accountable HUMAN or CI actor. `caller` identifies
the verified calling client (for example the Console BFF); `createdBy` preserves
the original accountable creator. Direct CI may have the same actor and caller
identity. A BFF bearer alone MUST NOT impersonate a human: providers must verify
both identities and delegation through their configured trust mechanism. Token
issuance and concrete issuer/delegation protocol are outside this contract and
must be admitted before human operation is enabled. No identity field is an
instruction to fetch an issuer URL. Responses MUST NOT expose bearer credentials.

Each operation MUST recheck the verified actor's current service grants and the
caller's delegation. Grants MUST be service-bound, default-deny and independent:

| Operation | Required service permission |
|:--|:--|
| Exact Run, artifacts, baseline reads; access and resolution | `run:read` |
| Create Run | `run:create` |
| Cancel Run | `run:cancel` |
| Attributable rerun (future operation) | `run:rerun` |
| Create baseline candidate | `baseline:create` |
| Transition to QUALIFIED | `baseline:qualify` |
| Transition to APPROVED | `baseline:approve` |
| Transition to RETIRED | `baseline:retire` |

These rights imply none of each other. Rerun permission does not grant arbitrary
create, cancellation or baseline approval. This PR does not add a rerun endpoint.
Existing baseline transition rules, revision conflicts and evidence qualification
remain mandatory. Baseline reads and transitions use their retained service
association, never a service selected by the reader. No association means denial.
`permissions` is a current advisory observation for this actor/caller/service,
not a transferable token, a promise that an operation exists, or a cached grant.
Auditable mutations must retain the verified actor, caller, service and target;
the audit delivery/read contract is a later provider/contract slice.

## Exact lookup and safe denial

`GET /v1/run-resolutions?requestIssuer=...&requestId=...` requires `run:read`
and returns `RunResolution`: the original Integration request tuple, native
`runId` and immutable service binding. Both query parameters are required,
percent-encoded once by the client and decoded once by the server; duplicate or
unknown parameters and a request body MUST be rejected with 400. The complete
issuer/id tuple is compared exactly, without normalization or dereferencing.
The selector is not a grant. No credentials belong in a CI deep link. A CI caller
may provide the native Run ID directly or use this authorized resolver; the
Console constructs its own local route from the returned ID, not a returned URL.

A request maps to at most one native Run. Retry requiring a new execution uses
new Integration request and attempt identities under existing retry semantics.
Never pick the newest attempt, parse a provider ID, recreate missing work or
redirect. Retain the mapping and service tombstone after native cleanup; resolution
does not assert the native Run snapshot or artifacts are still retained.

`GET /v1/runs/{runId}/access` returns `RunAccess` only for an authorized existing
Run with a retained service binding. Its current actor/caller can differ from CI
`createdBy`. Both operations are read-only and MUST use `Cache-Control: no-store`
on every response, including errors. Authentication failure is 401; a global
operation denial may be 403 before lookup. Unknown, unbound, cross-service,
revoked and not-yet-mapped selections MUST all return identical 404
`code: NOT_FOUND`, `message: Not Found` and an independent per-request UUID
`requestId`, without resource-specific details
or distinguishing headers. Actual provider failure is 503, never fabricated
absence or sample data. Existing throttling and Retry-After rules still apply.

## Compatibility, verification and rollout

Legacy bearer mode retains principal-owned exact read, create/idempotency and
baseline semantics. Service mode MUST be explicitly configured by the provider
and distinguishable from legacy credentials by verified trust configuration;
client fields cannot opt into it. Never OR service grants with legacy ownership
to bypass revocation. Unbound historical records stay legacy-only until an
explicit reviewed provider migration establishes authenticated bindings.

Run/CreateRun, Integration lifecycle payloads, existing routes, state transitions
and idempotency ownership remain unchanged. Integration's accepted provider Run
identity remains opaque; only retained provider association yields a native ID.
API-document consumers must pin the reviewed 0.5.0 document before opting in.
Providers ship first; an older provider's 404 is not proof of service readiness.

`service-access-cases.json` and `scripts/service_access.py` define offline
schema and relationship conformance using independently trusted inputs. They
are not an authorizer or proof of live enforcement. Providers must additionally
prove authentication, delegation, grant revocation, uniform HTTP denial and
mutation audit persistence before consumers enable service mode. Roll back by
disabling service-mode consumer entry points; retain admission and mappings.
No deployment, release, identity issuer selection or consumer pin changes occur
in this PR. See [ADR-0016](decisions/0016-service-scoped-run-discovery.md).
