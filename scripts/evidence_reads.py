"""Offline byte-read conformance, not authorization or an artifact transport."""

import base64
import hashlib
from typing import Any

from jsonschema import Draft202012Validator

from scripts.contracts_pack import parse_document

MAX_EVIDENCE_BYTES = 1048576


def check_bytes(
    raw: bytes, headers: dict[str, str], *, expected: dict[str, str], sha256: str
) -> None:
    """Compare original bytes and wire metadata against independent retained identity."""
    normalized = {key.lower(): value for key, value in headers.items()}
    if len(normalized) != len(headers) or any(
        name in normalized
        for name in ("content-encoding", "content-range", "location", "content-location")
    ):
        raise ValueError("Duplicate or forbidden response header")
    required = {
        "Content-Type": "application/octet-stream",
        "Content-Length": str(len(raw)),
        "Content-Digest": "sha-256=:"
        + base64.b64encode(hashlib.sha256(raw).digest()).decode()
        + ":",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "X-Perfeng-Evidence-Media-Type": "application/json",
        **expected,
    }
    if not 0 < len(raw) <= MAX_EVIDENCE_BYTES or hashlib.sha256(raw).hexdigest() != sha256:
        raise ValueError("Evidence exceeds 1 MiB or differs from retained digest")
    if any(normalized.get(key.lower()) != value for key, value in required.items()):
        raise ValueError("Missing or inconsistent evidence response metadata")


def check_artifact_content(
    *,
    run_id: str,
    artifact_id: str,
    associated: dict[str, list[dict[str, Any]]],
    raw: bytes,
    headers: dict[str, str],
) -> None:
    """Use independently retained, currently authorized associations for selected Run.

    Authorization and association provenance are provider prerequisites. Passing a
    caller-supplied descriptor, URI or unverified comparison is not admission.
    """
    matches = [
        reference for reference in associated.get(run_id, []) if reference["id"] == artifact_id
    ]
    if len(matches) != 1:
        raise ValueError("Artifact lacks a unique authorized association to selected Run")
    reference = matches[0]
    if (
        reference["format"] not in {"normalized-result/v1", "analysis-result/v1"}
        or reference["mediaType"] != "application/json"
        or reference["sizeBytes"] != len(raw)
    ):
        raise ValueError("Unsupported artifact or inconsistent retained size")
    check_bytes(
        raw,
        headers,
        sha256=reference["sha256"],
        expected={
            "X-Perfeng-Run-Id": run_id,
            "X-Perfeng-Artifact-Id": artifact_id,
            "X-Perfeng-Artifact-Run-Id": reference["runId"],
            "X-Perfeng-Evidence-Format": reference["format"],
        },
    )


def check_policy_content(
    *,
    run_id: str,
    policies: dict[str, dict[str, Any]],
    raw: bytes,
    headers: dict[str, str],
) -> None:
    """Policy is an independent report-used binding, never merely a request pin."""
    policy = policies.get(run_id)
    if policy is None:
        raise ValueError("No retained report-used policy")
    check_bytes(
        raw,
        headers,
        sha256=policy["sha256"],
        expected={
            "X-Perfeng-Run-Id": run_id,
            "X-Perfeng-Policy-Id": policy["id"],
            "X-Perfeng-Policy-Version": policy["version"],
            "X-Perfeng-Evidence-Format": "policy/v1",
        },
    )


def report_content_status(
    *,
    run_id: str,
    artifact_id: str,
    runs: dict[str, Any],
    authority: dict[str, Any] | None,
    raw: bytes | None,
    validator: Draft202012Validator,
) -> int:
    """Derive the expected status from independently supplied offline fixture facts.

    The mode and identities come from verified credentials. Grants and delegation are
    current provider facts. Runs and registrations are retained admission metadata.
    A missing raw body represents a storage read failure.
    """
    if authority is None:
        return 401
    if not authority["operationAllowed"]:
        return 403
    run = runs.get(run_id)
    if run is None:
        return 404
    if "service" in run:
        if (
            authority["mode"] != "service"
            or authority.get("actor") != run["createdBy"]
            or authority.get("grantService") != run["service"]
            or "run:read" not in authority.get("permissions", [])
            or not authority.get("callerAuthorizedForActor")
        ):
            return 404
    elif (
        authority["mode"] != "legacy"
        or not run.get("legacyPrincipal")
        or authority.get("legacyPrincipal") != run["legacyPrincipal"]
    ):
        return 404
    matches = [ref for ref in run["registrations"] if ref["id"] == artifact_id]
    if len(matches) != 1:
        return 404
    reference = matches[0]
    if (
        reference["runId"] != run_id
        or reference["kind"] != "normalized"
        or reference["format"] != "analysis-result/v1"
        or reference["mediaType"] != "application/json"
    ):
        return 404
    if reference["sizeBytes"] > MAX_EVIDENCE_BYTES:
        return 422
    if not raw or len(raw) != reference["sizeBytes"] or len(raw) > MAX_EVIDENCE_BYTES:
        return 503
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        return 503
    try:
        report = parse_document(raw)
    except (ValueError, RecursionError):
        return 503
    if not validator.is_valid(report):
        return 503
    if report["runId"] != run_id or report["candidateArtifact"]["runId"] != run_id:
        return 503
    return 200
