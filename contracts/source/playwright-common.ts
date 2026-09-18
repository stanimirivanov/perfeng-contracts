import { Schema } from "effect";

import {
  NonNegativeInteger,
  NonNegativeNumber,
  nonEmptyArray,
  PositiveInteger,
  PositiveNumber,
  StrictTimestamp,
} from "./common.js";
import { ResultMetric, ResultRunId } from "./result-common.js";
import { SemanticVersion, Sha256, WorkloadId, WorkloadProfile } from "./workload-v1.js";

export const BrowserWorkloadIdentity = Schema.Struct({
  id: WorkloadId,
  version: SemanticVersion,
  profile: WorkloadProfile,
  sha256: Sha256,
});

export const EnvironmentIdentity = Schema.Struct({
  profile: Schema.Struct({ id: WorkloadId, version: SemanticVersion }),
  fingerprint: Sha256,
});

const scenarioV1Rules = [
  {
    if: { properties: { cacheProfile: { const: "cold" } } },
    then: { properties: { contextReuse: { const: "per-iteration" } } },
  },
  {
    if: { properties: { cacheProfile: { const: "warm" } } },
    then: { properties: { contextReuse: { const: "per-run" } } },
  },
] as const;

export const ScenarioV1 = Schema.Struct({
  cacheProfile: Schema.Literal("cold", "warm"),
  contextReuse: Schema.Literal("per-iteration", "per-run"),
  warmupIterations: NonNegativeInteger,
  measurementIterations: PositiveInteger,
}).pipe(
  Schema.filter(
    (value) =>
      (value.cacheProfile === "cold" && value.contextReuse === "per-iteration") ||
      (value.cacheProfile === "warm" && value.contextReuse === "per-run"),
    {
      message: () => "Cache profile and context reuse are inconsistent",
      jsonSchema: { allOf: scenarioV1Rules },
    },
  ),
);

const scenarioV2Rules = [
  {
    if: { properties: { cacheProfile: { const: "cold" } } },
    then: {
      properties: {
        contextReuse: { const: "per-iteration" },
        pageReuse: { const: "per-iteration" },
      },
    },
  },
  {
    if: { properties: { cacheProfile: { const: "warm" } } },
    then: { properties: { contextReuse: { const: "per-run" } } },
  },
  {
    if: { properties: { pageReuse: { const: "per-run" } } },
    then: { properties: { contextReuse: { const: "per-run" } } },
  },
] as const;

export const ScenarioV2 = Schema.Struct({
  cacheProfile: Schema.Literal("cold", "warm"),
  contextReuse: Schema.Literal("per-iteration", "per-run"),
  pageReuse: Schema.Literal("per-iteration", "per-run"),
  warmupIterations: NonNegativeInteger,
  measurementIterations: PositiveInteger,
}).pipe(
  Schema.filter(
    (value) =>
      (value.cacheProfile !== "cold" ||
        (value.contextReuse === "per-iteration" && value.pageReuse === "per-iteration")) &&
      (value.cacheProfile !== "warm" || value.contextReuse === "per-run") &&
      (value.pageReuse !== "per-run" || value.contextReuse === "per-run"),
    {
      message: () => "Cache, context and page reuse are inconsistent",
      jsonSchema: { allOf: scenarioV2Rules },
    },
  ),
);

export const PlaywrightRuntime = Schema.Struct({
  playwrightVersion: SemanticVersion,
  nodeVersion: SemanticVersion,
  platform: Schema.Literal("linux", "darwin", "win32"),
  architecture: Schema.Literal("x64", "arm64"),
});

export const Browser = Schema.Struct({
  name: Schema.Literal("chromium", "firefox", "webkit"),
  version: Schema.String.pipe(Schema.pattern(/^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$/)),
  headless: Schema.Boolean,
  viewport: Schema.Struct({ width: PositiveInteger, height: PositiveInteger }),
  deviceScaleFactor: PositiveNumber,
});

export const BrowserMeasurementWindow = Schema.Struct({
  start: StrictTimestamp,
  end: StrictTimestamp,
});

const Measurement = Schema.Struct({
  iteration: PositiveInteger,
  name: ResultMetric.fields.name,
  durationMs: NonNegativeNumber,
});

export const BrowserMeasurements = nonEmptyArray(Measurement);

export const playwrightEnvelopeFields = {
  kind: Schema.Literal("PlaywrightMeasurements"),
  runId: ResultRunId,
  testId: WorkloadId,
  workload: BrowserWorkloadIdentity,
  runtime: PlaywrightRuntime,
  browser: Browser,
  measurementWindow: BrowserMeasurementWindow,
  createdAt: StrictTimestamp,
  measurements: BrowserMeasurements,
} as const;
