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

## Prepare a local archive

Run `make distribution-check` for the offline packaging tests. With the
tracer's historical revision already available locally, run:

```sh
uv run --locked --offline python -m scripts.contracts_pack \
  --selection distribution/tracer.json --output /tmp/perfeng-tracer.tar.gz
```

Choose an unused output path. The packager reads raw Git objects, checks
the source version and each declared digest, and writes a sorted tar stream
with fixed metadata inside a gzip envelope. Repeat with the same locked
toolchain and selection to reproduce the archive. Missing Git objects fail
locally. The caller supplies the approved member inventory and reference
closure. Packaging neither generates a promotion record nor publishes an
artifact.

## Exercise local publication

Use a disposable, trusted directory on a filesystem that supports hard links.
Prepare an archive from the approved selection, then supply a candidate
manifest containing the same source and member inventory, a release ID and
the archive's SHA-256 digest.

```sh
store=$(mktemp -d)
uv run --locked --offline python -m scripts.contracts_publish --root "$store" stage \
  --candidate candidate.json --archive /tmp/perfeng-tracer.tar.gz
uv run --locked --offline python -m scripts.contracts_publish --root "$store" promote \
  --release-id tracer --admission admission.json
```

The release ID in the command must match the candidate. The admission document
must include `candidateSha256` computed from the exact candidate manifest bytes.
The local publisher checks that binding and the stored archive hash. Admission
policy evaluation and publisher authentication are separate steps.

Archives and admission documents are stored under `objects/<sha256>`. The
candidate marker lives at `releases/<releaseId>/candidate.json`. The final
`promoted.json` marker binds the same archive and inventory plus the admission
document's digest. Write each marker only after its referenced objects are
available. Identical retries are safe. A competing attempt with different bytes
cannot replace a marker. An interrupted attempt can leave unreferenced objects
or temporary files, but their presence never indicates promotion.

This fixture exercises process interruption and atomic no-clobber writes.
Power-loss recovery and hosted publication are outside its scope. A local
marker alone grants no adoption authority. Run `make publication-check` for the
offline publication tests.
