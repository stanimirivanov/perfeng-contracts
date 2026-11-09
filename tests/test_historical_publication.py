"""Verify historical publication assembly and the protected workflow boundary."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts.contracts_history import INVENTORY
from scripts.contracts_publish import digest
from scripts.contracts_publish_history import prepare
from scripts.validate import ROOT, read_json


class HistoricalPublicationTests(unittest.TestCase):
    @patch("scripts.contracts_admission.pack_profile", return_value=b"exact archive")
    @patch("scripts.contracts_publish_history.pack_profile", return_value=b"exact archive")
    def test_every_profile_is_admitted_and_bound_to_the_catalog(self, _pack, _admit_pack) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "assets"
            prepare(output, "contract-history-123")
            catalog = read_json(output / "catalog.manifest.json")
            profiles = read_json(INVENTORY)["profiles"]
            self.assertEqual(set(catalog["profiles"]), set(profiles))
            self.assertEqual(len(list(output.iterdir())), len(profiles) * 4 + 1)
            for revision, checksum in catalog["profiles"].items():
                manifest_path = output / f"{revision}.manifest.json"
                manifest = read_json(manifest_path)
                admission_path = output / f"{revision}.admission.json"
                self.assertEqual(digest(manifest_path.read_bytes()), checksum)
                self.assertEqual(manifest["kind"], "promoted")
                self.assertEqual(manifest["source"]["revision"], revision)
                self.assertEqual(manifest["archiveSha256"], digest(b"exact archive"))
                self.assertEqual(manifest["admissionSha256"], digest(admission_path.read_bytes()))
                self.assertEqual(
                    read_json(admission_path)["candidateSha256"],
                    digest((output / f"{revision}.candidate.json").read_bytes()),
                )

    @patch(
        "scripts.contracts_publish_history.pack_profile",
        side_effect=ValueError("missing Git object"),
    )
    def test_failed_profile_leaves_no_batch(self, _pack) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "assets"
            with self.assertRaisesRegex(ValueError, "missing Git object"):
                prepare(output, "contract-history-123")
            self.assertFalse(output.exists())

    def test_workflow_attests_all_manifests_before_publishing(self) -> None:
        workflow = yaml.load(
            (ROOT / ".github/workflows/contracts-publish.yml").read_text(encoding="utf-8"),
            Loader=yaml.BaseLoader,
        )
        inputs = workflow["on"]["workflow_dispatch"]["inputs"]
        self.assertEqual(inputs["distribution"]["options"], ["tracer", "history"])
        jobs = workflow["jobs"]
        self.assertEqual(jobs["publish"]["needs"], "attest")
        self.assertTrue(
            any(
                step.get("with", {}).get("subject-path") == "release-inputs/*manifest.json"
                for step in jobs["attest"]["steps"]
            )
        )
