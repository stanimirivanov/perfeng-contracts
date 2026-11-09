"""Run pinned AxonOps compatibility probes in a private loopback namespace."""

import argparse
import hashlib
import http.client
import io
import json
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urljoin

from jsonschema import Draft202012Validator

from scripts.contracts_history import INVENTORY, pack_profile, validate_inventory
from scripts.contracts_pack import blob, git
from scripts.validate import ROOT, read_json, references

LOCK = ROOT / "tests/qualification/axonops/candidate.lock.json"
REQUIRED = {"current", "historical", "references", "jsonCompatibility", "byteIdentity"}
BASE = "https://perfeng.dev/"
PORT = 18081


def receipt(checks: dict[str, bool]) -> dict[str, Any]:
    """Require an explicit pass for every capability before reporting admission."""
    return {
        "status": "ADMITTED"
        if all(checks.get(name) is True for name in REQUIRED)
        else "NOT_ADMITTED",
        "checks": {name: checks.get(name) for name in sorted(REQUIRED | {"openapi"})},
    }


def schema_refs(
    path: str, document: Any, schemas: dict[str, Any], subjects: dict[str, str]
) -> list[dict[str, Any]]:
    """Bind external JSON Schema references to exact profile subjects and versions."""
    aliases: dict[str, str] = {}
    for name, schema in schemas.items():
        keys = [BASE + name]
        if isinstance(schema, dict) and isinstance(schema.get("$id"), str):
            keys.append(urljoin(BASE + name, schema["$id"]))
        for key in keys:
            if key in aliases and aliases[key] != name:
                raise ValueError("Ambiguous schema identifier")
            aliases[key] = name
    base = (
        urljoin(BASE + path, document.get("$id", "")) if isinstance(document, dict) else BASE + path
    )
    result = {}
    for ref in references(document):
        target = urldefrag(ref)[0]
        if not target:
            continue
        resolved = urljoin(base, target)
        if resolved in {base, BASE + path}:
            continue
        if resolved not in aliases:
            raise ValueError(f"Undeclared schema reference in {path}")
        result[target] = {"name": target, "subject": subjects[aliases[resolved]], "version": 1}
    return [result[name] for name in sorted(result)]


def request(method: str, path: str, payload: Any = None) -> tuple[int, Any]:
    connection = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5)
    try:
        connection.request(
            method,
            path,
            None if payload is None else json.dumps(payload),
            {"Content-Type": "application/vnd.schemaregistry.v1+json"},
        )
        response = connection.getresponse()
        data = response.read(16 * 1024 * 1024 + 1)
        if len(data) > 16 * 1024 * 1024:
            raise ValueError("Registry response exceeds limit")
        return response.status, json.loads(data)
    finally:
        connection.close()


def register(subject: str, text: str, kind: str = "JSON", refs: Any = None) -> tuple[int, Any]:
    return request(
        "POST",
        f"/subjects/{subject}/versions",
        {
            "schema": text,
            "schemaType": kind,
            "references": refs or [],
        },
    )


def compatible(subject: str, text: str, kind: str = "JSON") -> tuple[int, Any]:
    return request(
        "POST",
        f"/compatibility/subjects/{subject}/versions/latest",
        {
            "schema": text,
            "schemaType": kind,
        },
    )


def exact_lookup(subject: str, identifier: int, version: int, text: str) -> bool:
    paths = (f"/subjects/{subject}/versions/{version}", f"/schemas/ids/{identifier}")
    for path in paths:
        first = request("GET", path)
        if first[0] != 200 or first[1].get("schema") != text or request("GET", path) != first:
            return False
    return True


