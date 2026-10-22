import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { Schema } from "effect";

import { PerformanceIntegrationV1 } from "./performance-integration-v1.js";

const decode = Schema.decodeUnknownSync(PerformanceIntegrationV1, { onExcessProperty: "error" });
async function fixture(name = "completed") {
  return JSON.parse(
    await readFile(
      new URL(`../../examples/performance-integration/${name}.json`, import.meta.url),
      "utf8",
    ),
  );
}
test("integration message families decode strictly without granting execution authority", async () => {
  for (const name of ["completed", "cancelled", "rejected"]) {
    for (const message of await fixture(name)) {
      decode(message);
      assert.throws(() => decode({ ...message, credential: "not-allowed" }));
      assert.throws(() => decode({ ...message, specversion: "2.0" }));
      assert.throws(() => decode({ ...message, type: message.type.replace(".v1", ".v2") }));
      assert.throws(() => decode({ ...message, dataschema: "https://example.com/other" }));
    }
  }
});
test("immutable selections require provenance and reject injected execution fields", async () => {
  const [request] = await fixture();
  for (const name of [
    "service",
    "capability",
    "deployment",
    "environment",
    "workload",
    "profile",
    "policy",
    "baseline",
  ]) {
    for (const field of ["issuer", "id", "revision", "sha256"]) {
      const changed = structuredClone(request);
      delete changed.data.context[name][field];
      assert.throws(() => decode(changed), `${name}.${field}`);
    }
  }
  for (const field of ["command", "targetUrl", "callbackUrl", "credentials"]) {
    const changed = structuredClone(request);
    changed.data.context[field] = "unreviewed";
    assert.throws(() => decode(changed));
  }
  request.data.context.baseline = null;
  decode(request);
  request.data.context.candidate.source = { algorithm: "git-sha256", digest: "d".repeat(64) };
  decode(request);
  request.data.context.candidate.imageDigest = "image:latest";
  assert.throws(() => decode(request));
});
