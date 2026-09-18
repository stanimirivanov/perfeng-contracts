import { Schema } from "effect";

import { JsonValue, PositiveInteger } from "./common.js";

export const ResultRunId = Schema.String.pipe(
  Schema.pattern(/^perf-[0-9]{8}-[0-9]{6}-[a-f0-9]{8}$/),
).annotations({
  description: "Reference to the run metadata",
});

const MetricType = Schema.NullOr(
  Schema.Literal("latency", "throughput", "error_rate", "resource", "custom"),
);

export const ResultMetric = Schema.Struct({
  name: Schema.String.pipe(Schema.minLength(1), Schema.pattern(/^[a-z][a-z0-9_.]*$/)).annotations({
    description: "Metric name following naming convention",
  }),
  direction: Schema.Literal("lower-is-better", "higher-is-better").annotations({
    description: "Whether lower or higher values are better",
  }),
  type: Schema.optional(MetricType).annotations({
    default: null,
    description: "Metric type",
  }),
  unit: Schema.optional(Schema.NullOr(Schema.String)).annotations({
    default: null,
    description: "Unit of measurement (ms, req/s, %, etc.)",
  }),
});

const SloThreshold = Schema.Struct({
  passed: Schema.Boolean,
  threshold: Schema.optional(Schema.NullOr(Schema.String)).annotations({ default: null }),
  actual: Schema.optional(Schema.NullOr(Schema.Number)).annotations({ default: null }),
}).annotations({ identifier: "SloThreshold" });

const RegressionThreshold = Schema.Struct({
  passed: Schema.Boolean,
  baselineValue: Schema.optional(Schema.NullOr(Schema.Number)).annotations({ default: null }),
  actualValue: Schema.optional(Schema.NullOr(Schema.Number)).annotations({ default: null }),
  percentChange: Schema.optional(Schema.NullOr(Schema.Number)).annotations({ default: null }),
}).annotations({ identifier: "RegressionThreshold" });

export const ResultThresholds = Schema.Struct({
  slo: Schema.optional(
    Schema.NullOr(Schema.Record({ key: Schema.String, value: SloThreshold })),
  ).annotations({
    default: null,
    description: "SLO threshold results",
  }),
  regression: Schema.optional(
    Schema.NullOr(Schema.Record({ key: Schema.String, value: RegressionThreshold })),
  ).annotations({
    default: null,
    description: "Regression threshold results",
  }),
}).annotations({ identifier: "ResultThresholds" });

export const OptionalResultThresholds = Schema.optional(
  Schema.NullOr(ResultThresholds),
).annotations({
  default: null,
  description: "Threshold evaluation results",
});

const ResultMetadata = Schema.Record({ key: Schema.String, value: JsonValue }).annotations({
  identifier: "ResultMetadata",
});

export const OptionalResultMetadata = Schema.optional(Schema.NullOr(ResultMetadata)).annotations({
  default: null,
  description: "Additional metadata",
});

function optionalNullableNumber(description: string) {
  return Schema.optional(Schema.NullOr(Schema.Number)).annotations({
    default: null,
    description,
  });
}

function optionalNullableNonNegativeNumber(description: string) {
  return Schema.optional(
    Schema.NullOr(Schema.Number.pipe(Schema.greaterThanOrEqualTo(0))),
  ).annotations({
    default: null,
    description,
  });
}

export const DistributionStatistics = {
  mean: optionalNullableNumber("Arithmetic mean"),
  median: optionalNullableNumber("Median (p50)"),
  p90: optionalNullableNonNegativeNumber("90th percentile"),
  p95: optionalNullableNonNegativeNumber("95th percentile"),
  p99: optionalNullableNonNegativeNumber("99th percentile"),
  stddev: optionalNullableNonNegativeNumber("Standard deviation"),
  min: optionalNullableNumber("Minimum value"),
  max: optionalNullableNumber("Maximum value"),
  cv: optionalNullableNonNegativeNumber("Coefficient of variation"),
} as const;

export const RequiredSampleCount = PositiveInteger.annotations({
  description: "Number of samples",
});