def corpus() -> dict[str, dict[str, bytes]]:
    """Use exact current Git blobs and all locally verifiable SR-10 profiles."""
    head = git(ROOT, "rev-parse", "HEAD").decode().strip()
    names = (
        git(ROOT, "ls-tree", "-r", "--name-only", head, "--", "schemas", "api")
        .decode()
        .splitlines()
    )
    result = {"current": {path: blob(ROOT, head, path) for path in names if relevant(path)}}
    inventory = read_json(INVENTORY)
    validate_inventory(inventory)
    for revision, profile in inventory["profiles"].items():
        content = pack_profile(ROOT, revision, profile)
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as stream:
            documents = {}
            for member in stream:
                if member.isfile() and relevant(member.name):
                    entry = stream.extractfile(member)
                    if entry is None:
                        raise ValueError("Historical archive member unavailable")
                    documents[member.name] = entry.read()
            result[revision] = documents
    return result


def relevant(path: str) -> bool:
    return (path.startswith("schemas/") and path.endswith(".schema.json")) or (
        path.startswith("api/") and path.endswith("/openapi.json") and path.count("/") == 3
    )


def json_corpus(profile: str, documents: dict[str, bytes]) -> list[dict[str, Any]]:
    texts = {
        path: raw.decode("utf-8") for path, raw in documents.items() if path.startswith("schemas/")
    }
    schemas = {path: json.loads(raw) for path, raw in texts.items()}
    subjects = {path: f"sr29-{profile}-{index}" for index, path in enumerate(sorted(texts))}
    by_subject = {subject: path for path, subject in subjects.items()}
    rows: dict[str, dict[str, Any]] = {}
    pending = {path: schema_refs(path, value, schemas, subjects) for path, value in schemas.items()}
    while pending:
        ready = [
            path
            for path, refs in pending.items()
            if all(by_subject[ref["subject"]] in rows for ref in refs)
        ]
        if not ready:
            raise ValueError("Cyclic cross-document references in the selected profile")
        for path in sorted(ready):
            status, response = register(subjects[path], texts[path], refs=pending.pop(path))
            rows[path] = {
                "profile": profile,
                "path": path,
                "registrationStatus": status,
                "errorCode": response.get("error_code") if status != 200 else None,
                "passed": status == 200
                and exact_lookup(subjects[path], response["id"], 1, texts[path]),
            }
    return list(rows.values())


def probe_compatibility() -> dict[str, bool]:
    base = {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}}}
    conditional = {**base, "if": {"properties": {"x": {"const": 1}}}, "then": {"required": ["y"]}}
    witness = {"x": 1}
    if not Draft202012Validator(base).is_valid(witness) or Draft202012Validator(
        conditional
    ).is_valid(witness):
        raise ValueError("Conditional compatibility witness does not distinguish the schemas")
    initial, _ = register("sr29-compatibility", json.dumps(base))
    cases = {
        "descriptionOnly": ({**base, "description": "metadata"}, True),
        "requiredField": ({**base, "required": ["y"]}, False),
        "conditionalTightening": (conditional, False),
    }
    results = {}
    for name, (schema, expected) in cases.items():
        status, response = compatible("sr29-compatibility", json.dumps(schema))
        results[name] = initial == status == 200 and response.get("is_compatible") is expected
    return results


def probe_bytes() -> bool:
    one = '{"type":"string","title":"value"}'
    two = '{ "title": "value", "type": "string" }'
    first, _ = register("sr29-byte-identity", one)
    second, identifier = register("sr29-byte-identity", two)
    return first == second == 200 and exact_lookup("sr29-byte-identity", identifier["id"], 2, two)


def probe_refs() -> bool:
    name = "https://perfeng.dev/sr29/reference.json"
    dependency = json.dumps({"$id": name, "type": "string"})
    dependent = json.dumps({"$ref": name})
    first, _ = register("sr29-reference", dependency)
    refs = [{"name": name, "subject": "sr29-reference", "version": 1}]
    second, result = register("sr29-dependent", dependent, refs=refs)
    if first != 200 or second != 200:
        return False
    status, version = request("GET", "/subjects/sr29-dependent/versions/1")
    return (
        status == 200
        and version.get("references") == refs
        and exact_lookup("sr29-dependent", result["id"], 1, dependent)
    )


