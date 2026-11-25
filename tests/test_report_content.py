"""Offline report-only read cases use independent native registration and original bytes."""

import hashlib
import json
import unittest
from typing import Any

from scripts.evidence_reads import check_artifact_content, report_content_status
from scripts.validate import ROOT, load_contracts, manifest_member


class ReportContentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_contracts()[1]["analysis/v1"]

    def setUp(self):
        fixture = json.loads((ROOT / "tests/fixtures/report-content/cases.json").read_text())
        self.run_id = fixture["runId"]
        self.retained_run = fixture["run"]
        self.reference = self.retained_run["registrations"][0]
        self.authority = fixture["authority"]
        self.raw = manifest_member(ROOT, fixture["body"], "examples").read_bytes()
        self.fixture = fixture
        self.inputs: dict[str, Any] = {
            "run_id": self.run_id,
            "artifact_id": fixture["artifactId"],
            "runs": {self.run_id: self.retained_run},
            "authority": self.authority,
            "raw": self.raw,
            "validator": self.validator,
        }

    def outcome(self, **overrides):
        return report_content_status(**{**self.inputs, **overrides})

    def test_only_original_bytes_match_independent_native_registration(self):
        self.assertEqual(self.outcome(), 200)
        check_artifact_content(
            run_id=self.run_id,
            artifact_id=self.fixture["artifactId"],
            associated={self.run_id: self.retained_run["registrations"]},
            raw=self.raw,
            headers=self.fixture["headers"],
        )
        reserialized = json.dumps(json.loads(self.raw)).encode()
        self.assertEqual(self.outcome(raw=reserialized), 503)
        changed = self.raw.replace(b"search-browser", b"search-changed", 1)
        self.assertEqual(len(changed), len(self.raw))
        self.assertEqual(self.outcome(raw=changed), 503)

    def test_authority_precedes_disclosure(self):
        self.assertEqual(self.outcome(authority=None, runs={}), 401)
        self.assertEqual(
            self.outcome(authority={**self.authority, "operationAllowed": False}, runs={}), 403
        )
        for case in self.fixture["authorityCases"]:
            with self.subTest(case=case["name"]):
                self.assertEqual(
                    self.outcome(authority={**self.authority, **case["override"]}), case["status"]
                )
        self.assertEqual(self.outcome(runs={}), 404)

    def test_legacy_current_principal_must_own_selected_run(self):
        run = {"legacyPrincipal": "principal-1", "registrations": [self.reference]}
        authority = {"operationAllowed": True, "mode": "legacy", "legacyPrincipal": "principal-1"}
        for principal, expected in (("principal-1", 200), ("principal-2", 404)):
            with self.subTest(principal=principal):
                self.assertEqual(
                    self.outcome(
                        runs={self.run_id: run},
                        authority={**authority, "legacyPrincipal": principal},
                    ),
                    expected,
                )
        self.assertEqual(self.outcome(runs={self.run_id: run}), 404)
        self.assertEqual(self.outcome(authority=authority), 404)
        # Even matching identities in both namespaces must never authorize fallback.
        both = {**self.authority, **authority}
        self.assertEqual(self.outcome(authority=both), 404)
        self.assertEqual(
            self.outcome(runs={self.run_id: run}, authority={**both, "mode": "service"}), 404
        )

    def test_missing_ambiguous_and_ineligible_registrations_are_hidden(self):
        for registrations in ([], [self.reference, self.reference]):
            run = {**self.retained_run, "registrations": registrations}
            self.assertEqual(self.outcome(runs={self.run_id: run}, raw=None), 404)
        for case in self.fixture["registrationCases"]:
            registration = {**self.reference, **case["override"]}
            run = {**self.retained_run, "registrations": [registration]}
            with self.subTest(case=case["name"]):
                self.assertEqual(self.outcome(runs={self.run_id: run}), case["status"])

    def register_original(self, raw):
        self.reference.update(sizeBytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

    def test_storage_failure_advertised_size_and_runtime_overflow(self):
        self.assertEqual(self.outcome(raw=None), 503)
        at_limit = self.raw.ljust(1048576, b" ")
        self.register_original(at_limit)
        self.assertEqual(self.outcome(raw=at_limit), 200)
        self.assertEqual(self.outcome(raw=at_limit + b" "), 503)
        self.reference["sizeBytes"] += 1
        self.assertEqual(self.outcome(raw=None), 422)
        self.assertEqual(
            self.outcome(authority={**self.authority, "permissions": []}, raw=None), 404
        )

    def test_matching_bytes_still_require_a_complete_valid_report_for_the_run(self):
        foreign = "perf-20260901-130000-a1b2c3d5"
        duplicate_run_id = b'{"runId":"foreign",' + self.raw[1:]
        invalid = [b"", b"{", b"\xff", duplicate_run_id]
        for field in ("runId", "candidateArtifact", "producer"):
            report = json.loads(self.raw)
            if field == "runId":
                report[field] = foreign
            elif field == "candidateArtifact":
                report[field]["runId"] = foreign
            else:
                del report[field]["version"]
            invalid.append(json.dumps(report).encode())
        for raw in invalid:
            with self.subTest(raw=raw[:40]):
                self.register_original(raw)
                self.assertEqual(self.outcome(raw=raw), 503)
