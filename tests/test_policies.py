"""Policy/report conformance, including the cases that must not become PASS."""

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import Any, ClassVar

from jsonschema import Draft202012Validator

from scripts.validate import (
    ROOT,
    check_analysis_consistency,
    check_policy_consistency,
    check_transport_consistency,
    load_contracts,
    read_json,
)


class PolicyContractsTest(unittest.TestCase):
    validators: ClassVar[dict[str, Draft202012Validator]]

    @classmethod
    def setUpClass(cls) -> None:
        _, cls.validators = load_contracts()

    def policy(self, name: str = "browser") -> dict[str, Any]:
        return read_json(ROOT / f"examples/policy/{name}.json")

    def report(self, name: str = "slo-pass-regression-fail") -> dict[str, Any]:
        return read_json(ROOT / f"examples/analysis/{name}.json")

    def assert_report_invalid(
        self, report: dict[str, Any], message: str, policy: dict[str, Any] | None = None
    ) -> None:
        self.validators["analysis/v1"].validate(report)
        with self.assertRaisesRegex(ValueError, message):
            check_analysis_consistency(report, self.policy() if policy is None else policy)

    def test_examples_preserve_independent_outcomes(self) -> None:
        for name, policy_name, outcomes in (
            ("slo-pass-regression-fail", "browser", ("PASS", "PASS", "FAIL")),
            ("missing-reference", "browser", ("PASS", "PASS", "INCONCLUSIVE")),
            ("unknown-samples", "checkout", ("INCONCLUSIVE", "INCONCLUSIVE", "INCONCLUSIVE")),
        ):
            with self.subTest(name=name):
                report = self.report(name)
                self.validators["analysis/v1"].validate(report)
                check_analysis_consistency(report, self.policy(policy_name))
                evaluation = report["evaluations"][0]
                self.assertEqual(
                    tuple(evaluation[k]["status"] for k in ("quality", "slo", "regression")),
                    outcomes,
                )

    def test_policy_and_artifact_hashes_match_local_bytes(self) -> None:
        mappings = {
            "44444444-4444-4444-8444-444444444444": "examples/normalized-result/playwright.json",
            "66666666-6666-4666-8666-666666666666": "tests/fixtures/analysis/normalized-reference-browser.json",
            "33333333-3333-4333-8333-333333333333": "examples/normalized-result/k6.json",
        }
        for name, policy_name in (
            ("slo-pass-regression-fail", "browser"),
            ("missing-reference", "browser"),
            ("unknown-samples", "checkout"),
        ):
            report = self.report(name)
            policy_bytes = (ROOT / f"examples/policy/{policy_name}.json").read_bytes()
            self.assertEqual(report["policy"]["sha256"], hashlib.sha256(policy_bytes).hexdigest())
            for artifact in [report["candidateArtifact"], *report["referenceArtifacts"]]:
                with self.subTest(report=name, artifact=artifact["id"]):
                    path = ROOT / mappings[artifact["id"]]
                    content = path.read_bytes()
                    self.assertEqual(artifact["sha256"], hashlib.sha256(content).hexdigest())
                    self.assertEqual(artifact["sizeBytes"], len(content))
                    envelope = read_json(path)
                    self.validators["normalized-result/v1"].validate(envelope)
                    check_transport_consistency(envelope)
                    self.assertEqual(envelope["runId"], artifact["runId"])
                    self.assertEqual(envelope["testId"], report["testId"])

    def test_reference_statistics_match_raw_fixture(self) -> None:
        path = ROOT / "tests/fixtures/analysis/reference-measurements.json"
        baseline = read_json(ROOT / "tests/fixtures/analysis/normalized-reference-browser.json")
        artifact = baseline["sourceArtifacts"][0]
        self.assertEqual(artifact["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(artifact["sizeBytes"], len(path.read_bytes()))
        values = [sample["durationMs"] for sample in read_json(path)["measurements"]]
        self.assertEqual(
            baseline["results"][0]["distribution"],
            {
                "samples": len(values),
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
            },
        )
        report = self.report()
        self.assertEqual(
            report["evaluations"][0]["regression"]["referenceValue"], sum(values) / len(values)
        )

    def test_blocking_and_fail_open_modes_are_not_supported(self) -> None:
        for mode in ("confirm", "block"):
            with self.subTest(mode=mode):
                policy = self.policy()
                policy["spec"]["mode"] = mode
                self.assertFalse(self.validators["policy/v1"].is_valid(policy))
        policy = self.policy()
        policy["spec"]["missingData"] = "pass"
        self.assertFalse(self.validators["policy/v1"].is_valid(policy))
        report = self.report()
        report["blocking"] = True
        self.assertFalse(self.validators["analysis/v1"].is_valid(report))

    def test_policy_requires_explicit_numeric_thresholds(self) -> None:
        for value in ("200ms", None):
            policy = self.policy()
            policy["spec"]["rules"][0]["slo"]["max"] = value
            self.assertFalse(self.validators["policy/v1"].is_valid(policy))
        policy = self.policy()
        rule = policy["spec"]["rules"][0]
        del rule["slo"], rule["regression"]
        self.assertFalse(self.validators["policy/v1"].is_valid(policy))

    def test_duplicate_rules_selectors_and_inverted_bounds(self) -> None:
        for field, value, message in (
            ("id", "different-rule", "metric/statistic"),
            ("metric", {"name": "other.metric", "statistic": "mean", "unit": "ms"}, "rule ID"),
        ):
            policy = self.policy()
            duplicate = copy.deepcopy(policy["spec"]["rules"][0])
            duplicate[field] = value
            policy["spec"]["rules"].append(duplicate)
            self.validators["policy/v1"].validate(policy)
            with self.assertRaisesRegex(ValueError, message):
                check_policy_consistency(policy)
        policy = self.policy()
        policy["spec"]["rules"][0]["slo"]["min"] = 201
        with self.assertRaisesRegex(ValueError, "minimum exceeds"):
            check_policy_consistency(policy)

    def test_untrusted_quality_cannot_produce_pass_or_fail(self) -> None:
        for quality in ("INVALID", "UNSTABLE", "INCONCLUSIVE", "NOT_EVALUATED"):
            for status in ("PASS", "FAIL"):
                with self.subTest(quality=quality, status=status):
                    report = self.report()
                    evaluation = report["evaluations"][0]
                    evaluation["quality"] = {
                        "status": quality,
                        "reasons": ["Example quality problem."],
                    }
                    evaluation["slo"]["status"] = status
                    evaluation["slo"]["reasons"] = ["Example outcome."]
                    self.assert_report_invalid(report, "Untrusted quality")

    def test_decisive_outcomes_require_values_and_reference(self) -> None:
        for section, field in (
            ("slo", "value"),
            ("regression", "candidateValue"),
            ("regression", "referenceValue"),
            ("regression", "referenceArtifactId"),
            ("regression", "method"),
        ):
            with self.subTest(section=section, field=field):
                report = self.report()
                del report["evaluations"][0][section][field]
                self.assertFalse(self.validators["analysis/v1"].is_valid(report))

    def test_missing_references_reasons_and_rules_are_rejected(self) -> None:
        report = self.report()
        report["referenceArtifacts"] = []
        self.assert_report_invalid(report, "not declared")
        report = self.report()
        report["evaluations"][0]["regression"]["reasons"] = []
        self.assert_report_invalid(report, "require reasons")
        report = self.report()
        report["evaluations"][0]["ruleId"] = "unconfigured-rule"
        self.assert_report_invalid(report, "every policy rule")

    def test_report_must_match_policy_mode_and_units(self) -> None:
        report = self.report()
        report["policy"]["mode"] = "observe"
        self.assert_report_invalid(report, "identity/version/mode")
        report = self.report()
        report["evaluations"][0]["metric"]["unit"] = "s"
        self.assert_report_invalid(report, "metric/statistic/unit")

    def test_quality_pass_needs_configured_evidence(self) -> None:
        report = self.report()
        del report["evaluations"][0]["quality"]["samples"]
        self.assert_report_invalid(report, "sample count")
        policy = self.policy()
        policy["spec"]["rules"][0]["quality"]["maxCv"] = 0.1
        for value in (None, 0.2):
            report = self.report()
            if value is not None:
                report["evaluations"][0]["quality"]["cv"] = value
            self.assert_report_invalid(report, "variability bound", policy)

    def test_slo_and_effect_cannot_contradict_numeric_evidence(self) -> None:
        report = self.report()
        report["evaluations"][0]["slo"]["value"] = 201
        self.assert_report_invalid(report, "SLO outcome contradicts")
        report = self.report()
        report["evaluations"][0]["regression"]["effect"]["value"] = 40
        self.assert_report_invalid(report, "effect contradicts")
        report = self.report()
        report["evaluations"][0]["regression"]["referenceValue"] = 0
        self.assert_report_invalid(report, "against zero")

    def test_higher_is_better_and_absolute_changes(self) -> None:
        for kind, threshold, effect in (("relative", 0.1, 0.2), ("absolute", 10, 20)):
            with self.subTest(kind=kind):
                policy, report = self.policy(), self.report()
                policy["spec"]["rules"][0]["regression"].update(
                    direction="higher-is-better",
                    practicalDifference={"kind": kind, "value": threshold},
                )
                report["evaluations"][0]["regression"].update(
                    candidateValue=80, referenceValue=100, effect={"kind": kind, "value": effect}
                )
                check_analysis_consistency(report, policy)

    def test_candidate_cannot_be_its_own_reference(self) -> None:
        report = self.report()
        report["referenceArtifacts"] = [copy.deepcopy(report["candidateArtifact"])]
        self.assert_report_invalid(report, "Duplicate candidate/reference")
        report = self.report()
        report["candidateArtifact"]["runId"] = report["referenceArtifacts"][0]["runId"]
        self.assert_report_invalid(report, "Candidate run ID")

    def test_strict_json_rejects_nonfinite_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "number.json"
            for value in ("NaN", "Infinity", "-Infinity", "1e999"):
                with self.subTest(value=value):
                    path.write_text('{"value": ' + value + "}", encoding="utf-8")
                    with self.assertRaises(ValueError):
                        read_json(path)


if __name__ == "__main__":
    unittest.main()
