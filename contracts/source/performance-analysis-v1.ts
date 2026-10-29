import { Schema } from "effect";

import { NormalizedResultArtifact } from "./analysis-v1.js";
import { artifactReference } from "./artifact-v1.js";
import { Integer, NonBlankString, StrictTimestamp } from "./common.js";
import { RequestContext, ScopedIdentity } from "./performance-integration-v1.js";
import { ResultRunId } from "./result-common.js";
import { WorkloadIdentity } from "./transport-common.js";
import { WorkloadId } from "./workload-v1.js";

/** Explicit native association retained at admission; never reconstructed from labels. */
export const AnalysisNativeBinding = Schema.Struct({
  runId: ResultRunId,
  testId: WorkloadId,
  workload: WorkloadIdentity,
  policy: WorkloadIdentity,
  baseline: Schema.NullOr(
    Schema.Struct({ identity: WorkloadIdentity, artifact: NormalizedResultArtifact }),
  ),
});

const AnalysisArtifact = Schema.Struct({
  ...artifactReference(Schema.Literal("analysis")).fields,
  sizeBytes: Integer.pipe(Schema.between(1, 1_048_576)),
  mediaType: Schema.Literal("application/json"),
  format: Schema.Literal("analysis-result/v1"),
});

/** Independent publication claims. Authentication and admission binding are external checks. */
export const PerformanceAnalysisV1 = Schema.Struct({
  specversion: Schema.Literal("1.0"),
  id: NonBlankString.pipe(Schema.maxLength(256)),
  source: ScopedIdentity.fields.issuer,
  type: Schema.Literal("dev.perfeng.integration.analysis-published.v1"),
  time: StrictTimestamp,
  datacontenttype: Schema.Literal("application/json"),
  dataschema: Schema.Literal(
    "https://perfeng.dev/schemas/performance-analysis/v1/performance-analysis.schema.json",
  ),
  data: Schema.Struct({
    context: RequestContext,
    run: ScopedIdentity,
    native: AnalysisNativeBinding,
    artifact: AnalysisArtifact,
  }),
});
