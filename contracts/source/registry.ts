import type { Schema } from "effect";

import { CandidateV1 } from "./candidate-v1.js";
import { EnvironmentV1 } from "./environment-v1.js";
import { ResultV1 } from "./result-v1.js";
import { ResultV2 } from "./result-v2.js";
import { RunV1 } from "./run-v1.js";

export interface GeneratedContract {
  readonly name: string;
  readonly id: string;
  readonly output: string;
  readonly schema: Schema.Schema.Any;
}

/** Effect-authored contracts migrated during the staged source transition. */
export const GeneratedContracts: ReadonlyArray<GeneratedContract> = [
  {
    name: "candidate/v1",
    id: "https://perfeng.dev/schemas/candidate/v1/candidate.schema.json",
    output: "schemas/candidate/v1/candidate.schema.json",
    schema: CandidateV1,
  },
  {
    name: "environment/v1",
    id: "https://perfeng.dev/schemas/environment/v1/environment.schema.json",
    output: "schemas/environment/v1/environment.schema.json",
    schema: EnvironmentV1,
  },
  {
    name: "result/v1",
    id: "https://perfeng.dev/schemas/result/v1/test-result.schema.json",
    output: "schemas/result/v1/test-result.schema.json",
    schema: ResultV1,
  },
  {
    name: "result/v2",
    id: "https://perfeng.dev/schemas/result/v2/test-result.schema.json",
    output: "schemas/result/v2/test-result.schema.json",
    schema: ResultV2,
  },
  {
    name: "run/v1",
    id: "https://perfeng.dev/schemas/run/v1/run-metadata.schema.json",
    output: "schemas/run/v1/run-metadata.schema.json",
    schema: RunV1,
  },
];
