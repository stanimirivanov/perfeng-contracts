# ADR-0007: Discover a Native Worker's current slot without restoring authority

- Status: Proposed
- Date: 2026-10-11
- Milestone: M03 — Native Browser Decision Loop
- Deciders: Project owner and affected consumer maintainers
- Supersedes: None
- Superseded by: None

## TL;DR

- Add bounded worker-scoped discovery when an acquisition response was lost
  before its attempt ID became known.
- Observe stored availability and the single current measurement slot, not
  acquisition history or an idempotent request receipt.
- Serialize observation with acquisition and availability replacement; stop
  the old process and withdraw availability before manual recovery.
- Return no capability, recipe, object key or upload material. No result
  restores authority or permits deletion of retained evidence.
- Preserve existing v2 operation shapes and implement server and worker
  behavior in their owning repositories before enabling discovery.

## Context

Known-attempt inspection cannot resolve a lost acquisition response when the
worker never learned the Run/attempt pair. Acquisition has no client request
identity, and the worker intentionally does not persist lease capabilities.
An interrupted `run-once` leaves its owner marker even if it has no attempt
directory. Native v2 capacity is exactly one, so a bounded current-slot lookup
can identify a still-occupying attempt without historical enumeration.

An empty point-in-time lookup alone is unsafe for recovery: a request already
in flight can acquire afterward. Local timeouts, process exit and arbitrary
sleeps are not a server fence. Availability withdrawal must prevent a request
using an earlier AVAILABLE observation from committing after withdrawal.

## Decision

Add `discoverNativeAttempt` at `POST /native-worker/v2/attempts/discover` with
only `protocolVersion: 2`. Derive worker scope from its bearer principal, never
from a payload or query selector. Return one consistent observation with the
server timestamp, stored availability and NONE or FOUND.

NONE means no owned, unreleased v2 lease expires strictly after the observation.
FOUND names the single occupying attempt and slot expiry, reusing ACTIVE or
TERMINAL from known-attempt inspection. A durably accepted terminal report
takes precedence while its retained lease occupies capacity. Expired/released
leases and historical reports are not listed. Missing presence is UNREPORTED,
not a fabricated availability report; UNREPORTED with a current slot or
multiple slots is an integrity error, not a successful truncated observation.

Discovery is read-only at the domain boundary: no presence, lease, Run, artifact
or terminal record is changed. Internal serialization may use bounded locks;
the server reads its clock after waiting and must not return a stale snapshot
predating that wait. All returned state belongs to one consistent observation.
Acquisition must recheck current availability at commit, so accepted withdrawal
fences requests using a previous AVAILABLE report. Do not implement this as an
unserialized list followed by a separate availability read.

Before manual recovery the operator stops the old agent/browser tree, excludes
another process using the identity, reports UNAVAILABLE and obtains server
acknowledgement, then discovers. New availability reports can invalidate the
observation; a credential shared by independent installations cannot meet this
procedure. ACTIVE never restores the original capability and must expire
without renewal by the recovering process. NONE never proves an earlier
acquisition did not succeed. Local evidence/markers stay retained until a
separate conservative manual recovery procedure resolves their disposition.

## Alternatives considered

### Add acquisition request IDs and durable idempotency receipts

- Benefits: Can correlate one exact acquisition, including no-work outcomes.
- Costs and risks: Changes existing acquisition payloads, retention and retry
  semantics; replaying authority would add a capability-recovery trust boundary.
- Reason not selected: Manual recovery only needs bounded current capacity;
  historical request outcomes and automatic retries are outside M03's scope.

### Enumerate all attempts or select the latest by timestamp

- Benefits: Provides broader historical diagnostics.
- Costs and risks: Adds retention, pagination, ordering, disclosure and ambiguous
  association with the unknown request; latest does not mean current authority.
- Reason not selected: Exactly one measurement slot already supplies the
  bounded current identity needed here.

### Wait locally and treat an empty lookup as proof of safe recovery

- Benefits: Needs no explicit concurrency semantics.
- Costs and risks: A late commit or new availability report races the lookup;
  client time cannot prove the server stopped processing.
- Reason not selected: Accepted withdrawal and serialized server observation
  are necessary; even then cleanup remains a separate decision.

## Consequences

### Positive

- Lost-response recovery can observe current capacity without a known attempt
  ID, caller-selected identity or recovered secret.
- Existing acquisition and inspection clients need no payload migration.
- The contract specifies expiry, retained terminal precedence and late-commit
  obligations for storage and HTTP regression tests.

### Negative

- Discovery cannot establish an expired acquisition's historical outcome.
- The control plane needs bounded worker-scoped serialization and one clock;
  a single syntactically valid query is not sufficient proof of consistency.
- Operators still need process exclusion and retained-evidence policy.

### Neutral or follow-up

- Control-plane discovery and explicit Playwright manual recovery are the next
  substantial implementation batches. Unattended service recovery is deferred.
- Native runtime promotion and real Windows acceptance remain separate gates.

## Compatibility and migration

Advance the candidate bundle to 0.21.0 and Native Worker OpenAPI to 2.2.0. This
adds an operation and closed response union without changing existing operation
shapes, error codes, Run Management or Effect-authored data schemas. Strict
clients opt in deliberately. Deploy the implementing control plane before
workers call discovery; old workers remain on their reviewed behavior.
Do not repin already captured evidence merely to adopt a new transport API.
Rollback disables new calls; it does not delete records or convert evidence.
Native Worker v1 remains retired.

## Security and operations

- Authenticate independently from Run Management and bind every lookup to the
  worker principal. Absence of presence is not failure of authentication.
- Enforce bounded body size, polling and serialization time; retain standard
  authentication, authorization, rate-limit and dependency failures.
- Return `Cache-Control: no-store` on success. No lease capability, capability
  hash, target, recipe, object key, signed URL/header or artifact bytes may leak.
- Fail closed on ambiguous state, corrupted ownership or unavailable storage;
  do not disclose another worker's existence in messages or telemetry.
- Do not mutate stored state or claim the observation restores execution,
  release, upload, deletion or acquisition authority.

## Validation

The offline conformance suite checks the request, NONE/FOUND unions, recorded
versus unreported availability, single-slot shape, ACTIVE/TERMINAL reuse,
no-store header, identity-selector/secret rejection, exclusive expiry and one
consistent clock. Existing operations remain unchanged. Consumer suites must
prove worker isolation, withdrawal versus in-flight commit, terminal precedence,
capacity integrity failure, expiry and no mutation with live PostgreSQL, then
prove conservative process and local-evidence handling on the Windows worker.
