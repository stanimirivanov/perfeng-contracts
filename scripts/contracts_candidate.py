"""Assemble a PR-only candidate through the canonical local Git packager."""

import argparse
import json
import re
import shutil
from pathlib import Path

from scripts.contracts_pack import blob, git, pack, parse_document
from scripts.contracts_publish import digest
from scripts.validate import ROOT

BUNDLE_PATHS = (
    "contracts.json",
    "schemas",
    "examples",
    "api",
    "docs",
    "tests/fixtures",
    "README.md",
    "LICENSE",
)


def prepare(root: Path, revision: str, output: Path, release_id: str) -> None:
    """Preserve the complete legacy bundle inventory as an unpromoted candidate."""
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Expected a full candidate source revision")
    if not re.fullmatch(r"pr-candidate-[1-9][0-9]{0,63}", release_id):
        raise ValueError("Invalid PR candidate identifier")
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    if git(root, "cat-file", "-t", revision) != b"commit\n":
        raise ValueError("Candidate source revision must identify a Git commit")

    members = {}
    entries = git(root, "ls-tree", "-r", "-z", revision, "--", *BUNDLE_PATHS)
    for record in entries.split(b"\0"):
        if not record:
            continue
        metadata, _, path_bytes = record.partition(b"\t")
        mode, kind, _oid = metadata.split()
        if kind != b"blob" or mode not in (b"100644", b"100755"):
            raise ValueError("Candidate inputs must be regular Git files")
        path = path_bytes.decode("ascii")
        members[path] = digest(blob(root, revision, path))
    for prefix in BUNDLE_PATHS:
        if not any(path == prefix or path.startswith(prefix + "/") for path in members):
            raise ValueError(f"Missing candidate inventory root: {prefix}")
    version = parse_document(blob(root, revision, "contracts.json"))["version"]
    selection = {
        "schemaVersion": 1,
        "kind": "selection",
        "source": {
            "repository": "https://github.com/stanimirivanov/perfeng-contracts.git",
            "revision": revision,
            "version": version,
        },
        "members": members,
    }
    archive = pack(root, selection)
    candidate = {
        **selection,
        "kind": "candidate",
        "releaseId": release_id,
        "archiveSha256": digest(archive),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    try:
        for name, content in (
            ("candidate.json", json.dumps(candidate, sort_keys=True).encode() + b"\n"),
            ("candidate.tar.gz", archive),
        ):
            with (output / name).open("xb") as stream:
                stream.write(content)
    except BaseException:
        shutil.rmtree(output)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        prepare(ROOT, args.revision, args.output, args.release_id)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"contracts-candidate: {error}\n")


if __name__ == "__main__":
    main()
