# Contributing to perfeng-contracts

## TL;DR

- Deliver one coherent, verified contract outcome per issue and pull request.
- Use MUST, SHOULD and MAY as defined below; lowercase wording is explanatory.
- Proceed on documented, reversible assumptions and stop for choices that
  materially affect semantics, compatibility, safety, scope or external state.
- Prepare requested changes without staging or committing, then print issue
  content for the repository owner.
- Run the exact repository checks and report unavailable checks as not run—never
  as passed.
- Use exact published milestone titles in the form `MNN — Outcome`.

## Policy language and sources of truth

- **MUST** and **MUST NOT** identify requirements. A deviation needs an explicit
  reviewer-approved exception recorded in the issue or pull request.
- **SHOULD** and **SHOULD NOT** identify strong defaults. A deviation is allowed
  only when its reason and trade-off are recorded.
- **MAY** identifies an optional choice.

Lowercase words such as “prefer,” “avoid” and “may” provide guidance and do not
silently create another normative level.

| Concern | Canonical source |
|:--|:--|
| Contributor workflow, issue timing, escalation and completion | This document |
| Concise contributor and agent entry point | [AGENTS.md](AGENTS.md) |
| Task-oriented documentation routing | [docs/README.md](docs/README.md) |
| Coding harness and verification tiers | [docs/development/harness.md](docs/development/harness.md) |
| Contract engineering standards | [docs/development/engineering-standards.md](docs/development/engineering-standards.md) |
| Dependency admission and supply-chain checks | [docs/development/dependency-policy.md](docs/development/dependency-policy.md) |
| Architecture decisions | [docs/decisions](docs/decisions/README.md) |
| Cross-repository milestones | [perfeng-environment roadmap](https://github.com/stanimirivanov/perfeng-environment/blob/main/docs/roadmap/milestones.md) |
| Contract inventory and exact commands | [README.md](README.md) |
| Compatibility and migration | [docs/compatibility.md](docs/compatibility.md) |

When sources conflict, the narrower source governs its stated concern. An
accepted ADR governs its decision until superseded. A contributor MUST surface
an unresolved conflict rather than quietly choosing the convenient rule.

## Before starting

A contributor MUST:

- inspect the branch and working tree and preserve unrelated changes;
- read affected schemas, examples, tests, contract documentation and ADRs;
- identify the smallest independently reviewable observable outcome;
- identify affected producers, consumers, bundle versions, fixtures and
  migration requirements; and
- determine the applicable workflow under [Issue timing](#issue-timing).

A contributor MUST NOT discard, overwrite, reformat or incorporate unrelated
work merely to obtain a clean diff. Destructive operations and externally
visible writes outside the stated task require explicit authorization.

An ADR MUST be proposed when a change establishes or revises a durable decision
about contract meaning, compatibility strategy, schema/API foundations,
security, repository responsibility or cross-component behavior.

## Ambiguity and escalation

Before escalating, a contributor SHOULD inspect relevant schemas, examples,
tests, documentation, ADRs and issue history and perform safe read-only checks.

A contributor MAY proceed with a documented assumption only when it is local,
reversible and inexpensive; stays within the stated outcome; does not alter
published semantics, security, persisted meaning or external state; and would
not materially change what reviewers believe they are approving. Record the
assumption and consequence in the pull request and completion report.

A contributor MUST stop and request a decision when missing information could
materially change the observable outcome, milestone, compatibility, data
meaning, consumer migration, security, an irreversible action, external state,
operational ownership or a choice between materially different designs.

The request MUST state the exact decision, evidence already checked, viable
options and consequences, and work that can safely continue. Agents MUST NOT
bury a material choice in a diff or halt on a trivial reversible choice.

## Issue timing

- When an issue number is supplied, the contributor MUST follow its scope and
  milestone. A material mismatch follows the escalation rules.
- When no issue number is supplied, prepare the smallest coherent requested
  change and print a complete proposed issue in the completion report. The
  owner creates the issue and then creates or renames the branch so it contains
  the issue number.
- Contributors acting for the owner MUST NOT stage, commit, push, create or
  modify issues, create pull requests, publish bundles, create releases, or
  change milestones unless explicitly requested.
- Read-only investigation and scoping MAY occur before an issue exists.

Creating or modifying a GitHub record or published artifact is an externally
visible write and requires explicit authority.

## Milestones

Use exact published titles in the form `MNN — Short outcome`. Published
milestones MUST NOT be reused, renumbered or casually renamed. Every issue MUST
name one milestone. GitHub is authoritative for live assignment; the centralized
[roadmap](https://github.com/stanimirivanov/perfeng-environment/blob/main/docs/roadmap/milestones.md)
owns intended outcomes and sequencing.

## Required issue structure

```markdown
**Repository:** perfeng-contracts
**Milestone:** MNN — Outcome

## Goal

Describe the problem and observable result.

## Scope

- Included behavior and boundaries.

## Design decisions

- Choices, assumptions, compatibility effects, affected consumers and ADRs.

## Security and operations

- Trust boundaries, release effects, external writes and rollback.

## Acceptance criteria

- [ ] Observable contract behavior and verification evidence.
- [ ] Compatibility and relevant rejection behavior.
- [ ] Documentation and consumer migration effects.

## Verification

- Required and focused checks.

## Out of scope

- Explicit exclusions and deferred work.
```

Acceptance criteria MUST describe observable behavior or verifiable invariants,
not implementation activities. Known limitations MUST be visible.

## Pull-request-sized work

A pull request MUST solve one coherent contract problem; leave the candidate
bundle valid; include schemas, examples, tests, documentation and migration
notes required by that outcome; and be reviewable without an unmerged
speculative follow-up.

Split independent semantic changes, broad cleanup, dependency upgrades and
unrelated formatting. A vertical contract change may legitimately touch the
registry, schema, examples, validators, tests and documentation together.
Placeholder contract generations MUST NOT be added for roadmap appearance.

## Development workflow

1. Select the workflow defined in [Issue timing](#issue-timing).
2. Prepare one focused change without staging, committing or pushing for the
   owner.
3. Add positive and relevant negative conformance cases.
4. Implement the smallest coherent contract change and update documentation.
5. Format and run the exact repository checks.
6. Review the full diff for secrets, generated churn, accidental semantics,
   assumptions, bundle-version consistency and unrelated edits.
7. Print the canonical [completion report](#completion-report).
8. The owner creates or confirms the issue and branch, may adjust the change,
   commits with `[#N]`, pushes and opens the pull request.

Do not store task-specific issue bodies, PR descriptions or handoff notes in
the repository.

## External operations and destructive actions

Read-only inspection is allowed when relevant. Filesystem, GitHub, release and
other external mutations MUST remain within the requested scope and granted
authority.

- Validation MUST remain offline and side-effect-free outside disposable local
  caches and build output.
- Contract validation MUST NOT fetch remote schemas or artifacts.
- Credentials and sensitive data MUST NOT appear in schemas, examples, logs,
  fixtures or Git.
- Publishing bundles, releases or package artifacts requires explicit
  authorization and an immutable reviewed source revision.
- Deletion, history changes and replacement of published contract generations
  require explicit authorization and verified exact targets.

## Verification and constrained environments

Resolve locked dependencies once after checkout or dependency changes:

```sh
make bootstrap
```

Run the network-independent inner loop before handoff:

```sh
make verify
```

Run the complete non-publishing acceptance aggregate when current advisory data
is available:

```sh
make validate
```

The stable targets wrap these exact checks:

```sh
pnpm format:check
pnpm contracts:check
pnpm typecheck
pnpm test
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked ty check
uv run --locked python scripts/validate.py
uv run --locked python scripts/validate_api.py
uv run --locked python scripts/validate_native_worker_api.py
uv run --locked python -m unittest discover -s tests -v
```

`make verify` wraps deterministic generation, source and test checks and is
offline after `make bootstrap`. `make validate` adds the network-dependent
supply-chain checks. The command ownership and timing tiers are recorded in the
[harness guide](docs/development/harness.md).

When a check cannot run because of sandbox restrictions, network, credentials,
missing tools or another environmental constraint, report the exact check as
**not run**, the blocker, safe attempts, evidence that did run, residual risk,
and where it should run. Never weaken a check or claim an unexecuted check
passed. Report failures even when they appear unrelated.

## Documentation

Every long narrative document MUST contain a `## TL;DR` immediately after its
title and status metadata. A document is long when it has at least 800 words,
more than five second-level sections, or is an architecture, security,
compatibility, migration or end-to-end guide readers consult selectively.
Issue and pull-request templates are excluded.

The TL;DR SHOULD state purpose, intended reader, important outcome and next
action in three to seven bullets. Contract changes MUST update affected field
semantics, compatibility and migration documentation. Accepted ADRs are
historical records; supersede rather than rewrite them.

## Pull request description

A pull request MUST state the linked issue and milestone; outcome and exclusions;
assumptions and unresolved questions; compatibility and consumer effects;
verification including checks not run; security and release effects; migration
and rollback; and known limitations.

## Review checklist

- [ ] MUST: The issue uses the required structure and exact milestone title.
- [ ] MUST: The change is one coherent contract outcome.
- [ ] MUST: Assumptions and affected producers and consumers are explicit.
- [ ] MUST: Published meaning changes only through a compatible or versioned
      transition.
- [ ] MUST: Positive and relevant rejection behavior is tested.
- [ ] MUST: Schema registry, examples, fixtures and bundle version agree.
- [ ] MUST: Validation remains deterministic and offline.
- [ ] MUST: Documentation and migration guidance are current.
- [ ] MUST: Applicable checks passed and unavailable checks are reported.
- [ ] MUST: No secrets, machine-specific paths or unrelated changes are present.
- [ ] MUST: An ADR exists when the decision meets the ADR threshold.

## Completion report

After every work item, print the repository, exact milestone, proposed issue
title, complete issue body, assumptions and limitations, verification outcomes
distinguished as passed/failed/not run, and a suggested `[#N]` commit subject.
When an issue exists, repeat or amend its content so delivered scope is auditable.
Printing the report does not publish external records.
