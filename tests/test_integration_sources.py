"""Effect-owned fragments preserve component-local recursive definitions."""

import tempfile
import unittest
from pathlib import Path

from scripts.api_sources import load_source
from scripts.integration_sources import assemble, fragment_outputs, write_fragments


class IntegrationSourceTests(unittest.TestCase):
    def test_nested_component_ref_round_trip_preserves_root_and_definitions(self):
        document = {
            "openapi": "3.1.1",
            "paths": {
                "/requests": {
                    "get": {
                        "responses": {
                            "400": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/Error"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "Error": {
                        "$ref": "#/components/schemas/Error/$defs/IntegrationError",
                        "$defs": {
                            "IntegrationError": {
                                "type": "object",
                                "properties": {"code": {"enum": ["invalid"]}},
                            }
                        },
                    }
                }
            },
        }
        files = fragment_outputs(document)
        error = files["components/schemas/Error.json"]
        self.assertIn('"$ref": "#/$defs/IntegrationError"', error)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, contents in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contents)
            parsed = load_source(root, sorted(files))
            self.assertEqual(assemble(parsed), document)
            # The original document-root reference is invalid in an external component.
            (root / "components/schemas/Error.json").write_text(
                error.replace(
                    '"#/$defs/IntegrationError"',
                    '"#/components/schemas/Error/$defs/IntegrationError"',
                )
            )
            with self.assertRaisesRegex(ValueError, "pointer"):
                load_source(root, sorted(files))

    def test_generated_fragment_drift_and_unowned_files_fail(self):
        outputs = {"openapi.json": "{}\n"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fragments(root, outputs, check=False)
            write_fragments(root, outputs, check=True)
            (root / "openapi.json").write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError, "Stale"):
                write_fragments(root, outputs, check=True)
            (root / "manual.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "Unexpected"):
                write_fragments(root, outputs, check=False)

    def test_identity_changing_schema_keywords_require_admission(self):
        for keyword in ["$id", "$dynamicRef", "$recursiveRef"]:
            with self.assertRaisesRegex(ValueError, "separate emitter admission"):
                fragment_outputs(
                    {"paths": {}, "components": {"schemas": {"New": {keyword: "value"}}}}
                )
