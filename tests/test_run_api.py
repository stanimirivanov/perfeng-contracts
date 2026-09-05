import copy
import json
import unittest
from unittest.mock import patch

from jsonschema.exceptions import ValidationError

from scripts import validate_api as api
from scripts.validate import load_contracts, read_json, validate_bundle


class RunApiTests(unittest.TestCase):
    def setUp(self):
        root = api.ROOT / api.API_PATH
        self.document = read_json(root / "openapi.json")
        self.transitions = read_json(root / "transitions.json")
        self.examples = {
            name: read_json(root / "examples" / (name + ".json")) for name in api.FIXTURES
        }
        self.cases = read_json(root / "http-cases.json")

    def test_all_contracts_and_http_fixtures_validate_without_network(self):
        with patch("socket.create_connection", side_effect=AssertionError("network")):
            self.assertEqual(api.validate_api(), 14)
            self.assertEqual(validate_bundle(), (13, 26))

    def test_artifact_listing_is_scoped_unique_and_ordered(self):
        case = next(c for c in self.cases if c["operationId"] == "listRunArtifacts")
        api.check_http(self.document, case, self.examples)

        empty = copy.deepcopy(self.examples)
        empty["artifacts"]["artifacts"] = []
        api.check_http(self.document, case, empty)

        original = self.examples["artifacts"]
        changes = []

        wrong_run = copy.deepcopy(original)
        wrong_run["artifacts"][0]["runId"] = "perf-20260902-120000-ffffffff"
        changes.append(wrong_run)

        unordered = copy.deepcopy(original)
        unordered["artifacts"].reverse()
        changes.append(unordered)

        duplicate_id = copy.deepcopy(original)
        duplicate_id["artifacts"][1]["id"] = duplicate_id["artifacts"][0]["id"]
        changes.append(duplicate_id)

        duplicate_location = copy.deepcopy(original)
        duplicate_location["artifacts"][1]["uri"] = duplicate_location["artifacts"][0]["uri"]
        changes.append(duplicate_location)

        for artifacts in changes:
            examples = {**self.examples, "artifacts": artifacts}
            with self.assertRaises(ValueError):
                api.check_http(self.document, case, examples)

        invalid = copy.deepcopy(self.examples)
        invalid["artifacts"]["artifacts"][0]["uri"] += "?signature=secret"
        with self.assertRaises(ValidationError):
            api.check_http(self.document, case, invalid)

        credentialed = copy.deepcopy(self.examples)
        credentialed["artifacts"]["artifacts"][0]["uri"] = (
            "https://user@example.com/runs/perf-20260902-120000-abcdef12/raw-result.json"
        )
        with self.assertRaises(ValueError):
            api.check_http(self.document, case, credentialed)

    def test_required_request_fields_and_approved_resource_identity(self):
        validator = api.schema_validator(self.document, "CreateRun")
        original = self.examples["create"]
        for key in original:
            value = {k: v for k, v in original.items() if k != key}
            self.assertFalse(validator.is_valid(value))
        for field, value in [
            ("catalogue", {"id": "x", "version": "latest", "sha256": "a" * 64}),
            ("environment", {"id": "https://example.com", "version": "1.0.0", "sha256": "a" * 64}),
            ("candidate", {"gitSha": "a" * 40, "image": "example:latest"}),
            ("profile", "nightly"),
            ("command", "shell"),
            ("credentials", {"token": "secret"}),
        ]:
            self.assertFalse(validator.is_valid({**original, field: value}), field)

    def test_json_parser_rejects_duplicates_nonfinite_oversize_and_non_utf8(self):
        for body in [
            b'{"a":1,"a":2}',
            b'{"a":{"b":1,"b":2}}',
            b'{"x":NaN}',
            b'{"x":1e999}',
            b"\xff",
            b" " * 65537,
        ]:
            with self.assertRaises(ValueError):
                api.parse_request(body)
        compact = json.dumps(self.examples["create"]).encode()
        reordered = json.dumps(
            dict(reversed(list(self.examples["create"].items()))), indent=2
        ).encode()
        self.assertEqual(api.parse_request(compact), api.parse_request(reordered))

    def test_candidate_image_is_a_registry_digest_not_a_url_or_local_id(self):
        validator = api.schema_validator(self.document, "Candidate")
        for image in [
            "https://example.com/image@sha256:" + "a" * 64,
            "sha256:" + "a" * 64,
            "runner@sha256:" + "a" * 64,
        ]:
            self.assertFalse(validator.is_valid({"gitSha": "b" * 40, "image": image}))
        validator.validate(
            {
                "gitSha": "b" * 40,
                "image": "localhost:5000/team/runner@sha256:" + "a" * 64,
            }
        )

    def test_in_progress_requires_retry_delay_and_errors_match_http_status(self):
        examples = copy.deepcopy(self.examples)
        examples["error"]["code"] = "REQUEST_IN_PROGRESS"
        case = next(c for c in self.cases if c["operationId"] == "createRun" and c["status"] == 409)
        with self.assertRaises(ValueError):
            api.check_http(self.document, case, examples)
        api.check_http(self.document, {**case, "headers": {"Retry-After": 3}}, examples)
        examples["error"]["code"] = "NOT_FOUND"
        with self.assertRaises(ValidationError):
            api.check_http(self.document, case, examples)

    def test_error_detail_paths_are_json_pointers(self):
        validator = api.schema_validator(self.document, "Error")
        value = {
            **self.examples["error"],
            "details": [{"path": "/candidate/image", "message": "Invalid digest"}],
        }
        validator.validate(value)
        for path in ["candidate.image", "/invalid~escape"]:
            value["details"][0]["path"] = path
            self.assertFalse(validator.is_valid(value))

    def test_snapshot_lifecycle_and_failure_fields(self):
        validator = api.schema_validator(self.document, "Run")
        for name in ["created", "completed", "aborted", "invalid"]:
            validator.validate(self.examples[name])
        for change in [
            {"state": "INCONCLUSIVE"},
            {"state": "PASS"},
            {"quality": "PASS"},
            {"finishedAt": "2026-09-02T12:01:00Z"},
            {"revision": 0},
            {"toolExitCode": 256},
        ]:
            self.assertFalse(validator.is_valid({**self.examples["created"], **change}))
        completed = self.examples["completed"]
        self.assertEqual(completed["toolExitCode"], 99)
        api.check_run(completed)  # A threshold failure does not become a lifecycle verdict.
        for changed in [
            {**completed, "finishedAt": "2026-09-02T11:00:00Z"},
            {**self.examples["created"], "revision": 2},
            {**self.examples["invalid"], "failure": {"code": "TOOL_ERROR", "message": "x"}},
            {**self.examples["cancelling"], "updatedAt": "2026-09-02T11:00:00Z"},
        ]:
            with self.assertRaises(ValueError):
                api.check_run(changed)

    def test_cancel_http_codes_require_the_documented_states(self):
        for status, name in [(202, "cancelling"), (200, "aborted")]:
            case = {
                "operationId": "cancelRun",
                "status": status,
                "pathParameters": {"runId": "perf-20260902-120000-abcdef12"},
                "response": name,
            }
            api.check_http(self.document, case, self.examples)
            with self.assertRaises(ValidationError):
                api.check_http(self.document, {**case, "response": "completed"}, self.examples)

    def test_cancellation_distinguishes_pre_dispatch_and_dispatched_runs(self):
        self.assertEqual(self.transitions["CREATED"], ["VALIDATING", "ABORTED"])
        self.assertEqual(
            self.transitions["VALIDATING"],
            ["PROVISIONING", "INVALID", "INFRASTRUCTURE_FAILURE", "ABORTED"],
        )
        for state in [
            "PROVISIONING",
            "WARMING_UP",
            "RUNNING",
            "COLLECTING",
            "ANALYZING",
            "REPORTING",
        ]:
            self.assertIn("CANCELLING", self.transitions[state])
            self.assertNotIn("ABORTED", self.transitions[state])
        self.assertEqual(self.examples["aborted"]["revision"], 2)

        transitions = copy.deepcopy(self.transitions)
        transitions["CREATED"][-1] = "CANCELLING"
        with self.assertRaises(ValueError):
            api.lint(self.document, transitions)

    def test_create_requires_idempotency_and_consistent_response_headers(self):
        original = self.cases[0]
        changes = [
            {"requestHeaders": {}},
            {"requestHeaders": {"Idempotency-Key": "short"}},
            {"headers": {}},
            {
                "headers": {
                    **original["headers"],
                    "Location": "/v1/runs/perf-20260902-120000-ffffffff",
                }
            },
            {
                "headers": {
                    **original["headers"],
                    "Idempotency-Key-Expires-At": "2026-09-02T13:00:00Z",
                }
            },
        ]
        for change in changes:
            with self.assertRaises((ValueError, ValidationError)):
                api.check_http(self.document, {**original, **change}, self.examples)
        changed = copy.deepcopy(self.examples)
        changed["created"]["request"]["testSuite"] = "another-suite"
        with self.assertRaises(ValueError):
            api.check_http(self.document, original, changed)

    def test_baseline_create_uses_completed_evidence_and_server_actor(self):
        validator = api.schema_validator(self.document, "CreateBaseline")
        original = self.examples["baseline-create"]
        validator.validate(original)
        for key in original:
            self.assertFalse(validator.is_valid({k: v for k, v in original.items() if k != key}))

        changed = copy.deepcopy(original)
        changed["artifact"]["kind"] = "raw"
        self.assertFalse(validator.is_valid(changed))
        self.assertFalse(validator.is_valid({**original, "actor": "caller-selected"}))

        case = next(c for c in self.cases if c["operationId"] == "createBaseline")
        api.check_http(self.document, case, self.examples)
        with self.assertRaises(ValueError):
            api.check_http(
                self.document,
                {**case, "headers": {"Location": "/v1/baselines/other/versions/2.0.0"}},
                self.examples,
            )

    def test_baseline_transitions_are_revision_checked_and_state_specific(self):
        validator = api.schema_validator(self.document, "BaselineTransition")
        transitions = [
            self.examples["baseline-transition"],
            {
                "expectedRevision": 1,
                "state": "QUALIFIED",
                "qualification": {
                    "status": "PASSED",
                    "reasons": [],
                    "sampleCount": 40,
                    "maximumCv": 0.08,
                },
                "reason": "Evidence met the reviewed policy.",
            },
            {
                "expectedRevision": 1,
                "state": "RETIRED",
                "qualification": {
                    "status": "FAILED",
                    "reasons": ["Variability exceeded the reviewed policy."],
                },
                "reason": "Candidate rejected during qualification.",
            },
            {
                "expectedRevision": 3,
                "state": "RETIRED",
                "reason": "Superseded by another approved version.",
            },
        ]
        for transition in transitions:
            validator.validate(transition)

        for transition in [
            {**transitions[0], "expectedRevision": 0},
            {**transitions[0], "qualification": transitions[1]["qualification"]},
            {k: v for k, v in transitions[1].items() if k != "qualification"},
            {**transitions[1], "qualification": transitions[2]["qualification"]},
        ]:
            self.assertFalse(validator.is_valid(transition))

        case = next(c for c in self.cases if c["operationId"] == "transitionBaseline")
        api.check_http(self.document, case, self.examples)
        changed = copy.deepcopy(self.examples)
        changed["baseline-approved"]["revision"] = 4
        with self.assertRaises(ValueError):
            api.check_http(self.document, case, changed)

    def test_baseline_reads_are_exact_versioned_resources(self):
        case = next(c for c in self.cases if c["operationId"] == "getBaseline")
        api.check_http(self.document, case, self.examples)
        with self.assertRaises(ValueError):
            api.check_http(
                self.document,
                {**case, "pathParameters": {**case["pathParameters"], "version": "2.0.0"}},
                self.examples,
            )
        with self.assertRaises(ValidationError):
            api.check_http(
                self.document,
                {**case, "pathParameters": {**case["pathParameters"], "version": "latest"}},
                self.examples,
            )

    def test_authentication_remote_refs_and_terminal_escape_are_rejected(self):
        document = copy.deepcopy(self.document)
        document["paths"]["/v1/runs"]["post"]["security"] = []
        with self.assertRaises(ValueError):
            api.lint(document, self.transitions)
        for key, value in [
            ("$ref", "https://example.com/schema"),
            ("$ref", "#/missing"),
            ("$id", "https://example.com/root"),
            ("$dynamicRef", "https://example.com/schema"),
        ]:
            with self.assertRaises(ValueError):
                api.check_local_references({key: value}, self.document)
        transitions = copy.deepcopy(self.transitions)
        transitions["ABORTED"] = ["RUNNING"]
        with self.assertRaises(ValueError):
            api.lint(self.document, transitions)

    def test_legacy_run_metadata_is_not_silently_extended(self):
        _, validators = load_contracts()
        legacy = validators["run/v1"].schema["properties"]["run"]["properties"]["status"]["enum"]
        current = self.document["components"]["schemas"]["RunState"]["enum"]
        self.assertIn("INCONCLUSIVE", legacy)
        self.assertNotIn("CANCELLING", legacy)
        self.assertNotIn("INCONCLUSIVE", current)
        self.assertIn("CANCELLING", current)
        for terminal in api.TERMINAL:
            self.assertEqual(self.transitions[terminal], [])


if __name__ == "__main__":
    unittest.main()
