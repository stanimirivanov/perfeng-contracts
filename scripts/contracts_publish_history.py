"""Prepare a complete admitted batch from reviewed historical contract profiles."""

import argparse
import json
import re
import shutil
import tempfile
from pathlib import Path

from scripts.contracts_admission import admit_historical
from scripts.contracts_history import INVENTORY, pack_profile, selection, validate_inventory
from scripts.contracts_publish import digest, promote, stage_candidate
from scripts.validate import ROOT, read_json


def encode(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def prepare(output: Path, release_id: str) -> None:
    """Emit one archive, candidate, admission and promoted manifest per profile."""
    if not re.fullmatch(r"contract-history-[1-9][0-9]{0,63}", release_id):
        raise ValueError("Invalid historical release identifier")
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    inventory = read_json(INVENTORY)
    validate_inventory(inventory)
    manifests: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="perfeng-history-publish-") as directory:
        root = Path(directory)
        assets = root / "assets"
        assets.mkdir()
        for revision, profile in sorted(inventory["profiles"].items()):
            archive = pack_profile(ROOT, revision, profile)
            candidate = encode(
                {
                    **selection(revision, profile),
                    "kind": "candidate",
                    "releaseId": release_id,
                    "archiveSha256": digest(archive),
                }
            )
            admission = encode(admit_historical(candidate, ROOT, inventory))
            store = root / revision
            store.mkdir()
            stage_candidate(store, candidate, archive)
            promoted = promote(store, release_id, admission)
            for name, content in (
                ("tar.gz", archive),
                ("candidate.json", candidate),
                ("admission.json", admission),
                ("manifest.json", promoted),
            ):
                (assets / f"{revision}.{name}").write_bytes(content)
            manifests[revision] = digest(promoted)
        output.mkdir()
        for path in sorted(assets.iterdir()):
            shutil.copyfile(path, output / path.name)
        (output / "catalog.manifest.json").write_bytes(
            encode(
                {
                    "schemaVersion": 1,
                    "releaseId": release_id,
                    "profiles": manifests,
                }
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    args = parser.parse_args()
    try:
        prepare(args.output, args.release_id)
    except (OSError, ValueError) as error:
        parser.exit(1, f"contracts-publish-history: {error}\n")


if __name__ == "__main__":
    main()
