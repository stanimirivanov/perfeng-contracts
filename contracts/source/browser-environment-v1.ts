import { Schema } from "effect";

import {
  NonNegativeInteger,
  PositiveInteger,
  PositiveNumber,
  StrictTimestamp,
  uniqueArray,
} from "./common.js";
import { EnvironmentIdentity } from "./playwright-common.js";
import { ResultRunId } from "./result-common.js";

const OperatingSystem = Schema.Struct({
  family: Schema.Literal("windows", "linux", "macos"),
  edition: Schema.String.pipe(Schema.minLength(1)),
  version: Schema.String.pipe(Schema.minLength(1)),
  build: Schema.String.pipe(Schema.minLength(1)),
  architecture: Schema.Literal("x64", "arm64"),
});

const Host = Schema.Struct({
  virtualization: Schema.Literal("physical", "virtual"),
  os: OperatingSystem,
  cpu: Schema.Struct({
    model: Schema.String.pipe(Schema.minLength(1)),
    logicalCores: PositiveInteger,
    physicalCores: Schema.optional(PositiveInteger),
    availableLogicalCores: PositiveNumber,
  }),
  memory: Schema.Struct({ totalBytes: PositiveInteger, availableBytes: NonNegativeInteger }),
  gpu: Schema.Struct({
    model: Schema.String.pipe(Schema.minLength(1)),
    driverVersion: Schema.String.pipe(Schema.minLength(1)),
    hardwareAcceleration: Schema.Boolean,
  }),
  display: Schema.Struct({
    width: PositiveInteger,
    height: PositiveInteger,
    scaleFactor: PositiveNumber,
    refreshRateHz: PositiveNumber,
  }),
  power: Schema.Struct({
    source: Schema.Literal("ac", "battery", "unknown"),
    plan: Schema.String.pipe(Schema.minLength(1)),
    batterySaver: Schema.Boolean,
  }),
});

const BrowserHost = Schema.Struct({
  name: Schema.Literal("chromium", "firefox", "webkit"),
  channel: Schema.String.pipe(Schema.minLength(1)),
  version: Schema.String.pipe(Schema.minLength(1)),
  headless: Schema.Boolean,
});

const calibrationRules = [
  {
    if: { properties: { status: { const: "ACCEPTED" } } },
    then: { properties: { reasons: { maxItems: 0 } } },
    else: { properties: { reasons: { minItems: 1 } } },
  },
] as const;

const Calibration = Schema.Struct({
  status: Schema.Literal("ACCEPTED", "REJECTED"),
  reasons: uniqueArray(Schema.String.pipe(Schema.minLength(1))),
  idleCpuPercent: Schema.Number.pipe(Schema.between(0, 100)),
  availableMemoryBytes: NonNegativeInteger,
  clockSynchronized: Schema.Boolean,
  softwareRendering: Schema.Boolean,
}).pipe(
  Schema.filter(
    (value) =>
      (value.status === "ACCEPTED" && value.reasons.length === 0) ||
      (value.status === "REJECTED" && value.reasons.length >= 1),
    {
      message: () => "Calibration status and reasons are inconsistent",
      jsonSchema: { allOf: calibrationRules },
    },
  ),
);

/** BrowserEnvironmentV1 captures host, browser and calibration evidence. */
export const BrowserEnvironmentV1 = Schema.Struct({
  schemaVersion: Schema.Literal(1),
  kind: Schema.Literal("BrowserEnvironment"),
  runId: ResultRunId,
  profile: EnvironmentIdentity.fields.profile,
  fingerprint: EnvironmentIdentity.fields.fingerprint,
  host: Host,
  browser: BrowserHost,
  calibration: Calibration,
  capturedAt: StrictTimestamp,
}).annotations({ title: "Browser execution environment" });

export type BrowserEnvironmentV1 = typeof BrowserEnvironmentV1.Type;
