# Workload and test-catalogue contracts

These contracts implement the workload/catalogue slice of proposal sections
16-17, 30, 63, and 78. They describe k6 and Playwright workloads; cluster benchmark
adapters remain later work. They do not change the existing run-metadata schema.

## Responsibility and identity

A workload is a versioned profile for a tool. A catalogue assigns workloads to
named tests and records ownership, criticality, source, tool version, and runner
image. The test ID is the stable cross-run identity; changing a Git revision
does not require a new test ID. The source SHA and image digest identify the
specific implementation executed.

Workload IDs and versions identify immutable definitions. Change a workload
version whenever its configuration, phases, model, or dataset changes. A
catalogue may reuse an identical workload definition, but may not give different
definitions the same ID/version pair. V1 version labels are three numeric
components (for example `1.0.0`); prerelease labels and floating labels such as
`latest` are deliberately outside this initial contract.

Catalogue entries embed complete workloads so a selected profile is unambiguous.
The standalone workload examples demonstrate the same shape independently.
There is one workload per profile per test. `schedule` assigns a profile to a
pipeline tier; it is not a cron expression or an instruction to deploy a scheduler.

## Field semantics

| Field | Meaning |
| --- | --- |
| Workload `tool` | `k6` or `playwright`; must match the containing test's tool |
| `profile` | Testing purpose: smoke, average, regression, stress, capacity, or soak |
| `model` | Open: arrivals are externally scheduled; closed: the next iteration depends on the previous one finishing |
| `configuration.path` | Relative POSIX path inside the pinned runner artifact |
| `configuration.sha256` | Lowercase SHA-256 of the exact configuration file bytes used |
| `phases` | Explicit warm-up, measurement, and cooldown budgets; only measurement contributes to the reported measurement window |
| `dataset.kind: none` | No separately versioned dataset; not a wildcard for an unknown dataset |
| `dataset.kind: versioned` | Dataset ID, version, exact content checksum, and deterministic generation seed |
| Catalogue `source` | HTTPS repository, full Git SHA, and relative scenario entrypoint |
| Catalogue `artifact.image` | Immutable OCI image reference ending in `@sha256:<64 lowercase hex characters>` |
| Catalogue `tool.version` | Recorded runner tool version, independent of the workload version |

For k6, phase units are seconds. An adapter must verify that native executor
timings agree with the declared budgets. This contract does not validate k6's
native configuration language. Explicitly classify each supported executor as
open or closed when implementing the adapter; do not infer the model from the
profile name.

For Playwright, this initial contract uses a closed model and iteration counts.
One iteration means one complete business journey. Warm-up iterations are
excluded from measurements. Browser build, cold/warm context strategy, retries,
workers, and timing definitions must be pinned in the runner/configuration and
recorded by the eventual adapter. Open browser load and time-budgeted browser
execution are not defined by this v1 contract.

Warm-up and cooldown may be zero. Measurement must be positive. These are
declared budgets, not observed timestamps. Later run/artifact contracts record
actual phase boundaries and whether a run completed them. Schema-valid input
does not prove that a runner obeyed those boundaries.

## Hashing and resolution

1. Package the configuration with the runner image, including any imported
   modules. Compute `configuration.sha256` from the exact named file bytes in
   that artifact, after build-time line-ending/encoding processing.
2. Do not parse/reformat JSON, normalize YAML, reorder keys, or strip whitespace
   before hashing. Byte changes require a new digest. Hashing a source checkout
   is insufficient if packaging changes its bytes.
3. Pin the complete runner image by digest. This also pins imported source and
   configuration modules; hashing only the entry configuration cannot do that.
4. Hash a versioned dataset's exact immutable file/archive bytes. If generation
   is required, record the seed and pin the generator in the runner image.
5. For workload-definition or resolved-configuration artifact hashes, first
   persist their exact UTF-8 JSON bytes, then hash those bytes. Do not include a
   document's own digest inside its hash input. The reference/digest envelope is
   defined by [artifact/result transport](artifact-and-result-transport.md).

Before execution, the consumer must verify configuration/data checksums, tool
version, source/image correspondence, and the entrypoint. Reject missing or
mismatched inputs. Resolve paths within the extracted artifact, including a
check that symlinks cannot escape it. JSON Schema checks path spelling only.

Runtime configuration overrides and environment interpolation require a separate
resolved configuration snapshot; they must not silently alter the meaning of
the recorded file checksum. Record secret reference names/versions rather than
secret values. Candidate, reference, environment, and run IDs are execution
context, not part of the reusable workload definition. Seed or otherwise record
all execution-affecting randomness when reproducibility is required.

## Migrating the prototype k6 files

| Prototype input | New location/interpretation |
| --- | --- |
| `tests/k6/catalogue.yaml` API version, kind, metadata, test ID/owner/criticality | Retained in catalogue; JSON examples use the same object model as YAML |
| Test `tool: k6` | Object with tool name and exact version; add pinned source and image |
| `profiles: [...]` | Embedded workload definitions; each declared profile must have a real configuration |
| `schedule` | Preserved after checking every selected profile is declared |
| `metrics` | Reuse the existing normalized metric descriptor via a local schema reference |
| `workloads/<profile>/<scenario>.json` | Remains native k6 configuration inside the runner; reference its path and checksum |
| `workloads/registry.json` descriptions and typical values | Authoring guidance, not authoritative execution configuration |

The prototype catalogue and registry disagree: for example the registry lists
checkout's average profile while the catalogue omits it, and search's registry
lists stress/average while its catalogue lists smoke/regression. Reconcile the
actual available configurations with owners during runner extraction. Do not
invent missing profiles or silently choose one list as authoritative.

The checkout scenario also declares inline `options`. The future adapter must
resolve and test which options actually reach k6 before claiming that the
referenced configuration describes the execution. Preserve native SLO thresholds;
they are not automatically regression decisions.

The k6 example uses the prototype checkout smoke profile's total 120 seconds
as measurement, with zero excluded warm-up/cooldown. Its ramps are not implicitly
relabelled as warm-up. Any later change to the measurement selection requires a
new workload version and corresponding runner behaviour.

The browser example is a proposed fixture journey, not an extraction of a
working browser benchmark. All example image/configuration/dataset digests and
source SHAs are illustrative placeholders, not published artifacts or verified
source/image attestations. Tool versions are example labels, not recommendations.

## Validation and compatibility

Run the normal repository validation and unittest commands. All schema references
resolve from the manifest without network access. Schema checks enforce required
versions, phase bounds, tool/model combinations, digest syntax, and relative paths.
`check_catalogue_consistency` in the development validator also checks unique test
IDs, one workload per profile, tool agreement, consistent workload versions, and
schedule membership. Consumers must implement equivalent semantic checks after
schema validation; the Python helper is reference test tooling, not a runtime API.

The bundle validator accepts JSON fixtures. YAML catalogues must first be parsed
with duplicate-key rejection into equivalent JSON-compatible data. Quote version
labels in YAML. A native k6 configuration alone is not a workload document.

Bundle `0.2.0` adds two contracts without modifying the existing four schemas.
Old readers do not automatically understand these new documents. Consumer
adoption and a stable release remain explicit later steps.
