import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { Schema } from "effect";

import { CatalogueV1 } from "./catalogue-v1.js";
import { CatalogueV2 } from "./catalogue-v2.js";
import { KubernetesBenchmarkEvidenceV1 } from "./kubernetes-benchmark-evidence-v1.js";

async function example(path: string) {
  return JSON.parse(
    await readFile(new URL(`../../examples/${path}.json`, import.meta.url), "utf8"),
  );
}

const decode = Schema.decodeUnknownSync(KubernetesBenchmarkEvidenceV1, {
  onExcessProperty: "error",
});

test("Kubernetes evidence decodes accepted, unknown and rejected scopes strictly", async () => {
  for (const name of ["accepted-preflight", "unknown-preflight", "measurement"]) {
    const value = await example(`kubernetes-benchmark-evidence/${name}`);
    decode(value);
    assert.throws(() => decode({ ...value, unauthorized: true }));
    delete value.profile.sha256;
    assert.throws(() => decode(value));
  }
});

test("all checks occur exactly once and the summary cannot conceal UNKNOWN or FAIL", async () => {
  const value = await example("kubernetes-benchmark-evidence/accepted-preflight");
  value.checks[1].id = "cluster-identity";
  assert.throws(() => decode(value));
  value.checks[1].id = "node-readiness";
  value.checks[1].status = "UNKNOWN";
  assert.throws(() => decode(value));
  value.status = "UNKNOWN";
  decode(value);
  value.checks[0].status = "FAIL";
  assert.throws(() => decode(value));
  value.status = "REJECTED";
  decode(value);
});

test("preflight and measurement identities cannot be mixed", async () => {
  const value = await example("kubernetes-benchmark-evidence/accepted-preflight");
  value.scope.runId = "perf-20261013-120000-a1b2c3d4";
  assert.throws(() => decode(value));
  value.scope = { kind: "measurement", runId: value.scope.runId };
  assert.throws(() => decode(value));
});

test("missing metrics are explicit unavailable evidence, not null or inferred zero", async () => {
  const value = await example("kubernetes-benchmark-evidence/measurement");
  value.samples[0].usage.cpuMilliCores = 0;
  assert.throws(() => decode(value));
  delete value.samples[0].usage.cpuMilliCores;
  decode(value);
  value.samples[0].usage = { source: "metrics-api", cpuMilliCores: null, memoryBytes: 0 };
  assert.throws(() => decode(value));
});

test("Kubernetes catalogue admission is v2-only with explicit OCI or archive provenance", async () => {
  const value = await example("catalogue/kubernetes-tests-v2");
  const decodeV2 = Schema.decodeUnknownSync(CatalogueV2, { onExcessProperty: "error" });
  decodeV2(value);
  const legacy = structuredClone(value);
  legacy.apiVersion = "performance.perfeng.io/v1";
  legacy.tests[0].artifact = { image: value.tests[0].artifact.image };
  assert.throws(() => Schema.decodeUnknownSync(CatalogueV1, { onExcessProperty: "error" })(legacy));
  value.tests[0].artifact = {
    kind: "release-archive",
    url: "https://example.com/kube-burner.zip",
    archiveSha256: "a".repeat(64),
    executableSha256: "b".repeat(64),
  };
  decodeV2(value);
  value.tests[0].artifact = {
    kind: "source-checkout",
    ...value.tests[0].source,
    dependencyLock: { path: "go.sum", sha256: "a".repeat(64) },
  };
  delete value.tests[0].artifact.entrypoint;
  assert.throws(() => decodeV2(value));
});
