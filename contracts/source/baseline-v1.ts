import { Schema } from "effect";

import { NormalizedResultArtifact } from "./analysis-v1.js";
import { OciImage } from "./catalogue-common.js";
import {
  Integer,
  NonBlankString,
  NonNegativeNumber,
  PositiveInteger,
  StrictTimestamp,
  uniqueArray,
} from "./common.js";
import { ResultRunId } from "./result-common.js";
import { Dataset, SemanticVersion, Sha256, WorkloadId } from "./workload-v1.js";

const BaselineState = Schema.Literal("CANDIDATE", "QUALIFIED", "APPROVED", "RETIRED").annotations({
  identifier: "state",
});

const Identity = Schema.Struct({
  id: WorkloadId,
  version: SemanticVersion,
  sha256: Sha256,
}).annotations({ identifier: "identity" });

const qualificationRules = [
  {
    if: { properties: { status: { const: "PASSED" } } },
    then: { required: ["sampleCount", "maximumCv"] },
  },
  {
    if: { properties: { status: { const: "FAILED" } } },
    then: { properties: { reasons: { minItems: 1 } } },
  },
] as const;

const Qualification = Schema.Struct({
  status: Schema.Literal("PENDING", "PASSED", "FAILED"),
  reasons: uniqueArray(NonBlankString),
  sampleCount: Schema.optional(PositiveInteger),
  maximumCv: Schema.optional(NonNegativeNumber),
}).pipe(
  Schema.filter(
    (value) =>
      (value.status !== "PASSED" || ("sampleCount" in value && "maximumCv" in value)) &&
      (value.status !== "FAILED" || value.reasons.length >= 1),
    {
      message: () => "Baseline qualification status and evidence are inconsistent",
      jsonSchema: { allOf: qualificationRules },
    },
  ),
);

const LifecycleEntry = Schema.Struct({
  state: BaselineState,
  at: StrictTimestamp,
  actor: NonBlankString.pipe(Schema.maxLength(128)),
  reason: NonBlankString.pipe(Schema.maxLength(1024)),
});

/** BaselineV1 records a versioned baseline and its explicit approval history. */
export const BaselineV1 = Schema.Struct({
  schemaVersion: Schema.Literal(1),
  kind: Schema.Literal("PerformanceBaseline"),
  id: WorkloadId,
  version: SemanticVersion,
  revision: Integer.pipe(Schema.between(1, 9_007_199_254_740_991)),
  state: BaselineState,
  testId: WorkloadId,
  sourceRunId: ResultRunId,
  artifact: NormalizedResultArtifact,
  software: Schema.Struct({
    gitSha: Schema.String.pipe(Schema.pattern(/^[A-Fa-f0-9]{40}$/)),
    image: OciImage,
    version: Schema.optional(NonBlankString),
  }),
  workload: Identity,
  environment: Schema.Struct({
    id: WorkloadId,
    version: SemanticVersion,
    sha256: Sha256,
    fingerprint: Sha256,
  }),
  dataset: Dataset,
  qualification: Qualification,
  createdAt: StrictTimestamp,
  lifecycle: Schema.Array(LifecycleEntry).pipe(Schema.minItems(1)),
}).annotations({ title: "Versioned performance baseline with explicit approval history" });

export type BaselineV1 = typeof BaselineV1.Type;
