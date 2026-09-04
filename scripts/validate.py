"""Development-only checks for the language-neutral contract bundle."""

import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Never, NotRequired, TypedDict
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource

ROOT = Path(__file__).resolve().parents[1]


class ExampleDefinition(TypedDict):
    path: str
    items: NotRequired[bool]


class ContractDefinition(TypedDict):
    name: str
    schema: str
    examples: list[ExampleDefinition]


def reject_nonfinite_constant(value: str) -> Never:
    raise ValueError(f"Non-finite value is not valid JSON: {value}")


def parse_finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"JSON number exceeds finite float range: {value}")
    return number


def read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_nonfinite_constant,
        parse_float=parse_finite_float,
    )


def no_network(uri: str) -> Never:
    raise NoSuchResource(ref=uri)


def load_contracts(
    root: Path = ROOT,
) -> tuple[list[ContractDefinition], dict[str, Draft202012Validator]]:
    contracts: list[ContractDefinition] = read_json(root / "contracts.json")["contracts"]
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


def check_defaults(
    schema: dict[str, Any] | bool | None,
    validator: Draft202012Validator,
    location: str = "",
) -> None:
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


def check_catalogue_consistency(catalogue: dict[str, Any]) -> None:
    """Reference conformance checks after JSON Schema validation.

    These checks cover relationships that JSON Schema cannot express, such as
    unique identifiers and a schedule selecting a declared workload profile.
    """
    test_ids: set[str] = set()
    workload_versions: dict[tuple[str, str], dict[str, Any]] = {}
    for test in catalogue["tests"]:
        if test["id"] in test_ids:
            raise ValueError(f"Duplicate test ID: {test['id']}")
        test_ids.add(test["id"])
        profiles: set[str] = set()
        for workload in test["workloads"]:
            if workload["tool"] != test["tool"]["name"]:
                raise ValueError(f"Workload tool does not match test {test['id']}")
            if workload["profile"] in profiles:
                raise ValueError(f"Duplicate workload profile in test {test['id']}")
            profiles.add(workload["profile"])
            identity = (workload["id"], workload["version"])
            if identity in workload_versions and workload_versions[identity] != workload:
                raise ValueError(f"Conflicting workload definition: {identity}")
            workload_versions[identity] = workload
        for profile in test.get("schedule", {}).values():
            if profile not in profiles:
                raise ValueError(f"Schedule selects undeclared profile {profile}: {test['id']}")


def check_artifact_reference(reference: dict[str, Any]) -> None:
    """Check location semantics after schema validation; never fetch content."""
    location = urlsplit(reference["uri"])
    if not location.hostname:
        raise ValueError("Artifact URI must have a storage host or bucket")
    if location.username is not None or location.password is not None:
        raise ValueError("Artifact URI must not contain credentials")


def check_transport_consistency(document: dict[str, Any]) -> None:
    """Reference conformance checks after validating the envelope schema."""
    window = document["measurementWindow"]
    start = datetime.fromisoformat(window["start"])
    end = datetime.fromisoformat(window["end"])
    created = datetime.fromisoformat(document["createdAt"])
    if start >= end:
        raise ValueError("Measurement window start must precede end")
    if created < end:
        raise ValueError("Envelope creation must not precede measurement end")

    key = "artifacts" if document["kind"] == "RawResult" else "sourceArtifacts"
    ids: set[str] = set()
    locations: set[str] = set()
    for artifact in document[key]:
        check_artifact_reference(artifact)
        if artifact["runId"] != document["runId"]:
            raise ValueError("Artifact run ID does not match envelope")
        identity = artifact["id"].lower()
        if identity in ids:
            raise ValueError("Duplicate artifact ID")
        if artifact["uri"] in locations:
            raise ValueError("Duplicate artifact URI")
        ids.add(identity)
        locations.add(artifact["uri"])

    metric_names: set[str] = set()
    for result in document.get("results", []):
        if result["runId"] != document["runId"]:
            raise ValueError("Metric run ID does not match envelope")
        name = result["metric"]["name"]
        if name in metric_names:
            raise ValueError(f"Duplicate metric name: {name}")
        metric_names.add(name)


