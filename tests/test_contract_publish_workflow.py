"""Check the hosted tracer policy and its release inputs without GitHub writes."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts.contracts_pack import parse_document
from scripts.contracts_publish import digest
from scripts.contracts_tracer import prepare
from scripts.validate import ROOT


class ContractPublishWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = yaml.load(
            (ROOT / ".github/workflows/contracts-publish.yml").read_text(encoding="utf-8"),
            Loader=yaml.BaseLoader,
        )

    def test_hosted_jobs_are_manual_gated_and_least_privileged(self) -> None:
        workflow = self.workflow
        self.assertEqual(set(workflow["on"]), {"workflow_dispatch"})
        self.assertEqual(workflow["permissions"], {})
        jobs = workflow["jobs"]
        self.assertEqual(set(jobs), {"prepare", "attest", "publish"})
        for job in jobs.values():
            self.assertIn("github.ref == 'refs/heads/main'", job["if"])
            self.assertIn("github.ref_protected", job["if"])
            self.assertIn("github.sha == inputs.expected_sha", job["if"])
            self.assertIn("vars.PERFENG_TRACER_PUBLICATION_ENABLED == 'true'", job["if"])
            self.assertEqual(job["runs-on"], "ubuntu-24.04")
            for step in job["steps"]:
                if "uses" in step:
                    self.assertRegex(step["uses"], r"^[^@]+@[a-f0-9]{40}$")

        self.assertEqual(jobs["prepare"]["permissions"], {"contents": "read"})
        self.assertEqual(jobs["attest"]["needs"], "prepare")
        self.assertEqual(
            jobs["attest"]["permissions"],
            {"contents": "read", "id-token": "write", "attestations": "write"},
        )
        self.assertEqual(jobs["publish"]["needs"], "attest")
        self.assertEqual(jobs["publish"]["permissions"], {"contents": "write"})
        self.assertEqual(jobs["attest"]["environment"], "contract-tracer-attestation")
        self.assertEqual(jobs["publish"]["environment"], "contract-tracer-publication")
        script = jobs["publish"]["steps"][-1]["run"]
        self.assertLess(script.index("--draft"), script.index("--draft=false"))
        self.assertNotIn("--clobber", script)

    def test_failed_draft_upload_cannot_reach_publication(self) -> None:
        script = self.workflow["jobs"]["publish"]["steps"][-1]["run"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = root / "release-inputs"
            inputs.mkdir()
            for name in (
                "candidate.json",
                "admission.json",
                "manifest.json",
                "manifest.sigstore.jsonl",
                "tracer.tar.gz",
            ):
                (inputs / name).write_bytes(b"fixture")
            cli = root / "tracer-gh"
            cli.write_text(
                '#!/bin/bash\nprintf "%s\\n" "$1 $2" >> calls\n'
                'if [[ "$1 $2" == "release create" ]]; then exit 1; fi\n',
                encoding="utf-8",
            )
            cli.chmod(0o700)
            result = subprocess.run(
                ["bash", "-e", "-o", "pipefail", "-c", script],
                cwd=root,
                env={
                    "PATH": os.defpath,
                    "RUNNER_TEMP": str(root),
                    "RELEASE_ID": "contract-tracer-123",
                    "GITHUB_RUN_ID": "123",
                    "GITHUB_REPOSITORY": "stanimirivanov/perfeng-contracts",
                    "GITHUB_SHA": "a" * 40,
                },
                check=False,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((root / "calls").read_text(), "api --method\nrelease create\n")

    @patch("scripts.contracts_tracer.pack", return_value=b"test archive")
    def test_tracer_binds_exact_archive_candidate_and_admission(self, _pack) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            prepare(output, "contract-tracer-123")
            self.assertEqual(
                sorted(path.name for path in output.iterdir()),
                ["admission.json", "candidate.json", "manifest.json", "tracer.tar.gz"],
            )
            tracer = parse_document((ROOT / "distribution/tracer.json").read_bytes())
            candidate = (output / "candidate.json").read_bytes()
            admission = (output / "admission.json").read_bytes()
            manifest = parse_document((output / "manifest.json").read_bytes())
            self.assertEqual(manifest["kind"], "promoted")
            self.assertEqual(manifest["source"], tracer["source"])
            self.assertEqual(manifest["members"], tracer["members"])
            self.assertEqual(manifest["archiveSha256"], digest(b"test archive"))
            self.assertEqual(manifest["admissionSha256"], digest(admission))
            self.assertEqual(parse_document(admission)["candidateSha256"], digest(candidate))
            with self.assertRaises(FileExistsError):
                prepare(output, "contract-tracer-123")

    def test_tracer_refuses_other_release_namespaces(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            with self.assertRaisesRegex(ValueError, "tracer release"):
                prepare(output, "v0.22.0")
            self.assertFalse(output.exists())
