"""Bundle declared local JSON fragments with the pinned Redocly tool."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit

if __package__:
    from .api_review import digest
    from .integration_sources import assemble, fragment_outputs, write_fragments
else:
    from api_review import digest
    from integration_sources import assemble, fragment_outputs, write_fragments

ROOT = Path(__file__).resolve().parents[1]
CONFIG = {"extends": [], "rules": {}, "preprocessors": {}, "decorators": {}}


def owned_api_path(relative: str) -> Path:
    if (
        not isinstance(relative, str)
        or "\\" in relative
        or relative.split("/")[0] != "api"
        or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        raise ValueError("API ownership requires canonical relative paths")
    path = ROOT / relative
    # Equality rejects aliases anywhere in the ancestry, including aliases
    # that resolve into another otherwise permitted location inside api/.
    if path.resolve() != path:
        raise ValueError("Noncanonical API ownership path or symlink ancestor")
    return path


def load_source(root: Path, expected: list[str]) -> dict[str, Any]:
    if root.is_symlink():
        raise ValueError("Source root symlink")
    files: dict[str, Any] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Source symlink")
        if path.is_file():
            name = path.relative_to(root).as_posix()
            if name not in expected or path.suffix != ".json":
                raise ValueError("Source inventory mismatch")
            files[name] = json.loads(path.read_text())
    if len(expected) != len(set(expected)) or sorted(files) != sorted(expected):
        raise ValueError("Source inventory mismatch")

    def visit(value: Any, owner: str) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item, owner)
        if not isinstance(value, dict):
            return
        for key, item in value.items():
            if key in {"$ref", "$dynamicRef", "$recursiveRef"}:
                if not isinstance(item, str):
                    raise ValueError("Reference must be a string")
                url = urlsplit(item)
                if url.scheme or url.netloc or url.query or unquote(item) != item or "\\" in item:
                    raise ValueError("Remote or encoded reference")
                path = Path(owner).parent / url.path if url.path else Path(owner)
                resolved = (root / path).resolve()
                if not resolved.is_relative_to(root.resolve()):
                    raise ValueError("Escaping reference")
                name = resolved.relative_to(root.resolve()).as_posix()
                if name not in files:
                    raise ValueError("Undeclared reference")
                target = files[name]
                if url.fragment and not url.fragment.startswith("/"):
                    raise ValueError("Unsupported pointer")
                for part in url.fragment.split("/")[1:]:
                    try:
                        target = target[part.replace("~1", "/").replace("~0", "~")]
                    except (KeyError, TypeError) as error:
                        raise ValueError("Missing pointer") from error
            else:
                visit(item, owner)

    for owner, value in files.items():
        visit(value, owner)
    if "openapi.json" not in files:
        raise ValueError("Missing source root")
    return files


def build(entry: dict[str, Any], check: bool) -> None:
    source = owned_api_path(entry["root"])
    destination = owned_api_path(entry["output"])
    if source.name != "source":
        raise ValueError("Source is outside the API authoring tree")
    load_source(source, entry["files"])
    config = ROOT / "redocly.yaml"
    if config.is_symlink() or json.loads(config.read_text()) != CONFIG:
        raise ValueError("Bundler configuration differs from admitted local policy")
    mode = entry.get("mode", "redocly")
    if mode == "effect-components":
        document = assemble(load_source(source, entry["files"]))
    elif mode == "redocly":
        cli = ROOT / "node_modules/@redocly/cli/bin/cli.js"
        with tempfile.TemporaryDirectory(prefix="perfeng-api-bundle-") as directory:
            output = Path(directory) / "openapi.json"
            subprocess.run(
                [
                    "sh",
                    str(ROOT / "scripts/offline-node.sh"),
                    str(cli),
                    "bundle",
                    str(source / "openapi.json"),
                    "--config",
                    str(config),
                    "--component-renaming-conflicts-severity=error",
                    "--output",
                    str(output),
                ],
                check=True,
                cwd=ROOT,
                env={**os.environ, "REDOCLY_TELEMETRY": "off"},
            )
            document = json.loads(output.read_text())
    else:
        raise ValueError("Unreviewed API assembly mode")
    if digest(document) != entry["semanticSha256"]:
        raise ValueError("Semantic change requires explicit identity and compatibility review")
    generated = json.dumps(document, indent=2) + "\n"
    if check:
        if destination.read_text() != generated:
            raise ValueError(f"Stale API bundle: {entry['output']}")
    else:
        destination.write_text(generated)


def check_release_inventory() -> None:
    inventory = json.loads((ROOT / "contracts/api-release-files.json").read_text())
    actual = sorted(
        path.relative_to(ROOT).as_posix() for path in (ROOT / "api").rglob("*") if path.is_file()
    )
    if actual != inventory:
        raise ValueError("API release inventory changed without review")
    if any(
        PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts for name in inventory
    ):
        raise ValueError("Invalid release inventory")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--integration", action="store_true")
    args = parser.parse_args()
    registry = json.loads((ROOT / "contracts/api-sources.json").read_text())
    for entry in registry["apis"]:
        owned_api_path(entry["root"])
        owned_api_path(entry["output"])
    if args.integration:
        entries = [entry for entry in registry["apis"] if entry.get("mode") == "effect-components"]
        if len(entries) != 1:
            raise ValueError("Expected one reviewed Effect Integration source")
        entry = entries[0]
        source = owned_api_path(entry["root"])
        if source.name != "source":
            raise ValueError("Invalid generated source root")
        outputs = fragment_outputs(json.load(sys.stdin))
        if sorted(outputs) != sorted(entry["files"]):
            raise ValueError("Generated Integration inventory requires review")
        write_fragments(source, outputs, not args.write)
    check_release_inventory()
    for entry in registry["apis"]:
        build(entry, not args.write)


if __name__ == "__main__":
    main()
