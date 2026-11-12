"""Comparison is historical evidence, not a new lifecycle or verdict engine."""

import copy
import hashlib
import json
import unittest
from typing import Any

from scripts.validate import ROOT, load_contracts
from scripts.validate_api import check_http, schema_validator


class RunComparisonTest(unittest.TestCase):
    def setUp(self):
        self.api = json.loads((ROOT / "api/run-management/v1/openapi.json").read_text())
        _, self.validators = load_contracts()

    def fixture(self):
        publication = json.loads(
            (ROOT / "examples/performance-analysis/published.json").read_text()
        )
        request = json.loads((ROOT / "api/run-management/v1/examples/create.json").read_text())
        native = publication["data"]["native"]
        request.update(testSuite=native["testId"], policy=native["policy"])
        run = {"id": native["runId"], "request": request}
        return {
            "available": json.loads(
                (ROOT / "api/run-management/v1/comparison-cases.json").read_text()
            ),
            "run": run,
            "native": native,
            "reportArtifact": publication["data"]["artifact"],
            "publication": publication,
        }

    def test_exact_read_is_authenticated_bounded_and_not_a_lifecycle_transition(self):
        path = self.api["paths"]["/v1/runs/{runId}/comparison"]
        self.assertEqual(set(path), {"parameters", "get"})
        self.assertEqual(path["get"]["operationId"], "getRunComparison")
        self.assertEqual(path["get"]["x-perfeng-service-permission"], "run:read")
        self.assertEqual(path["get"]["x-perfeng-max-response-bytes"], 2097152)
        self.assertNotIn("requestBody", path["get"])
        self.assertEqual(self.api["security"], [{"bearerAuth": []}])

    def test_availability_never_masquerades_as_a_performance_verdict(self):
        fixture = self.fixture()
        validator = schema_validator(self.api, "RunComparison")
        validator.validate(fixture["available"])
        for status in ("INCOMPLETE", "INACCESSIBLE"):
            value = {
                "schemaVersion": 1,
                "kind": "RunComparison",
                "runId": fixture["run"]["id"],
                "status": status,
            }
            validator.validate(value)
            for name in ("evidence", "verdict", "overallPass", "request"):
                self.assertFalse(
                    validator.is_valid({**value, name: fixture["available"].get(name, "PASS")})
                )
        case: dict[str, Any] = {
            "operationId": "getRunComparison",
            "status": 200,
            "response": "available",
            "pathParameters": {"runId": fixture["run"]["id"]},
            "headers": {"Cache-Control": "no-store"},
        }
        check_http(self.api, case, fixture)
        foreign = copy.deepcopy(case)
        foreign["pathParameters"]["runId"] = "perf-20260902-130000-ffffffff"
        with self.assertRaises(ValueError):
            check_http(self.api, foreign, fixture)

    def check(self, value, fixture, **overrides):
        from scripts.run_comparison import check_comparison

        schema_validator(self.api, "RunComparison").validate(value)
        policy_bytes = (ROOT / "examples/policy/browser.json").read_bytes()
        self.validators["policy/v1"].validate(json.loads(policy_bytes))
        inputs: dict[str, Any] = {
            "run": fixture["run"],
            "native": fixture["native"],
            "report_artifact": fixture["reportArtifact"],
            "analysis_bytes": (
                ROOT / "examples/analysis/slo-pass-regression-fail.json"
            ).read_bytes(),
            "policy_bytes": policy_bytes,
            "publication": fixture["publication"],
        }
        check_comparison(value, **{**inputs, **overrides})

    def test_exact_report_and_policy_preserve_independent_outcomes(self):
        fixture = self.fixture()
        self.check(fixture["available"], fixture)
        self.check(fixture["available"], fixture, previous=copy.deepcopy(fixture["available"]))
        analysis = fixture["available"]["evidence"]["analysis"]
        self.assertEqual(analysis["evaluations"][0]["slo"]["status"], "PASS")
        self.assertEqual(analysis["evaluations"][0]["regression"]["status"], "FAIL")
        self.assertFalse(analysis["blocking"])
        native_only = copy.deepcopy(fixture["available"])
        native_only["evidence"]["publication"] = None
        self.check(native_only, fixture, publication=None)

    def test_schema_valid_substitutions_are_rejected(self):
        fixture = self.fixture()
        for path, replacement in (
            (("runId",), "perf-20260902-130000-ffffffff"),
            (("request", "candidate", "gitSha"), "a" * 40),
            (("request", "profile"), "stress"),
            (("request", "candidate", "image"), "ghcr.io/example/sample-api@sha256:" + "a" * 64),
            (("request", "policy", "sha256"), "a" * 64),
            (("evidence", "native", "baseline", "artifact", "sha256"), "a" * 64),
            (
                ("evidence", "analysis", "candidateArtifact", "runId"),
                "perf-20260902-130000-ffffffff",
            ),
            (("evidence", "analysis", "evaluations", 0, "quality", "status"), "INCONCLUSIVE"),
            (("evidence", "native", "baseline", "identity", "version"), "2.0.0"),
            (("evidence", "report", "sha256"), "a" * 64),
            (("evidence", "analysis", "evaluations", 0, "metric", "unit"), "s"),
            (("evidence", "directions", 0, "direction"), "higher-is-better"),
            (("evidence", "publication", "id"), "substituted-event"),
        ):
            value = copy.deepcopy(fixture["available"])
            parent = value
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = replacement
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.check(value, fixture)
        with self.assertRaises(ValueError):
            self.check(fixture["available"], fixture, analysis_bytes=b"{}")
        with self.assertRaises(ValueError):
            self.check(fixture["available"], fixture, policy_bytes=b"{}")

    def test_inconclusive_report_is_available_evidence_not_an_availability_failure(self):
        fixture = self.fixture()
        raw = (ROOT / "examples/analysis/missing-reference.json").read_bytes()
        value = copy.deepcopy(fixture["available"])
        reference = {
            **fixture["reportArtifact"],
            "id": "77777777-7777-4777-8777-777777777777",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "sizeBytes": len(raw),
        }
        value["evidence"].update(analysis=json.loads(raw), report=reference, publication=None)
        self.check(value, fixture, analysis_bytes=raw, report_artifact=reference, publication=None)
        self.assertEqual(value["status"], "AVAILABLE")
        self.assertEqual(
            value["evidence"]["analysis"]["evaluations"][0]["regression"]["status"], "INCONCLUSIVE"
        )
        changed = copy.deepcopy(fixture["available"])
        changed["evidence"]["publication"] = None
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.check(changed, fixture, publication=None, previous=fixture["available"])

    def test_direction_count_and_response_size_are_bounded(self):
        fixture = self.fixture()
        value = copy.deepcopy(fixture["available"])
        value["evidence"]["directions"] *= 1001
        self.assertFalse(schema_validator(self.api, "RunComparison").is_valid(value))
        value = copy.deepcopy(fixture["available"])
        value["evidence"]["analysis"]["evaluations"][0]["regression"]["reasons"] = ["x" * 2097152]
        with self.assertRaisesRegex(ValueError, "2 MiB"):
            self.check(value, fixture)
