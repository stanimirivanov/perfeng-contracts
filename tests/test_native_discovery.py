"""Conformance guards for bounded discovery without restored worker authority."""

import copy
import unittest
from typing import Any
from unittest.mock import patch

from jsonschema.exceptions import ValidationError

from scripts import validate_native_worker_api as native
from scripts.validate import read_json


class NativeDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        root = native.ROOT / native.API_PATH
        self.document = read_json(root / "openapi.json")
        self.values = {
            name: read_json(root / "examples" / f"{name}.json") for name in native.FIXTURES
        }
        self.cases = [
            case
            for case in read_json(root / "http-cases.json")
            if case["operationId"] == "discoverNativeAttempt"
        ]

    def case(self, response: str) -> dict[str, Any]:
        return next(case for case in self.cases if case["response"] == response)

    def test_request_has_no_identity_authority_or_history_selector(self) -> None:
        validator = native.schema_validator(self.document, "DiscoverAttempt")
        request = self.values["discover-attempt"]
        validator.validate(request)
        for value in [{}, {"protocolVersion": 1}, {"protocolVersion": "2"}]:
            with self.subTest(value=value):
                self.assertFalse(validator.is_valid(value))
        for field, value in {
            "workerId": "caller-selected",
            "principal": "caller-selected",
            "runId": self.values["lease"]["runId"],
            "attemptId": self.values["lease"]["attemptId"],
            "leaseId": self.values["lease"]["leaseId"],
            "requestId": self.values["lease"]["attemptId"],
            "since": "2026-09-18T12:00:00Z",
            "limit": 10,
            "cursor": "next",
            "leaseCapability": "example-not-a-real-lease-capability-0001",
        }.items():
            with self.subTest(field=field):
                self.assertFalse(validator.is_valid({**request, field: value}))

    def test_discovery_is_offline_and_covers_availability_without_conflating_authority(
        self,
    ) -> None:
        with patch("socket.create_connection", side_effect=AssertionError("network")):
            for case in self.cases:
                native.check_http(self.document, case, self.values)
        validator = native.schema_validator(self.document, "AttemptDiscovery")
        for availability in ["AVAILABLE", "DRAINING", "UNAVAILABLE", "UNREPORTED"]:
            value = {**self.values["discovery-none"], "availability": availability}
            validator.validate(value)
            if availability != "UNREPORTED":
                validator.validate(
                    {**self.values["discovery-active"], "availability": availability}
                )
        self.assertFalse(
            validator.is_valid({**self.values["discovery-none"], "availability": None})
        )
        self.assertFalse(
            validator.is_valid({**self.values["discovery-active"], "availability": "UNREPORTED"})
        )

    def test_no_result_returns_authority_recipe_keys_or_unbounded_attempts(self) -> None:
        validator = native.schema_validator(self.document, "AttemptDiscovery")
        forbidden = {
            "leaseCapability": "example-not-a-real-lease-capability-0001",
            "capabilityHash": "0" * 64,
            "workerId": "caller-selected",
            "uploadUrl": "https://objects.perfeng.invalid/object",
            "uploadHeaders": {},
            "objectKey": "runs/other/measurements",
            "assignment": self.values["lease"]["assignment"],
            "attempts": [],
        }
        for name in ["discovery-none", "discovery-active", "discovery-terminal"]:
            observation = self.values[name]
            for field, value in forbidden.items():
                with self.subTest(response=name, field=field):
                    self.assertFalse(validator.is_valid({**observation, field: value}))
                    if "attempt" in observation:
                        changed = copy.deepcopy(observation)
                        changed["attempt"][field] = value
                        self.assertFalse(validator.is_valid(changed))

    def test_none_is_not_a_historical_attempt_or_negative_acquisition_receipt(self) -> None:
        validator = native.schema_validator(self.document, "AttemptDiscovery")
        for field, value in {
            "attempt": self.values["attempt-inactive"],
            "slotExpiresAt": "2026-09-18T12:02:00Z",
            "neverAcquired": True,
        }.items():
            self.assertFalse(validator.is_valid({**self.values["discovery-none"], field: value}))
        for name in ["discovery-active", "discovery-terminal"]:
            observation = self.values[name]
            for field in observation:
                self.assertFalse(
                    validator.is_valid(
                        {key: value for key, value in observation.items() if key != field}
                    ),
                    field,
                )
            self.assertFalse(
                validator.is_valid({**observation, "attempt": self.values["attempt-inactive"]})
            )
            self.assertFalse(
                validator.is_valid({**observation, "attempt": [observation["attempt"]]})
            )

    def test_found_slot_expiry_is_exclusive_for_active_and_terminal(self) -> None:
        for response in ["discovery-active", "discovery-terminal"]:
            for expiry in ["2026-09-18T12:00:00Z", self.values[response]["serverTime"]]:
                with self.subTest(response=response, expiry=expiry):
                    changed = copy.deepcopy(self.values)
                    changed[response]["slotExpiresAt"] = expiry
                    with self.assertRaisesRegex(ValueError, "expired measurement slot"):
                        native.check_http(self.document, self.case(response), changed)

    def test_found_uses_one_clock_and_exact_active_slot_expiry(self) -> None:
        for response in ["discovery-active", "discovery-terminal"]:
            changed = copy.deepcopy(self.values)
            changed[response]["attempt"]["serverTime"] = "2026-09-18T12:01:10Z"
            with self.assertRaisesRegex(ValueError, "one server observation time"):
                native.check_http(self.document, self.case(response), changed)
        changed = copy.deepcopy(self.values)
        changed["discovery-active"]["slotExpiresAt"] = "2026-09-18T12:02:01Z"
        with self.assertRaisesRegex(ValueError, "differs from the active attempt"):
            native.check_http(self.document, self.case("discovery-active"), changed)
        changed = copy.deepcopy(self.values)
        changed["discovery-active"]["attempt"]["expiresAt"] = "2026-09-18T12:01:00Z"
        with self.assertRaisesRegex(ValueError, "expired lease"):
            native.check_http(self.document, self.case("discovery-active"), changed)

    def test_discovered_terminal_acceptance_cannot_be_in_the_future(self) -> None:
        for kind in ["COMPLETED", "FAILED"]:
            changed = copy.deepcopy(self.values)
            changed["discovery-terminal"]["attempt"]["terminalKind"] = kind
            changed["discovery-terminal"]["attempt"]["acceptedAt"] = changed["discovery-terminal"][
                "serverTime"
            ]
            native.check_http(self.document, self.case("discovery-terminal"), changed)
            changed["discovery-terminal"]["attempt"]["acceptedAt"] = "2026-09-18T12:01:51Z"
            with self.assertRaisesRegex(ValueError, "precedes acceptance"):
                native.check_http(self.document, self.case("discovery-terminal"), changed)

    def test_equivalent_rfc3339_offsets_describe_one_instant(self) -> None:
        changed = copy.deepcopy(self.values)
        changed["discovery-active"]["attempt"]["serverTime"] = "2026-09-18T14:01:00+02:00"
        changed["discovery-active"]["attempt"]["expiresAt"] = "2026-09-18T14:02:00+02:00"
        native.check_http(self.document, self.case("discovery-active"), changed)

    def test_discovery_requires_no_store_and_cannot_return_capability_headers(self) -> None:
        case = self.case("discovery-active")
        with self.assertRaisesRegex(ValueError, "response header missing"):
            native.check_http(self.document, {**case, "headers": {}}, self.values)
        with self.assertRaises(ValidationError):
            native.check_http(
                self.document, {**case, "headers": {"Cache-Control": "public"}}, self.values
            )
        native.check_http(
            self.document,
            {**case, "headers": {**case["headers"], "Content-Type": "application/json"}},
            self.values,
        )
        with self.assertRaisesRegex(ValueError, "capability response headers"):
            native.check_http(
                self.document,
                {
                    **case,
                    "headers": {
                        **case["headers"],
                        "X-Perfeng-Lease": "example-not-a-real-lease-capability-0001",
                    },
                },
                self.values,
            )

    def test_discovery_path_authentication_and_shapes_cannot_drift(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["paths"]["/native-worker/v2/attempts/list"] = changed["paths"].pop(
            "/native-worker/v2/attempts/discover"
        )
        with self.assertRaisesRegex(ValueError, "reviewed path"):
            native.lint(changed)
        changed = copy.deepcopy(self.document)
        _, operation = native.operation(changed, "discoverNativeAttempt")
        operation["security"] = []
        with self.assertRaisesRegex(ValueError, "disables worker authentication"):
            native.lint(changed)
        changed = copy.deepcopy(self.document)
        changed["components"]["schemas"]["DiscoverAttempt"]["properties"]["workerId"] = {
            "type": "string"
        }
        with self.assertRaisesRegex(ValueError, "cannot select"):
            native.lint(changed)

    def test_discovery_closure_time_and_inspection_reuse_cannot_drift(self) -> None:
        for field, value in [
            ("leaseCapability", {"type": "string"}),
            ("serverTime", {"type": "string"}),
            ("attempt", {"$ref": "#/components/schemas/AttemptInspection"}),
            ("slotExpiresAt", {"type": "string"}),
        ]:
            changed = copy.deepcopy(self.document)
            changed["components"]["schemas"]["AttemptDiscovery"]["oneOf"][1]["properties"][
                field
            ] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "Discovery"):
                native.lint(changed)
        changed = copy.deepcopy(self.document)
        changed["components"]["schemas"]["AttemptDiscovery"]["oneOf"][0]["additionalProperties"] = (
            True
        )
        with self.assertRaisesRegex(ValueError, "closed and bounded"):
            native.lint(changed)
        changed = copy.deepcopy(self.document)
        changed["components"]["schemas"]["DiscoveryAvailability"]["enum"].remove("UNREPORTED")
        with self.assertRaisesRegex(ValueError, "absent and recorded"):
            native.lint(changed)


if __name__ == "__main__":
    unittest.main()
