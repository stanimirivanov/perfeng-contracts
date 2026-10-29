"""Offline publication conformance, never authentication or artifact fetching."""

import hashlib
import json
from typing import Any
from urllib.parse import urlsplit

try:
    from .performance_integration import check_context, timestamp
except ImportError:
    from performance_integration import check_context, timestamp


def check_reference(message: dict[str, Any]) -> None:
    """Check relationships after validating performance-analysis/v1 schema."""
    check_context(message)
    data = message["data"]
    uri = urlsplit(data["artifact"]["uri"])
    if not uri.hostname or uri.username is not None or uri.password is not None:
        raise ValueError("Analysis reference cannot carry credentials or omit its host")
    if data["run"]["issuer"] != message["source"]:
        raise ValueError("Run issuer differs from publication source")
    if data["artifact"]["runId"] != data["native"]["runId"]:
        raise ValueError("Analysis reference differs from native run")
    if (data["native"]["baseline"] is None) != (data["context"]["baseline"] is None):
        raise ValueError("Baseline selection and native association disagree")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate artifact JSON member")
        result[key] = value
    return result


def check_binding(
    message: dict[str, Any],
    admission: dict[str, Any],
    native: dict[str, Any],
    analysis: dict[str, Any],
    artifact_bytes: bytes,
    policy_bytes: bytes,
    *,
    provider: str,
    principal: dict[str, str],
    previous: dict[str, Any] | None = None,
) -> None:
    """Inputs must pass their schemas and analysis policy conformance first.

    Admission/native come from independently retained authenticated evidence,
    never from the publication. Policy bytes must pass policy schema/semantics.
    The artifact bytes must decode to the supplied analysis.
    Previous, if supplied, is the retained authenticated publication for this
    request/attempt. This check never authorizes URIs, approval or verdicts.
    """
    check_reference(message)
    data = message["data"]
    if (
        message["source"] != provider
        or data["context"]["principal"] != principal
        or admission["source"] != provider
        or admission["type"] != "dev.perfeng.integration.accepted.v1"
        or data["context"] != admission["data"]["context"]
        or data["run"] != admission["data"]["run"]
        or data["native"] != native
        or timestamp(message["time"]) < timestamp(admission["time"])
    ):
        raise ValueError("Publication differs from authenticated admission binding")
    if previous is not None and (
        previous["source"] != provider
        or previous["data"] != data
        or (previous["id"] == message["id"] and previous != message)
    ):
        raise ValueError("Conflicting immutable analysis publication")
    artifact = data["artifact"]
    if (
        len(artifact_bytes) != artifact["sizeBytes"]
        or hashlib.sha256(artifact_bytes).hexdigest() != artifact["sha256"]
        or json.loads(artifact_bytes, object_pairs_hook=unique_object) != analysis
    ):
        raise ValueError("Analysis bytes differ from immutable reference")
    if (
        analysis["runId"] != native["runId"]
        or analysis["candidateArtifact"]["runId"] != native["runId"]
        or analysis["testId"] != native["testId"]
        or {key: analysis["policy"][key] for key in ("id", "version", "sha256")} != native["policy"]
        or timestamp(analysis["createdAt"]) < timestamp(admission["time"])
        or timestamp(analysis["createdAt"]) > timestamp(message["time"])
    ):
        raise ValueError("Analysis differs from frozen native association")
    allowed = [] if native["baseline"] is None else [native["baseline"]["artifact"]]
    if any(reference not in allowed for reference in analysis["referenceArtifacts"]):
        raise ValueError("Analysis reference is not the admitted baseline artifact")
    if hashlib.sha256(policy_bytes).hexdigest() != native["policy"]["sha256"]:
        raise ValueError("Policy bytes differ from frozen native digest")
    policy = json.loads(policy_bytes, object_pairs_hook=unique_object)
    for rule in policy["spec"]["rules"]:
        if "regression" in rule and (
            native["baseline"] is None
            or rule["regression"]["reference"]
            != {
                "baselineId": native["baseline"]["identity"]["id"],
                "version": native["baseline"]["identity"]["version"],
            }
        ):
            raise ValueError("Policy comparison does not select the admitted native baseline")
