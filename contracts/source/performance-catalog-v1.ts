import { Schema } from "effect";

import { NonNegativeInteger, PositiveInteger, StrictTimestamp } from "./common.js";
import { ImmutableReference, ScopedIdentity } from "./performance-integration-v1.js";
import { SemanticVersion, WorkloadProfile } from "./workload-v1.js";

const Text = Schema.String.pipe(Schema.minLength(1), Schema.maxLength(256), Schema.pattern(/\S/));
const Cursor = Schema.NullOr(Text);
const common = { reference: ImmutableReference, displayName: Text };
const active = { ...common, state: Schema.Literal("ACTIVE", "RETIRED") };
const references = Schema.Array(ImmutableReference).pipe(Schema.maxItems(32));
const Resource = Schema.Union(
  Schema.Struct({
    ...active,
    kind: Schema.Literal("workload"),
    ownerRoute: ImmutableReference,
    supportedProfiles: references,
  }),
  Schema.Struct({
    ...active,
    kind: Schema.Literal("profile"),
    purpose: WorkloadProfile,
    workload: ImmutableReference,
    selections: Schema.Array(
      Schema.Struct({
        environment: ImmutableReference,
        policy: ImmutableReference,
        baseline: Schema.NullOr(ImmutableReference),
      }),
    ).pipe(Schema.maxItems(32)),
  }),
  Schema.Struct({ ...active, kind: Schema.Literal("environment", "policy") }),
  Schema.Struct({
    ...active,
    kind: Schema.Literal("owner-route"),
    owner: ScopedIdentity,
    route: ScopedIdentity,
  }),
  Schema.Struct({
    ...common,
    kind: Schema.Literal("baseline"),
    state: Schema.Literal("CANDIDATE", "QUALIFIED", "APPROVED", "RETIRED"),
    workload: ImmutableReference,
    profile: ImmutableReference,
    environment: ImmutableReference,
    policy: ImmutableReference,
  }),
);

/** Authorized metadata only: no workload configuration or execution authority. */
export const PerformanceCatalogV1 = Schema.Struct({
  schemaVersion: Schema.Literal(1),
  kind: Schema.Literal("PerformanceCatalogPage"),
  snapshot: Schema.Struct({
    reference: ImmutableReference,
    principal: ScopedIdentity,
    producer: Schema.Struct({ identity: ScopedIdentity, version: SemanticVersion }),
    generatedAt: StrictTimestamp,
    validUntil: StrictTimestamp,
    complete: Schema.Literal(true),
    totalItems: NonNegativeInteger.pipe(Schema.lessThanOrEqualTo(100_000)),
    totalPages: PositiveInteger.pipe(Schema.lessThanOrEqualTo(1_000)),
  }),
  page: Schema.Struct({
    index: NonNegativeInteger.pipe(Schema.lessThan(1_000)),
    cursor: Cursor,
    nextCursor: Cursor,
  }),
  items: Schema.Array(Resource).pipe(Schema.maxItems(100)),
});
