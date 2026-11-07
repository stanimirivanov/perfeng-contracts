"""Direction-sensitive review receipts preserve meaningful API diffs."""

import copy
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
