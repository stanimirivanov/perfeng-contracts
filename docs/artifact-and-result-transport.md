# Artifact and result transport

This contract slice implements proposal sections 29 and 35-36: immutable raw
evidence, derived measurements, and the context needed to interpret them. It
defines documents, not an upload service, normalizer implementation, or quality
gate. Bundle `0.3.0` introduced the transport envelopes; candidate bundle
`0.10.0` added the native Playwright measurement schema, and `0.11.0` adds its
environment-aware generation and diagnostic evidence contracts.

## Documents

| Contract | Meaning |
| --- | --- |
| `artifact/v1` | A reference to exact stored bytes: ID, run ID, raw/normalized kind, stable URI, SHA-256, byte count, media type, and format |
| `raw-result/v1` | A manifest of raw artifacts from a measurement window, with producer, test, and workload identity |
| `playwright-measurements/v1` | Native semantic browser samples with cache, repetition, runtime, and browser context |
| `playwright-measurements/v2` | Native semantic browser samples with page lifetime, diagnostic mode, and environment identity |
| `browser-environment/v1` | Detailed browser-host identity and per-run calibration |
| `browser-diagnostics/v1` | Status and immutable references for diagnostic evidence |
| `result/v2` | One metric with available statistics and an optional/nullable sample count |
| `normalized-result/v1` | A set of v2 metrics plus the raw artifact references from which they were derived |

An envelope's `schemaVersion` describes that envelope only. Its
`contractsVersion` records the producer's bundle release, while each nested
metric declares `schemaVersion: 2`. The run ID joins execution metadata; test ID
joins the catalogue; workload ID/version/checksum identifies the exact persisted
workload definition. Runtime configuration overrides belong in a separate
immutable resolved-configuration snapshot, not silently in the workload digest.

The raw producer identifies the capture tool or adapter. The normalized producer
identifies the normalizer. Both record a numeric three-part version and a runner
image pinned by digest. These fields provide traceability, not proof that an
untrusted producer actually ran that image; the control plane must verify it.

## Artifact identity and integrity

Assign each stored artifact a UUID and bind that ID to its run, kind, URI, digest,
size, media type, and format. Never reuse an ID for different content. A URI
identifies an object, not a local filesystem path or an expiring signed URL.
V1 accepts S3 and HTTPS locations with no query string, fragment, or embedded
credentials. Authentication is supplied by the storage adapter at read time.

SHA-256 and size apply to exact bytes as stored, including any encoding,
line endings, or compression. Verify both before decoding. Do not canonicalize,
reformat, or migrate raw bytes in place. `mediaType` is a lowercase type/subtype
without parameters. `format` identifies the adapter-specific payload layout,
such as `k6-summary-json`; the producer version supplies its tool context.
Consumers must reject formats they cannot decode rather than guessing from a
filename. Artifact schemas validate reference syntax; the separate
`playwright-measurements/v1` contract validates that native browser payload.

A normalized envelope contains raw source references and inline metrics. After
writing its final UTF-8 JSON bytes, assign it a separate `kind: normalized`
artifact reference and compute that reference's checksum. The envelope never
contains its own checksum, which avoids a circular hash. A retry may reuse an
already registered reference only for the identical content/metadata; a changed
normalization produces a new artifact ID/location. Raw artifact IDs are retained.

The reference itself is metadata, not the referenced payload. Raw manifests
and normalized envelopes are separate documents. The raw manifest lists raw
payload references; the normalized envelope repeats only those raw references
actually used. Neither admits a normalized artifact as raw evidence. This
version does not describe derived-from-derived analysis graphs.

The eventual persistence layer must enforce ID immutability, retention and
access control. Hashes detect changed content; they do not prevent an object
from being overwritten or deleted. On retrieval, consumers must also verify
source references against stored raw manifests: run, test, workload, and window
must match. A schema-valid reference alone does not establish that relationship.

## Measurement windows and consistency

