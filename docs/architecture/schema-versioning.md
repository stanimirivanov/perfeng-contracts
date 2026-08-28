# Schema Versioning Policy

## Overview

All schemas in the performance platform follow semantic versioning principles to
ensure backward compatibility and clear migration paths.

## Version Format

Schemas use integer version numbers (1, 2, 3, ...) stored in the `schemaVersion`
field of each document.

## Versioning Rules

1. **Incremental Changes**: Minor additions that don't break existing consumers
   increment the patch version.

2. **Breaking Changes**: Changes that would break existing consumers require a
   new major version.

3. **Deprecation**: Fields are deprecated for at least one major version before
   removal.

4. **Migration**: Migration tools are provided for each major version change.

## Current Schema Versions

| Schema                   | Version | Status |
|--------------------------|---------|--------|
| run-metadata.schema.json | 1       | Stable |
| test-result.schema.json  | 1       | Stable |
| environment.schema.json  | 1       | Stable |
| candidate.schema.json    | 1       | Stable |

## Migration Process

When a schema changes:

1. Create new schema version
2. Update validation utilities
3. Provide migration script
4. Update examples
5. Deprecate old version
6. Remove old version after grace period

## Compatibility

- Data written with version N must be readable by version N+1 validators
- Version N+1 data may not be readable by version N validators
- Raw data is never modified; only normalized data is migrated
