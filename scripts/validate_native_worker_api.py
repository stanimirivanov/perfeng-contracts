"""Offline validation of the supported Native Worker API and conformance corpus."""

import base64
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from openapi_spec_validator import OpenAPIV31SpecValidator

if __package__:
    from .validate import ROOT, read_json
    from .validate_api import check_local_references, parse_request, schema_validator
else:
    from validate import ROOT, read_json
    from validate_api import check_local_references, parse_request, schema_validator

API_PATH = "api/native-worker/v2"
WORKLOAD_PROFILES = {"smoke", "average", "regression", "stress", "capacity", "soak"}
STANDARD_ERRORS = {"400", "401", "403", "429", "500", "503"}
LEASE_OPERATIONS = {
    "renewNativeLease",
    "releaseNativeLease",
    "createNativeUploadGrant",
    "registerNativeArtifact",
    "reportNativeTerminal",
}
OPERATIONS = {"reportWorkerPresence", "acquireNativeLease", *LEASE_OPERATIONS}
SIGNED_UPLOAD_HEADERS = {
    "content-type",
    "host",
    "x-amz-checksum-sha256",
}
REQUIRED_PRESIGN_PARAMETERS = {
    "X-Amz-Algorithm",
    "X-Amz-Credential",
    "X-Amz-Date",
    "X-Amz-Expires",
    "X-Amz-SignedHeaders",
    "X-Amz-Signature",
}
OPTIONAL_PRESIGN_PARAMETERS = {"X-Amz-Security-Token", "x-id"}
CANONICAL_ARTIFACT_FORMATS = {
    "measurements": "playwright-measurements/v2",
    "manifest": "raw-result/v2",
}
FIXTURES = {
    "presence": "WorkerPresence",
    "presence-status": "PresenceStatus",
    "acquire": "AcquireLease",
    "lease": "Lease",
    "renew": "RenewLease",
    "renewal": "LeaseRenewal",
    "release": "ReleaseLease",
    "upload-request": "UploadGrantRequest",
    "upload-grant": "UploadGrant",
    "register-artifact": "RegisterArtifact",
    "artifact": "ArtifactReference",
    "terminal-completed": "TerminalReport",
    "terminal-failed": "TerminalReport",
    "terminal-ack": "TerminalAck",
    "terminal-ack-duplicate": "TerminalAck",
    "lease-gone-error": "Error",
}
REJECTIONS = {
    "request-selected-worker-identity",
    "capacity-above-one",
    "worker-declares-qualification",
    "cancellation-missing-stop-deadline",
    "deadline-without-cancellation",
    "mutation-missing-revision-fence",
    "worker-chooses-artifact-uri",
    "completed-without-registered-manifest",
    "failed-without-failure-classification",
    "upload-grant-missing-signed-headers",
    "worker-chooses-object-key",
    "recipe-missing-workload-sha256",
    "recipe-unsupported-journey",
    "recipe-invalid-cache-reuse",
    "recipe-invalid-browser-settings",
}
HTTP_CASES = {
    ("reportWorkerPresence", 200, "presence", "presence-status"),
    ("acquireNativeLease", 200, "acquire", "lease"),
    ("acquireNativeLease", 204, "acquire", None),
    ("renewNativeLease", 200, "renew", "renewal"),
    ("renewNativeLease", 410, "renew", "lease-gone-error"),
    ("releaseNativeLease", 204, "release", None),
    ("createNativeUploadGrant", 201, "upload-request", "upload-grant"),
    ("registerNativeArtifact", 201, "register-artifact", "artifact"),
    ("reportNativeTerminal", 200, "terminal-completed", "terminal-ack"),
    ("reportNativeTerminal", 200, "terminal-completed", "terminal-ack-duplicate"),
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


def check_artifact_formats(values: dict[str, Any]) -> None:
    """Require assigned slots to name the canonical data contracts they carry."""
    actual = {item["slot"]: item["format"] for item in values["lease"]["artifactPlan"]}
    if actual != CANONICAL_ARTIFACT_FORMATS:
        raise ValueError("Native artifact plan does not use the canonical contract formats")


def check_recipe(values: dict[str, Any]) -> None:
    """Check identities spanning presence, assignment and the runner projection."""
    assignment = values["lease"]["assignment"]
    recipe = assignment["recipe"]
    presence = values["presence"]
    evidence = presence["qualificationEvidence"]
    if assignment["profile"] not in WORKLOAD_PROFILES:
        raise ValueError("Assigned workload profile is not a Playwright runner profile")
    if (
        recipe["environment"]["profileId"] != evidence["environmentId"]
        or recipe["environment"]["evidenceSha256"] != evidence["environmentSha256"]
    ):
        raise ValueError("Execution recipe differs from the qualified host evidence")
    if assignment["executionArtifact"] != evidence["runner"]:
        raise ValueError("Execution artifact differs from the qualified runner")
    capabilities = presence["capabilities"]
    if (
        assignment["browser"] not in capabilities["browsers"]
        or assignment["diagnosticMode"] not in capabilities["diagnosticModes"]
        or any(
            slot["kind"] not in capabilities["artifactKinds"]
            for slot in values["lease"]["artifactPlan"]
        )
    ):
        raise ValueError("Execution recipe exceeds the worker's claimed capabilities")
    if any(not slot["required"] for slot in values["lease"]["artifactPlan"]):
        raise ValueError("The baseline measurements and manifest must both be required")


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
    if upload.username is not None or upload.password is not None or upload.fragment:
        raise ValueError("Upload endpoint contains forbidden URL state")
    if not upload.path.endswith("/" + expected_key):
        raise ValueError("Upload endpoint differs from the exact server-selected object key")
    query_items = parse_qsl(upload.query, keep_blank_values=True, strict_parsing=True)
    if len(query_items) != len({name for name, _ in query_items}):
        raise ValueError("Presigned upload URL contains duplicate query parameters")
    query = dict(query_items)
    if not REQUIRED_PRESIGN_PARAMETERS <= set(query) or not set(query) <= (
        REQUIRED_PRESIGN_PARAMETERS | OPTIONAL_PRESIGN_PARAMETERS
    ):
        raise ValueError("Presigned upload URL has an unexpected parameter set")
    if query["X-Amz-Algorithm"] != "AWS4-HMAC-SHA256":
        raise ValueError("Upload grant does not use S3 Signature Version 4")
    if query.get("x-id", "PutObject") != "PutObject":
        raise ValueError("Presigned upload URL does not authorize PutObject")
    try:
        presign_seconds = int(query["X-Amz-Expires"])
    except ValueError as error:
        raise ValueError("Presigned upload expiry is not an integer") from error
    if not 1 <= presign_seconds <= 300:
        raise ValueError("Presigned upload expiry is outside the protocol bound")
    if query["X-Amz-SignedHeaders"] != ";".join(sorted(SIGNED_UPLOAD_HEADERS)):
        raise ValueError("Presigned upload URL does not bind the exact required headers")
    try:
        presign_issued = datetime.strptime(query["X-Amz-Date"], "%Y%m%dT%H%M%SZ").replace(
            tzinfo=UTC
        )
    except ValueError as error:
        raise ValueError("Presigned upload issue time is not an AWS basic timestamp") from error
    grant_expiry = datetime.fromisoformat(grant["expiresAt"])
    if presign_issued + timedelta(seconds=presign_seconds) != grant_expiry:
        raise ValueError("Presigned upload expiry differs from the declared grant expiry")

    expected_headers = {
        "content-type": request["mediaType"],
        "x-amz-checksum-sha256": base64.b64encode(bytes.fromhex(request["sha256"])).decode(),
    }
    if grant["uploadHeaders"] != expected_headers:
        raise ValueError("Presigned upload headers differ from the declared artifact")

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


def check_fixture_safety(
    examples: dict[str, Any], rejections: dict[str, Any], cases: list[dict[str, Any]]
) -> None:
    serialized = json.dumps({"examples": examples, "rejections": rejections}).lower()
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
            parsed = urlsplit(value)
            host = parsed.hostname
            if host is None or not host.endswith(".invalid"):
                raise ValueError("Fixtures must use reserved non-routable HTTPS endpoints")
            query = dict(parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True))
            if "X-Amz-Credential" in query and (
                not query["X-Amz-Credential"].startswith("EXAMPLE-NOT-A-REAL-")
                or query.get("X-Amz-Signature") != "0" * 64
            ):
                raise ValueError(
                    "Presigned upload fixture must contain explicit non-secret placeholders"
                )

    visit(examples)
    visit(rejections)
    for case in cases:
        for headers_name in ["requestHeaders", "headers"]:
            for name, value in case.get(headers_name, {}).items():
                if name == "X-Perfeng-Lease" and (
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
                raise ValueError("Native Worker is an outbound-pull POST-only protocol")
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
    if schemas["ArtifactPlan"]["properties"]["format"] != {
        "$ref": "#/components/schemas/ArtifactFormat"
    }:
        raise ValueError("Artifact plans must use the artifact-format contract")
    capacity = schemas["WorkerCapabilities"]["properties"]["capacity"]
    if capacity.get("const") != 1:
        raise ValueError("Native Worker must expose exactly one measurement slot")
    if {"workerId", "principal", "credential", "token"} & set(
        schemas["WorkerPresence"]["properties"]
    ):
        raise ValueError("Worker identity or credentials cannot be request-selected")
    if "objectKey" in schemas["UploadGrantRequest"]["properties"]:
        raise ValueError("Worker cannot select an upload object key")
    if "UploadCapability" in schemas:
        raise ValueError("Native upload authorization cannot use a custom capability header")
    if set(schemas["UploadGrant"]["required"]) != {
        "grantId",
        "leaseId",
        "attemptId",
        "runId",
        "slot",
        "objectKey",
        "uploadUrl",
        "uploadHeaders",
        "method",
        "expiresAt",
        "maximumBytes",
        "sha256",
    }:
        raise ValueError("Upload grant must require exact presigned PUT delivery material")

    _, acquire = operation(document, "acquireNativeLease")
    if set(acquire["responses"]["200"]["headers"]) != {"X-Perfeng-Lease"}:
        raise ValueError("Lease capability must be returned only in its response header")
    _, grant = operation(document, "createNativeUploadGrant")
    if grant["responses"]["201"].get("headers"):
        raise ValueError("Upload authorization must be returned only in the response body")

    if document["info"]["version"] != "2.0.0" or not all(
        path.startswith("/native-worker/v2/") for path in document["paths"]
    ):
        raise ValueError("Native Worker paths and version must identify protocol v2")
    if (
        schemas["WorkerPresence"]["properties"]["protocolVersion"] != {"const": 2}
        or schemas["AcquireLease"]["properties"]["protocolVersion"] != {"const": 2}
        or schemas["WorkerCapabilities"]["properties"]["runnerContract"] != {"const": 2}
    ):
        raise ValueError("Native Worker protocol and runner generation must be explicit")
    assignment = schemas["Lease"]["properties"]["assignment"]
    if "recipe" not in assignment["required"] or assignment["properties"]["recipe"] != {
        "$ref": "#/components/schemas/ExecutionRecipe"
    }:
        raise ValueError("Native Worker lease must require the reviewed execution recipe")
    if assignment["properties"]["browser"] != {"const": "chromium"} or assignment["properties"][
        "diagnosticMode"
    ] != {"const": "baseline"}:
        raise ValueError("Initial execution slice must remain baseline Chromium only")
    recipe = schemas["ExecutionRecipe"]
    if (
        set(recipe["required"])
        != {
            "journeyId",
            "workloadVersion",
            "workloadSha256",
            "scenario",
            "environment",
            "browserSettings",
        }
        or recipe["properties"]["journeyId"].get("const") != "search"
    ):
        raise ValueError("Native Worker recipe is incomplete or selects an unknown journey")


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
    """Validate the sole supported API, examples, rejections and HTTP cases."""
    document = read_json(root / API_PATH / "openapi.json")
    lint(document)
    examples = root / API_PATH / "examples"
    if {path.stem for path in examples.glob("*.json")} != set(FIXTURES):
        raise ValueError("Native Worker example inventory changed without validation coverage")
    values = {name: read_json(examples / f"{name}.json") for name in FIXTURES}
    for name, schema in FIXTURES.items():
        schema_validator(document, schema).validate(values[name])

    rejection_root = root / API_PATH / "rejections"
    if {path.stem for path in rejection_root.glob("*.json")} != REJECTIONS:
        raise ValueError("Native Worker rejection inventory changed without validation coverage")
    rejections = {name: read_json(rejection_root / f"{name}.json") for name in REJECTIONS}
    for name, fixture in rejections.items():
        if schema_validator(document, fixture["schema"]).is_valid(fixture["value"]):
            raise ValueError(f"Rejection fixture unexpectedly passed: {name}")

    check_times(values)
    check_artifact_formats(values)
    check_exact_object_scope(values)
    check_recipe(values)
    cases = read_json(root / API_PATH / "http-cases.json")
    coverage = {
        (case["operationId"], case["status"], case.get("request"), case.get("response"))
        for case in cases
    }
    if coverage != HTTP_CASES or len(cases) != len(HTTP_CASES):
        raise ValueError("Native Worker HTTP fixture coverage is incomplete or duplicated")
    check_fixture_safety(values, rejections, cases)
    for case in cases:
        check_http(document, case, values)
    return len(values), len(rejections), len(cases)


if __name__ == "__main__":
    valid_count, invalid_count, http_count = validate_native_worker_api()
    print(
        "Validated Native Worker OpenAPI, "
        f"{valid_count} positive fixtures, {invalid_count} rejection fixtures, "
        f"and {http_count} HTTP cases (offline)."
    )
