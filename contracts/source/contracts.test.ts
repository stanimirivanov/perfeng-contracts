import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { Schema } from "effect";

import { CandidateV1 } from "./candidate-v1.js";
import { EnvironmentV1 } from "./environment-v1.js";

const decodeCandidate = Schema.decodeUnknownSync(CandidateV1, { onExcessProperty: "error" });
const decodeEnvironment = Schema.decodeUnknownSync(EnvironmentV1, { onExcessProperty: "error" });

async function fixture(path: string): Promise<unknown> {
  return JSON.parse(await readFile(new URL(`../../${path}`, import.meta.url), "utf8"));
}

test("candidate/v1 accepts its fixture and rejects invalid identity or unknown fields", async () => {
  const candidate = await fixture("examples/metadata/candidate-example.json");
  decodeCandidate(candidate);

  assert.throws(() => decodeCandidate({ gitSha: "not-a-git-sha" }));
  assert.throws(() =>
    decodeCandidate({
      gitSha: "a".repeat(40),
      unexpected: true,
    }),
  );
});

test("environment/v1 accepts its fixture and enforces identity and nested bounds", async () => {
  const environment = await fixture("examples/metadata/environment-example.json");
  decodeEnvironment(environment);

  assert.throws(() => decodeEnvironment({ cluster: "local" }));
  assert.throws(() =>
    decodeEnvironment({
      cluster: "local",
      fingerprint: "a".repeat(64),
      kubernetes: { nodeCount: 0 },
    }),
  );
  decodeEnvironment({
    cluster: "local",
    fingerprint: "a".repeat(64),
    kubernetes: { nodeCount: 9_007_199_254_740_992 },
  });
});
