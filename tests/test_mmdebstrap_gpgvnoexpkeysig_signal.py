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


class GpgvNoExpKeySigSignalTest(unittest.TestCase):
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

    def prepare(self, root: pathlib.Path, label: str, *, signal_fix: bool) -> pathlib.Path:
        tree = root / label
        destination = tree / "upstream/mmdebstrap/gpgvnoexpkeysig"
        destination.parent.mkdir(parents=True)
        shutil.copy2(self.source, destination)
        patches = [self.status_patch]
        if signal_fix:
            patches.append(self.signal_patch)
        for patch in patches:
            applied = subprocess.run(
                ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
                cwd=tree,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                applied.returncode,
                0,
                f"{patch.name}:\n{applied.stdout}{applied.stderr}",
            )
        syntax = subprocess.run(
            ["/bin/sh", "-n", str(destination)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)
        return destination

    @staticmethod
    def fake_gpgv(directory: pathlib.Path) -> pathlib.Path:
        binary = directory / "gpgv"
        binary.write_text(
            """#!/usr/bin/python3
import os
import pathlib
import sys
import time

os.write(1, os.environ["FAKE_GPGV_STATUS_OUTPUT"].encode())
pathlib.Path(os.environ["FAKE_GPGV_PID_FILE"]).write_text(
    str(os.getpid()), encoding="ascii"
)
if os.environ["FAKE_GPGV_MODE"] == "block":
    time.sleep(60)
raise SystemExit(int(os.environ["FAKE_GPGV_STATUS"]))
""",
            encoding="utf-8",
        )
        binary.chmod(0o755)
        return binary

    @staticmethod
    def process_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def environment(
        self,
        fake_bin: pathlib.Path,
        case_tmp: pathlib.Path,
        pid_file: pathlib.Path,
        *,
        mode: str,
        status: int,
    ) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "TMPDIR": str(case_tmp),
                "FAKE_GPGV_MODE": mode,
                "FAKE_GPGV_STATUS": str(status),
                "FAKE_GPGV_STATUS_OUTPUT": STATUS_LINE,
                "FAKE_GPGV_PID_FILE": str(pid_file),
            }
        )
        return env

    @staticmethod
    def wait_for_pid_file(path: pathlib.Path, process: subprocess.Popen[str]) -> int:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if path.exists():
                return int(path.read_text(encoding="ascii"))
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise AssertionError(
                    f"wrapper exited before verifier start: {process.returncode}\n"
                    f"stdout={stdout}\nstderr={stderr}"
                )
            time.sleep(0.01)
        raise AssertionError("timed out waiting for verifier PID")

    def launch_blocked(
        self,
        wrapper: pathlib.Path,
        fake_bin: pathlib.Path,
        case_tmp: pathlib.Path,
        pid_file: pathlib.Path,
    ) -> subprocess.Popen[str]:
        return subprocess.Popen(
            ["/bin/sh", str(wrapper)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment(
                fake_bin, case_tmp, pid_file, mode="block", status=0
            ),
            start_new_session=True,
        )

    def test_parent_only_term_is_forwarded_and_children_are_reaped(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gpgv-wrapper-signal-") as tmp:
            root = pathlib.Path(tmp)
            predecessor = self.prepare(root, "predecessor", signal_fix=False)
            candidate = self.prepare(root, "candidate", signal_fix=True)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            self.fake_gpgv(fake_bin)

            predecessor_tmp = root / "predecessor-tmp"
            predecessor_tmp.mkdir()
            predecessor_pid_file = root / "predecessor.pid"
            predecessor_process = self.launch_blocked(
                predecessor,
                fake_bin,
                predecessor_tmp,
                predecessor_pid_file,
            )
            predecessor_child = self.wait_for_pid_file(
                predecessor_pid_file, predecessor_process
            )
            os.kill(predecessor_process.pid, signal.SIGTERM)
            time.sleep(0.5)
            self.assertIsNone(
                predecessor_process.poll(),
                "predecessor unexpectedly forwarded wrapper-only SIGTERM",
            )
            self.assertTrue(self.process_exists(predecessor_child))
            os.killpg(predecessor_process.pid, signal.SIGKILL)
            predecessor_process.communicate(timeout=5)

            candidate_tmp = root / "candidate-tmp"
            candidate_tmp.mkdir()
            candidate_pid_file = root / "candidate.pid"
            candidate_process = self.launch_blocked(
                candidate,
                fake_bin,
                candidate_tmp,
                candidate_pid_file,
            )
            candidate_child = self.wait_for_pid_file(
                candidate_pid_file, candidate_process
            )
            os.kill(candidate_process.pid, signal.SIGTERM)
            stdout, stderr = candidate_process.communicate(timeout=10)
            self.assertEqual(candidate_process.returncode, 143, stderr)
            self.assertEqual(stdout, EXPECTED_LINE)
            self.assertFalse(self.process_exists(candidate_child))
            self.assertEqual(list(candidate_tmp.iterdir()), [])

    def run_status(
        self,
        wrapper: pathlib.Path,
        fake_bin: pathlib.Path,
        case_tmp: pathlib.Path,
        pid_file: pathlib.Path,
        status: int,
    ) -> subprocess.CompletedProcess[str]:
        case_tmp.mkdir()
        return subprocess.run(
            ["/bin/sh", str(wrapper)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment(
                fake_bin, case_tmp, pid_file, mode="exit", status=status
            ),
            timeout=10,
        )

    def test_ordinary_status_and_output_precedence_are_unchanged(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gpgv-wrapper-status-") as tmp:
            root = pathlib.Path(tmp)
            predecessor = self.prepare(root, "predecessor", signal_fix=False)
            candidate = self.prepare(root, "candidate", signal_fix=True)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            self.fake_gpgv(fake_bin)

            for status in (0, 2):
                for label, wrapper in (
                    ("predecessor", predecessor),
                    ("candidate", candidate),
                ):
                    with self.subTest(status=status, wrapper=label):
                        case_tmp = root / f"{label}-{status}-tmp"
                        result = self.run_status(
                            wrapper,
                            fake_bin,
                            case_tmp,
                            root / f"{label}-{status}.pid",
                            status,
                        )
                        self.assertEqual(result.returncode, status, result.stderr)
                        self.assertEqual(result.stdout, EXPECTED_LINE)
                        self.assertEqual(list(case_tmp.iterdir()), [])

    def test_candidate_source_owns_verifier_and_filter_pids(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gpgv-wrapper-source-") as tmp:
            root = pathlib.Path(tmp)
            predecessor = self.prepare(root, "predecessor", signal_fix=False)
            candidate = self.prepare(root, "candidate", signal_fix=True)
            old = predecessor.read_text(encoding="utf-8")
            new = candidate.read_text(encoding="utf-8")
            self.assertNotIn("GPGV_PID=", old)
            self.assertIn("GPGV_PID=", new)
            self.assertIn('if wait "$GPGV_PID"; then', new)
            self.assertIn('kill -"$signum" "$GPGV_PID"', new)
            self.assertIn("trap - EXIT HUP INT TERM", new)
            self.assertIn("FILTER_PID=", new)


if __name__ == "__main__":
    unittest.main()
