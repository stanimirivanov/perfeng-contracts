import { Schema } from "effect";

import {
  NonBlankString,
  NonNegativeInteger,
  nonEmptyUniqueArray,
  PositiveInteger,
  StrictTimestamp,
  Uuid,
} from "./common.js";
import { ResultRunId } from "./result-common.js";
import { MeasurementWindow, WorkloadIdentity } from "./transport-common.js";
import { Sha256, WorkloadId } from "./workload-v1.js";

/** Required observations; the reviewed profile supplies thresholds and capture policy. */
export const KubernetesBenchmarkChecks = [
  "cluster-identity",
  "node-readiness",
  "placement",
  "capacity",
  "resource-pressure",
  "interference",
] as const;

const Check = Schema.Struct({
  id: Schema.Literal(...KubernetesBenchmarkChecks),
  status: Schema.Literal("PASS", "FAIL", "UNKNOWN"),
  reason: NonBlankString,
});

const Checks = nonEmptyUniqueArray(Check).pipe(
  Schema.maxItems(KubernetesBenchmarkChecks.length),
  Schema.filter(
    (checks) =>
      KubernetesBenchmarkChecks.every(
        (id) => checks.filter((check) => check.id === id).length === 1,
      ),
    {
      message: () => "Every required benchmark check must appear exactly once",
      jsonSchema: {
        allOf: KubernetesBenchmarkChecks.map((id) => ({
          contains: { properties: { id: { const: id } }, required: ["id"] },
          minContains: 1,
          maxContains: 1,
        })),
      },
    },
  ),
);

const Node = Schema.Struct({
  name: NonBlankString,
  uid: Uuid,
  kubernetesVersion: NonBlankString,
  containerRuntimeVersion: NonBlankString,
  architecture: Schema.Literal("amd64", "arm64"),
  allocatable: Schema.Struct({ cpuMilliCores: PositiveInteger, memoryBytes: PositiveInteger }),
});

const Condition = Schema.Literal("TRUE", "FALSE", "UNKNOWN");
const Sample = Schema.Struct({
  nodeUid: Uuid,
  observedAt: StrictTimestamp,
  conditions: Schema.Struct({
    ready: Condition,
    memoryPressure: Condition,
    diskPressure: Condition,
    pidPressure: Condition,
  }),
  usage: Schema.Union(
    Schema.Struct({
      source: Schema.Literal("metrics-api"),
      windowStart: StrictTimestamp,
      windowEnd: StrictTimestamp,
      cpuMilliCores: NonNegativeInteger,
      memoryBytes: NonNegativeInteger,
    }),
    Schema.Struct({ source: Schema.Literal("unavailable"), reason: NonBlankString }),
  ),
});

const Scope = Schema.Union(
  Schema.Struct({ kind: Schema.Literal("preflight") }),
  Schema.Struct({
    kind: Schema.Literal("measurement"),
    runId: ResultRunId,
    testId: WorkloadId,
    workload: WorkloadIdentity,
  }),
);

const failedCheck = { contains: { properties: { status: { const: "FAIL" } } } };
const unknownCheck = { contains: { properties: { status: { const: "UNKNOWN" } } } };
const statusRules = [
  {
    if: { properties: { checks: failedCheck } },
    then: { properties: { status: { const: "REJECTED" } } },
    else: {
      if: { properties: { checks: unknownCheck } },
      then: { properties: { status: { const: "UNKNOWN" } } },
      else: {
        properties: {
          status: { const: "ACCEPTED" },
          nodes: { minItems: 1 },
          samples: { minItems: 1 },
        },
      },
    },
  },
] as const;

/** Shared preflight/run evidence, not execution authority or baseline approval. */
export const KubernetesBenchmarkEvidenceV1 = Schema.Struct({
  schemaVersion: Schema.Literal(1),
  kind: Schema.Literal("KubernetesBenchmarkEvidence"),
  scope: Scope,
  profile: Schema.Struct({
    ...WorkloadIdentity.fields,
    purpose: Schema.Literal("integration", "performance-comparison"),
  }),
  environment: Schema.Struct({ ...WorkloadIdentity.fields, fingerprint: Sha256 }),
  target: Schema.Struct({ clusterId: WorkloadId, kubeSystemUid: Uuid }),
  captureWindow: MeasurementWindow,
  status: Schema.Literal("ACCEPTED", "REJECTED", "UNKNOWN"),
  checks: Checks,
  nodes: Schema.Array(Node).pipe(Schema.maxItems(256)),
  samples: Schema.Array(Sample).pipe(Schema.maxItems(4096)),
})
  .pipe(
    Schema.filter(
      (value) => {
        const expected = value.checks.some((check) => check.status === "FAIL")
          ? "REJECTED"
          : value.checks.some((check) => check.status === "UNKNOWN")
            ? "UNKNOWN"
            : "ACCEPTED";
        return (
          value.status === expected &&
          (expected !== "ACCEPTED" || (value.nodes.length > 0 && value.samples.length > 0))
        );
      },
      {
        message: () => "Benchmark status must summarize all required checks and available evidence",
        jsonSchema: { allOf: statusRules },
      },
    ),
  )
  .annotations({ title: "Kubernetes benchmark qualification and interference evidence" });

export type KubernetesBenchmarkEvidenceV1 = typeof KubernetesBenchmarkEvidenceV1.Type;