def probe_openapi(profiles: dict[str, dict[str, bytes]]) -> list[dict[str, Any]]:
    rows = []
    for profile, documents in profiles.items():
        for index, (path, raw) in enumerate(sorted(documents.items())):
            if not path.startswith("api/"):
                continue
            subject = f"sr29-api-{profile}-{index}"
            text = raw.decode("utf-8")
            schema = json.loads(text)
            breaking = json.dumps({**schema, "paths": {}})
            status, result = register(subject, text, "OPENAPI")
            gate, observed = compatible(subject, breaking, "OPENAPI")
            generic, _ = register(subject + "-generic", text)
            generic_gate, generic_observed = compatible(subject + "-generic", breaking)
            rows.append(
                {
                    "profile": profile,
                    "path": path,
                    "registrationStatus": status,
                    "genericAcceptsPathRemoval": generic == generic_gate == 200
                    and generic_observed.get("is_compatible") is True,
                    "passed": status == gate == 200
                    and observed.get("is_compatible") is False
                    and exact_lookup(subject, result["id"], 1, text),
                }
            )
    return rows


def exercise() -> dict[str, Any]:
    profiles = corpus()
    rows = [
        row for profile, documents in profiles.items() for row in json_corpus(profile, documents)
    ]
    apis = probe_openapi(profiles)
    compatibility = probe_compatibility()
    return {
        **receipt(
            {
                "current": any(row["profile"] == "current" for row in rows)
                and all(row["passed"] for row in rows if row["profile"] == "current"),
                "historical": any(row["profile"] != "current" for row in rows)
                and all(row["passed"] for row in rows if row["profile"] != "current"),
                "references": probe_refs(),
                "jsonCompatibility": all(compatibility.values()),
                "byteIdentity": probe_bytes(),
                "openapi": bool(apis) and all(row["passed"] for row in apis),
            }
        ),
        "candidate": read_json(LOCK),
        "currentRevision": git(ROOT, "rev-parse", "HEAD").decode().strip(),
        "schemas": rows,
        "apis": apis,
        "compatibility": compatibility,
        "persistence": "not exercised; separate recovery qualification",
    }


def isolated(binary: Path) -> dict[str, Any]:
    links = json.loads(subprocess.check_output(["ip", "-j", "link", "show"], timeout=5))
    if {link["ifname"] for link in links} != {"lo"}:
        raise ValueError("Qualification requires a private loopback-only network namespace")
    with tempfile.TemporaryDirectory(prefix="perfeng-axonops-") as temp:
        root = Path(temp)
        executable = root / "schema-registry"
        data = binary.read_bytes()
        if hashlib.sha256(data).hexdigest() != read_json(LOCK)["binarySha256"]:
            raise ValueError("Candidate executable checksum differs from the reviewed pin")
        executable.write_bytes(data)
        executable.chmod(0o700)
        config = root / "config.yaml"
        config.write_text(
            f"server:\n  host: 127.0.0.1\n  port: {PORT}\n"
            "storage:\n  type: memory\ncompatibility:\n  default_level: BACKWARD\n",
            encoding="utf-8",
        )
        with subprocess.Popen(
            [str(executable), "-config", str(config)],
            cwd=root,
            env={},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ) as process:
            try:
                for _ in range(60):
                    if process.poll() is not None:
                        raise ValueError("Pinned registry exited before readiness")
                    try:
                        if request("GET", "/schemas/types")[0] == 200:
                            return exercise()
                    except OSError:
                        pass
                    time.sleep(0.1)
                raise ValueError("Pinned registry did not become ready")
            finally:
                process.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = isolated(args.binary)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        http.client.HTTPException,
        subprocess.SubprocessError,
    ) as error:
        result = {**receipt({}), "unavailable": str(error)}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ADMITTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
