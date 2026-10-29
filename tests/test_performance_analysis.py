"""Request-linked analysis conformance requires independent admission evidence."""

import copy
import hashlib
import json
import unittest

from scripts.performance_analysis import check_binding, check_reference
from scripts.validate import ROOT, check_analysis_consistency, load_contracts, read_json

PROVIDER = "https://provider.example/identity"
PRINCIPAL = {"issuer": "https://auth.example/tenant", "id": "argus-service"}


class AnalysisPublicationTest(unittest.TestCase):
    def setUp(self):
        _, self.validators = load_contracts()
        self.message = read_json(ROOT / "examples/performance-analysis/published.json")
        self.admission = read_json(ROOT / "examples/performance-integration/completed.json")[1]
        self.admission["data"]["context"]["requestedAt"] = "2026-09-02T13:00:00Z"
        self.admission["data"]["context"]["deadline"] = "2026-09-02T13:01:00Z"
        self.admission["time"] = "2026-09-02T13:00:01Z"
        self.native = copy.deepcopy(self.message["data"]["native"])
        self.raw = (ROOT / "examples/analysis/slo-pass-regression-fail.json").read_bytes()

    def check(self, message, raw=None, **scope):
        raw = self.raw if raw is None else raw
        self.validators["performance-analysis/v1"].validate(message)
        analysis = json.loads(raw)
        self.validators["analysis/v1"].validate(analysis)
        policy_bytes = scope.get(
            "policy_bytes", (ROOT / "examples/policy/browser.json").read_bytes()
        )
        policy = json.loads(policy_bytes)
        self.validators["policy/v1"].validate(policy)
        check_analysis_consistency(analysis, policy)
        check_binding(
            message,
            self.admission,
            self.native,
            analysis,
            raw,
            policy_bytes,
            provider=scope.get("provider", PROVIDER),
            principal=scope.get("principal", PRINCIPAL),
            previous=scope.get("previous"),
        )

    def test_exact_publication_replay_and_late_independent_outcomes(self):
        self.check(self.message)
        self.check(copy.deepcopy(self.message))
        self.check(self.message, previous=copy.deepcopy(self.message))
        self.assertGreater(self.message["time"], self.message["data"]["context"]["deadline"])
        raw = (ROOT / "examples/analysis/missing-reference.json").read_bytes()
        changed = copy.deepcopy(self.message)
        changed["data"]["artifact"].update(
            sha256=hashlib.sha256(raw).hexdigest(), sizeBytes=len(raw)
        )
        self.check(changed, raw)
        with self.assertRaisesRegex(ValueError, "Conflicting immutable"):
            self.check(changed, raw, previous=self.message)

    def test_untrusted_scope_and_substituted_admission_or_native_binding(self):
        for scope in (
            {"provider": "https://other.example"},
            {"principal": {**PRINCIPAL, "id": "other"}},
        ):
            with self.assertRaises(ValueError):
                self.check(self.message, **scope)
        for path in (
            ("context", "attempt", "id"),
            ("context", "policy", "sha256"),
            ("run", "id"),
            ("native", "workload", "id"),
            ("native", "policy", "version"),
            ("native", "baseline", "identity", "version"),
        ):
            changed = copy.deepcopy(self.message)
            parent = changed["data"]
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = (
                "b" * 64 if path[-1] == "sha256" else ("other" if path[-1] == "id" else "2.0.0")
            )
            with self.assertRaises(ValueError, msg=str(path)):
                self.check(changed)

    def test_byte_identity_and_native_report_associations(self):
        with self.assertRaises(ValueError):
            self.check(self.message, self.raw + b" ")
        for field, value in (("runId", "perf-20260902-130000-ffffffff"), ("testId", "other")):
            report = json.loads(self.raw)
            report[field] = value
            if field == "runId":
                report["candidateArtifact"]["runId"] = value
            raw = json.dumps(report).encode()
            changed = copy.deepcopy(self.message)
            changed["data"]["artifact"].update(
                sha256=hashlib.sha256(raw).hexdigest(), sizeBytes=len(raw)
            )
            with self.assertRaises(ValueError):
                self.check(changed, raw)
        changed = copy.deepcopy(self.message)
        changed["data"]["native"]["baseline"] = None
        with self.assertRaises(ValueError):
            check_reference(changed)
        changed["data"]["context"]["baseline"] = None
        check_reference(changed)

    def test_foreign_baseline_bytes_duplicate_json_and_future_reports(self):
        for mode in ("baseline", "duplicate", "future"):
            report = json.loads(self.raw)
            if mode == "baseline":
                report["referenceArtifacts"][0]["uri"] = "https://other.example/result.json"
            if mode == "future":
                report["createdAt"] = "2026-09-02T13:04:00Z"
            raw = json.dumps(report).encode()
            if mode == "duplicate":
                raw = b'{"schemaVersion":1,' + raw[1:]
            changed = copy.deepcopy(self.message)
            changed["data"]["artifact"].update(
                sha256=hashlib.sha256(raw).hexdigest(), sizeBytes=len(raw)
            )
            with self.assertRaises(ValueError, msg=mode):
                self.check(changed, raw)

    def test_policy_baseline_must_match_even_when_published_binding_matches_admission(self):
        self.native["baseline"]["identity"]["id"] = "other-baseline"
        self.message["data"]["native"] = copy.deepcopy(self.native)
        with self.assertRaisesRegex(ValueError, "Policy comparison"):
            self.check(self.message)

    def test_no_baseline_is_valid_for_slo_only_policy(self):
        policy = read_json(ROOT / "examples/policy/browser.json")
        del policy["spec"]["rules"][0]["regression"]
        policy_bytes = json.dumps(policy).encode()
        self.native["policy"]["sha256"] = hashlib.sha256(policy_bytes).hexdigest()
        self.native["baseline"] = None
        self.admission["data"]["context"]["baseline"] = None
        self.message["data"]["context"]["baseline"] = None
        self.message["data"]["native"] = copy.deepcopy(self.native)
        report = json.loads(self.raw)
        report["policy"]["sha256"] = self.native["policy"]["sha256"]
        report["referenceArtifacts"] = []
        report["evaluations"][0]["regression"] = {
            "status": "NOT_EVALUATED",
            "reasons": ["not configured"],
        }
        raw = json.dumps(report).encode()
        self.message["data"]["artifact"].update(
            sha256=hashlib.sha256(raw).hexdigest(), sizeBytes=len(raw)
        )
        self.check(self.message, raw, policy_bytes=policy_bytes)
