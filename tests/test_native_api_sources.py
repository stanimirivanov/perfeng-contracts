"""Native split authoring preserves the reviewed API and provider loader identities."""

import json
import unittest
from pathlib import Path

from scripts.api_review import digest
from scripts.api_sources import load_source

ROOT = Path(__file__).resolve().parents[1]


class NativeApiSourceTests(unittest.TestCase):
    def test_native_source_registration_preserves_the_original_schema_identity(self):
        registry = json.loads((ROOT / "contracts/api-sources.json").read_text())
        entries = [
            entry
            for entry in registry["apis"]
            if entry["output"] == "api/native-worker/v2/openapi.json"
        ]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(
            entry["semanticSha256"],
            "af69607d655146701797b622ef3e0b1c9e5dea8712f0a9618f286cc2f52e6bd0",
        )
        files = load_source(ROOT / entry["root"], entry["files"])
        published = json.loads((ROOT / entry["output"]).read_text())
        self.assertEqual(published["info"]["version"], "2.3.0")
        self.assertEqual(digest(published), entry["semanticSha256"])
        self.assertEqual(len(published["paths"]), 9)
        self.assertEqual(
            set(files["openapi.json"]["components"]["schemas"]),
            set(published["components"]["schemas"]),
        )
        self.assertEqual(set(files["openapi.json"]["paths"]), set(published["paths"]))
