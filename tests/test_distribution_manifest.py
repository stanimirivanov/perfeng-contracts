"""Exercise the offline distribution metadata boundary."""

import copy
import unittest

from jsonschema import Draft202012Validator

from scripts.validate import ROOT, read_json


class DistributionManifestTests(unittest.TestCase):
    def test_tracer_and_release_states(self) -> None:
        schema = read_json(ROOT / "distribution/manifest.schema.json")
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        tracer = read_json(ROOT / "distribution/tracer.json")
        validator.validate(tracer)
        self.assertEqual(tracer["kind"], "selection")
        self.assertEqual(tracer["source"]["version"], "0.22.0")
        self.assertEqual(len(tracer["members"]), 3)

        candidate = {
            **tracer,
            "kind": "candidate",
            "releaseId": "tracer-1",
            "archiveSha256": "a" * 64,
        }
        promoted = {**candidate, "kind": "promoted", "admissionSha256": "b" * 64}
        validator.validate(candidate)
        validator.validate(promoted)
        self.assertFalse(validator.is_valid({**candidate, "kind": "promoted"}))
        self.assertFalse(validator.is_valid({**promoted, "kind": "candidate"}))
        self.assertFalse(validator.is_valid({**tracer, "archiveSha256": "a" * 64}))

    def test_rejects_missing_identity_and_unsafe_or_ambiguous_members(self) -> None:
        validator = Draft202012Validator(read_json(ROOT / "distribution/manifest.schema.json"))
        tracer = read_json(ROOT / "distribution/tracer.json")
        for field in ("repository", "revision", "version"):
            with self.subTest(field=field):
                bad = copy.deepcopy(tracer)
                del bad["source"][field]
                self.assertFalse(validator.is_valid(bad))
        for path in ("/absolute", "../escape", "a/../b", "a//b", "a\\b", "a%2fb", "a\n"):
            with self.subTest(path=path):
                self.assertFalse(
                    validator.is_valid({**tracer, "members": {**tracer["members"], path: "a" * 64}})
                )
        for member in ({"sha256": "a" * 64, "revision": "c" * 40}, "b" * 63):
            self.assertFalse(
                validator.is_valid({**tracer, "members": {**tracer["members"], "LICENSE": member}})
            )
