"""Consumer-facing constraints, including regressions found in the prototype."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar

from jsonschema import Draft202012Validator

from scripts.validate import (
    ROOT,
    check_bundle_identity,
    check_defaults,
    load_contracts,
    read_json,
    validate_bundle,
)


class ContractsTest(unittest.TestCase):
    validators: ClassVar[dict[str, Draft202012Validator]]

    @classmethod
    def setUpClass(cls) -> None:
        _, cls.validators = load_contracts()

    def test_all_examples_and_schema_defaults(self) -> None:
        self.assertEqual(validate_bundle(), (19, 33))

    def test_bundle_and_project_versions_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "contracts.json").write_text(json.dumps({"version": "1.0.0"}), encoding="utf-8")
            (root / "pyproject.toml").write_text('[project]\nversion = "2.0.0"\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "versions differ"):
                check_bundle_identity(root)

    def test_every_published_schema_reference_resolves(self) -> None:
        contracts, _ = load_contracts()
        original = read_json(ROOT / contracts[0]["schema"])
        broken = copy.deepcopy(original)
        broken["properties"] = {"broken": {"$ref": "#/$defs/missing"}}

        schema_path = ROOT / contracts[0]["schema"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ("contracts.json", "pyproject.toml"):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / path).read_bytes())
            for entry in contracts:
                target = root / entry["schema"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / entry["schema"]).read_bytes())
            (root / schema_path.relative_to(ROOT)).write_text(json.dumps(broken), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Unresolved schema reference"):
                load_contracts(root)

    def test_bad_candidate_identity(self) -> None:
        for value in ("1234567", "g" * 40, "a" * 39, "a" * 41):
            with self.subTest(value=value):
                self.assertFalse(self.validators["candidate/v1"].is_valid({"gitSha": value}))

    def test_run_metadata_rejects_invalid_required_fields(self) -> None:
        original = read_json(ROOT / "examples/metadata/run-metadata-example.json")
        for path, value in (
            (("run", "id"), "run-1"),
            (("run", "timestamp"), "not-a-date"),
            (("run", "timestamp"), "2026-02-30T12:00:00Z"),
            (("run", "status"), "REGRESSION"),
            (("run", "profile"), "unknown"),
            (("candidate", "gitSha"), "a" * 38),
            (("environment", "fingerprint"), "a" * 60),
        ):
            with self.subTest(path=path, value=value):
                data = copy.deepcopy(original)
                data[path[0]][path[1]] = value
                self.assertFalse(self.validators["run/v1"].is_valid(data))

    def test_result_constraints(self) -> None:
        original = read_json(ROOT / "examples/metadata/test-result-example.json")
        for key, value in (("schemaVersion", 2), ("runId", "invalid"), ("extra", True)):
            with self.subTest(key=key):
                self.assertFalse(self.validators["result/v1"].is_valid({**original, key: value}))
        for name, value in (("direction", "unknown"), ("name", "api.some-service.duration")):
            with self.subTest(name=name):
                data = copy.deepcopy(original)
                data["metric"][name] = value
                self.assertFalse(self.validators["result/v1"].is_valid(data))
        data = copy.deepcopy(original)
        data["distribution"]["samples"] = 0
        self.assertFalse(self.validators["result/v1"].is_valid(data))

    def test_nullable_metric_type_matches_declared_default(self) -> None:
        data = read_json(ROOT / "examples/metadata/test-result-example.json")
        data["metric"]["type"] = None
        self.validators["result/v1"].validate(data)

    def test_result_metadata_accepts_only_json_objects(self) -> None:
        data = read_json(ROOT / "examples/result-v2/k6-unknown-count.json")
        data["metadata"] = {"nested": ["value", 1, True, None]}
        validator = self.validators["result/v2"]
        validator.validate(data)

        data["metadata"] = ["not", "an", "object"]
        self.assertFalse(validator.is_valid(data))

    def test_environment_identity_is_required(self) -> None:
        for data in ({}, {"cluster": "local"}, {"cluster": "local", "fingerprint": "a" * 63}):
            with self.subTest(data=data):
                self.assertFalse(self.validators["environment/v1"].is_valid(data))

    def test_every_required_root_field_is_enforced(self) -> None:
        contracts, _ = load_contracts()
        for entry in contracts:
            data = read_json(ROOT / entry["examples"][0]["path"])
            validator = self.validators[entry["name"]]
            for key in validator.schema["required"]:
                with self.subTest(contract=entry["name"], field=key):
                    self.assertFalse(
                        validator.is_valid({k: v for k, v in data.items() if k != key})
                    )

    def test_invalid_default_is_detected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid schema default"):
            check_defaults({"type": "string", "default": None}, self.validators["result/v1"])


if __name__ == "__main__":
    unittest.main()
