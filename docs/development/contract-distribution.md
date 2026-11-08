# Immutable contract distribution

## TL;DR

- Package exact files from one reviewed provider revision per manifest.
- Keep candidates separate from approved releases. Verify provenance before adoption.
- Start with the historical Kubernetes evidence selection in the tracer fixture.
- Keep consumer pins and prepared builds independent of the publication service.

## Manifest and selection

The [distribution schema](../../distribution/manifest.schema.json) defines
metadata independent of platform payloads and the provider contract bundle
version. The [tracer selection](../../distribution/tracer.json) pins the
Kubernetes evidence schema at the environment's reviewed 0.22.0 source
revision, its accepted preflight example and the source licence. The
consumer's lock stays independently reviewed.

The source revision applies to every member. The member map binds canonical
relative paths to SHA-256 digests of raw Git blob bytes. A selection spanning
multiple revisions requires separate manifests and explicit consumer mappings.
Include the complete selected reference closure and applicable examples,
transitions and licences. A schema identifier is not a retrieval instruction.

A selection declares inputs. A candidate adds a release identifier and the
digest of the complete archive. A promoted manifest also binds an admission
record by digest. Promotion must use the tested archive without rebuilding it.
The admission record identifies the candidate and receipts. It does not
contain the final promoted manifest's digest, which would create a cycle.

## Trust and installation

A manifest's shape does not establish approval. The consumer must verify
provenance over the final manifest bytes against independently configured
publisher, workflow and source identity policy, then verify the selected
archive and every member. A candidate is eligible for testing only. Selection
and candidate inputs must never authorize installation as a promoted release.

Tooling must reject duplicate JSON keys, conflicting member paths, unsafe
archive entries, missing or extra files and undeclared references. The schema
covers lexical path safety and declared identities. It cannot inspect an
archive, prove that a file came from Git or authenticate a publisher.

## Retention and recovery

Retain the exact current and rollback inputs, their verification material and
the versions needed for supported evidence replay. Preserve unknown replay
dependencies until their status is determined. Historical reproduction verifies
against the retained trust inputs for that selection. New adoption requires the
current approved trust and withdrawal policy.

Withdrawal changes eligibility for future selection. It cannot revoke a cached
offline pin. Communicate revocation to affected owners, who review any required
replacement. Roll back through an explicit consumer selection of a retained
approved manifest. Recover a lost locator through an approved mirror or a
reviewed locator change, while preserving the content identity.

## Scope of SR-1

This change defines metadata, tests and policy. Later tasks own the packager,
publication, verification, restoration and consumer adoption. Existing contract
payloads and version pins need no migration for SR-1.
