# Authorized immutable Run evidence reads

## TL;DR

- Run API 0.7.0 defines service-authorized artifact and policy reads. Candidate
  0.9.0 adds a report-only read scoped to the original Run principal.
- Read original report, normalized-result or report-used policy bytes, never a URL proxy.
- Authorize all resources before disclosure; verify retained digest before releasing bytes.
- This contract does not establish live provider or generated-client qualification.

## Operations and authority

`GET /v1/runs/{runId}/artifacts/{artifactId}/content` (`getRunArtifactContent`)
requires current `run:read` authority on the selected Run and the artifact-owning
Run/service. The artifact MUST be directly registered to the selected Run or the
exact historical baseline normalized artifact bound in its verified frozen
comparison/report. UUID knowledge, a storage URI, current baseline selection,
or authority on only one service MUST NOT establish an association or grant.
Native artifact metadata retains its existing closed `kind` union; an analysis
report registered there uses `kind: normalized`, `format: analysis-result/v1`.
The analysis publication's separate descriptor may use `kind: analysis`.

`GET /v1/runs/{runId}/policy/content` (`getRunPolicyContent`) requires current
`run:read` and evidence authorization. Return the original retained policy bytes
whose ID, version and SHA-256 were used by this Run's report. A request pin alone
is insufficient proof of use. Never substitute current registry/catalog bytes,
reconstruct JSON, or follow a supplied URI. Retiring a baseline does not rewrite
historical evidence; current authorization still applies and grants no write.

## Run-owned Analysis Report content

`GET /v1/runs/{runId}/artifacts/{artifactId}/report-content`
(`getRunAnalysisReportContent`) lets the original operator fetch the exact
Analysis Report identified by the Run's artifact registration. The caller first
reads the Run and its artifact registrations through the authenticated Run API.
It supplies only the two identifiers to this operation. There is no request
body, object key, URI, principal selector or latest-report lookup.

**Determine ownership on each request.** In legacy bearer mode authenticate the
credential and compare its verified principal with the retained Run owner. A
replacement credential for the same principal can read the same Run after
rotation. In service mode require the verified accountable actor to equal the
Run's retained `createdBy` (issuer, id and kind), its current `run:read` grant
on the retained service, and valid delegation for the calling client. A second
engineer with a grant on the same service cannot use this operation to read the
first engineer's report. The provider selects the authentication mode from its
trust configuration. A failed service-mode check cannot fall back to a legacy
credential or a shared BFF identity. See [service identity](service-identity.md).

**Select the direct registration.** Resolve the artifact ID within that Run.
Require its registered `runId` to equal the route Run, `kind: normalized`,
`format: analysis-result/v1`, and `mediaType: application/json`. A raw or
normalized-result artifact, a historical comparison artifact, a foreign Run's
registration, and an absent registration all lack this report association.
Use the provider's approved storage resolver and the retained reference.

**Verify before releasing the body or success headers.** Bound storage reads
by size and deadline. Verify the original byte count and SHA-256 against the
direct registration, validate the analysis/v1 document, and require both its
`runId` and `candidateArtifact.runId` to equal the route Run. Preserve the
registered bytes including whitespace and the final newline. The caller can
compare the returned bytes and headers with its independent registration
before using the report for an SLO decision. Apply the byte and HTTP profile
below, including the 1,048,576-byte limit and identity headers. For this
operation both Run ID headers carry the route Run ID.

| Condition | Response |
|:--|:--|
| Unauthenticated or invalid credential | 401 |
| Operation denied globally, independently of the selected resource | 403 |
| Unknown Run or artifact, wrong owner, revoked resource grant, absent direct report association | Uniform scoped 404 before storage lookup |
| Eligible registration advertises a size greater than 1 MiB | 422 `VALIDATION_FAILED` before reading the object |
| Eligible registered object unavailable, oversized during retrieval, short, corrupt, malformed, or internally linked to another Run | 503 `UNAVAILABLE` with a sanitized error and zero report bytes |
| Complete verified report | 200 with exact bytes and all required artifact-content headers |

Scoped 404 responses share the existing `NOT_FOUND` code, `Not Found` message,
and response headers. Each response gets an independent request ID. Existing
400, 429 and 500 semantics apply. This operation adds no authority to submit
Runs, list objects or download other artifact formats.

## Byte and HTTP profile

