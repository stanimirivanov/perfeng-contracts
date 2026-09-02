# Extraction provenance

Source repository: https://github.com/stanimirivanov/performance-platform

Source revision: `57c1b5074898d4d86476e8b4f99c19eff3a77018`.

Extracted paths:

- `schemas/`
- `examples/metadata/`
- `docs/architecture/metric-naming.md`
- `docs/architecture/schema-versioning.md`

Git fast-export filtered the source history to these paths and fast-import
reconstructed it in an isolated temporary repository. Four relevant commits
retain their author, date, message, and selected file history. Their SHA values
change because the trees and ancestry are filtered. The destination's original
license commit remains the main-line ancestor; an unrelated-history merge
connects the imported commits to it. No source history is rewritten.

The four schema moves into domain/version directories happen after extraction,
so `git log --follow -- schemas/result/v1/test-result.schema.json` can follow the
file's previous path once the PR is committed. Preserve the PR merge ancestry
on GitHub; squash merging discards that ancestry.

Intentional content changes in this PR:

- Versioned schema paths and matching `$id` values.
- Result metric type accepts its declared null default.
- New examples for the standalone candidate and environment contracts.
- Metric documentation examples use valid underscores in service names.
- The inconsistent prototype version policy is superseded by compatibility.md.

The prototype's schemas and consumers remain available during migration.
This extraction does not publish a release, deploy services, or migrate data.
