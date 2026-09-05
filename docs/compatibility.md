# Contract compatibility

The current candidate bundle is 0.8.0. It extends the run-management OpenAPI
candidate to API 0.3.0 with additive baseline create, exact-version read and
revision-checked transition operations. Existing run operations and all thirteen
schema contracts are unchanged. Strict API clients that reject unknown paths or
error codes need an explicit upgrade; consumers pinned to 0.7.0 retain API 0.2.0.

Baseline administration accepts immutable evidence and an audit reason, while
the authenticated actor is server-derived. The contract has no list, latest,
automatic-promotion or delete operation. Lifecycle mutation requires the
observed revision and can only request QUALIFIED, APPROVED or RETIRED using the
state-specific qualification shape. These additions do not expose the internal
approved-baseline resolver used by analysis.

Bundle 0.7.0 added baseline/v1 as a new standalone contract without changing
the twelve earlier schema generations or run-management API 0.2.0. Strict bundle
readers must recognize the thirteenth contract; consumers pinned to 0.6.0
continue to use the unchanged earlier bundle.

Baseline/v1 records immutable normalized-result anchors together with exact
software, workload, environment and dataset identities. Their state and complete
lifecycle history distinguish qualification from explicit approval and retirement.
This is an additive bundle change, not permission to treat a floating or passing
result as an approved baseline.

Bundle 0.6.0 extended the run-management OpenAPI candidate with
principal-scoped artifact-reference listing and its HTTP fixture. The response
reuses artifact/v1 fields in a self-contained API component. API 0.2.0 readers
gain an operation and response type; existing 0.1.0 operations and payloads are
unchanged. See [API semantics](run-management-api.md).

Bundle 0.5.0 introduced the run-management OpenAPI candidate and lifecycle/HTTP
fixtures under api/run-management/v1. The API added CANCELLING and excluded
INCONCLUSIVE as a separate wire shape, not a replacement run/v1 record.

contracts.json now includes an apis inventory alongside contracts, and the
archive includes api/. Strict manifest readers may need updating. Existing
consumers stay on their pinned bundles; do not silently upgrade vendored
schemas or claim universal reader/writer compatibility.

Bundle 0.4.0 added policy/v1 and analysis/v1 to the transport foundation.
Policies still support only observe/inform; confirm/block are not accepted.
Establish the remaining phase-1 contracts before a stable 1.0.0 release.

Two versions serve different purposes:

- A path such as `result/v1` identifies a wire-format generation.
- A bundle release such as `0.1.0` identifies the exact set of shipped schemas.

The original result payload keeps integer `schemaVersion: 1`. `result/v2` uses
`schemaVersion: 2` and makes `distribution.samples` optional/nullable when the
tool does not provide a count. Known counts remain positive integers. New
normalized envelopes use v2 records; old readers need an explicit upgrade.

Envelope `schemaVersion: 1` identifies the envelope shape, not its nested metric
record version. `contractsVersion` records the producer's exact bundle version.
Candidate, environment, run-metadata, and artifact-reference schemas do not
declare a schemaVersion property; consumers must not inject one. Select their
schema using the API/containing contract. A catalogue instead declares apiVersion.

See [transport migration](artifact-and-result-transport.md#migrating-legacy-results)
before wrapping old result arrays. Missing raw evidence or sample counts cannot
be reconstructed by inventing placeholders.

Changed schema IDs in this extraction require consumers to update their
schema lookup paths. Payload fields are preserved except that an explicit
`null` metric type is now accepted, matching the schema's existing type and
default declarations. That broadening needs consumer review if a consumer
previously assumed a string whenever the field is present.

Within a stable generation, review compatibility in both directions: can a
new reader read old records, and can an old reader accept new records?
`additionalProperties: false` means even adding an optional property may break
old readers if a new producer emits it. Enum additions and newly accepted nulls
also need producer/consumer coordination. Do not label every additive edit
backward compatible.

For a breaking change, create a new domain major path, document conversion and
rollout, retain old readers during transition, and publish a new bundle major
once the bundle is stable. Preserve immutable raw evidence; conversions produce
new derived artifacts. Documentation-only corrections can use patch releases.

PR validation covers the checked-in compatibility corpus and rejects malformed
identifiers, timestamps, unknown states, unsupported result versions, and
invalid defaults. It does **not** prove compatibility for all possible JSON
documents. Every schema change must also explain reader/writer compatibility
and add positive and negative cases for the affected boundary.

Run lifecycle status, SLO outcome, regression outcome, and measurement quality
remain distinct concepts. The [policy and analysis contracts](performance-policies.md)
preserve the separation between failed execution, poor measurements, and
performance changes. Existing producers need not emit these new documents until
their analysis integration is implemented.
