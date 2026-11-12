"""Service access and CI resolution are additive, scoped contract boundaries."""

import copy
import json
import unittest
from typing import Any

from jsonschema.exceptions import ValidationError

from scripts.validate_api import ROOT, check_http, schema_validator


class ServiceAccessContractsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.api = json.loads((ROOT / "api/run-management/v1/openapi.json").read_text())

    def test_exact_resolution_requires_full_request_identity(self) -> None:
        operation = self.api["paths"]["/v1/run-resolutions"]["get"]
        self.assertEqual(operation["operationId"], "resolveRun")
        self.assertEqual(
            {(p["name"], p["in"], p["required"]) for p in operation["parameters"]},
            {("requestIssuer", "query", True), ("requestId", "query", True)},
        )
        self.assertNotIn("requestBody", operation)
        self.assertEqual(operation["x-perfeng-service-permission"], "run:read")

    def test_access_observation_is_read_only_and_not_an_authority_token(self) -> None:
        path = self.api["paths"]["/v1/runs/{runId}/access"]
        self.assertEqual(set(path), {"parameters", "get"})
        self.assertEqual(path["get"]["operationId"], "getRunAccess")
        for route in ("/v1/run-resolutions", "/v1/runs/{runId}/access"):
            operation = self.api["paths"][route]["get"]
            for status in ("200", "400", "401", "403", "404", "429", "500", "503"):
                self.assertIn(status, operation["responses"])
            self.assertEqual(
                operation["responses"]["200"]["headers"]["Cache-Control"]["schema"]["const"],
                "no-store",
            )

    def test_closed_access_and_resolution_fixtures(self) -> None:
        cases = json.loads((ROOT / "api/run-management/v1/service-access-cases.json").read_text())
        for schema, value in (
            ("RunAccess", cases["access"]),
            ("RunResolution", cases["resolution"]),
        ):
            validator = schema_validator(self.api, schema)
            validator.validate(value)
            forged = copy.deepcopy(value)
            forged["bearerToken"] = "secret"
            self.assertFalse(validator.is_valid(forged))
        access = copy.deepcopy(cases["access"])
        access["permissions"] = ["run:read", "run:read"]
        self.assertFalse(schema_validator(self.api, "RunAccess").is_valid(access))
        access["permissions"] = ["baseline:write"]
        self.assertFalse(schema_validator(self.api, "RunAccess").is_valid(access))

    def test_scope_conformance_uses_independent_grants_and_retained_mapping(self) -> None:
        from scripts.service_access import check_access, check_resolution

        cases = json.loads((ROOT / "api/run-management/v1/service-access-cases.json").read_text())
        for case in cases["checks"]:
            with self.subTest(case=case["name"]):
                inputs: dict[str, Any] = {**cases["trusted"], **case["overrides"]}
                if case["allowed"]:
                    check_access(cases["access"], **inputs)
                else:
                    with self.assertRaises(ValueError):
                        check_access(cases["access"], **inputs)
        check_resolution(
            cases["resolution"],
            request=cases["requestSelector"],
            run_id=cases["trusted"]["run_id"],
            service=cases["trusted"]["service"],
        )
        for key, value in (("issuer", "https://other.example/ci"), ("id", "retry-request")):
            request = {**cases["requestSelector"], key: value}
            with self.assertRaises(ValueError):
                check_resolution(
                    cases["resolution"],
                    request=request,
                    run_id=cases["trusted"]["run_id"],
                    service=cases["trusted"]["service"],
                )
        with self.assertRaises(ValueError):
            check_resolution(
                cases["resolution"],
                request=cases["requestSelector"],
                run_id="different-run",
                service=cases["trusted"]["service"],
            )

    def test_http_resolution_refuses_missing_issuer_and_sensitive_denial(self) -> None:
        cases = json.loads((ROOT / "api/run-management/v1/service-access-cases.json").read_text())
        case: dict[str, Any] = {
            "operationId": "resolveRun",
            "status": 200,
            "response": "resolution",
            "headers": {"Cache-Control": "no-store"},
            "queryParameters": {"requestIssuer": "https://ci.example", "requestId": "request-123"},
        }
        check_http(self.api, case, cases)
        missing = copy.deepcopy(case)
        del missing["queryParameters"]["requestIssuer"]
        with self.assertRaises(ValueError):
            check_http(self.api, missing, cases)
        missing = copy.deepcopy(case)
        missing["headers"] = {}
        with self.assertRaises(ValueError):
            check_http(self.api, missing, cases)
        error = {
            "code": "NOT_FOUND",
            "message": "Not Found",
            "requestId": "00000000-0000-4000-8000-000000000001",
        }
        denied = {**case, "status": 404, "response": "denied"}
        check_http(self.api, denied, {"denied": error})
        for update in (
            {"message": "search belongs to another service"},
            {"details": [{"path": "/service", "message": "search"}]},
        ):
            with self.assertRaises((ValueError, ValidationError)):
                check_http(self.api, denied, {"denied": {**error, **update}})

    def test_creation_cannot_assert_service_or_actor(self) -> None:
        request = json.loads((ROOT / "api/run-management/v1/examples/create.json").read_text())
        validator = schema_validator(self.api, "CreateRun")
        validator.validate(request)
        for name in ("service", "actor", "caller", "permissions"):
            self.assertFalse(validator.is_valid({**request, name: "forged"}))
