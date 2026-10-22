"""Identity, retry and lifecycle compatibility at the shared contract boundary."""

import copy
import unittest

from scripts.performance_integration import check_exchange
from scripts.validate import ROOT, load_contracts, read_json
from scripts.validate_api import schema_validator
from scripts.validate_performance_integration_api import validate_integration

PROVIDER = "https://provider.example/identity"


class IntegrationTest(unittest.TestCase):
    def trace(self, name: str = "completed") -> list:
        return read_json(ROOT / f"examples/performance-integration/{name}.json")

    def test_offline_openapi_and_all_exchange_fixtures(self) -> None:
        self.assertEqual(validate_integration(), 11)

    def test_json_schema_rejects_incomplete_provenance_and_versions(self) -> None:
        _, validators = load_contracts()
        validator = validators["performance-integration/v1"]
        request = self.trace()[0]
        for name in (
            "service",
            "capability",
            "deployment",
            "environment",
            "workload",
            "profile",
            "policy",
            "baseline",
        ):
            for field in ("issuer", "id", "revision", "sha256"):
                changed = copy.deepcopy(request)
                del changed["data"]["context"][name][field]
                self.assertFalse(validator.is_valid(changed), (name, field))
        for field, value in (
            ("specversion", "2.0"),
            ("dataschema", "https://other.example/v2"),
            ("type", "dev.perfeng.integration.requested.v2"),
            ("credential", "injected"),
        ):
            self.assertFalse(validator.is_valid({**request, field: value}))

    def test_context_and_provider_substitution_are_rejected(self) -> None:
        for name in self.trace()[0]["data"]["context"]:
            changed = self.trace()
            changed[1]["data"]["context"][name] = None
            with self.assertRaisesRegex(ValueError, "context|identity|Deadline"):
                check_exchange(changed, PROVIDER)
        changed = self.trace()
        changed[1]["source"] = "https://attacker.example"
        with self.assertRaisesRegex(ValueError, "provider"):
            check_exchange(changed, PROVIDER)

    def test_retries_are_idempotent_but_cannot_change_payload_or_run(self) -> None:
        trace = self.trace()
        check_exchange([trace[0], copy.deepcopy(trace[0]), *trace[1:]], PROVIDER)
        for field in ("deadline", "workload", "principal", "baseline"):
            changed = self.trace()
            retry = copy.deepcopy(changed[0])
            retry["data"]["context"][field] = changed[0]["data"]["context"]["profile"]
            with self.assertRaises(ValueError):
                check_exchange([changed[0], retry], PROVIDER)
        changed = self.trace()
        changed[2]["data"]["run"]["id"] = "another-run"
        with self.assertRaisesRegex(ValueError, "different run"):
            check_exchange(changed, PROVIDER)

    def test_invalid_state_progression_revision_and_deadline(self) -> None:
        for state, revision in (("ACCEPTED", 1), ("COMPLETED", 0)):
            changed = self.trace()
            changed[-1]["data"].update(state=state, revision=revision)
            with self.assertRaises(ValueError):
                check_exchange(changed, PROVIDER)
        changed = self.trace()
        extra = copy.deepcopy(changed[-1])
        extra["id"] = "late-cancel"
        extra["data"].update(state="CANCELLED", revision=2)
        with self.assertRaisesRegex(ValueError, "Terminal"):
            check_exchange([*changed, extra], PROVIDER)
        changed = self.trace()
        changed[1]["time"] = changed[0]["data"]["context"]["deadline"]
        with self.assertRaisesRegex(ValueError, "expired"):
            check_exchange(changed, PROVIDER)

    def test_cancellation_can_lose_race_to_completion(self) -> None:
        changed = self.trace("cancelled")
        changed[-1]["data"]["state"] = "COMPLETED"
        check_exchange(changed, PROVIDER)

    def test_cancelling_cannot_resume_and_admission_cannot_flip(self) -> None:
        changed = self.trace("cancelled")
        changed[-1]["data"]["state"] = "RUNNING"
        with self.assertRaisesRegex(ValueError, "Illegal"):
            check_exchange(changed, PROVIDER)
        acceptance = self.trace()[1]
        acceptance["id"] = "contradictory-admission"
        with self.assertRaisesRegex(ValueError, "disposition"):
            check_exchange([*self.trace("rejected"), acceptance], PROVIDER)
        changed = self.trace()
        changed[1]["data"]["run"]["issuer"] = "https://other.example"
        with self.assertRaisesRegex(ValueError, "Run issuer"):
            check_exchange(changed, PROVIDER)

    def test_http_operations_share_closed_generated_schemas(self) -> None:
        api = read_json(ROOT / "api/performance-integration/v1/openapi.json")
        self.assertEqual(api["security"], [{"bearerAuth": []}])
        for path in api["paths"].values():
            for method in ("get", "post"):
                if method not in path:
                    continue
                responses = path[method]["responses"]
                for status in ("400", "401", "403", "404", "409", "410", "429", "503"):
                    error = {"code": "unavailable", "message": "Retry later"}
                    schema_validator(api, "Error").validate(error)
                    self.assertIn(status, responses)
                self.assertIn("Retry-After", responses["429"]["headers"])
        self.assertEqual(len(api["paths"]), 3)
        pending, terminal = self.trace("cancelled")[-2:]
        schema_validator(api, "Cancelling").validate(pending)
        schema_validator(api, "Terminal").validate(terminal)
        self.assertFalse(schema_validator(api, "Terminal").is_valid(pending))
        self.assertFalse(schema_validator(api, "Cancelling").is_valid(terminal))
