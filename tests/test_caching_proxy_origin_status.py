from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


ERROR_BODY = "ORIGIN-404-BODY"
SUCCESS_BODY = "VALID-PACKAGE-BYTES"


class CachingProxyOriginStatusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/caching_proxy.py"
        cls.patch = cls.repo / (
            "investigations/caching-proxy-origin-status/"
            "0001-check-origin-status-at-runtime.patch"
        )
        cls.runner = cls.repo / (
            "investigations/caching-proxy-origin-status/run_case.py"
        )
        cls.work = tempfile.TemporaryDirectory(prefix="proxy-origin-status-")
        root = pathlib.Path(cls.work.name)
        cls.baseline = root / "baseline.py"
        cls.candidate_root = root / "candidate"
        cls.candidate = cls.candidate_root / "upstream/mmdebstrap/caching_proxy.py"
        cls.candidate.parent.mkdir(parents=True)
        shutil.copy2(cls.source, cls.baseline)
        shutil.copy2(cls.source, cls.candidate)

        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(cls.patch)],
            cwd=cls.candidate_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if applied.returncode != 0:
            cls.work.cleanup()
            raise AssertionError(applied.stdout + applied.stderr)

        for path in (cls.baseline, cls.candidate, cls.runner):
            compiled = subprocess.run(
                [sys.executable, "-m", "py_compile", str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if compiled.returncode != 0:
                cls.work.cleanup()
                raise AssertionError(compiled.stdout + compiled.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.work.cleanup()

    def run_case(
        self,
        module: pathlib.Path,
        label: str,
        status: int,
        body: str,
        *,
        optimized: bool,
        requests: int = 1,
        reason: str | None = None,
    ) -> dict:
        root = pathlib.Path(self.work.name) / label
        old_cache = root / "old"
        new_cache = root / "new"
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(
            [
                str(self.runner),
                "--module",
                str(module),
                "--old-cache",
                str(old_cache),
                "--new-cache",
                str(new_cache),
                "--status",
                str(status),
                "--body",
                body,
                "--requests",
                str(requests),
            ]
        )
        if reason is not None:
            command.extend(["--reason", reason])
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"{label}:\nstdout={completed.stdout}\nstderr={completed.stderr}",
        )
        return json.loads(completed.stdout)

    def assert_rejected(self, result: dict, *, requests: int) -> None:
        self.assertEqual(result["origin_requests"], requests)
        self.assertEqual(
            [response["status"] for response in result["responses"]],
            [502] * requests,
        )
        self.assertFalse(result["cache_exists"])
        self.assertEqual(result["temporary_paths"], [])

    def test_optimized_baseline_caches_404_as_200(self) -> None:
        result = self.run_case(
            self.baseline,
            "baseline-optimized-404",
            404,
            ERROR_BODY,
            optimized=True,
            requests=2,
        )
        self.assertTrue(result["optimized"])
        self.assertEqual(result["origin_requests"], 1)
        self.assertEqual(
            [response["status"] for response in result["responses"]], [200, 200]
        )
        self.assertEqual(
            [response["text"] for response in result["responses"]],
            [ERROR_BODY, ERROR_BODY],
        )
        self.assertTrue(result["cache_exists"])
        self.assertEqual(result["cache_text"], ERROR_BODY)
        self.assertEqual(result["temporary_paths"], [])

    def test_candidate_rejects_404_with_and_without_optimization(self) -> None:
        for optimized in (False, True):
            result = self.run_case(
                self.candidate,
                f"candidate-404-optimized-{optimized}",
                404,
                ERROR_BODY,
                optimized=optimized,
                requests=2,
            )
            self.assertEqual(result["optimized"], optimized)
            self.assert_rejected(result, requests=2)

    def test_normal_baseline_is_the_nonoptimized_control(self) -> None:
        result = self.run_case(
            self.baseline,
            "baseline-normal-404",
            404,
            ERROR_BODY,
            optimized=False,
            requests=2,
        )
        self.assertFalse(result["optimized"])
        self.assert_rejected(result, requests=2)

    def test_candidate_accepts_200_with_custom_reason_and_caches_once(self) -> None:
        expected_sha = hashlib.sha256(SUCCESS_BODY.encode()).hexdigest()
        for optimized in (False, True):
            result = self.run_case(
                self.candidate,
                f"candidate-200-optimized-{optimized}",
                200,
                SUCCESS_BODY,
                optimized=optimized,
                requests=2,
                reason="Mirror Success",
            )
            self.assertEqual(result["origin_requests"], 1)
            self.assertEqual(
                [response["status"] for response in result["responses"]],
                [200, 200],
            )
            self.assertEqual(
                [response["sha256"] for response in result["responses"]],
                [expected_sha, expected_sha],
            )
            self.assertTrue(result["cache_exists"])
            self.assertEqual(result["cache_sha256"], expected_sha)
            self.assertEqual(result["cache_text"], SUCCESS_BODY)
            self.assertEqual(result["temporary_paths"], [])

    def test_candidate_source_uses_runtime_status_check(self) -> None:
        baseline = self.baseline.read_text(encoding="utf-8")
        candidate = self.candidate.read_text(encoding="utf-8")
        self.assertIn("assert (res.status, res.reason)", baseline)
        self.assertNotIn("assert (res.status, res.reason)", candidate)
        self.assertIn("if res.status != 200", candidate)
        self.assertIn("unexpected upstream response", candidate)
        self.assertNotIn('res.reason) != (200, "OK")', candidate)


if __name__ == "__main__":
    unittest.main()
