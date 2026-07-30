from __future__ import annotations

import os
import pathlib
import shutil
import signal
import subprocess
import tempfile
import time
import unittest


STATUS_LINE = "[GNUPG:] EXPKEYSIG 0123456789ABCDEF expired key\n"
EXPECTED_LINE = STATUS_LINE.replace("EXPKEYSIG", "GOODSIG")


class GpgvSignalPidWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/gpgvnoexpkeysig"
        cls.status_patch = cls.repo / (
            "investigations/mmdebstrap-gpgvnoexpkeysig-status/"
            "0001-preserve-gpgv-status.patch"
        )
        cls.signal_patch = cls.repo / (
            "investigations/mmdebstrap-gpgvnoexpkeysig-signal/"
            "0001-forward-signals-to-gpgv.patch"
        )

    def prepare(self, root: pathlib.Path, label: str) -> pathlib.Path:
        tree = root / label
        wrapper = tree / "upstream/mmdebstrap/gpgvnoexpkeysig"
        wrapper.parent.mkdir(parents=True)
        shutil.copy2(self.source, wrapper)
        for patch in (self.status_patch, self.signal_patch):
            applied = subprocess.run(
                ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
                cwd=tree,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(
                applied.returncode,
                0,
                f"{patch.name}:\n{applied.stdout}{applied.stderr}",
            )
        return wrapper

    @staticmethod
    def process_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def assert_process_gone(self, pid: int) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and self.process_exists(pid):
            time.sleep(0.02)
        self.assertFalse(self.process_exists(pid))

    @staticmethod
    def fake_gpgv(directory: pathlib.Path) -> None:
        binary = directory / "gpgv"
        binary.write_text(
            """#!/usr/bin/env python3
import os
import pathlib
import sys
import time

os.write(1, os.environ["FAKE_GPGV_STATUS_OUTPUT"].encode())
pathlib.Path(os.environ["FAKE_GPGV_PID_FILE"]).write_text(
    str(os.getpid()), encoding="ascii"
)
if os.environ.get("FAKE_GPGV_BLOCK") == "yes":
    time.sleep(60)
raise SystemExit(0)
""",
            encoding="utf-8",
        )
        binary.chmod(0o755)

    @staticmethod
    def fake_sed(directory: pathlib.Path) -> None:
        binary = directory / "sed"
        binary.write_text(
            """#!/bin/sh
set -eu
printf '%s\n' "$$" >"$FAKE_SED_PID_FILE"
sleep 60
""",
            encoding="utf-8",
        )
        binary.chmod(0o755)

    def environment(
        self,
        fake_bin: pathlib.Path,
        case_tmp: pathlib.Path,
        gpgv_pid_file: pathlib.Path,
        sed_pid_file: pathlib.Path,
        *,
        block_gpgv: bool,
    ) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "TMPDIR": str(case_tmp),
                "FAKE_GPGV_STATUS_OUTPUT": STATUS_LINE,
                "FAKE_GPGV_PID_FILE": str(gpgv_pid_file),
                "FAKE_GPGV_BLOCK": "yes" if block_gpgv else "no",
                "FAKE_SED_PID_FILE": str(sed_pid_file),
            }
        )
        return env

    @staticmethod
    def wait_for_pid(path: pathlib.Path, process: subprocess.Popen[str]) -> int:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if path.exists():
                return int(path.read_text(encoding="ascii"))
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise AssertionError(
                    f"wrapper exited before child PID record: {process.returncode}\n"
                    f"stdout={stdout}\nstderr={stderr}"
                )
            time.sleep(0.01)
        raise AssertionError(f"timed out waiting for {path}")

    def inject(self, wrapper: pathlib.Path, old: str, new: str) -> None:
        source = wrapper.read_text(encoding="utf-8")
        self.assertEqual(source.count(old), 1)
        wrapper.write_text(source.replace(old, new, 1), encoding="utf-8")
        syntax = subprocess.run(
            ["/bin/sh", "-n", str(wrapper)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def test_signal_between_gpgv_launch_and_pid_assignment_is_owned(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gpgv-pid-window-") as tmp:
            root = pathlib.Path(tmp)
            wrapper = self.prepare(root, "candidate")
            fake_bin = root / "bin"
            fake_bin.mkdir()
            self.fake_gpgv(fake_bin)
            gpgv_pid_file = root / "gpgv.pid"
            sed_pid_file = root / "sed.pid"
            case_tmp = root / "tmp"
            case_tmp.mkdir()

            old = """GPGV_STARTING=yes
eval 'gpgv \"$@\" '"$GPGSTATUSFD"'>\"$STATUS_FILE\"' &
GPGV_PID=$!
GPGV_STARTING=no
"""
            new = """GPGV_STARTING=yes
eval 'gpgv \"$@\" '"$GPGSTATUSFD"'>\"$STATUS_FILE\"' &
while [ ! -s \"$FAKE_GPGV_PID_FILE\" ]; do sleep 0.01; done
kill -TERM $$
GPGV_PID=$!
GPGV_STARTING=no
"""
            self.inject(wrapper, old, new)

            process = subprocess.Popen(
                ["/bin/sh", str(wrapper)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.environment(
                    fake_bin,
                    case_tmp,
                    gpgv_pid_file,
                    sed_pid_file,
                    block_gpgv=True,
                ),
                start_new_session=True,
            )
            child_pid = self.wait_for_pid(gpgv_pid_file, process)
            stdout, stderr = process.communicate(timeout=10)

            self.assertEqual(process.returncode, 143, stderr)
            self.assertEqual(stdout, EXPECTED_LINE)
            self.assert_process_gone(child_pid)
            self.assertEqual(list(case_tmp.iterdir()), [])

    def test_signal_between_filter_launch_and_pid_assignment_is_owned(self) -> None:
        with tempfile.TemporaryDirectory(prefix="filter-pid-window-") as tmp:
            root = pathlib.Path(tmp)
            wrapper = self.prepare(root, "candidate")
            fake_bin = root / "bin"
            fake_bin.mkdir()
            self.fake_gpgv(fake_bin)
            self.fake_sed(fake_bin)
            gpgv_pid_file = root / "gpgv.pid"
            sed_pid_file = root / "sed.pid"
            case_tmp = root / "tmp"
            case_tmp.mkdir()

            old = """  FILTER_STARTING=yes
  eval 'sed \"s/^\\[GNUPG:\\] EXPKEYSIG /[GNUPG:] GOODSIG /\" <\"$STATUS_FILE\" >&'"$GPGSTATUSFD" &
  FILTER_PID=$!
  FILTER_STARTING=no
"""
            new = """  FILTER_STARTING=yes
  eval 'sed \"s/^\\[GNUPG:\\] EXPKEYSIG /[GNUPG:] GOODSIG /\" <\"$STATUS_FILE\" >&'"$GPGSTATUSFD" &
  while [ ! -s \"$FAKE_SED_PID_FILE\" ]; do sleep 0.01; done
  kill -TERM $$
  FILTER_PID=$!
  FILTER_STARTING=no
"""
            self.inject(wrapper, old, new)

            process = subprocess.Popen(
                ["/bin/sh", str(wrapper)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.environment(
                    fake_bin,
                    case_tmp,
                    gpgv_pid_file,
                    sed_pid_file,
                    block_gpgv=False,
                ),
                start_new_session=True,
            )
            filter_pid = self.wait_for_pid(sed_pid_file, process)
            stdout, stderr = process.communicate(timeout=10)

            self.assertEqual(process.returncode, 143, stderr)
            self.assertEqual(stdout, "")
            self.assert_process_gone(filter_pid)
            self.assertEqual(list(case_tmp.iterdir()), [])

    def test_candidate_source_tracks_launch_windows(self) -> None:
        with tempfile.TemporaryDirectory(prefix="signal-window-source-") as tmp:
            wrapper = self.prepare(pathlib.Path(tmp), "candidate")
            source = wrapper.read_text(encoding="utf-8")
            self.assertIn("GPGV_STARTING=no", source)
            self.assertIn("FILTER_STARTING=no", source)
            self.assertIn("capture_starting_pids()", source)
            self.assertIn('GPGV_PID=$!', source)
            self.assertIn('FILTER_PID=$!', source)
            self.assertIn("capture_starting_pids\n", source)


if __name__ == "__main__":
    unittest.main()
