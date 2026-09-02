"""Development-only checks for the language-neutral contract bundle."""

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def no_network(uri):
    raise NoSuchResource(ref=uri)


def load_contracts(root=ROOT):
    contracts = read_json(root / "contracts.json")["contracts"]
    schemas = {entry["name"]: read_json(root / entry["schema"]) for entry in contracts}
    if len(schemas) != len(contracts):
        raise ValueError("Duplicate contract names")
    ids = [schema["$id"] for schema in schemas.values()]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate schema IDs")
    registry = Registry(retrieve=no_network).with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    validators = {}
    for entry in contracts:
        schema = schemas[entry["name"]]
        if schema["$id"] != "https://perfeng.dev/" + entry["schema"]:
            raise ValueError(f"Schema ID/path mismatch: {entry['schema']}")
        Draft202012Validator.check_schema(schema)
        validators[entry["name"]] = Draft202012Validator(
            schema, registry=registry, format_checker=FormatChecker()
        )
    return contracts, validators


def check_defaults(schema, validator, location=""):
    """Walk actual subschemas, without interpreting arbitrary instance objects."""
    if not isinstance(schema, dict):
        return
    if "default" in schema:
        errors = list(validator.evolve(schema=schema).iter_errors(schema["default"]))
        if errors:
            raise ValueError(f"Invalid schema default at {location}: {errors[0].message}")
    for keyword in ("properties", "$defs", "patternProperties", "dependentSchemas"):
        for name, child in schema.get(keyword, {}).items():
            check_defaults(child, validator, f"{location}/{keyword}/{name}")
    for keyword in ("items", "additionalProperties", "contains", "not", "if", "then", "else"):
        check_defaults(schema.get(keyword), validator, f"{location}/{keyword}")
    for keyword in ("allOf", "anyOf", "oneOf", "prefixItems"):
        for index, child in enumerate(schema.get(keyword, [])):
            check_defaults(child, validator, f"{location}/{keyword}/{index}")


def validate_bundle(root=ROOT):
    contracts, validators = load_contracts(root)
    schema_paths = {entry["schema"] for entry in contracts}
    actual_schemas = {p.relative_to(root).as_posix() for p in (root / "schemas").rglob("*.json")}
    if schema_paths != actual_schemas or len(schema_paths) != len(contracts):
        raise ValueError("Manifest must cover every schema exactly once")
    example_paths = set()
    count = 0
    for entry in contracts:
        validator = validators[entry["name"]]
        check_defaults(validator.schema, validator)
        if not entry["examples"]:
            raise ValueError(f"No examples for {entry['name']}")
        for example in entry["examples"]:
            example_paths.add(example["path"])
            data = read_json(root / example["path"])
            if example.get("items"):
                if not isinstance(data, list) or not data:
                    raise ValueError(f"Expected a nonempty example array: {example['path']}")
                instances = data
            else:
                instances = [data]
            for index, instance in enumerate(instances):
                errors = list(validator.iter_errors(instance))
                if errors:
                    raise ValueError(f"{example['path']}[{index}]: {errors[0].message}")
                count += 1
    actual_examples = {p.relative_to(root).as_posix() for p in (root / "examples").rglob("*.json")}
    if example_paths != actual_examples:
        raise ValueError("Manifest must cover every example")
    return len(contracts), count


if __name__ == "__main__":
    try:
        schemas, examples = validate_bundle()
    except (ValueError, KeyError, OSError) as error:
        print(f"Contract validation failed: {error}", file=sys.stderr)
        sys.exit(1)
    print(f"Validated {schemas} schemas and {examples} example records (offline).")
