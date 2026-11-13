"""Exact evidence reads preserve bytes and independently retained associations."""

import base64
import copy
import hashlib
import json
import unittest
from typing import Any

from scripts.validate import ROOT


class EvidenceReadsTest(unittest.TestCase):
    def setUp(self):
        self.api = json.loads((ROOT / "api/run-management/v1/openapi.json").read_text())
        self.comparison = json.loads(
            (ROOT / "api/run-management/v1/comparison-cases.json").read_text()
        )
        self.run_id = self.comparison["runId"]
        self.reference = self.comparison["evidence"]["report"]
        self.raw = (ROOT / "examples/analysis/slo-pass-regression-fail.json").read_bytes()

    def headers(self, raw, **identity):
        return {
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(raw)),
            "Content-Digest": "sha-256=:"
            + base64.b64encode(hashlib.sha256(raw).digest()).decode()
            + ":",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Perfeng-Evidence-Media-Type": "application/json",
            "X-Perfeng-Evidence-Format": "analysis-result/v1",
            "X-Perfeng-Run-Id": self.run_id,
            **identity,
        }

    def check(self, raw=None, headers=None, **overrides):
        from scripts.evidence_reads import check_artifact_content

        inputs: dict[str, Any] = {
            "run_id": self.run_id,
            "artifact_id": self.reference["id"],
            "associated": {self.run_id: [self.reference]},
            "raw": self.raw if raw is None else raw,
            "headers": headers
            if headers is not None
            else self.headers(
                self.raw,
                **{
                    "X-Perfeng-Artifact-Id": self.reference["id"],
                    "X-Perfeng-Artifact-Run-Id": self.reference["runId"],
                },
            ),
        }
        inputs.update(overrides)
        return check_artifact_content(**inputs)

    def test_authenticated_bounded_identifier_only_operations(self):
        for path, operation in (
            ("/v1/runs/{runId}/artifacts/{artifactId}/content", "getRunArtifactContent"),
            ("/v1/runs/{runId}/policy/content", "getRunPolicyContent"),
        ):
            value = self.api["paths"][path]["get"]
            self.assertEqual(value["operationId"], operation)
            self.assertEqual(value["x-perfeng-service-permission"], "run:read")
            self.assertEqual(value["x-perfeng-max-response-bytes"], 1048576)
            self.assertNotIn("requestBody", value)
            self.assertEqual(
                set(value["responses"]),
                {"200", "400", "401", "403", "404", "422", "429", "500", "503"},
            )
        self.assertEqual(self.api["security"], [{"bearerAuth": []}])

    def test_original_report_and_explicit_historical_baseline_are_readable(self):
        self.check()
        reference = copy.deepcopy(self.comparison["evidence"]["native"]["baseline"]["artifact"])
        # Synthetic retained baseline: published examples do not include its original body.
        normalized = json.loads((ROOT / "examples/normalized-result/playwright.json").read_bytes())
        normalized["runId"] = reference["runId"]
        raw = json.dumps(normalized).encode()
        reference.update(sizeBytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        headers = self.headers(
            raw,
            **{
                "X-Perfeng-Artifact-Id": reference["id"],
                "X-Perfeng-Artifact-Run-Id": reference["runId"],
                "X-Perfeng-Evidence-Format": "normalized-result/v1",
            },
        )
        self.check(raw, headers, artifact_id=reference["id"], associated={self.run_id: [reference]})

    def test_substitution_requires_independent_binding_not_self_consistent_headers(self):
        with self.assertRaises(ValueError):
            self.check(associated={})
        with self.assertRaises(ValueError):
            self.check(run_id="perf-20260902-130000-ffffffff")
        foreign = "perf-20260902-130000-ffffffff"
        headers = self.headers(
            self.raw,
            **{
                "X-Perfeng-Run-Id": foreign,
                "X-Perfeng-Artifact-Id": self.reference["id"],
                "X-Perfeng-Artifact-Run-Id": self.reference["runId"],
            },
        )
        with self.assertRaises(ValueError):
            self.check(headers=headers, run_id=foreign)
        forged = self.raw + b" "
        headers = self.headers(
            forged,
            **{
                "X-Perfeng-Artifact-Id": self.reference["id"],
                "X-Perfeng-Artifact-Run-Id": self.reference["runId"],
            },
        )
        with self.assertRaises(ValueError):
            self.check(forged, headers)
        reference = copy.deepcopy(self.reference)
        reference["format"] = "raw/v1"
        with self.assertRaises(ValueError):
            self.check(associated={self.run_id: [reference]})

    def test_missing_or_unsafe_wire_metadata_is_rejected(self):
        original = self.headers(
            self.raw,
            **{
                "X-Perfeng-Artifact-Id": self.reference["id"],
                "X-Perfeng-Artifact-Run-Id": self.reference["runId"],
            },
        )
        for name in original:
            headers = {key: value for key, value in original.items() if key != name}
            with self.subTest(missing=name), self.assertRaises(ValueError):
                self.check(headers=headers)
        for name, value in (
            ("Content-Encoding", "gzip"),
            ("Content-Range", "bytes 0-1/2"),
            ("Location", "https://example.invalid/blob"),
            ("Content-Location", "s3://bucket/key"),
            ("content-length", str(len(self.raw))),
            ("Content-Length", "01"),
        ):
            with self.subTest(header=name), self.assertRaises(ValueError):
                self.check(headers={**original, name: value})
        with self.assertRaises(ValueError):
            self.check(raw=b"x" * 1048577)

    def test_policy_requires_exact_report_used_identity_and_bytes(self):
        from scripts.evidence_reads import check_policy_content

        raw = (ROOT / "examples/policy/browser.json").read_bytes()
        policy = self.comparison["evidence"]["native"]["policy"]
        headers = self.headers(
            raw,
            **{
                "X-Perfeng-Evidence-Format": "policy/v1",
                "X-Perfeng-Policy-Id": policy["id"],
                "X-Perfeng-Policy-Version": policy["version"],
            },
        )
        inputs: dict[str, Any] = {
            "run_id": self.run_id,
            "policies": {self.run_id: policy},
            "raw": raw,
            "headers": headers,
        }
        check_policy_content(**inputs)
        foreign = "perf-20260902-130000-ffffffff"
        with self.assertRaises(ValueError):
            check_policy_content(
                run_id=foreign,
                policies={self.run_id: policy},
                raw=raw,
                headers={**headers, "X-Perfeng-Run-Id": foreign},
            )
        for overrides in (
            {"policies": {}},
            {"raw": raw + b" "},
            {"policies": {self.run_id: {**policy, "version": "2.0.0"}}},
            {"policies": {self.run_id: {**policy, "sha256": "a" * 64}}},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                changed: dict[str, Any] = dict(inputs)
                changed.update(overrides)
                check_policy_content(**changed)
