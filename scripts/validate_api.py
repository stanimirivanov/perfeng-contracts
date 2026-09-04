"""Offline OpenAPI lint, fixture conformance, and lifecycle consistency checks."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.protocols import Validator
from openapi_spec_validator import OpenAPIV31SpecValidator
from referencing import Registry

if __package__:
    from .validate import ROOT, no_network, parse_finite_float, read_json, reject_nonfinite_constant
else:
    from validate import ROOT, no_network, parse_finite_float, read_json, reject_nonfinite_constant

API_PATH = "api/run-management/v1"
TERMINAL = {"COMPLETED", "INVALID", "ABORTED", "INFRASTRUCTURE_FAILURE", "TEST_FAILURE"}
FIXTURES = {
    "create": "CreateRun",
    "created": "Run",
    "cancelling": "Run",
    "aborted": "Run",
    "completed": "Run",
    "invalid": "Run",
    "error": "Error",
    "artifacts": "ArtifactCollection",
}


def check_local_references(value: Any, document: dict[str, Any]) -> None:
    if isinstance(value, list):
        for child in value:
            check_local_references(child, document)
    elif isinstance(value, dict):
        for key, child in value.items():
            if key in {"$id", "$dynamicRef", "$recursiveRef"}:
                raise ValueError("API schemas must use document-local static references")
            if key == "$ref":
                if not isinstance(child, str) or not child.startswith("#/"):
                    raise ValueError(
                        "API references must be document-local; network lookup refused"
                    )
                target: Any = document
                try:
                    for part in child[2:].split("/"):
                        target = target[part.replace("~1", "/").replace("~0", "~")]
                except (KeyError, TypeError):
                    raise ValueError(f"Unresolved local API reference: {child}") from None
            else:
                check_local_references(child, document)


def schema_validator(document: dict[str, Any], name: str) -> Validator:
    # Resolve component pointers against the whole document, never the network.
    return Draft202012Validator(
        document,
        registry=Registry(retrieve=no_network),
        format_checker=FormatChecker(),
    ).evolve(schema={"$ref": "#/components/schemas/" + name})


def parse_request(body: bytes) -> Any:
    if len(body) > 65536:
        raise ValueError("Request exceeds 64 KiB")

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON object key")
            result[key] = value
        return result

    return json.loads(
        body.decode("utf-8"),
        object_pairs_hook=unique,
        parse_constant=reject_nonfinite_constant,
        parse_float=parse_finite_float,
    )


def check_http(document: dict[str, Any], case: dict[str, Any], examples: dict[str, Any]) -> None:
    operation = next(
        op
        for path in document["paths"].values()
        for method, op in path.items()
        if method in {"get", "post"} and op["operationId"] == case["operationId"]
    )
    validator = schema_validator(document, "Run")
    for parameter in operation.get("parameters", []):
        if parameter["in"] != "header":
            continue
        headers = {k.lower(): v for k, v in case.get("requestHeaders", {}).items()}
        name = parameter["name"].lower()
        if parameter.get("required") and name not in headers:
            raise ValueError("Required request header missing")
        if name in headers:
            validator.evolve(schema=parameter["schema"]).validate(headers[name])
    if "requestBody" in operation:
        body = parse_request(json.dumps(examples[case["request"]]).encode())
        validator.evolve(
            schema=operation["requestBody"]["content"]["application/json"]["schema"]
        ).validate(body)
    elif "request" in case:
        raise ValueError("This operation has no request body")
    response = operation["responses"][str(case["status"])]
    if "$ref" in response:
        response = document["components"]["responses"][response["$ref"].split("/")[-1]]
    body = examples[case["response"]]
    validator.evolve(schema=response["content"]["application/json"]["schema"]).validate(body)
    headers = {k.lower(): v for k, v in case.get("headers", {}).items()}
    for name, definition in response.get("headers", {}).items():
        if definition.get("required") and name.lower() not in headers:
            raise ValueError("Required response header missing")
        if name.lower() in headers:
            validator.evolve(schema=definition["schema"]).validate(headers[name.lower()])
    if case["status"] == 201:
        check_run(body)
        if headers["location"] != "/v1/runs/" + body["id"]:
            raise ValueError("Location does not identify the accepted run")
        if body["request"] != examples[case["request"]]:
            raise ValueError("Accepted run request differs from submitted request")
        expires = datetime.fromisoformat(headers["idempotency-key-expires-at"])
        if expires < datetime.fromisoformat(body["createdAt"]) + timedelta(hours=24):
            raise ValueError("Idempotency retention is shorter than 24 hours")
    if body.get("code") == "REQUEST_IN_PROGRESS" and "retry-after" not in headers:
        raise ValueError("In-progress retry requires Retry-After")
    if case["operationId"] == "listRunArtifacts":
        check_artifacts(document, body, case.get("pathParameters", {}).get("runId"))


def check_artifacts(document: dict[str, Any], value: dict[str, Any], run_id: Any) -> None:
    if not isinstance(run_id, str):
        raise ValueError("Artifact listing requires the run path parameter")
    schema_validator(document, "RunId").validate(run_id)
    artifacts = value["artifacts"]
    ids = [artifact["id"] for artifact in artifacts]
    locations = [artifact["uri"] for artifact in artifacts]
    if ids != sorted(ids):
        raise ValueError("Artifacts are not ordered by ID")
    if len(ids) != len(set(ids)) or len(locations) != len(set(locations)):
        raise ValueError("Artifact identities and locations must be unique")
    if any(artifact["runId"] != run_id for artifact in artifacts):
        raise ValueError("Artifact belongs to another run")
    for location in locations:
        parsed = urlsplit(location)
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Artifact location contains user information")


def check_run(value: dict[str, Any]) -> None:
    """Semantic conformance only; not a runtime run manager."""
    created = datetime.fromisoformat(value["createdAt"])
    updated = datetime.fromisoformat(value["updatedAt"])
    if updated < created:
        raise ValueError("Run update precedes creation")
    if value["state"] in TERMINAL:
        finished = datetime.fromisoformat(value["finishedAt"])
        if not created <= finished <= updated:
            raise ValueError("Terminal timestamp is outside the run lifetime")
    if value["state"] == "CREATED" and (
        value["revision"] != 1 or updated != created or "toolExitCode" in value
    ):
        raise ValueError("Initial snapshot must have revision 1 and no execution result")
    if value["state"] != "CREATED" and value["revision"] < 2:
        raise ValueError("Transitioned snapshots require a newer revision")
    failure = value.get("failure", {}).get("code")
    allowed = {
        "INVALID": {"VALIDATION_FAILED"},
        "TEST_FAILURE": {"TOOL_ERROR"},
        "INFRASTRUCTURE_FAILURE": {"INFRASTRUCTURE_ERROR", "PIPELINE_TIMEOUT", "ANALYSIS_ERROR"},
    }
    if value["state"] in allowed and failure not in allowed[value["state"]]:
        raise ValueError("Failure code contradicts the terminal lifecycle state")


def lint(document: dict[str, Any], transitions: dict[str, list[str]]) -> None:
    check_local_references(document, document)
    errors = list(OpenAPIV31SpecValidator(document).iter_errors())
    if errors:
        raise ValueError(f"Invalid OpenAPI document: {errors[0]}")
    if document["openapi"] != "3.1.1" or document["security"] != [{"bearerAuth": []}]:
        raise ValueError("Expected the authenticated OpenAPI 3.1.1 contract")
    identifiers = set()
    for path in document["paths"].values():
        for method, operation in path.items():
            if method == "parameters":
                continue
            if method not in {"get", "post"}:
                raise ValueError("Unexpected API method")
            operation_id = operation["operationId"]
            if operation_id in identifiers:
                raise ValueError("Duplicate operation ID")
            identifiers.add(operation_id)
            if operation.get("security", document["security"]) != document["security"]:
                raise ValueError("Operation disables required authentication")
            for status in ["400", "401", "403", "429", "500", "503"]:
                if status not in operation["responses"]:
                    raise ValueError("Missing standard error response")
    if identifiers != {"createRun", "getRun", "listRunArtifacts", "cancelRun"}:
        raise ValueError("Unexpected API operation inventory")
    states = set(document["components"]["schemas"]["RunState"]["enum"])
    if set(transitions) != states or not TERMINAL <= states:
        raise ValueError("Lifecycle table and API states differ")
    for state, targets in transitions.items():
        if len(set(targets)) != len(targets) or state in targets or not set(targets) <= states:
            raise ValueError("Invalid lifecycle transition")
        if (state in TERMINAL) != (not targets):
            raise ValueError("Terminal states must have no outgoing transitions")
        if state not in TERMINAL | {"CANCELLING"} and "CANCELLING" not in targets:
            raise ValueError("Every active state must support cancellation")
    reached = {"CREATED"}
    while True:
        expanded = reached | {target for state in reached for target in transitions[state]}
        if expanded == reached:
            break
        reached = expanded
    if reached != states:
        raise ValueError("Unreachable lifecycle state")


def validate_api(root: Path = ROOT) -> int:
    entries = read_json(root / "contracts.json")["apis"]
    if entries != [
        {
            "name": "run-management/v1",
            "definition": API_PATH + "/openapi.json",
            "transitions": API_PATH + "/transitions.json",
        }
    ]:
        raise ValueError("Unexpected API manifest")
    document = read_json(root / API_PATH / "openapi.json")
    transitions = read_json(root / API_PATH / "transitions.json")
    lint(document, transitions)
    examples = root / API_PATH / "examples"
    if {p.stem for p in examples.glob("*.json")} != set(FIXTURES):
        raise ValueError("API fixture inventory changed without validation coverage")
    for name, schema in FIXTURES.items():
        value = read_json(examples / (name + ".json"))
        schema_validator(document, schema).validate(value)
        if schema == "Run":
            check_run(value)
    values = {name: read_json(examples / (name + ".json")) for name in FIXTURES}
    cases = read_json(root / API_PATH / "http-cases.json")
    expected = {
        ("createRun", 201),
        ("createRun", 409),
        ("getRun", 200),
        ("listRunArtifacts", 200),
        ("cancelRun", 200),
        ("cancelRun", 202),
    }
    if len(cases) != len(expected) or {(c["operationId"], c["status"]) for c in cases} != expected:
        raise ValueError("HTTP fixture coverage is incomplete or duplicated")
    for case in cases:
        check_http(document, case, values)
    return len(FIXTURES)


if __name__ == "__main__":
    print(f"Validated run-management OpenAPI and {validate_api()} fixtures (offline).")
