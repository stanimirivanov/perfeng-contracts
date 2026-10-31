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

    def test_linux_capability_extension_preserves_historical_documents(self):
        presence = copy.deepcopy(self.values["presence"])
        validator = native.schema_validator(self.document, native.FIXTURES["presence"])
        for platform in ("linux", "windows"):
            presence["capabilities"]["operatingSystem"] = platform
            validator.validate(presence)
        presence["capabilities"]["operatingSystem"] = "plan9"
        self.assertFalse(validator.is_valid(presence))

    def test_contract_and_conformance_corpus_validate_without_network(self):
        with patch("socket.create_connection", side_effect=AssertionError("network")):
            self.assertEqual(native.validate_native_worker_api(), (27, 27, 19))

    def test_attempt_inspection_is_worker_scoped_and_never_restores_authority(self):
        request = self.values["inspect-attempt"]
        request_validator = native.schema_validator(self.document, "InspectAttempt")
        request_validator.validate(request)
        for changed in [
            {**request, "protocolVersion": 1},
            {**request, "workerId": "caller-selected"},
            {**request, "leaseCapability": "example-not-a-real-lease-capability-0001"},
        ]:
            self.assertFalse(request_validator.is_valid(changed))

        response_validator = native.schema_validator(self.document, "AttemptInspection")
        for name in ["attempt-active", "attempt-inactive", "attempt-terminal"]:
            response_validator.validate(self.values[name])
            self.assertNotIn("leaseCapability", self.values[name])
            self.assertNotIn("workerId", self.values[name])
        active = copy.deepcopy(self.values["attempt-active"])
        active["leaseCapability"] = "example-not-a-real-lease-capability-0001"
        self.assertFalse(response_validator.is_valid(active))
        terminal = copy.deepcopy(self.values["attempt-terminal"])
        terminal["state"] = "INACTIVE"
        self.assertFalse(response_validator.is_valid(terminal))

    def test_attempt_inspection_http_cases_preserve_identity_and_time_order(self):
        inspection = next(
            case
            for case in self.cases
            if case["operationId"] == "inspectNativeAttempt"
            and case["response"] == "attempt-active"
        )
        native.check_http(self.document, inspection, self.values)
        changed = copy.deepcopy(self.values)
        changed["attempt-active"]["attemptId"] = "33333333-3333-4333-8333-333333333333"
        with self.assertRaisesRegex(ValueError, "requested identity"):
            native.check_http(self.document, inspection, changed)
        changed = copy.deepcopy(self.values)
        changed["attempt-active"]["expiresAt"] = "2026-09-18T12:00:00Z"
        with self.assertRaisesRegex(ValueError, "expired lease"):
            native.check_http(self.document, inspection, changed)

        terminal = next(
            case
            for case in self.cases
            if case["operationId"] == "inspectNativeAttempt"
            and case["response"] == "attempt-terminal"
        )
        changed = copy.deepcopy(self.values)
        changed["attempt-terminal"]["acceptedAt"] = "2026-09-18T12:04:00Z"
        with self.assertRaisesRegex(ValueError, "precedes acceptance"):
            native.check_http(self.document, terminal, changed)

        not_found = next(
            case
            for case in self.cases
            if case["operationId"] == "inspectNativeAttempt" and case["status"] == 404
        )
        changed = copy.deepcopy(self.values)
        changed["attempt-not-found-error"]["code"] = "NOT_AUTHORIZED"
        with self.assertRaises(ValidationError):
            native.check_http(self.document, not_found, changed)

    def test_inspection_path_and_closed_response_cannot_drift(self):
        changed = copy.deepcopy(self.document)
        inspection = changed["paths"].pop("/native-worker/v2/attempts/inspect")
        changed["paths"]["/native-worker/v2/attempts/search"] = inspection
        with self.assertRaisesRegex(ValueError, "reviewed path"):
            native.lint(changed)

        changed = copy.deepcopy(self.document)
        changed["components"]["schemas"]["AttemptInspection"]["oneOf"][0]["properties"][
            "leaseCapability"
        ] = {"type": "string"}
        with self.assertRaisesRegex(ValueError, "contain no authority"):
            native.lint(changed)

    def test_previous_protocol_generation_is_rejected(self):
        presence = copy.deepcopy(self.values["presence"])
        presence["protocolVersion"] = 1
        self.assertFalse(
            native.schema_validator(self.document, "WorkerPresence").is_valid(presence)
        )

        acquire = copy.deepcopy(self.values["acquire"])
        acquire["protocolVersion"] = 1
        self.assertFalse(native.schema_validator(self.document, "AcquireLease").is_valid(acquire))

        lease = copy.deepcopy(self.values["lease"])
        del lease["assignment"]["recipe"]
        self.assertFalse(native.schema_validator(self.document, "Lease").is_valid(lease))

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

    def test_artifact_plan_uses_canonical_contract_formats(self):
        native.check_artifact_formats(self.values)
        self.assertEqual(
            {item["slot"]: item["format"] for item in self.values["lease"]["artifactPlan"]},
            {
                "measurements": "playwright-measurements/v2",
                "manifest": "raw-result/v2",
            },
        )

        changed = copy.deepcopy(self.values)
        changed["lease"]["artifactPlan"][0]["format"] = "playwright-measurements-v2"
        with self.assertRaisesRegex(ValueError, "canonical contract formats"):
            native.check_artifact_formats(changed)

        validator = native.schema_validator(self.document, "ArtifactPlan")
        invalid = copy.deepcopy(self.values["lease"]["artifactPlan"][0])
        invalid["format"] = "../playwright-measurements/v2"
        self.assertFalse(validator.is_valid(invalid))

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

    def test_recipe_requires_every_runner_input_and_rejects_extra_fields(self):
        recipe = self.values["lease"]["assignment"]["recipe"]
        validator = native.schema_validator(self.document, "ExecutionRecipe")
        validator.validate(recipe)
        for name in [
            "journeyId",
            "workloadVersion",
            "workloadSha256",
            "scenario",
            "environment",
            "browserSettings",
        ]:
            changed = {key: value for key, value in recipe.items() if key != name}
            self.assertFalse(validator.is_valid(changed), name)
        for path, value in [
            (("journeyId",), "arbitrary-command"),
            (("workloadSha256",), "not-a-digest"),
            (("scenario", "measurementIterations"), 0),
            (("scenario", "warmupIterations"), 101),
            (("scenario", "pageReuse"), "per-run"),
            (("environment", "fingerprint"), "unknown"),
            (("browserSettings", "viewport", "width"), 0),
            (("browserSettings", "deviceScaleFactor"), 5),
        ]:
            changed = copy.deepcopy(recipe)
            target = changed
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            self.assertFalse(validator.is_valid(changed), path)
        self.assertFalse(validator.is_valid({**recipe, "diagnostics": {"captureIterations": [1]}}))

    def test_recipe_is_bound_to_qualification_and_baseline_capability(self):
        native.check_recipe(self.values)
        for path, value in [
            (("recipe", "environment", "profileId"), "other-host"),
            (("recipe", "environment", "evidenceSha256"), "1" * 64),
            (("executionArtifact", "revision"), "d" * 40),
            (("browser",), "edge"),
            (("diagnosticMode",), "trace"),
        ]:
            changed = copy.deepcopy(self.values)
            target = changed["lease"]["assignment"]
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            with self.assertRaises(ValueError):
                native.check_recipe(changed)

    def test_lease_rejects_unsupported_profile_and_incomplete_artifact_plan(self):
        validator = native.schema_validator(self.document, "Lease")
        lease = self.values["lease"]
        validator.validate(lease)
        for change in [
            lambda value: value["assignment"].update(profile="windows-mainstream"),
            lambda value: value["artifactPlan"].pop(),
            lambda value: value["artifactPlan"].reverse(),
            lambda value: value["artifactPlan"].append(copy.deepcopy(value["artifactPlan"][0])),
            lambda value: value["artifactPlan"][0].update(required=False),
            lambda value: value["assignment"]["target"].update(
                baseUrl="https://user@system.perfeng.invalid"
            ),
        ]:
            changed = copy.deepcopy(lease)
            change(changed)
            self.assertFalse(validator.is_valid(changed))

    def test_protocol_and_baseline_scope_are_not_accidental(self):
        changed = copy.deepcopy(self.document)
        changed["components"]["schemas"]["Lease"]["properties"]["assignment"]["required"].remove(
            "recipe"
        )
        with self.assertRaisesRegex(ValueError, "require the reviewed execution recipe"):
            native.lint(changed)
        changed = copy.deepcopy(self.document)
        changed["components"]["schemas"]["Lease"]["properties"]["assignment"]["properties"][
            "diagnosticMode"
        ] = {"enum": ["baseline", "trace"]}
        with self.assertRaisesRegex(ValueError, "baseline Chromium"):
            native.lint(changed)
        changed = copy.deepcopy(self.document)
        changed["info"]["version"] = "1.0.0"
        with self.assertRaisesRegex(ValueError, "protocol v2"):
            native.lint(changed)


if __name__ == "__main__":
    unittest.main()
