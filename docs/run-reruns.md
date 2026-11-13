# Attributed source-Run reruns and immutable audit receipts

## TL;DR

- Run API 0.8.0 / candidate bundle 0.31.0 specifies a service-mode rerun and exact receipt recovery.
- New intent creates a distinct child with the source's frozen selection, never today's defaults.
- Server-verified actor/caller and current service rights govern every operation.
- A receipt proves durable acceptance, not execution success; unknown responses require recovery.
- Provider transactions, concurrent admission and execution fencing must qualify separately.

## Operations, input and authority

`POST /v1/runs/{runId}/reruns` (`rerunRun`) accepts `RerunRequest` and requires
`Idempotency-Key` with the existing opaque 16–128 character key syntax.
`sourceReport.id` and `sourceReport.sha256` pin the report the operator inspected;
`reason` is a nonblank audit explanation of at most 1,024 characters, never a
command. The closed body accepts no actor, service, baseline override, candidate
change, URL, secret or caller-selected execution configuration. Keys and reasons
MUST NOT contain credentials or personal secrets; neither grants access.

This is an opt-in service-mode operation, not an extension of legacy CreateRun.
Require current `run:read` and `run:rerun` on the independently retained source
service, verified actor plus caller delegation and authorization over all
selected evidence and the child before disclosure. Do not OR these rights with
legacy principal ownership. Rerun grants neither arbitrary create nor baseline
approval. A BFF bearer alone cannot establish the engineer's identity. Token
issuer/delegation admission remains M05-PR58; these routes MUST remain disabled
until the provider qualifies it. Both verified HUMAN and CI actors use the same
accountability model; source creator and current actor need not be the same.

`GET /v1/runs/{runId}/reruns?idempotencyKey=...` (`resolveRunRerun`) performs
one exact lookup for the currently verified originating actor. Require current
`run:read` and current delegation/resource scope, but not `run:rerun`: an engineer
whose mutation right was revoked can still recover an accepted receipt if they
retain read authority. Another actor cannot obtain it by copying the key, even
with access to the same service. A later audit-search capability is outside this
contract. Encode selectors once, decode once and compare without normalization;
reject unknown/duplicate query keys. GET never creates, retries or dispatches work.

POST accepts no query parameters. GET accepts no body. Both reject ambiguous
headers and duplicate JSON keys, nonfinite numbers, invalid UTF-8, unknown fields
and malformed IDs. Apply the existing 65,536-byte UTF-8 request limit. Responses
MUST be at most 65,536 UTF-8 bytes; refuse rather than truncate. Every response,
including errors, MUST have `Cache-Control: no-store`. No redirects, credential
exposure, runtime schema fetching or dereferencing identity/storage URIs.

## Exact selection and acceptance receipt

Require a complete independently verified AVAILABLE source comparison. Missing
historical binding is not permission to reconstruct it. The submitted report
identity MUST equal the retained report. Current admission MUST authorize that
exact catalogue and enabled suite, environment, workload and policy within
their respective resource namespaces (approval of identical identity bytes in
another resource family is insufficient); a retained
baseline, when present, must have exactly the same version/digest/artifact and
currently be APPROVED. Missing/withdrawn resources do not authorize substitution
with latest versions. A historically absent baseline stays absent and is admissible
retains the existing policy/analysis missing-reference semantics; never silently
select a new baseline.

Acceptance MUST atomically retain the intent/key, verified actor/caller, source
creator, immutable service association, distinct child Run, exact selection and
receipt before responding 201. No accepted child without a recoverable receipt,
or receipt claiming a child whose acceptance did not commit. The ordinary child
Run uses its existing lifecycle and `selection` as its CreateRun request. No
existing Run schema or creation/idempotency semantics change.

`RerunReceipt` is a closed immutable acceptance record:

| Fields | Meaning |
|:--|:--|
| schemaVersion / kind / decision | `1` / `RunRerunReceipt` / `ACCEPTED`; never a performance verdict |
| id / sourceRunId / runId | Receipt UUID, selected source and distinct accepted child |
| service / sourceCreatedBy | Retained service and original source creator, including CI identity |
| actor / caller | Original verified accountable actor and delegated calling client |
| idempotencyKey | Original actor-scoped intent selector, not a credential |
| acceptedAt / idempotencyKeyExpiresAt | Server UTC decision instant and immutable replay deadline |
| request | Original parsed source-report pin and audit reason |
| selection | Exact original source CreateRun request, including candidate commit/image and resource pins |
| native | Original source report-time native binding, including exact workload, policy and nullable baseline artifact |

