"""Catalog mutation fixtures exercise complete, authorized snapshot consumption."""

import copy
import unittest
from datetime import datetime
from typing import ClassVar

from jsonschema import Draft202012Validator

from scripts.performance_catalog import check_snapshot, content_digest
from scripts.validate import ROOT, load_contracts, read_json

ISSUER = "https://provider.example/identity"
PRINCIPAL = {"issuer": "https://auth.example/tenant", "id": "argus-service"}
NOW = datetime.fromisoformat("2026-10-22T12:00:00+00:00")


class CatalogTest(unittest.TestCase):
    validator: ClassVar[Draft202012Validator]

    @classmethod
    def setUpClass(cls) -> None:
        _, validators = load_contracts()
        cls.validator = validators["performance-catalog/v1"]

    def pages(self, name: str = "pages") -> list:
        return read_json(ROOT / f"examples/performance-catalog/{name}.json")

    def check(self, pages: list, *, now: datetime = NOW) -> None:
        for page in pages:
            self.validator.validate(page)
        check_snapshot(pages, observed_at=now, principal=PRINCIPAL, issuer=ISSUER)

    def reseal(self, pages: list) -> None:
        items = [item for page in pages for item in page["items"]]
        for page in pages:
            page["snapshot"]["reference"]["sha256"] = content_digest(items)
            page["snapshot"]["totalItems"] = len(items)

    def test_complete_empty_and_digest_wire_format(self) -> None:
        self.check(self.pages())
        self.check(self.pages("empty"))
        self.assertEqual(
            content_digest([]), "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
        )
        pages = self.pages()
        profile = next(
            item for page in pages for item in page["items"] if item["kind"] == "profile"
        )
        profile["selections"][0]["baseline"] = None
        self.reseal(pages)
        self.check(pages)

    def test_missing_mixed_reordered_and_repeated_pages(self) -> None:
        pages = self.pages()
        for invalid in ([], pages[:1], pages[::-1], [pages[0], pages[0]]):
            with self.assertRaises(ValueError):
                self.check(invalid)
        for field in ("reference", "principal", "producer", "validUntil"):
            invalid = self.pages()
            if field == "validUntil":
                invalid[1]["snapshot"][field] = "2026-10-22T14:00:00Z"
            else:
                key = "version" if field == "producer" else "id"
                invalid[1]["snapshot"][field][key] = "2.0.0"
            with self.assertRaisesRegex(ValueError, "Mixed"):
                self.check(invalid)

    def test_cursor_count_and_digest_corruption(self) -> None:
        for mutation in ("cursor", "count", "digest"):
            invalid = self.pages()
            if mutation == "cursor":
                invalid[1]["page"]["cursor"] = "foreign-cursor"
            elif mutation == "count":
                for page in invalid:
                    page["snapshot"]["totalItems"] += 1
            else:
                invalid[0]["items"][0]["displayName"] = "tampered"
            with self.assertRaises(ValueError):
                self.check(invalid)

    def test_duplicate_id_and_reference_substitution(self) -> None:
        invalid = self.pages()
        duplicate = copy.deepcopy(invalid[0]["items"][0])
        duplicate["reference"]["revision"] = "another-revision"
        invalid[-1]["items"].append(duplicate)
        self.reseal(invalid)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.check(invalid)
        invalid = self.pages()
        profile = next(
            item for page in invalid for item in page["items"] if item["kind"] == "profile"
        )
        profile["selections"][0]["environment"]["issuer"] = "https://unrelated.example"
        self.reseal(invalid)
        with self.assertRaisesRegex(ValueError, "reference"):
            self.check(invalid)

    def test_retired_and_unapproved_baselines_cannot_support_active_profile(self) -> None:
        for state in ("CANDIDATE", "QUALIFIED", "RETIRED"):
            invalid = self.pages()
            baseline = next(
                item
                for page in invalid
                for item in page["items"]
                if item["kind"] == "baseline" and item["state"] == "APPROVED"
            )
            baseline["state"] = state
            self.reseal(invalid)
            with self.assertRaisesRegex(ValueError, "not approved"):
                self.check(invalid)

    def test_authority_freshness_and_secret_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "stale"):
            self.check(self.pages(), now=datetime.fromisoformat("2026-10-22T13:00:00+00:00"))
        pages = self.pages()
        with self.assertRaisesRegex(ValueError, "authority"):
            check_snapshot(
                pages,
                observed_at=NOW,
                principal={**PRINCIPAL, "id": "another-tenant"},
                issuer=ISSUER,
            )
        for field in ("command", "configuration", "credentials", "targetUrl"):
            invalid = self.pages()[0]
            invalid["items"][0][field] = "secret"
            self.assertFalse(self.validator.is_valid(invalid))
        for field in ("issuer", "id", "revision", "sha256"):
            invalid = self.pages()[0]
            del invalid["items"][0]["reference"][field]
            self.assertFalse(self.validator.is_valid(invalid))
        invalid = self.pages()[0]
        self.assertFalse(self.validator.is_valid({**invalid, "schemaVersion": 2}))
        invalid["snapshot"]["complete"] = False
        self.assertFalse(self.validator.is_valid(invalid))
