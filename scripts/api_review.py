"""Produce conservative, direction-aware API change receipts without resolving remote input."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

MISSING = object()
METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
APIS = (
    "api/run-management/v1/openapi.json",
    "api/native-worker/v2/openapi.json",
    "api/performance-integration/v1/openapi.json",
)


def canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: sorted(item, key=lambda entry: json.dumps(entry, sort_keys=True))
            if key in {"required", "enum"} and isinstance(item, list)
            else canonical(item)
            for key, item in sorted(value.items())
        }
    if isinstance(value, list):
        return [canonical(item) for item in value]
    return value


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(canonical(value), sort_keys=True).encode()).hexdigest()


def directions(document: dict[str, Any]) -> dict[str, set[str]]:
    usage: dict[str, set[str]] = {}

    def visit(value: Any, direction: str, seen: set[str]) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item, direction, seen)
        if not isinstance(value, dict):
            return
        for key, item in value.items():
            if key == "$ref":
                if not isinstance(item, str) or not item.startswith("#/components/"):
                    raise ValueError("Only local component references are admitted")
                parts = item[2:].split("/")
                if parts[:2] == ["components", "schemas"]:
                    usage.setdefault(parts[2], set()).add(direction)
                if item not in seen:
                    target: Any = document
                    for part in parts:
                        target = target[part.replace("~1", "/").replace("~0", "~")]
                    visit(target, direction, seen | {item})
            else:
                visit(item, direction, seen)

    for path in document.get("paths", {}).values():
        for method, operation in path.items():
            if method not in METHODS:
                continue
            visit(operation.get("requestBody", {}), "request", set())
            visit(operation.get("parameters", []), "request", set())
            visit(operation.get("responses", {}), "response", set())
    return usage


def classify(path: list[str], before: Any, after: Any, uses: set[str]) -> str:
    key = path[-1]
    if key in {"description", "summary", "title", "externalDocs"} and path[-2] not in {
        "properties",
        "schemas",
        "headers",
        "parameters",
    }:
        return "documentation"
    if path[0] == "paths" and len(path) <= 3 and after is MISSING:
        return "breaking"
    if key in {"required", "enum"} and isinstance(before, list) and isinstance(after, list):
        removed = set(before) - set(after)
        added = set(after) - set(before)
        if key == "required":
            broken = (added and "request" in uses) or (removed and "response" in uses)
        else:
            broken = (removed and "request" in uses) or (added and "response" in uses)
        if broken:
            return "breaking"
    return "review"


def review(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    usage = directions(before)
    for name, values in directions(after).items():
        usage.setdefault(name, set()).update(values)
    changes: list[dict[str, Any]] = []

    def compare(left: Any, right: Any, path: list[str]) -> None:
        if left == right:
            return
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(set(left) | set(right)):
                compare(left.get(key, MISSING), right.get(key, MISSING), [*path, key])
            return
        uses = usage.get(path[2], set()) if path[:2] == ["components", "schemas"] else set()
        changes.append(
            {
                "pointer": "/"
                + "/".join(part.replace("~", "~0").replace("/", "~1") for part in path),
                "directions": sorted(uses),
                "classification": classify(path, left, right, uses),
                "beforePresent": left is not MISSING,
                "afterPresent": right is not MISSING,
                "before": None if left is MISSING else left,
                "after": None if right is MISSING else right,
            }
        )

    compare(canonical(before), canonical(after), [])
    keywords: set[str] = set()

    def inventory(value: Any) -> None:
        if not isinstance(value, dict):
            return
        keywords.update(value)
        for key, item in value.items():
            if key in {"properties", "$defs", "patternProperties", "dependentSchemas"}:
                for child in item.values():
                    inventory(child)
            elif isinstance(item, list):
                for child in item:
                    inventory(child)
            elif isinstance(item, dict):
                inventory(item)

    for schema in after.get("components", {}).get("schemas", {}).values():
        inventory(schema)
    operations = [
        {"method": method.upper(), "path": path, "operationId": operation.get("operationId")}
        for path, methods in sorted(after.get("paths", {}).items())
        for method, operation in sorted(methods.items())
        if method in METHODS
    ]
    return {
        "beforeSha256": digest(before),
        "afterSha256": digest(after),
        "operations": operations,
        "schemaKeywords": sorted(keywords),
        "schemaRoots": sorted(after.get("components", {}).get("schemas", {})),
        "changes": changes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path)
    parser.add_argument("--after", type=Path)
    args = parser.parse_args()
    if bool(args.before) != bool(args.after):
        parser.error("Provide both --before and --after")
    if args.before:
        receipt = review(json.loads(args.before.read_text()), json.loads(args.after.read_text()))
        print(json.dumps(receipt, indent=2))
        if any(item["classification"] != "documentation" for item in receipt["changes"]):
            raise SystemExit(1)
    else:
        receipts = {
            path: review(json.loads(Path(path).read_text()), json.loads(Path(path).read_text()))
            for path in APIS
        }
        print(json.dumps(receipts, indent=2))


if __name__ == "__main__":
    main()
