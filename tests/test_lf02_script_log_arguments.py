from __future__ import annotations

import importlib.util
import os
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD = ROOT / "investigations/lf-02-upgrade-failure-recovery/build-fixtures.py"
SUMMARY = ROOT / "investigations/lf-02-upgrade-failure-recovery/summarize.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decode_arguments(value: str) -> list[str]:
    if value == "-":
        return []
    raw = bytes.fromhex(value)
    if not raw.endswith(b"\0"):
        raise ValueError("encoded argument vector lacks trailing NUL")
    return [part.decode("utf-8") for part in raw[:-1].split(b"\0")]


class LF02ScriptLogArgumentsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.build = load_module("lf02_build_fixtures", BUILD)
        cls.summary = load_module("lf02_summarize", SUMMARY)

    def run_script(self, arguments: tuple[str, ...]) -> dict[str, str]:
        with tempfile.TemporaryDirectory(prefix="lf02-script-log-") as td:
            root = pathlib.Path(td)
            target = root / "target"
            target.mkdir()
            script = root / "postinst"
            script.write_text(
                self.build.script_text("postinst", "2.0"), encoding="utf-8"
            )
            script.chmod(0o755)
            environment = os.environ.copy()
            environment["DPKG_ROOT"] = str(target)
            completed = subprocess.run(
                [str(script), *arguments],
                cwd=target,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            lines = (
                target / "var/lib/lf-lifecycle/script.log"
            ).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1, lines)
            return self.summary.parse_script_log_line(lines[0])

    def test_multiple_arguments_remain_one_strict_log_token(self) -> None:
        arguments = (
            "upgrade",
            "1.0",
            "2.0",
            "argument with spaces",
            "line\nbreak",
        )
        fields = self.run_script(arguments)
        self.assertEqual(fields["phase"], "postinst")
        self.assertEqual(fields["script_version"], "2.0")
        self.assertEqual(decode_arguments(fields["args_hex"]), list(arguments))

    def test_empty_argument_vector_uses_explicit_sentinel(self) -> None:
        fields = self.run_script(())
        self.assertEqual(fields["args_hex"], "-")
        self.assertEqual(decode_arguments(fields["args_hex"]), [])

    def test_ambiguous_legacy_argument_tokens_remain_rejected(self) -> None:
        line = (
            "phase=preinst script_version=2.0 args=upgrade 1.0 2.0 "
            "dpkg_root=/target cwd=/target uid=0 gid=0"
        )
        with self.assertRaisesRegex(
            self.summary.ValidationError,
            "script log token is not key=value: '1.0'",
        ):
            self.summary.parse_script_log_line(line)

    def test_generated_source_uses_nul_delimited_hex_not_raw_args(self) -> None:
        source = self.build.script_text("preinst", "1.0")
        self.assertIn("printf '%s\\000' \"$@\"", source)
        self.assertIn("od -An -tx1", source)
        self.assertIn("args_hex=%s", source)
        self.assertNotIn(" args=%s ", source)


if __name__ == "__main__":
    unittest.main()
