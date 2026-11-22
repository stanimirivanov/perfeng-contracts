# Repository agent guide

## Agent skills

Use `mattpocock/skills` as the primary workflow for planning, ticketing,
implementation, TDD, review, and pull requests. The skills take precedence where
contributor guidance covers the same steps. Follow the repository's technical
requirements, CI gates, and authorization boundaries.

### Issue tracker

Use GitHub Issues in `stanimirivanov/perfeng-contracts`. See [issue tracker configuration](docs/agents/issue-tracker.md).

### Triage labels

Use the default Matt Pocock label mapping. See [triage labels](docs/agents/triage-labels.md).

### Domain docs

Single context with a root glossary and ADRs in `docs/decisions/`. See [domain docs](docs/agents/domain.md).

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
-
- Tests MUST be deterministic, isolated and independent of network, locale,
  filesystem ordering and wall clock unless those are the subject.
- Comments SHOULD explain decisions and constraints and SHOULD NOT narrate
  syntax.
- Long documents MUST include the TL;DR required by CONTRIBUTING.
- Contract, examples, compatibility documentation and consumer migration notes
  MUST change together.

## Verification

Run `make verify` and the applicable additional checks documented in
[CONTRIBUTING.md](CONTRIBUTING.md#verification-and-constrained-environments).
Use the [documentation map](docs/README.md) to find affected standards, operational
guides and decisions. Report checks as passed, failed or unavailable.
