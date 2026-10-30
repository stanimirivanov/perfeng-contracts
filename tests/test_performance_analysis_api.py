"""Read-only HTTP analysis publication conformance with independent scope."""

import copy
import unittest

from jsonschema import Draft202012Validator

from scripts.performance_analysis import check_read_scope
from scripts.validate import ROOT, load_contracts, read_json
from scripts.validate_api import schema_validator

PATH = "/integration/v1/requests/{requestId}/analysis"
PROVIDER = "https://provider.example/identity"
PRINCIPAL = {"issuer": "https://auth.example/tenant", "id": "argus-service"}
REQUEST = {"issuer": "https://argus.example/identity", "id": "request-1"}


class AnalysisReadAPITest(unittest.TestCase):
    def setUp(self):
        self.api = read_json(ROOT / "api/performance-integration/v1/openapi.json")
        self.message = read_json(ROOT / "examples/performance-analysis/published.json")

    def test_read_operation_is_scoped_authenticated_and_not_a_mutation(self):
        resource = self.api["paths"][PATH]
        self.assertEqual(set(resource), {"parameters", "get"})
        self.assertEqual(self.api["security"], [{"bearerAuth": []}])
        self.assertNotIn("security", resource["get"])
        self.assertNotIn("requestBody", resource["get"])
        self.assertEqual(
            [(p["name"], p["in"], p["required"]) for p in resource["parameters"]],
            [("requestId", "path", True), ("issuer", "query", True)],
        )
        responses = resource["get"]["responses"]
        self.assertEqual(set(responses), {"200", "400", "401", "403", "404", "429", "503"})
        for response in responses.values():
            self.assertEqual(response["headers"]["Cache-Control"]["schema"]["const"], "no-store")
            self.assertTrue(response["headers"]["Cache-Control"]["required"])
        for status in ("429", "503"):
            self.assertEqual(responses[status]["headers"]["Retry-After"]["schema"]["minimum"], 1)
            self.assertTrue(responses[status]["headers"]["Retry-After"]["required"])
        self.assertEqual(
            responses["401"]["headers"]["WWW-Authenticate"]["schema"]["const"], "Bearer"
        )
        self.assertEqual(
            responses["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/AnalysisPublication",
        )

    def test_publication_response_stays_separate_and_closed(self):
        schema = schema_validator(self.api, "AnalysisPublication")
        schema.validate(self.message)
        _, validators = load_contracts()
        self.assertFalse(validators["performance-integration/v1"].is_valid(self.message))
        for name in ("Request", "Accepted", "Lifecycle"):
            self.assertFalse(schema_validator(self.api, name).is_valid(self.message))
        for message in read_json(ROOT / "examples/performance-integration/completed.json"):
            self.assertFalse(schema.is_valid(message))
        changed = copy.deepcopy(self.message)
        changed["credential"] = "injected"
        self.assertFalse(schema.is_valid(changed))

    def test_decoded_request_id_is_nonblank_and_bounded(self):
        schema = self.api["paths"][PATH]["parameters"][0]["schema"]
        identity = Draft202012Validator(schema)
        self.assertTrue(identity.is_valid("opaque/request"))
        for invalid in ("", "   ", "x" * 257):
            self.assertFalse(identity.is_valid(invalid))

    def test_read_errors_have_status_bound_codes_and_uniform_absence(self):
        responses = self.api["paths"][PATH]["get"]["responses"]
        codes = {
            "400": "invalid_request",
            "401": "unauthenticated",
            "403": "forbidden",
            "404": "unknown_request",
            "429": "rate_limited",
            "503": "unavailable",
        }
        for status, code in codes.items():
            schema = responses[status]["content"]["application/json"]["schema"]
            validator = schema_validator(self.api, "Error").evolve(schema=schema)
            validator.validate(
                {"code": code, "message": "Not Found" if status == "404" else "Error"}
            )
            self.assertFalse(validator.is_valid({"code": "expired", "message": "Error"}))
            if status == "404":
                self.assertFalse(validator.is_valid({"code": code, "message": "Not published yet"}))
                self.assertFalse(
                    validator.is_valid({"code": code, "message": "Not Found", "owner": "other"})
                )

    def test_response_cannot_supply_its_own_authenticated_scope(self):
        check_read_scope(self.message, provider=PROVIDER, principal=PRINCIPAL, request=REQUEST)
        for mode in ("provider", "principal", "request-id", "request-issuer"):
            with self.subTest(mode=mode):
                changed = copy.deepcopy(self.message)
                if mode == "provider":
                    changed["source"] = changed["data"]["run"]["issuer"] = "https://other.example"
                elif mode == "principal":
                    changed["data"]["context"]["principal"]["id"] = "other"
                elif mode == "request-id":
                    changed["data"]["context"]["request"]["id"] = "other"
                else:
                    changed["data"]["context"]["request"]["issuer"] = "https://other.example"
                schema_validator(self.api, "AnalysisPublication").validate(changed)
                with self.assertRaisesRegex(ValueError, "scope"):
                    check_read_scope(
                        changed, provider=PROVIDER, principal=PRINCIPAL, request=REQUEST
                    )
