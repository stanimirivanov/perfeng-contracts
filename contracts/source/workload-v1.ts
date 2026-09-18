import { Schema } from "effect";

import { NonNegativeInteger, PositiveInteger } from "./common.js";

export const WorkloadId = Schema.String.pipe(
  Schema.pattern(/^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/),
).annotations({ identifier: "id" });

export const SemanticVersion = Schema.String.pipe(
  Schema.pattern(/^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/),
).annotations({ identifier: "version" });

export const Sha256 = Schema.String.pipe(Schema.pattern(/^[a-f0-9]{64}$/)).annotations({
  identifier: "sha256",
});

export const RelativePath = Schema.String.pipe(
  Schema.pattern(/^(?!\/)(?!.*(?:^|\/)\.{1,2}(?:\/|$))[A-Za-z0-9_./-]+$/),
).annotations({ identifier: "relativePath" });

export const WorkloadProfile = Schema.Literal(
  "smoke",
  "average",
  "regression",
  "stress",
  "capacity",
  "soak",
);

const Configuration = Schema.Struct({ path: RelativePath, sha256: Sha256 });

const Phases = Schema.Struct({
  unit: Schema.Literal("seconds", "iterations"),
  warmup: NonNegativeInteger,
  measurement: PositiveInteger,
  cooldown: NonNegativeInteger,
});

const NoDataset = Schema.Struct({ kind: Schema.Literal("none") });
const VersionedDataset = Schema.Struct({
  kind: Schema.Literal("versioned"),
  id: WorkloadId,
  version: SemanticVersion,
  sha256: Sha256,
  seed: NonNegativeInteger,
});
export const Dataset = Schema.Union(NoDataset, VersionedDataset);

const WorkloadShape = Schema.Struct({
  schemaVersion: Schema.Literal(1),
  id: WorkloadId,
  version: SemanticVersion,
  tool: Schema.Literal("k6", "playwright", "kube-burner"),
  profile: WorkloadProfile,
  model: Schema.Literal("open", "closed"),
  configuration: Configuration,
  phases: Phases,
  dataset: Dataset,
});

const workloadRules = [
  {
    if: { properties: { tool: { const: "k6" } } },
    then: { properties: { phases: { properties: { unit: { const: "seconds" } } } } },
  },
  {
    if: { properties: { tool: { const: "playwright" } } },
    then: {
      properties: {
        model: { const: "closed" },
        phases: { properties: { unit: { const: "iterations" } } },
      },
    },
  },
  {
    if: { properties: { tool: { const: "kube-burner" } } },
    then: {
      properties: {
        model: { const: "open" },
        phases: { properties: { unit: { const: "iterations" } } },
      },
    },
  },
] as const;

/** WorkloadV1 defines a versioned, immutable performance workload. */
export const WorkloadV1 = WorkloadShape.pipe(
  Schema.filter(
    (value) =>
      (value.tool !== "k6" || value.phases.unit === "seconds") &&
      (value.tool !== "playwright" ||
        (value.model === "closed" && value.phases.unit === "iterations")) &&
      (value.tool !== "kube-burner" ||
        (value.model === "open" && value.phases.unit === "iterations")),
    {
      message: () => "Workload tool, model and phase unit are inconsistent",
      jsonSchema: { allOf: workloadRules },
    },
  ),
).annotations({ title: "Versioned workload definition" });

export type WorkloadV1 = typeof WorkloadV1.Type;
