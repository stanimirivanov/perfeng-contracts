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
export const NonNegativeInteger = Integer.pipe(Schema.greaterThanOrEqualTo(0));
export const PositiveNumber = Schema.Number.pipe(Schema.greaterThan(0));
export const NonNegativeNumber = Schema.Number.pipe(Schema.greaterThanOrEqualTo(0));

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

export const StrictTimestamp = DateTimeString.pipe(
  Schema.pattern(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:[0-5]\d(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/),
).annotations({ identifier: "timestamp" });

export const NonBlankString = Schema.String.pipe(Schema.minLength(1), Schema.pattern(/\S/));

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(canonicalJson).join(",")}]`;
  }
  if (value !== null && typeof value === "object") {
    return `{${Object.entries(value)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, entry]) => `${JSON.stringify(key)}:${canonicalJson(entry)}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

export function uniqueArray<A, I, R>(item: Schema.Schema<A, I, R>) {
  return Schema.Array(item).pipe(
    Schema.filter(
      (items) => {
        const values = items.map(canonicalJson);
        return new Set(values).size === values.length;
      },
      {
        message: () => "Expected unique array items",
        jsonSchema: { uniqueItems: true },
      },
    ),
  );
}

export function nonEmptyUniqueArray<A, I, R>(item: Schema.Schema<A, I, R>) {
  return uniqueArray(item).pipe(Schema.minItems(1));
}

export function nonEmptyArray<A, I, R>(item: Schema.Schema<A, I, R>) {
  return Schema.Array(item).pipe(Schema.minItems(1));
}

function isUri(value: string): boolean {
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
}

export const Uri = Schema.String.pipe(
  Schema.filter(isUri, {
    message: () => "Expected an absolute URI",
    jsonSchema: { type: "string", format: "uri" },
  }),
);

export const Uuid = Schema.String.pipe(
  Schema.filter(
    (value) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value),
    {
      message: () => "Expected a UUID",
      jsonSchema: { type: "string", format: "uuid" },
    },
  ),
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
