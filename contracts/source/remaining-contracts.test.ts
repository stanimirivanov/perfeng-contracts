import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { Schema } from "effect";

import { AnalysisV1 } from "./analysis-v1.js";
import { BaselineV1 } from "./baseline-v1.js";
import { BrowserDiagnosticsV1 } from "./browser-diagnostics-v1.js";
import { BrowserEnvironmentV1 } from "./browser-environment-v1.js";
import { CatalogueV1 } from "./catalogue-v1.js";
import { PlaywrightMeasurementsV2 } from "./playwright-measurements-v2.js";
import { PolicyV1 } from "./policy-v1.js";
import { RawResultV1 } from "./raw-result-v1.js";
import { GeneratedContracts } from "./registry.js";
import { WorkloadV1 } from "./workload-v1.js";

const migratedInThisChange = new Map<string, string>([
  ["baseline/v1", "schemaVersion"],
  ["policy/v1", "apiVersion"],
  ["analysis/v1", "schemaVersion"],
  ["artifact/v1", "id"],
  ["raw-result/v1", "schemaVersion"],
  ["raw-result/v2", "schemaVersion"],
  ["playwright-measurements/v1", "schemaVersion"],
  ["playwright-measurements/v2", "schemaVersion"],
  ["browser-environment/v1", "schemaVersion"],
  ["browser-diagnostics/v1", "schemaVersion"],
  ["normalized-result/v1", "schemaVersion"],
  ["workload/v1", "schemaVersion"],
  ["catalogue/v1", "apiVersion"],
  ["catalogue/v2", "apiVersion"],
]);

interface ManifestContract {
  readonly name: string;
  readonly examples: ReadonlyArray<{ readonly path: string; readonly items?: boolean }>;
}

async function json(path: string): Promise<unknown> {
  return JSON.parse(await readFile(new URL(`../../${path}`, import.meta.url), "utf8"));
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function decoder(schema: Schema.Schema.AnyNoContext) {
  return Schema.decodeUnknownSync(schema, { onExcessProperty: "error" });
}

test("all remaining contract fixtures decode strictly through Effect Schema", async () => {
  const manifest = (await json("contracts.json")) as { readonly contracts: ManifestContract[] };
  const schemas = new Map(GeneratedContracts.map((contract) => [contract.name, contract.schema]));

  for (const contract of manifest.contracts) {
    const requiredField = migratedInThisChange.get(contract.name);
    if (requiredField === undefined) {
      continue;
    }
    const decode = decoder(schemas.get(contract.name) as Schema.Schema.AnyNoContext);
    for (const example of contract.examples) {
      const document = await json(example.path);
      if (example.items === true) {
        assert.ok(Array.isArray(document));
        for (const item of document) {
          decode(item);
        }
      } else {
        decode(document);
      }
    }

    const document = (await json(contract.examples[0]?.path as string)) as Record<string, unknown>;
    const missing = clone(document);
    delete missing[requiredField];
    assert.throws(() => decode(missing), `${contract.name} requires ${requiredField}`);
    assert.throws(
      () => decode({ ...document, unexpected: true }),
      `${contract.name} rejects excess properties`,
    );
  }
});

test("workload, catalogue and transport refinements execute at the Effect boundary", async () => {
  const workload = (await json("examples/workload/k6-smoke.json")) as Record<string, unknown>;
  (workload.phases as Record<string, unknown>).unit = "iterations";
  assert.throws(() => decoder(WorkloadV1)(workload));

  const catalogue = (await json("examples/catalogue/application-tests.json")) as Record<
    string,
    unknown
  >;
  const tests = catalogue.tests as unknown[];
  tests.push(clone(tests[0]));
  assert.throws(() => decoder(CatalogueV1)(catalogue));

  const raw = (await json("examples/raw-result/k6.json")) as Record<string, unknown>;
  const artifacts = raw.artifacts as Array<Record<string, unknown>>;
  artifacts[0] = { ...artifacts[0], kind: "normalized" };
  assert.throws(() => decoder(RawResultV1)(raw));
});

test("browser refinements enforce reuse, calibration and capture evidence", async () => {
  const measurements = (await json(
    "examples/playwright-measurements/search-windows-lightweight.json",
  )) as Record<string, unknown>;
  const scenario = measurements.scenario as Record<string, unknown>;
  scenario.cacheProfile = "cold";
  scenario.contextReuse = "per-run";
  assert.throws(() => decoder(PlaywrightMeasurementsV2)(measurements));

  const environment = (await json(
    "examples/browser-environment/windows-mainstream.json",
  )) as Record<string, unknown>;
  const calibration = environment.calibration as Record<string, unknown>;
  calibration.status = "ACCEPTED";
  calibration.reasons = ["unexpected reason"];
  assert.throws(() => decoder(BrowserEnvironmentV1)(environment));

  const diagnostics = (await json("examples/browser-diagnostics/search-trace.json")) as Record<
    string,
    unknown
  >;
  const capture = (diagnostics.captures as Array<Record<string, unknown>>)[0] as Record<
    string,
    unknown
  >;
  capture.status = "COMPLETE";
  capture.reasons = ["unexpected reason"];
  assert.throws(() => decoder(BrowserDiagnosticsV1)(diagnostics));
});

test("policy, analysis and baseline refinements require decisive evidence", async () => {
  const policy = (await json("examples/policy/browser.json")) as Record<string, unknown>;
  const rule = (
    (policy.spec as Record<string, unknown>).rules as Array<Record<string, unknown>>
  )[0] as Record<string, unknown>;
  delete rule.slo;
  delete rule.regression;
  assert.throws(() => decoder(PolicyV1)(policy));

  const analysis = (await json("examples/analysis/slo-pass-regression-fail.json")) as Record<
    string,
    unknown
  >;
  const evaluation = (analysis.evaluations as Array<Record<string, unknown>>)[0] as Record<
    string,
    unknown
  >;
  const slo = evaluation.slo as Record<string, unknown>;
  slo.status = "PASS";
  delete slo.value;
  assert.throws(() => decoder(AnalysisV1)(analysis));

  const baseline = (await json("examples/baseline/approved.json")) as Record<string, unknown>;
  const qualification = baseline.qualification as Record<string, unknown>;
  qualification.status = "PASSED";
  delete qualification.sampleCount;
  assert.throws(() => decoder(BaselineV1)(baseline));
});
