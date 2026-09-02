"""Consumer-facing constraints, including regressions found in the prototype."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.validate import ROOT, check_defaults, load_contracts, read_json, validate_bundle


class ContractsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.validators = load_contracts()

    def test_all_examples_and_schema_defaults(self):
        self.assertEqual(validate_bundle(), (4, 8))

    def test_bad_candidate_identity(self):
        for value in ("1234567", "g" * 40, "a" * 39, "a" * 41):
            with self.subTest(value=value):
                self.assertFalse(self.validators["candidate/v1"].is_valid({"gitSha": value}))

    def test_run_metadata_rejects_invalid_required_fields(self):
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

    def test_result_constraints(self):
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

    def test_nullable_metric_type_matches_declared_default(self):
        data = read_json(ROOT / "examples/metadata/test-result-example.json")
        data["metric"]["type"] = None
        self.validators["result/v1"].validate(data)

    def test_environment_identity_is_required(self):
        for data in ({}, {"cluster": "local"}, {"cluster": "local", "fingerprint": "a" * 63}):
            with self.subTest(data=data):
                self.assertFalse(self.validators["environment/v1"].is_valid(data))

    def test_every_required_root_field_is_enforced(self):
        contracts, _ = load_contracts()
        for entry in contracts:
            data = read_json(ROOT / entry["examples"][0]["path"])
            validator = self.validators[entry["name"]]
            for key in validator.schema["required"]:
                with self.subTest(contract=entry["name"], field=key):
                    self.assertFalse(validator.is_valid({k: v for k, v in data.items() if k != key}))

    def test_invalid_default_is_detected(self):
        with self.assertRaisesRegex(ValueError, "Invalid schema default"):
            check_defaults({"type": "string", "default": None}, self.validators["result/v1"])


if __name__ == "__main__":
    unittest.main()
