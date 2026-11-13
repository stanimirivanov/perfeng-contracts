"""Offline rerun conformance; not a provider, authorizer or durable deduplicator."""

import json
from datetime import datetime, timedelta
from typing import Any


def check_selection(
    *,
    source: dict[str, Any],
    request: dict[str, Any],
    approved: dict[str, list[dict[str, Any]]],
    enabled_suites: list[str],
    evidence_available: bool,
) -> str:
    """Use an independently verified frozen source and current exact admission facts.

    Resource authorization precedes these inputs; invisible evidence must never
    be converted into a distinguishable validation error by a provider.
    """
    if source["status"] != "AVAILABLE":
        return "VALIDATION_FAILED"
    report = source["evidence"]["report"]
    required = {name: source["request"][name] for name in ("catalogue", "environment", "policy")}
    baseline = source["evidence"]["native"]["baseline"]
    required["workload"] = source["evidence"]["native"]["workload"]
    if baseline is not None:
        required["baseline"] = baseline["identity"]
    if (
        request["sourceReport"] != {key: report[key] for key in ("id", "sha256")}
        or source["request"]["testSuite"] not in enabled_suites
        or any(reference not in approved.get(kind, []) for kind, reference in required.items())
    ):
        return "VALIDATION_FAILED"
    return "ACCEPTABLE" if evidence_available else "UNAVAILABLE"


def check_intent_retry(
    *,
    stored: dict[str, Any],
    actor: dict[str, str],
    key: str,
    source_run_id: str,
    request: dict[str, Any],
    now: str,
) -> str:
    """Classify one retained rerun intent, after current authorization; no mutation.

    NEW means only that this record does not match the actor/key. It is not proof
    that no other record exists, admission succeeded or execution may begin.
    """
    if key != stored["key"] or any(
        actor[name] != stored["actor"][name] for name in ("issuer", "id")
    ):
        return "NEW"
    if (
        source_run_id != stored["source_run_id"]
        or request != stored["request"]
        or datetime.fromisoformat(now) >= datetime.fromisoformat(stored["expires_at"])
    ):
        return "IDEMPOTENCY_CONFLICT"
    return "REPLAY"


def check_receipt(
    value: dict[str, Any],
    *,
    source: dict[str, Any],
    source_run_id: str,
    run_id: str,
    receipt_id: str,
    service: dict[str, str],
    source_created_by: dict[str, str],
    actor: dict[str, str],
    caller: dict[str, str],
    current_actor: dict[str, str],
    grant_service: dict[str, str],
    grants: list[str],
    request: dict[str, Any],
    key: str,
    accepted_at: str,
    expires_at: str,
    recovery: bool = False,
    previous: dict[str, Any] | None = None,
) -> None:
    """Require schema-valid receipt and independently retained atomic acceptance.

    Authentication/delegation, evidence scope, current admission, child binding
    and transaction durability are provider prerequisites, never inferred here.
    caller is the original verified caller retained at acceptance; recovery must
    not rewrite it to the current delegated client.
    """
    if (
        current_actor != actor
        or service != grant_service
        or "run:read" not in grants
        or (not recovery and "run:rerun" not in grants)
    ):
        raise ValueError("Current identity or service grant does not authorize this observation")
    expected = {
        "id": receipt_id,
        "sourceRunId": source_run_id,
        "runId": run_id,
        "service": service,
        "sourceCreatedBy": source_created_by,
        "actor": actor,
        "caller": caller,
        "request": request,
        "idempotencyKey": key,
        "acceptedAt": accepted_at,
        "idempotencyKeyExpiresAt": expires_at,
    }
    if any(value[name] != expected_value for name, expected_value in expected.items()):
        raise ValueError("Receipt differs from independently retained acceptance")
    if (
        source["status"] != "AVAILABLE"
        or source["runId"] != source_run_id
        or run_id == source_run_id
        or value["selection"] != source["request"]
        or value["native"] != source["evidence"]["native"]
        or request["sourceReport"]
        != {name: source["evidence"]["report"][name] for name in ("id", "sha256")}
        or datetime.fromisoformat(expires_at)
        < datetime.fromisoformat(accepted_at) + timedelta(hours=24)
    ):
        raise ValueError("Receipt does not preserve distinct child, source selection or retention")
    if previous is not None and value != previous:
        raise ValueError("Accepted receipt is immutable, including on replay")
    if (
        len(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode())
        > 65536
    ):
        raise ValueError("Receipt exceeds 64 KiB")


def check_http_rerun(case: dict[str, Any], body: dict[str, Any], submitted: Any) -> None:
    """Check bounded public HTTP observations, without treating them as authorization."""
    headers = {name.lower(): value for name, value in case.get("headers", {}).items()}
    request_headers = {
        name.lower(): value for name, value in case.get("requestHeaders", {}).items()
    }
    post = case["operationId"] == "rerunRun"
    query = case.get("queryParameters", {})
    if (
        headers.get("cache-control") != "no-store"
        or len(headers) != len(case.get("headers", {}))
        or len(request_headers) != len(case.get("requestHeaders", {}))
        or set(query) != (set() if post else {"idempotencyKey"})
    ):
        raise ValueError("Rerun response/request lacks no-store or exact unambiguous selectors")
    if (
        len(json.dumps(body, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode())
        > 65536
    ):
        raise ValueError("Rerun response exceeds 64 KiB")
    if case["status"] not in (200, 201):
        return
    key = request_headers.get("idempotency-key") if post else query["idempotencyKey"]
    if (
        body["sourceRunId"] != case["pathParameters"]["runId"]
        or body["sourceRunId"] == body["runId"]
        or body["idempotencyKey"] != key
        or datetime.fromisoformat(body["idempotencyKeyExpiresAt"])
        < datetime.fromisoformat(body["acceptedAt"]) + timedelta(hours=24)
    ):
        raise ValueError("Receipt differs from route, key, child or minimum retention")
    if post and (
        body["request"] != submitted
        or headers.get("location") != "/v1/runs/" + body["runId"]
        or headers.get("idempotency-key-expires-at") != body["idempotencyKeyExpiresAt"]
    ):
        raise ValueError("Rerun acceptance differs from submitted intent or immutable headers")
