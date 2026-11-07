interface AnalysisContext {
  parameters: unknown[];
  analysisErrors: Record<string, unknown>;
  response: (name: string) => Record<string, unknown>;
  noStore: Record<string, unknown>;
}

export function analysisPaths({ parameters, analysisErrors, response, noStore }: AnalysisContext) {
  return {
    "/integration/v1/requests/{requestId}/analysis": {
      parameters,
      get: {
        operationId: "getPerformanceAnalysis",
        description:
          "Requires authenticated principal and existing request-read permission. Returns retained immutable analysis; never materializes, executes or fetches artifact bytes. Request identity is scoped by issuer and principal, never by native Run ID.",
        responses: {
          ...analysisErrors,
          "200": { ...response("AnalysisPublication"), headers: { "Cache-Control": noStore } },
        },
      },
    },
  };
}
