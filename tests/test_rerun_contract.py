"""Attribution and frozen selection are checked against independent provider evidence."""

import copy
import json
import unittest
from typing import Any

from scripts.validate import ROOT
from scripts.validate_api import check_http, schema_validator


class RerunContractTest(unittest.TestCase):
    def setUp(self):
        self.api = json.loads((ROOT / "api/run-management/v1/openapi.json").read_text())
        self.cases = json.loads((ROOT / "api/run-management/v1/rerun-cases.json").read_text())

    def test_rerun_and_recovery_are_authenticated_distinct_operations(self):
        path = self.api["paths"]["/v1/runs/{runId}/reruns"]
        self.assertEqual(path["post"]["operationId"], "rerunRun")
        self.assertEqual(path["get"]["operationId"], "resolveRunRerun")
        self.assertEqual(path["post"]["x-perfeng-service-permission"], "run:rerun")
        self.assertEqual(path["get"]["x-perfeng-service-permission"], "run:read")
        self.assertEqual(self.api["security"], [{"bearerAuth": []}])
        self.assertNotIn("requestBody", path["get"])
        for operation in (path["post"], path["get"]):
            self.assertEqual(operation["x-perfeng-max-response-bytes"], 65536)

    def test_closed_schemas_and_http_success_conflict_denial_and_withdrawal(self):
        for case in self.cases["http"]:
            with self.subTest(case=case["name"]):
                check_http(self.api, case, self.cases)
        for schema, name in (("RerunRequest", "request"), ("RerunReceipt", "receipt")):
            value = copy.deepcopy(self.cases[name])
            validator = schema_validator(self.api, schema)
            validator.validate(value)
            for field in ("actor", "actorOverride", "targetUrl", "bearerToken"):
                self.assertFalse(validator.is_valid({**value, field: "untrusted"}))
        receipt = self.cases["receipt"]
        self.assertFalse(
            schema_validator(self.api, "RerunReceipt").is_valid({**receipt, "decision": "DENIED"})
        )
        with self.assertRaises(ValueError):
            check_http(self.api, {**self.cases["http"][0], "headers": {}}, self.cases)

    def test_retention_and_size_bounds_do_not_allow_a_plausible_receipt(self):
        shortened = copy.deepcopy(self.cases["receipt"])
        shortened["idempotencyKeyExpiresAt"] = "2026-09-04T11:59:59Z"
        with self.assertRaises(ValueError):
            self.check_receipt(shortened, expires_at=shortened["idempotencyKeyExpiresAt"])
        oversized = copy.deepcopy(self.cases["receipt"])
        oversized["request"]["reason"] = "x" * 65536
        with self.assertRaises(ValueError):
            self.check_receipt(oversized, request=oversized["request"])
        request = copy.deepcopy(self.cases["request"])
        request["reason"] = " "
        self.assertFalse(schema_validator(self.api, "RerunRequest").is_valid(request))
        for malformed in (b'{"reason":"one","reason":"two"}', b'{"number":NaN}'):
            from scripts.validate_api import parse_request

            with self.assertRaises(ValueError):
                parse_request(malformed)

    def test_http_identity_cache_and_exact_lookup_cannot_drift(self):
        for name in ("accepted", "recovered", "forbidden"):
            case = copy.deepcopy(
                next(value for value in self.cases["http"] if value["name"] == name)
            )
            case["headers"].pop("Cache-Control")
            with self.subTest(name=name), self.assertRaises(ValueError):
                check_http(self.api, case, self.cases)
        accepted = self.cases["http"][0]
        for overrides in (
            {"pathParameters": {"runId": "perf-20260902-130000-ffffffff"}},
            {"requestHeaders": {"Idempotency-Key": "different-intent-1234"}},
            {"queryParameters": {"url": "https://example.invalid"}},
            {
                "headers": {
                    **accepted["headers"],
                    "Location": "/v1/runs/" + self.cases["receipt"]["sourceRunId"],
                }
            },
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                check_http(self.api, {**accepted, **overrides}, self.cases)
        recovered = next(value for value in self.cases["http"] if value["name"] == "recovered")
        with self.assertRaises(ValueError):
            check_http(
                self.api,
                {**recovered, "queryParameters": {**recovered["queryParameters"], "unknown": "1"}},
                self.cases,
            )

    def check_receipt(self, value=None, **overrides):
        from scripts.rerun import check_receipt

        inputs: dict[str, Any] = copy.deepcopy(self.cases["trusted"])
        inputs["source"] = json.loads(
            (ROOT / "api/run-management/v1/comparison-cases.json").read_text()
        )
        inputs.update(overrides)
        check_receipt(self.cases["receipt"] if value is None else value, **inputs)

    def test_accepted_intent_binds_actor_service_source_child_and_exact_selection(self):
        self.check_receipt()
        for path, replacement in (
            (("actor", "id"), "another-engineer"),
            (("caller", "id"), "untrusted-client"),
            (("service", "id"), "another-service"),
            (("sourceCreatedBy", "id"), "another-pipeline"),
            (("sourceRunId",), "perf-20260902-130000-ffffffff"),
            (("runId",), self.cases["receipt"]["sourceRunId"]),
            (("selection", "policy", "sha256"), "a" * 64),
            (("native", "baseline", "identity", "version"), "2.0.0"),
            (("request", "reason"), "Changed after acceptance"),
            (("acceptedAt",), "2026-09-03T12:01:00Z"),
            (("idempotencyKey",), "different-intent-1234"),
        ):
            value = copy.deepcopy(self.cases["receipt"])
            parent = value
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = replacement
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.check_receipt(value)

    def test_recovery_rechecks_read_authority_and_preserves_original_caller(self):
        self.check_receipt(grants=["run:read"], recovery=True)
        for overrides in (
            {"grants": ["run:read"]},
            {"grants": ["run:rerun"]},
            {"grants": ["run:create", "baseline:approve"]},
            {
                "current_actor": {
                    "issuer": "https://identity.example",
                    "id": "another",
                    "kind": "HUMAN",
                }
            },
            {"grant_service": {"issuer": "https://catalog.example/services", "id": "billing"}},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.check_receipt(**overrides)

    def test_idempotency_conflicts_are_actor_and_operation_scoped_and_explicit(self):
        from scripts.rerun import check_intent_retry

        stored = self.cases["trusted"]
        inputs = {
            "stored": stored,
            "actor": stored["actor"],
            "key": stored["key"],
            "source_run_id": stored["source_run_id"],
            "request": self.cases["request"],
            "now": "2026-09-03T12:00:00Z",
        }
        self.assertEqual(check_intent_retry(**inputs), "REPLAY")
        for overrides, expected in (
            (
                {"request": {**self.cases["request"], "reason": "Different intent"}},
                "IDEMPOTENCY_CONFLICT",
            ),
            ({"source_run_id": "perf-20260902-130000-ffffffff"}, "IDEMPOTENCY_CONFLICT"),
            ({"now": "2026-09-04T12:00:00Z"}, "IDEMPOTENCY_CONFLICT"),
            ({"key": "new-intent-123456"}, "NEW"),
            ({"actor": {**stored["actor"], "id": "different"}}, "NEW"),
        ):
            with self.subTest(overrides=overrides):
                arguments: dict[str, Any] = dict(inputs)
                arguments.update(overrides)
                self.assertEqual(check_intent_retry(**arguments), expected)
        replay = copy.deepcopy(self.cases["receipt"])
        replay["id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        with self.assertRaises(ValueError):
            self.check_receipt(previous=replay)

    def test_selection_failures_are_never_accepted_by_substitution(self):
        from scripts.rerun import check_selection

        for case in self.cases["selectionChecks"]:
            with self.subTest(case=case["name"]):
                inputs: dict[str, Any] = copy.deepcopy(self.cases["selectionInputs"])
                inputs["source"] = json.loads(
                    (ROOT / "api/run-management/v1/comparison-cases.json").read_text()
                )
                inputs.update(case["overrides"])
                self.assertEqual(check_selection(**inputs), case["expected"])
