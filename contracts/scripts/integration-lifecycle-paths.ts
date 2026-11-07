interface LifecycleContext {
  parameters: unknown[];
  content: (name: string) => Record<string, unknown>;
  response: (name: string) => Record<string, unknown>;
  errors: Record<string, unknown>;
  read: Record<string, unknown>;
}

export function lifecyclePaths({ parameters, content, response, errors, read }: LifecycleContext) {
  return {
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
  };
}
