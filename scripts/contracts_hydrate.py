"""Explicitly acquire missing reviewed historical Git commits before offline packaging."""

import argparse
import subprocess
from collections.abc import Iterable
from pathlib import Path

from scripts.contracts_history import INVENTORY, REVISION
from scripts.contracts_pack import git
from scripts.validate import ROOT, read_json


def fetch(root: Path, revision: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), "fetch", "--no-tags", "origin", revision],
        check=True,
        timeout=120,
    )


def hydrate(root: Path, revisions: Iterable[str]) -> None:
    """Fetch exact missing commit IDs and require each to be readable locally."""
    selected = sorted(set(revisions))
    if not selected or any(not REVISION.fullmatch(revision) for revision in selected):
        raise ValueError("Invalid historical revision inventory")
    for revision in selected:
        try:
            object_type = git(root, "cat-file", "-t", revision)
        except ValueError:
            fetch(root, revision)
            try:
                object_type = git(root, "cat-file", "-t", revision)
            except ValueError as error:
                raise ValueError(f"Historical Git commit still missing: {revision}") from error
        if object_type != b"commit\n":
            raise ValueError(f"Historical revision is not a Git commit: {revision}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        hydrate(args.source, read_json(INVENTORY)["profiles"])
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f"contracts-hydrate: {error}\n")


if __name__ == "__main__":
    main()
