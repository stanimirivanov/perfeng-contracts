"""Check that history preparation hydrates only reviewed missing commits."""

import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.contracts_hydrate import hydrate


class HistoryHydrationTests(unittest.TestCase):
    @patch("scripts.contracts_hydrate.fetch")
    @patch("scripts.contracts_hydrate.git")
    def test_fetches_each_missing_reviewed_revision_and_rechecks(self, git, fetch) -> None:
        root = Path("/fixture")
        existing, missing = "a" * 40, "b" * 40
        git.side_effect = [b"commit\n", ValueError("missing"), b"commit\n"]
        hydrate(root, [missing, existing])
        fetch.assert_called_once_with(root, missing)
        self.assertEqual(git.call_args.args, (root, "cat-file", "-t", missing))

    @patch("scripts.contracts_hydrate.fetch")
    @patch("scripts.contracts_hydrate.git")
    def test_refuses_invalid_revisions_before_fetch(self, git, fetch) -> None:
        with self.assertRaisesRegex(ValueError, "revision"):
            hydrate(Path("/fixture"), ["a" * 40, "--all"])
        git.assert_not_called()
        fetch.assert_not_called()

    @patch("scripts.contracts_hydrate.fetch")
    @patch("scripts.contracts_hydrate.git", side_effect=ValueError("missing"))
    def test_missing_object_after_fetch_fails(self, _git, _fetch) -> None:
        with self.assertRaisesRegex(ValueError, "missing"):
            hydrate(Path("/fixture"), ["b" * 40])
