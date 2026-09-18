import { Schema } from "effect";

import {
  DistributionStatistics,
  OptionalResultMetadata,
  OptionalResultThresholds,
  RequiredSampleCount,
  ResultMetric,
  ResultRunId,
} from "./result-common.js";

const ResultDistributionV1 = Schema.Struct({
  samples: RequiredSampleCount,
  ...DistributionStatistics,
});

/** ResultV1 is the original normalized metric contract with a required sample count. */
export const ResultV1 = Schema.Struct({
  schemaVersion: Schema.Literal(1).annotations({
    jsonSchema: { type: "integer", const: 1, description: "Schema version" },
  }),
  runId: ResultRunId,
  metric: ResultMetric,
  distribution: ResultDistributionV1,
  thresholds: OptionalResultThresholds,
  metadata: OptionalResultMetadata,
}).annotations({
  title: "Normalized Test Result",
  description: "Normalized performance test result independent of tool",
});

export type ResultV1 = typeof ResultV1.Type;
