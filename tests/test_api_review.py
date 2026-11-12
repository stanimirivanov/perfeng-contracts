"""Direction-sensitive review receipts preserve meaningful API diffs."""

import copy
import json
import unittest
from typing import Any

from scripts.api_review import review


class ApiReviewTests(unittest.TestCase):
    def setUp(self):
        self.document: dict[str, Any] = {
            "openapi": "3.1.1",
            "paths": {
                "/runs": {
                    "post": {
                        "operationId": "createRun",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Input"}
                                }
                            }
                        },
                        "responses": {
                            "201": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/Output"}
                                    }
                                }
                            }
                        },
                    }
                }
            },
            "components": {
                "schemas": {
                    "Input": {
                        "type": "object",
                        "required": ["id"],
                        "properties": {"id": {"type": "string", "enum": ["a", "b"]}},
                    },
                    "Output": {
                        "type": "object",
                        "required": ["id"],
                        "properties": {"id": {"type": "string", "enum": ["a", "b"]}},
                    },
                }
            },
        }

    def changed(self, name, key, value):
        candidate = copy.deepcopy(self.document)
        candidate["components"]["schemas"][name][key] = value
        return review(self.document, candidate)["changes"]

    def test_request_required_addition_and_response_removal_break(self):
        self.assertEqual(
            self.changed("Input", "required", ["id", "new"])[0]["classification"], "breaking"
        )
        self.assertEqual(self.changed("Output", "required", [])[0]["classification"], "breaking")

    def test_opposite_requiredness_change_is_recorded_for_review(self):
        self.assertEqual(self.changed("Input", "required", [])[0]["classification"], "review")
        self.assertEqual(
            self.changed("Output", "required", ["id", "new"])[0]["classification"], "review"
        )

    def test_enum_direction_and_unknown_schema_change(self):
        for name, values in [("Input", ["a"]), ("Output", ["a", "b", "c"])]:
            candidate = copy.deepcopy(self.document)
            candidate["components"]["schemas"][name]["properties"]["id"]["enum"] = values
            self.assertEqual(
                review(self.document, candidate)["changes"][0]["classification"], "breaking"
            )
        self.assertEqual(self.changed("Input", "maxProperties", 1)[0]["classification"], "review")

    def test_removed_path_and_reordered_enum(self):
        candidate = copy.deepcopy(self.document)
        del candidate["paths"]["/runs"]
        self.assertEqual(
            review(self.document, candidate)["changes"][0]["classification"], "breaking"
        )
        candidate = copy.deepcopy(self.document)
        candidate["components"]["schemas"]["Input"]["properties"]["id"]["enum"] = ["b", "a"]
        self.assertEqual(review(self.document, candidate)["changes"], [])

    def test_inventory_and_identity_are_stable(self):
        receipt = review(self.document, self.document)
        self.assertEqual(receipt["changes"], [])
        self.assertEqual(
            receipt["operations"], [{"method": "POST", "path": "/runs", "operationId": "createRun"}]
        )
        self.assertIn("required", receipt["schemaKeywords"])

    def test_null_constraint_addition_is_visible(self):
        changes = self.changed("Input", "const", None)
        self.assertEqual(changes[0]["classification"], "review")
        self.assertFalse(changes[0]["beforePresent"])
        self.assertTrue(changes[0]["afterPresent"])

    def test_cli_compares_actual_git_base_and_head(self):
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        from scripts.api_review import APIS

        script = Path(__file__).resolve().parents[1] / "scripts/api_review.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in APIS:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(self.document))

            def git(*args):
                return subprocess.run(
                    [
                        "git",
                        "-c",
                        "user.name=Fixture",
                        "-c",
                        "user.email=fixture@example.invalid",
                        *args,
                    ],
                    cwd=root,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()

            git("init")
            git("add", "api")
            git("commit", "-m", "baseline")
            base = git("rev-parse", "HEAD")
            candidate = copy.deepcopy(self.document)
            candidate["components"]["schemas"]["Input"]["required"].append("new")
            (root / APIS[0]).write_text(json.dumps(candidate))
            run = subprocess.run(
                [sys.executable, str(script), "--base", base],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 1)
            self.assertIn('"classification": "breaking"', run.stdout)
            self.assertIn("Semantic changes require exact review intent", run.stderr)
            intent = {
                "baseCommit": base,
                "apis": {
                    APIS[0]: {
                        "beforeSha256": review(self.document, candidate)["beforeSha256"],
                        "afterSha256": review(self.document, candidate)["afterSha256"],
                        "reason": "Deliberate fixture change; still requires human review.",
                    }
                },
            }
            (root / "contracts").mkdir()
            (root / "contracts/api-semantic-review.json").write_text(json.dumps(intent))
            admitted = subprocess.run(
                [sys.executable, str(script), "--base", base],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(admitted.returncode, 0, admitted.stderr)
            self.assertIn('"classification": "breaking"', admitted.stdout)
            candidate["components"]["schemas"]["Input"]["maxProperties"] = 2
            (root / APIS[0]).write_text(json.dumps(candidate))
            drifted = subprocess.run(
                [sys.executable, str(script), "--base", base],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(drifted.returncode, 1)

    def test_literal_arrays_and_description_are_semantic_changes(self):
        for before, after in [
            ({"const": {"required": ["a", "b"]}}, {"const": {"required": ["b", "a"]}}),
            ({"const": {"description": "a"}}, {"const": {"description": "b"}}),
            ({"const": True}, {"const": 1}),
            ({"x-vendor": {"enum": ["a", "b"]}}, {"x-vendor": {"enum": ["b", "a"]}}),
        ]:
            with self.subTest(before=before):
                baseline = copy.deepcopy(self.document)
                candidate = copy.deepcopy(self.document)
                baseline["components"]["schemas"]["Input"].update(before)
                candidate["components"]["schemas"]["Input"].update(after)
                receipt = review(baseline, candidate)
                self.assertNotEqual(receipt["beforeSha256"], receipt["afterSha256"])
                self.assertTrue(receipt["changes"])
                self.assertTrue(
                    all(item["classification"] != "documentation" for item in receipt["changes"])
                )

    def test_only_known_openapi_annotations_are_documentation(self):
        baseline = copy.deepcopy(self.document)
        baseline["info"] = {"title": "Example", "description": "before"}
        candidate = copy.deepcopy(baseline)
        candidate["info"]["description"] = "after"
        self.assertEqual(
            review(baseline, candidate)["changes"][0]["classification"], "documentation"
        )
        candidate = copy.deepcopy(baseline)
        candidate["x-vendor"] = {"description": "external semantic setting"}
        self.assertEqual(review(baseline, candidate)["changes"][0]["classification"], "review")

    def test_semantic_intent_is_bound_to_exact_base_and_both_api_digests(self):
        from scripts.api_review import check_review_intent

        candidate = copy.deepcopy(self.document)
        candidate["paths"]["/access"] = {"get": {"operationId": "getAccess"}}
        receipt = review(self.document, candidate)
        base = "a" * 40
        path = "api/run-management/v1/openapi.json"
        receipts = {path: receipt}
        intent: dict[str, Any] = {
            "baseCommit": base,
            "apis": {
                path: {
                    "beforeSha256": receipt["beforeSha256"],
                    "afterSha256": receipt["afterSha256"],
                    "reason": "Issue #109 and ADR-0016; proposed service identity semantics.",
                }
            },
        }
        check_review_intent(receipts, base, intent)
        for mutation in ("base", "before", "after", "missing", "extra", "reason"):
            invalid = copy.deepcopy(intent)
            if mutation == "base":
                invalid["baseCommit"] = "b" * 40
            elif mutation in {"before", "after"}:
                invalid["apis"][path][mutation + "Sha256"] = "0" * 64
            elif mutation == "missing":
                invalid["apis"] = {}
            elif mutation == "extra":
                invalid["apis"]["unknown-api"] = invalid["apis"][path]
            else:
                invalid["apis"][path]["reason"] = " "
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                check_review_intent(receipts, base, invalid)
        candidate["paths"]["/another"] = {"get": {"operationId": "another"}}
        with self.assertRaises(ValueError):
            check_review_intent({path: review(self.document, candidate)}, base, intent)
