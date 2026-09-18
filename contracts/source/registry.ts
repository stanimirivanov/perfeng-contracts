import type { Schema } from "effect";

import { AnalysisV1 } from "./analysis-v1.js";
import { ArtifactV1 } from "./artifact-v1.js";
import { BaselineV1 } from "./baseline-v1.js";
import { BrowserDiagnosticsV1 } from "./browser-diagnostics-v1.js";
import { BrowserEnvironmentV1 } from "./browser-environment-v1.js";
import { CandidateV1 } from "./candidate-v1.js";
import { CatalogueV1 } from "./catalogue-v1.js";
import { CatalogueV2 } from "./catalogue-v2.js";
import { EnvironmentV1 } from "./environment-v1.js";
import { NormalizedResultV1 } from "./normalized-result-v1.js";
import { PlaywrightMeasurementsV1 } from "./playwright-measurements-v1.js";
import { PlaywrightMeasurementsV2 } from "./playwright-measurements-v2.js";
import { PolicyV1 } from "./policy-v1.js";
import { RawResultV1 } from "./raw-result-v1.js";
import { RawResultV2 } from "./raw-result-v2.js";
import { ResultV1 } from "./result-v1.js";
import { ResultV2 } from "./result-v2.js";
import { RunV1 } from "./run-v1.js";
import { WorkloadV1 } from "./workload-v1.js";

export interface GeneratedContract {
  readonly name: string;
  readonly id: string;
  readonly output: string;
  readonly schema: Schema.Schema.AnyNoContext;
}

/** Complete registry of Effect-authored data contracts and generated artifacts. */
export const GeneratedContracts: ReadonlyArray<GeneratedContract> = [
  {
    name: "candidate/v1",
    id: "https://perfeng.dev/schemas/candidate/v1/candidate.schema.json",
    output: "schemas/candidate/v1/candidate.schema.json",
    schema: CandidateV1,
  },
  {
    name: "environment/v1",
    id: "https://perfeng.dev/schemas/environment/v1/environment.schema.json",
    output: "schemas/environment/v1/environment.schema.json",
    schema: EnvironmentV1,
  },
  {
    name: "result/v1",
    id: "https://perfeng.dev/schemas/result/v1/test-result.schema.json",
    output: "schemas/result/v1/test-result.schema.json",
    schema: ResultV1,
  },
  {
    name: "result/v2",
    id: "https://perfeng.dev/schemas/result/v2/test-result.schema.json",
    output: "schemas/result/v2/test-result.schema.json",
    schema: ResultV2,
  },
  {
    name: "run/v1",
    id: "https://perfeng.dev/schemas/run/v1/run-metadata.schema.json",
    output: "schemas/run/v1/run-metadata.schema.json",
    schema: RunV1,
  },
  {
    name: "workload/v1",
    id: "https://perfeng.dev/schemas/workload/v1/workload.schema.json",
    output: "schemas/workload/v1/workload.schema.json",
    schema: WorkloadV1,
  },
  {
    name: "catalogue/v1",
    id: "https://perfeng.dev/schemas/catalogue/v1/test-catalogue.schema.json",
    output: "schemas/catalogue/v1/test-catalogue.schema.json",
    schema: CatalogueV1,
  },
  {
    name: "catalogue/v2",
    id: "https://perfeng.dev/schemas/catalogue/v2/test-catalogue.schema.json",
    output: "schemas/catalogue/v2/test-catalogue.schema.json",
    schema: CatalogueV2,
  },
  {
    name: "artifact/v1",
    id: "https://perfeng.dev/schemas/artifact/v1/artifact-reference.schema.json",
    output: "schemas/artifact/v1/artifact-reference.schema.json",
    schema: ArtifactV1,
  },
  {
    name: "raw-result/v1",
    id: "https://perfeng.dev/schemas/raw-result/v1/raw-result.schema.json",
    output: "schemas/raw-result/v1/raw-result.schema.json",
    schema: RawResultV1,
  },
  {
    name: "raw-result/v2",
    id: "https://perfeng.dev/schemas/raw-result/v2/raw-result.schema.json",
    output: "schemas/raw-result/v2/raw-result.schema.json",
    schema: RawResultV2,
  },
  {
    name: "normalized-result/v1",
    id: "https://perfeng.dev/schemas/normalized-result/v1/normalized-result.schema.json",
    output: "schemas/normalized-result/v1/normalized-result.schema.json",
    schema: NormalizedResultV1,
  },
  {
    name: "playwright-measurements/v1",
    id: "https://perfeng.dev/schemas/playwright-measurements/v1/playwright-measurements.schema.json",
    output: "schemas/playwright-measurements/v1/playwright-measurements.schema.json",
    schema: PlaywrightMeasurementsV1,
  },
  {
    name: "playwright-measurements/v2",
    id: "https://perfeng.dev/schemas/playwright-measurements/v2/playwright-measurements.schema.json",
    output: "schemas/playwright-measurements/v2/playwright-measurements.schema.json",
    schema: PlaywrightMeasurementsV2,
  },
  {
    name: "browser-environment/v1",
    id: "https://perfeng.dev/schemas/browser-environment/v1/browser-environment.schema.json",
    output: "schemas/browser-environment/v1/browser-environment.schema.json",
    schema: BrowserEnvironmentV1,
  },
  {
    name: "browser-diagnostics/v1",
    id: "https://perfeng.dev/schemas/browser-diagnostics/v1/browser-diagnostics.schema.json",
    output: "schemas/browser-diagnostics/v1/browser-diagnostics.schema.json",
    schema: BrowserDiagnosticsV1,
  },
  {
    name: "policy/v1",
    id: "https://perfeng.dev/schemas/policy/v1/performance-policy.schema.json",
    output: "schemas/policy/v1/performance-policy.schema.json",
    schema: PolicyV1,
  },
  {
    name: "analysis/v1",
    id: "https://perfeng.dev/schemas/analysis/v1/analysis-result.schema.json",
    output: "schemas/analysis/v1/analysis-result.schema.json",
    schema: AnalysisV1,
  },
  {
    name: "baseline/v1",
    id: "https://perfeng.dev/schemas/baseline/v1/baseline.schema.json",
    output: "schemas/baseline/v1/baseline.schema.json",
    schema: BaselineV1,
  },
];
