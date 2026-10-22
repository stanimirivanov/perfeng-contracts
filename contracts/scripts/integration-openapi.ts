import { JSONSchema, type Schema } from "effect";

import { IntegrationMessages } from "../source/performance-integration-v1.js";

export function integrationOpenAPI() {
  const messages: Readonly<Record<string, Schema.Schema.AnyNoContext>> = IntegrationMessages;
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
    info: { title: "Performance integration", version: "1.0.0" },
    security: [{ bearerAuth: [] }],
    paths: {
      "/integration/v1/requests": {
        post: {
          operationId: "requestPerformanceRun",
          requestBody: { required: true, content: content("Request") },
          responses: { ...errors, "202": response("Accepted"), "422": response("Rejected") },
        },
      },
      "/integration/v1/requests/{requestId}": {
        parameters,
        get: {
          operationId: "getPerformanceRequest",
          responses: { ...read, "422": response("Rejected") },
        },
      },
      "/integration/v1/requests/{requestId}/cancellation": {
        parameters,
        post: {
          operationId: "cancelPerformanceRequest",
          requestBody: { required: true, content: content("Cancellation") },
          responses: { ...errors, "200": response("Terminal"), "202": response("Cancelling") },
        },
      },
    },
    components: { securitySchemes: { bearerAuth: { type: "http", scheme: "bearer" } }, schemas },
  };
}
