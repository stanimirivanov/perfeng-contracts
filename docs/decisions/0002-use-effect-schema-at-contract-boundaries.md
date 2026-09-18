# ADR-0002: Use Effect Schema to author data contracts

- Status: Accepted
- Date: 2026-09-18
- Milestone: M01 — Local Performance Decision Loop
- Deciders: Repository owner
- Supersedes: None
- Superseded by: None

## TL;DR

- Author Perfeng data contracts in stable Effect Schema v3 and infer their
  TypeScript wire types from the same authoritative source.
- Generate deterministic JSON Schema Draft 2020-12 documents in the existing
  `schemas` paths so non-TypeScript consumers keep a language-neutral boundary.
- Migrate contract families in reviewable stages; a schema has exactly one
  authoritative source during the transition.
- Keep semantic and cross-document validation in the existing Python tooling
  until a deliberate replacement proves equivalent behavior.
- Keep OpenAPI documents hand-authored for now; this decision does not make
  TypeScript a control-plane runtime dependency.

## Context

Perfeng's nineteen data-contract schemas are currently hand-authored JSON
Schema documents. They are portable and supported by every current producer
and consumer, but composition, refactoring and TypeScript type reuse require
parallel hand-written models. That is especially costly for the Playwright
runner and the planned native Windows worker boundary.

JSON Schema remains the appropriate interchange and validation format for the
Go control plane, Python analysis package, runner implementations, OpenAPI
documents and release bundles. Replacing it at the wire boundary would create
unnecessary language coupling. The authoring source and distributed artifact
do not, however, have to be the same representation.

Effect Schema provides typed TypeScript authoring, inferred encoded types,
runtime decoding and a JSON Schema compiler. Perfeng already separates
structural validation from semantic checks such as referential integrity,
ordered timestamps, lifecycle consistency and provenance. Adopting Effect
Schema must not silently weaken those checks or claim that structural validity
proves scientific quality.

Migrating every contract and the Run Management API in one pull request would
make wire-compatibility review impractical. The repository therefore needs a
staged transition in which generated and legacy schemas coexist without
competing sources of truth.

## Decision

### Source and generated artifacts

The authoritative source for a migrated Perfeng data contract is Effect Schema
v3 under `contracts/source`. The repository uses an exact stable Effect version,
an exact TypeScript toolchain, Node.js 24 and a committed pnpm lockfile.

Generate JSON Schema Draft 2020-12 documents into their existing paths under
`schemas`. Preserve every published `$id`, contract name and manifest path.
These checked-in documents remain the language-neutral artifacts consumed by
other repositories and included in candidate bundles. They MUST NOT be edited
independently after their contract enters the generated registry.

Generation MUST compare exact bytes and fail verification when a committed
artifact is stale. It MUST be deterministic on Windows and Linux, MUST NOT read
the previous generated document, and MUST NOT access the network. Generated
presentation MAY use local `$defs` or add descriptive annotations, but a
migration MUST preserve the set of accepted JSON instances unless it is
released as an intentional semantic change.

The Run Management OpenAPI document and its embedded component schemas remain
hand-authored. OpenAPI generation or composition needs a separate decision
based on a concrete API workflow. Language bindings MAY be generated from JSON
Schema or OpenAPI only when an owning producer or consumer can test and maintain
them.

### Staged migration

The TypeScript generated-contract registry is the transition ledger. A data
contract listed there is Effect-authored; a contract not yet listed continues
to use its existing hand-authored JSON Schema as the authority. No schema path
may be produced by more than one source.

Migrate the two self-contained foundation contracts, `candidate/v1` and
`environment/v1`, with this decision and toolchain. Migrate later contracts in
coherent families so each pull request can review shared primitives, generated
output, examples, negative cases and consumer effects together. Complete the
data-contract migration before declaring the transition finished.

### Runtime validation and semantic checks

Incoming documents are untrusted. Effect Schema strips excess object
properties by default, so Perfeng decoders MUST use
`onExcessProperty: "error"` whenever they enforce a published closed-object
contract.

Continue to validate generated documents and examples with the existing
offline Python JSON Schema validator. Continue to enforce cross-field,
cross-document, checksum, lifecycle and provenance rules in the existing
semantic checks. Moving a rule into an Effect refinement is optional only when
generated JSON Schema and non-TypeScript consumer behavior stay explicit.

JSON Schema annotations MAY express a standard constraint that Effect's type
operators cannot emit directly. They MUST be attached to the narrowest Effect
schema that owns the meaning and covered by positive and rejection tests. A raw
JSON Schema document hidden inside an unconstrained Effect schema is not an
acceptable migration.

