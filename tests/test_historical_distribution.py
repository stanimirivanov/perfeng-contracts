"""Check exact historical profiles before distribution."""

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.contracts_history import INVENTORY, pack_profile, selection, validate_inventory
from scripts.contracts_pack import pack
from scripts.validate import read_json


class HistoricalDistributionTests(unittest.TestCase):
    def test_profiles_use_exact_git_blobs_and_refuse_missing_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", "--object-format=sha1", directory], check=True)
            contents = {
                "LICENSE": b"licence",
                "schema.json": b"{}",
                "unclosed.json": b'{"$ref":"https://perfeng.dev/missing.json"}',
                "contracts.json": b'{"version":"0.13.0"}',
            }
            for name, content in contents.items():
                (root / name).write_bytes(content)
            subprocess.run(["git", "-C", directory, "add", "."], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    directory,
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.org",
                    "-c",
                    "commit.gpgsign=false",
                    "commit",
                    "-qm",
                    "fixture",
                ],
                check=True,
            )
            revision = subprocess.check_output(
                ["git", "-C", directory, "rev-parse", "HEAD"], text=True
            ).strip()
            profile = {
                "version": "0.13.0",
                "members": {
                    name: hashlib.sha256(contents[name]).hexdigest()
                    for name in ("LICENSE", "schema.json")
                },
            }
            expected = pack_profile(root, revision, profile)
            incomplete = {
                **profile,
                "members": {
                    **profile["members"],
                    "unclosed.json": hashlib.sha256(contents["unclosed.json"]).hexdigest(),
                },
            }
            with self.assertRaisesRegex(ValueError, "Unresolved historical reference"):
                pack_profile(root, revision, incomplete)
            (root / "schema.json").write_bytes(b"working tree substitution")
            self.assertEqual(pack(root, selection(revision, profile)), expected)
            with self.assertRaisesRegex(ValueError, "Git object"):
                pack(root, selection("a" * 40, profile))
            with self.assertRaisesRegex(ValueError, "digest"):
                pack(
                    root,
                    selection(
                        revision,
                        {**profile, "members": {**profile["members"], "schema.json": "0" * 64}},
                    ),
                )

    def test_inventory_refuses_mappings_outside_profile(self) -> None:
        inventory = read_json(INVENTORY)
        validate_inventory(inventory)
        mappings = inventory["consumers"]["environment"]["selections"]["current"]["profiles"]
        next(iter(mappings.values()))["undeclared.json"] = "untrusted.json"
        with self.assertRaisesRegex(ValueError, "undeclared"):
            validate_inventory(inventory)
