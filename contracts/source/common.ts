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

export const PositiveInteger = Integer.pipe(Schema.greaterThanOrEqualTo(1));

export type JsonValue =
  | string
  | boolean
  | number
  | null
  | ReadonlyArray<JsonValue>
  | { readonly [key: string]: JsonValue };

/** JsonValue accepts exactly values representable by JSON. */
export const JsonValue: Schema.Schema<JsonValue> = Schema.suspend(() =>
  Schema.Union(
    JsonPrimitive,
    Schema.Array(JsonValue),
    Schema.Record({ key: Schema.String, value: JsonValue }),
  ),
).annotations({ identifier: "JsonValue" });
