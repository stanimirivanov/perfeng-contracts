"""Baseline identity, evidence, qualification, and lifecycle contracts."""

import copy
import unittest
from typing import Any, ClassVar

from jsonschema import Draft202012Validator

from scripts.validate import (
    ROOT,
    check_baseline_consistency,
    load_contracts,
    read_json,
)


class BaselineContractsTest(unittest.TestCase):
    validators: ClassVar[dict[str, Draft202012Validator]]

    @classmethod
    def setUpClass(cls) -> None:
        _, cls.validators = load_contracts()

    def baseline(self, name: str = "approved") -> dict[str, Any]:
        return read_json(ROOT / f"examples/baseline/{name}.json")

    def assert_semantically_invalid(self, baseline: dict[str, Any], message: str) -> None:
        self.validators["baseline/v1"].validate(baseline)
        with self.assertRaisesRegex(ValueError, message):
            check_baseline_consistency(baseline)

    def test_candidate_and_approved_examples(self) -> None:
        for name, state, qualification in (
            ("candidate", "CANDIDATE", "PENDING"),
            ("approved", "APPROVED", "PASSED"),
        ):
            with self.subTest(name=name):
                baseline = self.baseline(name)
                self.validators["baseline/v1"].validate(baseline)
                check_baseline_consistency(baseline)
                self.assertEqual(baseline["state"], state)
                self.assertEqual(baseline["qualification"]["status"], qualification)

    def test_baseline_requires_normalized_immutable_evidence(self) -> None:
        for path, value in (
            (("artifact", "kind"), "raw"),
            (("artifact", "format"), "analysis-result/v1"),
            (("artifact", "mediaType"), "text/plain"),
            (("artifact", "sha256"), "bad"),
            (("environment", "fingerprint"), "bad"),
            (("software", "gitSha"), "abc"),
            (("software", "image"), "ghcr.io/example/search:latest"),
        ):
            with self.subTest(path=path):
                baseline = self.baseline()
                baseline[path[0]][path[1]] = value
                self.assertFalse(self.validators["baseline/v1"].is_valid(baseline))

    def test_artifact_must_belong_to_source_run(self) -> None:
        baseline = self.baseline()
        baseline["sourceRunId"] = "perf-20260902-130000-deadbeef"
        self.assert_semantically_invalid(baseline, "source run")

    def test_lifecycle_starts_at_candidate_and_matches_current_state(self) -> None:
        baseline = self.baseline()
        baseline["lifecycle"][0]["state"] = "QUALIFIED"
        self.assert_semantically_invalid(baseline, "start at CANDIDATE")

        baseline = self.baseline()
        baseline["state"] = "QUALIFIED"
        self.assert_semantically_invalid(baseline, "last lifecycle event")

        baseline = self.baseline()
        baseline["createdAt"] = "2026-09-01T13:04:00Z"
        self.assert_semantically_invalid(baseline, "creation time")

        baseline = self.baseline()
        baseline["revision"] = 4
        self.assert_semantically_invalid(baseline, "revision")

    def test_lifecycle_rejects_skips_reversal_and_reordered_time(self) -> None:
        for mutate in (
            lambda b: b["lifecycle"].pop(1),
            lambda b: b["lifecycle"].append(
                {
                    "state": "QUALIFIED",
                    "at": "2026-09-01T16:00:00Z",
                    "actor": "performance-team",
                    "reason": "Attempted reversal.",
                }
            ),
            lambda b: b["lifecycle"].__setitem__(
                2,
                {
                    **b["lifecycle"][2],
                    "at": "2026-09-01T13:30:00Z",
                },
            ),
        ):
            baseline = self.baseline()
            mutate(baseline)
            baseline["revision"] = len(baseline["lifecycle"])
            baseline["state"] = baseline["lifecycle"][-1]["state"]
            with self.subTest(states=[event["state"] for event in baseline["lifecycle"]]):
                self.assert_semantically_invalid(baseline, "transition|timestamps")

    def test_qualification_controls_usable_states(self) -> None:
        baseline = self.baseline()
        baseline["qualification"] = {"status": "FAILED", "reasons": ["Too variable."]}
        self.assert_semantically_invalid(baseline, "must pass qualification")

        candidate = self.baseline("candidate")
        candidate["qualification"] = {
            "status": "PASSED",
            "reasons": [],
            "sampleCount": 20,
            "maximumCv": 0.1,
        }
        self.assert_semantically_invalid(candidate, "must advance")

    def test_passed_and_failed_qualification_requires_evidence(self) -> None:
        baseline = self.baseline()
        del baseline["qualification"]["sampleCount"]
        self.assertFalse(self.validators["baseline/v1"].is_valid(baseline))

        candidate = self.baseline("candidate")
        candidate["qualification"] = {"status": "FAILED", "reasons": []}
        self.assertFalse(self.validators["baseline/v1"].is_valid(candidate))

    def test_lifecycle_actor_and_reason_are_mandatory(self) -> None:
        for field, value in (("actor", ""), ("reason", " ")):
            baseline = self.baseline()
            baseline["lifecycle"][-1][field] = value
            self.assertFalse(self.validators["baseline/v1"].is_valid(baseline))

    def test_baseline_versions_are_independent_anchors(self) -> None:
        approved = self.baseline()
        candidate = self.baseline("candidate")
        self.assertEqual(approved["id"], candidate["id"])
        self.assertNotEqual(approved["version"], candidate["version"])
        self.assertNotEqual(approved["artifact"], candidate["artifact"])

        changed = copy.deepcopy(approved)
        changed["version"] = candidate["version"]
        self.validators["baseline/v1"].validate(changed)
        check_baseline_consistency(changed)


if __name__ == "__main__":
    unittest.main()
