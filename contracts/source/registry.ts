import type { Schema } from "effect";

import { CandidateV1 } from "./candidate-v1.js";
import { EnvironmentV1 } from "./environment-v1.js";

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
];
