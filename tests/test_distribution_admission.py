"""Check the admission boundary with independently selected policy inputs."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.contracts_admission import admit_changed, admit_historical
from scripts.contracts_publish import digest

ARCHIVE = b"test archive"
SOURCE = {
    "repository": "https://github.com/stanimirivanov/perfeng-contracts.git",
    "revision": "a" * 40,
    "version": "0.27.0",
}
MEMBERS = {"LICENSE": "b" * 64, "schema.json": "c" * 64}
CANDIDATE = json.dumps(
    {
        "kind": "candidate",
        "schemaVersion": 1,
        "releaseId": "test-1",
        "archiveSha256": digest(ARCHIVE),
        "source": SOURCE,
        "members": MEMBERS,
    }
).encode()
CHECK = {
    "repository": "stanimirivanov/perfeng-environment",
    "sourceRevision": "e" * 40,
    "workflow": "stanimirivanov/perfeng-environment/.github/workflows/admission.yml",
    "signerRevision": "e" * 40,
    "baselineSha256": "d" * 64,
    "direction": "backward",
    "command": "make contracts-shadow",
}
POLICY = {
    "schemaVersion": 1,
    "candidateSha256": digest(CANDIDATE),
    "checks": {"environment": CHECK},
}
RECEIPT = {
    "schemaVersion": 1,
    "check": "environment",
    "candidateSha256": digest(CANDIDATE),
    "archiveSha256": digest(ARCHIVE),
    **{
        key: CHECK[key]
        for key in ("repository", "sourceRevision", "baselineSha256", "direction", "command")
    },
    "outcome": "passed",
}


class DistributionAdmissionTests(unittest.TestCase):
    @patch("scripts.contracts_admission.verify_receipt")
    def test_changed_admission_binds_authenticated_exact_bytes(self, verify) -> None:
        receipt = json.dumps(RECEIPT).encode()
        policy = json.dumps(POLICY).encode()
        result = admit_changed(
            CANDIDATE,
            policy,
            digest(policy),
            {"environment": (receipt, b"bundle")},
            Path("/trusted/gh"),
            Path("/trusted/root"),
        )
        verify.assert_called_once_with(
            Path("/trusted/gh"), Path("/trusted/root"), receipt, b"bundle", CHECK
        )
        self.assertEqual(result["receiptSha256"], {"environment": digest(receipt)})
        self.assertEqual(result["policySha256"], digest(policy))

    @patch("scripts.contracts_admission.verify_receipt")
    def test_changed_admission_rejects_missing_failed_or_wrong_receipts(self, verify) -> None:
        policy = json.dumps(POLICY).encode()
        bad = [
            {},
            {"unexpected": (b"{}", b"bundle")},
            *[
                {"environment": (json.dumps({**RECEIPT, key: value}).encode(), b"bundle")}
                for key, value in (
                    ("repository", "someone/else"),
                    ("outcome", "failed"),
                    ("candidateSha256", "0" * 64),
                    ("sourceRevision", "0" * 40),
                    ("baselineSha256", "0" * 64),
                    ("direction", "forward"),
                )
            ],
        ]
        for receipts in bad:
            with self.subTest(receipts=receipts), self.assertRaises(ValueError):
                admit_changed(
                    CANDIDATE, policy, digest(policy), receipts, Path("/gh"), Path("/root")
                )
        verify.assert_not_called()

    @patch("scripts.contracts_admission.verify_receipt", side_effect=ValueError("bad signer"))
    def test_changed_admission_requires_verifier_success(self, _verify) -> None:
        policy = json.dumps(POLICY).encode()
        receipts = {"environment": (json.dumps(RECEIPT).encode(), b"bundle")}
        with self.assertRaisesRegex(ValueError, "policy digest"):
            admit_changed(CANDIDATE, policy, "0" * 64, receipts, Path("/gh"), Path("/root"))
        with self.assertRaisesRegex(ValueError, "bad signer"):
            admit_changed(CANDIDATE, policy, digest(policy), receipts, Path("/gh"), Path("/root"))

    @patch("scripts.contracts_admission.pack_profile", return_value=ARCHIVE)
    def test_historical_admission_requires_exact_profile_and_archive(self, _pack) -> None:
        inventory = {
            "profiles": {SOURCE["revision"]: {"version": SOURCE["version"], "members": MEMBERS}}
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = admit_historical(CANDIDATE, root, inventory)
            self.assertEqual(receipt["candidateSha256"], digest(CANDIDATE))
            for field, change in (
                ("members", {"LICENSE": "0" * 64, "schema.json": "c" * 64}),
                ("archiveSha256", "0" * 64),
            ):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    candidate = json.loads(CANDIDATE)
                    candidate[field] = change
                    admit_historical(json.dumps(candidate).encode(), root, inventory)
            other = copy.deepcopy(inventory)
            other["profiles"].clear()
            with self.assertRaises(ValueError):
                admit_historical(CANDIDATE, root, other)