Only `normalized-result/v1`, `analysis-result/v1` and (policy route only)
`policy/v1` JSON are supported. Successful bodies MUST be original nonempty
bytes of at most 1,048,576 bytes. Verify authoritative identity, association,
size, SHA-256 and the applicable canonical schema before sending any bytes.
Read with a bounded buffer (limit plus one), a finite configured deadline and
cancellation; oversized streams MUST NOT be fully buffered. Never reserialize.
Schema-valid JSON with different whitespace is different content.

Success is 200 with transport `Content-Type: application/octet-stream` and these
required headers (HTTP names are case-insensitive; duplicate fields are refused):

| Header | Value |
|:--|:--|
| Content-Length | Exact original byte count, canonical unsigned decimal |
| Content-Digest | Exactly one RFC 9530 `sha-256=:BASE64_OF_32_DIGEST_BYTES=:` member |
| Cache-Control | `no-store` |
| X-Content-Type-Options | `nosniff` |
| X-Perfeng-Evidence-Media-Type | `application/json` |
| X-Perfeng-Evidence-Format | Exact supported format above |
| X-Perfeng-Run-Id | Selected route Run ID |
| X-Perfeng-Artifact-Id | Artifact route only: exact selected artifact UUID |
| X-Perfeng-Artifact-Run-Id | Artifact route only: independently retained owning Run ID |
| X-Perfeng-Policy-Id / X-Perfeng-Policy-Version | Policy route only: exact report-used identity |

The digest MUST match both actual bytes and independently retained metadata;
a self-consistent body/header pair is insufficient. Policy bytes also MUST
identify the retained policy ID/version. Clients verify bytes before JSON parsing
and schema validation. These headers provide integrity, not authentication.

MUST NOT send Content-Encoding, Content-Range, Location or Content-Location,
compress/transform bytes, redirect, serve partial content, or emit 304. Reject
request bodies, query parameters, Range and all conditional request headers with
400. No ETag or runtime schema fetching. All responses, including errors, MUST
have `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`; errors MUST
NOT expose storage addresses, hidden identity, credentials or body fragments.

## Errors and conformance

401: missing/invalid identity. 403: operation permission denial independent of
resource existence. After resource scoping, unknown, invisible, unassociated or
not-yet-bound evidence all use the existing uniform scoped 404. Only after
authorization and association are established on the broader evidence operations,
unsupported media/format or an advertised size over the limit returns 422 `VALIDATION_FAILED`. Runtime overflow,
read failure, digest/size/schema mismatch or lost storage availability returns
503 `UNAVAILABLE`, without a partial body. 429 retains Retry-After; 500 retains
the existing sanitized internal-error contract. Run lifecycle is not changed.

`tests/test_evidence_reads.py` exercises independently retained fixture references,
original report/policy bytes, a synthetic historical baseline, identity swaps,
tampering, missing headers, transformations, duplicate names and bounds.
The offline conformance checker verifies wire integrity and models report-read
outcomes from independent identity, authorization, registration and storage
fixtures. These examples do not establish live provider authority or provenance.
Provider admission MUST test authorization/revocation, cross-service associations,
all error mappings, bounded storage I/O and exact schema validation separately.

## Compatibility, rollout and sources

Bundle 0.30.0 introduced the Run API 0.7.0 evidence reads. Bundle 0.32.0
adds the owner-only operation in Run API 0.9.0. Consumer implementations can
exercise the [portable report cases](../tests/fixtures/report-content/cases.json)
and [conformance test](../tests/test_report_content.py) before provider
admission. Control Plane must exercise the route with two authenticated
principals, a revoked credential and failing storage. Environment selects the
qualified immutable release after those checks pass. No existing operations,
closed enums, lifecycle transitions or Integration/Native API semantics change.
Publish a reviewed provider-capable bundle before enabling consumers. Qualify a
raw-byte client adapter, including required headers and negative wire cases;
OpenAPI generation alone is not client admission. Older pins remain supported.
Rollback disables the new consumer routes first, then reverts provider exposure;
retain historical bindings and bytes. No persistence migration is specified here.

The wire profile adapts [RFC 9530 Content-Digest](https://www.rfc-editor.org/rfc/rfc9530.html)
and [OpenAPI 3.1.1 raw binary content](https://spec.openapis.org/oas/v3.1.1.html#considerations-for-file-uploads).
A schema-free octet-stream Media Type Object represents original binary, rather
than a JSON string or base64 envelope. No new dependency is introduced.
