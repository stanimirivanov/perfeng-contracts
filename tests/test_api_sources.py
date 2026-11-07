"""Only explicitly declared local source fragments reach the bundler."""

import json
import tempfile
import unittest
from pathlib import Path

from scripts.api_sources import load_source


class ApiSourceTests(unittest.TestCase):
    def test_closure_rejects_remote_escaping_missing_and_symlink_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "openapi.json"
            source.write_text('{"openapi":"3.1.1"}')
            load_source(root, ["openapi.json"])
            for reference in ["https://example.invalid/schema", "../secret.json", "missing.json"]:
                source.write_text(json.dumps({"$ref": reference}))
                with self.assertRaises(ValueError):
                    load_source(root, ["openapi.json"])
            source.unlink()
            source.symlink_to(root / "other.json")
            with self.assertRaises(ValueError):
                load_source(root, ["openapi.json"])

    def test_extra_files_and_missing_json_pointer_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "openapi.json").write_text('{"$ref":"other.json#/missing"}')
            (root / "other.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "inventory"):
                load_source(root, ["openapi.json"])
            with self.assertRaisesRegex(ValueError, "pointer"):
                load_source(root, ["openapi.json", "other.json"])

    def test_disjoint_and_shared_edits_merge_in_both_orders_and_reproduce(self):
        from scripts import api_sources

        registry = json.loads((api_sources.ROOT / "contracts/api-sources.json").read_text())
        for output in (
            "api/run-management/v1/openapi.json",
            "api/native-worker/v2/openapi.json",
        ):
            entry = next(item for item in registry["apis"] if item["output"] == output)
            with self.subTest(output=output):
                self.assert_merge_reproduction(entry)

    def assert_merge_reproduction(self, entry):
        import copy
        import shutil
        import subprocess
        from unittest.mock import patch

        from scripts import api_sources
        from scripts.api_review import digest

        original = json.loads((api_sources.ROOT / entry["output"]).read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / entry["root"]
            source.parent.mkdir(parents=True)
            shutil.copytree(api_sources.ROOT / entry["root"], source)
            (root / "scripts").mkdir()
            shutil.copy(
                api_sources.ROOT / "scripts/offline-node.sh", root / "scripts/offline-node.sh"
            )
            shutil.copy(api_sources.ROOT / "redocly.yaml", root / "redocly.yaml")
            (root / "node_modules").symlink_to(api_sources.ROOT / "node_modules")

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

            git("init", "--initial-branch=base")
            git("add", entry["root"])
            git("commit", "-m", "base")
            paths = list(original["paths"])[:2]
            expected = copy.deepcopy(original)
            for index, path in enumerate(paths):
                branch = f"edit-{index}"
                git("switch", "-c", branch, "base")
                name = json.loads((source / "openapi.json").read_text())["paths"][path]["$ref"]
                fragment = source / name
                document = json.loads(fragment.read_text())
                document["summary"] = branch
                fragment.write_text(json.dumps(document, indent=2) + "\n")
                git("add", str(fragment.relative_to(root)))
                git("commit", "-m", branch)
                expected["paths"][path]["summary"] = branch
            git("switch", "-c", "shared", "base")
            name = next(iter(original["components"]["schemas"]))
            fragment = source / "components/schemas" / (name + ".json")
            document = json.loads(fragment.read_text())
            document["description"] = "Shared fixture edit"
            fragment.write_text(json.dumps(document, indent=2) + "\n")
            git("add", str(fragment.relative_to(root)))
            git("commit", "-m", "shared")
            expected["components"]["schemas"][name]["description"] = "Shared fixture edit"
            outputs = []
            for index, order in enumerate(
                [("edit-0", "edit-1", "shared"), ("shared", "edit-1", "edit-0")]
            ):
                git("switch", "-c", f"merged-{index}", order[0])
                for branch in order[1:]:
                    git("merge", "--no-edit", branch)
                candidate = {**entry, "semanticSha256": digest(expected)}
                with patch.object(api_sources, "ROOT", root):
                    api_sources.build(candidate, check=False)
                    api_sources.build(candidate, check=True)
                outputs.append((root / entry["output"]).read_bytes())
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(json.loads(outputs[0]), expected)

    def test_in_tree_ancestor_alias_cannot_redirect_source_or_output_ownership(self):
        from unittest.mock import patch

        from scripts import api_sources
        from scripts.api_review import digest

        document = {"openapi": "3.1.1", "paths": {}, "components": {"schemas": {}}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "api/real/v1/source"
            source.mkdir(parents=True)
            (source / "openapi.json").write_text(json.dumps(document))
            (root / "api/alias").symlink_to(root / "api/real", target_is_directory=True)
            (root / "api/result").mkdir()
            (root / "redocly.yaml").write_text(json.dumps(api_sources.CONFIG))
            entry = {
                "root": "api/real/v1/source",
                "output": "api/result/openapi.json",
                "files": ["openapi.json"],
                "mode": "effect-components",
                "semanticSha256": digest(document),
            }
            with patch.object(api_sources, "ROOT", root):
                for alias in [
                    {"root": "api/alias/v1/source"},
                    {"output": "api/alias/openapi.json"},
                ]:
                    with self.subTest(alias=alias), self.assertRaisesRegex(ValueError, "canonical"):
                        api_sources.build({**entry, **alias}, check=False)
