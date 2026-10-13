"""Kubernetes admission, evidence integrity and cross-document comparison boundaries."""

import copy
import unittest
from typing import Any, ClassVar

from jsonschema import Draft202012Validator

from scripts.kubernetes_evidence import (
    check_kubernetes_benchmark_context,
    check_kubernetes_benchmark_evidence,
)
from scripts.validate import ROOT, check_catalogue_consistency, load_contracts, read_json


class KubernetesEvidenceTests(unittest.TestCase):
    validators: ClassVar[dict[str, Draft202012Validator]]

    @classmethod
    def setUpClass(cls) -> None:
        _, cls.validators = load_contracts()

    def evidence(self, name: str = "accepted-preflight") -> dict[str, Any]:
        return read_json(ROOT / f"examples/kubernetes-benchmark-evidence/{name}.json")

    def validate(self, evidence: dict[str, Any]) -> None:
        self.validators["kubernetes-benchmark-evidence/v1"].validate(evidence)
        check_kubernetes_benchmark_evidence(evidence)

    def test_all_evidence_outcomes_and_scopes_are_explicit(self) -> None:
        for name in ("accepted-preflight", "unknown-preflight", "measurement"):
            with self.subTest(name=name):
                self.validate(self.evidence(name))
        rejected = self.evidence("measurement")
        self.assertEqual(rejected["status"], "REJECTED")
        self.assertIn("UNKNOWN", [check["status"] for check in rejected["checks"]])
        self.assertEqual(rejected["samples"][0]["usage"]["source"], "unavailable")

    def test_catalogue_v2_admits_oci_and_archive_without_broadening_v1(self) -> None:
        catalogue = read_json(ROOT / "examples/catalogue/kubernetes-tests-v2.json")
        self.validators["catalogue/v2"].validate(catalogue)
        check_catalogue_consistency(catalogue)
        archive = copy.deepcopy(catalogue)
        archive["tests"][0]["artifact"] = {
            "kind": "release-archive",
            "url": "https://example.com/kube-burner.zip",
            "archiveSha256": "a" * 64,
            "executableSha256": "b" * 64,
        }
        self.validators["catalogue/v2"].validate(archive)
        check_catalogue_consistency(archive)
        legacy = copy.deepcopy(catalogue)
        legacy["apiVersion"] = "performance.perfeng.io/v1"
        legacy["tests"][0]["artifact"] = {"image": catalogue["tests"][0]["artifact"]["image"]}
        self.assertFalse(self.validators["catalogue/v1"].is_valid(legacy))
        native = copy.deepcopy(catalogue)
        native["tests"][0]["artifact"] = {
            "kind": "source-checkout",
            "repository": native["tests"][0]["source"]["repository"],
            "gitSha": native["tests"][0]["source"]["gitSha"],
            "dependencyLock": {"path": "go.sum", "sha256": "a" * 64},
        }
        self.assertFalse(self.validators["catalogue/v2"].is_valid(native))
        catalogue["tests"][0]["workloads"][0]["tool"] = "playwright"
        with self.assertRaisesRegex(ValueError, "Workload tool"):
            check_catalogue_consistency(catalogue)

    def test_checks_are_complete_unique_and_status_cannot_hide_failures(self) -> None:
        for mutate in (
            lambda value: value["checks"].pop(),
            lambda value: value["checks"].append(copy.deepcopy(value["checks"][0])),
            lambda value: value["checks"][1].update(id="cluster-identity"),
            lambda value: value.update(status="REJECTED"),
            lambda value: value["checks"][0].update(status="FAIL"),
            lambda value: value["checks"][0].update(status="UNKNOWN"),
            lambda value: value.update(nodes=[], samples=[]),
        ):
            value = self.evidence()
            mutate(value)
            self.assertFalse(self.validators["kubernetes-benchmark-evidence/v1"].is_valid(value))
        unknown = self.evidence("unknown-preflight")
        unknown["checks"][0]["status"] = "FAIL"
        unknown["status"] = "REJECTED"
        self.validate(unknown)

    def test_usage_is_measured_or_unavailable_never_an_inferred_zero(self) -> None:
        evidence = self.evidence()
        usage = evidence["samples"][0]["usage"]
        usage["cpuMilliCores"] = 0
        self.validate(evidence)
        for value in (None, -1, 0.5, "unknown", True):
            usage["cpuMilliCores"] = value
            self.assertFalse(self.validators["kubernetes-benchmark-evidence/v1"].is_valid(evidence))
        evidence = self.evidence()
        evidence["samples"][0]["usage"] = {"source": "unavailable", "reason": "Metrics unavailable"}
        with self.assertRaisesRegex(ValueError, "Missing usage"):
            self.validate(evidence)
        evidence["checks"][-1]["status"] = "UNKNOWN"
        evidence["status"] = "UNKNOWN"
        self.validate(evidence)
        evidence["samples"][0]["usage"]["cpuMilliCores"] = 0
        self.assertFalse(self.validators["kubernetes-benchmark-evidence/v1"].is_valid(evidence))

    def test_pressure_and_readiness_cannot_contradict_observations(self) -> None:
        for condition, observed, message in (
            ("ready", "FALSE", "Node-readiness"),
            ("ready", "UNKNOWN", "Node-readiness"),
            ("diskPressure", "TRUE", "Resource-pressure"),
            ("memoryPressure", "UNKNOWN", "Resource-pressure"),
        ):
            value = self.evidence()
            value["samples"][0]["conditions"][condition] = observed
            with self.subTest(condition=condition), self.assertRaisesRegex(ValueError, message):
                self.validate(value)

    def test_node_identity_sample_coverage_and_order_are_required(self) -> None:
        cases = []
        value = self.evidence()
        value["nodes"].append(copy.deepcopy(value["nodes"][0]))
        cases.append((value, "unique"))
        value = self.evidence()
        value["samples"][0]["nodeUid"] = "33333333-3333-4333-8333-333333333333"
        cases.append((value, "undeclared node"))
        value = self.evidence()
        value["samples"].append(copy.deepcopy(value["samples"][0]))
        cases.append((value, "increase per node"))
        value = self.evidence()
        other = copy.deepcopy(value["nodes"][0])
        other.update(name="other-worker", uid="33333333-3333-4333-8333-333333333333")
        value["nodes"].append(other)
        cases.append((value, "Node-readiness"))
        for value, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.validate(value)

    def test_capture_and_usage_timestamps_are_bounded(self) -> None:
        for field, timestamp, message in (
            ("observedAt", "2026-10-13T12:00:11Z", "outside capture"),
            ("windowStart", "2026-10-13T11:59:59Z", "usage window"),
            ("windowEnd", "2026-10-13T12:00:11Z", "usage window"),
            ("windowEnd", "2026-10-13T12:00:00Z", "usage window"),
        ):
            value = self.evidence()
            target = value["samples"][0] if field == "observedAt" else value["samples"][0]["usage"]
            target[field] = timestamp
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                self.validate(value)
        value = self.evidence("measurement")
        value["captureWindow"]["end"] = value["captureWindow"]["start"]
        with self.assertRaisesRegex(ValueError, "capture window"):
            self.validate(value)

    def test_scope_is_closed_and_preflight_cannot_claim_run_evidence(self) -> None:
        value = self.evidence()
        value["scope"]["runId"] = "perf-20261013-120000-a1b2c3d4"
        self.assertFalse(self.validators["kubernetes-benchmark-evidence/v1"].is_valid(value))
        value = self.evidence("measurement")
        del value["scope"]["workload"]
        self.assertFalse(self.validators["kubernetes-benchmark-evidence/v1"].is_valid(value))

    def test_context_binds_run_workload_environment_and_capture(self) -> None:
        evidence = self.evidence("measurement")
        environment = {
            "cluster": evidence["target"]["clusterId"],
            "fingerprint": evidence["environment"]["fingerprint"],
        }
        manifest: dict[str, Any] = {
            "schemaVersion": 2,
            "kind": "RawResult",
            "contractsVersion": "0.22.0",
            **{key: evidence["scope"][key] for key in ("runId", "testId", "workload")},
            "producer": {
                "name": "kube-burner",
                "version": "2.8.5",
                "artifact": {
                    "kind": "oci-image",
                    "image": "quay.io/kube-burner/kube-burner@sha256:" + "d" * 64,
                },
            },
            "measurementWindow": dict(evidence["captureWindow"]),
            "createdAt": "2026-10-13T12:00:10Z",
            "artifacts": [read_json(ROOT / "examples/artifact/raw-reference.json")],
        }
        manifest["artifacts"][0]["runId"] = manifest["runId"]
        self.validators["environment/v1"].validate(environment)
        self.validators["raw-result/v2"].validate(manifest)
        check_kubernetes_benchmark_context(evidence, environment, manifest)
        for key, replacement in (
            ("runId", "perf-20261013-120000-b1b2c3d4"),
            ("testId", "other-k8s"),
            ("workload", {**manifest["workload"], "id": "other-workload"}),
        ):
            changed = copy.deepcopy(manifest)
            changed[key] = replacement
            self.validators["raw-result/v2"].validate(changed)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "Run and workload"):
                check_kubernetes_benchmark_context(evidence, environment, changed)
        changed = copy.deepcopy(manifest)
        changed["measurementWindow"]["end"] = "2026-10-13T12:00:11Z"
        with self.assertRaisesRegex(ValueError, "cover the measurement"):
            check_kubernetes_benchmark_context(evidence, environment, changed)
        with self.assertRaisesRegex(ValueError, "Preflight evidence"):
            check_kubernetes_benchmark_context(self.evidence(), environment, manifest)
        for key in ("cluster", "fingerprint"):
            changed = dict(environment)
            changed[key] = "different"
            with self.assertRaisesRegex(ValueError, "selected environment"):
                check_kubernetes_benchmark_context(evidence, changed, manifest)


if __name__ == "__main__":
    unittest.main()
