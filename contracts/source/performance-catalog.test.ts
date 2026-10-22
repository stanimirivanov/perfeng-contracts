import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { Schema } from "effect";

import { PerformanceCatalogV1 } from "./performance-catalog-v1.js";

const decode = Schema.decodeUnknownSync(PerformanceCatalogV1, { onExcessProperty: "error" });
test("catalog pages decode strictly, including empty and retired resources", async () => {
  for (const name of ["pages", "empty"]) {
    const pages = JSON.parse(
      await readFile(
        new URL(`../../examples/performance-catalog/${name}.json`, import.meta.url),
        "utf8",
      ),
    );
    for (const page of pages) {
      decode(page);
      assert.throws(() => decode({ ...page, schemaVersion: 2 }));
      assert.throws(() => decode({ ...page, credential: "forbidden" }));
      assert.throws(() => decode({ ...page, snapshot: { ...page.snapshot, complete: false } }));
      for (const [index, item] of page.items.entries()) {
        for (const field of ["issuer", "id", "revision", "sha256"]) {
          const invalid = structuredClone(page);
          delete invalid.items[index].reference[field];
          assert.throws(() => decode(invalid));
        }
        for (const field of ["command", "configuration", "credentials", "targetUrl"]) {
          assert.throws(() => decode({ ...page, items: [{ ...item, [field]: "forbidden" }] }));
        }
      }
    }
  }
});
