"""Browser environment, execution-lifetime, and diagnostic evidence contracts."""

import copy
import hashlib
import unittest
from typing import Any, ClassVar

from jsonschema import Draft202012Validator

from scripts.validate import (
    ROOT,
    check_browser_diagnostics,
    check_browser_environment,
    check_playwright_measurements,
    load_contracts,
    read_json,
)


class BrowserDiagnosticsContractsTest(unittest.TestCase):
    validators: ClassVar[dict[str, Draft202012Validator]]

    @classmethod
    def setUpClass(cls) -> None:
        _, cls.validators = load_contracts()

    def example(self, path: str) -> dict[str, Any]:
        return read_json(ROOT / "examples" / path)

    def assert_environment_inconsistent(self, data: dict[str, Any], message: str) -> None:
        self.validators["browser-environment/v1"].validate(data)
        with self.assertRaisesRegex(ValueError, message):
            check_browser_environment(data)

    def assert_diagnostics_inconsistent(self, data: dict[str, Any], message: str) -> None:
        self.validators["browser-diagnostics/v1"].validate(data)
        with self.assertRaisesRegex(ValueError, message):
            check_browser_diagnostics(data)

    def test_windows_environment_and_diagnostics_examples(self) -> None:
        environment = self.example("browser-environment/windows-mainstream.json")
        diagnostics = self.example("browser-diagnostics/search-trace.json")
        self.validators["browser-environment/v1"].validate(environment)
        self.validators["browser-diagnostics/v1"].validate(diagnostics)
        check_browser_environment(environment)
        check_browser_diagnostics(diagnostics)
        content = (ROOT / "examples/browser-environment/windows-mainstream.json").read_bytes()
        reference = diagnostics["environment"]["artifact"]
        self.assertEqual(reference["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(reference["sizeBytes"], len(content))

    def test_accepted_environment_must_be_usable_and_internally_consistent(self) -> None:
        original = self.example("browser-environment/windows-mainstream.json")
        for mutate, message in (
            (
                lambda data: data["host"]["cpu"].update(availableLogicalCores=13),
                "Available logical cores",
            ),
            (
                lambda data: data["host"]["memory"].update(availableBytes=20_000_000_000),
                "Available memory exceeds",
            ),
            (
                lambda data: data["calibration"].update(availableMemoryBytes=1),
                "available memory disagree",
            ),
            (
                lambda data: data["calibration"].update(clockSynchronized=False),
                "synchronized clock",
            ),
            (
                lambda data: data["calibration"].update(softwareRendering=True),
                "hardware rendering",
            ),
        ):
            with self.subTest(message=message):
                data = copy.deepcopy(original)
                mutate(data)
                self.assert_environment_inconsistent(data, message)

    def test_rejected_calibration_requires_a_reason(self) -> None:
        data = self.example("browser-environment/windows-mainstream.json")
        data["calibration"]["status"] = "REJECTED"
        self.assertFalse(self.validators["browser-environment/v1"].is_valid(data))
        data["calibration"]["reasons"] = ["Software rendering was active."]
        self.validators["browser-environment/v1"].validate(data)

    def test_v2_separates_page_context_and_diagnostic_modes(self) -> None:
        original = self.example("playwright-measurements/search-windows-lightweight.json")
        validator = self.validators["playwright-measurements/v2"]
        validator.validate(original)
        check_playwright_measurements(original)
        for changes in (
            {"cacheProfile": "cold", "contextReuse": "per-iteration", "pageReuse": "per-run"},
            {"cacheProfile": "warm", "contextReuse": "per-iteration"},
            {"contextReuse": "per-iteration", "pageReuse": "per-run"},
        ):
            with self.subTest(changes=changes):
                data = copy.deepcopy(original)
                data["scenario"].update(changes)
                self.assertFalse(validator.is_valid(data))
        self.assertFalse(self.validators["playwright-measurements/v1"].is_valid(original))

    def test_trace_loss_and_capture_scope_are_explicit(self) -> None:
        original = self.example("browser-diagnostics/search-trace.json")
        for mutate, message in (
            (
                lambda data: data["captures"][2].update(status="COMPLETE", reasons=[]),
                "Trace data loss requires",
            ),
            (
                lambda data: data["captures"][2].update(
                    status="COMPLETE", reasons=[], dataLossOccurred=None
                ),
                "explicit no-data-loss",
            ),
            (
                lambda data: data["captures"][1]["scope"].update(iteration=3),
                "not selected",
            ),
            (
                lambda data: data["captures"][2]["artifact"].update(
                    format="browser-observations-json"
                ),
                "format does not match",
            ),
            (
                lambda data: data["captures"][2].update(sensitive=False),
                "not classified as sensitive",
            ),
        ):
            with self.subTest(message=message):
                data = copy.deepcopy(original)
                mutate(data)
                self.assert_diagnostics_inconsistent(data, message)

    def test_mode_run_identity_and_artifact_uniqueness_are_enforced(self) -> None:
        original = self.example("browser-diagnostics/search-trace.json")
        for mutate, message in (
            (
                lambda data: data["captures"].pop(),
                "required captures",
            ),
            (
                lambda data: data["sources"].remove("cdp"),
                "require the CDP source",
            ),
            (
                lambda data: data["captures"][0]["artifact"].update(
                    runId="perf-20260903-130000-a1b2c3d5"
                ),
                "run ID does not match",
            ),
            (
                lambda data: data["captures"][1]["artifact"].update(
                    id=data["captures"][0]["artifact"]["id"]
                ),
                "Duplicate diagnostic artifact",
            ),
        ):
            with self.subTest(message=message):
                data = copy.deepcopy(original)
                mutate(data)
                self.assert_diagnostics_inconsistent(data, message)

    def test_failed_trace_can_report_unknown_data_loss_without_an_artifact(self) -> None:
        data = self.example("browser-diagnostics/search-trace.json")
        trace = data["captures"][2]
        trace.update(
            status="FAILED",
            reasons=["Tracing failed before completion."],
            dataLossOccurred=None,
        )
        del trace["artifact"]
        self.validators["browser-diagnostics/v1"].validate(data)
        check_browser_diagnostics(data)


if __name__ == "__main__":
    unittest.main()
