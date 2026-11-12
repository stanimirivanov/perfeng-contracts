"""Offline service identity conformance; never authentication or a runtime authorizer."""

from typing import Any


def check_access(
    observation: dict[str, Any],
    *,
    run_id: str,
    service: dict[str, str] | None,
    grant_service: dict[str, str],
    actor: dict[str, str],
    caller: dict[str, str],
    created_by: dict[str, str],
    grants: list[str],
    permission: str = "run:read",
) -> None:
    """Compare a schema-valid observation to independently trusted provider evidence.

    Identities come from verified authentication; service and creator come from
    retained admission; grants come from current provider authorization. Never
    populate these inputs from the observation or caller-supplied identity fields.
    This does not prove provider authentication, revocation or audit persistence.
    """
    if (
        service is None
        or service != grant_service
        or permission not in grants
        or "run:read" not in grants
        or observation["runId"] != run_id
        or observation["service"] != service
        or observation["createdBy"] != created_by
        or observation["actor"] != actor
        or observation["caller"] != caller
        or set(observation["permissions"]) != set(grants)
    ):
        raise ValueError("Observation differs from verified identity, binding or current grants")


def check_resolution(
    observation: dict[str, Any],
    *,
    request: dict[str, str],
    run_id: str,
    service: dict[str, str],
) -> None:
    """Check exact parsed selector against independently retained native association.

    Authorization must be checked separately using the same retained service.
    No URL fetching, request creation, attempt selection or lease recovery occurs.
    """
    if (
        observation["request"] != request
        or observation["runId"] != run_id
        or observation["service"] != service
    ):
        raise ValueError("Resolution differs from exact retained request association")
