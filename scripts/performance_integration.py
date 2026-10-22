"""Offline protocol conformance only; never an admission or authorization service."""

from datetime import datetime
from typing import Any

TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}
NEXT = {
    "ACCEPTED": {"ACCEPTED", "RUNNING", "CANCELLING", *TERMINAL},
    "RUNNING": {"RUNNING", "CANCELLING", *TERMINAL},
    "CANCELLING": {"CANCELLING", *TERMINAL},
}


def timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def check_context(message: dict[str, Any]) -> None:
    context = message["data"]["context"]
    if timestamp(context["deadline"]) <= timestamp(context["requestedAt"]):
        raise ValueError("Deadline must follow request creation")
    if context["request"] == context["attempt"]:
        raise ValueError("Request and attempt identities must be distinct")
    if message["type"].endswith(("requested.v1", "cancel-requested.v1")):
        if message["source"] != context["request"]["issuer"]:
            raise ValueError("Request source differs from identity issuer")
    if timestamp(message["time"]) < timestamp(context["requestedAt"]):
        raise ValueError("Event predates request creation")
    if message["type"].endswith(".accepted.v1"):
        if timestamp(message["time"]) >= timestamp(context["deadline"]):
            raise ValueError("Cannot accept an expired request")


def check_exchange(messages: list[dict[str, Any]], provider: str) -> None:
    """Verify a complete fixture trace; provider is independently configured authority."""
    if not messages or not messages[0]["type"].endswith(".requested.v1"):
        raise ValueError("Exchange must start with a request")
    context = messages[0]["data"]["context"]
    events: dict[tuple[str, str], dict[str, Any]] = {}
    run = None
    disposition = None
    admission = None
    previous = None
    for message in messages:
        data = message["data"]
        if data["context"] != context:
            raise ValueError("Conflicting retry or substituted request context")
        check_context(message)
        key = (message["source"], message["id"])
        if key in events:
            if events[key] != message:
                raise ValueError("Event identity reused with different content")
            continue
        events[key] = message
        kind = message["type"].removeprefix("dev.perfeng.integration.").removesuffix(".v1")
        if kind in {"requested", "cancel-requested"}:
            continue
        if message["source"] != provider:
            raise ValueError("Unexpected provider issuer")
        if kind in {"accepted", "rejected"}:
            if disposition is not None and disposition != kind:
                raise ValueError("Admission disposition is immutable")
            if admission is not None and admission != data:
                raise ValueError("Admission payload is immutable")
            disposition = kind
            admission = data
        if kind != "rejected":
            if disposition != "accepted":
                raise ValueError("Lifecycle requires accepted admission")
            if data["run"]["issuer"] != provider:
                raise ValueError("Run issuer differs from provider authority")
            if run is not None and run != data["run"]:
                raise ValueError("Request cannot acquire a different run")
            run = data["run"]
        if kind == "lifecycle":
            if previous is not None and data != previous:
                if previous["state"] in TERMINAL:
                    raise ValueError("Terminal lifecycle snapshot is immutable")
                if data["revision"] <= previous["revision"]:
                    raise ValueError("Lifecycle revision must increase")
                if data["state"] not in NEXT[previous["state"]]:
                    raise ValueError("Illegal lifecycle transition")
            previous = data
