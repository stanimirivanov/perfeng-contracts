"""Package an explicit distribution selection from local Git objects."""

import argparse
import gzip
import hashlib
import io
import json
import os
import subprocess
import tarfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scripts.validate import ROOT, parse_finite_float, read_json, reject_nonfinite_constant

MAX_MEMBER_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_MEMBERS = 4096


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate key in distribution input")
        result[key] = value
    return result


def parse_document(content: bytes) -> Any:
    return json.loads(
        content.decode("utf-8"),
        object_pairs_hook=unique_object,
        parse_constant=reject_nonfinite_constant,
        parse_float=parse_finite_float,
    )


def git(root: Path, *args: str) -> bytes:
    """Read local objects with replace refs and implicit network access disabled."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_NO_LAZY_FETCH="1", GIT_ALLOW_PROTOCOL="")
    try:
        return subprocess.check_output(
            ["git", "--no-replace-objects", "--literal-pathspecs", "-C", str(root), *args],
            env=env,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("Cannot read required local Git object") from error


def blob(root: Path, revision: str, path: str) -> bytes:
    entry = git(root, "ls-tree", "-z", revision, "--", path)
    if not entry:
        raise ValueError(f"Declared member is missing: {path}")
    metadata, _, name = entry.partition(b"\t")
    mode, kind, oid = metadata.split()
    if (
        name != path.encode("ascii") + b"\0"
        or kind != b"blob"
        or mode not in (b"100644", b"100755")
    ):
        raise ValueError(f"Expected a regular Git file: {path}")
    object_id = oid.decode("ascii")
    size = int(git(root, "cat-file", "-s", object_id))
    if size > MAX_MEMBER_BYTES:
        raise ValueError(f"Git blob exceeds size limit: {path}")
    return git(root, "cat-file", "blob", object_id)


def pack(root: Path, selection: dict[str, Any]) -> bytes:
    """Return a gzip-compressed tar containing only the declared, verified blobs."""
    validator = Draft202012Validator(read_json(ROOT / "distribution/manifest.schema.json"))
    if not validator.is_valid(selection) or selection["kind"] != "selection":
        raise ValueError("Invalid distribution selection")
    revision = selection["source"]["revision"]
    if git(root, "cat-file", "-t", revision) != b"commit\n":
        raise ValueError("Git source revision must identify a commit")
    version = parse_document(blob(root, revision, "contracts.json"))
    if not isinstance(version, dict) or version.get("version") != selection["source"]["version"]:
        raise ValueError("Selected version differs from pinned contracts.json")

    members = selection["members"]
    if len(members) > MAX_MEMBERS:
        raise ValueError("Selection exceeds member limit")
    paths = {path.lower() for path in members}
    if len(paths) != len(members) or any(
        str(parent) in paths for path in paths for parent in Path(path).parents
    ):
        raise ValueError("Selection contains conflicting member paths")

    output = io.BytesIO()
    total = 0
    with gzip.GzipFile(
        fileobj=output, mode="wb", filename="", mtime=0, compresslevel=9
    ) as compressed:
        with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as archive:
            for path, expected in sorted(members.items()):
                content = blob(root, revision, path)
                total += len(content)
                if total > MAX_TOTAL_BYTES:
                    raise ValueError("Selection exceeds total size limit")
                if hashlib.sha256(content).hexdigest() != expected:
                    raise ValueError(f"Declared digest differs from Git blob: {path}")
                info = tarfile.TarInfo(path)
                info.size = len(content)
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(content))
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        archive = pack(args.source, parse_document(args.selection.read_bytes()))
        with args.output.open("xb") as stream:
            stream.write(archive)
    except (OSError, ValueError) as error:
        parser.exit(1, f"contracts-pack: {error}\n")


if __name__ == "__main__":
    main()
