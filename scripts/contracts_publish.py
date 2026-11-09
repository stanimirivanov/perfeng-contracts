"""Stage and promote immutable contract releases in a trusted local fixture directory."""

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scripts.contracts_pack import MAX_TOTAL_BYTES, parse_document
from scripts.validate import ROOT, read_json

MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
MAX_ARCHIVE_BYTES = MAX_TOTAL_BYTES + 16 * 1024 * 1024
RELEASE_ID = re.compile(r"[a-z0-9][a-z0-9.-]{0,127}")


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def read_bounded(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Required file is missing or nonregular: {path.name}")
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError(f"File exceeds size limit: {path.name}")
    return content


def local_directory(path: Path) -> Path:
    path.mkdir(exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"Expected a local directory: {path.name}")
    return path


def release_directory(root: Path, release_id: str) -> Path:
    if not RELEASE_ID.fullmatch(release_id):
        raise ValueError("Invalid release identifier")
    return local_directory(local_directory(root / "releases") / release_id)


def publish_once(path: Path, content: bytes) -> None:
    """Install complete bytes atomically without replacing a competing writer."""
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".staging-") as staging:
        staging.write(content)
        staging.flush()
        os.fsync(staging.fileno())
        try:
            os.link(staging.name, path)
        except FileExistsError as error:
            if read_bounded(path, len(content)) != content:
                raise ValueError(f"Refusing conflicting publication: {path.name}") from error


def manifest(content: bytes, kind: str) -> dict[str, Any]:
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError("Manifest exceeds size limit")
    value = parse_document(content)
    schema = read_json(ROOT / "distribution/manifest.schema.json")
    if not Draft202012Validator(schema).is_valid(value) or value["kind"] != kind:
        raise ValueError(f"Expected a valid {kind} manifest")
    return value


def stage_candidate(root: Path, candidate: bytes, archive: bytes) -> None:
    """Publish the candidate marker after its verified archive is available."""
    value = manifest(candidate, "candidate")
    archive_digest = value["archiveSha256"]
    if len(archive) > MAX_ARCHIVE_BYTES or digest(archive) != archive_digest:
        raise ValueError("Archive size or digest differs from candidate")
    release = release_directory(root, value["releaseId"])
    objects = local_directory(root / "objects")
    publish_once(objects / archive_digest, archive)
    publish_once(release / "candidate.json", candidate)


def promote(root: Path, release_id: str, admission: bytes) -> bytes:
    """Bind the tested candidate and admission record in a final local marker."""
    release = release_directory(root, release_id)
    candidate = read_bounded(release / "candidate.json", MAX_DOCUMENT_BYTES)
    value = manifest(candidate, "candidate")
    if value["releaseId"] != release_id:
        raise ValueError("Candidate release identifier differs from directory")
    if len(admission) > MAX_DOCUMENT_BYTES:
        raise ValueError("Admission record exceeds size limit")
    record = parse_document(admission)
    if not isinstance(record, dict) or record.get("candidateSha256") != digest(candidate):
        raise ValueError("Admission record does not bind the exact candidate")
    objects = local_directory(root / "objects")
    archive = read_bounded(objects / value["archiveSha256"], MAX_ARCHIVE_BYTES)
    if digest(archive) != value["archiveSha256"]:
        raise ValueError("Stored archive digest differs from candidate")

    admission_digest = digest(admission)
    promoted = (
        json.dumps(
            {**value, "kind": "promoted", "admissionSha256": admission_digest},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        + b"\n"
    )
    manifest(promoted, "promoted")
    publish_once(objects / admission_digest, admission)
    publish_once(release / "promoted.json", promoted)
    return promoted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    actions = parser.add_subparsers(dest="action", required=True)
    stage = actions.add_parser("stage")
    stage.add_argument("--candidate", required=True, type=Path)
    stage.add_argument("--archive", required=True, type=Path)
    promote_parser = actions.add_parser("promote")
    promote_parser.add_argument("--release-id", required=True)
    promote_parser.add_argument("--admission", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.action == "stage":
            stage_candidate(
                args.root,
                read_bounded(args.candidate, MAX_DOCUMENT_BYTES),
                read_bounded(args.archive, MAX_ARCHIVE_BYTES),
            )
        else:
            promote(args.root, args.release_id, read_bounded(args.admission, MAX_DOCUMENT_BYTES))
    except (OSError, ValueError, RecursionError) as error:
        parser.exit(1, f"contracts-publish: {error}\n")


if __name__ == "__main__":
    main()
