"""Exercise local immutable publication with disposable storage."""

import concurrent.futures
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import contracts_publish
from scripts.validate import ROOT, read_json


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class PublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.archive = b"already packed bytes"
        self.candidate = json.dumps(
            {
                **read_json(ROOT / "distribution/tracer.json"),
                "kind": "candidate",
                "releaseId": "tracer",
                "archiveSha256": digest(self.archive),
            }
        ).encode()
        self.admission = json.dumps({"candidateSha256": digest(self.candidate)}).encode()
        self.release = self.root / "releases/tracer"

    def test_retries_preserve_candidate_and_promote_exact_tested_bytes(self) -> None:
        for _ in range(2):
            contracts_publish.stage_candidate(self.root, self.candidate, self.archive)
        self.assertEqual((self.release / "candidate.json").read_bytes(), self.candidate)
        self.assertFalse((self.release / "promoted.json").exists())
        for _ in range(2):
            contracts_publish.promote(self.root, "tracer", self.admission)
        promoted = json.loads((self.release / "promoted.json").read_bytes())
        self.assertEqual(
            promoted,
            {
                **json.loads(self.candidate),
                "kind": "promoted",
                "admissionSha256": digest(self.admission),
            },
        )
        self.assertEqual(
            (self.root / "objects" / promoted["archiveSha256"]).read_bytes(), self.archive
        )
        self.assertEqual(
            (self.root / "objects" / promoted["admissionSha256"]).read_bytes(), self.admission
        )

    def test_failed_and_interrupted_promotion_leave_no_marker(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing"):
            contracts_publish.promote(self.root, "tracer", self.admission)
        contracts_publish.stage_candidate(self.root, self.candidate, self.archive)
        with self.assertRaisesRegex(ValueError, "candidate"):
            contracts_publish.promote(self.root, "tracer", b'{"candidateSha256":"wrong"}')
        original = contracts_publish.publish_once

        def interrupt(path: Path, content: bytes) -> None:
            if path.name == "promoted.json":
                raise OSError("interrupted before marker")
            original(path, content)

        with (
            patch.object(contracts_publish, "publish_once", side_effect=interrupt),
            self.assertRaisesRegex(OSError, "interrupted"),
        ):
            contracts_publish.promote(self.root, "tracer", self.admission)
        self.assertTrue((self.root / "objects" / digest(self.admission)).exists())
        self.assertFalse((self.release / "promoted.json").exists())
        contracts_publish.promote(self.root, "tracer", self.admission)
        self.assertTrue((self.release / "promoted.json").exists())

    def test_competing_markers_cannot_replace_the_winner(self) -> None:
        contracts_publish.stage_candidate(self.root, self.candidate, self.archive)
        barrier = threading.Barrier(2)
        admissions = [self.admission, self.admission + b"\n"]

        def compete(admission: bytes) -> bytes | None:
            barrier.wait(timeout=5)
            try:
                contracts_publish.promote(self.root, "tracer", admission)
            except ValueError as error:
                self.assertIn("conflicting", str(error))
                return None
            return admission

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(compete, admissions))
        winners = [result for result in results if result is not None]
        self.assertEqual(len(winners), 1)
        promoted = json.loads((self.release / "promoted.json").read_bytes())
        self.assertEqual(promoted["admissionSha256"], digest(winners[0]))

    def test_wrong_archive_or_unsafe_release_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "digest"):
            contracts_publish.stage_candidate(self.root, self.candidate, b"wrong")
        self.assertFalse((self.release / "candidate.json").exists())
        with self.assertRaisesRegex(ValueError, "release"):
            contracts_publish.promote(self.root, "../outside", self.admission)
        contracts_publish.stage_candidate(self.root, self.candidate, self.archive)
        (self.root / "objects" / digest(self.archive)).write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "digest"):
            contracts_publish.promote(self.root, "tracer", self.admission)
        self.assertFalse((self.release / "promoted.json").exists())

    def test_conflicting_candidate_cannot_replace_tested_selection(self) -> None:
        contracts_publish.stage_candidate(self.root, self.candidate, self.archive)
        with self.assertRaisesRegex(ValueError, "conflicting"):
            contracts_publish.stage_candidate(self.root, self.candidate + b"\n", self.archive)
        self.assertEqual((self.release / "candidate.json").read_bytes(), self.candidate)
