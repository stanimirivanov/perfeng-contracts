import { Schema } from "effect";

import { Integer, Uri, Uuid } from "./common.js";
import { ResultRunId } from "./result-common.js";
import { Sha256 } from "./workload-v1.js";

export const ArtifactUri = Uri.pipe(Schema.pattern(/^(s3|https):\/\/[^\s?#]+$/));
export const ArtifactMediaType = Schema.String.pipe(
  Schema.pattern(/^[a-z0-9][a-z0-9!#$&^_.+-]*\/[a-z0-9][a-z0-9!#$&^_.+-]*$/),
);
export const ArtifactFormat = Schema.String.pipe(
  Schema.minLength(1),
  Schema.pattern(/^[a-z0-9][a-z0-9./_-]*$/),
);

export function artifactReference(kind: "raw" | "normalized" | Schema.Schema.AnyNoContext) {
  const kindSchema = typeof kind === "string" ? Schema.Literal(kind) : kind;
  return Schema.Struct({
    id: Uuid,
    runId: ResultRunId,
    kind: kindSchema,
    uri: ArtifactUri,
    sha256: Sha256,
    sizeBytes: Integer.pipe(Schema.greaterThanOrEqualTo(0)),
    mediaType: ArtifactMediaType,
    format: ArtifactFormat,
  });
}

/** ArtifactV1 identifies immutable raw or normalized evidence. */
export const ArtifactV1 = artifactReference(Schema.Literal("raw", "normalized")).annotations({
  title: "Immutable artifact reference",
});

export type ArtifactV1 = typeof ArtifactV1.Type;
