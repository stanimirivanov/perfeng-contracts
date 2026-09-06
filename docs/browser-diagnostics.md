# Browser environments and diagnostics

Browser performance results are meaningful only within a known execution and
capture cohort. `browser-environment/v1` records the host and its calibration;
`browser-diagnostics/v1` records what diagnostic collection was attempted and
where its immutable evidence is stored. Neither document defines a performance
threshold or verdict.

## Browser environment

An environment profile is a versioned operational specification such as
`windows-mainstream/1.0.0`. The fingerprint identifies the exact stable profile
inputs selected by the environment owner. The per-run document additionally
records current capacity and calibration values. Changing available memory or
idle CPU does not create a new profile version, but can reject that run.

Host identity covers physical versus virtual execution, OS build and
architecture, CPU capacity, memory, GPU acceleration and driver, display size,
scale and refresh rate, and power state. Browser identity includes engine,
channel, exact version, and headless mode. Values that cannot be measured must
not be replaced by attractive defaults; define another profile generation if a
required field must change.

`ACCEPTED` calibration requires an empty reason list, a synchronized clock, and
hardware rendering. `REJECTED` requires at least one reason. The semantic checks
also reject impossible CPU and memory relationships and require the calibration
memory observation to match the host snapshot.

The example describes a synthetic Windows reference profile. It is not a claim
about an average customer device. Production profile values should come from
owned device telemetry or an explicit product decision and should be reviewed
when the user population changes.

## Diagnostic manifest

A diagnostic manifest binds its run, test, workload, environment, page/context
lifetime, capture mode, selected iterations, sources, and capture window. It
references evidence rather than embedding traces or heap snapshots. All
artifact references are raw and immutable.

Capture status has four meanings:

- `COMPLETE`: evidence was produced with no known loss and has no reasons;
- `INCOMPLETE`: useful evidence exists but a stated limitation applies;
- `FAILED`: capture failed and has no artifact reference;
- `NOT_SUPPORTED`: the pinned environment cannot perform the capture.

A trace always records `dataLossOccurred`. It is `false` for a complete trace,
`true` when Chrome reported buffer loss, and may be `null` if collection failed
before the collector learned the trace-loss state. Reported loss makes the trace
incomplete; it does not invalidate independent semantic measurements.

Lightweight mode accounts for an observations artifact. Trace and smoothness
modes account for a trace. Memory mode accounts for before and after heap
snapshots. A failed or unsupported required capture still satisfies accounting
when its status and reason are explicit; it does not become successful evidence.

Deep diagnostic modes require `cdp` among their declared sources. That
explicitly marks the Chromium-specific boundary. Standards-based observations
can also declare `web-performance`; Playwright events and Windows-native
telemetry have separate source values.

## Artifact roles

The manifest defines stable roles and formats for observations, sanitized
network summaries, console diagnostics, Chrome traces, V8 CPU/allocation
profiles, heap snapshots, screenshots, and video. Raw tool formats are retained
so improved analysis can reprocess them. Their contents receive separate
contracts only when the platform is ready to depend on a stable normalized
shape.

Capture scope is either the run or one declared measurement iteration.
Iteration-scoped evidence cannot point at an iteration outside
`captureIterations`. Artifact IDs and URIs are unique within the manifest and
every artifact belongs to the manifest run.

## Measurement isolation

Tracing, CPU profiling, heap tracking, forced garbage collection, screenshots,
and video can perturb the application. Store their timings under the declared
diagnostic mode and do not silently use them as baseline regression samples.
A baseline run and a diagnostic follow-up may share workload intent, but they
are separate executions and artifacts.

Memory diagnosis normally reuses one page and context for repeated SPA actions.
Warm-navigation timing commonly reuses a context but creates a page for each
iteration. These are distinct v2 scenarios. V1 has no page-lifetime claim and
must not be interpreted as either one.

## Privacy and retention

Traces, profiles, heap snapshots, screenshots, and videos are always classified
as sensitive by bundle validation. They can contain source locations, DOM text,
retained strings, URLs, credentials, or personal data. Network and console
summaries may be marked non-sensitive only after their producer applies the
documented sanitization policy. Access control, encryption, retention, and
redaction belong to storage and environment implementations; a checksum does
not provide any of them.
