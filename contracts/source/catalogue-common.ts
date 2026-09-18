import { Schema } from "effect";

import { NonBlankString, nonEmptyUniqueArray, Uri } from "./common.js";
import { ResultMetric } from "./result-common.js";
import {
  RelativePath,
  SemanticVersion,
  Sha256,
  WorkloadId,
  WorkloadProfile,
  WorkloadV1,
} from "./workload-v1.js";

export const OciImage = Schema.String.pipe(
  Schema.pattern(/^[a-z0-9][a-z0-9._:/-]*@sha256:[a-f0-9]{64}$/),
);

export const HttpsUri = Uri.pipe(Schema.pattern(/^https:\/\//));
export const ReleaseArchiveUri = Uri.pipe(Schema.pattern(/^https:\/\/[^\s@?#]+$/));

export const CatalogueMetadata = Schema.Struct({
  name: WorkloadId,
  version: SemanticVersion,
});

export const CatalogueTool = Schema.Struct({
  name: Schema.Literal("k6", "playwright"),
  version: SemanticVersion,
});

export const CatalogueSourceV1 = Schema.Struct({
  repository: HttpsUri,
  gitSha: Schema.String.pipe(Schema.pattern(/^[a-fA-F0-9]{40}$/)),
  entrypoint: RelativePath,
});

export const CatalogueSourceV2 = Schema.Struct({
  repository: HttpsUri,
  gitSha: Schema.String.pipe(Schema.pattern(/^[a-f0-9]{40}$/)),
  entrypoint: RelativePath,
});

const OciExecutionArtifact = Schema.Struct({
  kind: Schema.Literal("oci-image"),
  image: OciImage,
});

const SourceCheckoutArtifact = Schema.Struct({
  kind: Schema.Literal("source-checkout"),
  repository: HttpsUri,
  gitSha: Schema.String.pipe(Schema.pattern(/^[a-f0-9]{40}$/)),
  dependencyLock: Schema.Struct({ path: RelativePath, sha256: Sha256 }),
});

const ReleaseArchiveArtifact = Schema.Struct({
  kind: Schema.Literal("release-archive"),
  url: ReleaseArchiveUri,
  archiveSha256: Sha256,
  executableSha256: Sha256,
});

export const ExecutionArtifactV2 = Schema.Union(
  OciExecutionArtifact,
  SourceCheckoutArtifact,
  ReleaseArchiveArtifact,
).annotations({ identifier: "executionArtifact" });

const CatalogueProfile = WorkloadProfile.annotations({ identifier: "profile" });

export const CatalogueSchedule = Schema.Struct({
  pr: Schema.optional(CatalogueProfile),
  main: Schema.optional(CatalogueProfile),
  nightly: Schema.optional(CatalogueProfile),
  scheduled: Schema.optional(CatalogueProfile),
  release: Schema.optional(CatalogueProfile),
}).pipe(
  Schema.filter((value) => Object.keys(value).length >= 1, {
    message: () => "Expected at least one schedule trigger",
    jsonSchema: { minProperties: 1 },
  }),
);

export const catalogueTestFields = {
  id: WorkloadId,
  name: NonBlankString,
  owner: NonBlankString,
  criticality: Schema.Literal("low", "medium", "high", "critical"),
  description: Schema.optional(Schema.String),
  tool: CatalogueTool,
  workloads: nonEmptyUniqueArray(WorkloadV1),
  schedule: Schema.optional(CatalogueSchedule),
  metrics: Schema.optional(nonEmptyUniqueArray(ResultMetric)),
} as const;
