import { Schema } from "effect";

export const JsonPrimitive = Schema.Union(
  Schema.String,
  Schema.Boolean,
  Schema.Number,
  Schema.Null,
);

export const FeatureFlags = Schema.Record({
  key: Schema.String,
  value: JsonPrimitive,
});

/** Integer preserves JSON Schema integer semantics without adding a safe-integer bound. */
export const Integer = Schema.Number.pipe(
  Schema.filter(Number.isInteger, {
    message: () => "Expected an integer",
    jsonSchema: { type: "integer" },
  }),
);
