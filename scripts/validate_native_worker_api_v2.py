"""Offline conformance checks for the baseline Native Worker API v2 candidate."""

from pathlib import Path
from typing import Any

if __package__:
    from .validate import ROOT, read_json
    from .validate_api import schema_validator
    from .validate_native_worker_api import (
        FIXTURES,
        HTTP_CASES,
        check_artifact_formats,
        check_exact_object_scope,
        check_fixture_safety,
        check_http,
        check_times,
        lint,
    )
    from .validate_native_worker_api import (
        REJECTIONS as V1_REJECTIONS,
    )
else:
    from validate import ROOT, read_json
    from validate_api import schema_validator
    from validate_native_worker_api import (
        FIXTURES,
        HTTP_CASES,
        check_artifact_formats,
        check_exact_object_scope,
        check_fixture_safety,
        check_http,
        check_times,
        lint,
    )
    from validate_native_worker_api import (
        REJECTIONS as V1_REJECTIONS,
    )

API_PATH = "api/native-worker/v2"
WORKLOAD_PROFILES = {"smoke", "average", "regression", "stress", "capacity", "soak"}
REJECTIONS = V1_REJECTIONS | {
    "recipe-missing-workload-sha256",
    "recipe-unsupported-journey",
    "recipe-invalid-cache-reuse",
    "recipe-invalid-browser-settings",
}


def lint_v2(document: dict[str, Any]) -> None:
    """Require an independent v2 route generation and closed baseline recipe."""
    lint(document)
    if document["info"]["version"] != "2.0.0" or not all(
        path.startswith("/native-worker/v2/") for path in document["paths"]
    ):
        raise ValueError("Native Worker v2 paths and version must be independent of v1")
    schemas = document["components"]["schemas"]
    if (
        schemas["WorkerPresence"]["properties"]["protocolVersion"] != {"const": 2}
        or schemas["AcquireLease"]["properties"]["protocolVersion"] != {"const": 2}
        or schemas["WorkerCapabilities"]["properties"]["runnerContract"] != {"const": 2}
    ):
        raise ValueError("Native Worker v2 protocol and runner generation must be explicit")
    assignment = schemas["Lease"]["properties"]["assignment"]
    if "recipe" not in assignment["required"] or assignment["properties"]["recipe"] != {
        "$ref": "#/components/schemas/ExecutionRecipe"
    }:
        raise ValueError("Native Worker v2 lease must require the reviewed execution recipe")
    if assignment["properties"]["browser"] != {"const": "chromium"} or assignment["properties"][
        "diagnosticMode"
    ] != {"const": "baseline"}:
        raise ValueError("Initial v2 execution slice must remain baseline Chromium only")
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
        raise ValueError("Native Worker v2 recipe is incomplete or selects an unknown journey")


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


def validate_native_worker_api_v2(root: Path = ROOT) -> tuple[int, int, int]:
    """Validate the independent v2 API, examples, rejections and HTTP corpus."""
    path = root / API_PATH
    document = read_json(path / "openapi.json")
    lint_v2(document)
    if {item.stem for item in (path / "examples").glob("*.json")} != set(FIXTURES):
        raise ValueError("Native Worker v2 example inventory changed without validation")
    values = {name: read_json(path / "examples" / f"{name}.json") for name in FIXTURES}
    for name, schema in FIXTURES.items():
        schema_validator(document, schema).validate(values[name])
    if {item.stem for item in (path / "rejections").glob("*.json")} != REJECTIONS:
        raise ValueError("Native Worker v2 rejection inventory changed without validation")
    rejections = {name: read_json(path / "rejections" / f"{name}.json") for name in REJECTIONS}
    for name, fixture in rejections.items():
        if schema_validator(document, fixture["schema"]).is_valid(fixture["value"]):
            raise ValueError(f"Native Worker v2 rejection unexpectedly passed: {name}")
    cases = read_json(path / "http-cases.json")
    coverage = {
        (case["operationId"], case["status"], case.get("request"), case.get("response"))
        for case in cases
    }
    if coverage != HTTP_CASES or len(cases) != len(HTTP_CASES):
        raise ValueError("Native Worker v2 HTTP fixture coverage is incomplete or duplicated")
    check_times(values)
    check_artifact_formats(values)
    check_exact_object_scope(values)
    check_recipe(values)
    check_fixture_safety(values, rejections, cases)
    for case in cases:
        check_http(document, case, values)
    return len(values), len(rejections), len(cases)


if __name__ == "__main__":
    valid, rejected, http = validate_native_worker_api_v2()
    print(
        f"Validated Native Worker v2: {valid} examples, {rejected} rejections, {http} HTTP cases (offline)."
    )
