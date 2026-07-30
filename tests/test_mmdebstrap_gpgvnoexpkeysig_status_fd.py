from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


STATUS = "[GNUPG:] EXPKEYSIG 0123456789ABCDEF expired key\n"
REWRITTEN = STATUS.replace("EXPKEYSIG", "GOODSIG")


class GpgvNoExpKeySigStatusFdTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/gpgvnoexpkeysig"
        cls.patch = cls.repo / (
            "investigations/mmdebstrap-gpgvnoexpkeysig-status-fd/"
            "0001-validate-status-fd-options.patch"
        )
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="gpgvnoexpkeysig-status-fd-"
        )
        root = pathlib.Path(cls.temporary.name)
        cls.fake_bin = root / "bin"
        cls.fake_bin.mkdir()
        cls.marker = root / "gpgv-invoked"
        fake = cls.fake_bin / "gpgv"
        fake.write_text(
            """#!/bin/sh
set -eu
status_fd=1
while [ "$#" -gt 0 ]; do
  case $1 in
    --status-fd)
      status_fd=$2
      shift 2
      ;;
    --status-fd=*)
      status_fd=${1#--status-fd=}
      shift
      ;;
    *)
      shift
      ;;
  esac
done
printf 'invoked\n' >"$FAKE_GPGV_MARKER"
eval 'printf %s "$FAKE_GPGV_STATUS" >&'"$status_fd"
exit 0
""",
            encoding="utf-8",
        )
        fake.chmod(0o755)

        cls.baseline = root / "baseline"
        cls.candidate_root = root / "candidate"
        cls.candidate = cls.candidate_root / "upstream/mmdebstrap/gpgvnoexpkeysig"
        cls.candidate.parent.mkdir(parents=True)
        shutil.copy2(cls.source, cls.baseline)
        shutil.copy2(cls.source, cls.candidate)
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(cls.patch)],
            cwd=cls.candidate_root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if applied.returncode != 0:
            cls.temporary.cleanup()
            raise AssertionError(applied.stdout + applied.stderr)
        for wrapper in (cls.baseline, cls.candidate):
            checked = subprocess.run(
                ["/bin/sh", "-n", str(wrapper)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            if checked.returncode != 0:
                cls.temporary.cleanup()
                raise AssertionError(checked.stdout + checked.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self.fake_bin}:/usr/bin:/bin",
                "FAKE_GPGV_MARKER": str(self.marker),
                "FAKE_GPGV_STATUS": STATUS,
            }
        )
        return env

    def run_plain(
        self, wrapper: pathlib.Path, args: list[str]
    ) -> subprocess.CompletedProcess[str]:
        self.marker.unlink(missing_ok=True)
        return subprocess.run(
            ["/bin/sh", str(wrapper), *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment(),
            timeout=10,
        )

    def run_with_descriptors(
        self,
        wrapper: pathlib.Path,
        argument_builder,
        descriptor_count: int,
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        self.marker.unlink(missing_ok=True)
        pipes = [os.pipe() for _ in range(descriptor_count)]
        read_fds = [pair[0] for pair in pipes]
        write_fds = [pair[1] for pair in pipes]
        args = argument_builder(write_fds)
        try:
            result = subprocess.run(
                ["/bin/sh", str(wrapper), *args],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.environment(),
                pass_fds=tuple(write_fds),
                timeout=10,
            )
        finally:
            for fd in write_fds:
                os.close(fd)
        captured: list[str] = []
        for fd in read_fds:
            with os.fdopen(fd, encoding="utf-8") as stream:
                captured.append(stream.read())
        return result, captured

    def test_missing_value_uses_controlled_wrapper_diagnostic(self) -> None:
        baseline = self.run_plain(self.baseline, ["--status-fd"])
        candidate = self.run_plain(self.candidate, ["--status-fd"])

        self.assertNotEqual(baseline.returncode, 0)
        self.assertEqual(candidate.returncode, 1)
        self.assertIn("invalid --status-fd argument", candidate.stderr)
        self.assertNotIn("parameter not set", candidate.stderr.lower())
        self.assertFalse(self.marker.exists())

    def test_malformed_separate_and_equals_values_are_rejected_before_gpgv(self) -> None:
        for args in (
            ["--status-fd", "abc"],
            ["--status-fd="],
            ["--status-fd=3x"],
            ["--status-fd", "-1"],
        ):
            with self.subTest(args=args):
                result = self.run_plain(self.candidate, args)
                self.assertEqual(result.returncode, 1)
                self.assertIn("invalid --status-fd argument", result.stderr)
                self.assertFalse(self.marker.exists())

    def test_absent_option_keeps_default_stdout_status_stream(self) -> None:
        result = self.run_plain(self.candidate, [])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, REWRITTEN)
        self.assertTrue(self.marker.exists())

    def test_separate_and_equals_forms_select_explicit_descriptor(self) -> None:
        for style in ("separate", "equals"):
            with self.subTest(style=style):
                def arguments(fds: list[int], style: str = style) -> list[str]:
                    if style == "separate":
                        return ["--status-fd", str(fds[0])]
                    return [f"--status-fd={fds[0]}"]

                result, captured = self.run_with_descriptors(
                    self.candidate, arguments, 1
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(captured, [REWRITTEN])
                self.assertTrue(self.marker.exists())

    def test_repeated_valid_options_use_last_occurrence(self) -> None:
        def arguments(fds: list[int]) -> list[str]:
            return [
                "--status-fd",
                str(fds[0]),
                f"--status-fd={fds[1]}",
            ]

        result, captured = self.run_with_descriptors(self.candidate, arguments, 2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(captured, ["", REWRITTEN])
        self.assertTrue(self.marker.exists())

    def test_any_malformed_occurrence_rejects_the_whole_invocation(self) -> None:
        def arguments(fds: list[int]) -> list[str]:
            return [
                "--status-fd",
                str(fds[0]),
                "--status-fd=broken",
            ]

        result, captured = self.run_with_descriptors(self.candidate, arguments, 1)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid --status-fd argument", result.stderr)
        self.assertEqual(captured, [""])
        self.assertFalse(self.marker.exists())

    def test_candidate_source_contract(self) -> None:
        candidate = self.candidate.read_text(encoding="utf-8")
        self.assertIn("if [ \"$#\" -lt 2 ]; then", candidate)
        self.assertIn("--status-fd=*)", candidate)
        self.assertIn("candidate=${1#--status-fd=}", candidate)
        self.assertIn("status_fd=$candidate", candidate)
        self.assertIn(
            'if ! GPGSTATUSFD="$(find_gpgv_status_fd "$@")"; then', candidate
        )


if __name__ == "__main__":
    unittest.main()
