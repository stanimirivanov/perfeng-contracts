import { Schema } from "effect";

import { PositiveInteger } from "./common.js";
import {
  DistributionStatistics,
  OptionalResultMetadata,
  OptionalResultThresholds,
  ResultMetric,
  ResultRunId,
} from "./result-common.js";

const ResultDistributionV2 = Schema.Struct({
  samples: Schema.optional(Schema.NullOr(PositiveInteger)).annotations({
    description:
      "Known positive observation count, or absent/null when unavailable. Never invent a count.",
  }),
  ...DistributionStatistics,
});

/** ResultV2 permits an unavailable sample count without inventing evidence. */
export const ResultV2 = Schema.Struct({
  schemaVersion: Schema.Literal(2).annotations({
    jsonSchema: { type: "integer", const: 2 },
  }),
  runId: ResultRunId,
  metric: ResultMetric,
  distribution: ResultDistributionV2,
  thresholds: OptionalResultThresholds,
  metadata: OptionalResultMetadata,
}).annotations({
  title: "Normalized metric with explicit support for unavailable sample counts",
});

export type ResultV2 = typeof ResultV2.Type;
