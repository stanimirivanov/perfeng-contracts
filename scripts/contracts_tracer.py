"""Prepare the protected workflow's fixed tracer publication inputs locally."""

import argparse
import json
import re
import tempfile
from pathlib import Path

from scripts.contracts_pack import pack
from scripts.contracts_publish import digest, promote, stage_candidate
from scripts.validate import ROOT, read_json


def prepare(output: Path, release_id: str) -> None:
    """Bind a fixed selection, tested archive, and local admission in a manifest."""
    if not re.fullmatch(r"contract-tracer-[1-9][0-9]{0,63}", release_id):
        raise ValueError("Invalid tracer release identifier")
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)

    selection = read_json(ROOT / "distribution/tracer.json")
    archive = pack(ROOT, selection)
    candidate = (
        json.dumps(
            {
                **selection,
                "kind": "candidate",
                "releaseId": release_id,
                "archiveSha256": digest(archive),
            },
            sort_keys=True,
        ).encode()
        + b"\n"
    )
    admission = (
        json.dumps(
            {"candidateSha256": digest(candidate), "check": "tracer-exact-git-selection/v1"},
            sort_keys=True,
        ).encode()
        + b"\n"
    )
    with tempfile.TemporaryDirectory(prefix="contract-tracer-") as directory:
        store = Path(directory)
        stage_candidate(store, candidate, archive)
        promoted = promote(store, release_id, admission)

    output.mkdir()
    for name, content in (
        ("admission.json", admission),
        ("candidate.json", candidate),
        ("manifest.json", promoted),
        ("tracer.tar.gz", archive),
    ):
        (output / name).write_bytes(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    args = parser.parse_args()
    try:
        prepare(args.output, args.release_id)
    except (OSError, ValueError) as error:
        parser.exit(1, f"contracts-tracer: {error}\n")


if __name__ == "__main__":
    main()
