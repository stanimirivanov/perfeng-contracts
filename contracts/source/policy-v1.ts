import { Schema } from "effect";

import {
  NonBlankString,
  NonNegativeNumber,
  nonEmptyUniqueArray,
  PositiveInteger,
  PositiveNumber,
} from "./common.js";
import { ResultMetric } from "./result-common.js";
import { SemanticVersion, WorkloadId } from "./workload-v1.js";

export const MetricSelector = Schema.Struct({
  name: ResultMetric.fields.name,
  statistic: Schema.Literal("mean", "median", "p90", "p95", "p99", "min", "max"),
  unit: NonBlankString,
}).annotations({ identifier: "metricSelector" });

function atLeastOneProperty<S extends Schema.Schema.Any>(schema: S) {
  return schema.pipe(
    Schema.filter((value) => Object.keys(value as object).length >= 1, {
      message: () => "Expected at least one configured property",
      jsonSchema: { minProperties: 1 },
    }),
  );
}

const QualityThreshold = atLeastOneProperty(
  Schema.Struct({
    minSamples: Schema.optional(PositiveInteger),
    maxCv: Schema.optional(NonNegativeNumber),
  }),
);

const SloThreshold = atLeastOneProperty(
  Schema.Struct({
    min: Schema.optional(Schema.Number),
    max: Schema.optional(Schema.Number),
  }),
);

const RegressionThreshold = Schema.Struct({
  direction: Schema.Literal("lower-is-better", "higher-is-better"),
  practicalDifference: Schema.Struct({
    kind: Schema.Literal("relative", "absolute"),
    value: PositiveNumber,
  }),
  reference: Schema.Struct({ baselineId: WorkloadId, version: SemanticVersion }),
});

const policyRuleFields = {
  id: WorkloadId,
  metric: MetricSelector,
  quality: Schema.optional(QualityThreshold),
} as const;

const PolicyRule = Schema.Union(
  Schema.Struct({
    ...policyRuleFields,
    slo: SloThreshold,
    regression: Schema.optional(RegressionThreshold),
  }),
  Schema.Struct({
    ...policyRuleFields,
    slo: Schema.optional(SloThreshold),
    regression: RegressionThreshold,
  }),
);

/** PolicyV1 defines non-blocking quality, SLO and regression evaluation rules. */
export const PolicyV1 = Schema.Struct({
  apiVersion: Schema.Literal("performance.perfeng.io/v1"),
  kind: Schema.Literal("PerformancePolicy"),
  metadata: Schema.Struct({
    name: WorkloadId,
    version: SemanticVersion,
    owner: NonBlankString,
  }),
  spec: Schema.Struct({
    mode: Schema.Literal("observe", "inform"),
    missingData: Schema.Literal("inconclusive"),
    rules: nonEmptyUniqueArray(PolicyRule),
  }),
}).annotations({ title: "Versioned non-blocking performance policy" });

export type PolicyV1 = typeof PolicyV1.Type;
