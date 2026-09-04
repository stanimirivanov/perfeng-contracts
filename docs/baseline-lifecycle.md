# Performance baseline lifecycle

Baseline/v1 defines a versioned, auditable anchor for candidate/reference
comparison. One baseline record points to one immutable normalized-result/v1
artifact from a completed source Run. A policy selects the exact `(id, version)`;
there is no `latest`, `current`, or automatically promoted alias.

The baseline captures the source software image and Git revision, workload
identity, environment definition and fingerprint, and dataset identity. These
fields are comparison inputs, not display-only metadata. A resolver must reject
an otherwise approved baseline when the candidate's required compatibility
dimensions do not match.

## States

The only forward transitions are:

```text
CANDIDATE -> QUALIFIED -> APPROVED -> RETIRED
        \-----------> RETIRED
                     QUALIFIED -> RETIRED
```

- `CANDIDATE` is explicitly created from a selected Run and is not usable by a
  regression policy.
- `QUALIFIED` has passed the recorded sample-count and variability checks but is
  still not an approved anchor.
- `APPROVED` records an explicit human or governed-system decision and is the
  only state eligible for policy resolution.
- `RETIRED` is terminal and prevents future selection without erasing history.

Every state change appends one lifecycle event with its actor, timestamp and
reason, increments the revision, and preserves all previous events. The first
event is CANDIDATE and matches `createdAt`; the current state is the final event.
Lifecycle validation rejects skipped, reversed, repeated or time-reordered
transitions.

Qualification `PASSED` requires the observed aggregate sample count and maximum
coefficient of variation. These are evidence summaries, not universal policy
thresholds. The service that performs qualification must resolve its reviewed
criteria and verify the normalized artifact before recording them.

Creating a new version never mutates the approved version's artifact or identity.
An approved anchor can coexist with later candidates and rolling Run history.
Promotion is always explicit; a successful or newer Run does not become a
baseline by itself.

JSON Schema validates each record's closed shape. The offline bundle validator
also checks artifact/source-Run binding, lifecycle order, revision/history
agreement, current-state agreement and qualification/state consistency. Durable
storage, authorization, optimistic updates, uniqueness of `(id, version)`, and
selection of an environment-compatible approved record belong to the control
plane.
