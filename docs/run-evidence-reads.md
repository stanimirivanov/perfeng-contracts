# Authorized immutable Run evidence reads

## TL;DR

- Candidate Run API 0.7.0 adds two identifier-only authenticated byte reads.
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
authorization and association are established, unsupported media/format or an
advertised size over the limit returns 422 `VALIDATION_FAILED`. Runtime overflow,
read failure, digest/size/schema mismatch or lost storage availability returns
503 `UNAVAILABLE`, without a partial body. 429 retains Retry-After; 500 retains
the existing sanitized internal-error contract. Run lifecycle is not changed.

`tests/test_evidence_reads.py` exercises independently retained fixture references,
original report/policy bytes, a synthetic historical baseline, identity swaps,
tampering, missing headers, transformations, duplicate names and bounds.
`scripts/evidence_reads.py` checks wire integrity only; it cannot authenticate
principals, establish provenance, or prove live storage/authorization behavior.
Provider admission MUST test authorization/revocation, cross-service associations,
all error mappings, bounded storage I/O and exact schema validation separately.

## Compatibility, rollout and sources

Bundle 0.30.0 / Run API 0.7.0 are additive candidates. No existing operations,
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
