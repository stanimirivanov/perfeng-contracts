# PR-sized implementation sequence

Source of requirements: performance-platform/docs/project-proposal.md.
The polyrepo migration blueprint supplies the repository and language boundaries.
Each numbered item below is a separate PR and includes text suitable for a
GitHub issue. Only step 1 is implemented by this change. Repeat the same
issue/implementation/validation handoff for subsequent steps.

## Step 1

Repository: `perfeng-contracts`

Title and body: [Extract versioned performance contracts with history and CI validation](issues/001-contract-foundation.md).

## Step 2

Repository: `perfeng-contracts`

Title: Define reproducible workload and test-catalogue contracts

Body: Add schemas for test identity, workload profiles, tool/artifact versions,
dataset identity, and measurement phases (proposal sections 16-17, 30, 63, 78).
Use existing k6 catalogue and workload files as migration inputs. Document any
required conversion instead of silently changing them. Acceptance: valid k6
and browser examples; rejected missing versions and invalid workload models;
documented workload/configuration hashing inputs; CI validates all examples.
Depends on step 1.

## Step 3

Repository: `perfeng-contracts`

Title: Define raw-artifact and normalized-result transport envelopes

Body: Define immutable artifact references, checksum, media type, run window,
producer version, contract version, and a normalized multi-metric result
envelope (sections 29, 35-36, 78). Acceptance: k6/browser fixture coverage;
no requirement to fabricate missing statistics; separate raw and derived
artifact identities; explicit migration from existing array examples.
Depends on step 2.

## Step 4

Repository: `perfeng-contracts`

Title: Define performance policies and independent decision outcomes

Body: Add SLO/regression policy and analysis-output schemas with separate
measurement quality, requirement, and regression outcomes (sections 41-44,
73-74). Acceptance: examples can pass SLO while regressing; inconclusive data
does not produce a false pass; policies record version and observe/inform mode.
Stable v1 publication is a subsequent release decision after consumers agree.
Depends on step 3.

## Step 5

Repository: `perfeng-k6`

Title: Extract k6 scenarios and workload profiles into a standalone runner

Body: Preserve history for tests/k6 and replace monorepo-only tooling. Keep
scenario/profile separation and produce local raw artifacts conforming to the
accepted contracts (sections 16-20, 80). Acceptance: smoke tests exercise a
deterministic fixture target; failure exits are retained; standalone image
build; pinned tool version; no prototype-relative runtime paths.
Depends on steps 2-3.

## Step 6

Repository: `perfeng-analysis`

Title: Extract the k6 normalizer as a package and CLI

Body: Preserve normalizer history and fixtures, remove orchestration/database
dependencies, and emit contract-valid normalized output (sections 29, 36, 80).
Acceptance: offline fixture-driven CLI; tests for absent statistics and malformed
input; original raw data unchanged; no fabricated percentiles or sample counts.
Depends on steps 3 and 5.

## Step 7

Repository: `perfeng-environment`

Title: Add a portable sibling-repository workspace manifest

Body: Register the seven actual GitHub repositories with relative sibling paths
and bootstrap/status scripts. Replace the earlier suggested absolute C:\Source
manifest with a portable workspace rooted above perfeng-environment. Acceptance:
PowerShell and shell instructions; cloning never overwrites existing checkouts;
source refs are separate from deployed artifact versions. No submodules needed.

## Step 8

Repository: `perfeng-environment`

Title: Extract and validate the local Kubernetes environment

Body: Preserve local cluster scripts and Helm history; document namespaces,
generator placement, secrets, and local storage (sections 14-15, 79).
Acceptance: manifests render; documented cluster up/down; health checks; sample
SUT deploys; no committed credentials; local-only configuration identified.
Depends on step 7.

## Step 9

Repository: `perfeng-environment`

Title: Execute an artifact-pinned k6 smoke Job with durable raw output

