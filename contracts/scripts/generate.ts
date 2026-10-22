import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { JSONSchema } from "effect";

import { GeneratedContracts } from "../source/registry.js";
import { integrationOpenAPI } from "./integration-openapi.js";

const repositoryRoot = fileURLToPath(new URL("../../", import.meta.url));
const check = process.argv.includes("--check");
const manifest = JSON.parse(
  await readFile(new URL("../../contracts.json", import.meta.url), "utf8"),
) as {
  readonly version: string;
  readonly contracts: ReadonlyArray<{ readonly name: string; readonly schema: string }>;
};
const packageDocument = JSON.parse(
  await readFile(new URL("../../package.json", import.meta.url), "utf8"),
) as { readonly version: string };
if (packageDocument.version !== manifest.version) {
  throw new Error("package.json and contracts.json versions differ");
}
const manifestContracts = new Map(manifest.contracts.map((entry) => [entry.name, entry.schema]));
const names = new Set<string>();
const outputs = new Set<string>();

for (const contract of GeneratedContracts) {
  if (names.has(contract.name) || outputs.has(contract.output)) {
    throw new Error(`Duplicate generated contract registry entry: ${contract.name}`);
  }
  names.add(contract.name);
  outputs.add(contract.output);
  if (manifestContracts.get(contract.name) !== contract.output) {
    throw new Error(`${contract.name} does not match its contracts.json schema path`);
  }

  const generated = JSONSchema.make(contract.schema, { target: "jsonSchema2020-12" });
  const { $schema: _draft, ...body } = generated;
  const document = {
    $schema: "https://json-schema.org/draft/2020-12/schema",
    $id: contract.id,
    ...body,
  };
  const expected = `${JSON.stringify(document, undefined, 2)}\n`;
  const output = new URL(contract.output.replaceAll("\\", "/"), new URL("../../", import.meta.url));

  if (check) {
    const actual = await readFile(output, "utf8");
    if (actual !== expected) {
      throw new Error(
        `${contract.name} JSON Schema is stale; run pnpm contracts:generate from ${repositoryRoot}`,
      );
    }
  } else {
    await writeFile(output, expected, "utf8");
  }
}

const apiOutput = new URL("../../api/performance-integration/v1/openapi.json", import.meta.url);
const apiExpected = `${JSON.stringify(integrationOpenAPI(), undefined, 2)}\n`;
if (check) {
  if ((await readFile(apiOutput, "utf8")) !== apiExpected) {
    throw new Error("Performance integration OpenAPI is stale; run pnpm contracts:generate");
  }
} else {
  await writeFile(apiOutput, apiExpected, "utf8");
}

console.log(
  check
    ? `Verified ${GeneratedContracts.length} generated contract schemas.`
    : `Generated ${GeneratedContracts.length} contract schemas from Effect Schema.`,
);
