"""Offline comparison conformance; never authenticates, fetches or rewrites evidence."""

import hashlib
import json
from typing import Any
from urllib.parse import urlsplit

from scripts.performance_analysis import check_reference, unique_object
from scripts.validate import (
    check_analysis_consistency,
    parse_finite_float,
    reject_nonfinite_constant,
)


def evidence_json(raw: bytes, reference: dict[str, Any]) -> Any:
    """Hash exact bounded bytes before parsing; never normalize before verification."""
    if (
        not 0 < len(raw) <= 1048576
        or len(raw) != reference["sizeBytes"]
        or hashlib.sha256(raw).hexdigest() != reference["sha256"]
    ):
        raise ValueError("Evidence bytes differ from retained reference")
    return json.loads(
        raw,
        object_pairs_hook=unique_object,
        parse_float=parse_finite_float,
        parse_constant=reject_nonfinite_constant,
    )


def check_comparison(
    value: dict[str, Any],
    *,
    run: dict[str, Any],
    native: dict[str, Any],
    report_artifact: dict[str, Any],
    analysis_bytes: bytes,
    policy_bytes: bytes,
    publication: dict[str, Any] | None,
    previous: dict[str, Any] | None = None,
) -> None:
    """Require schema-valid projection and independently retained, authorized inputs.

    Run request, report-time native binding, report reference and optional original
    publication must not be copied from the projection. Provider admission and
    object authorization are external prerequisites. Policy bytes must already
    satisfy policy/v1; native association must attest historical baseline approval.
    This checks report/policy bytes and relationships, not normalized artifact I/O.
    """
    if (
        len(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode())
        > 2097152
    ):
        raise ValueError("Comparison exceeds 2 MiB compact JSON bound")
    if value["runId"] != run["id"]:
        raise ValueError("Comparison differs from selected Run")
    if value["status"] != "AVAILABLE":
        return
    evidence = value["evidence"]
    if (
        value["request"] != run["request"]
        or evidence["native"] != native
        or evidence["report"] != report_artifact
        or evidence["publication"] != publication
    ):
        raise ValueError("Comparison differs from retained historical binding")
    analysis = evidence_json(analysis_bytes, report_artifact)
    if (
        not 0 < len(policy_bytes) <= 1048576
        or hashlib.sha256(policy_bytes).hexdigest() != native["policy"]["sha256"]
    ):
        raise ValueError("Policy differs from retained digest")
    policy = json.loads(
        policy_bytes,
        object_pairs_hook=unique_object,
        parse_float=parse_finite_float,
        parse_constant=reject_nonfinite_constant,
    )
    check_analysis_consistency(analysis, policy)
    identity = {key: analysis["policy"][key] for key in ("id", "version", "sha256")}
    if (
        evidence["analysis"] != analysis
        or native["runId"] != run["id"]
        or report_artifact["runId"] != run["id"]
        or analysis["runId"] != run["id"]
        or analysis["candidateArtifact"]["runId"] != run["id"]
        or analysis["testId"] != native["testId"]
        or identity != native["policy"]
        or run["request"]["policy"] != identity
    ):
        raise ValueError("Report differs from this Run, candidate or policy")
    baseline = native["baseline"]
    allowed = [] if baseline is None else [baseline["artifact"]]
    if any(reference not in allowed for reference in analysis["referenceArtifacts"]):
        raise ValueError("Reference differs from report-time baseline")
    rules = {rule["id"]: rule for rule in policy["spec"]["rules"]}
    directions = []
    for evaluation in analysis["evaluations"]:
        rule = rules[evaluation["ruleId"]]
        regression = rule.get("regression")
        if regression is not None and (
            baseline is None
            or regression["reference"]
            != {
                "baselineId": baseline["identity"]["id"],
                "version": baseline["identity"]["version"],
            }
        ):
            raise ValueError("Policy does not select the retained baseline version")
        directions.append(
            {
                "ruleId": rule["id"],
                "direction": None if regression is None else regression["direction"],
            }
        )
    if evidence["directions"] != directions:
        raise ValueError("Directions differ from frozen policy or report rule coverage")
    for reference in [
        report_artifact,
        analysis["candidateArtifact"],
        *analysis["referenceArtifacts"],
        *allowed,
    ]:
        uri = urlsplit(reference["uri"])
        if not uri.hostname or uri.username is not None or uri.password is not None:
            raise ValueError("Evidence reference contains credentials or lacks an authority")
    if publication is not None:
        check_reference(publication)
        data = publication["data"]
        candidate = run["request"]["candidate"]
        if (
            data["native"] != native
            or data["artifact"] != report_artifact
            or data["context"]["candidate"]["source"]
            != {"algorithm": "git-sha1", "digest": candidate["gitSha"]}
            or data["context"]["candidate"]["imageDigest"] != candidate["image"].rsplit("@", 1)[-1]
        ):
            raise ValueError("Publication differs from retained native evidence or candidate")
    if previous is not None and previous["status"] == "AVAILABLE" and previous != value:
        raise ValueError("Available comparison is immutable")
