import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { Schema } from "effect";

import { ResultV1 } from "./result-v1.js";
import { ResultV2 } from "./result-v2.js";

const decodeV1 = Schema.decodeUnknownSync(ResultV1, { onExcessProperty: "error" });
const decodeV2 = Schema.decodeUnknownSync(ResultV2, { onExcessProperty: "error" });

async function fixture(path: string): Promise<unknown> {
  return JSON.parse(await readFile(new URL(`../../${path}`, import.meta.url), "utf8"));
}

test("result/v1 accepts all fixtures and requires a positive sample count", async () => {
  decodeV1(await fixture("examples/metadata/test-result-example.json"));
  const normalized = await fixture("examples/metadata/normalized-result-example.json");
  assert.ok(Array.isArray(normalized));
  for (const result of normalized) {
    decodeV1(result);
  }

  const base = {
    schemaVersion: 1,
    runId: "perf-20260918-120000-a1b2c3d4",
    metric: { name: "api.duration", direction: "lower-is-better" },
  };
  assert.throws(() => decodeV1({ ...base, distribution: {} }));
  assert.throws(() => decodeV1({ ...base, distribution: { samples: null } }));
  assert.throws(() => decodeV1({ ...base, distribution: { samples: 0 } }));
  decodeV1({ ...base, distribution: { samples: 9_007_199_254_740_992 } });
});

test("result/v2 distinguishes unavailable, null, positive, and zero sample counts", async () => {
  decodeV2(await fixture("examples/result-v2/k6-unknown-count.json"));
  decodeV2(await fixture("examples/result-v2/playwright-known-count.json"));

  const base = {
    schemaVersion: 2,
    runId: "perf-20260918-130000-a1b2c3d5",
    metric: { name: "ui.duration", direction: "lower-is-better", type: null },
  };
  decodeV2({ ...base, distribution: {} });
  decodeV2({ ...base, distribution: { samples: null } });
  decodeV2({ ...base, distribution: { samples: 1 } });
  decodeV2({
    ...base,
    distribution: { samples: 1 },
    metadata: { nested: ["value", 1, true, null] },
  });
  assert.throws(() => decodeV2({ ...base, distribution: { samples: 0 } }));
  assert.throws(() => decodeV2({ ...base, distribution: { extra: true } }));
  assert.throws(() =>
    decodeV2({ ...base, distribution: { samples: 1 }, metadata: { invalid: undefined } }),
  );
});
