import { JSONSchema } from "effect";

import { ComparisonEvidence } from "../source/run-comparison.js";

/** Self-contained fragment; Redocly relocates its local definitions when bundling. */
export function comparisonComponent(): string {
  const { $schema: _draft, ...body } = JSONSchema.make(ComparisonEvidence, {
    target: "jsonSchema2020-12",
  });
  return `${JSON.stringify(body, undefined, 2)}\n`;
}
