import { Schema } from "effect";

import { nonEmptyUniqueArray, StrictTimestamp } from "./common.js";
import { ResultRunId } from "./result-common.js";
import {
  MeasurementWindow,
  ProducerV2,
  RawArtifactReference,
  WorkloadIdentity,
} from "./transport-common.js";
import { SemanticVersion, WorkloadId } from "./workload-v1.js";

/** RawResultV2 records raw evidence with polymorphic execution provenance. */
export const RawResultV2 = Schema.Struct({
  schemaVersion: Schema.Literal(2),
  kind: Schema.Literal("RawResult"),
  contractsVersion: SemanticVersion,
  runId: ResultRunId,
  testId: WorkloadId,
  workload: WorkloadIdentity,
  producer: ProducerV2,
  measurementWindow: MeasurementWindow,
  createdAt: StrictTimestamp,
  artifacts: nonEmptyUniqueArray(RawArtifactReference),
}).annotations({ title: "Raw measurement artifact manifest with execution provenance" });

export type RawResultV2 = typeof RawResultV2.Type;
