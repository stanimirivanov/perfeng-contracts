# ADR-0012: Read retained analysis by request

- Status: Proposed
- Date: 2026-10-30
- Milestone: M01 — Local Performance Decision Loop
- Deciders: Repository owner, control-plane and Argus consumers
- Supersedes: None
- Superseded by: None

## TL;DR

- Add a scoped authenticated GET without expanding lifecycle message unions.
- Return original retained analysis, with uniform absence and no execution side effect.
- Version the API addition and coordinate provider before consumer activation.

## Decision and consequences

Candidate bundle 0.26.0 and integration API 1.1.0 add GET
`/integration/v1/requests/{requestId}/analysis?issuer=...`. Reuse bearer request-read
authorization and principal isolation. Path/query identify the original request,
never a native Run or artifact URL. The 200 body uses the existing separate closed
performance-analysis/v1 schema; lifecycle union and data schemas remain unchanged.

Authenticate and authorize before revealing absence. Unknown, invisible and
not-yet-published requests share 404/unknown_request, message "Not Found" and no
distinguishing headers. New read error schemas bind each status to its safe code.
All responses use Cache-Control: no-store. Rate limiting/unavailability use existing
429/503 errors and positive Retry-After seconds. Reading never creates, schedules,
materializes, cancels or downloads evidence, nor proves an overall PASS or terminal
state. Repeated success returns the immutable stored publication and its event/time.

Read-scope conformance compares independently trusted provider/principal and parsed
request identity. It is not authentication or full admission/native/artifact/policy
verification; consumers still perform those checks. No response claim grants fetch
authority. Existing offline local-reference and schema rejection checks remain.

Old operations and payloads retain meaning. Strict API-document consumers must opt
in to the changed document; pin reviewed provider API support before enabling new
reads, because an old provider's 404 does not establish publication readiness.
This review changes no runtime, stable release or deployment. Roll back consumer
opt-in while preserving provider evidence; do not rewrite retained publications.
