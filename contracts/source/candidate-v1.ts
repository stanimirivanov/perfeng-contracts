import { Schema } from "effect";

import { FeatureFlags } from "./common.js";

const GitSha = Schema.String.pipe(Schema.pattern(/^[A-Fa-f0-9]{40}$/)).annotations({
  description: "Git commit SHA",
});

/** CandidateV1 identifies the software version under test. */
export const CandidateV1 = Schema.Struct({
  gitSha: GitSha,
  branch: Schema.optional(Schema.String.annotations({ description: "Git branch" })),
  imageDigest: Schema.optional(
    Schema.String.annotations({ description: "Container image digest" }),
  ),
  version: Schema.optional(Schema.String.annotations({ description: "Application version" })),
  configurationHash: Schema.optional(
    Schema.String.annotations({ description: "Configuration hash" }),
  ),
  featureFlags: Schema.optional(FeatureFlags),
  databaseMigrationVersion: Schema.optional(
    Schema.String.annotations({ description: "Database migration version" }),
  ),
  dependencies: Schema.optional(
    Schema.Record({ key: Schema.String, value: Schema.String }).annotations({
      description: "Dependency versions",
    }),
  ),
}).annotations({
  title: "Candidate Specification",
  description: "Candidate software version under test",
});

export type CandidateV1 = typeof CandidateV1.Type;
