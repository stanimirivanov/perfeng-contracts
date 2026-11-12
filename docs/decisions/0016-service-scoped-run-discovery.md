# ADR-0016: Separate service authority from CI Run identity

- Status: Proposed
- Date: 2026-11-12
- Milestone: M05 — Operator Visibility and Diagnostics
- Deciders: Repository owner and control-plane/Console consumers
- Supersedes: None
- Superseded by: None

## TL;DR

- Add exact authorized request resolution and Run access observation.
- Preserve legacy principal ownership and closed lifecycle payloads.
- Require explicit service-mode provider admission before human adoption.

## Context and decision

Maya must follow a CI link without inheriting CI's credential or creator identity.
Add Run API 0.5.0 in candidate bundle 0.28.0. Use retained Integration request
issuer/id to resolve a native Run, and distinguish immutable service binding,
original creator, current verified actor, calling client and current permissions.
Adopt the normative [service identity contract](../service-identity.md).

Do not add actor/service inputs to CreateRun or reinterpret opaque Integration
Run IDs. Do not expose a public list or discovery-by-name endpoint. Rejected
alternatives are sharing CI credentials (breaks accountability), unconditionally
expanding legacy reads (breaks isolation), and embedding native IDs into closed
Integration events (breaks existing strict consumers). Two additive read routes
allow independent provider rollout and preserve existing wire payloads.

## Compatibility and migration

Service-mode authorization is an explicit semantic extension, not a claim that
old providers support delegated human access. Existing principal credentials
retain their scope. Provider trust configuration must prevent a client choosing
legacy fallback after service-grant revocation. Providers establish authenticated
service bindings and actor/delegation verification before consumers opt in;
unbound historical data is never inferred into a service. Later slices own the
rerun API, audit read model, grants, authentication protocol and runtime rollout.

## Security and operations

Links are selectors, never credentials. All service observations are no-store
and advisory. Enforce current grants at every operation and use uniform scoped
404s. Keep mapping tombstones across native cleanup. No operation restores an
execution lease, downloads artifacts or issues a capability.

## Validation

Offline positive/negative schema and independently scoped relationship fixtures
cover human-vs-CI access, revoked grants, cross-service denial, distinct rights,
issuer collision and native mapping substitution. Existing contract checks prove
reproducibility and legacy shape preservation. Live identity, audit and HTTP
isolation require provider tests; this contracts-only PR cannot verify them.
