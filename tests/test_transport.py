"""Transport conformance and byte-level provenance of the example fixtures."""

import copy
import hashlib
import unittest
from typing import Any, ClassVar

from jsonschema import Draft202012Validator

from scripts.validate import (
    ROOT,
    check_artifact_reference,
    check_transport_consistency,
    load_contracts,
    read_json,
)


class TransportContractsTest(unittest.TestCase):
    validators: ClassVar[dict[str, Draft202012Validator]]

    @classmethod
    def setUpClass(cls) -> None:
        _, cls.validators = load_contracts()

    def envelope(self, kind: str = "normalized-result", tool: str = "k6") -> dict[str, Any]:
        return read_json(ROOT / f"examples/{kind}/{tool}.json")

    def assert_inconsistent(self, document: dict[str, Any], message: str) -> None:
        contract = "raw-result/v1" if document["kind"] == "RawResult" else "normalized-result/v1"
        self.validators[contract].validate(document)
        with self.assertRaisesRegex(ValueError, message):
            check_transport_consistency(document)

    def test_k6_and_browser_envelopes_resolve_all_references(self) -> None:
        for kind in ("raw-result", "normalized-result"):
            for tool in ("k6", "playwright"):
                with self.subTest(kind=kind, tool=tool):
                    data = self.envelope(kind, tool)
                    self.validators[f"{kind}/v1"].validate(data)
                    check_transport_consistency(data)

    def test_raw_fixture_checksums_sizes_and_workload_hashes(self) -> None:
        for tool, filename in (
            ("k6", "k6-summary.json"),
            ("playwright", "playwright-measurements.json"),
        ):
            with self.subTest(tool=tool):
                raw = self.envelope("raw-result", tool)
                normalized = self.envelope(tool=tool)
                reference = raw["artifacts"][0]
                content = (ROOT / "tests/fixtures/transport" / filename).read_bytes()
                self.assertEqual(reference["sha256"], hashlib.sha256(content).hexdigest())
                self.assertEqual(reference["sizeBytes"], len(content))
                self.assertEqual(normalized["sourceArtifacts"], raw["artifacts"])
                workload_bytes = (ROOT / f"examples/workload/{tool}-smoke.json").read_bytes()
                self.assertEqual(
                    raw["workload"]["sha256"], hashlib.sha256(workload_bytes).hexdigest()
                )
                self.assertEqual(normalized["workload"], raw["workload"])

    def test_derived_reference_hashes_the_completed_envelope(self) -> None:
        reference = read_json(ROOT / "examples/artifact/normalized-reference.json")
        content = (ROOT / "examples/normalized-result/k6.json").read_bytes()
        self.assertEqual(reference["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(reference["sizeBytes"], len(content))
        envelope = self.envelope()
        for source in envelope["sourceArtifacts"]:
            self.assertNotEqual(reference["id"], source["id"])
            self.assertNotEqual(reference["uri"], source["uri"])
            self.assertNotEqual(reference["sha256"], source["sha256"])

    def test_unknown_count_is_preserved_without_changing_v1(self) -> None:
        record = self.envelope()["results"][0]
        summary = read_json(ROOT / "tests/fixtures/transport/k6-summary.json")
        values = summary["metrics"]["http_req_duration"]["values"]
        self.assertEqual(record["distribution"], {"mean": values["avg"], "p95": values["p(95)"]})
        self.validators["result/v2"].validate(record)
        self.assertFalse(self.validators["result/v1"].is_valid({**record, "schemaVersion": 1}))
        record["distribution"]["samples"] = None
        self.validators["result/v2"].validate(record)
        for count in (0, -1, "unknown"):
            with self.subTest(count=count):
                record["distribution"]["samples"] = count
                self.assertFalse(self.validators["result/v2"].is_valid(record))

    def test_browser_statistics_use_only_observed_samples(self) -> None:
        raw = read_json(ROOT / "tests/fixtures/transport/playwright-measurements.json")
        durations = [measurement["durationMs"] for measurement in raw["measurements"]]
        distribution = self.envelope(tool="playwright")["results"][0]["distribution"]
        self.assertEqual(
            distribution,
            {
                "samples": len(durations),
                "mean": sum(durations) / len(durations),
                "min": min(durations),
                "max": max(durations),
            },
        )

    def test_reference_syntax_rejects_bad_digest_size_and_ephemeral_uri(self) -> None:
        original = read_json(ROOT / "examples/artifact/raw-reference.json")
        for key, value in (
            ("sha256", "abc"),
            ("sizeBytes", -1),
            ("id", "not-an-id"),
            ("uri", "file:///tmp/results.json"),
            ("uri", "s3://bucket/key?token=secret"),
            ("uri", "https://example.invalid/key#fragment"),
            ("mediaType", "json"),
        ):
            with self.subTest(key=key, value=value):
                self.assertFalse(self.validators["artifact/v1"].is_valid({**original, key: value}))

    def test_reference_location_must_not_embed_credentials(self) -> None:
        data = read_json(ROOT / "examples/artifact/raw-reference.json")
        data["uri"] = "https://user:password@example.invalid/results.json"
        self.validators["artifact/v1"].validate(data)
        with self.assertRaisesRegex(ValueError, "credentials"):
            check_artifact_reference(data)

    def test_timestamps_need_valid_dates_offsets_and_supported_precision(self) -> None:
        for timestamp in (
            "2026-02-30T12:00:00Z",
            "2026-09-02T12:00:00",
            "2026-09-02T12:00:60Z",
            "2026-09-02T12:00:00.1234567Z",
        ):
            with self.subTest(timestamp=timestamp):
                data = self.envelope()
                data["measurementWindow"]["start"] = timestamp
                self.assertFalse(self.validators["normalized-result/v1"].is_valid(data))

    def test_time_order_compares_instants_not_strings(self) -> None:
        data = self.envelope()
        data["measurementWindow"]["start"] = "2026-09-02T14:00:00+02:00"
        self.validators["normalized-result/v1"].validate(data)
        check_transport_consistency(data)
        data["measurementWindow"]["start"] = data["measurementWindow"]["end"]
        self.assert_inconsistent(data, "start must precede")
        data = self.envelope()
        data["createdAt"] = "2026-09-02T12:01:59Z"
        self.assert_inconsistent(data, "creation must not precede")

    def test_sources_and_metrics_must_belong_to_envelope_run(self) -> None:
        for key in ("sourceArtifacts", "results"):
            with self.subTest(key=key):
                data = self.envelope()
                data[key][0]["runId"] = "perf-20260902-130000-a1b2c3d5"
                self.assert_inconsistent(data, "run ID does not match")

    def test_raw_manifest_cannot_reference_another_run(self) -> None:
        data = self.envelope("raw-result")
        data["artifacts"][0]["runId"] = "perf-20260902-130000-a1b2c3d5"
        self.assert_inconsistent(data, "Artifact run ID")

    def test_duplicate_source_ids_and_locations_are_rejected(self) -> None:
        for field, value, message in (
            ("uri", "s3://perfeng-example/another.json", "Duplicate artifact ID"),
            ("id", "44444444-4444-4444-8444-444444444444", "Duplicate artifact URI"),
        ):
            with self.subTest(field=field):
                data = self.envelope()
                duplicate = copy.deepcopy(data["sourceArtifacts"][0])
                duplicate[field] = value
                data["sourceArtifacts"].append(duplicate)
                self.assert_inconsistent(data, message)

    def test_duplicate_metric_names_are_ambiguous(self) -> None:
        data = self.envelope()
        duplicate = copy.deepcopy(data["results"][0])
        duplicate["distribution"]["mean"] = 99
        data["results"].append(duplicate)
        self.assert_inconsistent(data, "Duplicate metric name")

    def test_normalized_data_cannot_be_presented_as_raw_evidence(self) -> None:
        for kind, key in (("raw-result", "artifacts"), ("normalized-result", "sourceArtifacts")):
            with self.subTest(kind=kind):
                data = self.envelope(kind)
                data[key][0]["kind"] = "normalized"
                self.assertFalse(self.validators[f"{kind}/v1"].is_valid(data))

    def test_required_provenance_and_nonempty_results(self) -> None:
        for path in (("producer", "version"), ("producer", "image"), ("workload", "sha256")):
            with self.subTest(path=path):
                data = self.envelope()
                del data[path[0]][path[1]]
                self.assertFalse(self.validators["normalized-result/v1"].is_valid(data))
        for field in ("results", "sourceArtifacts"):
            with self.subTest(field=field):
                data = self.envelope()
                data[field] = []
                self.assertFalse(self.validators["normalized-result/v1"].is_valid(data))


if __name__ == "__main__":
    unittest.main()
