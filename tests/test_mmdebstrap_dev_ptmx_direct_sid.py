from __future__ import annotations

import hashlib
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/tests/dev-ptmx"
PATCH = (
    ROOT
    / "investigations/mmdebstrap-dev-ptmx-bsdutils"
    / "dev-ptmx-bsdutils-source.patch"
)
SCRIPT = ROOT / "scripts/reproduce-mmdebstrap-dev-ptmx-direct.sh"
WORKFLOW = ROOT / ".github/workflows/unit09-dev-ptmx-direct-sid.yml"

BASELINE_BLOB = "ca1cde040f945fe871f904ef6a56e040b6a5c9ea"
CANDIDATE_BLOB = "fa93b4b845ff4927a72f258364bd920e8c7dc573"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class MmdebstrapDevPtmxDirectSidTests(unittest.TestCase):
    def test_candidate_applies_exactly_and_matches_controlled_fork_blob(self) -> None:
        self.assertEqual(git_blob_sha(SOURCE.read_bytes()), BASELINE_BLOB)
        with tempfile.TemporaryDirectory(prefix="unit09-direct-") as temporary:
            tree = pathlib.Path(temporary)
            destination = tree / "tests/dev-ptmx"
            destination.parent.mkdir(parents=True)
            shutil.copy2(SOURCE, destination)
            completed = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "-p1",
                    "-d",
                    str(tree),
                    "-i",
                    str(PATCH),
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            combined = (completed.stdout + completed.stderr).lower()
            self.assertNotIn("fuzz", combined)
            self.assertNotIn("offset", combined)
            candidate = destination.read_bytes()

        text = candidate.decode("utf-8")
        self.assertEqual(git_blob_sha(candidate), CANDIDATE_BLOB)
        self.assertIn("--include=bsdutils,gcc,libc6-dev,python3,passwd", text)
        self.assertEqual(text.count("script -c"), 2)

    def test_runner_selects_only_root_apt_dev_ptmx_on_remote_sid(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("MMDEBSTRAP_MIRROR:-https://deb.debian.org/debian", script)
        self.assertIn("MMDEBSTRAP_DIST:-unstable", script)
        self.assertIn("python3 ./coverage.py", script)
        self.assertIn("--mode=root", script)
        self.assertIn("--variant=apt", script)
        self.assertIn("dev-ptmx", script)
        self.assertIn("CMD=/usr/bin/mmdebstrap", script)
        self.assertNotIn("make_mirror.sh", script)
        self.assertIn("residual-mounts.txt", script)
        self.assertIn("residual-files.txt", script)
        self.assertIn("residual-processes.txt", script)
        self.assertIn("cleanup-exit-status", script)

        syntax = subprocess.run(
            ["bash", "-n", str(SCRIPT)],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def test_workflow_is_same_repository_gated_and_disposable(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "github.event.pull_request.head.repo.full_name == github.repository",
            workflow,
        )
        self.assertIn("investigation/mmdebstrap-dev-ptmx-direct-sid", workflow)
        self.assertIn("docker run --privileged --rm", workflow)
        self.assertIn("debian:sid-slim", workflow)
        self.assertIn("bsdutils ca-certificates curl mmdebstrap patch", workflow)
        self.assertIn("python3-debian shellcheck shfmt sudo util-linux", workflow)
        self.assertNotIn("curl findmnt mmdebstrap", workflow)
        self.assertIn("bash scripts/reproduce-mmdebstrap-dev-ptmx-direct.sh", workflow)
        self.assertIn("Upload direct execution evidence", workflow)
        self.assertIn("retention-days: 14", workflow)


if __name__ == "__main__":
    unittest.main()
