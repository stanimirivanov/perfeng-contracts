import { Schema } from "effect";

import { nonEmptyUniqueArray, StrictTimestamp } from "./common.js";
import { ResultRunId } from "./result-common.js";
import {
  MeasurementWindow,
  ProducerV1,
  RawArtifactReference,
  WorkloadIdentity,
} from "./transport-common.js";
import { SemanticVersion, WorkloadId } from "./workload-v1.js";

/** RawResultV1 records OCI-produced raw evidence and its execution context. */
export const RawResultV1 = Schema.Struct({
  schemaVersion: Schema.Literal(1),
  kind: Schema.Literal("RawResult"),
  contractsVersion: SemanticVersion,
  runId: ResultRunId,
  testId: WorkloadId,
  workload: WorkloadIdentity,
  producer: ProducerV1,
  measurementWindow: MeasurementWindow,
  createdAt: StrictTimestamp,
  artifacts: nonEmptyUniqueArray(RawArtifactReference),
}).annotations({ title: "Raw measurement artifact manifest" });

export type RawResultV1 = typeof RawResultV1.Type;
