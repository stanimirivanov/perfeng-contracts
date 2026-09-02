# Performance policies and analysis outcomes

The candidate bundle `0.4.0` introduces `policy/v1` and `analysis/v1` without
changing existing schemas. These are interchange contracts, not an analysis
engine, API implementation, or stable release.

## Policy rules

A `PerformancePolicy` has an owned, versioned identity and uniquely named rules.
Each rule selects an exact metric name, statistic, and unit. Selectors must not
repeat the same name/statistic pair, even with different units. Consumers must
resolve the selected statistic from normalized evidence without substituting
another statistic or silently converting units.

Each rule configures an SLO, a regression comparison, or both:

- SLO `min` and `max` bounds are inclusive and expressed in the selected unit.
  When both exist, `min` must not exceed `max`.
- Regression `direction` specifies whether lower or higher values are better.
  `practicalDifference.kind` is `relative` or `absolute`, with a positive value.
  Relative `0.10` means 10%, not ten times the reference. Absolute differences
  use the selected metric unit.
- Regression `reference` names a baseline ID and a pinned version. Baseline
  resolution must preserve the mapping to immutable normalized artifacts;
  neither floating aliases nor automatic baseline promotion are implied.

For lower-is-better metrics, directed change is candidate minus reference;
for higher-is-better metrics it is reference minus candidate. Relative effect
divides directed change by the absolute reference value. Positive effect means
degradation. A decisive report claims `FAIL` at or above the configured practical
difference and `PASS` below it. A zero reference makes relative comparison
inconclusive; do not manufacture a percentage. An analyzer may remain inconclusive
when evidence does not justify a decisive outcome.

Optional quality requirements are `minSamples` and `maxCv`. Sample counts must be
known positive integers; unavailable counts are never zero. Thresholds require
metric-specific empirical calibration. There is no universal acceptable CV or
production sample count. Quality evidence must cover the measurements used for
the decision, including relevant reference measurements. When reporting a single
count/CV across inputs, use the minimum known count and worst applicable CV;
missing required evidence prevents a quality pass.

## Independent outcomes

An `AnalysisResult` accounts for every policy rule exactly once, with separate
quality, SLO, and regression sections. It has no overall performance-pass field.

| Section | Statuses | Meaning |
| --- | --- | --- |
| Quality | `PASS`, `INVALID`, `UNSTABLE`, `INCONCLUSIVE`, `NOT_EVALUATED` | Whether the measurements support evaluation |
| SLO | `PASS`, `FAIL`, `INCONCLUSIVE`, `NOT_EVALUATED` | Whether the selected value satisfies absolute bounds |
| Regression | `PASS`, `FAIL`, `INCONCLUSIVE`, `NOT_EVALUATED` | Whether comparison supports a practical degradation verdict |

Non-pass outcomes require reasons. If quality is not `PASS`, neither SLO nor
regression may claim `PASS` or `FAIL`. An unconfigured SLO/regression section must
be `NOT_EVALUATED`. Missing evidence for a configured decision means
`INCONCLUSIVE`, consistent with the policy's required `missingData: inconclusive`.
A missing reference need not prevent an independently supported SLO decision.
Passing an SLO does not imply passing a regression comparison.

Run lifecycle, execution errors, and environment health remain separate from
these outcomes. Consumers must assess whether those conditions invalidate the
measurements and record quality reasons; a completed run alone proves no quality
or performance outcome.

Only `observe` and `inform` modes are currently supported. Every report has
`blocking: false`. `inform` permits presentation of findings, not an automatic
authorization to post PR comments or change external statuses. `confirm` and
`block` need later contracts and calibrated decision logic.

## Evidence and validation boundaries

Reports pin policy identity, version, mode, and SHA-256 of the exact policy file
bytes. They reference one candidate normalized artifact and zero or more
reference normalized artifacts using the existing immutable artifact contract.
The candidate run ID must match the report; references must come from different
runs. Artifact IDs and URIs cannot repeat. A decisive regression must identify
a declared reference artifact, numeric candidate/reference values, an effect,
and a versioned method. A decisive SLO must include its numeric value.

The offline bundle validator resolves policy examples by identity, version, and
checksum, then checks rule coverage, selectors, quality requirements, bounds,
and claimed effect arithmetic. Calling the analysis consistency helper without
a policy performs only report-local checks. JSON Schema alone cannot enforce
these cross-document rules. JSON tooling rejects non-finite numbers, including
overflowing numeric literals.

Consumers still need to retrieve and verify referenced bytes, sizes, checksums,
schema versions, test and run identities, workload/environment comparability,
units, measurement windows, source evidence, and timestamps. They must verify
that reported values and quality evidence actually derive from those inputs,
and that baseline resolution matches the pinned identity/version. Report
validation does not perform those retrievals, recompute statistics, validate a
statistical method, or establish scientific confidence. There is no implemented
normalization, calibration, hypothesis-testing, or production gating engine here.

The executable examples cover an SLO pass alongside a regression failure, a
missing baseline, and unavailable samples. The browser comparison uses synthetic
two-sample fixtures and `synthetic-point-comparison`, solely to exercise contract
arithmetic and provenance. Its sample threshold and decisive outcomes are not
recommendations for production inference. Tests verify policy/artifact checksums
against exact local fixture bytes, including the synthetic baseline's raw source.

## Migrating prototype policies

Keep prototype YAML files unchanged until their consumers are migrated. Convert
them explicitly, with owner review:

1. Use `apiVersion: performance.perfeng.io/v1` and `kind: PerformancePolicy`,
   replacing prototype `performance.platform.io/v1` shapes where present. Add
   metadata ownership and a three-part version such as `1.0.0`, not `1.0`.
2. Map each prototype threshold to an actual catalogue metric, statistic, and
   unit. A label such as `checkout_duration_p95` is not automatically a valid
   catalogue metric selector.
3. Convert quantities such as `500ms` to numeric `max: 500` with unit `ms`.
   Preserve scale: an error ratio of `0.01` is 1%, not a ratio of `1`.
4. Make practical differences explicitly relative or absolute. In particular,
   error-rate percentage changes and percentage-point changes are not equivalent;
   do not infer the intended meaning from an untyped prototype value.
5. Pin baseline identity/version, select `observe` or `inform`, and make missing
   data inconclusive. Preserve independent quality, SLO, and regression outcomes.
6. Calibrate quality and comparison methods before considering later blocking
   modes. Do not translate a legacy Boolean verdict into evidence that was never
   collected.

Policy hashes identify the stored UTF-8 bytes, not a reserialized equivalent
object. Reformatting a policy or fixture changes its hash and requires updating
its references. Pin a merged contracts commit until an actual release exists.