Body: Connect the extracted k6 runner to local Kubernetes and capture results
(sections 19-20, 36, 79-80). Acceptance: Job uses an immutable image reference;
run ID and measurement window recorded; raw artifact upload survives Job cleanup;
timeouts and tool failures are distinguishable from SLO failures.
Depends on steps 5 and 8.

## Step 10

Repository: `perfeng-contracts`

Title: Define the run-management OpenAPI contract

Body: Specify create/get/cancel run operations, idempotency, validation errors,
and lifecycle state vs. analysis outcomes (sections 12-13). Acceptance: request
and response fixtures; lifecycle transition documentation; API linting and
compatibility tests. Depends on steps 2-4.

## Step 11

Repository: `perfeng-control-plane`

Title: Implement the Go run domain and HTTP API

Body: Implement the accepted run API and state transitions behind a repository
interface (sections 12-13). Acceptance: in-memory adapter for focused tests;
idempotent create and cancel; invalid transitions rejected; no statistical
algorithms in the service. Depends on step 10.

## Step 12

Repository: `perfeng-control-plane`

Title: Add PostgreSQL run persistence and migrations

Body: Port the prototype storage behaviour and migration intent into a Go
adapter (sections 37-38). Acceptance: migration from empty DB, durable run and
artifact references, concurrency and restart tests, documented schema ownership.
Depends on step 11.

## Step 13

Repository: `perfeng-control-plane`

Title: Dispatch and reconcile Kubernetes test Jobs

Body: Add a Kubernetes adapter for the accepted lifecycle (sections 13-14, 79).
Acceptance: duplicate reconciliation does not launch duplicate Jobs; cancellation,
timeouts, restart recovery, and Job failures tested; artifact collection state
is explicit. Depends on steps 9 and 12.

## Step 14

Repository: `perfeng-control-plane`

Title: Collect artifacts and orchestrate normalization Jobs

Body: Connect completed test Jobs to immutable artifact references and dispatch
the analysis CLI (sections 35-38). Acceptance: retries cannot duplicate final
results; invalid artifacts and failed analysis remain distinct from regression;
normalized results can be retrieved; restart recovery tested.
Depends on steps 6 and 13.

## Step 15

Repository: `perfeng-playwright`

Title: Extract a browser performance runner with semantic timing

Body: Replace placeholder browser tests with one deterministic fixture journey
and a browser-side measureInteraction helper (sections 21-28, 81). Acceptance:
action-to-visible measurement, browser version, cold/warm scenario metadata,
failure traces, and contract-valid raw output. Preserve useful source history.
Depends on steps 2-3.

## Step 16

Repository: `perfeng-environment`

Title: Assemble the first API-to-analysis end-to-end environment

Body: Pin control-plane, k6, analysis, and browser artifacts and document a
reproducible end-to-end smoke run. Acceptance: API creates a run, Job executes,
raw data persists, analysis produces normalized output, and the result can be
retrieved after a service restart. Dependencies: steps 14 and 15.

## Later proposal phases

After the first vertical slice, split each of these into concrete PR-sized
issues with fixture-based acceptance criteria before implementation:

- Observability correlation (phase 5): environment config, then control-plane
  run-window collection, then analysis correlation.
- Data platform and deterministic gates (phases 6-7): storage/retention and
  dashboards, then analysis requirement evaluation, then CI reporting.
- Quality and statistics (phases 8-9): calibration fixtures, quality rules,
  reference compatibility, baseline lifecycle, then noise-aware comparison.
- Cluster workloads (phase 10): first owned perfeng-k8s benchmark, then optional
  telemetry export and deployment integration.
- Historical analysis (phase 11): OpenSearch environment configuration, then an
  Orion adapter behind the perfeng-analysis historical interface.
- Detector validation and blocking gates (phases 12-13): controlled regressions,
  measured false-positive/negative rates, then an explicit blocking-mode rollout.
- Diagnosis, selection, bisect, capacity, and optimization (phases 14-18): each
  remains gated by the preceding measurement and decision-quality evidence.
