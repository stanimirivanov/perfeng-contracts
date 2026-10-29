import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { Schema } from "effect";

import { PerformanceAnalysisV1 } from "./performance-analysis-v1.js";
import { PerformanceIntegrationV1 } from "./performance-integration-v1.js";

const decode = Schema.decodeUnknownSync(PerformanceAnalysisV1, { onExcessProperty: "error" });
test("analysis publication is a separate closed family with complete native pins", async () => {
  const fixture = JSON.parse(
    await readFile(
      new URL("../../examples/performance-analysis/published.json", import.meta.url),
      "utf8",
    ),
  );
  decode(fixture);
  assert.throws(() => Schema.decodeUnknownSync(PerformanceIntegrationV1)(fixture));
  for (const path of [
    ["id"],
    ["data", "context"],
    ["data", "run"],
    ["data", "native", "testId"],
    ["data", "native", "workload", "sha256"],
    ["data", "native", "policy", "version"],
    ["data", "native", "baseline", "identity"],
    ["data", "artifact", "sha256"],
  ]) {
    const changed = structuredClone(fixture);
    let parent = changed;
    for (const key of path.slice(0, -1)) parent = parent[key];
    delete parent[path.at(-1) as string];
    assert.throws(() => decode(changed), path.join("."));
  }
  for (const artifact of [
    { kind: "normalized" },
    { format: "analysis-result/v2" },
    { sizeBytes: 0 },
    { sizeBytes: 1_048_577 },
    { uri: "https://example.com/result?token=secret" },
    { credentials: "injected" },
    { mediaType: "text/plain" },
  ]) {
    assert.throws(() =>
      decode({
        ...fixture,
        data: {
          ...fixture.data,
          artifact: { ...fixture.data.artifact, ...artifact },
        },
      }),
    );
  }
  assert.throws(() => decode({ ...fixture, type: fixture.type.replace(".v1", ".v2") }));
  assert.throws(() => decode({ ...fixture, overallPass: true }));
  fixture.data.native.baseline = null;
  fixture.data.context.baseline = null;
  decode(fixture);
});
