import { Schema } from "effect";

import {
  CatalogueMetadata,
  CatalogueSourceV2,
  catalogueTestFields,
  ExecutionArtifactV2,
} from "./catalogue-common.js";
import { nonEmptyUniqueArray } from "./common.js";
import { SemanticVersion } from "./workload-v1.js";

const CatalogueTestV2 = Schema.Struct({
  ...catalogueTestFields,
  tool: Schema.Struct({
    name: Schema.Literal("k6", "playwright", "kube-burner"),
    version: SemanticVersion,
  }),
  source: CatalogueSourceV2,
  artifact: ExecutionArtifactV2,
}).pipe(
  Schema.filter(
    (value) => value.tool.name !== "kube-burner" || value.artifact.kind !== "source-checkout",
    {
      message: () => "Kube-burner requires an OCI image or a verified release archive",
      jsonSchema: {
        allOf: [
          {
            if: { properties: { tool: { properties: { name: { const: "kube-burner" } } } } },
            then: {
              properties: {
                artifact: { properties: { kind: { enum: ["oci-image", "release-archive"] } } },
              },
            },
          },
        ],
      },
    },
  ),
);

/** CatalogueV2 adds native and release-archive execution provenance. */
export const CatalogueV2 = Schema.Struct({
  apiVersion: Schema.Literal("performance.perfeng.io/v2"),
  kind: Schema.Literal("TestCatalogue"),
  metadata: CatalogueMetadata,
  tests: nonEmptyUniqueArray(CatalogueTestV2),
}).annotations({ title: "Versioned performance test catalogue with execution provenance" });

export type CatalogueV2 = typeof CatalogueV2.Type;
