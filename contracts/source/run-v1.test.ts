import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { Schema } from "effect";

import { RunV1 } from "./run-v1.js";

const decode = Schema.decodeUnknownSync(RunV1, { onExcessProperty: "error" });

async function fixture(): Promise<Record<string, unknown>> {
  return JSON.parse(
    await readFile(
      new URL("../../examples/metadata/run-metadata-example.json", import.meta.url),
      "utf8",
    ),
  ) as Record<string, unknown>;
}

test("run/v1 accepts its fixture and nullable optional sections", async () => {
  decode(await fixture());

  const minimal = await fixture();
  delete minimal.runtime;
  minimal.data = null;
  minimal.phases = null;
  decode(minimal);
});

test("run/v1 enforces identities, enumerations, timestamps and bounds", async () => {
  const cases: ReadonlyArray<readonly [readonly string[], unknown]> = [
    [["run", "id"], "run-1"],
    [["run", "profile"], "unknown"],
    [["run", "status"], "REGRESSION"],
    [["run", "timestamp"], "2026-02-30T12:00:00Z"],
    [["candidate", "gitSha"], "a".repeat(38)],
    [["environment", "fingerprint"], "a".repeat(60)],
    [["environment", "nodeCount"], 0],
    [["runtime", "replicas"], 0],
    [["runtime", "hpa", "targetCpuUtilization"], 101],
    [["data", "databaseSize"], "10 gigabytes"],
    [["phases", "measurementEnd"], "not-a-date"],
  ];

  for (const [path, value] of cases) {
    const input = await fixture();
    let target: Record<string, unknown> = input;
    for (const segment of path.slice(0, -1)) {
      target = target[segment] as Record<string, unknown>;
    }
    target[path.at(-1) as string] = value;
    assert.throws(() => decode(input), path.join("."));
  }
});

test("run/v1 closes every object while preserving legacy inline shapes", async () => {
  const input = await fixture();
  (input.candidate as Record<string, unknown>).unexpected = true;
  assert.throws(() => decode(input));

  const legacy = await fixture();
  (legacy.environment as Record<string, unknown>).kubernetesVersion = "v1.28.0-provider";
  (legacy.environment as Record<string, unknown>).nodeCount = 9_007_199_254_740_992;
  decode(legacy);
});
