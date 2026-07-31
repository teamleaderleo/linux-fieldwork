from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
HELPER = ROOT / (
    "investigations/mmdebstrap-chrootless-env/classify_env_invocations.py"
)


class ChrootlessEnvInvocationReceiptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location(
            "classify_env_invocations_tested", HELPER
        )
        if spec is None or spec.loader is None:
            raise AssertionError("failed to load env invocation classifier")
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls) -> None:
        sys.modules.pop("classify_env_invocations_tested", None)

    def run_helper(
        self,
        records: list[list[str]],
        expectation: str,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object] | None]:
        with tempfile.TemporaryDirectory(prefix="env-invocation-receipt-") as td:
            root = pathlib.Path(td)
            log = root / "env.jsonl"
            summary = root / "summary.json"
            log.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    "python3",
                    str(HELPER),
                    str(log),
                    "--governed-dpkg",
                    expectation,
                    "--summary",
                    str(summary),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            parsed = (
                json.loads(summary.read_text(encoding="utf-8"))
                if summary.exists()
                else None
            )
            return completed, parsed

    def test_command_parser_skips_options_assignments_and_separator(self) -> None:
        cases = (
            (["-i", "PATH=/usr/bin", "TMPDIR=/tmp", "dpkg", "--root=/tmp/r"], "dpkg"),
            (["--ignore-environment", "A=B", "--", "/usr/bin/dpkg", "-i"], "/usr/bin/dpkg"),
            (["--unset", "LD_PRELOAD", "PATH=/usr/bin", "sh", "-c", "true"], "sh"),
            (["--chdir=/tmp", "--version"], None),
            (["--version"], None),
            ([], None),
        )
        for argv, expected in cases:
            with self.subTest(argv=argv):
                self.assertEqual(self.module.command_from_env_argv(argv), expected)

    def test_forbid_accepts_version_and_unrelated_host_invocations(self) -> None:
        completed, summary = self.run_helper(
            [
                ["--version"],
                ["--unset=LD_PRELOAD", "/bin/sh", "-c", "true"],
                ["NAME=value with spaces", "printf", "%s", "x y"],
            ],
            "forbid",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        assert summary is not None
        self.assertEqual(summary["version_probe_count"], 1)
        self.assertEqual(summary["governed_dpkg_count"], 0)
        self.assertEqual(len(summary["other_invocations"]), 2)

    def test_forbid_rejects_governed_dpkg_even_with_absolute_spelling(self) -> None:
        for command in ("dpkg", "/usr/bin/dpkg"):
            with self.subTest(command=command):
                completed, summary = self.run_helper(
                    [["-i", "PATH=/usr/bin", command, "--force-script-chrootless"]],
                    "forbid",
                )
                self.assertEqual(completed.returncode, 1)
                self.assertIn("launched governed dpkg", completed.stderr)
                self.assertIsNone(summary)

    def test_require_needs_at_least_one_governed_dpkg_launch(self) -> None:
        missing, summary = self.run_helper([["--version"]], "require")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("did not launch governed dpkg", missing.stderr)
        self.assertIsNone(summary)

        present, summary = self.run_helper(
            [
                ["--version"],
                ["-i", "PATH=/caller", "dpkg", "--root=/tmp/root", "--unpack"],
            ],
            "require",
        )
        self.assertEqual(present.returncode, 0, present.stderr)
        assert summary is not None
        self.assertEqual(summary["governed_dpkg_count"], 1)

    def test_malformed_or_unsupported_receipt_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="env-invocation-invalid-") as td:
            root = pathlib.Path(td)
            for label, content in (
                ("json", "not-json\n"),
                ("schema", '{"argv": []}\n'),
                ("option", '["--unknown", "dpkg"]\n'),
            ):
                with self.subTest(label=label):
                    log = root / f"{label}.jsonl"
                    log.write_text(content, encoding="utf-8")
                    completed = subprocess.run(
                        [
                            "python3",
                            str(HELPER),
                            str(log),
                            "--governed-dpkg",
                            "forbid",
                        ],
                        check=False,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=10,
                    )
                    self.assertEqual(completed.returncode, 2)
                    self.assertIn("receipt validation failed", completed.stderr)


if __name__ == "__main__":
    unittest.main()
