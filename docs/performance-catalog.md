# Safe performance catalog projection v1

## TL;DR

- Candidate bundle 0.24.0 adds authorized metadata pages, not execution authority.
- Collect and verify the entire immutable snapshot before replacing a usable view.
- Preserve issuer-scoped identities; labels never establish ownership or identity.
- Reject stale, partial or inconsistent snapshots and retired execution dependencies.

## Resources and supported selections

`performance-catalog/v1` exposes workload, profile, environment, policy, baseline
and owner-route records. It reuses integration v1 issuer/ID/revision/SHA-256
references without changing that contract. Reference digests identify exact
producer-published artifact bytes, not the limited metadata projection. Names
are labels. Owner and route IDs refer to reviewed ownership/routing authorities;
they are not delivery URLs, credentials or Argus capability ownership.

This is a current authorized view: one record per `(kind, issuer, id)` per
snapshot. A new resource revision replaces the old reference atomically; older
snapshots retain history. Two revisions of the same ID cannot hide retirement
behind an older approval. Different issuers may reuse an ID. Missing references
and revision/digest substitutions invalidate the snapshot.

Workloads explicitly list supported profiles and an owner route. Each profile
lists exact supported environment/policy/baseline combinations and its purpose.
One profile identity can support multiple environments without inventing aliases.
Consumers must not infer a Cartesian product of individually available resources.
Active workloads require active routes/profiles; active profiles require active
workloads/environments/policies and reciprocal membership. Every referenced
record, including historical retired dependencies, must be present in the view.
Providers omit an unauthorized selection and its dependent metadata coherently.

Baselines retain CANDIDATE, QUALIFIED, APPROVED and RETIRED states. Only an APPROVED
baseline with matching profile/workload/environment/policy can back an active
profile. A null baseline means explicitly unselected, never latest or implicit
approval. Unselected retired/candidate records can remain visible for review.
Listing a profile, including stress/capacity, grants no launch permission;
provider admission independently revalidates authority, validity and provenance.

## Snapshot, pagination and freshness

Snapshot metadata includes immutable reference, authenticated principal scope,
producer identity/version, generation/expiry instants, total resource/page counts
and `complete: true`. The producer publishes only a fully materialized authorized
snapshot. That flag does not mean the consumer has received every page.
Exactly one empty page represents a complete empty view; omission is not empty.

Pages are zero-indexed and ordered. Only the first cursor is null; each subsequent
cursor equals the previous next cursor, and only the final next cursor is null.
Cursors are opaque and must be bound to principal, snapshot and page by the
provider; clients cannot manufacture authority from them. All pages repeat
identical snapshot metadata. Missing, repeated, reordered or mixed pages fail.
Limits are 100 records/page, 1,000 pages and 100,000 records/snapshot.

The snapshot reference SHA-256 covers the flat ordered resource array across all
pages, serialized as compact UTF-8 JSON: object keys sorted lexically (all schema
keys are ASCII), no whitespace, no unnecessary ASCII/non-ASCII or slash escaping,
standard JSON string escaping, and no Unicode normalization. Resource values
contain strings, arrays, objects and null, never numbers. Invalid Unicode cannot
be hashed. This restricted canonical format avoids number/locale ambiguity.
The same resource order has the same digest regardless of page partition.

Consumers compare expected issuer/principal with verified transport credentials,
not body claims, verify counts/digest and reference closure, and atomically swap
the view only after full enumeration. Snapshot metadata cannot change under an
existing identity; restart pagination after cursor expiry or authorization change.
At observation time require `generatedAt <= observedAt < validUntil` and a positive
freshness window. Stale or incomplete views cannot create new execution eligibility
or erase prior evidence; retain them only as labeled historical evidence and
require refresh/manual review. Missing records after a complete refresh cease to
be eligible; explicit RETIRED records communicate retirement without deletion.

## Compatibility and conformance

This additive candidate leaves existing schemas/APIs byte-identical. Consumers
opt in by pinning reviewed immutable artifacts. No endpoints, synchronization,
publication, new dependencies or raw workload configuration are included.
Provider publication and Argus consumption belong to M09-PR3/PR4.

`make generate-contracts` generates the JSON artifact. `make validate` checks
shape/provenance in Effect and JSON Schema plus complete snapshot semantics in
offline Python tooling. Fixture observation time is frozen at 2026-10-22 12:00Z;
production consumers must supply actual observation time and independently verified
scope. Structural validation cannot authorize access or establish external artifact
provenance. See [ADR-0010](decisions/0010-project-safe-performance-catalog-snapshots.md).
