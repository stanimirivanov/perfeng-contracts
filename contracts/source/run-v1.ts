import { Schema } from "effect";

import { DateTimeString, FeatureFlags, Integer, PositiveInteger } from "./common.js";

function optionalNullable<A, I, R>(schema: Schema.Schema<A, I, R>, description?: string) {
  return Schema.optional(Schema.NullOr(schema)).annotations({
    default: null,
    ...(description === undefined ? {} : { description }),
  });
}

const RunIdentity = Schema.Struct({
  id: Schema.String.pipe(Schema.pattern(/^perf-[0-9]{8}-[0-9]{6}-[a-f0-9]{8}$/)).annotations({
    description: "Unique performance run identifier",
  }),
  suite: Schema.String.pipe(Schema.minLength(1)).annotations({
    description: "Test suite name (e.g., checkout-api, search-flow)",
  }),
  profile: Schema.Literal(
    "smoke",
    "average",
    "regression",
    "stress",
    "capacity",
    "soak",
  ).annotations({ description: "Workload profile used" }),
  timestamp: DateTimeString.annotations({
    jsonSchema: {
      type: "string",
      format: "date-time",
      description: "Run start timestamp in ISO 8601",
    },
  }),
  trigger: Schema.Literal("manual", "ci", "schedule", "bisect", "release").annotations({
    description: "What triggered this run",
  }),
  status: Schema.Literal(
    "CREATED",
    "VALIDATING",
    "PROVISIONING",
    "WARMING_UP",
    "RUNNING",
    "COLLECTING",
    "ANALYZING",
    "REPORTING",
    "COMPLETED",
    "INVALID",
    "ABORTED",
    "INFRASTRUCTURE_FAILURE",
    "TEST_FAILURE",
    "INCONCLUSIVE",
  ).annotations({ description: "Current run state" }),
  policyVersion: optionalNullable(Schema.String, "Version of the policy used for evaluation"),
  notes: optionalNullable(
    Schema.String.pipe(Schema.maxLength(1000)),
    "Optional notes about this run",
  ),
});

const TestIdentity = Schema.Struct({
  type: Schema.Literal("api", "browser", "kubernetes", "infrastructure").annotations({
    description: "Type of performance test",
  }),
  tool: Schema.Literal("k6", "playwright", "kube-burner", "benchmark-operator").annotations({
    description: "Tool used for testing",
  }),
  toolVersion: Schema.String.pipe(Schema.minLength(1)).annotations({
    description: "Version of the test tool",
  }),
  scenario: Schema.String.pipe(Schema.minLength(1)).annotations({
    description: "Specific scenario name",
  }),
  workloadVersion: optionalNullable(Schema.String, "Version of the workload definition"),
  configHash: optionalNullable(Schema.String, "Hash of the test configuration"),
});

const InlineCandidate = Schema.Struct({
  gitSha: Schema.String.pipe(Schema.pattern(/^[A-Fa-f0-9]{40}$/)).annotations({
    description: "Git commit SHA of the candidate",
  }),
  imageDigest: optionalNullable(Schema.String, "Container image digest"),
  version: optionalNullable(Schema.String, "Application version string"),
  branch: optionalNullable(Schema.String, "Git branch name"),
  configurationHash: optionalNullable(Schema.String, "Hash of application configuration"),
  featureFlags: optionalNullable(FeatureFlags, "Feature flag settings"),
  databaseMigrationVersion: optionalNullable(Schema.String, "Database migration version"),
});

const InlineEnvironment = Schema.Struct({
  cluster: Schema.String.pipe(Schema.minLength(1)).annotations({ description: "Cluster name" }),
  kubernetesVersion: Schema.String.pipe(Schema.pattern(/^v?\d+\.\d+\.\d+/)).annotations({
    description: "Kubernetes version",
  }),
  nodePool: optionalNullable(Schema.String, "Node pool identifier"),
  nodeModel: optionalNullable(Schema.String, "Node hardware model"),
  cpuArchitecture: optionalNullable(
    Schema.String.pipe(Schema.pattern(/^(amd64|arm64)$/)),
    "CPU architecture (e.g., amd64, arm64)",
  ),
  kernel: optionalNullable(Schema.String, "Kernel version"),
  containerRuntime: optionalNullable(Schema.String, "Container runtime (containerd, cri-o, etc.)"),
  cni: optionalNullable(Schema.String, "Container Network Interface"),
  storageClass: optionalNullable(Schema.String, "Storage class used"),
  fingerprint: optionalNullable(
    Schema.String.pipe(Schema.pattern(/^[a-f0-9]{64}$/)),
    "Canonical environment fingerprint",
  ),
  nodeCount: optionalNullable(PositiveInteger, "Number of nodes"),
  region: optionalNullable(Schema.String, "Geographic region"),
});

const HorizontalPodAutoscaler = Schema.Struct({
  enabled: optionalNullable(Schema.Boolean),
  minReplicas: optionalNullable(PositiveInteger),
  maxReplicas: optionalNullable(PositiveInteger),
  targetCpuUtilization: optionalNullable(Integer.pipe(Schema.between(1, 100))),
});

const RuntimeConfiguration = Schema.Struct({
  replicas: optionalNullable(PositiveInteger, "Number of replicas"),
  cpuRequests: optionalNullable(
    Schema.String.pipe(Schema.pattern(/^\d+(\.\d+)?m?$/)),
    "CPU requests (e.g., '500m')",
  ),
  cpuLimits: optionalNullable(Schema.String.pipe(Schema.pattern(/^\d+(\.\d+)?m?$/)), "CPU limits"),
  memoryRequests: optionalNullable(
    Schema.String.pipe(Schema.pattern(/^\d+(\.\d+)?(Ki|Mi|Gi|Ti|K|M|G|T)?$/)),
    "Memory requests (e.g., '512Mi')",
  ),
  memoryLimits: optionalNullable(
    Schema.String.pipe(Schema.pattern(/^\d+(\.\d+)?(Ki|Mi|Gi|Ti|K|M|G|T)?$/)),
    "Memory limits",
  ),
  hpa: optionalNullable(HorizontalPodAutoscaler, "Horizontal Pod Autoscaler configuration"),
});

const TestData = Schema.Struct({
  datasetId: optionalNullable(Schema.String, "Dataset identifier"),
  datasetVersion: optionalNullable(Schema.String, "Dataset version"),
  databaseSize: optionalNullable(
    Schema.String.pipe(Schema.pattern(/^\d+(\.\d+)?(KB|MB|GB|TB|KiB|MiB|GiB|TiB)$/)),
    "Database size (e.g., '10GB')",
  ),
  seedVersion: optionalNullable(Schema.String, "Data seed version"),
});

const RunPhases = Schema.Struct({
  provisionStart: optionalNullable(DateTimeString),
  warmupStart: optionalNullable(DateTimeString),
  measurementStart: optionalNullable(DateTimeString),
  measurementEnd: optionalNullable(DateTimeString),
  cooldownEnd: optionalNullable(DateTimeString),
});

/** RunV1 records execution identity, context, configuration and phase timing. */
export const RunV1 = Schema.Struct({
  run: RunIdentity,
  test: TestIdentity,
  candidate: InlineCandidate,
  environment: InlineEnvironment,
  runtime: optionalNullable(RuntimeConfiguration, "Runtime resource configuration"),
  data: optionalNullable(TestData, "Test data information"),
  phases: optionalNullable(RunPhases, "Timing information for different phases"),
}).annotations({
  title: "Performance Run Metadata",
  description: "Complete metadata for a single performance test run",
});

export type RunV1 = typeof RunV1.Type;
