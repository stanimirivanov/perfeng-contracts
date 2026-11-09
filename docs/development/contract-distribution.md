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

## Protected tracer workflow

[Publish protected contract tracer](../../.github/workflows/contracts-publish.yml)
is an opt-in manual workflow for the fixed historical selection. An administrator
must protect `main`, create both `contract-tracer-attestation` and
`contract-tracer-publication` environments, restrict their deployment branches
to `main`, and require reviewer approval with self-review disabled. Configure
those controls before setting the repository variable
`PERFENG_TRACER_PUBLICATION_ENABLED` to `true`. Environment names alone do not
establish protection. The repository and plan must support GitHub artifact
attestations. Enable GitHub immutable releases if the repository relies on
GitHub to prevent post-publication edits by other actors.

After separate authorization for the hosted exercise, dispatch from `main`
with `expected_sha` set to the exact reviewed workflow commit. The prepare job
has read access. The attestation job can sign the final manifest and preserve
its bundle. The publication job reserves a unique `contract-tracer-<run-id>`
tag, creates a draft with all five assets, then publishes the complete draft.
It does not overwrite an existing tag or reuse an earlier attempt. A failed
run may leave a tag or a draft. Inspect it separately, then use a new authorized
dispatch rather than rerunning the same workflow run.

For the downstream SR-4 policy, independently review the exact manifest
digest, the workflow's main commit as both source and signer digest, the
source ref `refs/heads/main`, and signer workflow
`stanimirivanov/perfeng-contracts/.github/workflows/contracts-publish.yml`.
The manifest's source revision identifies historical contract bytes and
differs from the workflow commit. Retain the manifest, archive, candidate,
admission document and Sigstore bundle. The local policy tests exercise the
job gates and interruption before publication. The separately authorized
hosted run must still demonstrate retrieval and offline verification against
the reviewed publisher identity. Disable the repository variable to stop
future publication.

## Historical contract inventory

The [supported selections inventory](../../distribution/supported-selections.json)
records observed consumer lock revisions and SHA-256 values. `current` means the
observed checked-in selection at the recorded consumer commit. An earlier
`historicalCandidate` means a different checked-in selection was found. These
observations leave deployment, rollback readiness and retained-evidence replay
coverage unknown. Keep the selected historical bytes and verify those states
before any retirement or rollback claim.

Each profile groups the union of observed files from one exact provider
revision. Paths in a consumer selection map source members to destinations
relative to that consumer's snapshot directory. A null destination marks a
verification-only input, such as Playwright's reviewed OpenAPI or the environment
tracer example. The licence travels with each profile. The Playwright raw-result
producer identity remains separate from its Native API selection.

After preparing the required Git objects, run:

```sh
make distribution-history-check
uv run --locked --offline python -m scripts.contracts_history \
  --revision 3b86afa18b468d831c7c2c176618180db18b2764 --output /tmp/history.tar.gz
```

The earlier k6 selection at `8363ec6d54721a4750761df37c80465e9f76be4d` is
not an ancestor of the provider main revision used for this inventory. The
provider served that exact commit when explicitly requested. Prepare it
separately from the default checkout and retain its bytes with the closure.

The check verifies Git digests and resolves JSON references using only members
in each archive. A missing object, mismatched member or unresolved reference
fails the check. Historical schemas in 0.4.0, 0.12.0 and 0.13.0 include
absolute `perfeng.dev` identifiers that the provider resolves from local
members. The current consumer inspector's relative-reference profile requires
separate qualification for those archives. Packaging establishes provider
byte and reference closure. Consumer acceptance and hosted publication need
their own receipts.
