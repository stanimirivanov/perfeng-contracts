"""Offline complete-snapshot conformance; never authorization or runtime selection."""

import hashlib
import json
from datetime import datetime
from typing import Any

try:
    from .performance_integration import timestamp
except ImportError:
    from performance_integration import timestamp


def content_digest(items: list[dict[str, Any]]) -> str:
    # Schema keys are fixed ASCII and resource values contain no numbers.
    encoded = json.dumps(items, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def identity(reference: dict[str, str]) -> tuple[str, str]:
    return reference["issuer"], reference["id"]


def check_page(page: dict[str, Any]) -> None:
    snapshot, position = page["snapshot"], page["page"]
    if timestamp(snapshot["generatedAt"]) >= timestamp(snapshot["validUntil"]):
        raise ValueError("Invalid snapshot freshness window")
    if position["index"] >= snapshot["totalPages"]:
        raise ValueError("Page index exceeds snapshot")
    if (position["cursor"] is None) != (position["index"] == 0):
        raise ValueError("Only the first page has no cursor")
    if (position["nextCursor"] is None) != (position["index"] == snapshot["totalPages"] - 1):
        raise ValueError("Only the final page has no next cursor")
    if not page["items"] and (snapshot["totalPages"] != 1 or snapshot["totalItems"] != 0):
        raise ValueError("Empty pages cannot conceal missing resources")


def check_snapshot(
    pages: list[dict[str, Any]], *, observed_at: datetime, principal: dict[str, str], issuer: str
) -> None:
    if not pages:
        raise ValueError("Missing snapshot pages")
    snapshot = pages[0]["snapshot"]
    if (
        snapshot["principal"] != principal
        or snapshot["reference"]["issuer"] != issuer
        or snapshot["producer"]["identity"]["issuer"] != issuer
    ):
        raise ValueError("Unexpected snapshot authority or principal")
    if not timestamp(snapshot["generatedAt"]) <= observed_at < timestamp(snapshot["validUntil"]):
        raise ValueError("Snapshot is stale or from the future")
    if len(pages) != snapshot["totalPages"]:
        raise ValueError("Missing snapshot pages")
    items, cursors = [], set()
    for index, page in enumerate(pages):
        check_page(page)
        if page["snapshot"] != snapshot or page["page"]["index"] != index:
            raise ValueError("Mixed snapshot or reordered pages")
        cursor = page["page"]["cursor"]
        if index and (cursor != pages[index - 1]["page"]["nextCursor"] or cursor in cursors):
            raise ValueError("Broken or repeated page cursor")
        cursors.add(cursor)
        items.extend(page["items"])
    if (
        len(items) != snapshot["totalItems"]
        or content_digest(items) != snapshot["reference"]["sha256"]
    ):
        raise ValueError("Snapshot count or content digest mismatch")
    resources = {}
    for item in items:
        key = item["kind"], *identity(item["reference"])
        if key in resources:
            raise ValueError("Duplicate resource identity")
        resources[key] = item

    def resolve(kind: str, reference: dict[str, str]) -> dict[str, Any]:
        value = resources.get((kind, *identity(reference)))
        if value is None or value["reference"] != reference:
            raise ValueError("Missing or substituted resource reference")
        return value

    for item in items:
        if item["kind"] == "workload":
            route = resolve("owner-route", item["ownerRoute"])
            profiles = [resolve("profile", ref) for ref in item["supportedProfiles"]]
            if len({identity(ref) for ref in item["supportedProfiles"]}) != len(profiles):
                raise ValueError("Duplicate supported profile")
            if any(profile["workload"] != item["reference"] for profile in profiles):
                raise ValueError("Profile belongs to another workload")
            if item["state"] == "ACTIVE" and any(
                value["state"] != "ACTIVE" for value in [route, *profiles]
            ):
                raise ValueError("Active workload references retired resources")
        if item["kind"] == "profile":
            workload = resolve("workload", item["workload"])
            if item["state"] == "ACTIVE" and (
                workload["state"] != "ACTIVE"
                or item["reference"] not in workload["supportedProfiles"]
            ):
                raise ValueError("Active profile is unsupported or retired")
            if len({json.dumps(value, sort_keys=True) for value in item["selections"]}) != len(
                item["selections"]
            ):
                raise ValueError("Duplicate supported selection")
            for selection in item["selections"]:
                dependencies = [
                    resolve(kind, selection[kind]) for kind in ("environment", "policy")
                ]
                if item["state"] == "ACTIVE" and any(
                    value["state"] != "ACTIVE" for value in dependencies
                ):
                    raise ValueError("Active profile references retired resources")
                if selection["baseline"] is not None:
                    baseline = resolve("baseline", selection["baseline"])
                    if (
                        baseline["workload"] != item["workload"]
                        or baseline["profile"] != item["reference"]
                        or any(
                            baseline[kind] != selection[kind] for kind in ("environment", "policy")
                        )
                    ):
                        raise ValueError("Baseline belongs to another profile context")
                    if item["state"] == "ACTIVE" and baseline["state"] != "APPROVED":
                        raise ValueError("Baseline is not approved for this profile")
        if item["kind"] == "baseline":
            for kind in ("workload", "environment", "policy"):
                resolve(kind, item[kind])
            if resolve("profile", item["profile"])["workload"] != item["workload"]:
                raise ValueError("Baseline belongs to another workload")
