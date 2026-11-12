import { Schema } from "effect";

import { AnalysisV1 } from "./analysis-v1.js";
import {
  AnalysisArtifact,
  AnalysisNativeBinding,
  PerformanceAnalysisV1,
} from "./performance-analysis-v1.js";
import { ResultMetric } from "./result-common.js";
import { WorkloadId } from "./workload-v1.js";

/** Reuse original report/publication semantics; availability belongs to the HTTP envelope. */
export const ComparisonEvidence = Schema.Struct({
  native: AnalysisNativeBinding,
  report: AnalysisArtifact,
  analysis: AnalysisV1,
  directions: Schema.Array(
    Schema.Struct({ ruleId: WorkloadId, direction: Schema.NullOr(ResultMetric.fields.direction) }),
  ).pipe(Schema.minItems(1), Schema.maxItems(1000)),
  publication: Schema.NullOr(PerformanceAnalysisV1),
});
