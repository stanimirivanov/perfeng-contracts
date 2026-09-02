"""Contract boundaries for reproducible workload and catalogue declarations."""

import copy
import unittest
from typing import Any, ClassVar

from jsonschema import Draft202012Validator

from scripts.validate import ROOT, check_catalogue_consistency, load_contracts, read_json


class WorkloadContractsTest(unittest.TestCase):
    validators: ClassVar[dict[str, Draft202012Validator]]

    @classmethod
    def setUpClass(cls) -> None:
        _, cls.validators = load_contracts()

    def workload(self, tool: str = "k6") -> dict[str, Any]:
        return read_json(ROOT / f"examples/workload/{tool}-smoke.json")

    def catalogue(self) -> dict[str, Any]:
        return read_json(ROOT / "examples/catalogue/application-tests.json")

    def test_both_tool_examples_and_nested_references(self) -> None:
        for tool in ("k6", "playwright"):
            with self.subTest(tool=tool):
                self.validators["workload/v1"].validate(self.workload(tool))
        catalogue = self.catalogue()
        self.validators["catalogue/v1"].validate(catalogue)
        check_catalogue_consistency(catalogue)

    def test_versions_models_and_phase_bounds(self) -> None:
        for path, value in (
            (("version",), "latest"),
            (("version",), "1.0"),
            (("model",), "unknown"),
            (("profile",), "nightly"),
            (("phases", "measurement"), 0),
            (("phases", "warmup"), -1),
            (("phases", "cooldown"), -1),
            (("phases", "unit"), "iterations"),
            (("configuration", "sha256"), "not-a-checksum"),
        ):
            with self.subTest(path=path, value=value):
                data = self.workload()
                parent = data if len(path) == 1 else data[path[0]]
                parent[path[-1]] = value
                self.assertFalse(self.validators["workload/v1"].is_valid(data))

    def test_configuration_paths_cannot_escape_artifact(self) -> None:
        for path in (
            "../config.json",
            "a/../../config.json",
            "/config.json",
            "C:/config.json",
            "a\\config.json",
        ):
            with self.subTest(path=path):
                data = self.workload()
                data["configuration"]["path"] = path
                self.assertFalse(self.validators["workload/v1"].is_valid(data))

    def test_browser_model_and_phase_unit(self) -> None:
        for key, value in (("model", "open"), ("unit", "seconds")):
            with self.subTest(key=key):
                data = self.workload("playwright")
                if key == "unit":
                    data["phases"][key] = value
                else:
                    data[key] = value
                self.assertFalse(self.validators["workload/v1"].is_valid(data))

    def test_versioned_dataset_requires_identity_digest_and_seed(self) -> None:
        for key in ("id", "version", "sha256", "seed"):
            with self.subTest(key=key):
                data = self.workload("playwright")
                del data["dataset"][key]
                self.assertFalse(self.validators["workload/v1"].is_valid(data))
        data = self.workload()
        data["dataset"]["version"] = "1.0.0"
        self.assertFalse(self.validators["workload/v1"].is_valid(data))

    def test_catalogue_requires_pinned_tool_source_and_image(self) -> None:
        for section, key in (("tool", "version"), ("source", "gitSha"), ("artifact", "image")):
            with self.subTest(section=section):
                data = self.catalogue()
                del data["tests"][0][section][key]
                self.assertFalse(self.validators["catalogue/v1"].is_valid(data))
        for section, key, value in (
            ("artifact", "image", "ghcr.io/example/runner:latest"),
            ("source", "gitSha", "main"),
            ("tool", "version", "latest"),
        ):
            with self.subTest(section=section):
                data = self.catalogue()
                data["tests"][0][section][key] = value
                self.assertFalse(self.validators["catalogue/v1"].is_valid(data))

    def assert_inconsistent(self, data: dict[str, Any], message: str) -> None:
        # Prove these relationships need semantic checks, not schema validation.
        self.validators["catalogue/v1"].validate(data)
        with self.assertRaisesRegex(ValueError, message):
            check_catalogue_consistency(data)

    def test_schedule_must_select_a_declared_profile(self) -> None:
        data = self.catalogue()
        data["tests"][0]["schedule"]["nightly"] = "regression"
        self.assert_inconsistent(data, "undeclared profile")

    def test_test_ids_must_be_unique(self) -> None:
        data = self.catalogue()
        data["tests"][1]["id"] = data["tests"][0]["id"]
        self.assert_inconsistent(data, "Duplicate test ID")

    def test_profile_selection_must_be_unambiguous(self) -> None:
        data = self.catalogue()
        other = copy.deepcopy(data["tests"][0]["workloads"][0])
        other["id"] = "other-smoke"
        data["tests"][0]["workloads"].append(other)
        self.assert_inconsistent(data, "Duplicate workload profile")

    def test_workload_and_runner_tools_must_agree(self) -> None:
        data = self.catalogue()
        data["tests"][0]["workloads"] = [self.workload("playwright")]
        self.assert_inconsistent(data, "Workload tool does not match")

    def test_workload_versions_cannot_describe_different_content(self) -> None:
        data = self.catalogue()
        other = copy.deepcopy(data["tests"][0])
        other["id"] = "other-checkout"
        data["tests"].append(other)
        check_catalogue_consistency(data)  # Reuse of an identical definition is valid.
        other["workloads"][0]["phases"]["measurement"] += 1
        self.assert_inconsistent(data, "Conflicting workload definition")


if __name__ == "__main__":
    unittest.main()
