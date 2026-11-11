"""Guard candidate packaging and the retired duplicate CI tar assembly."""

import io
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from scripts.contracts_candidate import prepare
from scripts.contracts_pack import pack
from scripts.contracts_publish import digest
from scripts.validate import ROOT, read_json


class DistributionRetirementTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.area = Path(scratch.name)
        self.root = self.area / "source"
        self.root.mkdir()
        self.files = {
            "contracts.json": b'{"version":"0.27.0"}\n',
            "LICENSE": b"fixture licence\n",
            "README.md": b"fixture readme\n",
            **{
                f"{directory}/fixture.json": b'{"fixture":true}\n'
                for directory in ("schemas", "examples", "api", "docs", "tests/fixtures")
            },
        }
        for name, data in self.files.items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        self.git("init", "-q", "--object-format=sha1")
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.org",
            "commit",
            "-qm",
            "fixture",
        )
        self.revision = self.git("rev-parse", "HEAD").strip()

    def git(self, *args: str) -> str:
        env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        return subprocess.check_output(["git", "-C", str(self.root), *args], env=env, text=True)

    def test_candidate_uses_the_canonical_packager_and_exact_git_inventory(self) -> None:
        first, second = self.area / "first", self.area / "second"
        prepare(self.root, self.revision, first, "pr-candidate-123")
        (self.root / "README.md").write_text("dirty checkout", encoding="utf-8")
        (self.root / "schemas/untracked.json").write_text("{}", encoding="utf-8")
        prepare(self.root, self.revision, second, "pr-candidate-123")
        self.assertEqual(
            sorted(path.name for path in first.iterdir()), ["candidate.json", "candidate.tar.gz"]
        )
        manifest = read_json(first / "candidate.json")
        Draft202012Validator(read_json(ROOT / "distribution/manifest.schema.json")).validate(
            manifest
        )
        self.assertEqual(manifest["kind"], "candidate")
        self.assertEqual(manifest["source"]["revision"], self.revision)
        selection = {
            key: value
            for key, value in manifest.items()
            if key not in ("releaseId", "archiveSha256")
        }
        selection["kind"] = "selection"
        compressed = (first / "candidate.tar.gz").read_bytes()
        self.assertEqual(manifest["archiveSha256"], digest(compressed))
        self.assertEqual(compressed, pack(self.root, selection))
        self.assertEqual(compressed, (second / "candidate.tar.gz").read_bytes())
        with tarfile.open(fileobj=io.BytesIO(compressed), mode="r:gz") as archive:
            self.assertEqual(archive.getnames(), sorted(self.files))
            for entry in archive:
                stream = archive.extractfile(entry)
                assert stream is not None
                self.assertEqual(stream.read(), self.files[entry.name])

    def test_refuses_promoted_identity_existing_output_and_nonregular_git_input(self) -> None:
        output = self.area / "candidate"
        with self.assertRaisesRegex(ValueError, "identifier"):
            prepare(self.root, self.revision, output, "contract-history-123")
        prepare(self.root, self.revision, output, "pr-candidate-123")
        with self.assertRaises(FileExistsError):
            prepare(self.root, self.revision, output, "pr-candidate-123")
        (self.root / "schemas/alias").symlink_to("../LICENSE")
        self.git("add", "schemas/alias")
        self.git(
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.org",
            "commit",
            "-qm",
            "symlink",
        )
        with self.assertRaisesRegex(ValueError, "regular"):
            prepare(
                self.root,
                self.git("rev-parse", "HEAD").strip(),
                self.area / "invalid",
                "pr-candidate-123",
            )
        self.assertFalse((self.area / "invalid").exists())

    def test_ci_calls_only_canonical_candidate_assembly_and_labels_the_artifact(self) -> None:
        workflow = yaml.safe_load((ROOT / ".github/workflows/validate.yml").read_text())
        steps = workflow["jobs"]["validate"]["steps"]
        assembly = next(
            step for step in steps if step.get("name") == "Assemble candidate contract bundle"
        )
        self.assertIn("scripts.contracts_candidate", assembly["run"])
        self.assertNotIn("tar -", assembly["run"])
        self.assertEqual(assembly["env"]["SOURCE_REVISION"], "${{ github.sha }}")
        upload = next(
            step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@")
        )
        self.assertIn("pr-candidate", upload["with"]["name"])
        self.assertEqual(upload["with"]["path"], "dist/pr-candidate/")
