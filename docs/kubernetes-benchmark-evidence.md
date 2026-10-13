# Kubernetes benchmark admission and evidence

## TL;DR

- Catalogue v2 admits kube-burner OCI images and verified release archives; v1 stays unchanged.
- `kubernetes-benchmark-evidence/v1` distinguishes preflight observations from evidence for an actual Run.
- Stable environment/profile identities are separate from changing pressure, usage and timestamps.
- Every required check reports PASS, FAIL or UNKNOWN; unknown observations are never healthy zeros.
- ACCEPTED means the declared profile's checks passed, not authorization, isolation, scientific quality or baseline approval.
- Consumers verify bytes, trusted profiles, freshness, capture coverage and comparison eligibility before acting.

## Admission and provenance

Candidate bundle 0.22.0 adds kube-burner to catalogue v2 only. The workload
retains its open, iteration-budgeted model. The executable identity is either
an OCI image digest or a release archive with separate archive/executable hashes;
native source-checkout execution is not admitted for this tool. Tool and workload
must agree, schedules must select declared profiles, and immutable definitions
must not reuse an ID/version with different content.

For newly admitted Kubernetes OCI entries, the executable image is not proof
that the workload configuration was included in that image. Consumers must
verify the selected source/configuration bytes, every referenced template and
the complete resolved execution input set before launching the tool. Mounted
configuration must have an immutable reviewed source, exact content hashes and
captured substitution values; it is not a mutable override. The existing
configuration checksum identifies only the named entry file. Candidate image
identity must describe the benchmark workload, not the unrelated generator image.

Reuse `raw-result/v2` for OCI/archive producer provenance, the existing
pod-latency artifact formats and `artifact/v1` integrity references. Retain
resolved configuration/template evidence and measurement-scoped benchmark evidence
in the raw manifest. Publish that manifest only after its declared objects are
durable and verified. No new Run Management or Native Worker API is introduced.

## Stable comparison identities

`profile` identifies the reviewed qualification/capture policy by ID, version,
exact persisted-byte SHA-256 and purpose. Thresholds, required node placement,
minimum capacity, maximum interference, freshness and sampling cadence belong
to that versioned policy in the environment repository, not this shared schema.
The policy must specify how all six checks are evaluated. A producer cannot
choose its own thresholds, omit a check or grant itself eligibility.

`environment` repeats the selected ID/version, SHA-256 of the exact immutable
environment descriptor, and comparison fingerprint. The descriptor uses the
existing `environment/v1` shape; a consumer must verify its bytes and require
the facts needed by the reviewed profile. A structurally valid sparse descriptor
is not automatically qualified. The SHA-256 is not the hash of this evidence
document, and the fingerprint must not incorporate transient usage or timestamps.

`target.clusterId` and the observed `kube-system` namespace UID identify the
particular cluster incarnation for execution verification and target reservations.
The UID is an observation, not an API endpoint or permission. Consumers must
compare it with trusted target state, not merely echo the expected UID. A
recreated cluster must be reviewed and qualified again.

For M04's initial path the cluster environment is a controlled comparison
condition, while the actual benchmark Pod image/configuration is the software
candidate. Comparing Kubernetes, CNI or node-configuration changes as candidates
needs a separately reviewed compatibility rule; do not waive environmental
equality silently. A profile with `purpose: integration` proves local functional
integration only. It is not a production-performance cohort, even when ACCEPTED.

## Capture scope and observations

`scope.kind: preflight` deliberately has no Run identity. It may be captured
before admission. `scope.kind: measurement` requires an actual Run ID, test ID
and exact workload identity. Preflight cannot substitute for Run evidence.

The capture window is UTC/offset-qualified RFC 3339 time. Preflight may be an
instant; measurement must have positive duration and cover the manifest's full
measurement window. Sampling can include surrounding phases, but a consumer
must not relabel warm-up/cooldown observations as measurement iterations.
Profiles must require sufficient coverage, cadence and freshness: one sample
can satisfy structure but does not prove a sustained absence of interference.

