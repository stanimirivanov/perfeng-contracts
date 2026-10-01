# Repository working agreement

## TL;DR

- Read `CONTRIBUTING.md`; it is the canonical workflow policy.
- Preserve published contract meaning and make compatibility effects explicit.
- Keep validation offline, deterministic and independent of consumer code.
- Run the exact repository checks and report their results honestly.

This file is the concise, tool-facing entry point for contributors and coding
agents. [CONTRIBUTING.md](CONTRIBUTING.md) is the canonical workflow policy.
Normative terms such as MUST, SHOULD and MAY have the meanings defined there.

## Before changing anything

1. You MUST read [CONTRIBUTING.md](CONTRIBUTING.md), especially its ambiguity,
   issue-timing, verification and external-side-effect rules.
2. You MUST inspect the branch and working tree and preserve pre-existing work.
3. You MUST use the [documentation map](docs/README.md) to select the relevant
   engineering, contract, compatibility and decision sources. Do not bulk-read
   unrelated guides or ADRs.
4. You MUST use the repository-local checks. You MUST NOT claim an unavailable
   or unexecuted check passed.

If schemas, examples, documentation and an accepted decision disagree, you MUST
NOT silently pick one. Correct an obvious local defect or propose a superseding
ADR. Ordinary ambiguity follows CONTRIBUTING.

## Repository responsibility

`perfeng-contracts` owns language-neutral interchange contracts, compatibility
rules, examples, conformance fixtures, the run-management OpenAPI description
and candidate contract-bundle composition. It does not own service behavior,
persistence, runner implementation, analysis algorithms or deployment.

- Consumers MUST depend on published contract meaning, not validator internals.
- Runtime implementations belong in their component repositories.
- A schema, example or API fixture MUST NOT imply behavior that the documented
  contract does not define.
- Consumer migrations MUST be coordinated when closed unions, required fields
  or semantics evolve.

## Shape of work

- Each task and pull request MUST deliver one coherent, independently
  reviewable contract outcome.
- Compatibility changes, dependency updates and broad cleanup MUST remain
  separate unless inseparable for correctness.
- Existing schema generations and candidate bundles MUST remain reproducible.
- Scope, assumptions, compatibility effects, migration, affected consumers and
  verification evidence MUST be explicit.

## Contract and implementation rules

- Treat schemas, OpenAPI documents, examples, fixtures and `contracts.json` as
  compatibility boundaries.
- Version semantics rather than filenames alone. Do not change published field
  meaning in place.
- Validate every added or changed contract with positive and negative cases.
- Keep schema resolution offline and reject undeclared or ambiguous references.
- Preserve exact bytes when checksums or content identity form part of a test.
- Python is validation tooling, not a runtime SDK or product dependency.
- Repository content and parsed JSON are untrusted input and MUST be validated
  before use.

Follow the engineering standards and relevant contract documentation.

## Quality and documentation

- Test observable compatibility behavior at the lowest boundary that proves it.
- Defect fixes SHOULD begin with a failing regression test.
- Tests MUST be deterministic, isolated and independent of network, locale,
  filesystem ordering and wall clock unless those are the subject.
- Comments SHOULD explain decisions and constraints and SHOULD NOT narrate
  syntax.
- Long documents MUST include the TL;DR required by CONTRIBUTING.
- Contract, examples, compatibility documentation and consumer migration notes
  MUST change together.

## Completion

The canonical required checks and completion-report format are defined in
[CONTRIBUTING.md](CONTRIBUTING.md). Follow them after every work item.