### Tooling and distribution

Use Biome for TypeScript formatting and linting, TypeScript in strict no-emit
mode, and Node's test runner through `tsx`. `make validate` runs TypeScript
generation drift, formatting, type checking and tests together with the
existing Python checks.

Candidate bundles continue to distribute language-neutral JSON Schema,
examples, APIs and documentation. Consumers do not need Node, pnpm, Effect or
TypeScript. This repository's authoring and validation environment needs both
the locked Node and Python toolchains.

## Alternatives considered

### Hand-author JSON Schema

- Benefits: Language-neutral and directly supported by validators and code
  generators.
- Costs and risks: Weaker refactoring and composition ergonomics, duplicated
  TypeScript types, and verbose authoring.
- Reason not selected: JSON Schema remains the generated interchange artifact,
  while Effect Schema provides a better authoritative authoring model.

### Replace JSON Schema at consumer boundaries

- Benefits: TypeScript consumers could use Effect directly everywhere.
- Costs and risks: Couples Go and Python consumers to a TypeScript toolchain and
  removes the existing language-neutral interchange format.
- Reason not selected: repository ownership is the shared wire contract, not a
  particular consumer runtime.

### Convert every schema and OpenAPI document in one change

- Benefits: No mixed-authority transition period.
- Costs and risks: An unreviewable generated diff across nineteen schemas and
  one API, with compatibility failures difficult to isolate.
- Reason not selected: Staged families keep every candidate bundle valid and
  make semantic review possible.

### Generate every language binding immediately

- Benefits: Demonstrates generator reach and creates ready-made stubs.
- Costs and risks: Adds toolchains, generated churn, and unsupported APIs with
  no real producer or consumer.
- Reason not selected: Consumer-driven generation gives compatibility tests a
  concrete purpose and avoids speculative maintenance.

## Consequences

### Positive

- Contract authors get typed composition, inferred wire types and executable
  decoding from one source.
- JSON Schema remains portable to validators, OpenAPI, and downstream language
  generators.
- Existing Go, Python and other consumers retain Draft 2020-12 JSON Schema.
- Drift between migrated source and committed artifacts fails validation.
- Contract-family migration can proceed without a flag day.

### Negative

- Contributors and CI require locked Node/pnpm and Python/uv toolchains.
- The transition temporarily has two authoring forms, although never two
  authorities for one schema.
- Generated schema presentation and byte identity can change without changing
  accepted instances, requiring explicit bundle patch releases.
- Some JSON Schema constraints require careful annotations and dual-runtime
  tests because they have no direct Effect type operator.

### Neutral or follow-up

- Later PRs migrate result and run metadata, workloads and catalogues,
  transport and browser evidence, and policy/baseline/analysis families.
- Native Worker API v1 can compose generated data schemas after the relevant
  family has migrated, but its OpenAPI definition remains an explicit
  deliverable.
- Consumer-specific domain models remain owned and hand-written in their
  repositories; inferred Effect types describe wire data only.

## Compatibility and migration

The first migration preserves the accepted JSON instance set, schema IDs,
manifest names and paths for `candidate/v1` and `environment/v1`. Generated
documents may reorder keywords, add descriptive annotations, and include empty
`required` arrays for open-key records. These are schema-document changes but
not wire-data changes.

Because exact schema bytes change, the candidate bundle receives a patch
version. Consumers that pin immutable bundle bytes must update deliberately;
producers and consumers of candidate/environment JSON need no payload change.
Existing schemas remain supported throughout the staged transition.

Rollback restores the previous hand-authored documents and removes their
generated-registry entries together. Editing generated JSON without changing
the Effect source is not a valid rollback or hotfix.

## Security and operations

- Keep generation and validation deterministic, offline and bounded.
- Commit the exact dependency lock and review dependency changes separately
  from contract semantics when practical.
- Treat decoded documents as untrusted and reject excess properties at strict
  contract boundaries.
- Do not allow schema resolution to fetch remote identifiers.
- Do not put credentials, private endpoints or production evidence in source,
  examples, generated documents or tests.
- Type inference and structural validation do not establish authorization,
  provenance, host qualification or measurement quality.

## Validation

The decision is verified by:

- deterministic Effect Schema to Draft 2020-12 generation and exact drift
  detection;
- Biome formatting and linting plus strict TypeScript type checking;
- direct Effect decoding of positive and negative fixtures with
  excess-property rejection enabled;
- existing offline Python validation of all generated and legacy schemas;
- the shared semantic and regression test suite;
- stable schema IDs, contract names and manifest paths; and
- the complete `make validate` suite in CI.
