"""Relocate generated local pointers without hoisting component-owned definitions."""

from __future__ import annotations

import copy
import json
import os
import posixpath
import re
from pathlib import Path
from typing import Any


def fragment_outputs(document: dict[str, Any]) -> dict[str, str]:
    root = copy.deepcopy(document)
    schema_files = {
        name: f"components/schemas/{name}.json" for name in document["components"]["schemas"]
    }
    if any(not re.fullmatch(r"[A-Za-z0-9_.-]+", name) for name in schema_files):
        raise ValueError("Unsupported component name")

    def relocate(value: Any, owner: str) -> Any:
        if isinstance(value, list):
            return [relocate(item, owner) for item in value]
        if not isinstance(value, dict):
            return value
        output = {}
        for key, item in value.items():
            if key in {"$id", "$dynamicRef", "$recursiveRef"}:
                raise ValueError(
                    "Schema identity/dynamic reference needs separate emitter admission"
                )
            if key == "$ref":
                prefix = "#/components/schemas/"
                if not isinstance(item, str) or not item.startswith(prefix):
                    raise ValueError("Expected a declared document-root schema reference")
                name, separator, suffix = item[len(prefix) :].partition("/")
                if name not in schema_files:
                    raise ValueError("Undeclared component reference")
                relative = os.path.relpath(schema_files[name], posixpath.dirname(owner) or ".")
                if schema_files[name] == owner:
                    relative = ""
                output[key] = relative + ("#/" + suffix if separator else "")
            else:
                output[key] = relocate(item, owner)
        return output

    fragments: dict[str, Any] = {}
    for path, item in document["paths"].items():
        name = "paths/" + path.strip("/").replace("/", "_") + ".json"
        if name in fragments or ".." in name or "\\" in name:
            raise ValueError("Ambiguous operation fragment path")
        fragments[name] = relocate(item, name)
        root["paths"][path] = {"$ref": name}
    for name, schema in document["components"]["schemas"].items():
        owner = schema_files[name]
        fragments[owner] = relocate(schema, owner)
        root["components"]["schemas"][name] = {"$ref": owner}
    fragments["openapi.json"] = root
    return {name: json.dumps(value, indent=2) + "\n" for name, value in sorted(fragments.items())}


def assemble(files: dict[str, Any]) -> dict[str, Any]:
    root = copy.deepcopy(files["openapi.json"])
    anchors = {
        pointer["$ref"]: "#/components/schemas/" + name
        for name, pointer in root["components"]["schemas"].items()
    }

    def restore(value: Any, owner: str) -> Any:
        if isinstance(value, list):
            return [restore(item, owner) for item in value]
        if not isinstance(value, dict):
            return value
        output = {}
        for key, item in value.items():
            if key == "$ref":
                path, separator, fragment = item.partition("#")
                target = (
                    posixpath.normpath(posixpath.join(posixpath.dirname(owner), path))
                    if path
                    else owner
                )
                if target not in anchors:
                    raise ValueError("Reference has no declared component anchor")
                output[key] = anchors[target] + (fragment if separator else "")
            else:
                output[key] = restore(item, owner)
        return output

    for path, reference in root["paths"].items():
        name = reference["$ref"]
        root["paths"][path] = restore(files[name], name)
    for name, reference in root["components"]["schemas"].items():
        owner = reference["$ref"]
        root["components"]["schemas"][name] = restore(files[owner], owner)
    return root


def write_fragments(root: Path, outputs: dict[str, str], check: bool) -> None:
    if root.is_symlink() or any(path.is_symlink() for path in root.rglob("*")):
        raise ValueError("Generated source symlink")
    actual = (
        sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
        if root.exists()
        else []
    )
    if any(name not in outputs for name in actual):
        raise ValueError("Unexpected generated Integration fragment")
    for name, contents in outputs.items():
        path = root / name
        if check:
            if not path.is_file() or path.read_text() != contents:
                raise ValueError(f"Stale generated Integration fragment: {name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents)
