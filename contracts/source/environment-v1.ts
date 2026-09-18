import { Schema } from "effect";

import { FeatureFlags, Integer } from "./common.js";

const PositiveInteger = Integer.pipe(Schema.greaterThanOrEqualTo(1));
const NonNegativeNumber = Schema.Number.pipe(Schema.greaterThanOrEqualTo(0));

const NodePool = Schema.Struct({
  name: Schema.optional(Schema.String),
  nodeModel: Schema.optional(Schema.String),
  cpuArchitecture: Schema.optional(Schema.Literal("amd64", "arm64")),
  cpuCount: Schema.optional(PositiveInteger),
  memoryGiB: Schema.optional(NonNegativeNumber),
});

const KubernetesEnvironment = Schema.Struct({
  version: Schema.optional(
    Schema.String.pipe(Schema.pattern(/^v?\d+\.\d+\.\d+$/)).annotations({
      description: "Kubernetes version",
    }),
  ),
  nodeCount: Schema.optional(PositiveInteger),
  nodePools: Schema.optional(Schema.Array(NodePool)),
});

const RuntimeEnvironment = Schema.Struct({
  containerRuntime: Schema.optional(Schema.String),
  cni: Schema.optional(Schema.String),
  storageClass: Schema.optional(Schema.String),
  kernel: Schema.optional(Schema.String),
});

const ApplicationEnvironment = Schema.Struct({
  configurationHash: Schema.optional(Schema.String),
  featureFlags: Schema.optional(FeatureFlags),
});

const Compatibility = Schema.Struct({
  status: Schema.optional(Schema.Literal("COMPATIBLE", "PARTIALLY_COMPATIBLE", "INCOMPATIBLE")),
  reasons: Schema.optional(Schema.Array(Schema.String)),
}).annotations({ description: "Compatibility evaluation" });

/** EnvironmentV1 describes the environment in which a performance test ran. */
export const EnvironmentV1 = Schema.Struct({
  cluster: Schema.String.pipe(Schema.minLength(1)).annotations({
    description: "Cluster identifier",
  }),
  fingerprint: Schema.String.pipe(Schema.pattern(/^[a-f0-9]{64}$/)).annotations({
    description: "SHA256 fingerprint of environment characteristics",
  }),
  kubernetes: Schema.optional(KubernetesEnvironment),
  runtime: Schema.optional(RuntimeEnvironment),
  application: Schema.optional(ApplicationEnvironment),
  compatibility: Schema.optional(Compatibility),
}).annotations({
  title: "Environment Specification",
  description: "Performance test environment specification",
});

export type EnvironmentV1 = typeof EnvironmentV1.Type;