`native.runId` identifies the **source**, not the child. Execution adapts only the
new Run identity; it MUST preserve the resource and baseline identities. Receipt
selection is not proof that dispatch honored it: PR59 must prove the stored
selection survives resolver retries and worker restart. Recheck current execution
admission before dispatch/new attempts. Withdrawal before admission is 422 with
no accepted child. Withdrawal after acceptance but before dispatch prevents that
dispatch. While VALIDATING, use existing `INVALID` / `VALIDATION_FAILED`
semantics; after that state use only existing state-appropriate failure/cleanup
transitions, never an illegal jump to INVALID. A later retry
cannot silently reselect another resource. A change after an attempt has already
dispatched does not rewrite historical approval or evidence; its current attempt
uses its admitted selection. Subsequent attempts must recheck admission and use
existing state-appropriate failure/cleanup rules, never launch with substitutes.

## Idempotency, uncertainty and retention

Scope the key to stable verified actor `(issuer, id)` and this rerun operation,
not the BFF token/caller, source alone or mutable display name. The retained
source ID and parsed JSON body (including reason) are the request fingerprint;
ignore only object-member ordering, not string/numeric values. Current identity,
delegation and resource visibility MUST be checked before any key lookup result
is disclosed. A renewed caller credential does not replace the original caller
in an existing receipt.

| Same actor/operation/key | Required result |
|:--|:--|
| Same source and parsed body, accepted within replay window | Original 201 receipt, child Location and deadline; no new child |
| Different source or parsed body | 409 `IDEMPOTENCY_CONFLICT` |
| Identical intent is still resolving/committing | 409 `REQUEST_IN_PROGRESS` with Retry-After, or wait and replay; never two accepted children |
| Replay deadline reached or exceeded | 409 `IDEMPOTENCY_CONFLICT`; use exact GET to recover retained acceptance |
| Different actor or new key | Separate intent namespace; still requires full fresh admission |

The replay deadline MUST be at least 24 hours after original acceptance and MUST
NOT extend on retry. Current approval changes do not alter an already accepted
receipt; replay performs no new execution/admission. Revocation of `run:rerun`
blocks POST, including replay; GET recovery may still be authorized independently.

Transport failure, timeout, 500, 503 or a missing GET receipt does **not** prove
that no acceptance committed. Keep the original actor/key/body, resolve by GET,
and retry the identical POST only while allowed; never automatically mint a new
key. Exact GET returns the original receipt beyond the replay deadline while
retained. Retain acceptance/audit at least through that deadline and for as long
as either source or child Run is retained. After payload retirement keep a sealed
actor/operation/key tombstone: an expired or retired key MUST NOT create another
child. GET then uses the uniform 404. Size retention operationally; this candidate
does not choose a fleet-wide audit retention duration. An unresolved in-flight
reservation cannot be dropped or treated as absent while its acceptance may commit.

## Failure mapping and compatibility

401: unauthenticated identity/delegation. 403: resource-independent operation
denial. Unknown, invisible, service-unbound source/evidence/child or a receipt owned by
another actor use the same scoped 404 (`NOT_FOUND`, `Not Found`), without details.
After current authorization, missing comparison, wrong report pin, withdrawn or
unapproved exact selection use 422 `VALIDATION_FAILED`; body validation uses
existing 400/413/415 rules. Storage failure, failed evidence integrity or an
unavailable acceptance store is 503 `UNAVAILABLE` with Retry-After. Never turn
an outage into fabricated absence, successful sample data or a new key.
409 retains the existing conflict/in-progress error family and Retry-After rule.
429 and sanitized 500 retain existing semantics. Errors create no success receipt;
500/503 can nevertheless follow an uncertain commit and require recovery.

This is additive to Run API 0.7.0. Existing operations, Run/failure/verdict enums,
legacy principal-scoped idempotency and Integration/Native bytes remain unchanged.
Providers must qualify PR50 atomic storage, PR59 execution fencing and PR51 serving
before consumers opt in. Publish reviewed contracts/provider capability first;
retain old consumer pins. Rollback disables opt-in consumers/new routes first;
retain accepted children, intent tombstones and receipts. Any required provider
migration belongs to its reviewed persistence slice, not this contract.

## Conformance limits

`rerun-cases.json`, `tests/test_rerun_contract.py` and `scripts/rerun.py` check
closed schemas, HTTP identities/headers, frozen-selection relationships and
retry classification against independently retained inputs. They neither
authenticate nor implement durable deduplication. NEW classification against one
nonmatching record is not proof that the provider can create work. Providers
must separately prove current delegated identity/evidence scope, revocation,
concurrent duplicates, atomic child/receipt writes, crash recovery, retention
sealing and state-appropriate execution admission with real persistence.
