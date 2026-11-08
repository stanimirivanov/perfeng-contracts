"""Exercise packing against immutable objects in a disposable Git repository."""

import hashlib
import io
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.contracts_pack import pack


class ContractPackTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.git("init", "-q", "--object-format=sha1")
        self.members = {"z.json": b'{"a":1}\n', "LICENSE": b"fixture licence\n"}
        for name, content in self.members.items():
            (self.root / name).write_bytes(content)
        (self.root / "contracts.json").write_text('{"version":"0.22.0"}', encoding="utf-8")
        (self.root / "alias").symlink_to("z.json")
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
        self.selection: dict[str, Any] = {
            "schemaVersion": 1,
            "kind": "selection",
            "source": {
                "repository": "https://github.com/stanimirivanov/perfeng-contracts.git",
                "revision": self.git("rev-parse", "HEAD").strip(),
                "version": "0.22.0",
            },
            "members": {
                path: hashlib.sha256(content).hexdigest() for path, content in self.members.items()
            },
        }

    def git(self, *args: str) -> str:
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True, env=env)

    def test_deterministic_archive_reads_only_declared_git_bytes(self) -> None:
        first = pack(self.root, self.selection)
        (self.root / "z.json").write_bytes(b"dirty checkout")
        self.selection["members"] = dict(reversed(list(self.selection["members"].items())))
        self.assertEqual(first, pack(self.root, self.selection))
        with tarfile.open(fileobj=io.BytesIO(first), mode="r:gz") as archive:
            self.assertEqual(archive.getnames(), sorted(self.members))
            for member in archive:
                self.assertEqual(
                    (member.uid, member.gid, member.mode, member.mtime), (0, 0, 0o644, 0)
                )
                stream = archive.extractfile(member)
                assert stream is not None
                with stream:
                    self.assertEqual(stream.read(), self.members[member.name])

    def test_rejects_unsafe_or_unavailable_members(self) -> None:
        for path, error in (
            ("../z.json", "selection"),
            ("missing", "missing"),
            ("alias", "regular"),
            ("Z.JSON", "conflicting"),
            ("z.json/child", "conflicting"),
        ):
            with self.subTest(path=path):
                members = {**self.selection["members"], path: hashlib.sha256(b"z.json").hexdigest()}
                with self.assertRaisesRegex(ValueError, error):
                    pack(self.root, {**self.selection, "members": members})

    def test_rejects_mismatched_source_or_bytes(self) -> None:
        for field, value, error in (
            ("revision", "a" * 40, "Git"),
            ("version", "0.23.0", "version"),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, error):
                pack(
                    self.root,
                    {**self.selection, "source": {**self.selection["source"], field: value}},
                )
        with self.assertRaisesRegex(ValueError, "digest"):
            pack(
                self.root,
                {**self.selection, "members": {**self.selection["members"], "z.json": "a" * 64}},
            )
