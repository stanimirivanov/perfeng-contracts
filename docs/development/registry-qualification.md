# AxonOps registry qualification

## TL;DR

- Run this optional gate against the pinned Linux AMD64 executable in a private
  loopback-only network namespace.
- The gate checks the exact current Git corpus and every SR-10 historical
  profile. Missing inputs block qualification.
- The pinned candidate returned `NOT_ADMITTED` and the admission command failed. It cannot
  be used to satisfy the Option C admission prerequisite.

## Prepare the exact inputs

Acquire the [pinned upstream release archive](https://github.com/axonops/axonops-schema-registry/releases/tag/v0.4.0-mcp-phase7)
and verify its SHA-256 against
[the candidate lock](../../tests/qualification/axonops/candidate.lock.json)
before extracting the executable into a private directory. The runner also
verifies the executable digest before launch. Prepare the exact Git objects
listed by the [historical selection inventory](../../distribution/supported-selections.json)
using the [historical distribution instructions](contract-distribution.md).
No command in the gate downloads missing inputs.

Run `make registry-qualification-check` to test the qualification logic.
Run the actual gate on Linux with user and network namespace support,
iproute2 and the prepared executable:

```sh
make registry-admission REGISTRY_BINARY=/absolute/path/to/schema-registry
```

The candidate starts with memory storage and binds only to loopback inside the
private namespace. The runner verifies the interface inventory before starting
the executable, uses a temporary directory, and stops the process on exit.
If namespace creation fails, the Make target fails before running the
candidate. If a corpus or capability check fails, the JSON receipt records
`NOT_ADMITTED`; absent observations never satisfy a required check. Retain
the receipt with the candidate and current source revisions it reports.

## Observed result

The pinned replay exercised 61 JSON Schema instances and seven OpenAPI
documents across current and historical profiles. Explicit cross-subject
reference registration and retrieval passed. The registry rejected current
and historical schema registrations, including the known regex-dependent
schemas. The compatibility endpoint rejected a newly required field but
incorrectly approved conditional tightening. A Draft 2020-12 witness
independently establishes that the conditional change rejects an instance the
original schema accepts.

Formatting-distinct equivalent schemas did not retain independently
retrievable exact bytes. The native OpenAPI registrations failed. The
diagnostic generic-JSON registration accepted removal of all API paths.
Neither generic storage nor registry IDs establish contract compatibility or
published byte identity.
OpenAPI is diagnostic here. Option C retains bundled OpenAPI separately,
so native OpenAPI support is not an admission requirement for that option.

The exercise does not establish persistent backup/recovery, hosted identity,
authorization or production operational behavior. Persistent recovery is
a separate qualification with its own receipt.
