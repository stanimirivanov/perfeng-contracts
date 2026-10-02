"""Conformance and compatibility tests for the baseline native execution recipe."""

import copy
import unittest
from unittest.mock import patch

from scripts import validate_native_worker_api as v1
from scripts import validate_native_worker_api_v2 as v2
from scripts.validate import read_json
from scripts.validate_api import schema_validator


class NativeWorkerV2Tests(unittest.TestCase):
    def setUp(self):
        root = v2.ROOT / v2.API_PATH
        self.document = read_json(root / "openapi.json")
        self.values = {name: read_json(root / "examples" / f"{name}.json") for name in v2.FIXTURES}

    def test_v1_and_v2_validate_independently_offline(self):
        with patch("socket.create_connection", side_effect=AssertionError("network")):
            self.assertEqual(v1.validate_native_worker_api(), (16, 11, 10))
            self.assertEqual(v2.validate_native_worker_api_v2(), (16, 15, 10))
        self.assertFalse(
            schema_validator(self.document, "Lease").is_valid(
                read_json(v2.ROOT / v1.API_PATH / "examples" / "lease.json")
            )
        )
        self.assertFalse(
            schema_validator(self.document, "AcquireLease").is_valid(
                read_json(v2.ROOT / v1.API_PATH / "examples" / "acquire.json")
            )
        )

    def test_recipe_requires_every_runner_input_and_rejects_extra_fields(self):
        recipe = self.values["lease"]["assignment"]["recipe"]
        validator = schema_validator(self.document, "ExecutionRecipe")
        validator.validate(recipe)
        for name in [
            "journeyId",
            "workloadVersion",
            "workloadSha256",
            "scenario",
            "environment",
            "browserSettings",
        ]:
            changed = {key: value for key, value in recipe.items() if key != name}
            self.assertFalse(validator.is_valid(changed), name)
        for path, value in [
            (("journeyId",), "arbitrary-command"),
            (("workloadSha256",), "not-a-digest"),
            (("scenario", "measurementIterations"), 0),
            (("scenario", "warmupIterations"), 101),
            (("scenario", "pageReuse"), "per-run"),
            (("environment", "fingerprint"), "unknown"),
            (("browserSettings", "viewport", "width"), 0),
            (("browserSettings", "deviceScaleFactor"), 5),
        ]:
            changed = copy.deepcopy(recipe)
            target = changed
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            self.assertFalse(validator.is_valid(changed), path)
        self.assertFalse(validator.is_valid({**recipe, "diagnostics": {"captureIterations": [1]}}))

    def test_recipe_is_bound_to_qualification_and_baseline_capability(self):
        v2.check_recipe(self.values)
        for path, value in [
            (("recipe", "environment", "profileId"), "other-host"),
            (("recipe", "environment", "evidenceSha256"), "1" * 64),
            (("executionArtifact", "revision"), "d" * 40),
            (("browser",), "edge"),
            (("diagnosticMode",), "trace"),
        ]:
            changed = copy.deepcopy(self.values)
            target = changed["lease"]["assignment"]
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            with self.assertRaises(ValueError):
                v2.check_recipe(changed)

    def test_lease_rejects_unsupported_profile_and_incomplete_artifact_plan(self):
        validator = schema_validator(self.document, "Lease")
        lease = self.values["lease"]
        validator.validate(lease)
        for change in [
            lambda value: value["assignment"].update(profile="windows-mainstream"),
            lambda value: value["artifactPlan"].pop(),
            lambda value: value["artifactPlan"].reverse(),
            lambda value: value["artifactPlan"].append(copy.deepcopy(value["artifactPlan"][0])),
            lambda value: value["artifactPlan"][0].update(required=False),
            lambda value: value["assignment"]["target"].update(
                baseUrl="https://user@system.perfeng.invalid"
            ),
        ]:
            changed = copy.deepcopy(lease)
            change(changed)
            self.assertFalse(validator.is_valid(changed))

    def test_generation_and_baseline_scope_are_not_accidental(self):
        changed = copy.deepcopy(self.document)
        changed["components"]["schemas"]["Lease"]["properties"]["assignment"]["required"].remove(
            "recipe"
        )
        with self.assertRaisesRegex(ValueError, "require the reviewed execution recipe"):
            v2.lint_v2(changed)
        changed = copy.deepcopy(self.document)
        changed["components"]["schemas"]["Lease"]["properties"]["assignment"]["properties"][
            "diagnosticMode"
        ] = {"enum": ["baseline", "trace"]}
        with self.assertRaisesRegex(ValueError, "baseline Chromium"):
            v2.lint_v2(changed)


if __name__ == "__main__":
    unittest.main()
