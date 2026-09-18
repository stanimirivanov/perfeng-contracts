import { Schema } from "effect";

import { playwrightEnvelopeFields, ScenarioV1 } from "./playwright-common.js";

/** PlaywrightMeasurementsV1 records semantic browser timings and runtime context. */
export const PlaywrightMeasurementsV1 = Schema.Struct({
  schemaVersion: Schema.Literal(1),
  ...playwrightEnvelopeFields,
  scenario: ScenarioV1,
}).annotations({ title: "Playwright semantic measurements" });

export type PlaywrightMeasurementsV1 = typeof PlaywrightMeasurementsV1.Type;
