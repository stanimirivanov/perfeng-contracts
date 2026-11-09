"""Produce provider admission records from independently reviewed offline inputs."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scripts.contracts_history import INVENTORY, pack_profile, selection, validate_inventory
from scripts.contracts_pack import parse_document
from scripts.contracts_publish import MAX_DOCUMENT_BYTES, digest, manifest, read_bounded
from scripts.validate import ROOT, read_json

VERIFIER_SHA256 = "b768184570b12536be4ac1528893f6340d1c6a7b40b56ad45bca9cd0e87ad34d"
TRUST_ROOT_SHA256 = "455b3fe53e2678889f093d66ebbfda5f12ebb9d682b146c3535fa04e97689787"
POLICY_FIELDS = ("repository", "sourceRevision", "baselineSha256", "direction", "command")


def pinned_bytes(path: Path, limit: int, expected: str) -> bytes:
    content = read_bounded(path, limit)
    if digest(content) != expected:
        raise ValueError(f"Digest mismatch for pinned verifier input: {path.name}")
    return content


def verify_receipt(
    verifier: Path, trust_root: Path, receipt: bytes, bundle: bytes, check: dict[str, str]
) -> None:
    """Authenticate the exact receipt using the independently pinned offline verifier."""
    executable = pinned_bytes(verifier, 128 * 1024 * 1024, VERIFIER_SHA256)
    root_bytes = pinned_bytes(trust_root, 1024 * 1024, TRUST_ROOT_SHA256)
    with tempfile.TemporaryDirectory(prefix="perfeng-admission-") as directory:
        scratch = Path(directory)
        gh, root = scratch / "gh", scratch / "trusted-root.json"
        subject, signature = scratch / "receipt.json", scratch / "receipt.sigstore.jsonl"
        gh.write_bytes(executable)
        gh.chmod(0o700)
        root.write_bytes(root_bytes)
        subject.write_bytes(receipt)
        signature.write_bytes(bundle)
        result = subprocess.run(
            [
                str(gh),
                "attestation",
                "verify",
                str(subject),
                "--bundle",
                str(signature),
                "--custom-trusted-root",
                str(root),
                "--repo",
                check["repository"],
                "--source-ref",
                "refs/heads/main",
                "--source-digest",
                check["sourceRevision"],
                "--signer-workflow",
                check["workflow"],
                "--signer-digest",
                check["signerRevision"],
                "--deny-self-hosted-runners",
            ],
            cwd=scratch,
            env={"HOME": directory, "GH_CONFIG_DIR": directory, "GH_PROMPT_DISABLED": "1"},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise ValueError("Consumer receipt publisher attestation failed")


def checked_policy(candidate: bytes, policy_bytes: bytes, policy_sha256: str) -> dict[str, Any]:
    if len(policy_bytes) > MAX_DOCUMENT_BYTES or digest(policy_bytes) != policy_sha256:
        raise ValueError("Admission policy digest differs from independently reviewed pin")
    policy = parse_document(policy_bytes)
    schema = read_json(ROOT / "distribution/admission.schema.json")
    if not Draft202012Validator(schema).is_valid(policy):
        raise ValueError("Invalid admission policy")
    if policy["candidateSha256"] != digest(candidate):
        raise ValueError("Admission policy does not bind the exact candidate")
    return policy


def admit_changed(
    candidate: bytes,
    policy_bytes: bytes,
    policy_sha256: str,
    receipts: dict[str, tuple[bytes, bytes]],
    verifier: Path,
    trust_root: Path,
) -> dict[str, Any]:
    """Require exactly the independently selected and authenticated passing receipts."""
    value = manifest(candidate, "candidate")
    policy = checked_policy(candidate, policy_bytes, policy_sha256)
    if receipts.keys() != policy["checks"].keys():
        raise ValueError("Missing or unexpected consumer receipt")

    accepted = {}
    for name, check in sorted(policy["checks"].items()):
        receipt, bundle = receipts[name]
        if len(receipt) > MAX_DOCUMENT_BYTES or len(bundle) > MAX_DOCUMENT_BYTES:
            raise ValueError(f"Consumer receipt exceeds size limit: {name}")
        expected = {
            "schemaVersion": 1,
            "check": name,
            "candidateSha256": digest(candidate),
            "archiveSha256": value["archiveSha256"],
            **{key: check[key] for key in POLICY_FIELDS},
            "outcome": "passed",
        }
        if json.dumps(parse_document(receipt), sort_keys=True) != json.dumps(
            expected, sort_keys=True
        ):
            raise ValueError(f"Consumer receipt does not match the required passing check: {name}")
        verify_receipt(verifier, trust_root, receipt, bundle, check)
        accepted[name] = digest(receipt)
    return {
        "schemaVersion": 1,
        "check": "changed-contract-consumer-receipts/v1",
        "candidateSha256": digest(candidate),
        "policySha256": policy_sha256,
        "receiptSha256": accepted,
    }


def admit_historical(candidate: bytes, root: Path, inventory: dict[str, Any]) -> dict[str, Any]:
    """Admit only the exact reviewed historical inventory and canonical packed bytes."""
    value = manifest(candidate, "candidate")
    revision = value["source"]["revision"]
    profile = inventory["profiles"].get(revision)
    if profile is None:
        raise ValueError("Candidate revision is absent from the historical inventory")
    expected = selection(revision, profile)
    if value["source"] != expected["source"] or value["members"] != expected["members"]:
        raise ValueError("Candidate differs from the reviewed historical profile")
    if value["archiveSha256"] != digest(pack_profile(root, revision, profile)):
        raise ValueError("Candidate archive differs from the reviewed historical bytes")
    return {
        "schemaVersion": 1,
        "check": "historical-exact-git-profile/v1",
        "candidateSha256": digest(candidate),
    }


def read_receipts(directory: Path, names: set[str]) -> dict[str, tuple[bytes, bytes]]:
    expected = {f"{name}{suffix}" for name in names for suffix in (".json", ".sigstore.jsonl")}
    if {path.name for path in directory.iterdir()} != expected:
        raise ValueError("Missing or unexpected consumer receipt file")
    return {
        name: (
            read_bounded(directory / f"{name}.json", MAX_DOCUMENT_BYTES),
            read_bounded(directory / f"{name}.sigstore.jsonl", MAX_DOCUMENT_BYTES),
        )
        for name in names
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    historical = actions.add_parser("historical")
    historical.add_argument("--candidate", required=True, type=Path)
    historical.add_argument("--source", type=Path, default=ROOT)
    changed = actions.add_parser("changed")
    for name in ("candidate", "policy", "receipts", "verifier", "trust-root"):
        changed.add_argument(f"--{name}", required=True, type=Path)
    changed.add_argument("--policy-sha256", required=True)
    args = parser.parse_args()
    try:
        candidate = read_bounded(args.candidate, MAX_DOCUMENT_BYTES)
        if args.action == "historical":
            inventory = read_json(INVENTORY)
            validate_inventory(inventory)
            result = admit_historical(candidate, args.source, inventory)
        else:
            policy_bytes = read_bounded(args.policy, MAX_DOCUMENT_BYTES)
            policy = checked_policy(candidate, policy_bytes, args.policy_sha256)
            result = admit_changed(
                candidate,
                policy_bytes,
                args.policy_sha256,
                read_receipts(args.receipts, set(policy["checks"])),
                args.verifier,
                args.trust_root,
            )
        print(json.dumps(result, indent=2, sort_keys=True))
    except (OSError, ValueError, RecursionError, subprocess.SubprocessError) as error:
        parser.exit(1, f"contracts-admission: {error}\n")


if __name__ == "__main__":
    main()
