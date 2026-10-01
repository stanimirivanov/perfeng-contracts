# ADR-0004: Version complete Native Worker execution recipes

- Status: Proposed
- Date: 2026-10-01
- Milestone: M03 — Native Browser Decision Loop
- Deciders: Repository owner and affected consumer maintainers
- Supersedes: None
- Superseded by: None

## TL;DR

- Native Worker API v1 identifies reviewed work but does not carry enough inputs to execute the existing Playwright runner without worker-selected defaults.
- Propose a v2 lease assignment containing a complete, server-reviewed execution recipe; keep v1 wire behavior unchanged.
- The worker must verify the recipe against its qualification evidence and supported capabilities before starting a browser.
- Do not advertise availability or acquire work until the contract, control plane and worker implement the same recipe.

## Context

Native Worker API v1 leases provide the Run, attempt, catalogue test, workload and profile IDs, target URL, browser family, diagnostic mode, execution artifact and artifact plan. The existing Playwright runner additionally requires a journey selection, workload version and content hash, cache and page-reuse policy, warm-up and measured iteration counts, an environment profile version and fingerprint, headless/viewport/device-scale settings, and mode-specific diagnostic capture iterations. These values affect measurement meaning, artifact validity or comparability. The worker cannot infer them safely from the IDs or its local preferences.

V1's lease and assignment objects are closed. Adding required fields to their existing response changes what old clients accept; making the fields optional would still leave an executable lease underspecified. The presence-only worker deliberately reports `UNAVAILABLE`. Its existing lease, upload and terminal transports do not make the execution loop safe to enable.

## Decision

Propose a Native Worker API v2 lease assignment with a complete, immutable execution recipe resolved from reviewed control-plane policy. The recipe must specify:

- the supported repository-owned journey identifier and exact workload ID, version, profile and SHA-256 identity;
- cache profile, page reuse, warm-up count and measured iteration count;
- the qualified environment ID, evidence SHA-256, profile version and measurement fingerprint;
- browser family, headless setting, viewport and device scale factor;
- diagnostic mode and its mode-specific capture iteration selection; and
- the already reviewed target URL and execution-artifact identity, without caller- or worker-selected substitutions.

The contract PR will define closed shapes and bounded values, including which diagnostic settings are absent for modes that do not use them. The control plane will persist the exact recipe with the lease and return that same recipe on acquisition. The worker will reject an unsupported journey, mismatched local source or environment evidence, unsupported browser/mode, or any incomplete recipe before browser execution. It will not fill a missing field from a worker-local default.

V1 remains independently valid for existing presence and protocol clients; it is not silently reinterpreted as an executable assignment. V2 acquisition and lease-scoped operations will use an explicit API generation so strict v1 readers cannot mistake a v2 response for v1. The exact endpoint inventory and conformance fixtures belong to the follow-up contract implementation.

## Alternatives considered

### Use worker-local profiles keyed by v1 IDs

- Benefits: No new wire generation; small response.
- Costs and risks: The same lease can mean different measurements on different hosts or worker revisions, and the server cannot attest the effective recipe.
- Reason not selected: It would make worker configuration an unreviewed execution authority.

### Add optional recipe fields to v1

- Benefits: Less API duplication during rollout.
- Costs and risks: Strict v1 readers reject unknown fields, and optional fields leave old or partial leases executable only through guessed defaults.
- Reason not selected: The compatibility and completeness rules cannot be expressed safely as an additive v1 change.

### Fetch workload and environment documents after acquisition

- Benefits: A smaller lease response and reuse of document identities.
- Costs and risks: Additional authenticated endpoints, mid-attempt version races, offline/cache behavior and a larger failure surface before execution.
- Reason not selected: The lease needs one frozen, auditable execution decision. A future implementation may carry exact document references only if retrieval and integrity are part of that frozen contract.

## Consequences

### Positive

- One server-reviewed recipe determines the executable browser work and the raw measurement identity.
- The worker can fail closed on unsupported or mismatched inputs before creating evidence.
- Exact recipe persistence supports retry, restart diagnosis and comparison with registered artifacts.

### Negative

- A new API generation and coordinated control-plane/worker rollout are required.
- The server must resolve and validate more execution details before leasing work.

### Neutral or follow-up

- This ADR does not enable a worker, add an API field, change a published bundle or select a live target.
- The contract implementation must add positive and rejection fixtures for every recipe dimension and document coexistence with v1.
- The control plane must prove the stored recipe equals the issued lease and remains stable across renewal and restart.
- The worker lifecycle coordinator must bind runner configuration and artifact publication to the recipe, then enable availability only after cancellation and process-tree cleanup are tested.
- Local infrastructure must provide the reviewed HTTPS control-plane and object-store paths required by a native Windows worker.

## Compatibility and migration

Publish v2 as a new candidate contract generation. Preserve the v1 paths, fixtures and meaning while consumers migrate. Pin the same reviewed v2 bundle in the control plane and Playwright worker; reject mixed versions rather than translating an incomplete v1 lease into v2. Existing v1 presence and dormant lease data require no evidence migration. Any persisted native assignment made under v1 must remain v1 or be explicitly replaced before native execution is enabled.

## Security and operations

The recipe contains no bearer credential, presigned URL or operator-selected command. It cannot change the authenticated worker, target authorization, lease capability, attempt fence or server-selected object key. The control plane authorizes and qualifies before issuing work; the worker verifies its local source, environment evidence and capabilities again before execution. Diagnostics and failure messages must not expose sensitive recipe-derived URLs or credentials. Rollback disables v2 acquisition while retaining the versioned contract and any accepted evidence.

## Validation

Review the v2 schema and examples against the current `RunnerConfiguration` and Native Worker v1 lease fields. Contract tests must reject missing, contradictory, extra and out-of-range recipe fields. Control-plane integration tests must prove reviewed resolution, durable identity and stale-lease fencing. Worker tests must prove no browser launch on mismatch, exact configuration projection, bounded cancellation, and artifact identities matching the issued recipe. End-to-end acceptance must use an authorized representative Windows host and reviewed HTTPS endpoints; Linux CI proves behavior, not performance comparability.
