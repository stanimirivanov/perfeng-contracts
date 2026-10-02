# Native Worker API v2 candidate: baseline execution recipe

## TL;DR

- Candidate bundle `0.18.0` adds an independent `/native-worker/v2` protocol; v1 remains unchanged.
- V2 initially supports the repository-owned `search` journey, baseline diagnostics, Chromium and source-checkout runner artifacts only.
- An acquired lease includes the reviewed recipe needed to project a `RunnerConfiguration` without worker-selected measurement defaults.
- The Windows worker must remain unavailable for execution until the control plane and worker pin and implement this generation together.

## Scope and authority

The [v2 OpenAPI description](../api/native-worker/v2/openapi.json) and its examples, rejections and HTTP cases define the candidate wire contract. Accepted [ADR-0004](decisions/0004-version-native-worker-execution-recipes.md) governs the versioning decision; this candidate does not authorize a production rollout. The v1 protocol and its fixtures remain valid for existing presence and dormant transport clients. A v1 lease is not an executable v2 recipe.

V2 uses separate paths for presence, acquisition, renewal, release, upload grants, artifact registration and terminal reporting. Presence and acquisition require `protocolVersion: 2`; capabilities require `runnerContract: 2`. A v2 lease and its capability must stay within v2 operations. Do not silently translate an incomplete v1 assignment. Bearer identity, attempt/revision fencing, cancellation, presigned exact-key S3 `PUT`, artifact verification and terminal ordering retain the v1 security model.

## Complete baseline recipe

The lease still carries the server-reviewed catalogue test, workload ID/profile, SUT target, browser, diagnostic mode, execution artifact and artifact plan. `assignment.recipe` supplies the missing inputs: repository-owned journey, workload version and SHA-256, cache/page-reuse policy, warm-up and measurement counts, qualified host profile/version/fingerprint and evidence SHA-256, and headless/viewport/device-scale settings. The required two-slot plan uses `playwright-measurements/v2` and `raw-result/v2`; both slots are required. The initial v2 generation admits only `search`, `baseline`, `chromium` and `source-checkout`. No diagnostic capture selections or extra diagnostic artifacts are implied by baseline mode.

The projection to the current Playwright `RunnerConfiguration` is exact:

| Runner field | Reviewed lease source |
| --- | --- |
| `schemaVersion` | `2` |
| `runId`, `testId` | `runId`, `assignment.catalogueTestId` |
| `workload.id`, `.profile` | `assignment.workloadId`, `.profile` |
| `workload.version`, `.sha256` | `assignment.recipe.workloadVersion`, `.workloadSha256` |
| `scenario` | `assignment.recipe.scenario` |
| `diagnosticMode` | `assignment.diagnosticMode` (`baseline`) |
| `environment.profile.id`, `.version` | `assignment.recipe.environment.profileId`, `.profileVersion` |
| `environment.fingerprint` | `assignment.recipe.environment.fingerprint` |
| `target.baseUrl` | `assignment.target.baseUrl` |
| `browser` | `assignment.recipe.browserSettings` |

The worker must additionally compare `recipe.environment.profileId` and `evidenceSha256` with its current qualification evidence, and compare the assigned execution artifact with the qualified runner identity. The SUT `target.environmentId` is separate from the Windows host profile ID. The worker must verify that its capabilities include the assigned browser, diagnostic mode and artifact kinds before launching a browser. The `journeyId` selects repository-owned code; it is never a command supplied by the Run caller.

## Compatibility and rollout

This is an additive API generation in candidate bundle `0.18.0`, not an in-place extension of the closed v1 lease. Existing v1 consumers can remain pinned to `0.17.0`; strict bundle readers upgrading to `0.18.0` must recognize the additional API entry. The control plane must persist the exact reviewed v2 recipe and issue it unchanged across acquisition and retry. The Playwright worker must reject missing, unsupported or mismatched inputs before execution. Both consumers must pin the same reviewed bundle revision and prove v2 lease fencing, cancellation, uploads and terminal reporting before advertising `AVAILABLE`.

The v2 candidate does not migrate existing assignments or evidence, enable a Windows worker, or select a live target. Trace, memory, smoothness, Edge/Chrome and release archives require a separate contract review because the current runner modes and output artifacts do not map one-to-one to v1's diagnostic vocabulary and two-slot artifact plan. Rollback disables v2 acquisition without rewriting accepted evidence; v1 remains independently available.
