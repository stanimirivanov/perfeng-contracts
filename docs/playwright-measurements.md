# Playwright measurements

`playwright-measurements/v1` defines the original native JSON payload produced
by the Playwright runner. V2 retains its samples and adds page lifetime,
diagnostic mode, and browser-environment identity. Both record individual
semantic browser timings and the
execution context required to compare them. It does not define orchestration,
artifact upload, aggregation, statistical quality, or a performance verdict.

## Measurement semantics

Each measurement identifies a metric, a one-based measurement iteration, and
the observed duration in milliseconds. Metric names use the shared metric-name
grammar. A producer may emit more than one metric per iteration, but every
metric must cover every declared measurement iteration exactly once. Records
are ordered first by iteration and then by metric name so identical executions
produce a deterministic document layout.

`measurementWindow` is the half-open interval containing measured iterations.
Warm-up is excluded. The start must precede the end, and `createdAt` cannot
precede the end. Durations should use the browser's monotonic clock around the
semantic action and observable completion condition; wall-clock timestamps are
only for correlation and artifact provenance.

## Repeatability context

The workload identity binds the payload to an immutable workload definition.
The scenario records the actual warm-up and measurement iteration counts.
Warm-up measurements are discarded, not mixed into the reported samples.

Cache and browser-context behavior are explicit:

- `cold` requires a new browser context for each iteration;
- `warm` requires one browser context reused for the run.

This distinction prevents cold and warm observations from being compared as if
they belonged to the same population. V1 intentionally does not define a mixed
profile or an implementation-specific cache-clearing operation.

V2 separately declares `pageReuse`. A warm navigation run may reuse the context
while creating a page per iteration. An SPA steady-state or memory run may reuse
both page and context. A page cannot outlive its context, and cold runs require
both to be recreated per iteration. Page reuse changes observable application
state and therefore defines a different comparison cohort.

V2 also declares one diagnostic mode. `baseline` means the stable semantic
measurement has no diagnostic collector overhead. `lightweight`, `trace`,
`memory`, and `smoothness` disclose increasingly specialized collection. These
values describe instrumentation, not test outcomes. Do not compare diagnostic
timings with baseline timings as if their overhead were identical.

The runtime and browser objects define a comparison cohort: Playwright and Node
versions, operating-system platform and architecture, browser engine and exact
reported version, headless mode, viewport, and device scale factor. Normalizers
must preserve this provenance and analysis must not silently combine different
cohorts.

V2's environment profile and fingerprint bind the measurement to a separately
captured `browser-environment/v1` document. The compact identity is repeated in
the measurement; detailed hardware and calibration data remains a separate
artifact.

## Transport boundary

The payload is stored as immutable UTF-8 JSON and referenced from a
`raw-result/v1` manifest using `format: playwright-measurements-json`. SHA-256
and byte count describe the exact stored bytes. The native payload repeats run,
test, workload, and window identity so a consumer can reject a payload attached
to the wrong manifest. Consumers verify the artifact reference before decoding,
validate this schema, apply its semantic checks, and then compare those repeated
identities with the manifest.

The payload contains samples, not aggregates or PASS/FAIL decisions. A
normalizer derives `result/v2` statistics from the observed durations without
inventing samples. Quality, SLO, and regression evaluation remain separate
analysis concerns.

## Migrating from v1 to v2

Do not relabel stored v1 bytes. A new v2 producer must observe and emit the
actual page-reuse policy, diagnostic mode, and environment identity. The
existing v1 context rule remains unchanged. Historical v1 data without those
facts stays v1 rather than receiving invented values.
