"""Check and package the reviewed inventory of exact historical contract inputs."""

import argparse
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

from referencing import Registry, Resource
from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT202012

from scripts.contracts_pack import pack, parse_document
from scripts.validate import ROOT, no_network, read_json, references

INVENTORY = ROOT / "distribution/supported-selections.json"
REPOSITORY = "https://github.com/stanimirivanov/perfeng-contracts.git"
REVISION = re.compile(r"[a-f0-9]{40}")
DIGEST = re.compile(r"[a-f0-9]{64}")
PATH = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*(/[A-Za-z0-9_][A-Za-z0-9_.-]*)*")


def selection(revision: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Project one inventory profile into the existing single-source pack contract."""
    return {
        "schemaVersion": 1,
        "kind": "selection",
        "source": {"repository": REPOSITORY, "revision": revision, "version": profile["version"]},
        "members": profile["members"],
    }


def validate_inventory(inventory: dict[str, Any]) -> None:
    """Reject ambiguous mappings and profiles with no recorded consumer selection."""
    if inventory["schemaVersion"] != 1:
        raise ValueError("Unsupported historical inventory version")
    profiles = inventory["profiles"]
    used: set[str] = set()
    for consumer in inventory["consumers"].values():
        if (
            consumer["deploymentStatus"] != "unknown"
            or consumer["rollbackStatus"] != "unknown"
            or consumer["replayStatus"] != "unknown"
            or "current" not in consumer["selections"]
        ):
            raise ValueError("Expected an observed selection with explicit unqualified retention")
        for observation in consumer["selections"].values():
            if not (
                REVISION.fullmatch(observation["consumerRevision"])
                and DIGEST.fullmatch(observation["lockSha256"])
                and PATH.fullmatch(observation["lockPath"])
            ):
                raise ValueError("Invalid consumer lock provenance")
            destinations: set[str] = set()
            for revision, mapping in observation["profiles"].items():
                if not REVISION.fullmatch(revision) or revision not in profiles or not mapping:
                    raise ValueError("Unknown or empty historical profile")
                used.add(revision)
                for source, destination in mapping.items():
                    if source not in profiles[revision]["members"]:
                        raise ValueError("Consumer selects an undeclared historical member")
                    if destination is None:
                        continue
                    if not PATH.fullmatch(destination) or destination.lower() in destinations:
                        raise ValueError("Unsafe or ambiguous historical destination")
                    destinations.add(destination.lower())
            if any(
                parent.as_posix() in destinations
                for name in destinations
                for parent in PurePosixPath(name).parents
            ):
                raise ValueError("Conflicting historical destination hierarchy")
    if used != profiles.keys():
        raise ValueError("Historical profiles must have recorded consumer selections")


def pack_profile(root: Path, revision: str, profile: dict[str, Any]) -> bytes:
    """Require an exact byte archive whose JSON references resolve within it."""
    archive = pack(root, selection(revision, profile))
    documents = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as stream:
        for member in stream:
            if member.name.endswith(".json"):
                content = stream.extractfile(member)
                assert content is not None
                documents[member.name] = parse_document(content.read())
    registry = Registry(retrieve=no_network).with_resources(
        (
            "https://perfeng.dev/" + path,
            Resource.from_contents(value, default_specification=DRAFT202012),
        )
        for path, value in documents.items()
    )
    for path, value in documents.items():
        resolver = registry.resolver("https://perfeng.dev/" + path)
        for reference in references(value):
            try:
                resolver.lookup(reference)
            except Unresolvable as error:
                raise ValueError(
                    f"Unresolved historical reference in {path}: {reference}"
                ) from error
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--revision")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and not args.revision:
        parser.error("--output requires an explicit --revision")
    try:
        inventory = read_json(INVENTORY)
        validate_inventory(inventory)
        profiles = inventory["profiles"]
        revisions = [args.revision] if args.revision else sorted(profiles)
        if any(revision not in profiles for revision in revisions):
            raise ValueError("Revision is not in the historical inventory")
        receipts = []
        for revision in revisions:
            data = pack_profile(args.source, revision, profiles[revision])
            if args.output:
                with args.output.open("xb") as output:
                    output.write(data)
            receipts.append(
                {"revision": revision, "archiveSha256": hashlib.sha256(data).hexdigest()}
            )
        print(json.dumps(receipts, indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, f"contracts-history: {error}\n")


if __name__ == "__main__":
    main()
