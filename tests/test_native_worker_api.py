import copy
import unittest
from unittest.mock import patch

from jsonschema.exceptions import ValidationError

from scripts import validate_native_worker_api as native
from scripts.validate import read_json


class NativeWorkerApiTests(unittest.TestCase):
    def setUp(self):
        root = native.ROOT / native.API_PATH
        self.document = read_json(root / "openapi.json")
        self.values = {
            name: read_json(root / "examples" / f"{name}.json") for name in native.FIXTURES
        }
        self.rejections = {
            name: read_json(root / "rejections" / f"{name}.json") for name in native.REJECTIONS
        }
        self.cases = read_json(root / "http-cases.json")

    def test_contract_and_conformance_corpus_validate_without_network(self):
        with patch("socket.create_connection", side_effect=AssertionError("network")):
            self.assertEqual(native.validate_native_worker_api(), (16, 11, 10))

    def test_presence_cannot_select_identity_qualification_or_parallel_capacity(self):
        validator = native.schema_validator(self.document, "WorkerPresence")
        presence = self.values["presence"]
        for changed in [
            {**presence, "workerId": "caller-selected"},
            {**presence, "qualified": True},
            {
                **presence,
                "capabilities": {**presence["capabilities"], "capacity": 2},
            },
        ]:
            self.assertFalse(validator.is_valid(changed))

        document = copy.deepcopy(self.document)
        document["components"]["schemas"]["WorkerPresence"]["properties"]["workerId"] = {
            "type": "string"
        }
        with self.assertRaisesRegex(ValueError, "request-selected"):
            native.lint(document)

    def test_state_dimensions_remain_separate(self):
        status = self.values["presence-status"]
        self.assertEqual(status["availability"], "AVAILABLE")
        self.assertEqual(status["qualification"]["status"], "QUALIFIED")
        self.assertTrue(status["authorizedToAcquire"])
        validator = native.schema_validator(self.document, "PresenceStatus")
        for field in ["availability", "qualification", "authorizedToAcquire"]:
            changed = {name: value for name, value in status.items() if name != field}
            self.assertFalse(validator.is_valid(changed), field)

    def test_lease_and_grant_lifetimes_are_server_bounded(self):
        native.check_times(self.values)
        for name, field, value in [
            ("lease", "expiresAt", "2026-09-18T12:00:00Z"),
            ("lease", "renewAfterSeconds", 120),
            ("renewal", "stopBy", "2026-09-18T12:04:00Z"),
            ("upload-grant", "expiresAt", "2026-09-18T12:03:00Z"),
        ]:
            changed = copy.deepcopy(self.values)
            changed[name][field] = value
            with self.assertRaises(ValueError):
                native.check_times(changed)

    def test_artifact_publication_is_attempt_scoped_and_byte_exact(self):
        native.check_exact_object_scope(self.values)
        changes = [
            ("upload-grant", "objectKey", "runs/other/attempts/other/measurements"),
            ("upload-grant", "sha256", "a" * 64),
            ("upload-grant", "maximumBytes", 1024),
            (
                "upload-grant",
                "uploadUrl",
                "https://objects.perfeng.invalid/perfeng-artifacts/runs/other?X-Amz-Algorithm=AWS4-HMAC-SHA256",
            ),
            (
                "upload-grant",
                "uploadHeaders",
                {
                    "content-type": "text/plain",
                    "x-amz-checksum-sha256": "//////////////////////////////////////////8=",
                },
            ),
            (
                "upload-grant",
                "uploadHeaders",
                {
                    "content-type": "application/json",
                    "x-amz-checksum-sha256": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                },
            ),
            ("artifact", "uri", "s3://perfeng/runs/other/measurements"),
            ("artifact", "size", 4097),
        ]
        for name, field, value in changes:
            changed = copy.deepcopy(self.values)
            changed[name][field] = value
            with self.assertRaises(ValueError):
                native.check_exact_object_scope(changed)

        changed = copy.deepcopy(self.values)
        changed["upload-grant"]["uploadUrl"] = changed["upload-grant"]["uploadUrl"].replace(
            "X-Amz-Expires=120", "X-Amz-Expires=121"
        )
        with self.assertRaisesRegex(ValueError, "declared grant expiry"):
            native.check_exact_object_scope(changed)

    def test_lease_mutations_require_capability_attempt_and_revision_fences(self):
        fixtures = {
            "RenewLease": self.values["renew"],
            "ReleaseLease": self.values["release"],
            "UploadGrantRequest": self.values["upload-request"],
            "RegisterArtifact": self.values["register-artifact"],
            "TerminalReport": self.values["terminal-completed"],
        }
        for schema, fixture in fixtures.items():
            for field in ["attemptId", "expectedRunRevision"]:
                changed = {name: value for name, value in fixture.items() if name != field}
                self.assertFalse(
                    native.schema_validator(self.document, schema).is_valid(changed),
                    f"{schema}.{field}",
                )

        case = next(case for case in self.cases if case["operationId"] == "registerNativeArtifact")
        without_capability = {**case, "requestHeaders": {}}
        with self.assertRaisesRegex(ValueError, "parameter missing"):
            native.check_http(self.document, without_capability, self.values)

    def test_stale_leases_and_conflicting_duplicates_are_explicit(self):
        for operation_id in native.LEASE_OPERATIONS:
            _, operation = native.operation(self.document, operation_id)
            self.assertIn("409", operation["responses"])
            self.assertIn("410", operation["responses"])
        dispositions = self.document["components"]["schemas"]["TerminalAck"]["properties"][
            "disposition"
        ]["enum"]
        self.assertEqual(dispositions, ["ACCEPTED", "ALREADY_ACCEPTED"])

        document = copy.deepcopy(self.document)
        _, operation = native.operation(document, "registerNativeArtifact")
        del operation["responses"]["410"]
        with self.assertRaisesRegex(ValueError, "lost-lease"):
            native.lint(document)

    def test_upload_locations_are_server_selected_and_presigned(self):
        upload_request = self.values["upload-request"]
        validator = native.schema_validator(self.document, "UploadGrantRequest")
        self.assertFalse(validator.is_valid({**upload_request, "objectKey": "arbitrary/key"}))

        acquire = next(
            case
            for case in self.cases
            if case["operationId"] == "acquireNativeLease" and case["status"] == 200
        )
        with self.assertRaisesRegex(ValueError, "response header missing"):
            native.check_http(self.document, {**acquire, "headers": {}}, self.values)

        _, grant_operation = native.operation(self.document, "createNativeUploadGrant")
        self.assertNotIn("headers", grant_operation["responses"]["201"])
        self.assertNotIn("UploadCapability", self.document["components"]["schemas"])
        upload_grant = self.values["upload-grant"]
        self.assertIn("X-Amz-Signature=", upload_grant["uploadUrl"])
        self.assertEqual(
            set(upload_grant["uploadHeaders"]),
            {"content-type", "x-amz-checksum-sha256"},
        )

        document = copy.deepcopy(self.document)
        _, changed_grant = native.operation(document, "createNativeUploadGrant")
        changed_grant["responses"]["201"]["headers"] = {
            "X-Perfeng-Upload-Grant": {"schema": {"type": "string"}}
        }
        with self.assertRaisesRegex(ValueError, "response body"):
            native.lint(document)

        for fixture in self.values.values():
            serialized = str(fixture).lower()
            self.assertNotIn("authorization", serialized)

    def test_fixture_endpoints_are_reserved_and_non_routable(self):
        native.check_fixture_safety(self.values, self.rejections, self.cases)
        changed = copy.deepcopy(self.values)
        changed["presence"]["qualificationEvidence"]["runner"]["repository"] = (
            "https://github.com/example/perfeng-playwright.git"
        )
        with self.assertRaisesRegex(ValueError, "non-routable"):
            native.check_fixture_safety(changed, self.rejections, self.cases)

        changed = copy.deepcopy(self.values)
        changed["upload-grant"]["uploadUrl"] = changed["upload-grant"]["uploadUrl"].replace(
            "EXAMPLE-NOT-A-REAL-ACCESS-KEY", "AKIAIOSFODNN7EXAMPLE"
        )
        with self.assertRaisesRegex(ValueError, "non-secret placeholders"):
            native.check_fixture_safety(changed, self.rejections, self.cases)

    def test_cancellation_and_terminal_variants_are_closed(self):
        renewal = self.values["renewal"]
        validator = native.schema_validator(self.document, "LeaseRenewal")
        without_deadline = {name: value for name, value in renewal.items() if name != "stopBy"}
        self.assertFalse(validator.is_valid(without_deadline))
        self.assertFalse(validator.is_valid({**renewal, "cancellationRequested": False}))

        terminal = native.schema_validator(self.document, "TerminalReport")
        completed = self.values["terminal-completed"]
        failed = self.values["terminal-failed"]
        terminal.validate(completed)
        terminal.validate(failed)
        with self.assertRaises(ValidationError):
            terminal.validate({**completed, "kind": "CANCELLED"})


if __name__ == "__main__":
    unittest.main()
