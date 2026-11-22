# ADR-0005: Retire the undeployed Native Worker v1 candidate

- Status: Accepted
- Date: 2026-10-06
- Milestone: M03 — Native Browser Decision Loop
- Deciders: Repository owner and affected consumer maintainers
- Supersedes: ADR-0004's v1/v2 coexistence requirement only
- Superseded by: None

## TL;DR

- Native Worker v1 was never deployed and cannot supply the complete reviewed
  execution recipe required by the Playwright runner.
- Keep `/native-worker/v2` and its wire version 2, but make it the only supported
  Native Worker generation in the current candidate bundle.
- Remove v1 contracts, validators, fixtures and consumer code in three
  repository-scoped PRs; do not rewrite historical candidate revisions.
- Coordinate control-plane and worker rollout before enabling acquisition.

## Context

[ADR-0004](0004-version-native-worker-execution-recipes.md) selected a separate
v2 generation because v1 leases lack the complete execution recipe. It also
required keeping v1 alongside v2 during migration. That coexistence would be
appropriate for a deployed protocol, but v1 was never deployed. Retaining two
candidate APIs now duplicates routes, fixtures, validators and consumer modes
without preserving production compatibility. The current implementation work
targets v2, and the historical v1 bundle remains recoverable from Git.

## Decision

Retire `native-worker/v1` from the active bundle. Keep the existing
`native-worker/v2` paths, `protocolVersion: 2`, `runnerContract: 2`, and v2
OpenAPI and fixture meanings unchanged. Use un-suffixed names for the one
supported Native Worker validator, tests and guide. This decision supersedes
only ADR-0004's requirement that v1 remain concurrently supported; its recipe
and fail-closed execution decisions still apply.

The retirement is three separate PRs: contracts first, then control-plane,
then Playwright. Each consumer pins a reviewed bundle revision and removes v1
code and tests in its own repository. Until both consumers are updated and
verified together, Native Worker acquisition remains disabled. Unrelated v1
data schemas, Run Management v1, migration history and accepted ADR text remain
unchanged.

## Alternatives considered

### Retain v1 indefinitely

- Benefits: No deletion or bundle-inventory change.
- Costs and risks: Two ongoing implementations and conformance surfaces for a
  protocol that was never deployed, including an incomplete lease shape.
- Reason not selected: It adds maintenance cost without a compatibility need.

### Rename v2 wire paths to v1

- Benefits: A single numerically first Native Worker route generation.
- Costs and risks: Existing v2 control-plane and worker work, fixtures and
  contract pins would need coordinated wire changes; historical v1 would then
  have two incompatible meanings.
- Reason not selected: Version numbers identify wire meaning, not the count of
  currently supported versions.

## Consequences

### Positive

- One current Native Worker API, validator, test corpus and implementation path.
- No incomplete v1 lease can be mistaken for an executable assignment.

### Negative

- Bundle `0.19.0` removes an API inventory entry. Strict readers must update.
- Dormant local v1 assignments cannot be reused as v2 assignments.

### Neutral or follow-up

- Historical candidate bundles and accepted decisions remain readable at
  their original Git revisions.
- This contract change does not itself deploy or enable a Windows worker.

## Compatibility and migration

The v2 wire shape does not change. Consumers pinned to an older bundle continue
to see that historical inventory until explicitly repinned. Control-plane and
Playwright must remove v1 routes, payload handling and dual-version tests in
separate PRs, then validate the same v2 bundle revision before enabling work.
Do not mix a v2-only worker with a v1-only control plane. Review and recreate
any dormant local v1 assignments under a complete v2 recipe; do not silently
translate them. No production wire traffic or authoritative evidence requires
migration.

## Security and operations

Keep worker bearer identity, lease capability, attempt/revision fencing,
cancellation, exact-key presigned upload and artifact verification as defined
by v2. Removing v1 does not loosen authentication or allow worker-selected
commands, targets, object keys or measurement defaults. Rollback can pin an
older immutable bundle revision, but must not re-enable v1 acquisition as a
substitute for a complete recipe.

## Validation

The contracts PR must validate only the v2 OpenAPI, positive/rejection/HTTP
fixtures and security invariants offline. Consumer PRs must prove v2 route and
runner behavior, reject v1-shaped input, and pass their integration suites.
An end-to-end representative Windows run is required before enabling Native
Worker acquisition.
