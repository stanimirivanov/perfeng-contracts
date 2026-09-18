import { Schema } from "effect";

import { artifactReference } from "./artifact-v1.js";
import { ExecutionArtifactV2, OciImage } from "./catalogue-common.js";
import { StrictTimestamp } from "./common.js";
import { SemanticVersion, Sha256, WorkloadId } from "./workload-v1.js";

export const WorkloadIdentity = Schema.Struct({
  id: WorkloadId,
  version: SemanticVersion,
  sha256: Sha256,
});

export const ProducerV1 = Schema.Struct({
  name: WorkloadId,
  version: SemanticVersion,
  image: OciImage,
});

export const ProducerV2 = Schema.Struct({
  name: WorkloadId,
  version: SemanticVersion,
  artifact: ExecutionArtifactV2,
});

export const MeasurementWindow = Schema.Struct({
  start: StrictTimestamp,
  end: StrictTimestamp,
});

export const RawArtifactReference = artifactReference("raw");
export const NormalizedArtifactReference = artifactReference("normalized");