def check_policy_consistency(policy: dict[str, Any]) -> None:
    ids: set[str] = set()
    selectors: set[tuple[str, str]] = set()
    for rule in policy["spec"]["rules"]:
        if rule["id"] in ids:
            raise ValueError("Duplicate policy rule ID")
        selector = (rule["metric"]["name"], rule["metric"]["statistic"])
        if selector in selectors:
            raise ValueError("Duplicate policy metric/statistic selector")
        ids.add(rule["id"])
        selectors.add(selector)
        slo = rule.get("slo", {})
        if "min" in slo and "max" in slo and slo["min"] > slo["max"]:
            raise ValueError("SLO minimum exceeds maximum")


def check_analysis_consistency(
    report: dict[str, Any], policy: dict[str, Any] | None = None
) -> None:
    """Check a supplied report; do not select baselines or produce verdicts.

    Call after schema validation. Runtime consumers must resolve and verify the
    policy and artifact bytes before trusting reported values and provenance.
    """
    candidate = report["candidateArtifact"]
    check_artifact_reference(candidate)
    if candidate["runId"] != report["runId"]:
        raise ValueError("Candidate run ID does not match analysis")
    ids = {candidate["id"].lower()}
    locations = {candidate["uri"]}
    references: set[str] = set()
    for artifact in report["referenceArtifacts"]:
        check_artifact_reference(artifact)
        identity = artifact["id"].lower()
        if identity in ids or artifact["uri"] in locations:
            raise ValueError("Duplicate candidate/reference artifact identity")
        if artifact["runId"] == report["runId"]:
            raise ValueError("Reference must come from a different run")
        ids.add(identity)
        locations.add(artifact["uri"])
        references.add(identity)

    evaluations: dict[str, Any] = {}
    for evaluation in report["evaluations"]:
        if evaluation["ruleId"] in evaluations:
            raise ValueError("Duplicate evaluation rule ID")
        evaluations[evaluation["ruleId"]] = evaluation
        for section in ("quality", "slo", "regression"):
            verdict = evaluation[section]
            if verdict["status"] != "PASS" and not verdict["reasons"]:
                raise ValueError("Non-PASS outcomes require reasons")
        if evaluation["quality"]["status"] != "PASS":
            if any(evaluation[s]["status"] in {"PASS", "FAIL"} for s in ("slo", "regression")):
                raise ValueError("Untrusted quality cannot yield a decisive performance outcome")
        regression = evaluation["regression"]
        if "referenceArtifactId" in regression:
            if regression["referenceArtifactId"].lower() not in references:
                raise ValueError("Regression reference artifact is not declared")

    if policy is None:
        return
    check_policy_consistency(policy)
    if (report["policy"]["id"], report["policy"]["version"], report["policy"]["mode"]) != (
        policy["metadata"]["name"],
        policy["metadata"]["version"],
        policy["spec"]["mode"],
    ):
        raise ValueError("Analysis policy identity/version/mode mismatch")
    rules = {rule["id"]: rule for rule in policy["spec"]["rules"]}
    if set(rules) != set(evaluations):
        raise ValueError("Analysis must account for every policy rule exactly once")
    for rule_id, rule in rules.items():
        evaluation = evaluations[rule_id]
        if evaluation["metric"] != rule["metric"]:
            raise ValueError("Analysis metric/statistic/unit does not match policy")
        for section in ("slo", "regression"):
            if section not in rule and evaluation[section]["status"] != "NOT_EVALUATED":
                raise ValueError("Unconfigured policy sections must be NOT_EVALUATED")
        quality = evaluation["quality"]
        if quality["status"] == "PASS":
            requirement = rule.get("quality", {})
            if "minSamples" in requirement:
                if quality.get("samples", 0) < requirement["minSamples"]:
                    raise ValueError("Quality PASS requires the configured sample count")
            if "maxCv" in requirement:
                if "cv" not in quality or quality["cv"] > requirement["maxCv"]:
                    raise ValueError("Quality PASS requires the configured variability bound")
        slo = evaluation["slo"]
        if slo["status"] in {"PASS", "FAIL"}:
            bounds = rule["slo"]
            passes = bounds.get("min", -math.inf) <= slo["value"] <= bounds.get("max", math.inf)
            if (slo["status"] == "PASS") != passes:
                raise ValueError("SLO outcome contradicts the reported value and policy bounds")
        regression = evaluation["regression"]
        if regression["status"] in {"PASS", "FAIL"}:
            requirement = rule["regression"]
            difference = requirement["practicalDifference"]
            if regression["effect"]["kind"] != difference["kind"]:
                raise ValueError("Regression effect kind does not match policy")
            change = regression["candidateValue"] - regression["referenceValue"]
            if requirement["direction"] == "higher-is-better":
                change = -change
            if difference["kind"] == "relative":
                if regression["referenceValue"] == 0:
                    raise ValueError("Relative comparison against zero is inconclusive")
                change /= abs(regression["referenceValue"])
            if not math.isclose(change, regression["effect"]["value"], rel_tol=1e-9, abs_tol=1e-12):
                raise ValueError(
                    "Reported regression effect contradicts candidate/reference values"
                )
            if (regression["status"] == "FAIL") != (change >= difference["value"]):
                raise ValueError("Regression verdict contradicts the practical threshold")


