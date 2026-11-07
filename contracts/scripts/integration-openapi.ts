import { JSONSchema, type Schema } from "effect";
import { PerformanceAnalysisV1 } from "../source/performance-analysis-v1.js";
import { IntegrationMessages } from "../source/performance-integration-v1.js";
import { analysisPaths } from "./integration-analysis-paths.js";
import { lifecyclePaths } from "./integration-lifecycle-paths.js";

export function integrationOpenAPI() {
  const messages: Readonly<Record<string, Schema.Schema.AnyNoContext>> = {
    ...IntegrationMessages,
    AnalysisPublication: PerformanceAnalysisV1,
  };
  const schemas = Object.fromEntries(
    Object.entries(messages).map(([name, schema]) => {
      const {
        $schema: _draft,
        $defs: definitions,
        ...body
      } = JSONSchema.make(schema, { target: "jsonSchema2020-12" });
      // Each component owns its definitions; relocate refs into that component.
      const component = JSON.parse(
        JSON.stringify({ ...body, $defs: definitions }).replaceAll(
          '"#/$defs/',
          `"#/components/schemas/${name}/$defs/`,
        ),
      );
      return [name, component];
    }),
  );
  const content = (name: string) => ({
    "application/json": { schema: { $ref: `#/components/schemas/${name}` } },
  });
  const response = (name: string) => ({ description: name, content: content(name) });
  const errors = Object.fromEntries(
    [400, 401, 403, 404, 409, 410, 415, 429, 503].map((code) => [
      String(code),
      {
        ...response("Error"),
        ...([429, 503].includes(code)
          ? {
              headers: {
                "Retry-After": {
                  schema: { type: "integer", minimum: 1 },
                  description:
                    "Seconds before retry; preserve request identity and immutable context.",
                },
              },
            }
          : {}),
      },
    ]),
  );
  const read = { ...errors, "200": response("Lifecycle") };
  const noStore = { required: true, schema: { type: "string", const: "no-store" } };
  const analysisCodes = {
    "400": "invalid_request",
    "401": "unauthenticated",
    "403": "forbidden",
    "404": "unknown_request",
    "429": "rate_limited",
    "503": "unavailable",
  } as const;
  const analysisErrors = Object.fromEntries(
    Object.entries(analysisCodes).map(([status, errorCode]) => {
      const code = Number(status);
      const base = errors[status];
      if (base === undefined) throw new Error(`Missing integration error response: ${code}`);
      return [
        String(code),
        {
          ...base,
          content: {
            "application/json": {
              schema: {
                allOf: [
                  { $ref: "#/components/schemas/Error" },
                  {
                    properties: {
                      code: { const: errorCode },
                      ...(code === 404 ? { message: { const: "Not Found" } } : {}),
                    },
                  },
                ],
              },
            },
          },
          description: code === 404 ? "Unknown, invisible or not yet published" : "Error",
          headers: {
            ...base.headers,
            "Cache-Control": noStore,
            ...([429, 503].includes(code)
              ? {
                  "Retry-After": {
                    required: true,
                    schema: { type: "integer", minimum: 1 },
                    description: "Seconds before retrying the same scoped read.",
                  },
                }
              : {}),
            ...(code === 401
              ? {
                  "WWW-Authenticate": {
                    required: true,
                    schema: { type: "string", const: "Bearer" },
                  },
                }
              : {}),
          },
        },
      ];
    }),
  );
  const parameters = [
    {
      name: "requestId",
      in: "path",
      required: true,
      schema: { type: "string", minLength: 1, maxLength: 256 },
    },
    {
      name: "issuer",
      in: "query",
      required: true,
      schema: { type: "string", format: "uri", maxLength: 512 },
    },
  ];
  return {
    openapi: "3.1.1",
    info: { title: "Performance integration", version: "1.1.0" },
    security: [{ bearerAuth: [] }],
    paths: {
      ...lifecyclePaths({ parameters, content, response, errors, read }),
      ...analysisPaths({
        parameters: parameters.map((parameter) =>
          parameter.name === "requestId"
            ? { ...parameter, schema: { ...parameter.schema, pattern: "\\S" } }
            : parameter,
        ),
        analysisErrors,
        response,
        noStore,
      }),
    },
    components: { securitySchemes: { bearerAuth: { type: "http", scheme: "bearer" } }, schemas },
  };
}
