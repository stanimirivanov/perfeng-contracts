import { Schema } from "effect";

import {
  CatalogueMetadata,
  CatalogueSourceV2,
  catalogueTestFields,
  ExecutionArtifactV2,
} from "./catalogue-common.js";
import { nonEmptyUniqueArray } from "./common.js";

const CatalogueTestV2 = Schema.Struct({
  ...catalogueTestFields,
  source: CatalogueSourceV2,
  artifact: ExecutionArtifactV2,
});

/** CatalogueV2 adds native and release-archive execution provenance. */
export const CatalogueV2 = Schema.Struct({
  apiVersion: Schema.Literal("performance.perfeng.io/v2"),
  kind: Schema.Literal("TestCatalogue"),
  metadata: CatalogueMetadata,
  tests: nonEmptyUniqueArray(CatalogueTestV2),
}).annotations({ title: "Versioned performance test catalogue with execution provenance" });

export type CatalogueV2 = typeof CatalogueV2.Type;