def check_baseline_consistency(baseline: dict[str, Any]) -> None:
    """Check baseline lifecycle and evidence relationships after schema validation."""
    artifact = baseline["artifact"]
    check_artifact_reference(artifact)
    if artifact["runId"] != baseline["sourceRunId"]:
        raise ValueError("Baseline artifact run ID does not match source run")

    lifecycle = baseline["lifecycle"]
    if lifecycle[0]["state"] != "CANDIDATE":
        raise ValueError("Baseline lifecycle must start at CANDIDATE")
    if lifecycle[-1]["state"] != baseline["state"]:
        raise ValueError("Baseline state must match the last lifecycle event")
    if lifecycle[0]["at"] != baseline["createdAt"]:
        raise ValueError("Baseline creation time must match its first lifecycle event")
    if baseline["revision"] != len(lifecycle):
        raise ValueError("Baseline revision must match its lifecycle length")

    transitions = {
        "CANDIDATE": {"QUALIFIED", "RETIRED"},
        "QUALIFIED": {"APPROVED", "RETIRED"},
        "APPROVED": {"RETIRED"},
        "RETIRED": set(),
    }
    previous_state = lifecycle[0]["state"]
    previous_time = datetime.fromisoformat(lifecycle[0]["at"])
    for event in lifecycle[1:]:
        event_time = datetime.fromisoformat(event["at"])
        if event["state"] not in transitions[previous_state]:
            raise ValueError("Invalid baseline lifecycle transition")
        if event_time < previous_time:
            raise ValueError("Baseline lifecycle timestamps must be ordered")
        previous_state = event["state"]
        previous_time = event_time

    qualification = baseline["qualification"]
    if baseline["state"] in {"QUALIFIED", "APPROVED"}:
        if qualification["status"] != "PASSED":
            raise ValueError("Qualified or approved baseline must pass qualification")
    if baseline["state"] == "CANDIDATE" and qualification["status"] == "PASSED":
        raise ValueError("Passed qualification must advance the baseline state")


def validate_bundle(root: Path = ROOT) -> tuple[int, int]:
    contracts, validators = load_contracts(root)
    policies = [
        (
            read_json(root / example["path"]),
            hashlib.sha256((root / example["path"]).read_bytes()).hexdigest(),
        )
        for entry in contracts
        if entry["name"] == "policy/v1"
        for example in entry["examples"]
    ]
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
                if entry["name"] == "catalogue/v1":
                    check_catalogue_consistency(instance)
                if entry["name"] == "artifact/v1":
                    check_artifact_reference(instance)
                if entry["name"] in {"raw-result/v1", "normalized-result/v1"}:
                    check_transport_consistency(instance)
                if entry["name"] == "policy/v1":
                    check_policy_consistency(instance)
                if entry["name"] == "analysis/v1":
                    matches = [
                        policy
                        for policy, digest in policies
                        if policy["metadata"]["name"] == instance["policy"]["id"]
                        and policy["metadata"]["version"] == instance["policy"]["version"]
                        and digest == instance["policy"]["sha256"]
                    ]
                    if len(matches) != 1:
                        raise ValueError(
                            "Analysis must reference exactly one checked-in policy by hash"
                        )
                    check_analysis_consistency(instance, matches[0])
                if entry["name"] == "baseline/v1":
                    check_baseline_consistency(instance)
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
