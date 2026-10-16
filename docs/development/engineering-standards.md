# Contract engineering standards

## TL;DR

- Preserve language-neutral meaning and keep runtime implementation elsewhere.
- Treat schemas, OpenAPI, examples, fixtures and bundle metadata as contracts.
- Evolve published meaning compatibly or introduce a new explicit generation.
- Keep validators offline, deterministic, typed and strict at input boundaries.
- Test success, rejection and consumer migration behavior together.
- Pin tools and run the same checked-in checks locally and in CI.

## Policy strength

Normative terms use the meanings defined in
[CONTRIBUTING.md](../../CONTRIBUTING.md#policy-language-and-sources-of-truth).
MUST and MUST NOT are requirements; SHOULD and SHOULD NOT are strong defaults
that require a recorded reason to deviate; MAY is optional.

## Ownership and architecture

This repository owns the shared language between producers and consumers. It
does not own orchestration, persistence, runner behavior, statistical methods or
deployment. Contract documents MUST describe interoperable meaning without
depending on one implementation language or framework.

- Organize by contract capability and generation.
- Keep validation tooling separate from the interchange documents it checks.
- Do not encode a consumer's private storage or transport representation as a
  shared contract merely for implementation convenience.
- Put component-specific behavior in its owning repository.
- Introduce a shared abstraction only when multiple consumers require the same
  stable meaning.

## Contract evolution and compatibility

- Version semantics, not filenames alone. Never change a published field's
  meaning in place.
- Additive fields define required/optional status, defaults, absence semantics,
  old-reader behavior and old-writer behavior.
- A breaking change requires a new schema or API generation, coexistence rules,
  consumer migration guidance, conformance fixtures and an ADR when it changes
  the evolution strategy.
- Closed enums and discriminated unions are compatibility boundaries. Adding a
  value can break strict consumers and requires coordinated evidence.
- Distinguish absent, null, zero, unknown, unavailable and not applicable.
- Make units, clocks, identifiers, revisions, checksums and ownership explicit.
- Do not claim scientific quality, authorization or provenance from structural
  validation alone.

## JSON Schema and OpenAPI

- Follow ADR-0002 for source authority. Every data schema MUST be listed in the
  generated registry, generated from Effect Schema and never edited directly.
  The hand-authored Run Management and Native Worker OpenAPI descriptions are
  the documented exceptions.
- Preserve stable IDs and manifest paths when migrating authoring source. Test
  accepted and rejected instances through Effect and the generated artifact.
- Strict Effect decoders MUST set `onExcessProperty: "error"` for published
  closed objects; the default stripping behavior is not contract enforcement.
- Keep generation deterministic and fail validation on any source/artifact
  drift.
- Use the repository's declared JSON Schema draft and self-contained OpenAPI
  version consistently.
- Give published schemas stable absolute IDs and deterministic local resolution.
- Validation MUST NOT fetch remote references.
- Reject unknown fields where ambiguity or silent producer mistakes would be
  unsafe; allow extension only through a deliberate documented boundary.
- Use constraints to enforce stable structural invariants, not prose-only
  assumptions that machines can reliably check.
- Keep examples valid, realistic, credential-free and minimal enough to expose
  the contract behavior being demonstrated.
- Add negative cases for required fields, closed values, identity mismatches,
  ambiguous unions and security-sensitive shapes as applicable.

## Bundle identity and provenance

- `contracts.json`, the project version, documentation and CI artifact name MUST
  identify the same candidate bundle.
- Every declared contract and executable example MUST resolve within the
  repository and be included where consumers expect it. The offline validator
  checks manifest paths before reading files, including resolved symlink targets.
- Checksums refer to exact bytes. Do not normalize or regenerate referenced
  fixtures without updating the identity and all consumers deliberately.
- Candidate CI artifacts are not stable releases. Consumers pin a reviewed
  commit or an explicitly published immutable release.
- Generated content, if introduced, MUST be reproducible and verified for a
  clean regeneration diff.

## Python validation tooling

- Use the Python version in `.python-version`, dependencies from `uv.lock`, Ruff
  formatting and the configured type checker.
- Type public functions and parsing boundaries. Normalize parsed JSON before
  core validation uses it and isolate necessary `Any` values.
- Keep import-time behavior side-effect-free and prefer `pathlib`, context
  managers and standard-library facilities.
- Raise precise exceptions and preserve causes. Do not discard error
  classification with a broad catch.
- Bound files, collections, recursion, error output and expensive validation.
- Inject or isolate filesystem roots and other environmental inputs needed for
  deterministic tests.
- Docstrings explain public contracts, failures and non-obvious side effects,
  not signatures.

## Testing

Test behavior at the lowest boundary that proves it:

- schema and example validation;
- registry completeness and exact bundle identity;
- positive and negative compatibility cases;
- self-contained OpenAPI validation and operation fixtures;
- cross-contract identity and provenance invariants; and
- consumer-facing migration fixtures when a generation changes.

Tests MUST be deterministic, isolated, parallel-safe and independent of network,
locale, filesystem ordering and wall clock unless those are the subject. Defect
fixes SHOULD begin with a failing regression test. Never weaken assertions or
accept broader input merely to preserve an invalid fixture.

## Documentation and security

- Document field meaning, units, absence, ownership, mutability, compatibility
  and consumer obligations where they are not evident from structure.
- Comments explain decisions and constraints rather than JSON or Python syntax.
- Long documents follow the TL;DR policy in CONTRIBUTING.
- Treat repository content, parsed documents and references as untrusted input.
- Do not embed credentials, personal data, private endpoints or production
  evidence in examples or fixtures.
- Bound diagnostic output and avoid echoing untrusted payloads unnecessarily.
- Dependencies require a current need, compatible license, maintained release,
  pinned resolution and proportionate security review.

## Required verification

Run the exact checks in CONTRIBUTING plus focused validation for every changed
schema, example, API fixture or compatibility path. A check that cannot run
follows the constrained-environment protocol and MUST NOT be reported as passed.
