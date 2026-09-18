import { Schema } from "effect";

import {
  nonEmptyArray,
  nonEmptyUniqueArray,
  PositiveInteger,
  StrictTimestamp,
  uniqueArray,
} from "./common.js";
import { EnvironmentIdentity } from "./playwright-common.js";
import { ResultRunId } from "./result-common.js";
import { RawArtifactReference } from "./transport-common.js";
import { SemanticVersion, Sha256, WorkloadId, WorkloadProfile } from "./workload-v1.js";

const WorkloadIdentity = Schema.Struct({
  id: WorkloadId,
  version: SemanticVersion,
  profile: WorkloadProfile,
  sha256: Sha256,
}).annotations({ identifier: "workloadIdentity" });

const BrowserEnvironmentArtifact = Schema.Struct({
  ...RawArtifactReference.fields,
  mediaType: Schema.Literal("application/json"),
  format: Schema.Literal("browser-environment/v1"),
});

const CaptureScope = Schema.Union(
  Schema.Struct({ kind: Schema.Literal("run") }),
  Schema.Struct({ kind: Schema.Literal("iteration"), iteration: PositiveInteger }),
);

const captureRules = [
  {
    if: { properties: { status: { enum: ["COMPLETE", "INCOMPLETE"] } } },
    then: { required: ["artifact"] },
    else: { not: { required: ["artifact"] } },
  },
  {
    if: { properties: { status: { const: "COMPLETE" } } },
    then: { properties: { reasons: { maxItems: 0 } } },
    else: { properties: { reasons: { minItems: 1 } } },
  },
  {
    if: { properties: { type: { const: "trace" } } },
    then: { required: ["dataLossOccurred"] },
    else: { not: { required: ["dataLossOccurred"] } },
  },
] as const;

const CaptureShape = Schema.Struct({
  type: Schema.Literal(
    "observations",
    "network-summary",
    "console",
    "trace",
    "cpu-profile",
    "heap-snapshot-before",
    "heap-snapshot-after",
    "allocation-profile",
    "screenshot",
    "video",
  ),
  scope: CaptureScope,
  status: Schema.Literal("COMPLETE", "INCOMPLETE", "FAILED", "NOT_SUPPORTED"),
  reasons: uniqueArray(Schema.String.pipe(Schema.minLength(1))),
  sensitive: Schema.Boolean,
  dataLossOccurred: Schema.optional(Schema.NullOr(Schema.Boolean)),
  artifact: Schema.optional(RawArtifactReference),
});

const Capture = CaptureShape.pipe(
  Schema.filter(
    (value) => {
      const hasArtifact = "artifact" in value;
      const hasDataLoss = "dataLossOccurred" in value;
      const artifactMatches =
        value.status === "COMPLETE" || value.status === "INCOMPLETE" ? hasArtifact : !hasArtifact;
      const reasonsMatch =
        value.status === "COMPLETE" ? value.reasons.length === 0 : value.reasons.length >= 1;
      const dataLossMatches = value.type === "trace" ? hasDataLoss : !hasDataLoss;
      return artifactMatches && reasonsMatch && dataLossMatches;
    },
    {
      message: () => "Capture status, evidence, reasons and data-loss fields are inconsistent",
      jsonSchema: { allOf: captureRules },
    },
  ),
).annotations({ identifier: "capture" });

/** BrowserDiagnosticsV1 records diagnostic capture coverage and immutable evidence. */
export const BrowserDiagnosticsV1 = Schema.Struct({
  schemaVersion: Schema.Literal(1),
  kind: Schema.Literal("BrowserDiagnostics"),
  runId: ResultRunId,
  testId: WorkloadId,
  workload: WorkloadIdentity,
  environment: Schema.Struct({
    profile: EnvironmentIdentity.fields.profile,
    fingerprint: EnvironmentIdentity.fields.fingerprint,
    artifact: BrowserEnvironmentArtifact,
  }),
  execution: Schema.Struct({
    mode: Schema.Literal("lightweight", "trace", "memory", "smoothness"),
    contextReuse: Schema.Literal("per-iteration", "per-run"),
    pageReuse: Schema.Literal("per-iteration", "per-run"),
    captureIterations: nonEmptyUniqueArray(PositiveInteger),
  }),
  sources: nonEmptyUniqueArray(Schema.Literal("playwright", "web-performance", "cdp", "windows")),
  captureWindow: Schema.Struct({ start: StrictTimestamp, end: StrictTimestamp }),
  captures: nonEmptyArray(Capture),
  createdAt: StrictTimestamp,
}).annotations({ title: "Browser diagnostic capture manifest" });

export type BrowserDiagnosticsV1 = typeof BrowserDiagnosticsV1.Type;
