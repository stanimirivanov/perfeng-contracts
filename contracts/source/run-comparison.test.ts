import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { Schema } from "effect";

import { ComparisonEvidence } from "./run-comparison.js";

const decode = Schema.decodeUnknownSync(ComparisonEvidence, { onExcessProperty: "error" });

test("comparison evidence retains closed canonical report/publication shapes and bounds", async () => {
  const { evidence } = JSON.parse(
    await readFile(
      new URL("../../api/run-management/v1/comparison-cases.json", import.meta.url),
      "utf8",
    ),
  );
  decode(evidence);
  decode({ ...evidence, publication: null });
  assert.throws(() => decode({ ...evidence, overallPass: true }));
  assert.throws(() => decode({ ...evidence, analysis: { ...evidence.analysis, blocking: true } }));
  assert.throws(() =>
    decode({ ...evidence, directions: Array(1001).fill(evidence.directions[0]) }),
  );
  assert.throws(() =>
    decode({ ...evidence, publication: { ...evidence.publication, credentials: "forged" } }),
  );
});
