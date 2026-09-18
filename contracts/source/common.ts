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

const rfc3339DateTime =
  /^(\d{4})-(0[1-9]|1[0-2])-(\d{2})T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/;

function isLeapYear(year: number): boolean {
  return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}

function isRfc3339DateTime(value: string): boolean {
  const match = rfc3339DateTime.exec(value);
  if (match === null) {
    return false;
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (year === 0) {
    return false;
  }

  const daysInMonth = [31, isLeapYear(year) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return day >= 1 && day <= (daysInMonth[month - 1] ?? 0);
}

/** DateTimeString preserves the Draft 2020-12 date-time wire format at runtime. */
export const DateTimeString = Schema.String.pipe(
  Schema.filter(isRfc3339DateTime, {
    message: () => "Expected an RFC 3339 date-time",
    jsonSchema: { type: "string", format: "date-time" },
  }),
);

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
