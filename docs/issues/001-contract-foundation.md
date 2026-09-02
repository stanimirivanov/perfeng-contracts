Repository: `perfeng-contracts`

Title: Extract versioned performance contracts with history and CI validation

## Description

Implement the existing-contract slice of phase 1 in the platform proposal
(sections 29-32 and 78). Extract candidate, environment, run-metadata, and
normalized metric schemas from performance-platform into their dedicated
repository, retaining relevant Git history.

Add versioned domain paths, an explicit bundle manifest, positive fixtures,
negative regression tests, and CI that validates and packages the contracts.
Correct the nullable metric type/default inconsistency. Document compatibility,
provenance, and remaining contract gaps.

## Acceptance criteria

- [ ] Four existing schemas live under domain/v1 paths with matching IDs.
- [ ] Every schema and example is listed in contracts.json and validated offline.
- [ ] Invalid timestamps, identifiers, states, and result versions are rejected.
- [ ] Declared defaults validate against their own subschemas.
- [ ] CI executes validation/tests and uploads a candidate schema bundle.
- [ ] Relevant source ancestry survives extraction and PR merge.
- [ ] Existing prototype consumers remain usable during migration.

## Validation

Run `python scripts/validate.py` and `python -m unittest discover -s tests -v`.
Inspect the imported history and use a merge commit when merging this PR.

## Scope

This is a 0.1.0 foundation. Stable release publication, workload/catalogue/policy
schemas, transport envelopes, OpenAPI, and component extraction are later PRs.
