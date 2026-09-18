import { Schema } from "effect";

import {
  NonBlankString,
  NonNegativeNumber,
  nonEmptyUniqueArray,
  PositiveInteger,
  StrictTimestamp,
  Uuid,
  uniqueArray,
} from "./common.js";
import { MetricSelector } from "./policy-v1.js";
import { ResultRunId } from "./result-common.js";
import { NormalizedArtifactReference, ProducerV1 } from "./transport-common.js";
import { SemanticVersion, Sha256, WorkloadId } from "./workload-v1.js";

export const NormalizedResultArtifact = Schema.Struct({
  ...NormalizedArtifactReference.fields,
  mediaType: Schema.Literal("application/json"),
  format: Schema.Literal("normalized-result/v1"),
});

const Reasons = uniqueArray(NonBlankString);

const QualityOutcome = Schema.Struct({
  status: Schema.Literal("PASS", "INVALID", "UNSTABLE", "INCONCLUSIVE", "NOT_EVALUATED"),
  reasons: Reasons,
  samples: Schema.optional(PositiveInteger),
  cv: Schema.optional(NonNegativeNumber),
});

const decisiveValueRule = [
  {
    if: { properties: { status: { enum: ["PASS", "FAIL"] } } },
    then: { required: ["value"], properties: { value: { type: "number" } } },
  },
] as const;

const SloOutcome = Schema.Struct({
  status: Schema.Literal("PASS", "FAIL", "INCONCLUSIVE", "NOT_EVALUATED"),
  reasons: Reasons,
  value: Schema.optional(Schema.NullOr(Schema.Number)),
}).pipe(
  Schema.filter(
    (value) =>
      (value.status !== "PASS" && value.status !== "FAIL") || typeof value.value === "number",
    {
      message: () => "A decisive SLO outcome requires a numeric value",
      jsonSchema: { allOf: decisiveValueRule },
    },
  ),
);

const RegressionEffect = Schema.Struct({
  kind: Schema.Literal("relative", "absolute"),
  value: Schema.Number,
});

const AnalysisMethod = Schema.Struct({ name: NonBlankString, version: SemanticVersion });

const regressionValueRule = [
  {
    if: { properties: { status: { enum: ["PASS", "FAIL"] } } },
    then: {
      required: ["candidateValue", "referenceValue", "referenceArtifactId", "effect", "method"],
      properties: {
        candidateValue: { type: "number" },
        referenceValue: { type: "number" },
      },
    },
  },
] as const;

const RegressionOutcome = Schema.Struct({
  status: Schema.Literal("PASS", "FAIL", "INCONCLUSIVE", "NOT_EVALUATED"),
  reasons: Reasons,
  candidateValue: Schema.optional(Schema.NullOr(Schema.Number)),
  referenceValue: Schema.optional(Schema.NullOr(Schema.Number)),
  referenceArtifactId: Schema.optional(Uuid),
  effect: Schema.optional(RegressionEffect),
  method: Schema.optional(AnalysisMethod),
}).pipe(
  Schema.filter(
    (value) => {
      if (value.status !== "PASS" && value.status !== "FAIL") {
        return true;
      }
      return (
        typeof value.candidateValue === "number" &&
        typeof value.referenceValue === "number" &&
        "referenceArtifactId" in value &&
        "effect" in value &&
        "method" in value
      );
    },
    {
      message: () => "A decisive regression outcome requires complete numeric evidence",
      jsonSchema: { allOf: regressionValueRule },
    },
  ),
);

const Evaluation = Schema.Struct({
  ruleId: WorkloadId,
  metric: MetricSelector,
  quality: QualityOutcome,
  slo: SloOutcome,
  regression: RegressionOutcome,
});

/** AnalysisV1 records independent quality, SLO and regression outcomes. */
export const AnalysisV1 = Schema.Struct({
  schemaVersion: Schema.Literal(1),
  kind: Schema.Literal("AnalysisResult"),
  contractsVersion: SemanticVersion,
  runId: ResultRunId,
  testId: WorkloadId,
  createdAt: StrictTimestamp,
  producer: ProducerV1,
  policy: Schema.Struct({
    id: WorkloadId,
    version: SemanticVersion,
    sha256: Sha256,
    mode: Schema.Literal("observe", "inform"),
  }),
  candidateArtifact: NormalizedResultArtifact,
  referenceArtifacts: uniqueArray(NormalizedResultArtifact),
  blocking: Schema.Literal(false),
  evaluations: nonEmptyUniqueArray(Evaluation),
}).annotations({ title: "Independent quality, requirement, and regression outcomes" });

export type AnalysisV1 = typeof AnalysisV1.Type;