`nodes` declares selected observed nodes: name/UID, actual Kubernetes and
container-runtime versions, architecture and allocatable CPU/memory. CPU uses
integer millicores and memory uses integer bytes. `samples` refers to those
UIDs, increases in time per node and records Ready/MemoryPressure/DiskPressure/
PIDPressure as TRUE, FALSE or UNKNOWN. Node replacements are not interchangeable
with earlier observations. The document is bounded to 256 nodes and 4096 samples;
longer captures require a reviewed sampling policy, not silent truncation.

Usage has two mutually exclusive shapes:

- `metrics-api`: actual non-negative integer CPU millicores and memory bytes,
  with the provider's positive measurement window ending no later than the
  observation time. The window must lie within the declared capture window.
- `unavailable`: a nonblank safe reason and no numeric usage fields. Missing
  metrics cannot be replaced by zero or be treated as an interference PASS.

Node metrics do not establish host-level isolation. Shared-host Docker/kind
contention and other workloads must be accounted for by the profile and
interference check; no metrics-server installation or broad telemetry stack
is mandated by the schema. Consumers that cannot obtain required observations
must retain UNKNOWN and report which capture prerequisite is missing.

## Check and eligibility semantics

Exactly one check is required for each of cluster identity, node readiness,
placement, capacity, resource pressure and interference. Each has a nonblank,
credential-free reason. Summary status follows deterministic precedence:

1. Any FAIL means REJECTED, even when other checks are UNKNOWN.
2. Otherwise any UNKNOWN means UNKNOWN.
3. Otherwise all checks PASS and nonempty node/sample evidence means ACCEPTED.

After schema validation, the reference semantic checker rejects duplicate node
identities, undeclared sample nodes, non-increasing or out-of-window samples,
missing selected-node coverage presented as PASS, and contradictory readiness
or pressure claims. Observed not-Ready or pressure conditions require FAIL;
unknown/incomplete conditions require UNKNOWN unless a known failure dominates.
Unavailable usage cannot establish an interference PASS.

The optional context checker binds cluster/fingerprint and Run/test/workload,
requires supported kube-burner provenance and full measurement-window coverage.
It does not download artifacts, verify hashes against content, evaluate profile
thresholds, check sample freshness against the current clock, reserve targets,
authorize cleanup or approve baselines. Producers and consumers implement these
obligations in their owning repositories. Consumers must also bind this evidence
artifact's Run/integrity reference to the raw manifest.

Rejected/unknown captures are retained for diagnosis but cannot establish
comparable baseline eligibility. ACCEPTED is necessary evidence, not sufficient
permission: sample quality, approved-reference selection and policy/regression
outcomes remain separate. The contract does not assert statistical significance
from the existing ten-observation smoke workload.

## Compatibility and verification

The new contract is additive to the bundle; strict inventory readers must
recognize it explicitly. Catalogue v2's closed tool union changes and old
readers must opt in. Catalogue v1, environment v1, workload v1, raw-result v2,
baseline/result/report schemas and both APIs retain their existing meaning.
The analysis implementation must explicitly adopt OCI kube-burner provenance;
updating schemas alone does not make its archive-only reader compatible.

All examples are synthetic, non-deployable conformance fixtures, including
their hashes, UIDs, image/configuration/source identities and status claims.
They do not qualify the local cluster or publish a runtime bundle. Preserve
historical bundle revisions and raw evidence; rollback repins consumers to
their prior reviewed revision rather than relabeling OCI execution as an archive.

Run `make verify` and `make validate`. Strict Effect and generated JSON Schema
tests cover scopes, completeness, summary precedence, units and closed shapes;
offline Python tests cover temporal/node consistency and cross-document binding.
See [ADR-0008](decisions/0008-separate-kubernetes-benchmark-evidence.md).
