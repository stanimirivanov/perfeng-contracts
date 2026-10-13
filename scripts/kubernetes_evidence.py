"""Offline reference semantics after Kubernetes benchmark evidence schema validation."""

from datetime import datetime
from typing import Any


def check_kubernetes_benchmark_evidence(evidence: dict[str, Any]) -> None:
    """Verify capture ordering, node membership and observable check results.

    Callers validate the JSON Schema first. This does not fetch artifacts,
    evaluate profile thresholds, authorize execution or approve a baseline.
    """
    window = evidence["captureWindow"]
    start = datetime.fromisoformat(window["start"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(window["end"].replace("Z", "+00:00"))
    if start > end or (evidence["scope"]["kind"] == "measurement" and start == end):
        raise ValueError("Invalid Kubernetes evidence capture window")
    nodes = evidence["nodes"]
    node_ids = {node["uid"] for node in nodes}
    if len(node_ids) != len(nodes) or len({node["name"] for node in nodes}) != len(nodes):
        raise ValueError("Kubernetes evidence node identities must be unique")
    checks = {check["id"]: check["status"] for check in evidence["checks"]}
    last_sample: dict[str, datetime] = {}
    readiness: list[str] = []
    pressure: list[str] = []
    unavailable_usage = False
    for sample in evidence["samples"]:
        uid = sample["nodeUid"]
        observed = datetime.fromisoformat(sample["observedAt"].replace("Z", "+00:00"))
        if uid not in node_ids:
            raise ValueError("Kubernetes evidence sample names an undeclared node")
        if not start <= observed <= end:
            raise ValueError("Kubernetes evidence sample lies outside capture window")
        if uid in last_sample and observed <= last_sample[uid]:
            raise ValueError("Kubernetes evidence samples must increase per node")
        last_sample[uid] = observed
        conditions = sample["conditions"]
        readiness.append(conditions["ready"])
        pressure.extend(
            conditions[name] for name in ("memoryPressure", "diskPressure", "pidPressure")
        )
        usage = sample["usage"]
        if usage["source"] == "unavailable":
            unavailable_usage = True
        else:
            usage_start = datetime.fromisoformat(usage["windowStart"].replace("Z", "+00:00"))
            usage_end = datetime.fromisoformat(usage["windowEnd"].replace("Z", "+00:00"))
            if not start <= usage_start < usage_end <= observed:
                raise ValueError(
                    "Kubernetes usage window must be positive and contained before observation"
                )
    incomplete = not node_ids or set(last_sample) != node_ids
    expected_ready = (
        "FAIL"
        if "FALSE" in readiness
        else "UNKNOWN"
        if incomplete or "UNKNOWN" in readiness
        else "PASS"
    )
    expected_pressure = (
        "FAIL"
        if "TRUE" in pressure
        else "UNKNOWN"
        if incomplete or "UNKNOWN" in pressure
        else "PASS"
    )
    if checks["node-readiness"] != expected_ready:
        raise ValueError("Node-readiness check contradicts observed evidence")
    if checks["resource-pressure"] != expected_pressure:
        raise ValueError("Resource-pressure check contradicts observed evidence")
    if (incomplete or unavailable_usage) and checks["interference"] == "PASS":
        raise ValueError("Missing usage evidence cannot establish interference PASS")


def check_kubernetes_benchmark_context(
    evidence: dict[str, Any],
    environment: dict[str, Any],
    raw_manifest: dict[str, Any] | None = None,
) -> None:
    """Bind evidence to an already schema-validated environment and optional Run manifest.

    Consumers independently verify referenced bytes/digests and the trusted
    profile. Timestamp coverage, freshness and required cadence are profile
    obligations; a matching capture is not execution authority.
    """
    check_kubernetes_benchmark_evidence(evidence)
    if (
        evidence["target"]["clusterId"] != environment["cluster"]
        or evidence["environment"]["fingerprint"] != environment["fingerprint"]
    ):
        raise ValueError("Kubernetes evidence does not match the selected environment")
    if raw_manifest is None:
        return
    scope = evidence["scope"]
    if scope["kind"] != "measurement":
        raise ValueError("Preflight evidence cannot substitute for Run measurement evidence")
    if any(scope[key] != raw_manifest[key] for key in ("runId", "testId", "workload")):
        raise ValueError("Kubernetes evidence does not match the selected Run and workload")
    producer = raw_manifest["producer"]
    if (
        raw_manifest["schemaVersion"] != 2
        or producer["name"] != "kube-burner"
        or producer["artifact"]["kind"] not in {"oci-image", "release-archive"}
    ):
        raise ValueError("Kubernetes evidence requires supported kube-burner execution provenance")
    capture = evidence["captureWindow"]
    measurement = raw_manifest["measurementWindow"]

    def parse(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    if (
        not parse(capture["start"])
        <= parse(measurement["start"])
        < parse(measurement["end"])
        <= parse(capture["end"])
    ):
        raise ValueError("Kubernetes evidence must cover the measurement window")
