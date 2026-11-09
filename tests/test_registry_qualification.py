"""Exercise admission and reference binding without a registry or network."""

import unittest
from unittest.mock import patch

from scripts.registry_qualification import exact_lookup, receipt, schema_refs


class RegistryQualificationTests(unittest.TestCase):
    def test_incomplete_or_negative_evidence_never_admits(self) -> None:
        self.assertEqual(receipt({})["status"], "NOT_ADMITTED")
        self.assertEqual(receipt({"registration": True})["status"], "NOT_ADMITTED")
        cases = {
            "current": True,
            "historical": True,
            "references": True,
            "jsonCompatibility": False,
            "byteIdentity": True,
            "openapi": True,
        }
        self.assertEqual(receipt(cases)["status"], "NOT_ADMITTED")
        self.assertEqual(
            receipt({**cases, "jsonCompatibility": True, "openapi": False})["status"], "ADMITTED"
        )

    def test_absolute_and_relative_refs_bind_the_declared_subject(self) -> None:
        target = {"$id": "https://perfeng.dev/schemas/shared.json", "type": "string"}
        consumer = {
            "$id": "https://perfeng.dev/schemas/test.json",
            "allOf": [
                {"$ref": "shared.json#/$defs/value"},
                {"$ref": "https://perfeng.dev/schemas/shared.json"},
                {"$ref": "#/$defs/local"},
            ],
        }
        refs = schema_refs(
            "schemas/test.json",
            consumer,
            {"schemas/shared.json": target},
            {"schemas/shared.json": "fixture.shared"},
        )
        self.assertEqual(
            refs,
            [
                {
                    "name": "https://perfeng.dev/schemas/shared.json",
                    "subject": "fixture.shared",
                    "version": 1,
                },
                {"name": "shared.json", "subject": "fixture.shared", "version": 1},
            ],
        )

    def test_unavailable_reference_is_not_silently_omitted(self) -> None:
        with self.assertRaisesRegex(ValueError, "Undeclared"):
            schema_refs("schemas/test.json", {"$ref": "missing.json"}, {}, {})

    @patch("scripts.registry_qualification.request")
    def test_byte_identity_checks_both_locators_and_detects_unstable_results(self, request) -> None:
        exact = (200, {"schema": "{}"})
        request.side_effect = [exact, exact, exact, exact]
        self.assertTrue(exact_lookup("fixture", 7, 2, "{}"))
        self.assertEqual(
            [call.args[1] for call in request.call_args_list],
            ["/subjects/fixture/versions/2"] * 2 + ["/schemas/ids/7"] * 2,
        )
        request.side_effect = [exact, exact, exact, (200, {"schema": "{ }"})]
        self.assertFalse(exact_lookup("fixture", 7, 2, "{}"))
