"""Produce conservative, direction-aware API change receipts without resolving remote input."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

MISSING = object()
METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
APIS = (
    "api/run-management/v1/openapi.json",
    "api/native-worker/v2/openapi.json",
    "api/performance-integration/v1/openapi.json",
)


SCHEMA_MAPS = {"properties", "patternProperties", "$defs", "definitions", "dependentSchemas"}
SCHEMA_ARRAYS = {"allOf", "anyOf", "oneOf", "prefixItems"}
SCHEMA_CHILDREN = {
    "additionalProperties",
    "unevaluatedProperties",
    "items",
    "additionalItems",
    "contains",
    "not",
    "if",
    "then",
    "else",
    "propertyNames",
    "unevaluatedItems",
    "contentSchema",
}
LITERAL_FIELDS = {"const", "default", "example", "examples"}


def literal(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: literal(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [literal(item) for item in value]
    return value


def canonical_schema(value: Any) -> Any:
    if isinstance(value, list):
        return [canonical_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    output = {}
    for key, item in sorted(value.items()):
        if key in {"required", "enum"} and isinstance(item, list):
            output[key] = sorted(
                (literal(entry) for entry in item),
                key=lambda entry: json.dumps(entry, sort_keys=True),
            )
        elif key in SCHEMA_MAPS and isinstance(item, dict):
            output[key] = {name: canonical_schema(child) for name, child in sorted(item.items())}
        elif key in SCHEMA_ARRAYS and isinstance(item, list):
            output[key] = [canonical_schema(child) for child in item]
        elif key in SCHEMA_CHILDREN:
            output[key] = canonical_schema(item)
        else:
            # Literal and unknown keyword values retain all array ordering.
            output[key] = literal(item)
    return output


def canonical(value: Any, path: tuple[str, ...] = ()) -> Any:
    if (len(path) == 3 and path[:2] == ("components", "schemas")) or (
        path and path[0] in {"paths", "components"} and path[-1] == "schema"
    ):
        return canonical_schema(value)
    if isinstance(value, dict):
        return {
            key: literal(item)
            if key in LITERAL_FIELDS or key.startswith("x-")
            else canonical(item, (*path, key))
            for key, item in sorted(value.items())
        }
    if isinstance(value, list):
        return [canonical(item, path) for item in value]
    return value


def known_annotation(path: list[str]) -> bool:
    if len(path) == 2 and path[0] == "info" and path[1] in {"description", "title", "summary"}:
        return True
    if len(path) == 3 and path[0] == "paths" and path[-1] in {"description", "summary"}:
        return True
    if (
        len(path) == 4
        and path[0] == "paths"
        and path[2] in METHODS
        and path[-1] in {"description", "summary"}
    ):
        return True
    return (
        len(path) == 6
        and path[0] == "paths"
        and path[2] in METHODS
        and path[3] == "responses"
        and path[-1] == "description"
    )


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
    if known_annotation(path) and isinstance(before, str) and isinstance(after, str):
        return "documentation"
    if path[0] == "paths" and len(path) <= 3 and after is MISSING:
        return "breaking"
    if key in {"required", "enum"} and isinstance(before, list) and isinstance(after, list):
        previous = {json.dumps(item, sort_keys=True) for item in before}
        candidate = {json.dumps(item, sort_keys=True) for item in after}
        removed = previous - candidate
        added = candidate - previous
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
        if left is MISSING or right is MISSING:
            unchanged = left is right
        else:
            unchanged = json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)
        if unchanged:
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


def check_review_intent(receipts: dict[str, Any], base: str, intent: Any) -> None:
    """Bind proposed semantic changes to exact inputs; never confer human approval."""
    changed = {
        path: receipt
        for path, receipt in receipts.items()
        if any(change["classification"] != "documentation" for change in receipt["changes"])
    }
    if (
        not isinstance(intent, dict)
        or set(intent) != {"baseCommit", "apis"}
        or intent["baseCommit"] != base
        or not isinstance(intent["apis"], dict)
        or set(intent["apis"]) != set(changed)
    ):
        raise ValueError("Semantic intent must cover exactly the changed APIs at this PR base")
    for path, receipt in changed.items():
        entry = intent["apis"][path]
        if (
            not isinstance(entry, dict)
            or set(entry) != {"beforeSha256", "afterSha256", "reason"}
            or entry["beforeSha256"] != receipt["beforeSha256"]
            or entry["afterSha256"] != receipt["afterSha256"]
            or not isinstance(entry["reason"], str)
            or not 1 <= len(entry["reason"].strip()) <= 1000
        ):
            raise ValueError(f"Stale or incomplete semantic intent for {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Immutable Git commit for PR comparison")
    parser.add_argument("--before", type=Path)
    parser.add_argument("--after", type=Path)
    args = parser.parse_args()
    if args.base:
        if (
            args.before
            or args.after
            or len(args.base) != 40
            or any(char not in "0123456789abcdef" for char in args.base)
        ):
            parser.error("--base requires one exact commit hash and no file pair")
        receipts = {}
        for path in APIS:
            previous = subprocess.run(
                ["git", "show", args.base + ":" + path], check=True, capture_output=True, text=True
            )
            receipts[path] = review(json.loads(previous.stdout), json.loads(Path(path).read_text()))
        print(json.dumps({"baseCommit": args.base, "apis": receipts}, indent=2))
        if any(
            change["classification"] != "documentation"
            for receipt in receipts.values()
            for change in receipt["changes"]
        ):
            try:
                intent = json.loads(Path("contracts/api-semantic-review.json").read_text())
                check_review_intent(receipts, args.base, intent)
            except (OSError, ValueError) as error:
                parser.exit(1, f"Semantic changes require exact review intent: {error}\n")
        return
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