`measurementWindow` is the observed half-open interval `[start, end)`, excluding
warm-up and cooldown. It is not the total Job lifetime or the workload's planned
budget. Start must precede end. `createdAt` records envelope creation and must
not precede the measurement end. Synchronize producer clocks before relying
on these fields for cross-system telemetry correlation.

Timestamps require uppercase T/Z or an explicit numeric UTC offset. They support
up to six fractional second digits; leap seconds are excluded. Format checks
validate calendar dates and offsets. Semantic checks compare instants after
parsing their offsets, never their textual ordering.

Every listed artifact and metric must belong to the envelope's run. Artifact
IDs and URIs must be unique within an envelope. UUID comparisons ignore case.
There is one aggregate record per metric name in this initial envelope; combining
multiple repetitions, label sets, or windows under the same name is outside v1.
Keep those measurements in separate envelopes until their dimensions are defined.

Raw manifests require at least one raw artifact, and normalized envelopes require
at least one raw source and one metric. A generator failure with no measurement
window or an empty normalization is not represented as a successful empty
result. Preserve available artifacts separately and report that outcome through
the future lifecycle/analysis contracts. Envelopes do not themselves mean PASS.

## Missing statistics and result/v2

`result/v1` requires a positive sample count. Some summary formats provide
percentiles and means without the corresponding count, so v2 allows `samples`
to be absent or null. A known count must still be positive. Never substitute 0,
1, request count, or a fabricated sample population for an unknown metric count.

Other distribution fields retain the existing optional/nullable semantics.
An absent value or null is unavailable, not zero. Empty distributions are
structurally allowed but are not evidence of satisfactory performance. Do not
reconstruct percentiles from summary averages or manufacture individual samples.
Quality/SLO/regression policy is a later contract slice and must handle missing
information explicitly.

The new record reuses the established metric, threshold, metadata, and statistic
definitions through versioned schema references. This preserves compatibility
for known fields without loosening result/v1. Legacy threshold fields remain
possible, but this step does not implement or conflate scientific decisions.

## Migrating legacy results

1. Keep original raw files and the old array as immutable historical evidence.
2. Verify that array records belong to the same run and have unique metric names.
3. Convert each known v1 metric to v2 by changing its record schemaVersion to 2;
   preserve existing values. Missing counts from native summaries stay missing
   when producing new v2 records.
4. Supply the actual producer, workload checksum, observed window, and verified
   raw references. These cannot be inferred safely from the old metric array.
5. Build a normalized-result/v1 envelope, validate its schema and consistency,
   persist its final bytes, then create a separate normalized artifact reference.

If provenance is unavailable, retain the data as a legacy import rather than
claiming a conformant envelope with invented IDs, checksums, or timestamps.
Downgrading v2 with unknown counts to v1 is not possible without additional
evidence. Consumers must choose a supported version explicitly.

## Fixtures and validation

The k6 and browser raw payloads under `tests/fixtures/transport` are small
synthetic format examples. The k6 fixture has a mean and p95 but no count. The
browser fixture is schema-backed and has ten observed durations after two
excluded warm-up iterations; its example reports only the count, mean, minimum,
and maximum derivable from them. Neither fixture demonstrates a production run.

The examples' raw-data and workload checksums match checked-in bytes. The
standalone normalized artifact reference hashes the completed k6 envelope.
Storage locations and producer image digests are illustrative, not deployed
resources. The existing workload examples still contain placeholder configuration
and dataset hashes; transport validation does not turn those into verified inputs.

Fixture checksum tests intentionally fail if payload bytes are reformatted.
When intentionally changing a fixture, recompute SHA-256 and byte count and
update every reference to it, including any affected normalized envelope's
external reference. The archive includes the fixtures for inspection.

Run the repository's normal uv validation and test commands. Schema references
resolve offline. Development semantic checks enforce location, window, run-ID,
and uniqueness rules. Playwright checks additionally enforce cache/context
pairing, complete iteration coverage, deterministic ordering, and native timing
order; equivalent checks are required in each runtime consumer.
Only fixture tests read local payloads. The general validator does not download
artifacts or verify remote storage, native payload formats, or scientific quality.
