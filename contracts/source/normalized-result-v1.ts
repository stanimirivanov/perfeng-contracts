import { Schema } from "effect";

import { nonEmptyUniqueArray, StrictTimestamp } from "./common.js";
import { ResultRunId } from "./result-common.js";
import { ResultV2 } from "./result-v2.js";
import {
  MeasurementWindow,
  ProducerV1,
  RawArtifactReference,
  WorkloadIdentity,
} from "./transport-common.js";
import { SemanticVersion, WorkloadId } from "./workload-v1.js";

/** NormalizedResultV1 groups normalized metrics with their immutable raw evidence. */
export const NormalizedResultV1 = Schema.Struct({
  schemaVersion: Schema.Literal(1),
  kind: Schema.Literal("NormalizedResult"),
  contractsVersion: SemanticVersion,
  runId: ResultRunId,
  testId: WorkloadId,
  workload: WorkloadIdentity,
  producer: ProducerV1,
  measurementWindow: MeasurementWindow,
  createdAt: StrictTimestamp,
  sourceArtifacts: nonEmptyUniqueArray(RawArtifactReference),
  results: nonEmptyUniqueArray(ResultV2),
}).annotations({ title: "Normalized multi-metric result envelope" });

export type NormalizedResultV1 = typeof NormalizedResultV1.Type;
