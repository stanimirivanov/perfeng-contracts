import { Schema } from "effect";

import {
  CatalogueMetadata,
  CatalogueSourceV1,
  catalogueTestFields,
  OciImage,
} from "./catalogue-common.js";
import { nonEmptyUniqueArray } from "./common.js";

const CatalogueTestV1 = Schema.Struct({
  ...catalogueTestFields,
  source: CatalogueSourceV1,
  artifact: Schema.Struct({ image: OciImage }),
});

/** CatalogueV1 publishes versioned performance tests and pinned OCI runners. */
export const CatalogueV1 = Schema.Struct({
  apiVersion: Schema.Literal("performance.perfeng.io/v1"),
  kind: Schema.Literal("TestCatalogue"),
  metadata: CatalogueMetadata,
  tests: nonEmptyUniqueArray(CatalogueTestV1),
}).annotations({ title: "Versioned performance test catalogue" });

export type CatalogueV1 = typeof CatalogueV1.Type;
