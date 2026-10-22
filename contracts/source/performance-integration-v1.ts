import { Schema } from "effect";

import { NonNegativeInteger, StrictTimestamp, Uri } from "./common.js";

const Text = Schema.String.pipe(Schema.minLength(1), Schema.maxLength(256), Schema.pattern(/\S/));
const Digest = Schema.String.pipe(Schema.pattern(/^[0-9a-f]{64}$/));
export const ScopedIdentity = Schema.Struct({
  issuer: Uri.pipe(Schema.maxLength(512)),
  id: Text,
}).annotations({ identifier: "IntegrationIdentity" });
export const ImmutableReference = Schema.Struct({
  ...ScopedIdentity.fields,
  revision: Text,
  sha256: Digest,
}).annotations({ identifier: "IntegrationReference" });
export const RequestContext = Schema.Struct({
  request: ScopedIdentity,
  attempt: ScopedIdentity,
  principal: ScopedIdentity,
  requestedAt: StrictTimestamp,
  deadline: StrictTimestamp,
  service: ImmutableReference,
  capability: ImmutableReference,
  deployment: ImmutableReference,
  environment: ImmutableReference,
  workload: ImmutableReference,
  profile: ImmutableReference,
  policy: ImmutableReference,
  baseline: Schema.NullOr(ImmutableReference),
  evidence: Schema.Array(ImmutableReference).pipe(Schema.maxItems(32)),
  candidate: Schema.Struct({
    source: Schema.Union(
      Schema.Struct({
        algorithm: Schema.Literal("git-sha1"),
        digest: Schema.String.pipe(Schema.pattern(/^[0-9a-f]{40}$/)),
      }),
      Schema.Struct({ algorithm: Schema.Literal("git-sha256"), digest: Digest }),
    ),
    imageDigest: Schema.String.pipe(Schema.pattern(/^sha256:[0-9a-f]{64}$/)),
  }),
}).annotations({ identifier: "IntegrationRequestContext" });
export const IntegrationState = Schema.Literal(
  "ACCEPTED",
  "RUNNING",
  "CANCELLING",
  "COMPLETED",
  "FAILED",
  "CANCELLED",
);
export const IntegrationError = Schema.Struct({
  code: Schema.Literal(
    "invalid_request",
    "unauthenticated",
    "forbidden",
    "conflict",
    "unknown_request",
    "expired",
    "unsupported_version",
    "unsupported_revision",
    "unavailable_reference",
    "rate_limited",
    "unavailable",
  ),
  message: Text,
}).annotations({ identifier: "IntegrationError" });
const envelope = {
  specversion: Schema.Literal("1.0"),
  id: Text,
  source: Uri.pipe(Schema.maxLength(512)),
  time: StrictTimestamp,
  datacontenttype: Schema.Literal("application/json"),
  dataschema: Schema.Literal(
    "https://perfeng.dev/schemas/performance-integration/v1/performance-integration.schema.json",
  ),
};
function message<const Kind extends string, A, I>(kind: Kind, data: Schema.Schema<A, I>) {
  return Schema.Struct({
    ...envelope,
    type: Schema.Literal(`dev.perfeng.integration.${kind}.v1`),
    data,
  });
}
const context = { context: RequestContext };
export const IntegrationRequest = message("requested", Schema.Struct(context));
export const IntegrationAccepted = message(
  "accepted",
  Schema.Struct({ ...context, run: ScopedIdentity }),
);
export const IntegrationRejected = message(
  "rejected",
  Schema.Struct({ ...context, error: IntegrationError }),
);
const lifecycle = {
  ...context,
  run: ScopedIdentity,
  revision: NonNegativeInteger.pipe(Schema.lessThanOrEqualTo(Number.MAX_SAFE_INTEGER)),
};
export const IntegrationLifecycle = message(
  "lifecycle",
  Schema.Struct({ ...lifecycle, state: IntegrationState }),
);
const Cancelling = message(
  "lifecycle",
  Schema.Struct({ ...lifecycle, state: Schema.Literal("CANCELLING") }),
);
const Terminal = message(
  "lifecycle",
  Schema.Struct({ ...lifecycle, state: Schema.Literal("COMPLETED", "FAILED", "CANCELLED") }),
);
export const IntegrationCancellation = message(
  "cancel-requested",
  Schema.Struct({
    ...context,
    reason: Schema.Literal("user", "superseded", "deadline"),
  }),
);
export const PerformanceIntegrationV1 = Schema.Union(
  IntegrationRequest,
  IntegrationAccepted,
  IntegrationRejected,
  IntegrationLifecycle,
  IntegrationCancellation,
);

/** HTTP operations are candidate protocol contracts, not implemented endpoints. */
export const IntegrationMessages = {
  Request: IntegrationRequest,
  Accepted: IntegrationAccepted,
  Rejected: IntegrationRejected,
  Lifecycle: IntegrationLifecycle,
  Cancellation: IntegrationCancellation,
  Error: IntegrationError,
  Cancelling,
  Terminal,
};
