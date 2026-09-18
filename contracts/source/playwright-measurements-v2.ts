import { Schema } from "effect";

import { EnvironmentIdentity, playwrightEnvelopeFields, ScenarioV2 } from "./playwright-common.js";

/** PlaywrightMeasurementsV2 adds page reuse, diagnostics and environment identity. */
export const PlaywrightMeasurementsV2 = Schema.Struct({
  schemaVersion: Schema.Literal(2),
  ...playwrightEnvelopeFields,
  scenario: ScenarioV2,
  diagnosticMode: Schema.Literal("baseline", "lightweight", "trace", "memory", "smoothness"),
  environment: EnvironmentIdentity,
}).annotations({ title: "Playwright semantic measurements with execution context" });

export type PlaywrightMeasurementsV2 = typeof PlaywrightMeasurementsV2.Type;
