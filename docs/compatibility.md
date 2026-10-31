# Contract compatibility

## TL;DR

- The current candidate bundle is `0.27.0`; it is not a stable release.
- Consumers must explicitly support new schema generations and new members of
  closed execution-artifact or tool unions before accepting them.
- Existing documents retain their original meaning; conversions create new
  documents and do not rewrite evidence.
- Bundle upgrades must coordinate producer, validator and consumer changes and
  preserve immutable provenance.
- Use this document as the compatibility and migration ledger for candidate
  bundle changes.

Candidate bundle 0.27.0 extends Native Worker API v2 to OpenAPI 2.3.0 with
`linux` in the closed operating-system capability union. Protocol version and
routes remain v2; existing Windows documents keep their meaning. Strict consumers
must opt into the new API digest before sending Linux capabilities. Active
Perfeng execution supports Linux only; the Windows enum remains for historical
contract compatibility, not admission authority. Linux workers require a fresh
Linux profile and qualification; never relabel Windows evidence or persisted
execution targets. Data schemas remain byte-identical. This source change does
not publish a release, qualify a host or activate native acquisition.

Candidate bundle 0.26.0 adds a scoped retained-analysis GET in integration OpenAPI
1.1.0. All payload schemas and existing operations remain unchanged; the API document
gains a separate AnalysisPublication component and read path. Strict API-document
readers must opt in to its new digest. Providers implement/authenticate the route
before consumers enable polling; an older provider's 404 cannot establish readiness.
No release or endpoint activation occurs here. See [analysis reads](performance-analysis.md#scoped-http-reads).

Candidate bundle 0.25.0 adds `performance-analysis/v1` as a separate closed family.
Existing schemas and APIs remain byte-identical, including the integration union.
Opt-in producers must retain authenticated admission/native bindings and publish
immutable exact-byte references; consumers must implement scope, association and
policy checks before activating ingestion. No HTTP operation, release or deployment
is added. See [analysis publications](performance-analysis.md) and proposed
[ADR-0011](decisions/0011-bind-analysis-publications-to-retained-admission.md).

Candidate bundle 0.24.0 adds `performance-catalog/v1`: authorized resource metadata,
exact supported profile bindings, baseline lifecycle and complete fresh snapshot
pagination. Existing schemas and APIs remain byte-identical. Consumers opt in
through pinned reviewed artifacts and must verify scope, reference closure,
completeness and freshness before replacing eligibility views. There is no
existing-consumer migration or deployed endpoint. See the
[catalog guide](performance-catalog.md) and proposed
[ADR-0010](decisions/0010-project-safe-performance-catalog-snapshots.md).

Candidate bundle 0.23.0 adds `performance-integration/v1` and its generated
self-contained OpenAPI contract. Existing schema generations and native APIs
remain byte-identical. No runtime endpoint is activated. Integration consumers
must pin a released bundle after review and implement the identity, admission,
retry and cancellation obligations in the [integration guide](performance-integration.md).
There is no migration for existing consumers unless they opt into this boundary.

Candidate bundle 0.22.0 adds `kubernetes-benchmark-evidence/v1` and admits
`kube-burner` in catalogue v2 with OCI-image or release-archive provenance.
Catalogue v1's tool union and all other existing schemas/APIs remain unchanged.
Strict catalogue and bundle-inventory readers must opt in; archive-only analysis
readers must explicitly implement verified OCI provenance. The new evidence
contract separates immutable profile/environment identities from changing
preflight/Run observations and distinguishes UNKNOWN from PASS/zero. It does
not qualify a cluster, authorize execution or approve a baseline. Consumers
must verify content, trusted capture policy and comparable evidence before
promotion. No runtime release or historical evidence is rewritten. See
[Kubernetes evidence](kubernetes-benchmark-evidence.md) and
[ADR-0008](decisions/0008-separate-kubernetes-benchmark-evidence.md).

Candidate bundle 0.21.0 adds `discoverNativeAttempt` to Native Worker API v2
(OpenAPI `2.2.0`) for acquisition responses lost before the worker learns the
attempt ID. The request has only `protocolVersion: 2`; the bearer principal
scopes a bounded observation of recorded availability and the single current
measurement slot. NONE is not proof that acquisition never succeeded. FOUND
reuses ACTIVE/TERMINAL inspection without capability or assignment material;
terminal acceptance takes precedence while the retained lease occupies capacity.
The new availability union distinguishes UNREPORTED from actual reports.
Existing operation shapes, error codes, Run Management and all nineteen
Effect-authored data schemas are unchanged. Strict clients must opt in to the
new operation and response union; 0.20.0 clients retain the earlier API.
The control plane must implement consistent worker-scoped discovery serialized
with acquisition and presence replacement before workers call it. Manual
recovery must stop the old process and withdraw availability; discovery does not
restore execution authority or permit clearing evidence. Bundle promotion and
unattended restart remain separate work. See
[ADR-0007](decisions/0007-discover-native-worker-slot-without-restoring-authority.md)
and the [Native Worker guide](native-worker-api.md#read-only-current-slot-discovery).

Candidate bundle 0.20.0 adds `inspectNativeAttempt` to Native Worker API v2
as an authenticated, read-only operation. Existing v2 requests and responses,
Run Management and data schemas are unchanged. Strict API clients must opt in
to the new `2.1.0` OpenAPI operation and `ATTEMPT_NOT_FOUND` error code;
consumers pinned to 0.19.0 continue using the earlier `2.0.0` API. The control
plane must implement worker-scoped snapshots before the Playwright worker can
use the operation. An inspection result never restores a lease capability,
permits evidence deletion or authorizes unattended acquisition. See
[ADR-0006](decisions/0006-inspect-native-attempt-without-restoring-authority.md).

Candidate bundle 0.19.0 retires the never-deployed `native-worker/v1` API from
the active manifest, OpenAPI corpus and validators. `native-worker/v2` is the
sole supported Native Worker API; its wire path, `protocolVersion: 2`, runner
contract and fixtures retain their meaning. Run Management v1 and all nineteen
data contracts are unchanged. Strict bundle readers must stop expecting the
v1 API entry. Control-plane and Playwright consumers must repin together,
remove v1 routes and payload handling, and prove v2 conformance before enabling
acquisition. Do not mix a v2-only worker with a v1-only control plane. Historical
candidate bundles remain available from earlier Git revisions, but v1 is not
retained in current source or release artifacts. Dormant local v1 assignments
must be reviewed and recreated under the complete v2 recipe; there is no
production traffic or authoritative evidence to migrate. See the
[Native Worker guide](native-worker-api.md) and
[ADR-0005](decisions/0005-retire-native-worker-v1.md).

Candidate bundle 0.18.0 adds `native-worker/v2` as an independent candidate API
generation with a complete baseline Chromium execution recipe. V1 paths,
examples, fixtures and meaning are unchanged. Strict bundle readers must
recognize the additional API entry; v1 workers and control planes do not become
v2-compatible merely by updating the bundle. V2 initially admits only the
repository-owned search journey, baseline mode, Chromium and source-checkout
runner artifact. No native execution is enabled by this bundle. Control plane
and Playwright worker must pin one reviewed revision and implement the v2 lease
and runner projection together. Existing v1 assignments are not converted;
trace, memory, smoothness, branded browsers and release archives remain deferred.
See the [Native Worker guide](native-worker-api.md) and accepted
[ADR-0004](decisions/0004-version-native-worker-execution-recipes.md).

Candidate bundle 0.17.0 corrects Native Worker artifact-plan `format` values to
use the registered data-contract names `playwright-measurements/v2` and
`raw-result/v2`. The previous hyphenated placeholders did not identify bundled
contracts and could not be consumed by strict analysis readers. The field now
uses the artifact-format grammar, which permits the slash in a versioned
contract name without weakening ordinary identifiers. No data schema or API
operation changes. The control plane and Playwright worker must repin together,
replace the hyphenated values, and recreate any dormant native assignments made
from an earlier candidate. Native execution has not been activated, so there is
no authoritative evidence to migrate.

Candidate bundle 0.16.0 corrects the not-yet-implemented native artifact upload
authorization selected by
[ADR-0003](decisions/0003-use-s3-presigned-put-for-native-artifacts.md). The
upload-grant response now carries a short-lived S3 SigV4 presigned `PUT` URL and
a closed set of exact signed headers instead of a custom
`X-Perfeng-Upload-Grant` header paired with a credential-free gateway URL. The
URL and signed headers are secret delivery material and must be redacted and
never persisted as evidence. Presence, acquisition, renewal, release,
registration and terminal-reporting semantics are unchanged. Control-plane and
Playwright consumers must repin together before enabling upload grants and must
not mix the 0.15.0 header shape with direct object-store upload. There is no
persisted upload-grant data to migrate.

Candidate bundle 0.15.0 adds the independent `native-worker/v1` API without
changing any data schema or Run Management API operation. Strict bundle readers
must accept a second API inventory entry. Existing Run Management clients and
data-contract producers require no payload migration. Native worker clients and
the control plane must pin the same reviewed bundle and implement the complete
v1 lease fence: authenticated worker identity, attempt identity, expected Run
revision and lease capability. A consumer must not treat presence as
qualification, availability or authorization, and must not send worker,
lease-capability, upload-capability or object-key choices in JSON requests. Its
custom upload-capability transport is retained only as candidate history and
must not be implemented after 0.16.0.

Candidate bundle 0.14.0 completes the Effect Schema authoring migration for all
nineteen data contracts. The remaining workload, catalogue, artifact,
transport, Playwright, browser, policy, analysis and baseline families now
generate their existing Draft 2020-12 artifacts from typed sources. Runtime
refinements and generated constraints retain conditional, uniqueness,
timestamp, provenance and closed-object behavior. Published IDs, manifest
names, paths and externally referenced fragments are unchanged. Existing
positive and negative compatibility suites pass without producer or reader
migration. Exact-byte consumers must update deliberately. The Run Management
OpenAPI description remains hand-authored under the separate API workflow.

Candidate bundle 0.13.3 changed the authoring source and exact schema bytes for
`run/v1` without changing accepted run-metadata documents. Effect Schema now
owns the legacy inline candidate and environment shapes as well as run, test,
runtime, data and phase metadata. The inline shapes intentionally remain
different from the standalone `candidate/v1` and `environment/v1` contracts.
Runtime Effect decoding and generated JSON Schema both enforce RFC 3339
timestamps, including calendar validity. Stable IDs, manifest names and paths
are unchanged. Payload producers and readers require no migration; exact-byte
consumers must update deliberately. Fourteen data contracts and the Run
Management API retain their previous authority during the staged migration.

Candidate bundle 0.13.2 changed the authoring source and exact schema bytes for
`result/v1` and `result/v2` without changing accepted metric documents. Effect
Schema now owns their shared run identity, metric, distribution, threshold and
metadata shapes. V1 still requires a positive sample count. V2 still permits
the count to be absent or null, but rejects zero and negative values. The
generated v2 document inlines the shared shapes instead of referencing v1;
nullable unions and open metadata also have equivalent generated
representations. Stable IDs, manifest names and paths are unchanged. Payload
producers and readers require no migration; exact-byte consumers must update
deliberately. Fifteen data contracts and the Run Management API retain their
previous authority during the staged migration.

Candidate bundle 0.13.1 changed the authoring source and exact schema bytes for
`candidate/v1` and `environment/v1` without changing their accepted JSON
instances, stable IDs, manifest names or paths. Effect Schema is authoritative
for those two contracts and deterministically generates their Draft 2020-12
documents. Generated presentation adds descriptive metadata and empty
`required` arrays for open-key records. Payload producers and readers require
no migration; consumers that pin exact schema or bundle bytes must update
deliberately. The other seventeen data contracts and the Run Management API
retain their previous authority and behavior during the staged migration.

Candidate bundle 0.13.0 extended the existing workload and
execution-artifact unions without adding a schema generation or changing the
run-management API. `workload/v1` now accepts `kube-burner` only as an open,
iteration-budgeted workload. The shared catalogue/raw-result v2 execution
artifact adds `release-archive`, which records an HTTPS release URL and separate
SHA-256 values for the downloaded archive and extracted executable. URLs with
credentials, query parameters, or fragments are rejected. Consumers pinned to
0.12.0 must not accept kube-burner workloads or release archives until their
closed unions and provenance checks are updated.

Bundle 0.12.0 added `catalogue/v2` and `raw-result/v2` without changing the
seventeen contracts and API shipped in 0.11.0. V2 retains digest-pinned OCI
execution and adds a mutually exclusive native source-checkout identity: HTTPS
repository, full Git SHA, and the exact dependency-lock path and SHA-256. Native
catalogue artifacts must repeat the catalogue source repository and revision
exactly. Existing v1 producers and consumers remain on v1; consumers must add an
explicit v2 reader before native browser manifests are registered.

An OCI v1 raw manifest can be converted by moving `producer.image` to
`producer.artifact.image` and adding `producer.artifact.kind: oci-image`, then
setting `schemaVersion: 2` and the new bundle version. A native manifest cannot
be derived from v1: capture and verify its source revision and dependency-lock
bytes at execution time. Conversion creates a new manifest and never rewrites
raw evidence.

Bundle 0.11.0 added three contracts without
changing the fourteen contracts or run-management API shipped in 0.10.0:
`playwright-measurements/v2`, `browser-environment/v1`, and
`browser-diagnostics/v1`. Strict bundle readers must recognize seventeen
contracts. Existing Playwright producers remain valid v1 producers; they do not
gain v2 page-lifetime, diagnostic-mode, or environment claims automatically.
Consumers must select the measurement generation explicitly and must not mix v1
and v2 documents as one comparison cohort without an intentional migration.

Bundle 0.10.0 added the
`playwright-measurements/v1` native payload contract without changing existing
schema generations or run-management API 0.4.0. Strict bundle readers must
recognize the fourteenth contract. The checked-in Playwright raw fixture and
its transport references now use the contract shape; consumers of those
candidate fixtures must update their expected checksum and sample statistics.
Consumers pinned to bundle 0.9.0 retain the earlier informal two-sample payload.

Bundle 0.9.0 made run-management API 0.4.0 pre-dispatch cancellation
synchronous: CREATED and VALIDATING now transition
directly to ABORTED with HTTP 200, while PROVISIONING and later active states
continue through CANCELLING with HTTP 202. This replaces two lifecycle edges and
changes observable behavior without changing the Run wire schema. Upgrade the
control plane and its pinned transition snapshot together; consumers that still
implement universal asynchronous cancellation must remain on bundle 0.8.0.

Bundle 0.8.0 extended the run-management OpenAPI candidate to API 0.3.0 with
additive baseline create, exact-version read and revision-checked transition
operations. Existing run operations and all thirteen schema contracts were
unchanged. Strict API clients that reject unknown paths or error codes need an
explicit upgrade; consumers pinned to 0.7.0 retain API 0.2.0.

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
