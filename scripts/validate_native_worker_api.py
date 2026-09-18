"""Offline Native Worker OpenAPI and conformance validation."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from openapi_spec_validator import OpenAPIV31SpecValidator

if __package__:
    from .validate import ROOT, read_json
    from .validate_api import check_local_references, parse_request, schema_validator
else:
    from validate import ROOT, read_json
    from validate_api import check_local_references, parse_request, schema_validator

API_PATH = "api/native-worker/v1"
STANDARD_ERRORS = {"400", "401", "403", "429", "500", "503"}
LEASE_OPERATIONS = {
    "renewNativeLease",
    "releaseNativeLease",
    "createNativeUploadGrant",
    "registerNativeArtifact",
    "reportNativeTerminal",
}
OPERATIONS = {"reportWorkerPresence", "acquireNativeLease", *LEASE_OPERATIONS}
INVALID_CASES = {
    "request-selected worker identity",
    "capacity above one",
    "worker declares qualification",
    "cancellation missing stop deadline",
    "deadline without cancellation",
    "mutation missing revision fence",
    "worker chooses artifact uri",
    "completed without registered manifest",
    "failed without failure classification",
    "worker chooses object key",
}
HTTP_CASES = {
    "presence is interpreted by the server",
    "compatible work is leased",
    "no compatible work has bounded retry",
    "renewal observes cancellation",
    "an expired lease rejects mutation",
    "release is idempotent",
    "exact object upload is granted",
    "uploaded bytes are registered",
    "terminal completion is acknowledged",
    "duplicate terminal completion is idempotent",
}


def operation(document: dict[str, Any], operation_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the path item and operation with the requested unique ID."""
    matches = [
        (path_item, candidate)
        for path_item in document["paths"].values()
        for method, candidate in path_item.items()
        if method == "post" and candidate["operationId"] == operation_id
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one operation named {operation_id}")
    return matches[0]


def resolve_component(document: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    """Resolve one document-local component reference."""
    if "$ref" not in value:
        return value
    target: Any = document
    for part in value["$ref"][2:].split("/"):
        target = target[part]
    if not isinstance(target, dict):
        raise ValueError("Component reference does not resolve to an object")
    return target


def request_schema(operation_value: dict[str, Any]) -> dict[str, Any]:
    return operation_value["requestBody"]["content"]["application/json"]["schema"]


def response_schema(
    document: dict[str, Any], operation_value: dict[str, Any], status: int
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    response = resolve_component(document, operation_value["responses"][str(status)])
    content = response.get("content")
    schema = None if content is None else content["application/json"]["schema"]
    return response, schema


def check_times(values: dict[str, Any]) -> None:
    lease = values["lease"]
    issued = datetime.fromisoformat(lease["issuedAt"])
    expires = datetime.fromisoformat(lease["expiresAt"])
    if issued >= expires or lease["renewAfterSeconds"] >= (expires - issued).total_seconds():
        raise ValueError("Lease renewal is not bounded by its server-issued lifetime")

    renewal = values["renewal"]
    server_time = datetime.fromisoformat(renewal["serverTime"])
    renewed_expiry = datetime.fromisoformat(renewal["expiresAt"])
    stop_by = datetime.fromisoformat(renewal["stopBy"])
    if not server_time < stop_by <= renewed_expiry:
        raise ValueError("Cancellation deadline is outside the renewed lease lifetime")

    grant_expiry = datetime.fromisoformat(values["upload-grant"]["expiresAt"])
    if not issued < grant_expiry <= expires:
        raise ValueError("Upload grant outlives its execution lease")


def check_exact_object_scope(values: dict[str, Any]) -> None:
    grant = values["upload-grant"]
    expected_key = f"runs/{grant['runId']}/attempts/{grant['attemptId']}/{grant['slot']}"
    if grant["objectKey"] != expected_key:
        raise ValueError("Upload grant is not bound to the exact server-selected object key")
    request = values["upload-request"]
    if grant["slot"] != request["slot"] or grant["sha256"] != request["sha256"]:
        raise ValueError("Upload grant differs from the requested artifact identity")
    if request["size"] > grant["maximumBytes"]:
        raise ValueError("Upload grant is smaller than the declared artifact")
    upload = urlsplit(grant["uploadUrl"])
    if (
        upload.username is not None
        or upload.password is not None
        or upload.query
        or upload.fragment
    ):
        raise ValueError("Upload endpoint contains credential or mutable URL state")
    if upload.path != "/upload/" + expected_key:
        raise ValueError("Upload endpoint differs from the exact server-selected object key")

    plan = next(
        (item for item in values["lease"]["artifactPlan"] if item["slot"] == grant["slot"]),
        None,
    )
    if plan is None or grant["maximumBytes"] > plan["maximumBytes"]:
        raise ValueError("Upload grant exceeds its assigned artifact plan")

    artifact = values["artifact"]
    suffix = f"/runs/{artifact['runId']}/attempts/{artifact['attemptId']}/{artifact['slot']}"
    if not artifact["uri"].endswith(suffix):
        raise ValueError("Registered artifact URI differs from its immutable identity")
    registration = values["register-artifact"]
    for field in ["attemptId", "slot", "size", "sha256"]:
        if artifact[field] != registration[field]:
            raise ValueError("Registered artifact differs from uploaded bytes")
    if artifact["kind"] != plan["kind"] or artifact["mediaType"] != plan["mediaType"]:
        raise ValueError("Registered artifact differs from its assigned artifact plan")


def check_fixture_safety(conformance: dict[str, Any], cases: list[dict[str, Any]]) -> None:
    serialized = json.dumps(conformance).lower()
    for forbidden in ["password", "authorization", "access_token", "refresh_token"]:
        if forbidden in serialized:
            raise ValueError("Conformance fixtures contain credential-shaped material")

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str) and value.startswith(("http://", "https://")):
            host = urlsplit(value).hostname
            if host is None or not host.endswith(".invalid"):
                raise ValueError("Fixtures must use reserved non-routable HTTPS endpoints")

    visit(conformance)
    for case in cases:
        for headers_name in ["requestHeaders", "headers"]:
            for name, value in case.get(headers_name, {}).items():
                if name in {"X-Perfeng-Lease", "X-Perfeng-Upload-Grant"} and (
                    not isinstance(value, str) or not value.startswith("example-not-a-real-")
                ):
                    raise ValueError("HTTP fixtures may contain only explicit fake capabilities")


def lint(document: dict[str, Any]) -> None:
    check_local_references(document, document)
    errors = list(OpenAPIV31SpecValidator(document).iter_errors())
    if errors:
        raise ValueError(f"Invalid OpenAPI document: {errors[0]}")
    if document["openapi"] != "3.1.1" or document["security"] != [{"workerBearer": []}]:
        raise ValueError("Expected the authenticated Native Worker OpenAPI 3.1.1 contract")
    server = urlsplit(document["servers"][0]["url"])
    if server.scheme != "https" or server.hostname != "control.perfeng.invalid":
        raise ValueError("API server must be the reserved non-routable HTTPS endpoint")

    identifiers: set[str] = set()
    for path_item in document["paths"].values():
        for method, candidate in path_item.items():
            if method == "parameters":
                continue
            if method != "post":
                raise ValueError("Native Worker v1 is an outbound-pull POST-only protocol")
            operation_id = candidate["operationId"]
            if operation_id in identifiers:
                raise ValueError("Duplicate operation ID")
            identifiers.add(operation_id)
            if candidate.get("security", document["security"]) != document["security"]:
                raise ValueError("Operation disables worker authentication")
            if not STANDARD_ERRORS <= set(candidate["responses"]):
                raise ValueError("Operation is missing a standard error response")
            parameters = [
                resolve_component(document, item)
                for item in path_item.get("parameters", []) + candidate.get("parameters", [])
            ]
            names = {item["name"] for item in parameters}
            if operation_id in LEASE_OPERATIONS:
                if names != {"leaseId", "X-Perfeng-Lease"}:
                    raise ValueError("Lease mutation is not bound to its path and capability")
                if not {"409", "410"} <= set(candidate["responses"]):
                    raise ValueError("Lease mutation lacks stale-revision and lost-lease outcomes")
            elif names:
                raise ValueError("Presence and acquisition cannot accept a lease capability")
    if identifiers != OPERATIONS:
        raise ValueError("Unexpected Native Worker operation inventory")

    schemas = document["components"]["schemas"]
    capacity = schemas["WorkerCapabilities"]["properties"]["capacity"]
    if capacity.get("const") != 1:
        raise ValueError("Native Worker v1 must expose exactly one measurement slot")
    if {"workerId", "principal", "credential", "token"} & set(
        schemas["WorkerPresence"]["properties"]
    ):
        raise ValueError("Worker identity or credentials cannot be request-selected")
    if "objectKey" in schemas["UploadGrantRequest"]["properties"]:
        raise ValueError("Worker cannot select an upload object key")

    _, acquire = operation(document, "acquireNativeLease")
    if set(acquire["responses"]["200"]["headers"]) != {"X-Perfeng-Lease"}:
        raise ValueError("Lease capability must be returned only in its response header")
    _, grant = operation(document, "createNativeUploadGrant")
    if set(grant["responses"]["201"]["headers"]) != {"X-Perfeng-Upload-Grant"}:
        raise ValueError("Upload capability must be returned only in its response header")


def check_http(document: dict[str, Any], case: dict[str, Any], values: dict[str, Any]) -> None:
    path_item, operation_value = operation(document, case["operationId"])
    parameters = [
        resolve_component(document, item)
        for item in path_item.get("parameters", []) + operation_value.get("parameters", [])
    ]
    for parameter in parameters:
        source = (
            {name.lower(): value for name, value in case.get("requestHeaders", {}).items()}
            if parameter["in"] == "header"
            else case.get("pathParameters", {})
        )
        name = parameter["name"].lower() if parameter["in"] == "header" else parameter["name"]
        if parameter.get("required") and name not in source:
            raise ValueError("Required Native Worker request parameter missing")
        if name in source:
            schema_validator(document, "Uuid").evolve(schema=parameter["schema"]).validate(
                source[name]
            )

    request = parse_request(json.dumps(values[case["request"]]).encode())
    schema_validator(document, "Uuid").evolve(schema=request_schema(operation_value)).validate(
        request
    )
    response, schema = response_schema(document, operation_value, case["status"])
    if schema is None:
        if "response" in case:
            raise ValueError("Response body supplied for an empty response")
    else:
        body = values[case["response"]]
        schema_validator(document, "Uuid").evolve(schema=schema).validate(body)
    response_headers = {name.lower(): value for name, value in case.get("headers", {}).items()}
    for name, header in response.get("headers", {}).items():
        definition = resolve_component(document, header)
        if definition.get("required") and name.lower() not in response_headers:
            raise ValueError("Required Native Worker response header missing")
        if name.lower() in response_headers:
            schema_validator(document, "Uuid").evolve(schema=definition["schema"]).validate(
                response_headers[name.lower()]
            )

    operation_id = case["operationId"]
    if operation_id in LEASE_OPERATIONS:
        if case["pathParameters"]["leaseId"] != values["lease"]["leaseId"]:
            raise ValueError("HTTP case targets a different lease")
    if operation_id == "renewNativeLease" and case["status"] == 200:
        if values[case["request"]]["attemptId"] != values[case["response"]]["attemptId"]:
            raise ValueError("Renewal changed execution attempt")
    if operation_id == "reportNativeTerminal" and (
        values[case["request"]]["attemptId"] != values[case["response"]]["attemptId"]
    ):
        raise ValueError("Terminal acknowledgement changed execution attempt")


def validate_native_worker_api(root: Path = ROOT) -> tuple[int, int, int]:
    document = read_json(root / API_PATH / "openapi.json")
    lint(document)
    conformance = read_json(root / API_PATH / "conformance.json")
    valid = conformance["valid"]
    invalid = conformance["invalid"]
    values: dict[str, Any] = {}
    for fixture in valid:
        if fixture["name"] in values:
            raise ValueError("Duplicate Native Worker fixture name")
        schema_validator(document, fixture["schema"]).validate(fixture["value"])
        values[fixture["name"]] = fixture["value"]
    if {fixture["name"] for fixture in invalid} != INVALID_CASES:
        raise ValueError("Native Worker negative fixture inventory changed")
    for fixture in invalid:
        if schema_validator(document, fixture["schema"]).is_valid(fixture["value"]):
            raise ValueError(f"Negative fixture unexpectedly passed: {fixture['name']}")

    check_times(values)
    check_exact_object_scope(values)
    cases = read_json(root / API_PATH / "http-cases.json")
    if {case["name"] for case in cases} != HTTP_CASES or len(cases) != len(HTTP_CASES):
        raise ValueError("Native Worker HTTP fixture coverage is incomplete or duplicated")
    check_fixture_safety(conformance, cases)
    for case in cases:
        check_http(document, case, values)
    return len(valid), len(invalid), len(cases)


if __name__ == "__main__":
    valid_count, invalid_count, http_count = validate_native_worker_api()
    print(
        "Validated Native Worker OpenAPI, "
        f"{valid_count} positive fixtures, {invalid_count} rejection fixtures, "
        f"and {http_count} HTTP cases (offline)."
    )
